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
# Redirecionamento de log
# =====================================================

class MultiAccountLogRedirector:
    """Substitui sys.stdout prefixando cada linha com o apelido da conta."""

    def __init__(self, widget, original):
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
        self.widget.yview_moveto(1.0)
        self.widget.configure(state="disabled")

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
        ctk.CTkEntry(form, textvariable=self.label_var, width=260).grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))

        ctk.CTkLabel(form, text="Usuario:").grid(row=1, column=0, sticky="w", pady=4)
        ctk.CTkEntry(form, textvariable=self.username_var, width=260).grid(row=1, column=1, sticky="ew", pady=4, padx=(8, 0))

        ctk.CTkLabel(form, text="Senha:").grid(row=2, column=0, sticky="w", pady=4)
        ctk.CTkEntry(form, textvariable=self.password_var, show="*", width=260).grid(row=2, column=1, sticky="ew", pady=4, padx=(8, 0))

        ctk.CTkLabel(form, text="Servidor:").grid(row=3, column=0, sticky="w", pady=4)
        ctk.CTkEntry(form, textvariable=self.server_var, width=260).grid(row=3, column=1, sticky="ew", pady=4, padx=(8, 0))

        ctk.CTkLabel(form, text="Personagem:").grid(row=4, column=0, sticky="w", pady=4)
        combo = ctk.CTkComboBox(
            form,
            values=[CharacterSlot.LEFT, CharacterSlot.CENTER, CharacterSlot.RIGHT],
            variable=self.slot_var,
            width=260,
            state="readonly",
        )
        combo.grid(row=4, column=1, sticky="ew", pady=4, padx=(8, 0))

        ctk.CTkCheckBox(
            form,
            text="Auto-login ao abrir o Bot",
            variable=self.auto_login_var,
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

    FEATURES = [
        "Attack", "Potion", "Pet Food", "Buff",
        "Helper", "Fairy", "Revive", "Delete",
        "BC", "Hollow", "Sell", "DR Lure",
    ]

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Talisman Online - Auto Login")
        self.root.geometry("960x650")
        self.root.minsize(800, 520)

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

        self._build_top_bar()
        self._build_main_shell()
        self.log_redirector = None
        self._build_center_frames()
        self._build_home_content()
        self._build_side_panels()
        self._build_status_bar()

        self._load_saved_client_path()
        self._rebuild_login_table()
        self.root.after(500, self._auto_start_accounts)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # =====================================================
    # Barra superior
    # =====================================================

    def _build_top_bar(self):
        top = ctk.CTkFrame(self.root, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 0))

        self._top_buttons: dict[str, ctk.CTkButton] = {}

        for label in ("List", "Config", "Login", "Pricing", "Help"):
            btn = ctk.CTkButton(
                top, text=label,
                command=lambda l=label: self._on_top_bar(l),
                fg_color="transparent",
                hover_color="#3a3a3a",
                width=60,
                height=28,
            )
            btn.pack(side="left", padx=2)
            self._top_buttons[label] = btn

        # Separador
        ctk.CTkFrame(
            self.root, height=1, fg_color="#444444",
        ).pack(fill="x", padx=8, pady=4)

    def _on_top_bar(self, label: str):
        if label == "Login":
            self.tabview.set("Home")
            self.sidebar._select("Home")
        elif label == "Config":
            self.tabview.set("Config")
        elif label == "Help":
            self._show_help_dialog()
        elif label == "Pricing":
            self._show_pricing_dialog()
        elif label == "List":
            self._toggle_window_list()

    def _toggle_window_list(self):
        messagebox.showinfo("List", "Ordenacao de janelas sera implementada em breve.")

    # =====================================================
    # Dialogs
    # =====================================================

    def _show_pricing_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Pricing")
        dialog.resizable(False, False)
        dialog.transient(self.root)

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Planos", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 16))

        free = ctk.CTkFrame(frame)
        free.pack(fill="x", pady=4)
        ctk.CTkLabel(free, text="Gratuito", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))
        for item in [
            "Login automatico",
            "Configuracoes basicas",
            "1 conta simultanea",
        ]:
            ctk.CTkLabel(free, text=f"  - {item}", text_color="#aaaaaa").pack(anchor="w", padx=12)

        premium = ctk.CTkFrame(frame)
        premium.pack(fill="x", pady=4)
        ctk.CTkLabel(premium, text="Premium", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))
        for item in [
            "Multiplas contas simultaneas",
            "Todos os scripts de automacao",
            "Perfis personalizados",
            "Atualizacoes prioritarias",
            "Suporte dedicado",
        ]:
            ctk.CTkLabel(premium, text=f"  - {item}", text_color="#aaaaaa").pack(anchor="w", padx=12)

        ctk.CTkLabel(
            frame,
            text="Contato: contato@loginto.app",
            text_color="#888888",
        ).pack(pady=(16, 0))

        ctk.CTkButton(frame, text="Fechar", command=dialog.destroy).pack(pady=(12, 0))

        dialog.grab_set()
        dialog.wait_window()

    def _show_help_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Help / Sobre")
        dialog.resizable(False, False)
        dialog.transient(self.root)

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Auto Login TO", font=ctk.CTkFont(size=16, weight="bold")).pack()
        ctk.CTkLabel(frame, text="Versao 0.2.0", text_color="#888888").pack(pady=(2, 12))
        ctk.CTkLabel(frame, text="Automatizacao de login para Talisman Online").pack()

        ctk.CTkFrame(frame, height=1, fg_color="#444444").pack(fill="x", pady=12)

        ctk.CTkButton(
            frame, text="Verificar Atualizacao",
            command=self._check_for_updates,
        ).pack(pady=(0, 8))
        ctk.CTkButton(
            frame, text="Fechar", command=dialog.destroy,
            fg_color="transparent", border_width=1,
        ).pack()

        dialog.grab_set()
        dialog.wait_window()

    def _check_for_updates(self):
        try:
            import urllib.request
            url = "https://api.github.com/repos/anomalyco/opencode/releases/latest"
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("User-Agent", "LoginTO-UpdateChecker")
            with urllib.request.urlopen(req, timeout=10) as resp:
                import json as _json
                data = _json.loads(resp.read())
                latest = data.get("tag_name", "")
            if latest:
                messagebox.showinfo(
                    "Atualizacao",
                    f"Ultima versao: {latest}\nVersao atual: 0.2.0\n\nA atualizacao manual e necessaria.",
                )
            else:
                messagebox.showinfo("Atualizacao", "Nao foi possivel verificar.")
        except Exception as e:
            messagebox.showinfo("Atualizacao", f"Erro: {e}")

    # =====================================================
    # Layout 3 colunas
    # =====================================================

    def _build_main_shell(self):
        self._main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self._main_frame.pack(fill="both", expand=True, padx=8, pady=4)
        self._main_frame.grid_columnconfigure(1, weight=1)
        self._main_frame.grid_rowconfigure(0, weight=1)

        self.center_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self.center_frame.grid(row=0, column=1, sticky="nsew")

    def _build_side_panels(self):
        sidebar_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent", width=130)
        sidebar_frame.grid(row=0, column=0, sticky="ns", padx=(0, 4))
        sidebar_frame.grid_propagate(False)

        self.sidebar = Sidebar(sidebar_frame, on_select=self._on_sidebar_select)
        self.sidebar.pack(fill="both", expand=True)

        right_frame = ctk.CTkFrame(self._main_frame, width=190)
        right_frame.grid(row=0, column=2, sticky="ns", padx=(4, 0))
        right_frame.grid_propagate(False)

        self.right_panel = RightPanel(
            right_frame,
            on_select=self._on_right_panel_select,
            on_action=self._on_right_panel_action,
        )
        self.right_panel.pack(fill="both", expand=True)

    # =====================================================
    # Centro: CTkTabview
    # =====================================================

    def _build_center_frames(self):
        self.tabview = ctk.CTkTabview(self.center_frame)
        self.tabview.pack(fill="both", expand=True)

        self.tabview.add("Home")
        self.tabview.add("Config")
        self.tabview.add("Dashboard")
        self.tabview.add("Key")

        self._home_frame = self.tabview.tab("Home")
        self._config_frame = self.tabview.tab("Config")
        self._dashboard_frame = self.tabview.tab("Dashboard")
        self._key_frame = self.tabview.tab("Key")

        self._build_config_content()
        self._build_dashboard_content()
        self._build_key_content()

        self.tabview.set("Home")

    def _build_config_content(self):
        frame = ctk.CTkFrame(self._config_frame, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text="Configuracoes", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 12))

        row1 = ctk.CTkFrame(frame, fg_color="transparent")
        row1.pack(fill="x", pady=4)
        ctk.CTkLabel(row1, text="Client:").pack(side="left")
        ctk.CTkEntry(row1, textvariable=self._client_path, width=320).pack(side="left", padx=(8, 4))
        ctk.CTkButton(
            row1, text="Procurar", width=80,
            command=self._browse_client_path,
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text="Demais configuracoes ficam em config.py e .env",
            text_color="#888888",
        ).pack(anchor="w", pady=(16, 0))

    # =====================================================
    # Home: login
    # =====================================================

    def _build_home_content(self):
        self._home_frame.grid_columnconfigure(0, weight=1)
        self._home_frame.grid_rowconfigure(2, weight=1)

        # Tabela de contas
        self._login_scroll = ctk.CTkScrollableFrame(self._home_frame)
        self._login_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))

        btn_row = ctk.CTkFrame(self._home_frame, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        ctk.CTkButton(btn_row, text="Adicionar Conta", command=self._on_add_account).pack(side="left")

        # Log
        log_frame = ctk.CTkFrame(self._home_frame, fg_color="transparent")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="Log:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")

        self.log_text = ctk.CTkTextbox(log_frame)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        self.log_text.configure(state="disabled")

        self.log_redirector = MultiAccountLogRedirector(self.log_text, sys.stdout)

        self._home_frame.grid_rowconfigure(2, weight=1)

    def _rebuild_login_table(self):
        for widget in self._login_scroll.winfo_children():
            widget.destroy()

        old_checked = {label for label, var in self._login_vars.items() if var.get()}
        self._login_vars.clear()
        self._account_index.clear()

        if not self.accounts:
            ctk.CTkLabel(
                self._login_scroll,
                text="Nenhuma conta cadastrada.\nClique em 'Adicionar Conta' para comecar.",
            ).pack(expand=True, pady=20)
            return

        hdr = ctk.CTkFrame(self._login_scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(4, 4))
        ctk.CTkLabel(hdr, text="Conta", font=ctk.CTkFont(weight="bold"), width=120, anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="Servidor", font=ctk.CTkFont(weight="bold"), width=140, anchor="w").pack(side="left", padx=(8, 0))
        ctk.CTkLabel(hdr, text="Usuario", font=ctk.CTkFont(weight="bold"), width=140, anchor="w").pack(side="left", padx=(8, 0))

        ctk.CTkFrame(self._login_scroll, height=1, fg_color="#444444").pack(fill="x", pady=(0, 4))

        for idx, account in enumerate(self.accounts):
            self._account_index[account.label] = idx

            row = ctk.CTkFrame(self._login_scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)

            var = ctk.BooleanVar(value=(account.label in old_checked))
            self._login_vars[account.label] = var

            cb = ctk.CTkCheckBox(
                row, text="",
                variable=var,
                command=lambda label=account.label: self._on_checkbox_toggle(label),
                width=20,
            )
            cb.pack(side="left")

            ctk.CTkLabel(row, text=account.label, width=120, anchor="w").pack(side="left", padx=(4, 0))
            ctk.CTkLabel(row, text=account.server_name, width=140, anchor="w").pack(side="left", padx=(8, 0))
            ctk.CTkLabel(row, text=account.username, width=140, anchor="w").pack(side="left", padx=(8, 0))

            edit_btn = ctk.CTkButton(
                row, text="E", width=28, height=24,
                command=lambda a=account: self._on_edit_inline(a),
                fg_color="transparent", border_width=1,
            )
            edit_btn.pack(side="right", padx=(4, 2))
            ctk.CTkButton(
                row, text="X", width=28, height=24,
                command=lambda a=account: self._on_remove_inline(a),
                fg_color="transparent", border_width=1,
                text_color="#cc4444",
            ).pack(side="right")

    def _on_sidebar_select(self, label: str):
        if label == "Home":
            self.tabview.set("Home")
        elif label == "Config":
            self.tabview.set("Config")
        elif label == "Key":
            self.tabview.set("Key")
        else:
            self.tabview.set("Dashboard")
            self._highlight_feature(label)

    # =====================================================
    # Dashboard
    # =====================================================

    def _build_dashboard_content(self):
        self._dashboard_frame.grid_columnconfigure(0, weight=1)
        self._dashboard_frame.grid_rowconfigure(3, weight=1)

        # Char Info
        char_frame = ctk.CTkFrame(self._dashboard_frame)
        char_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        ctk.CTkLabel(char_frame, text="Char Info", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(6, 4))

        hp_row = ctk.CTkFrame(char_frame, fg_color="transparent")
        hp_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(hp_row, text="HP:", width=60, anchor="w").pack(side="left")
        self._char_hp_bar = ctk.CTkProgressBar(hp_row, width=180)
        self._char_hp_bar.pack(side="left", padx=(8, 8))
        self._char_hp_bar.set(0)
        self._char_hp_label = ctk.CTkLabel(hp_row, text="---", width=40)
        self._char_hp_label.pack(side="left")

        res_row = ctk.CTkFrame(char_frame, fg_color="transparent")
        res_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(res_row, text="Recurso:", width=60, anchor="w").pack(side="left")
        self._char_res_bar = ctk.CTkProgressBar(res_row, width=180)
        self._char_res_bar.pack(side="left", padx=(8, 8))
        self._char_res_bar.set(0)
        self._char_res_label = ctk.CTkLabel(res_row, text="---", width=40)
        self._char_res_label.pack(side="left")

        # Target Info
        tgt_frame = ctk.CTkFrame(self._dashboard_frame)
        tgt_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=4)

        ctk.CTkLabel(tgt_frame, text="Target Info", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(6, 4))

        t_hp_row = ctk.CTkFrame(tgt_frame, fg_color="transparent")
        t_hp_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(t_hp_row, text="HP:", width=60, anchor="w").pack(side="left")
        self._target_hp_bar = ctk.CTkProgressBar(t_hp_row, width=180)
        self._target_hp_bar.pack(side="left", padx=(8, 8))
        self._target_hp_bar.set(0)
        self._target_hp_label = ctk.CTkLabel(t_hp_row, text="---", width=40)
        self._target_hp_label.pack(side="left")

        t_name_row = ctk.CTkFrame(tgt_frame, fg_color="transparent")
        t_name_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(t_name_row, text="Nome:", width=60, anchor="w").pack(side="left")
        self._target_name_label = ctk.CTkLabel(t_name_row, text="---")
        self._target_name_label.pack(side="left", padx=(8, 0))

        # Feature Checkboxes
        func_frame = ctk.CTkFrame(self._dashboard_frame)
        func_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=4)

        ctk.CTkLabel(func_frame, text="Funcoes", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(6, 4))

        grid = ctk.CTkFrame(func_frame, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=(0, 8))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        self._feature_widgets: dict[str, ctk.CTkCheckBox] = {}
        self._feature_highlight_labels: dict[str, ctk.CTkLabel] = {}

        half = len(self.FEATURES) // 2
        for i, feature in enumerate(self.FEATURES):
            col = 0 if i < half else 1
            row_num = i if i < half else i - half

            check_row = ctk.CTkFrame(grid, fg_color="transparent")
            check_row.grid(row=row_num, column=col, sticky="w", pady=4, padx=(0, 20))

            hl = ctk.CTkLabel(check_row, text="  ", width=20)
            hl.pack(side="left")
            self._feature_highlight_labels[feature] = hl

            cb = ctk.CTkCheckBox(check_row, text=feature, state="disabled")
            cb.pack(side="left")
            self._feature_widgets[feature] = cb

        # Status
        self._dashboard_status = ctk.CTkLabel(
            self._dashboard_frame,
            text="Selecione uma janela no painel direito para configurar as funcoes.",
            text_color="#888888",
        )
        self._dashboard_status.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 4))

        # Dashboard Log
        log_frame = ctk.CTkFrame(self._dashboard_frame)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(4, 8))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="Log da Janela", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))

        self._dashboard_log = ctk.CTkTextbox(log_frame, height=100)
        self._dashboard_log.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._dashboard_log.configure(state="disabled")

    def _ensure_window_state(self, label: str):
        if label not in self._feature_vars:
            self._feature_vars[label] = {
                f: ctk.BooleanVar(value=False) for f in self.FEATURES
            }
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
            status = "INICIADO"
        else:
            self._stop_bot_for_window(label)
            status = "PARADO"

        self._dashboard_log_append(f"[{label}] Bot {status}.\n")
        self._refresh_dashboard()

    def _refresh_dashboard(self):
        label = self._selected_window

        if label is None or label not in self._feature_vars:
            self._dashboard_status.configure(text="Selecione uma janela no painel direito para configurar as funcoes.")
            for feature in self.FEATURES:
                self._feature_widgets[feature].configure(state="disabled")
                self._feature_highlight_labels[feature].configure(text="  ")
            self._char_hp_bar.set(0)
            self._char_hp_label.configure(text="---")
            self._char_res_bar.set(0)
            self._char_res_label.configure(text="---")
            self._target_hp_bar.set(0)
            self._target_hp_label.configure(text="---")
            self._target_name_label.configure(text="---")
            return

        running = self._widget_states.get(label, False)
        self._dashboard_status.configure(text=f"Janela: {label}  |  Status: {'ATIVO' if running else 'PARADO'}")

        for feature in self.FEATURES:
            cb = self._feature_widgets[feature]
            var = self._feature_vars[label][feature]
            cb.configure(state="normal", variable=var)

    def _highlight_feature(self, feature: str):
        if feature not in self._feature_highlight_labels:
            return
        hl = self._feature_highlight_labels[feature]
        hl.configure(text=">")
        def _clear():
            hl.configure(text="  ")
        self.root.after(2000, _clear)

    def _start_dashboard_poll(self):
        self._poll_dashboard()

    def _poll_dashboard(self):
        label = self._selected_window
        if label is None or not self._widget_states.get(label, False):
            return

        sessions = SessionRegistry.get_all()
        session = sessions.get(label)
        if session is None:
            return

        hwnd = session.get("hwnd")
        if hwnd is None:
            return

        try:
            from src.infrastructure.window.service import WindowService
            ws = WindowService()
            screenshot = ws.capture_hwnd(hwnd)

            char_info = self._game_reader.read_char_info(screenshot)
            target_info = self._game_reader.read_target_info(screenshot)

            self._char_hp_bar.set(char_info.hp_pct / 100.0)
            self._char_hp_label.configure(text=f"{char_info.hp_pct:.0f}%")
            self._char_res_bar.set(char_info.resource_pct / 100.0)
            self._char_res_label.configure(text=f"{char_info.resource_pct:.0f}%")
            self._target_hp_bar.set(target_info.hp_pct / 100.0)
            self._target_hp_label.configure(text=f"{target_info.hp_pct:.0f}%")
            self._target_name_label.configure(text=target_info.name or "---")
        except Exception:
            pass

        if self._widget_states.get(label, False):
            self.root.after(1000, self._poll_dashboard)

    def _dashboard_log_append(self, text: str):
        self._dashboard_log.configure(state="normal")
        self._dashboard_log.insert("end", text)
        self._dashboard_log.yview_moveto(1.0)
        self._dashboard_log.configure(state="disabled")

    # =====================================================
    # Key (licenciamento)
    # =====================================================

    def _build_key_content(self):
        frame = ctk.CTkFrame(self._key_frame, fg_color="transparent")
        frame.pack(expand=True, padx=24)

        ctk.CTkLabel(frame, text="Licenciamento", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 16))

        key_row = ctk.CTkFrame(frame, fg_color="transparent")
        key_row.pack(fill="x", pady=4)
        self._license_key_var = tk.StringVar()
        ctk.CTkEntry(key_row, textvariable=self._license_key_var, width=220, placeholder_text="TO-AAAAMMDD-HASH").pack(side="left", padx=(0, 8))
        ctk.CTkButton(key_row, text="Validar", command=self._on_validate_license).pack(side="left")

        ctk.CTkButton(
            frame, text="Usar modo Demo (30 dias gratuitos)",
            command=self._on_activate_demo,
            fg_color="transparent", border_width=1,
        ).pack(pady=(16, 20))

        self._license_status_frame = ctk.CTkFrame(frame)
        self._license_status_frame.pack(fill="x")

        self._license_status_text = ctk.CTkLabel(
            self._license_status_frame,
            text="",
            font=ctk.CTkFont(size=12),
        )
        self._license_status_text.pack(anchor="w", padx=12, pady=12)

        ctk.CTkFrame(frame, height=1, fg_color="#444444").pack(fill="x", pady=(16, 4))

        ctk.CTkLabel(
            frame,
            text="Adquira sua licenca: contato@loginto.app",
            text_color="#888888",
        ).pack()

        self._refresh_license_status()

    def _refresh_license_status(self):
        self._license.check()
        info = self._license.info

        if info.status == "demo":
            status = "Demonstracao"
            color = "#aaaa00"
        elif info.status == "active":
            status = "Ativa"
            color = "#00aa00"
        else:
            status = "Expirada"
            color = "#aa0000"

        tier = info.tier.capitalize()
        days = info.days_remaining

        self._license_status_text.configure(
            text=(
                f"Status: {status}\n"
                f"Dias restantes: {days}\n"
                f"Tipo: {tier}\n"
                f"Chave: {info.key if info.key else '---'}"
            ),
            text_color=color,
        )

        if hasattr(self, "_license_label"):
            self._license_label.configure(
                text=f"Licenca: {tier} ({days}d)",
                text_color=color,
            )

    def _on_validate_license(self):
        key = self._license_key_var.get().strip()
        if not key:
            messagebox.showwarning("Chave vazia", "Insira uma chave.")
            return
        success, msg = self._license.activate(key)
        if success:
            messagebox.showinfo("Licenca ativada", msg)
        else:
            messagebox.showerror("Erro", msg)
        self._license_key_var.set("")
        self._refresh_license_status()

    def _on_activate_demo(self):
        self._license.activate("DEMO")
        self._refresh_license_status()

    # =====================================================
    # Status bar
    # =====================================================

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=(0, 6))

        self._license_label = ctk.CTkLabel(bar, text="", text_color="#888888")
        self._license_label.pack(side="right")

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
        except Exception as e:
            print(f"[GUI] Aviso: nao foi possivel salvar configuracoes ({e})")

    def _on_close(self):
        self._save_client_path()
        for stop_event in list(self._stop_events.values()):
            stop_event.set()
        self.root.destroy()

    # =====================================================
    # Gerenciamento de contas
    # =====================================================

    def _browse_client_path(self):
        path = filedialog.askopenfilename(
            title="Selecione o executavel/launcher do client",
            filetypes=[("Executaveis", "*.exe;*.bat;*.cmd"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self._client_path.set(path)

    def _on_add_account(self):
        dialog = AccountDialog(self.root, "Adicionar Conta")
        if dialog.result:
            self.accounts.append(dialog.result)
            save_accounts(self.accounts)
            self._rebuild_login_table()

    def _on_edit_inline(self, account: Account):
        idx = self._account_index.get(account.label)
        if idx is None:
            return
        old_label = account.label
        dialog = AccountDialog(self.root, "Editar Conta", self.accounts[idx])
        if dialog.result:
            new_label = dialog.result.label
            if new_label != old_label:
                self._stop_login_thread(old_label)
            self.accounts[idx] = dialog.result
            save_accounts(self.accounts)
            self._rebuild_login_table()
            if dialog.result.auto_login:
                self._start_login_thread(new_label)

    def _on_remove_inline(self, account: Account):
        if not messagebox.askyesno("Remover Conta", f"Remover '{account.label}'?"):
            return
        self._stop_login_thread(account.label)
        idx = self._account_index.get(account.label)
        if idx is not None:
            del self.accounts[idx]
        save_accounts(self.accounts)
        self._rebuild_login_table()

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

        thread = threading.Thread(
            target=self._run_account_loop,
            args=(account, client_path, stop_event),
            daemon=True,
        )
        thread.start()

    def _stop_login_thread(self, label: str):
        stop_event = self._stop_events.pop(label, None)
        if stop_event:
            stop_event.set()

    def _run_account_loop(self, account: Account, client_path: str, stop_event: threading.Event):
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

                    SessionRegistry.register(account.label, hwnd)
                    self._monitor_game_window(hwnd, account.label, stop_event)

                except Exception as e:
                    print(f"[{account.label}] Erro: {e}")
                    if stop_event.wait(5.0):
                        break
                finally:
                    SessionRegistry.unregister(account.label)
                    if app:
                        try:
                            app.shutdown()
                        except Exception:
                            pass
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
            if var:
                var.set(False)
        self.root.after(0, _uncheck)

        self._stop_bot_for_window(label)

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

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # =====================================================
    # Bot Engine
    # =====================================================

    def _get_or_create_bot_engine(self, label: str) -> BotEngine:
        if not hasattr(self, "_bot_engines"):
            self._bot_engines: dict[str, BotEngine] = {}

        if label not in self._bot_engines:
            engine = BotEngine()
            engine.register(AttackScript())
            engine.register(PotionScript())
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
        session = sessions.get(label)
        if session is None or not session.get("hwnd"):
            return

        hwnd = session["hwnd"]
        engine = self._get_or_create_bot_engine(label)
        if engine.is_running:
            return

        from src.infrastructure.window.service import WindowService
        from src.infrastructure.vision.service import VisionService
        from src.infrastructure.input.service import InputService

        ws = WindowService()
        vs = VisionService(window_service=ws)
        ins = InputService()

        engine.start(hwnd, ins, vs, ws, self._game_reader)

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
