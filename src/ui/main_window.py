from __future__ import annotations

import json
import sys
import threading
import time
import tkinter as tk
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import win32gui

from src.app.application import Application
from src.config.settings import Settings
from src.shared.character_slots import CharacterSlot

GUI_SETTINGS_FILE = Path(__file__).resolve().parents[2] / "gui_settings.json"
ACCOUNTS_FILE = Path(__file__).resolve().parents[2] / "accounts.json"

_DEFAULTS = Settings()


# =====================================================
# Modelo de conta + persistencia
# =====================================================

@dataclass
class Account:
    label: str
    username: str
    password: str
    server_name: str
    character_slot: str
    auto_login: bool = False


def load_accounts() -> list[Account]:
    if not ACCOUNTS_FILE.exists():
        return []
    try:
        data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        accounts = []
        for item in data:
            item.setdefault("auto_login", False)
            accounts.append(Account(**item))
        return accounts
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
        print(f"[GUI] Aviso: nao foi possivel salvar as contas ({e})")


# =====================================================
# Redirecionamento de log com identificacao por conta
# =====================================================

class MultiAccountLogRedirector:
    """
    Substitui sys.stdout enquanto a automacao roda. Cada linha impressa
    e prefixada com o apelido da conta responsavel.
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
# Dialogo de adicionar / editar conta
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
        self.server_var = tk.StringVar(value=account.server_name if account else _DEFAULTS.server_name)
        self.slot_var = tk.StringVar(value=account.character_slot if account else CharacterSlot.CENTER)
        self.auto_login_var = tk.BooleanVar(value=account.auto_login if account else False)

        form = ttk.Frame(self, padding=12)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Apelido:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.label_var, width=30).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Usuario:").grid(row=1, column=0, sticky="w", pady=4)
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

        ttk.Checkbutton(
            form,
            text="Auto-login ao abrir o Bot",
            variable=self.auto_login_var,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        buttons = ttk.Frame(form)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="Salvar", command=self._on_save).pack(side="right")

        self.grab_set()
        self.wait_window()

    def _on_save(self):
        label = self.label_var.get().strip()
        username = self.username_var.get().strip()

        if not label or not username or not self.password_var.get():
            messagebox.showwarning(
                "Campos obrigatorios",
                "Preencha ao menos apelido, usuario e senha.",
            )
            return

        self.result = Account(
            label=label,
            username=username,
            password=self.password_var.get(),
            server_name=self.server_var.get().strip(),
            character_slot=self.slot_var.get(),
            auto_login=self.auto_login_var.get(),
        )
        self.destroy()


# =====================================================
# Janela principal
# =====================================================

class MainWindow:
    """
    Interface grafica com duas abas:
      1. Gerenciar Contas  — cadastro, edicao e remocao de contas.
      2. Login             — checkboxes para logar, com relogging
                              automatico enquanto o checkbox estiver
                              marcado.

    Contas com auto_login=True tem o checkbox marcado automaticamente
    na abertura do bot.
    """

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("Talisman Online - Auto Login")
        self.root.geometry("720x660")
        self.root.minsize(620, 520)

        self.accounts: list[Account] = load_accounts()

        self._active_threads = 0
        self._active_lock = threading.Lock()

        # Controle de threads por conta
        self._stop_events: dict[str, threading.Event] = {}

        # Variaveis dos checkboxes na aba Login (label -> BooleanVar)
        self._login_vars: dict[str, tk.BooleanVar] = {}

        # Label -> indice na lista de contas (cache para lookup)
        self._account_index: dict[str, int] = {}

        self._client_path = tk.StringVar(value=_DEFAULTS.client_path)

        self.log_redirector = None  # criado depois que o widget de log existir

        self._build_client_path_row()
        self._build_notebook()
        self._build_log_area()

        self.log_redirector = MultiAccountLogRedirector(self.log_text, sys.stdout)

        self._load_saved_client_path()
        self._refresh_accounts_list()
        self._rebuild_login_tab()

        # Auto-login ao abrir
        self.root.after(500, self._auto_start_accounts)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # =====================================================
    # Layout: caminho do client (topo)
    # =====================================================

    def _build_client_path_row(self):
        frame = ttk.Frame(self.root, padding=(12, 12, 12, 6))
        frame.pack(fill="x")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Client (.exe/.bat):").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self._client_path).grid(
            row=0, column=1, sticky="ew", padx=(6, 6)
        )
        ttk.Button(frame, text="Procurar...", command=self._browse_client_path).grid(
            row=0, column=2
        )

    # =====================================================
    # Notebook (abas)
    # =====================================================

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(6, 0))

        # Aba 1: Gerenciar Contas
        self._manage_frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self._manage_frame, text="Gerenciar Contas")
        self._build_manage_tab()

        # Aba 2: Login
        self._login_frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self._login_frame, text="Login")

    # -----------------------------------------------------
    # Aba: Gerenciar Contas
    # -----------------------------------------------------

    def _build_manage_tab(self):
        self._manage_frame.columnconfigure(0, weight=1)
        self._manage_frame.rowconfigure(0, weight=1)

        # Lista de contas
        list_frame = ttk.Frame(self._manage_frame)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.accounts_listbox = tk.Listbox(
            list_frame,
            selectmode="extended",
            height=10,
            yscrollcommand=scrollbar.set,
        )
        self.accounts_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.accounts_listbox.yview)

        # Botoes
        btn_frame = ttk.Frame(self._manage_frame)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        ttk.Button(btn_frame, text="Adicionar", command=self._on_add_account).pack(side="left")
        ttk.Button(btn_frame, text="Editar", command=self._on_edit_account).pack(side="left", padx=(6, 0))
        ttk.Button(btn_frame, text="Remover", command=self._on_remove_account).pack(side="left", padx=(6, 0))

    # -----------------------------------------------------
    # Aba: Login
    # -----------------------------------------------------

    def _rebuild_login_tab(self):
        """Reconstroi o conteudo da aba de Login."""

        for widget in self._login_frame.winfo_children():
            widget.destroy()

        # Guarda o estado atual dos checkboxes antes de recriar
        old_checked: set[str] = set()
        old_vars = getattr(self, "_login_vars", {})
        for label, var in old_vars.items():
            if var.get():
                old_checked.add(label)

        self._login_vars.clear()
        self._account_index.clear()

        if not self.accounts:
            ttk.Label(
                self._login_frame,
                text="Nenhuma conta cadastrada.\nVa em 'Gerenciar Contas' para adicionar.",
                justify="center",
            ).pack(expand=True)
            return

        # Canvas + scrollbar para muitas contas
        canvas = tk.Canvas(self._login_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._login_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Vincula roda do mouse ao canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Cabecalho
        header = ttk.Frame(scroll_frame)
        header.pack(fill="x", pady=(0, 6))
        ttk.Label(header, text="Conta", font=("", 9, "bold"), width=16, anchor="w").pack(side="left")
        ttk.Label(header, text="Servidor", font=("", 9, "bold"), width=18, anchor="w").pack(side="left", padx=(8, 0))
        ttk.Label(header, text="Usuario", font=("", 9, "bold"), width=18, anchor="w").pack(side="left", padx=(8, 0))

        ttk.Separator(scroll_frame, orient="horizontal").pack(fill="x", pady=(0, 4))

        for idx, account in enumerate(self.accounts):
            self._account_index[account.label] = idx

            row = ttk.Frame(scroll_frame)
            row.pack(fill="x", pady=1)

            var = tk.BooleanVar(value=(account.label in old_checked))
            self._login_vars[account.label] = var

            cb = ttk.Checkbutton(
                row,
                variable=var,
                command=lambda label=account.label: self._on_checkbox_toggle(label),
            )
            cb.pack(side="left")

            ttk.Label(row, text=account.label, width=14, anchor="w").pack(side="left", padx=(2, 0))
            ttk.Label(row, text=account.server_name, width=16, anchor="w").pack(side="left", padx=(8, 0))
            ttk.Label(row, text=account.username, width=16, anchor="w").pack(side="left", padx=(8, 0))

    # =====================================================
    # Area de log (rodape)
    # =====================================================

    def _build_log_area(self):
        frame = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Log:").grid(row=0, column=0, sticky="w")

        text_frame = ttk.Frame(frame)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.log_text = tk.Text(
            text_frame,
            state="disabled",
            wrap="word",
            yscrollcommand=scrollbar.set,
            height=10,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.log_text.yview)

    # =====================================================
    # Persistencia
    # =====================================================

    def _load_saved_client_path(self):
        if not GUI_SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(GUI_SETTINGS_FILE.read_text(encoding="utf-8"))
            self._client_path.set(data.get("client_path", _DEFAULTS.client_path))
        except Exception:
            pass

    def _save_client_path(self):
        data = {"client_path": self._client_path.get()}
        try:
            GUI_SETTINGS_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[GUI] Aviso: nao foi possivel salvar as configuracoes ({e})")

    def _refresh_accounts_list(self):
        self.accounts_listbox.delete(0, "end")
        for account in self.accounts:
            auto = " [auto-login]" if account.auto_login else ""
            self.accounts_listbox.insert(
                "end",
                f"{account.label}  —  usuario: {account.username}  "
                f"—  servidor: {account.server_name}  —  slot: {account.character_slot}{auto}",
            )

    def _on_close(self):
        self._save_client_path()
        # Para todas as threads ativas
        for stop_event in list(self._stop_events.values()):
            stop_event.set()
        self.root.destroy()

    # =====================================================
    # Gerenciamento de contas (Aba Gerenciar)
    # =====================================================

    def _browse_client_path(self):
        path = filedialog.askopenfilename(
            title="Selecione o executavel/launcher do client",
            filetypes=[
                ("Executaveis", "*.exe;*.bat;*.cmd"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if path:
            self._client_path.set(path)

    def _on_add_account(self):
        dialog = AccountDialog(self.root, "Adicionar conta")
        if dialog.result:
            self.accounts.append(dialog.result)
            save_accounts(self.accounts)
            self._refresh_accounts_list()
            self._rebuild_login_tab()

    def _on_edit_account(self):
        index = self._get_single_selected_index()
        if index is None:
            return

        old_label = self.accounts[index].label

        dialog = AccountDialog(self.root, "Editar conta", self.accounts[index])
        if dialog.result:
            # Se o apelido mudou, para a thread antiga e atualiza
            new_label = dialog.result.label
            if new_label != old_label:
                self._stop_login_thread(old_label)

            self.accounts[index] = dialog.result
            save_accounts(self.accounts)
            self._refresh_accounts_list()
            self._rebuild_login_tab()

            # Se o novo apelido tinha auto_login ativo e estava
            # rodando antes, reinicia a thread com o novo apelido
            if dialog.result.auto_login:
                self._start_login_thread(new_label)

    def _on_remove_account(self):
        index = self._get_single_selected_index()
        if index is None:
            return

        account = self.accounts[index]
        if not messagebox.askyesno("Remover conta", f"Remover a conta '{account.label}'?"):
            return

        # Para a thread se estiver rodando
        self._stop_login_thread(account.label)

        del self.accounts[index]
        save_accounts(self.accounts)
        self._refresh_accounts_list()
        self._rebuild_login_tab()

    def _get_single_selected_index(self) -> int | None:
        selection = self.accounts_listbox.curselection()
        if not selection:
            messagebox.showinfo("Nenhuma conta selecionada", "Selecione uma conta na lista.")
            return None
        if len(selection) > 1:
            messagebox.showinfo("Selecione apenas uma", "Essa acao funciona com uma conta por vez.")
            return None
        return selection[0]

    # =====================================================
    # Controle de login por checkbox (Aba Login)
    # =====================================================

    def _on_checkbox_toggle(self, label: str):
        """Callback quando o usuario marca/desmarca um checkbox."""
        var = self._login_vars.get(label)
        if var is None:
            return
        if var.get():
            self._start_login_thread(label)
        else:
            self._stop_login_thread(label)

    def _start_login_thread(self, label: str):
        """Inicia a thread de login + relogging para a conta."""

        if label not in self._account_index:
            return

        # Se ja existe uma thread rodando para esse label, nao inicia outra
        if label in self._stop_events and not self._stop_events[label].is_set():
            return

        client_path = self._client_path.get().strip()
        if not client_path:
            messagebox.showwarning(
                "Client nao informado",
                "Informe o caminho do client antes de logar.",
            )
            # Desmarca o checkbox
            var = self._login_vars.get(label)
            if var:
                self.root.after(0, lambda: var.set(False))
            return

        self._save_client_path()

        with self._active_lock:
            if self._active_threads == 0:
                self._clear_log()
                sys.stdout = self.log_redirector
            self._active_threads += 1

        stop_event = threading.Event()
        self._stop_events[label] = stop_event

        idx = self._account_index[label]
        account = self.accounts[idx]

        thread = threading.Thread(
            target=self._run_account_loop,
            args=(account, client_path, stop_event),
            daemon=True,
        )
        thread.start()

    def _stop_login_thread(self, label: str):
        """Para a thread de login da conta (desmarca checkbox)."""
        stop_event = self._stop_events.pop(label, None)
        if stop_event:
            stop_event.set()

    # =====================================================
    # Loop principal de login + relogging (roda na thread)
    # =====================================================

    def _run_account_loop(self, account: Account, client_path: str, stop_event: threading.Event):
        """Loop que faz login e monitora a janela. Se a janela fechar
        e o stop_event nao estiver ativo, refaz o login."""

        self.log_redirector.register(account.label)

        try:
            while not stop_event.is_set():
                app = None
                try:
                    settings = replace(
                        Settings(),
                        username=account.username,
                        password=account.password,
                        server_name=account.server_name,
                        character_slot=account.character_slot,
                        client_path=client_path,
                        account_label=account.label,
                    )

                    app = Application(settings=settings)
                    app.start()

                    hwnd = app.container.session.hwnd
                    if hwnd is None:
                        raise RuntimeError("Login concluido mas sem handle de janela.")

                    print(f"[{account.label}] Login concluido com sucesso!")

                    # Entra no modo de monitoramento
                    self._monitor_game_window(hwnd, account.label, stop_event)

                except Exception as e:
                    print(f"[{account.label}] Erro: {e}")
                    if stop_event.wait(5.0):
                        break
                finally:
                    if app:
                        try:
                            app.shutdown()
                        except Exception:
                            pass

        finally:
            self.log_redirector.unregister()
            self._on_account_finished(account.label)

    def _monitor_game_window(self, hwnd: int, label: str, stop_event: threading.Event):
        """Monitora a janela do jogo. Retorna quando a janela fechar
        ou o stop_event for ativado."""

        print(f"[{label}] Monitorando janela (hwnd={hwnd})...")

        while not stop_event.is_set():
            if not win32gui.IsWindow(hwnd):
                print(f"[{label}] Janela fechada. Reiniciando login...")
                return
            time.sleep(2.0)

    def _on_account_finished(self, label: str):
        """Chamado quando a thread de uma conta termina (stop_event
        ativado ou loop encerrado por outro motivo)."""

        # Desmarca o checkbox na interface
        def _uncheck():
            var = self._login_vars.get(label)
            if var:
                var.set(False)

        self.root.after(0, _uncheck)

        with self._active_lock:
            self._active_threads -= 1
            remaining = self._active_threads

        if remaining <= 0:
            self.root.after(0, self._on_all_finished)

    def _on_all_finished(self):
        """Todas as threads pararam."""
        sys.stdout = self.log_redirector.original

    # =====================================================
    # Auto-login na abertura do bot
    # =====================================================

    def _auto_start_accounts(self):
        """Marca os checkboxes das contas com auto_login=True e
        dispara as threads de login."""

        for account in self.accounts:
            if account.auto_login:
                var = self._login_vars.get(account.label)
                if var is not None:
                    var.set(True)
                    self._start_login_thread(account.label)

    # =====================================================
    # Log
    # =====================================================

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # =====================================================
    # Execucao
    # =====================================================

    def run(self):
        self.root.mainloop()
