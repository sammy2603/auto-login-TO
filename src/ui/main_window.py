from __future__ import annotations

import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import config
from src.app.application import Application
from src.config.settings import Settings
from src.shared.character_slots import CharacterSlot

# Arquivo onde a interface lembra os últimos valores digitados (fica
# na raiz do projeto, ao lado do config.py). Mesmo nível de sensibilidade
# do .env -- fica em texto puro no disco, mesma observação de sempre.
SETTINGS_FILE = Path(__file__).resolve().parents[2] / "gui_settings.json"


class TextRedirector:
    """
    Redireciona qualquer print() feito durante a automação (pelos
    workflows, engine, etc) pra dentro da caixa de log da interface,
    em vez do terminal. Repassa a escrita pra thread principal do
    Tkinter via .after(), porque widgets Tkinter não são thread-safe.
    """

    def __init__(self, widget: tk.Text):
        self.widget = widget

    def write(self, text: str):
        self.widget.after(0, self._append, text)

    def _append(self, text: str):
        self.widget.configure(state="normal")
        self.widget.insert("end", text)
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        pass


class MainWindow:
    """
    Janela principal: formulário com conta/servidor/personagem/caminho
    do client, botão pra iniciar o login automático, e uma área de log
    mostrando o progresso em tempo real.

    Roda a automação numa thread separada pra não travar a interface
    enquanto o bot espera telas carregarem (às vezes por minutos, no
    caso de fila de servidor).
    """

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("Talisman Online - Auto Login")
        self.root.geometry("560x480")
        self.root.resizable(False, False)

        self._build_form()
        self._build_log_area()
        self._load_saved_values()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # =====================================================
    # Construção da interface
    # =====================================================

    def _build_form(self):

        form = ttk.Frame(self.root, padding=12)
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.server_var = tk.StringVar()
        self.slot_var = tk.StringVar()
        self.client_path_var = tk.StringVar()

        row = 0

        ttk.Label(form, text="Usuário:").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.username_var).grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
        row += 1

        ttk.Label(form, text="Senha:").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.password_var, show="*").grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
        row += 1

        ttk.Label(form, text="Servidor:").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.server_var).grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
        row += 1

        ttk.Label(form, text="Personagem:").grid(row=row, column=0, sticky="w", pady=4)
        slot_combo = ttk.Combobox(
            form,
            textvariable=self.slot_var,
            values=[CharacterSlot.LEFT, CharacterSlot.CENTER, CharacterSlot.RIGHT],
            state="readonly",
        )
        slot_combo.grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
        row += 1

        ttk.Label(form, text="Client (.exe/.bat):").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.client_path_var).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(form, text="Procurar...", command=self._browse_client_path).grid(row=row, column=2, padx=(6, 0), pady=4)
        row += 1

        self.start_button = ttk.Button(form, text="Iniciar Login", command=self._on_start_clicked)
        self.start_button.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(12, 0))

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
    # Persistência simples (lembrar os últimos valores)
    # =====================================================

    def _load_saved_values(self):

        saved = {}

        if SETTINGS_FILE.exists():
            try:
                saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                saved = {}

        self.username_var.set(saved.get("username", config.USERNAME))
        self.password_var.set(saved.get("password", config.PASSWORD))
        self.server_var.set(saved.get("server_name", config.SERVER_NAME))
        self.slot_var.set(saved.get("character_slot", config.CHARACTER_SLOT))
        self.client_path_var.set(saved.get("client_path", config.CLIENT_PATH))

    def _save_values(self):

        data = {
            "username": self.username_var.get(),
            "password": self.password_var.get(),
            "server_name": self.server_var.get(),
            "character_slot": self.slot_var.get(),
            "client_path": self.client_path_var.get(),
        }

        try:
            SETTINGS_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[UI] Aviso: não foi possível salvar as configurações ({e})")

    def _on_close(self):
        self._save_values()
        self.root.destroy()

    # =====================================================
    # Ações
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

    def _on_start_clicked(self):

        if not self.username_var.get() or not self.password_var.get():
            messagebox.showwarning(
                "Campos obrigatórios",
                "Preencha usuário e senha antes de iniciar.",
            )
            return

        self._save_values()

        self._clear_log()

        self.start_button.configure(state="disabled", text="Rodando...")

        settings = Settings(
            client_path=self.client_path_var.get(),
            username=self.username_var.get(),
            password=self.password_var.get(),
            server_name=self.server_var.get(),
            character_slot=self.slot_var.get(),
        )

        thread = threading.Thread(
            target=self._run_automation,
            args=(settings,),
            daemon=True,
        )
        thread.start()

    def _run_automation(self, settings: Settings):

        original_stdout = sys.stdout
        sys.stdout = TextRedirector(self.log_text)

        success = True
        error_message = ""

        try:
            app = Application(settings=settings)
            try:
                app.start()
            finally:
                app.shutdown()

        except Exception as e:
            success = False
            error_message = str(e)

        finally:
            sys.stdout = original_stdout

        self.root.after(0, self._on_automation_finished, success, error_message)

    def _on_automation_finished(self, success: bool, error_message: str):

        self.start_button.configure(state="normal", text="Iniciar Login")

        if success:
            messagebox.showinfo("Concluído", "Login realizado com sucesso!")
        else:
            messagebox.showerror("Erro", f"A automação falhou:\n\n{error_message}")

    def _clear_log(self):

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # =====================================================
    # Execução
    # =====================================================

    def run(self):

        self.root.mainloop()