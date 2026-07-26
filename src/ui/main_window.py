from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import config
from src.app.application import Application
from src.config.settings import Settings
from src.shared.character_slots import CharacterSlot

# Onde a interface lembra o caminho do client entre execuções.
GUI_SETTINGS_FILE = Path(__file__).resolve().parents[2] / "gui_settings.json"

# Onde ficam as contas cadastradas. Mesmo nível de sensibilidade do
# .env / gui_settings.json -- fica em texto puro no disco (senha
# incluída), então não sincronize essa pasta nem suba pra repositório
# compartilhado.
ACCOUNTS_FILE = Path(__file__).resolve().parents[2] / "accounts.json"


# =====================================================
# Modelo de conta + persistência
# =====================================================

@dataclass
class Account:
    label: str
    username: str
    password: str
    server_name: str
    character_slot: str


def load_accounts() -> list[Account]:
    if not ACCOUNTS_FILE.exists():
        return []
    try:
        data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        return [Account(**item) for item in data]
    except Exception:
        return []


def save_accounts(accounts: list[Account]):
    data = [asdict(a) for a in accounts]
    try:
        ACCOUNTS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[GUI] Aviso: não foi possível salvar as contas ({e})")


# =====================================================
# Redirecionamento de log com identificação por conta
# =====================================================

class MultiAccountLogRedirector:
    """
    Substitui sys.stdout enquanto a automação roda. Como várias contas
    podem estar rodando ao mesmo tempo (cada uma na sua própria
    thread), cada linha impressa é prefixada com o apelido da conta
    responsável, pra não misturar os logs na mesma caixa de texto.

    O mapeamento thread -> apelido é registrado/removido pela própria
    thread de cada conta (ver AccountRunner).
    """

    def __init__(self, widget: tk.Text, original):
        self.widget = widget
        self.original = original
        self._labels: dict[int, str] = {}
        self._buffers: dict[int, str] = {}
        self._lock = threading.Lock()

    def register(self, label: str):
        with self._lock:
            self._labels[threading.get_ident()] = label

    def unregister(self):
        with self._lock:
            self._labels.pop(threading.get_ident(), None)
            self._buffers.pop(threading.get_ident(), None)

    def write(self, text: str):
        self.original.write(text)

        ident = threading.get_ident()

        with self._lock:
            label = self._labels.get(ident)
            buf = self._buffers.get(ident, "") + text

            lines_to_flush = []
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                lines_to_flush.append(line)

            self._buffers[ident] = buf

        for line in lines_to_flush:
            prefixed = f"[{label}] {line}" if label else line
            self.widget.after(0, self._append, prefixed + "\n")

    def _append(self, text: str):
        self.widget.configure(state="normal")
        self.widget.insert("end", text)
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        self.original.flush()


# =====================================================
# Diálogo de adicionar/editar conta
# =====================================================

class AccountDialog(tk.Toplevel):

    def __init__(self, parent, title: str, account: Account | None = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)

        self.result: Account | None = None

        self.label_var = tk.StringVar(value=account.label if account else "")
        self.username_var = tk.StringVar(value=account.username if account else "")
        self.password_var = tk.StringVar(value=account.password if account else "")
        self.server_var = tk.StringVar(value=account.server_name if account else config.SERVER_NAME)
        self.slot_var = tk.StringVar(value=account.character_slot if account else CharacterSlot.CENTER)

        form = ttk.Frame(self, padding=12)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Apelido:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.label_var, width=30).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Usuário:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.username_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Senha:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.password_var, show="*").grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Servidor:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.server_var).grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Personagem:").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Combobox(
            form,
            textvariable=self.slot_var,
            values=[CharacterSlot.LEFT, CharacterSlot.CENTER, CharacterSlot.RIGHT],
            state="readonly",
        ).grid(row=4, column=1, sticky="ew", pady=4)

        buttons = ttk.Frame(form)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="Salvar", command=self._on_save).pack(side="right")

        self.grab_set()
        self.wait_window()

    def _on_save(self):
        label = self.label_var.get().strip()
        username = self.username_var.get().strip()

        if not label or not username or not self.password_var.get():
            messagebox.showwarning(
                "Campos obrigatórios",
                "Preencha ao menos apelido, usuário e senha.",
            )
            return

        self.result = Account(
            label=label,
            username=username,
            password=self.password_var.get(),
            server_name=self.server_var.get().strip(),
            character_slot=self.slot_var.get(),
        )
        self.destroy()


# =====================================================
# Janela principal
# =====================================================

class MainWindow:
    """
    Janela principal: cadastro de contas (apelido, usuário, senha,
    servidor, personagem), seleção de múltiplas contas pra logar de
    uma vez, e log em tempo real identificado por conta.

    Cada conta selecionada roda numa thread própria, cada uma abrindo
    seu próprio client e operando de forma independente -- então dá
    pra logar várias contas em paralelo, não uma de cada vez.
    """

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("Talisman Online - Auto Login")
        self.root.geometry("700x620")
        self.root.minsize(620, 480)

        self.accounts: list[Account] = load_accounts()
        self._active_threads = 0
        self._active_lock = threading.Lock()

        self._build_client_path_field()
        self._build_accounts_panel()
        self._build_log_area()
        self._load_saved_client_path()
        self._refresh_accounts_list()

        self.log_redirector = MultiAccountLogRedirector(self.log_text, sys.stdout)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # =====================================================
    # Construção da interface
    # =====================================================

    def _build_client_path_field(self):

        frame = ttk.Frame(self.root, padding=(12, 12, 12, 0))
        frame.pack(fill="x")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Client (.exe/.bat):").grid(row=0, column=0, sticky="w")
        self.client_path_var = tk.StringVar(value=config.CLIENT_PATH)
        ttk.Entry(frame, textvariable=self.client_path_var).grid(row=0, column=1, sticky="ew", padx=(6, 6))
        ttk.Button(frame, text="Procurar...", command=self._browse_client_path).grid(row=0, column=2)

    def _build_accounts_panel(self):

        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=False)

        ttk.Label(frame, text="Contas cadastradas (selecione uma ou mais pra logar):").pack(anchor="w")

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, pady=(4, 6))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.accounts_listbox = tk.Listbox(
            list_frame,
            selectmode="extended",
            height=8,
            yscrollcommand=scrollbar.set,
        )
        self.accounts_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.accounts_listbox.yview)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        ttk.Button(buttons, text="Adicionar", command=self._on_add_account).pack(side="left")
        ttk.Button(buttons, text="Editar", command=self._on_edit_account).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Remover", command=self._on_remove_account).pack(side="left", padx=(6, 0))

        self.start_button = ttk.Button(
            buttons, text="Logar Selecionadas", command=self._on_start_selected
        )
        self.start_button.pack(side="right")

    def _build_log_area(self):

        frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Log:").pack(anchor="w")

        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            text_frame,
            state="disabled",
            wrap="word",
            yscrollcommand=scrollbar.set,
            height=14,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

    # =====================================================
    # Persistência
    # =====================================================

    def _load_saved_client_path(self):

        if not GUI_SETTINGS_FILE.exists():
            return

        try:
            data = json.loads(GUI_SETTINGS_FILE.read_text(encoding="utf-8"))
            self.client_path_var.set(data.get("client_path", config.CLIENT_PATH))
        except Exception:
            pass

    def _save_client_path(self):

        data = {"client_path": self.client_path_var.get()}

        try:
            GUI_SETTINGS_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[GUI] Aviso: não foi possível salvar as configurações ({e})")

    def _refresh_accounts_list(self):

        self.accounts_listbox.delete(0, "end")

        for account in self.accounts:
            self.accounts_listbox.insert(
                "end",
                f"{account.label}  —  usuário: {account.username}  "
                f"—  servidor: {account.server_name}  —  slot: {account.character_slot}",
            )

    def _on_close(self):
        self._save_client_path()
        self.root.destroy()

    # =====================================================
    # Gerenciamento de contas
    # =====================================================

    def _browse_client_path(self):

        path = filedialog.askopenfilename(
            title="Selecione o executável/launcher do client",
            filetypes=[
                ("Executáveis", "*.exe;*.bat;*.cmd"),
                ("Todos os arquivos", "*.*"),
            ],
        )

        if path:
            self.client_path_var.set(path)

    def _on_add_account(self):

        dialog = AccountDialog(self.root, "Adicionar conta")

        if dialog.result:
            self.accounts.append(dialog.result)
            save_accounts(self.accounts)
            self._refresh_accounts_list()

    def _on_edit_account(self):

        index = self._get_single_selected_index()

        if index is None:
            return

        dialog = AccountDialog(self.root, "Editar conta", self.accounts[index])

        if dialog.result:
            self.accounts[index] = dialog.result
            save_accounts(self.accounts)
            self._refresh_accounts_list()

    def _on_remove_account(self):

        index = self._get_single_selected_index()

        if index is None:
            return

        account = self.accounts[index]

        if not messagebox.askyesno(
            "Remover conta", f"Remover a conta '{account.label}'?"
        ):
            return

        del self.accounts[index]
        save_accounts(self.accounts)
        self._refresh_accounts_list()

    def _get_single_selected_index(self) -> int | None:

        selection = self.accounts_listbox.curselection()

        if not selection:
            messagebox.showinfo("Nenhuma conta selecionada", "Selecione uma conta na lista.")
            return None

        if len(selection) > 1:
            messagebox.showinfo(
                "Selecione apenas uma", "Essa ação funciona com uma conta por vez."
            )
            return None

        return selection[0]

    # =====================================================
    # Execução (uma ou várias contas em paralelo)
    # =====================================================

    def _on_start_selected(self):

        selection = self.accounts_listbox.curselection()

        if not selection:
            messagebox.showinfo(
                "Nenhuma conta selecionada",
                "Selecione uma ou mais contas na lista antes de logar.",
            )
            return

        client_path = self.client_path_var.get().strip()

        if not client_path:
            messagebox.showwarning(
                "Client não informado", "Informe o caminho do client antes de continuar."
            )
            return

        self._save_client_path()

        selected_accounts = [self.accounts[i] for i in selection]

        self._clear_log()

        sys.stdout = self.log_redirector

        self.start_button.configure(state="disabled", text="Rodando...")

        for account in selected_accounts:
            thread = threading.Thread(
                target=self._run_account,
                args=(account, client_path),
                daemon=True,
            )
            with self._active_lock:
                self._active_threads += 1
            thread.start()

    def _run_account(self, account: Account, client_path: str):

        self.log_redirector.register(account.label)

        settings = replace(
            Settings(),
            username=account.username,
            password=account.password,
            server_name=account.server_name,
            character_slot=account.character_slot,
            client_path=client_path,
        )

        try:
            app = Application(settings=settings)
            try:
                app.start()
                print(f"[{account.label}] Login concluído com sucesso!")
            finally:
                app.shutdown()

        except Exception as e:
            print(f"[{account.label}] Falhou: {e}")

        finally:
            self.log_redirector.unregister()

            with self._active_lock:
                self._active_threads -= 1
                remaining = self._active_threads

            if remaining <= 0:
                self.root.after(0, self._on_all_finished)

    def _on_all_finished(self):

        sys.stdout = self.log_redirector.original
        self.start_button.configure(state="normal", text="Logar Selecionadas")

    # =====================================================
    # Log
    # =====================================================

    def _clear_log(self):

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # =====================================================
    # Execução
    # =====================================================

    def run(self):

        self.root.mainloop()