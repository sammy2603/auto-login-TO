from __future__ import annotations

import json
import sys
import threading
import time
import tkinter as tk
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import win32gui

from src.app.application import Application
from src.config.settings import Settings
from src.services.license.service import LicenseService
from src.services.game.game_reader import GameReader
from src.services.game.memory_reader import MemoryReader
from src.services.bot.bot_engine import BotEngine
from src.services.bot.scripts.attack import AttackScript
from src.services.bot.scripts.potion import PotionScript
from src.services.bot.scripts.pet_food import PetFoodScript
from src.services.bot.scripts.buff import BuffScript
from src.services.bot.scripts.helper import HelperScript
from src.services.bot.scripts.fairy import FairyScript
from src.services.bot.scripts.revive import ReviveScript
from src.services.bot.scripts.delete import DeleteScript
from src.services.bot.scripts.bc import BCScript
from src.services.bot.scripts.hollow import HollowScript
from src.services.bot.scripts.sell import SellScript
from src.services.bot.scripts.dr_lure import DRLureScript
from src.shared.character_slots import CharacterSlot
from src.ui.session_registry import SessionRegistry
from src.ui.widgets.sidebar import Sidebar
from src.ui.widgets.right_panel import RightPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

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
        return [
            Account(**{**item, "auto_login": item.get("auto_login", False)})
            for item in data
        ]
    except Exception:
        return []


def save_accounts(accounts: list[Account]):
    data = [asdict(a) for a in accounts]
    try:
        ACCOUNTS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        print(f"[GUI] Aviso: nao foi possivel salvar as contas ({e})")


# =====================================================
# Log redirector
# =====================================================

class MultiAccountLogRedirector:

    def __init__(self, widgets: list, original):
        self.widgets = widgets
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
            lines = []
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                lines.append(line)
            self._buffers[ident] = buf
        for line in lines:
            prefixed = f"[{label}] {line}" if label else line
            for widget in self.widgets:
                widget.after(0, self._append, widget, prefixed + "\n")

    def _append(self, widget, text: str):
        widget.configure(state="normal")
        widget.insert("end", text)
        widget.yview_moveto(1.0)
        widget.configure(state="disabled")

    def flush(self):
        self.original.flush()


# =====================================================
# Dialogo de conta
# =====================================================

class AccountDialog(ctk.CTkToplevel):

    def __init__(self, parent, title: str, account: Account | None = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)

        # Centraliza no pai
        parent.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        self.geometry(f"350x400+{px + (pw - 350) // 2}+{py + (ph - 400) // 2}")
        self.result: Account | None = None

        self.label_var = tk.StringVar(value=account.label if account else "")
        self.username_var = tk.StringVar(value=account.username if account else "")
        self.password_var = tk.StringVar(value=account.password if account else "")
        self.server_var = tk.StringVar(value=account.server_name if account else _DEFAULTS.server_name)
        self.slot_var = tk.StringVar(value=account.character_slot if account else CharacterSlot.CENTER)
        self.auto_login_var = ctk.BooleanVar(value=account.auto_login if account else False)

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(form, text="Apelido:").grid(row=0, column=0, sticky="w", pady=4)
        ctk.CTkEntry(form, textvariable=self.label_var, width=260).grid(row=0, column=1, pady=4, padx=(8, 0))

        ctk.CTkLabel(form, text="Usuario:").grid(row=1, column=0, sticky="w", pady=4)
        ctk.CTkEntry(form, textvariable=self.username_var, width=260).grid(row=1, column=1, pady=4, padx=(8, 0))

        ctk.CTkLabel(form, text="Senha:").grid(row=2, column=0, sticky="w", pady=4)
        ctk.CTkEntry(form, textvariable=self.password_var, show="*", width=260).grid(row=2, column=1, pady=4, padx=(8, 0))

        ctk.CTkLabel(form, text="Servidor:").grid(row=3, column=0, sticky="w", pady=4)
        ctk.CTkEntry(form, textvariable=self.server_var, width=260).grid(row=3, column=1, pady=4, padx=(8, 0))

        ctk.CTkLabel(form, text="Personagem:").grid(row=4, column=0, sticky="w", pady=4)
        ctk.CTkComboBox(
            form, values=[CharacterSlot.LEFT, CharacterSlot.CENTER, CharacterSlot.RIGHT],
            variable=self.slot_var, width=260, state="readonly",
        ).grid(row=4, column=1, pady=4, padx=(8, 0))

        ctk.CTkCheckBox(
            form, text="Auto-login ao abrir o Bot", variable=self.auto_login_var,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        btns = ctk.CTkFrame(form, fg_color="transparent")
        btns.grid(row=6, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ctk.CTkButton(btns, text="Salvar", command=self._on_save).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btns, text="Cancelar", fg_color="transparent", border_width=1, command=self.destroy).pack(side="right")

        self.grab_set()
        self.wait_window()

    def _on_save(self):
        label = self.label_var.get().strip()
        username = self.username_var.get().strip()
        if not label or not username or not self.password_var.get():
            messagebox.showwarning("Campos obrigatorios", "Preencha ao menos apelido, usuario e senha.")
            return
        self.result = Account(
            label=label, username=username, password=self.password_var.get(),
            server_name=self.server_var.get().strip(), character_slot=self.slot_var.get(),
            auto_login=self.auto_login_var.get(),
        )
        self.destroy()


# =====================================================
# Janela de Login (contas)
# =====================================================

class LoginWindow(ctk.CTkToplevel):

    def __init__(self, controller):
        super().__init__(controller.root)
        self.controller = controller
        self.title("Login — Contas")
        self.resizable(True, True)
        self.minsize(420, 350)
        self.transient(controller.root)
        controller._center_on_parent(self, 520, 480)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Tabela de contas
        self._table = ctk.CTkScrollableFrame(self)
        self._table.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 4))

        # Botoes
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 12))
        ctk.CTkButton(btns, text="Adicionar Conta", command=self._on_add).pack(side="left")

        self._refresh_table()

    def _refresh_table(self):
        for w in self._table.winfo_children():
            w.destroy()

        accounts = self.controller.accounts
        if not accounts:
            ctk.CTkLabel(
                self._table,
                text="Nenhuma conta cadastrada.\nClique em 'Adicionar Conta'.",
            ).pack(expand=True, pady=30)
            return

        hdr = ctk.CTkFrame(self._table, fg_color="transparent")
        hdr.pack(fill="x", pady=(4, 4))
        ctk.CTkLabel(hdr, text="Conta", font=ctk.CTkFont(weight="bold"), width=100, anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="Servidor", font=ctk.CTkFont(weight="bold"), width=120, anchor="w").pack(side="left", padx=(8, 0))
        ctk.CTkLabel(hdr, text="Usuario", font=ctk.CTkFont(weight="bold"), width=120, anchor="w").pack(side="left", padx=(8, 0))

        ctk.CTkFrame(self._table, height=1, fg_color="#444444").pack(fill="x", pady=(0, 4))

        for idx, account in enumerate(accounts):
            self.controller._account_index[account.label] = idx
            if account.label not in self.controller._login_vars:
                self.controller._login_vars[account.label] = ctk.BooleanVar(value=False)

            row = ctk.CTkFrame(self._table, fg_color="transparent")
            row.pack(fill="x", pady=1)

            var = self.controller._login_vars[account.label]
            ctk.CTkCheckBox(
                row, text="", variable=var, width=20,
                command=lambda label=account.label: self.controller._on_checkbox_toggle(label),
            ).pack(side="left")

            ctk.CTkLabel(row, text=account.label, width=100, anchor="w").pack(side="left", padx=(4, 0))
            ctk.CTkLabel(row, text=account.server_name, width=120, anchor="w").pack(side="left", padx=(8, 0))
            ctk.CTkLabel(row, text=account.username, width=120, anchor="w").pack(side="left", padx=(8, 0))

            ctk.CTkButton(
                row, text="E", width=28, height=24,
                command=lambda a=account: self._on_edit(a),
                fg_color="transparent", border_width=1,
            ).pack(side="right", padx=(4, 2))
            ctk.CTkButton(
                row, text="X", width=28, height=24,
                command=lambda a=account: self._on_remove(a),
                fg_color="transparent", border_width=1, text_color="#cc4444",
            ).pack(side="right")

    def _on_add(self):
        self.controller._on_add_account()
        self._refresh_table()

    def _on_edit(self, account: Account):
        self.controller._on_edit_inline(account)
        self._refresh_table()

    def _on_remove(self, account: Account):
        self.controller._on_remove_inline(account)
        self._refresh_table()

    def _on_close(self):
        self.controller._login_window = None
        self.destroy()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self._refresh_table()


# =====================================================
# Janela de Configuracao
# =====================================================

class ConfigWindow(ctk.CTkToplevel):

    def __init__(self, controller):
        super().__init__(controller.root)
        self.controller = controller
        self.title("Configuracoes")
        self.resizable(False, False)
        self.transient(controller.root)
        controller._center_on_parent(self, 500, 200)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()

    def _build(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text="Configuracoes", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 12))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text="Client (.bat/.exe):").pack(side="left")
        ctk.CTkEntry(row, textvariable=self.controller._client_path, width=280).pack(side="left", padx=(8, 4))
        ctk.CTkButton(row, text="Procurar", width=80, command=self.controller._browse_client_path).pack(side="left")

        ctk.CTkLabel(
            frame,
            text="Demais configuracoes ficam em config.py e .env",
            text_color="#888888",
        ).pack(anchor="w", pady=(12, 0))

        ctk.CTkButton(
            frame, text="Fechar", command=self._on_close,
            fg_color="transparent", border_width=1,
        ).pack(pady=(16, 0))

    def _on_close(self):
        self.controller._config_window = None
        self.controller._save_client_path()
        self.destroy()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()


# =====================================================
# Janela de Licenca (Key)
# =====================================================

class KeyWindow(ctk.CTkToplevel):

    def __init__(self, controller):
        super().__init__(controller.root)
        self.controller = controller
        self.title("Licenca")
        self.resizable(False, False)
        self.transient(controller.root)
        controller._center_on_parent(self, 440, 360)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self)
        f.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(f, text="Licenciamento", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 16))

        kr = ctk.CTkFrame(f, fg_color="transparent"); kr.pack(fill="x", pady=4)
        self._key_var = tk.StringVar()
        ctk.CTkEntry(kr, textvariable=self._key_var, width=220, placeholder_text="TO-AAAAMMDD-HASH").pack(side="left", padx=(0, 8))
        ctk.CTkButton(kr, text="Validar", command=self._on_validate).pack(side="left")

        ctk.CTkButton(
            f, text="Usar modo Demo (30 dias gratuitos)",
            command=self._on_demo, fg_color="transparent", border_width=1,
        ).pack(pady=(16, 20))

        self._status_frame = ctk.CTkFrame(f); self._status_frame.pack(fill="x")
        self._status_text = ctk.CTkLabel(self._status_frame, text="", font=ctk.CTkFont(size=12))
        self._status_text.pack(anchor="w", padx=12, pady=12)

        ctk.CTkFrame(f, height=1, fg_color="#444444").pack(fill="x", pady=(16, 4))
        ctk.CTkLabel(f, text="Adquira: contato@loginto.app", text_color="#888888").pack()

        ctk.CTkButton(
            f, text="Fechar", command=self._on_close,
            fg_color="transparent", border_width=1,
        ).pack(pady=(12, 0))

        self._refresh()

    def _refresh(self):
        ctrl = self.controller
        ctrl._license.check(); info = ctrl._license.info
        color = {"demo": "#aaaa00", "active": "#00aa00", "expired": "#aa0000"}.get(info.status, "#888888")
        status = {"demo": "Demonstracao", "active": "Ativa", "expired": "Expirada"}.get(info.status, info.status)
        self._status_text.configure(
            text=f"Status: {status}\nDias restantes: {info.days_remaining}\nTipo: {info.tier.capitalize()}\nChave: {info.key or '---'}",
            text_color=color,
        )

    def _on_validate(self):
        key = self._key_var.get().strip()
        if not key:
            messagebox.showwarning("Chave vazia", "Insira uma chave."); return
        ok, msg = self.controller._license.activate(key)
        (messagebox.showinfo if ok else messagebox.showerror)("Licenca", msg)
        self._key_var.set("")
        self._refresh()
        self.controller._refresh_license_status()

    def _on_demo(self):
        self.controller._license.activate("DEMO")
        self._refresh()
        self.controller._refresh_license_status()

    def _on_close(self):
        self.controller._key_window = None
        self.destroy()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self._refresh()


# =====================================================
# Janela principal
# =====================================================

class MainWindow:

    FEATURES = [
        "Attack", "Potion", "Pet Food", "Buff",
        "Helper", "Fairy", "Revive", "Delete",
        "BC", "Hollow", "Sell", "DR Lure",
    ]

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Talisman Online - Auto Login")
        self.root.geometry("900x640")
        self.root.resizable(False, False)

        # Grid do root: topo (0) | main (1) | status (2)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        self.accounts: list[Account] = load_accounts()
        self._active_threads = 0
        self._active_lock = threading.Lock()
        self._stop_events: dict[str, threading.Event] = {}
        self._login_vars: dict[str, ctk.BooleanVar] = {}
        self._account_index: dict[str, int] = {}
        self._client_path = tk.StringVar(value=_DEFAULTS.client_path)
        self._license = LicenseService()

        self._selected_window: str | None = None
        self._feature_vars: dict[str, dict[str, ctk.BooleanVar]] = {}
        self._widget_states: dict[str, bool] = {}
        self._game_reader = GameReader()

        self._login_window: LoginWindow | None = None
        self._config_window: ConfigWindow | None = None
        self._key_window: KeyWindow | None = None

        self._build_top_bar()
        self._build_main_area()
        self._build_status_bar()

        self.log_redirector = MultiAccountLogRedirector(
            [self._log_tab_text], sys.stdout
        )

        self._load_saved_client_path()

        self.root.after(500, self._auto_start_accounts)
        self.root.after(1000, self._scan_for_game_windows)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # =====================================================
    # Top bar
    # =====================================================

    def _build_top_bar(self):
        top = ctk.CTkFrame(self.root, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))

        for label in ("List", "Config", "Login", "Pricing", "Help"):
            ctk.CTkButton(
                top, text=label,
                command=lambda l=label: self._on_top_bar(l),
                fg_color="transparent", hover_color="#3a3a3a",
                width=60, height=28,
            ).pack(side="left", padx=2)

        ctk.CTkFrame(top, height=1, fg_color="#444444").pack(fill="x", pady=(4, 0))

    def _on_top_bar(self, label: str):
        if label == "Login":
            self._open_login_window()
        elif label == "Config":
            self._open_config_window()
        elif label == "Help":
            self._show_help_dialog()
        elif label == "Pricing":
            self._show_pricing_dialog()
        elif label == "List":
            messagebox.showinfo("List", "Ordenacao de janelas em breve.")

    def _open_login_window(self):
        if self._login_window is None:
            self._login_window = LoginWindow(self)
        else:
            self._login_window.show()

    def _open_config_window(self):
        if self._config_window is None:
            self._config_window = ConfigWindow(self)
        else:
            self._config_window.show()

    # =====================================================
    # Pricing / Help dialogs
    # =====================================================

    def _center_on_parent(self, child, width: int, height: int):
        """Centraliza uma janela filha em relacao a janela principal."""
        self.root.update_idletasks()
        px = self.root.winfo_x()
        py = self.root.winfo_y()
        pw = self.root.winfo_width()
        ph = self.root.winfo_height()
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
        child.geometry(f"{width}x{height}+{x}+{y}")

    def _show_pricing_dialog(self):
        d = ctk.CTkToplevel(self.root)
        d.title("Pricing"); d.resizable(False, False); d.transient(self.root)
        self._center_on_parent(d, 380, 340)
        f = ctk.CTkFrame(d); f.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(f, text="Planos", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 16))
        free = ctk.CTkFrame(f); free.pack(fill="x", pady=4)
        ctk.CTkLabel(free, text="Gratuito", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))
        for t in ["Login automatico", "Configuracoes basicas", "1 conta simultanea"]:
            ctk.CTkLabel(free, text=f"  - {t}", text_color="#aaaaaa").pack(anchor="w", padx=12)
        prem = ctk.CTkFrame(f); prem.pack(fill="x", pady=4)
        ctk.CTkLabel(prem, text="Premium", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))
        for t in ["Multiplas contas", "Todos os scripts", "Perfis personalizados", "Atualizacoes prioritarias", "Suporte dedicado"]:
            ctk.CTkLabel(prem, text=f"  - {t}", text_color="#aaaaaa").pack(anchor="w", padx=12)
        ctk.CTkLabel(f, text="Contato: contato@loginto.app", text_color="#888888").pack(pady=(16, 0))
        ctk.CTkButton(f, text="Fechar", command=d.destroy).pack(pady=(12, 0))
        d.grab_set(); d.wait_window()

    def _show_help_dialog(self):
        d = ctk.CTkToplevel(self.root)
        d.title("Help / Sobre"); d.resizable(False, False); d.transient(self.root)
        self._center_on_parent(d, 340, 260)
        f = ctk.CTkFrame(d); f.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(f, text="Auto Login TO", font=ctk.CTkFont(size=16, weight="bold")).pack()
        ctk.CTkLabel(f, text="Versao 0.2.0", text_color="#888888").pack(pady=(2, 12))
        ctk.CTkLabel(f, text="Automatizacao de login para Talisman Online").pack()
        ctk.CTkFrame(f, height=1, fg_color="#444444").pack(fill="x", pady=12)
        ctk.CTkButton(f, text="Verificar Atualizacao", command=self._check_for_updates).pack(pady=(0, 8))
        ctk.CTkButton(f, text="Fechar", command=d.destroy, fg_color="transparent", border_width=1).pack()
        d.grab_set(); d.wait_window()

    def _check_for_updates(self):
        try:
            import urllib.request
            url = "https://api.github.com/repos/anomalyco/opencode/releases/latest"
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("User-Agent", "LoginTO-UpdateChecker")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                latest = data.get("tag_name", "")
            messagebox.showinfo("Atualizacao", f"Ultima: {latest}\nAtual: 0.2.0" if latest else "Nao foi possivel verificar.")
        except Exception as e:
            messagebox.showinfo("Atualizacao", f"Erro: {e}")

    # =====================================================
    # Area principal (3 colunas)
    # =====================================================

    def _build_main_area(self):
        mf = ctk.CTkFrame(self.root, fg_color="transparent")
        mf.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        mf.grid_columnconfigure(1, weight=1)
        mf.grid_rowconfigure(0, weight=1)

        # Centro — notebook (criado primeiro, sidebar depende dele)
        self.center_frame = ctk.CTkFrame(mf, fg_color="transparent")
        self.center_frame.grid(row=0, column=1, sticky="nsew")

        self.tabview = ctk.CTkTabview(self.center_frame)
        self.tabview.pack(fill="both", expand=True)
        self.tabview.add("Dashboard")
        self.tabview.add("Log")

        self._dashboard_frame = self.tabview.tab("Dashboard")
        self._log_tab_frame = self.tabview.tab("Log")

        self._build_dashboard_content()
        self._build_log_tab()

        self.tabview.set("Dashboard")

        # Sidebar (criado depois do notebook estar pronto)
        sf = ctk.CTkFrame(mf, fg_color="transparent", width=80)
        sf.grid(row=0, column=0, sticky="ns", padx=(0, 4))
        sf.grid_propagate(False)
        self.sidebar = Sidebar(sf, on_select=self._on_sidebar_select)
        self.sidebar.pack(fill="both", expand=True)

        # Right panel
        rf = ctk.CTkFrame(mf, width=190)
        rf.grid(row=0, column=2, sticky="ns", padx=(4, 0))
        rf.grid_propagate(False)
        self.right_panel = RightPanel(
            rf, on_select=self._on_right_panel_select,
            on_action=self._on_right_panel_action,
        )
        self.right_panel.pack(fill="both", expand=True)

    def _on_sidebar_select(self, label: str):
        if label == "Key":
            self._open_key_window()
        elif label == "Config":
            self._open_config_window()
        elif label == "Home":
            self.tabview.set("Dashboard")
            self._clear_feature_config()
        else:
            self.tabview.set("Dashboard")
            self._highlight_feature(label)

    # =====================================================
    # Dashboard
    # =====================================================

    def _build_dashboard_content(self):
        self._dashboard_frame.grid_columnconfigure(0, weight=1)
        self._dashboard_frame.grid_rowconfigure(0, weight=0)  # Char
        self._dashboard_frame.grid_rowconfigure(1, weight=0)  # Target
        self._dashboard_frame.grid_rowconfigure(2, weight=1)  # Config (expande)
        self._dashboard_frame.grid_rowconfigure(3, weight=0)  # Status

        # Char Info
        cf = ctk.CTkFrame(self._dashboard_frame)
        cf.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkLabel(cf, text="Char Info", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(6, 4))

        for name, bar_attr, lbl_attr in [
            ("HP:", "_char_hp_bar", "_char_hp_label"),
            ("Recurso:", "_char_res_bar", "_char_res_label"),
        ]:
            r = ctk.CTkFrame(cf, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(r, text=name, width=60, anchor="w").pack(side="left")
            bar = ctk.CTkProgressBar(r, width=180); bar.pack(side="left", padx=(8, 8)); bar.set(0)
            lbl = ctk.CTkLabel(r, text="---", width=60); lbl.pack(side="left")
            setattr(self, bar_attr, bar)
            setattr(self, lbl_attr, lbl)

        # Target Info
        tf = ctk.CTkFrame(self._dashboard_frame)
        tf.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(tf, text="Target Info", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(6, 4))

        r = ctk.CTkFrame(tf, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text="HP:", width=60, anchor="w").pack(side="left")
        self._target_hp_bar = ctk.CTkProgressBar(r, width=180); self._target_hp_bar.pack(side="left", padx=(8, 8)); self._target_hp_bar.set(0)
        self._target_hp_label = ctk.CTkLabel(r, text="---", width=60); self._target_hp_label.pack(side="left")

        r2 = ctk.CTkFrame(tf, fg_color="transparent"); r2.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r2, text="Nome:", width=60, anchor="w").pack(side="left")
        self._target_name_label = ctk.CTkLabel(r2, text="---"); self._target_name_label.pack(side="left", padx=(8, 0))

        # Feature Config (parte inferior, expande)
        self._feature_config_frame = ctk.CTkFrame(self._dashboard_frame)
        self._feature_config_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        self._feature_config_inner = ctk.CTkFrame(
            self._feature_config_frame, fg_color="transparent",
        )
        self._feature_config_inner.pack(fill="both", expand=True, padx=4, pady=4)
        ctk.CTkLabel(
            self._feature_config_inner,
            text="Selecione uma funcao na sidebar para configurar.",
            text_color="#888888",
        ).pack(expand=True)

        # Status
        self._dashboard_status = ctk.CTkLabel(
            self._dashboard_frame,
            text="Selecione um character no painel direito.",
            text_color="#888888",
        )
        self._dashboard_status.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 4))

    def _ensure_window_state(self, label: str):
        if label not in self._feature_vars:
            self._feature_vars[label] = {f: ctk.BooleanVar(value=False) for f in self.FEATURES}
            self._widget_states[label] = False

    def _on_right_panel_select(self, label: str):
        self._selected_window = label
        self._ensure_window_state(label)
        self._refresh_dashboard()
        self._start_dashboard_poll()

    def _on_right_panel_action(self, label: str):
        running = self.right_panel.running
        self._widget_states[label] = running
        if running:
            self._start_bot_for_window(label)
        else:
            self._stop_bot_for_window(label)
        self._refresh_dashboard()

    def _refresh_dashboard(self):
        label = self._selected_window
        if label is None or label not in self._feature_vars:
            self._dashboard_status.configure(text="Selecione um character no painel direito.")
            self._char_hp_bar.set(0); self._char_hp_label.configure(text="---")
            self._char_res_bar.set(0); self._char_res_label.configure(text="---")
            self._target_hp_bar.set(0); self._target_hp_label.configure(text="---")
            self._target_name_label.configure(text="---")
            return
        running = self._widget_states.get(label, False)
        sessions = SessionRegistry.get_all()
        display = sessions.get(label, {}).get("display", label)
        self._dashboard_status.configure(text=f"{display}  |  {'ATIVO' if running else 'PARADO'}")

    def _clear_feature_config(self):
        """Limpa o painel de config voltando ao placeholder."""
        for w in self._feature_config_inner.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self._feature_config_inner,
            text="Selecione uma funcao na sidebar para configurar.",
            text_color="#888888",
        ).pack(expand=True)

    def _highlight_feature(self, feature: str):
        """Mostra a configuracao da feature no Dashboard."""
        for w in self._feature_config_inner.winfo_children():
            w.destroy()

        method = getattr(
            self, f"_show_{feature.lower().replace(' ', '_')}_config", None
        )
        if method:
            method()
        else:
            ctk.CTkLabel(
                self._feature_config_inner,
                text=f"Configuracao de '{feature}' em breve.",
                text_color="#888888",
            ).pack(pady=12)

    # =====================================================
    # Feature Configs
    # =====================================================

    def _show_attack_config(self):
        """Configuracao de Attack: 5 slots de skill + velocidade."""
        if not hasattr(self, "_attack_config"):
            self._attack_config = {
                "keys": ["1", "2", "3", "4", "5"],
                "speed": 150,
            }
        cfg = self._attack_config

        inner = self._feature_config_inner
        ctk.CTkLabel(inner, text="Attack", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 6))

        # Slots de skill
        slots = ctk.CTkFrame(inner, fg_color="transparent")
        slots.pack(fill="x", pady=2)

        skill_vars = []
        for i in range(5):
            row = ctk.CTkFrame(slots, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"Skill {i+1}:", width=60, anchor="w").pack(side="left")
            var = tk.StringVar(value=cfg["keys"][i] if i < len(cfg["keys"]) else "")
            ctk.CTkEntry(row, textvariable=var, width=80).pack(side="left", padx=(8, 0))
            skill_vars.append(var)

        # Velocidade
        speed_frame = ctk.CTkFrame(inner, fg_color="transparent")
        speed_frame.pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(speed_frame, text="Velocidade:", width=80, anchor="w").pack(side="left")

        speeds = [50, 100, 150, 200, 250]
        speed_var = tk.IntVar(value=cfg["speed"])

        speed_btns = ctk.CTkFrame(speed_frame, fg_color="transparent")
        speed_btns.pack(side="left")
        for s in speeds:
            ctk.CTkButton(
                speed_btns, text=f"{s}ms", width=50, height=26,
                fg_color="transparent" if speed_var.get() != s else "#1a5c2a",
                border_width=1,
                command=lambda v=s: self._set_attack_speed(v, speed_var, speed_btns, speeds),
            ).pack(side="left", padx=2)

        # Save
        ctk.CTkButton(
            inner, text="Salvar", width=80,
            command=lambda: self._save_attack_config(skill_vars, speed_var),
        ).pack(pady=(12, 4))

    def _set_attack_speed(self, value, speed_var, parent, speeds):
        speed_var.set(value)
        for child, s in zip(parent.winfo_children(), speeds):
            child.configure(
                fg_color="#1a5c2a" if s == value else "transparent"
            )

    def _save_attack_config(self, skill_vars, speed_var):
        cfg = self._attack_config
        cfg["keys"] = [v.get().strip() for v in skill_vars]
        cfg["speed"] = speed_var.get()
        print(f"[GUI] Attack config salvo: {cfg}")

    def _show_potion_config(self):
        """Configuracao de Potion: tecla + threshold de HP."""
        if not hasattr(self, "_potion_config"):
            self._potion_config = {"key": "2", "hp_threshold": 55}
        cfg = self._potion_config

        inner = self._feature_config_inner
        ctk.CTkLabel(inner, text="Potion", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 6))

        r1 = ctk.CTkFrame(inner, fg_color="transparent"); r1.pack(fill="x", pady=2)
        ctk.CTkLabel(r1, text="Tecla:", width=80, anchor="w").pack(side="left")
        key_var = tk.StringVar(value=cfg["key"])
        ctk.CTkEntry(r1, textvariable=key_var, width=80).pack(side="left", padx=(8, 0))

        r2 = ctk.CTkFrame(inner, fg_color="transparent"); r2.pack(fill="x", pady=2)
        ctk.CTkLabel(r2, text="Usar se HP <", width=80, anchor="w").pack(side="left")
        hp_var = tk.IntVar(value=cfg["hp_threshold"])
        ctk.CTkEntry(r2, textvariable=hp_var, width=60).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(r2, text="%").pack(side="left")

        ctk.CTkButton(
            inner, text="Salvar", width=80,
            command=lambda: self._save_potion_config(key_var, hp_var),
        ).pack(pady=(12, 4))

    def _save_potion_config(self, key_var, hp_var):
        cfg = self._potion_config
        cfg["key"] = key_var.get().strip()
        cfg["hp_threshold"] = hp_var.get()
        print(f"[GUI] Potion config salvo: {cfg}")

    def _start_dashboard_poll(self):
        if hasattr(self, "_poll_id") and self._poll_id:
            self.root.after_cancel(self._poll_id)
        self._poll_id = self.root.after(500, self._poll_dashboard)

    def _poll_dashboard(self):
        label = self._selected_window
        if label is not None:
            sessions = SessionRegistry.get_all()
            session = sessions.get(label)
            if session:
                pid = session.get("pid")
                if pid:
                    mr = self._get_memory_reader(label, pid)
                    if mr:
                        try:
                            self._char_hp_bar.set(mr.hp_pct / 100.0)
                            self._char_hp_label.configure(text=f"{mr.hp:.0f}/{mr.max_hp}")
                            self._char_res_bar.set(mr.mana_pct / 100.0)
                            self._char_res_label.configure(text=f"{mr.mana:.0f}/{mr.max_mana}")
                            self._target_hp_bar.set(mr.target_hp_pct / 100.0)
                            self._target_hp_label.configure(text=f"{mr.target_hp}")
                            self._target_name_label.configure(text=mr.target_name or "---")
                        except Exception:
                            pass
        self._poll_id = self.root.after(500, self._poll_dashboard)

    def _get_memory_reader(self, label: str, pid: int) -> MemoryReader | None:
        if not hasattr(self, "_memory_readers"):
            self._memory_readers: dict[str, MemoryReader] = {}
        if label not in self._memory_readers:
            try:
                self._memory_readers[label] = MemoryReader(pid)
            except Exception as e:
                print(f"[GUI] MemoryReader falhou para '{label}': {e}")
                return None
        return self._memory_readers[label]

    # =====================================================
    # Log tab (dentro do notebook)
    # =====================================================

    def _build_log_tab(self):
        self._log_tab_frame.grid_columnconfigure(0, weight=1)
        self._log_tab_frame.grid_rowconfigure(0, weight=1)

        self._log_tab_text = ctk.CTkTextbox(self._log_tab_frame)
        self._log_tab_text.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._log_tab_text.configure(state="disabled")

    # =====================================================
    # Key — janela separada (sidebar)
    # =====================================================

    def _open_key_window(self):
        if self._key_window is None:
            self._key_window = KeyWindow(self)
        else:
            self._key_window.show()

    def _refresh_license_status(self):
        self._license.check(); info = self._license.info
        color = {"demo": "#aaaa00", "active": "#00aa00", "expired": "#aa0000"}.get(info.status, "#888888")
        tier = info.tier.capitalize(); days = info.days_remaining
        if hasattr(self, "_license_label"):
            self._license_label.configure(text=f"Licenca: {tier} ({days}d)", text_color=color)
        if hasattr(self, "_key_window") and self._key_window:
            self._key_window._refresh()

    # =====================================================
    # Log area (rodape)
    # =====================================================

    def _clear_log(self):
        self._log_tab_text.configure(state="normal")
        self._log_tab_text.delete("1.0", "end")
        self._log_tab_text.configure(state="disabled")

    # =====================================================
    # Status bar
    # =====================================================

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color="#1a1a1a", height=28)
        bar.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
        bar.grid_propagate(False)
        self._license_label = ctk.CTkLabel(bar, text="", text_color="#888888")
        self._license_label.pack(side="right", padx=8)
        self._refresh_license_status()

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
        try:
            GUI_SETTINGS_FILE.write_text(
                json.dumps({"client_path": self._client_path.get()}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _on_close(self):
        self._save_client_path()
        for ev in list(self._stop_events.values()):
            ev.set()
        if hasattr(self, "_memory_readers"):
            for mr in self._memory_readers.values():
                mr.close()
        self.root.destroy()

    # =====================================================
    # Gerenciamento de contas
    # =====================================================

    def _browse_client_path(self):
        path = filedialog.askopenfilename(
            title="Selecione o executavel/launcher",
            filetypes=[("Executaveis", "*.exe;*.bat;*.cmd"), ("Todos", "*.*")],
        )
        if path:
            self._client_path.set(path)

    def _on_add_account(self):
        d = AccountDialog(self.root, "Adicionar Conta")
        if d.result:
            self.accounts.append(d.result)
            save_accounts(self.accounts)

    def _on_edit_inline(self, account: Account):
        idx = self._account_index.get(account.label)
        if idx is None:
            return
        old_label = account.label
        d = AccountDialog(self.root, "Editar Conta", self.accounts[idx])
        if d.result:
            if d.result.label != old_label:
                self._stop_login_thread(old_label)
            self.accounts[idx] = d.result
            save_accounts(self.accounts)
            if d.result.auto_login:
                self._start_login_thread(d.result.label)

    def _on_remove_inline(self, account: Account):
        if not messagebox.askyesno("Remover Conta", f"Remover '{account.label}'?"):
            return
        self._stop_login_thread(account.label)
        idx = self._account_index.get(account.label)
        if idx is not None:
            del self.accounts[idx]
        save_accounts(self.accounts)

    # =====================================================
    # Login / relogging
    # =====================================================

    def _on_checkbox_toggle(self, label: str):
        var = self._login_vars.get(label)
        if var is None:
            return
        if var.get():
            self._start_login_thread(label)
        else:
            self._stop_login_thread(label)

    def _start_login_thread(self, label: str):
        if label not in self._account_index:
            return
        if label in self._stop_events and not self._stop_events[label].is_set():
            return
        client_path = self._client_path.get().strip()
        if not client_path:
            messagebox.showwarning("Client nao informado", "Informe o caminho do client.")
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
        account = self.accounts[self._account_index[label]]
        threading.Thread(
            target=self._run_account_loop,
            args=(account, client_path, stop_event),
            daemon=True,
        ).start()

    def _stop_login_thread(self, label: str):
        ev = self._stop_events.pop(label, None)
        if ev:
            ev.set()

    def _run_account_loop(self, account: Account, client_path: str, stop_event: threading.Event):
        self.log_redirector.register(account.label)
        try:
            while not stop_event.is_set():
                app = None
                try:
                    settings = replace(Settings(),
                        username=account.username, password=account.password,
                        server_name=account.server_name, character_slot=account.character_slot,
                        client_path=client_path, account_label=account.label)
                    app = Application(settings=settings)
                    app.start()
                    hwnd = app.container.session.hwnd
                    if hwnd is None:
                        raise RuntimeError("Login concluido mas sem handle de janela.")
                    pid = app.container.session.pid
                    # Le o nome real do personagem da memoria
                    char_name = account.label
                    if pid:
                        try:
                            tmp_mr = MemoryReader(pid)
                            char_name = tmp_mr.char_name or account.label
                            tmp_mr.close()
                        except Exception:
                            pass
                    SessionRegistry.register(
                        account.label, hwnd, pid, display=char_name,
                    )
                    # Renomeia a janela do jogo com o nome real
                    try:
                        win32gui.SetWindowText(hwnd, char_name)
                    except Exception:
                        pass
                    print(f"[{account.label}] Login concluido — {char_name}")
                    self._monitor_game_window(hwnd, account.label, stop_event)

                except Exception as e:
                    print(f"[{account.label}] Erro: {e}")
                    if stop_event.wait(5.0):
                        break
                finally:
                    SessionRegistry.unregister(account.label)
                    if app:
                        try: app.shutdown()
                        except Exception: pass
        finally:
            self.log_redirector.unregister()
            self._on_account_finished(account.label)

    def _monitor_game_window(self, hwnd: int, label: str, stop_event: threading.Event):
        while not stop_event.is_set():
            if not win32gui.IsWindow(hwnd):
                return
            time.sleep(2.0)

    def _on_account_finished(self, label: str):
        def _uncheck():
            var = self._login_vars.get(label)
            if var: var.set(False)
        self.root.after(0, _uncheck)
        self._stop_bot_for_window(label)
        if hasattr(self, "_memory_readers"):
            mr = self._memory_readers.pop(label, None)
            if mr: mr.close()
        with self._active_lock:
            self._active_threads -= 1
            remaining = self._active_threads
        if remaining <= 0:
            self.root.after(0, self._restore_stdout)

    def _restore_stdout(self):
        sys.stdout = self.log_redirector.original

    def _auto_start_accounts(self):
        for account in self.accounts:
            if account.auto_login:
                var = self._login_vars.get(account.label)
                if var is not None:
                    var.set(True)
                    self._start_login_thread(account.label)

    def _scan_for_game_windows(self):
        """Detecta janelas do jogo que ja estao abertas, mesmo que
        ja tenham sido renomeadas. Identifica pelo processo:
        tenta ler o nome do personagem da memoria — se funcionar,
        e uma janela do jogo."""

        from src.infrastructure.window.service import WindowService

        ws = WindowService()
        existing = SessionRegistry.get_all()

        # Remove janelas externas que fecharam
        for label, info in list(existing.items()):
            if label.startswith("ext_") and info.get("hwnd"):
                if not win32gui.IsWindow(info["hwnd"]):
                    SessionRegistry.unregister(label)

        # Busca TODAS as janelas visiveis e filtra pelo processo
        all_hwnds = ws._list_windows()
        tracked = {s["hwnd"] for s in existing.values() if s.get("hwnd")}

        for hwnd in all_hwnds:
            if hwnd in tracked:
                continue

            pid = ws._get_window_pid(hwnd)

            # Tenta ler o nome do personagem — se funcionar, e jogo
            char_name = None
            if pid:
                try:
                    mr = MemoryReader(pid)
                    char_name = mr.char_name
                    mr.close()
                except Exception:
                    continue

            if not char_name:
                continue

            display = char_name
            label = f"ext_{hwnd}"

            try:
                win32gui.SetWindowText(hwnd, char_name)
            except Exception:
                pass

            SessionRegistry.register(label, hwnd, pid, display=display)
            print(f"[GUI] Janela detectada: {display}")

        self.root.after(5000, self._scan_for_game_windows)

    # =====================================================
    # Bot Engine
    # =====================================================

    def _get_or_create_bot_engine(self, label: str) -> BotEngine:
        if not hasattr(self, "_bot_engines"):
            self._bot_engines: dict[str, BotEngine] = {}

        # Garante que as configs existam
        if not hasattr(self, "_attack_config"):
            self._attack_config = {"keys": ["1","2","3","4","5"], "speed": 150}
        if not hasattr(self, "_potion_config"):
            self._potion_config = {"key": "2", "hp_threshold": 55}

        if label not in self._bot_engines:
            engine = BotEngine()
            engine.register(AttackScript(config=self._attack_config))
            engine.register(PotionScript(config=self._potion_config))
            engine.register(PetFoodScript())
            engine.register(BuffScript())
            engine.register(HelperScript())
            engine.register(FairyScript())
            engine.register(ReviveScript())
            engine.register(DeleteScript())
            engine.register(BCScript())
            engine.register(HollowScript())
            engine.register(SellScript())
            engine.register(DRLureScript())
            self._bot_engines[label] = engine
        return self._bot_engines[label]

    def _start_bot_for_window(self, label: str):
        sessions = SessionRegistry.get_all()
        s = sessions.get(label)
        if s is None or not s.get("hwnd"):
            return
        hwnd = s["hwnd"]; pid = s.get("pid")
        engine = self._get_or_create_bot_engine(label)
        if engine.is_running:
            return
        from src.infrastructure.window.service import WindowService
        from src.infrastructure.vision.service import VisionService
        from src.infrastructure.input.service import InputService
        ws = WindowService(); vs = VisionService(window_service=ws); ins = InputService()
        mr = self._get_memory_reader(label, pid) if pid else None
        engine.start(hwnd, ins, vs, ws, self._game_reader, mr)

    def _stop_bot_for_window(self, label: str):
        if not hasattr(self, "_bot_engines"):
            return
        engine = self._bot_engines.get(label)
        if engine:
            engine.stop()

    # =====================================================
    # Execucao
    # =====================================================

    def run(self):
        self.root.mainloop()
