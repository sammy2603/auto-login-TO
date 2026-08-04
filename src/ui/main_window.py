from __future__ import annotations

import json, logging, threading, time, tkinter as tk
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import win32gui

from src.app.application import Application
from src.app.automation_controller import AutomationController
from src.config.settings import Settings
from src.infrastructure.logging import (
    LoggingService,
    get_logger,
    session_context,
)
from src.infrastructure.logging.service import (
    CONSOLE_DATE_FORMAT,
    CONSOLE_FORMAT,
)
from src.services.license.service import LicenseService
from src.services.game.memory_reader import MemoryReader
from src.services.bot.script_registry import ScriptRegistry
from src.services.bot.scripts.bc import DEFAULT_CONFIG as BC_DEFAULT_CONFIG
from src.shared.character_slots import CharacterSlot
from src.ui.log_handler import TextboxLogHandler

logger = get_logger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# Paleta
BG = "#080B14"; PANEL = "#0F1525"; CARD = "#141C2F"; HOVER = "#1B2640"
TEXT = "#E8EEF9"; TEXT2 = "#95A7C8"; TEXT3 = "#5D6A84"
GREEN = "#22C55E"; BLUE = "#4F8CFF"; YELLOW = "#FACC15"; RED = "#FF4D4F"
PURPLE = "#A855F7"; CYAN = "#38BDF8"

# Traduz a 'category' semântica de cada script (definida em
# script_registry.py, sem depender da UI) pra uma cor concreta desta
# paleta. Novos scripts com uma categoria já existente ganham cor
# automaticamente -- só precisa de entrada nova aqui se vier uma
# categoria nova.
CATEGORY_COLORS = {
    "combat": RED, "support": GREEN, "companion": PURPLE,
    "highlight": YELLOW, "utility": BLUE, "special": CYAN, "neutral": TEXT3,
}

_SCRIPTS = ScriptRegistry.all()
COLORS = {d.display_name: CATEGORY_COLORS.get(d.category, TEXT2) for d in _SCRIPTS}
ICONS = {d.display_name: d.icon for d in _SCRIPTS}

# Fontes — inicializadas via _init_fonts()
FONT_H1 = FONT_H2 = FONT_H3 = FONT_TEXT = FONT_SMALL = FONT_MONO = None
def _init_fonts():
    global FONT_H1, FONT_H2, FONT_H3, FONT_TEXT, FONT_SMALL, FONT_MONO
    FONT_H2 = ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
    FONT_H3 = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
    FONT_TEXT = ctk.CTkFont(family="Segoe UI", size=13)
    FONT_SMALL = ctk.CTkFont(family="Segoe UI", size=11)
    FONT_MONO = ctk.CTkFont(family="Consolas", size=11)

GUI_SETTINGS_FILE = Path(__file__).resolve().parents[2] / "gui_settings.json"
ACCOUNTS_FILE = Path(__file__).resolve().parents[2] / "accounts.json"
_DEFAULTS = Settings()

@dataclass
class Account:
    label: str; username: str; password: str; server_name: str
    character_slot: str; auto_login: bool = False

def load_accounts():
    if not ACCOUNTS_FILE.exists(): return []
    try:
        data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        return [Account(**{**d, "auto_login": d.get("auto_login", False)}) for d in data]
    except: return []

def save_accounts(acts):
    try: ACCOUNTS_FILE.write_text(json.dumps([asdict(a) for a in acts], indent=2, ensure_ascii=False), encoding="utf-8")
    except: pass


class AccountDialog:
    """
    Formulário de adicionar/editar conta. Bloqueia (via wait_window)
    até o usuário salvar ou cancelar; o resultado fica em .result
    (None se cancelado).
    """

    def __init__(self, parent, title: str, account: "Account | None" = None):
        self.result: Account | None = None

        d = ctk.CTkToplevel(parent)
        d.title(title)
        d.geometry("420x520")
        d.configure(fg_color=BG)
        d.resizable(False, False)
        d.transient(parent)

        parent.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        d.geometry(f"420x520+{px + (pw - 420) // 2}+{py + (ph - 520) // 2}")

        outer = ctk.CTkFrame(d, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(outer, text=title, font=FONT_H3, text_color=TEXT).pack(anchor="w")
        ctk.CTkFrame(outer, height=1, fg_color="#1A2540").pack(fill="x", pady=(6, 16))

        self.label_var = ctk.StringVar(value=account.label if account else "")
        self.username_var = ctk.StringVar(value=account.username if account else "")
        self.password_var = ctk.StringVar(value=account.password if account else "")
        self.server_var = ctk.StringVar(value=account.server_name if account else "")
        self.slot_var = ctk.StringVar(value=account.character_slot if account else CharacterSlot.CENTER)
        self.auto_var = ctk.BooleanVar(value=account.auto_login if account else False)

        self._field(outer, "Apelido da conta", self.label_var)
        self._field(outer, "Usuário", self.username_var)
        self._field(outer, "Senha", self.password_var, show="*")
        self._field(outer, "Servidor", self.server_var)

        slot_frame = ctk.CTkFrame(outer, fg_color="transparent")
        slot_frame.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(slot_frame, text="Personagem", font=FONT_SMALL, text_color=TEXT2).pack(anchor="w", pady=(0, 4))
        ctk.CTkOptionMenu(
            slot_frame, variable=self.slot_var,
            values=[CharacterSlot.LEFT, CharacterSlot.CENTER, CharacterSlot.RIGHT],
            font=FONT_TEXT, fg_color=CARD, button_color=HOVER, button_hover_color=BLUE,
            dropdown_fg_color=CARD, dropdown_text_color=TEXT, text_color=TEXT,
        ).pack(fill="x")

        ctk.CTkCheckBox(
            outer, text="Login automático ao abrir o programa",
            variable=self.auto_var, font=FONT_SMALL, text_color=TEXT2,
        ).pack(anchor="w", pady=(16, 0))

        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom", pady=(20, 0))
        ctk.CTkButton(
            btn_row, text="Cancelar", font=FONT_SMALL, fg_color="transparent", border_width=1,
            border_color=TEXT3, text_color=TEXT2, hover_color=HOVER, width=90,
            command=d.destroy,
        ).pack(side="right")
        ctk.CTkButton(
            btn_row, text="Salvar", font=FONT_SMALL, fg_color=GREEN, hover_color="#1B9E4B",
            width=90, command=lambda: self._save(d),
        ).pack(side="right", padx=(0, 8))

        d.grab_set()
        d.wait_window()

    def _field(self, parent, label, var, show=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(frame, text=label, font=FONT_SMALL, text_color=TEXT2).pack(anchor="w", pady=(0, 4))
        entry = ctk.CTkEntry(
            frame, textvariable=var, font=FONT_TEXT,
            fg_color=CARD, border_color="#1A2540", text_color=TEXT,
        )
        if show:
            entry.configure(show=show)
        entry.pack(fill="x")

    def _save(self, dialog):
        label = self.label_var.get().strip()
        username = self.username_var.get().strip()

        if not label or not username or not self.password_var.get():
            messagebox.showwarning(
                "Campos obrigatórios", "Preencha ao menos apelido, usuário e senha."
            )
            return

        self.result = Account(
            label=label,
            username=username,
            password=self.password_var.get(),
            server_name=self.server_var.get().strip(),
            character_slot=self.slot_var.get(),
            auto_login=self.auto_var.get(),
        )
        dialog.destroy()

# ============================================================
# SCRIPT CARD
# ============================================================
class ScriptCard(ctk.CTkFrame):
    def __init__(self, parent, name, on_toggle, on_config, **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=12, border_width=1,
                         border_color="#1A2540", width=190, height=100, **kw)
        self.pack_propagate(False)
        self.name = name
        self._on_toggle = on_toggle
        self._on_config = on_config
        self._build()

    def _build(self):
        color = COLORS.get(self.name, TEXT2)
        icon = ICONS.get(self.name, "?")

        # Linha 1: icon + nome + settings
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(12, 2))
        ctk.CTkLabel(hdr, text=icon, font=ctk.CTkFont(size=22), text_color=color).pack(side="left")
        ctk.CTkLabel(hdr, text=self.name, font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT).pack(side="left", padx=6)
        ctk.CTkButton(hdr, text="\u2699", width=22, height=22, font=ctk.CTkFont(size=11),
                      fg_color="transparent", hover_color=HOVER,
                      command=lambda: self._on_config(self.name)).pack(side="right")

        # Linha 2: switch + status
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(8, 10))
        self._sw = ctk.CTkSwitch(bottom, text="", width=36, command=lambda: self._on_toggle(self.name, self._sw.get()))
        self._sw.pack(side="left")
        self._dot = ctk.CTkLabel(bottom, text="\u25CF", font=ctk.CTkFont(size=10), text_color=TEXT3)
        self._dot.pack(side="right")

    def set_enabled(self, enabled: bool):
        if self._sw.get() != enabled:
            self._sw.select() if enabled else self._sw.deselect()
        self._dot.configure(text_color=GREEN if enabled else TEXT3)

# ============================================================
# MAIN WINDOW
# ============================================================
class MainWindow:
    FEATURES = [d.display_name for d in _SCRIPTS]

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Auto Login TO")
        self.root.geometry("1200x740")
        self.root.configure(fg_color=BG)
        _init_fonts()

        self.accounts = load_accounts()
        self._stop_events: dict[str, threading.Event] = {}
        self._feature_vars: dict[str, dict[str, ctk.BooleanVar]] = {}
        self._widget_states: dict[str, bool] = {}
        self._client_path = tk.StringVar(value=_DEFAULTS.client_path)
        self._license = LicenseService()
        self.controller = AutomationController()

        # Assina eventos do núcleo de automação -- em vez de esperar o
        # próximo ciclo do polling (até 500ms), a UI reage na hora
        # quando um script liga/desliga. Publish() pode vir de
        # qualquer thread, então o callback só agenda o trabalho real
        # de volta pra thread principal via root.after().
        self.controller.events.subscribe("bot.started", self._on_bot_state_event)
        self.controller.events.subscribe("bot.stopped", self._on_bot_state_event)
        self.controller.events.subscribe("session.registered", self._on_session_event)
        self.controller.events.subscribe("session.unregistered", self._on_session_event)
        self._selected_window: str | None = None
        self._client_cards: dict[str, any] = {}
        self._kill_track: dict = {}
        self._script_cards: dict[str, ScriptCard] = {}
        # Config do BC por conta -- ver _bc_config_da_conta().
        self._bc_configs: dict[str, dict] = {}
        self._login_win = None; self._config_win = None

        self._build_top_bar()
        self._build_layout()
        self._build_bottom_bar()

        # O console da GUI e apenas mais um destino do logging: recebe
        # as mesmas mensagens que vao pro terminal e pro arquivo.
        self._log_handler = TextboxLogHandler(self._console)
        self._log_handler.setFormatter(
            logging.Formatter(CONSOLE_FORMAT, datefmt=CONSOLE_DATE_FORMAT)
        )
        LoggingService.add_handler(self._log_handler)

        self._load_client_path()
        self.root.after(500, self._auto_start_accounts)
        self.root.after(1000, self._scan_for_game_windows)
        self.root.after(1500, self._poll_loop)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ============================================================
    # TOP BAR
    # ============================================================
    def _build_top_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color=PANEL, height=48, corner_radius=0)
        bar.pack(fill="x"); bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="\u25B6 AUTO LOGIN TO", font=FONT_H3, text_color=TEXT).pack(side="left", padx=16, pady=10)
        for label in ("List", "Config", "Login", "Pricing", "Help"):
            ctk.CTkButton(bar, text=label, font=FONT_SMALL, fg_color="transparent",
                         hover_color=HOVER, height=30, width=60,
                         command=lambda l=label: self._on_top_menu(l)).pack(side="right", padx=2)
        for name, color in [("Online", GREEN), ("Scripts", BLUE)]:
            frame = ctk.CTkFrame(bar, fg_color="transparent"); frame.pack(side="right", padx=12)
            ctk.CTkLabel(frame, text="\u25CF", font=ctk.CTkFont(size=8), text_color=color).pack(side="left", padx=(0,4))
            lbl = ctk.CTkLabel(frame, text=f"0 {name}", font=FONT_SMALL, text_color=color); lbl.pack(side="left")
            setattr(self, f"_ind_{name.lower()}", lbl)

    def _on_top_menu(self, label):
        if label == "Login": self._open_login()
        elif label == "Config": self._open_config()
        elif label == "Pricing": self._show_pricing()
        elif label == "Help": self._show_help()

    # ============================================================
    # LAYOUT: Scripts grid (esq) | Right panel (dir)
    # ============================================================
    def _build_layout(self):
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.pack(fill="both", expand=True)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_rowconfigure(0, weight=1)

        # Scripts Grid (left)
        self._scripts_container = ctk.CTkFrame(main, fg_color="transparent")
        self._scripts_container.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        ctk.CTkLabel(self._scripts_container, text="SCRIPTS", font=FONT_H3, text_color=TEXT).pack(anchor="w")

        self._editing_label = ctk.CTkLabel(
            self._scripts_container,
            text="Nenhuma conta selecionada — clique num client à direita",
            font=FONT_SMALL,
            text_color=TEXT3,
        )
        self._editing_label.pack(anchor="w", pady=(2, 0))

        self._bot_toggle_btn = ctk.CTkButton(
            self._scripts_container,
            text="Start Scripts",
            state="disabled",
            fg_color=GREEN,
            hover_color="#1B9E4B",
            height=32,
            command=self._toggle_bot_for_selected,
        )
        self._bot_toggle_btn.pack(anchor="w", pady=(6, 0))

        ctk.CTkFrame(self._scripts_container, height=1, fg_color="#1A2540").pack(fill="x", pady=4)

        self._cards_grid = ctk.CTkFrame(self._scripts_container, fg_color="transparent")
        self._cards_grid.pack(fill="both", expand=True, pady=4)

        for i, feat in enumerate(self.FEATURES):
            card = ScriptCard(self._cards_grid, feat,
                            on_toggle=self._on_script_toggle,
                            on_config=self._open_script_config)
            row = i // 3; col = i % 3
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self._script_cards[feat] = card

        for c in range(3): self._cards_grid.grid_columnconfigure(c, weight=1)

        # Right Panel
        self._right = ctk.CTkFrame(main, fg_color=PANEL, width=280)
        self._right.grid(row=0, column=1, sticky="ns")
        self._right.grid_rowconfigure(0, weight=8)
        self._right.grid_rowconfigure(1, weight=2)
        self._right.grid_columnconfigure(0, weight=1)
        self._build_clients()
        self._build_console()

    def _build_clients(self):
        f = ctk.CTkFrame(self._right, fg_color="transparent")
        f.grid(row=0, column=0, sticky="nsew")
        f.grid_columnconfigure(0, weight=1); f.grid_rowconfigure(0, weight=0); f.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(f, text="CLIENTS", font=FONT_SMALL, text_color=TEXT3).grid(row=0, column=0, sticky="w", padx=8, pady=(8,2))
        self._clients_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        self._clients_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=2)
        self._clients_scroll.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._clients_scroll, text="No clients", font=FONT_SMALL, text_color=TEXT3).pack(expand=True, pady=20)

    def _build_console(self):
        f = ctk.CTkFrame(self._right, fg_color="transparent")
        f.grid(row=1, column=0, sticky="nsew")
        hdr = ctk.CTkFrame(f, fg_color="transparent"); hdr.pack(fill="x", padx=8, pady=(2,1))
        ctk.CTkLabel(hdr, text="CONSOLE", font=FONT_SMALL, text_color=TEXT3).pack(side="left")
        ctk.CTkButton(hdr, text="Clear", width=40, height=18, font=ctk.CTkFont(size=9),
                      fg_color="transparent", border_width=1, border_color=TEXT3, command=self._clear_console).pack(side="right")
        self._console = ctk.CTkTextbox(f, font=FONT_MONO, fg_color=BG, border_width=0)
        self._console.pack(fill="both", expand=True, padx=8, pady=(1,4)); self._console.configure(state="disabled")

    def _clear_console(self):
        self._console.configure(state="normal"); self._console.delete("1.0","end"); self._console.configure(state="disabled")

    # ============================================================
    # BOTTOM BAR
    # ============================================================
    def _build_bottom_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color=PANEL, height=26, corner_radius=0)
        bar.pack(fill="x"); bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="v0.3.0", font=ctk.CTkFont(size=10), text_color=TEXT3).pack(side="left", padx=12, pady=4)
        self._license_label = ctk.CTkLabel(bar, text="", font=ctk.CTkFont(size=10), text_color=TEXT3)
        self._license_label.pack(side="right", padx=12, pady=4)
        self._refresh_license()

    def _refresh_license(self):
        self._license.check(); info = self._license.info
        c = {"demo": YELLOW, "active": GREEN, "expired": RED}.get(info.status, TEXT3)
        self._license_label.configure(text=f"License: {info.tier.capitalize()} ({info.days_remaining}d)", text_color=c)

    # ============================================================
    # SCRIPT TOGGLE & CONFIG
    # ============================================================
    def _on_script_toggle(self, name, enabled):
        win = self._selected_window
        if win:
            vars_for_win = self._feature_vars.setdefault(win, {})
            if name not in vars_for_win:
                vars_for_win[name] = ctk.BooleanVar(value=False)
            vars_for_win[name].set(enabled)
        if name in self._script_cards:
            self._script_cards[name].set_enabled(enabled)
        self._refresh_bot_toggle_button()

    def _open_script_config(self, name):
        method = getattr(self, f"_cfg_{name.lower().replace(' ', '_')}", None)
        if not method:
            method = self._cfg_generic
        method(name)

    def _cfg_window(self, title, width, height, build_fn):
        d = ctk.CTkToplevel(self.root); d.title(f"{title} Config"); d.configure(fg_color=BG)
        d.resizable(False, False); d.transient(self.root)
        self.root.update_idletasks()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        px, py = self.root.winfo_x(), self.root.winfo_y()
        d.geometry(f"{width}x{height}+{px+(pw-width)//2}+{py+(ph-height)//2}")
        build_fn(d)
        d.grab_set(); d.wait_window()

    def _cfg_generic(self, name):
        self._cfg_window(name, 350, 200, lambda d: (
            ctk.CTkLabel(d, text=name, font=FONT_H2, text_color=TEXT).pack(pady=20),
            ctk.CTkLabel(d, text="Config em breve...", font=FONT_SMALL, text_color=TEXT3).pack()
        ))

    def _cfg_attack(self, name):
        if not hasattr(self, "_attack_config"):
            self._attack_config = {"keys":["1","2","3","4","5"],"speed":150,"target_list":[],
                                   "unstuck":{"enabled":False,"timeout":10},"spot":{"enabled":False,"distance":20}}
        cfg = self._attack_config
        def build(d):
            inner = ctk.CTkScrollableFrame(d, fg_color="transparent"); inner.pack(fill="both", expand=True, padx=12, pady=8)
            ctk.CTkLabel(inner, text="Attack", font=FONT_H3, text_color=TEXT).pack(anchor="w")
            ctk.CTkFrame(inner, height=1, fg_color="#1A2540").pack(fill="x", pady=4)
            # Skills
            ctk.CTkLabel(inner, text="Skills", font=FONT_SMALL, text_color=TEXT2).pack(anchor="w")
            sv = []; sr = ctk.CTkFrame(inner, fg_color="transparent"); sr.pack(fill="x", pady=2)
            for i in range(5):
                r = ctk.CTkFrame(sr, fg_color="transparent"); r.pack(fill="x", pady=1)
                ctk.CTkLabel(r, text=f"Skill {i+1}:", width=55, font=FONT_SMALL).pack(side="left")
                v = tk.StringVar(value=cfg["keys"][i] if i<len(cfg["keys"]) else "")
                ctk.CTkEntry(r, textvariable=v, width=50, font=FONT_SMALL).pack(side="left", padx=4); sv.append(v)
            # Speed
            ctk.CTkLabel(inner, text="Speed", font=FONT_SMALL, text_color=TEXT2).pack(anchor="w", pady=(6,2))
            sp = tk.StringVar(value=f"{cfg['speed']}ms")
            ctk.CTkComboBox(inner, values=["50ms","100ms","150ms","200ms","250ms"], variable=sp, width=120, font=FONT_SMALL).pack(anchor="w")
            # Target List
            ctk.CTkLabel(inner, text="Target List", font=FONT_SMALL, text_color=TEXT2).pack(anchor="w", pady=(6,2))
            tl = cfg.setdefault("target_list",[])
            tr = ctk.CTkFrame(inner, fg_color="transparent"); tr.pack(fill="x")
            mode = tk.StringVar(value="attack")
            ctk.CTkComboBox(tr, values=["attack","ignore"], variable=mode, width=65, font=FONT_SMALL).pack(side="left")
            ctk.CTkButton(tr, text="Capture", width=60, font=FONT_SMALL, command=lambda: self._capture_target(tl,mode,inner)).pack(side="left", padx=4)
            ctk.CTkButton(tr, text="Clear", width=50, font=FONT_SMALL, fg_color="transparent", border_width=1,
                         command=lambda: (tl.clear(), build(d))).pack(side="left", padx=4)
            for item in tl:
                r = ctk.CTkFrame(inner, fg_color="transparent"); r.pack(fill="x", pady=1)
                c = GREEN if item["mode"]=="attack" else RED
                ctk.CTkLabel(r, text=f"[{item['mode'][:3].upper()}]", width=40, font=FONT_SMALL, text_color=c).pack(side="left")
                ctk.CTkLabel(r, text=item["name"], font=FONT_SMALL).pack(side="left", fill="x", expand=True)
                ctk.CTkButton(r, text="X", width=20, height=18, font=ctk.CTkFont(size=9), fg_color="transparent", border_width=1,
                             command=lambda i=item: (tl.remove(i), build(d))).pack(side="right")
            # Unstuck
            us = cfg.setdefault("unstuck",{"enabled":False,"timeout":10})
            ctk.CTkLabel(inner, text="Unstuck", font=FONT_SMALL, text_color=TEXT2).pack(anchor="w", pady=(6,2))
            ur = ctk.CTkFrame(inner, fg_color="transparent"); ur.pack(fill="x")
            ue = ctk.BooleanVar(value=us.get("enabled",False))
            ctk.CTkCheckBox(ur, text="Enable", variable=ue, font=FONT_SMALL).pack(side="left")
            ctk.CTkLabel(ur, text="Timeout:", font=FONT_SMALL).pack(side="left", padx=4)
            ut = tk.IntVar(value=us.get("timeout",10))
            ctk.CTkEntry(ur, textvariable=ut, width=40, font=FONT_SMALL).pack(side="left", padx=2)
            ctk.CTkLabel(ur, text="s", font=FONT_SMALL).pack(side="left")
            # Spot
            spot = cfg.setdefault("spot",{"enabled":False,"distance":20})
            ctk.CTkLabel(inner, text="Spot Area", font=FONT_SMALL, text_color=TEXT2).pack(anchor="w", pady=(6,2))
            sr2 = ctk.CTkFrame(inner, fg_color="transparent"); sr2.pack(fill="x")
            se = ctk.BooleanVar(value=spot.get("enabled",False))
            ctk.CTkCheckBox(sr2, text="Enable", variable=se, font=FONT_SMALL).pack(side="left")
            ctk.CTkLabel(sr2, text="Dist:", font=FONT_SMALL).pack(side="left", padx=4)
            sd = tk.IntVar(value=spot.get("distance",20))
            ctk.CTkEntry(sr2, textvariable=sd, width=40, font=FONT_SMALL).pack(side="left", padx=2)
            # Save
            ctk.CTkButton(inner, text="Save", font=FONT_SMALL, width=80,
                         command=lambda: self._save_attack(sv,sp,ue,ut,se,sd,d)).pack(pady=(12,4))
        self._cfg_window("Attack", 420, 550, build)

    def _capture_target(self, tl, mode, parent):
        sessions = self.controller.get_sessions()
        w = self._selected_window
        if not w: return
        s = sessions.get(w)
        if not s or not s.get("pid"): return
        try:
            mr = MemoryReader(s["pid"]); name = mr.target_name; mr.close()
            if name and not any(t["name"]==name for t in tl):
                tl.append({"name":name,"mode":mode.get()})
        except: pass

    def _save_attack(self, sv, sp, ue, ut, se, sd, d):
        cfg = self._attack_config
        cfg["keys"]=[v.get().strip() for v in sv]
        cfg["speed"]=int(sp.get().replace("ms",""))
        cfg["unstuck"]={"enabled":ue.get(),"timeout":ut.get()}
        cfg["spot"]={"enabled":se.get(),"distance":sd.get()}
        d.destroy()

    def _cfg_potion(self, name):
        if not hasattr(self, "_potion_config"):
            self._potion_config = {"hp_potion":{"key":"2","enabled":True,"threshold":55},
                                   "mana_potion":{"key":"3","enabled":False,"threshold":40},
                                   "battle_hp":{"key":"4","enabled":False,"threshold":35},
                                   "battle_mana":{"key":"5","enabled":False,"threshold":25}}
        cfg = self._potion_config
        def build(d):
            inner = ctk.CTkScrollableFrame(d, fg_color="transparent"); inner.pack(fill="both", expand=True, padx=12, pady=8)
            ctk.CTkLabel(inner, text="Potion", font=FONT_H3, text_color=TEXT).pack(anchor="w")
            ctk.CTkFrame(inner, height=1, fg_color="#1A2540").pack(fill="x", pady=4)
            pv = {}
            for k, lb in [("hp_potion","HP"),("mana_potion","Mana"),("battle_hp","Battle HP"),("battle_mana","Battle Mana")]:
                it = cfg.setdefault(k,{"key":"","enabled":False,"threshold":50})
                r = ctk.CTkFrame(inner, fg_color="transparent"); r.pack(fill="x", pady=2)
                en = ctk.BooleanVar(value=it.get("enabled",False))
                ctk.CTkCheckBox(r, text="", variable=en, width=20).pack(side="left")
                ctk.CTkLabel(r, text=lb, width=75, font=FONT_SMALL).pack(side="left", padx=2)
                ctk.CTkLabel(r, text="Key:", font=FONT_SMALL).pack(side="left")
                kv = tk.StringVar(value=it.get("key",""))
                ctk.CTkEntry(r, textvariable=kv, width=40, font=FONT_SMALL).pack(side="left", padx=2)
                ctk.CTkLabel(r, text="HP<%", font=FONT_SMALL).pack(side="left", padx=4)
                tv = tk.IntVar(value=it.get("threshold",50))
                ctk.CTkEntry(r, textvariable=tv, width=35, font=FONT_SMALL).pack(side="left", padx=2)
                pv[k] = (en, kv, tv)
            ctk.CTkButton(inner, text="Save", font=FONT_SMALL, width=80,
                         command=lambda: self._save_potion(pv, d)).pack(pady=(12,4))
        self._cfg_window("Potion", 400, 350, build)

    def _save_potion(self, pv, d):
        for k, (en, kv, tv) in pv.items():
            self._potion_config[k] = {"key":kv.get().strip(),"enabled":en.get(),"threshold":tv.get()}
        d.destroy()

    def _cfg_pet(self, name):
        if not hasattr(self, "_pet_config"):
            self._pet_config = {"pet_key":"7","food_key":"3","interval_min":30}
        cfg = self._pet_config
        def build(d):
            inner = ctk.CTkFrame(d, fg_color="transparent"); inner.pack(fill="both", expand=True, padx=12, pady=12)
            ctk.CTkLabel(inner, text="Pet", font=FONT_H3, text_color=TEXT).pack(anchor="w")
            ctk.CTkFrame(inner, height=1, fg_color="#1A2540").pack(fill="x", pady=4)
            for lb, k, dv in [("Pet Key:","pet_key","7"),("Food Key:","food_key","3"),("Interval (min):","interval_min","30")]:
                r = ctk.CTkFrame(inner, fg_color="transparent"); r.pack(fill="x", pady=3)
                ctk.CTkLabel(r, text=lb, width=100, font=FONT_SMALL).pack(side="left")
                v = tk.StringVar(value=str(cfg.get(k,dv)))
                ctk.CTkEntry(r, textvariable=v, width=70, font=FONT_SMALL).pack(side="left", padx=4)
                setattr(inner, f"_pv_{k}", v)
            ctk.CTkButton(inner, text="Save", font=FONT_SMALL, width=80,
                         command=lambda: self._save_pet(inner, d)).pack(pady=(12,4))
        self._cfg_window("Pet", 320, 250, build)

    def _save_pet(self, inner, d):
        self._pet_config = {"pet_key": getattr(inner,"_pv_pet_key").get().strip(),
                           "food_key": getattr(inner,"_pv_food_key").get().strip(),
                           "interval_min": int(getattr(inner,"_pv_interval_min").get() or 30)}
        d.destroy()

    def _cfg_buff(self, name):
        if not hasattr(self, "_buff_config"):
            self._buff_config = {"skills":[{"key":"4","enabled":True},{"key":"5","enabled":False},{"key":"6","enabled":False}],
                                 "self_buff":{"enabled":False,"interval_min":15}}
        cfg = self._buff_config
        def build(d):
            inner = ctk.CTkFrame(d, fg_color="transparent"); inner.pack(fill="both", expand=True, padx=12, pady=12)
            ctk.CTkLabel(inner, text="Buff", font=FONT_H3, text_color=TEXT).pack(anchor="w")
            ctk.CTkFrame(inner, height=1, fg_color="#1A2540").pack(fill="x", pady=4)
            skills = cfg.setdefault("skills",[{"key":"4","enabled":True},{"key":"5","enabled":False},{"key":"6","enabled":False}])
            while len(skills)<3: skills.append({"key":"","enabled":False})
            sv = []
            for i in range(3):
                sk = skills[i]
                r = ctk.CTkFrame(inner, fg_color="transparent"); r.pack(fill="x", pady=2)
                en = ctk.BooleanVar(value=sk.get("enabled",False))
                ctk.CTkCheckBox(r, text="", variable=en, width=20).pack(side="left")
                ctk.CTkLabel(r, text=f"Buff {i+1}:", width=50, font=FONT_SMALL).pack(side="left", padx=2)
                kv = tk.StringVar(value=sk.get("key",""))
                ctk.CTkEntry(r, textvariable=kv, width=50, font=FONT_SMALL).pack(side="left", padx=2); sv.append((en,kv))
            sb = cfg.setdefault("self_buff",{"enabled":False,"interval_min":15})
            ctk.CTkLabel(inner, text="Self Buff", font=FONT_SMALL, text_color=TEXT2).pack(anchor="w", pady=(8,2))
            sr = ctk.CTkFrame(inner, fg_color="transparent"); sr.pack(fill="x")
            sbe = ctk.BooleanVar(value=sb.get("enabled",False))
            ctk.CTkCheckBox(sr, text="Enable", variable=sbe, font=FONT_SMALL).pack(side="left")
            ctk.CTkLabel(sr, text="Every:", font=FONT_SMALL).pack(side="left", padx=4)
            sbi = tk.IntVar(value=sb.get("interval_min",15))
            ctk.CTkEntry(sr, textvariable=sbi, width=40, font=FONT_SMALL).pack(side="left", padx=2)
            ctk.CTkLabel(sr, text="min", font=FONT_SMALL).pack(side="left")
            ctk.CTkButton(inner, text="Save", font=FONT_SMALL, width=80,
                         command=lambda: self._save_buff(sv,sbe,sbi,d)).pack(pady=(12,4))
        self._cfg_window("Buff", 350, 320, build)

    def _save_buff(self, sv, sbe, sbi, d):
        self._buff_config["skills"] = [{"key":v[1].get().strip(),"enabled":v[0].get()} for v in sv]
        self._buff_config["self_buff"] = {"enabled":sbe.get(),"interval_min":sbi.get()}
        d.destroy()

    def _cfg_bc(self, name):
        """
        Configuração do Bewitcher Cave, em 4 abas.

        O BC é auto-contido: tem as próprias skills, teclas E POÇÕES.
        Por isso o diálogo repete campos que existem em Attack, Potion e
        Fairy -- é intencional, não duplicação por descuido.
        """
        label = self._selected_window

        if not label:
            messagebox.showinfo(
                "BC",
                "Selecione um client antes de configurar o BC.\n\n"
                "A configuração é por conta: numa dupla, um personagem "
                "roda a BC e o outro é o reseter.",
            )
            return

        cfg = self._bc_config_da_conta(label)
        campos = {}

        def grupo(pai, titulo):
            caixa = ctk.CTkFrame(pai, fg_color="transparent", border_width=1,
                                 border_color="#1A2540", corner_radius=6)
            caixa.pack(fill="x", pady=(4, 8), padx=2)
            ctk.CTkLabel(caixa, text=titulo, font=ctk.CTkFont(size=10),
                         text_color=TEXT2).pack(anchor="w", padx=8, pady=(4, 0))
            interno = ctk.CTkFrame(caixa, fg_color="transparent")
            interno.pack(fill="x", padx=8, pady=(2, 8))
            return interno

        def texto(pai, rotulo, chave, largura=70):
            r = ctk.CTkFrame(pai, fg_color="transparent"); r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=rotulo, width=150, font=FONT_SMALL,
                         anchor="e").pack(side="left", padx=(0, 8))
            v = tk.StringVar(value=str(cfg.get(chave, "")))
            ctk.CTkEntry(r, textvariable=v, width=largura, font=FONT_SMALL).pack(side="left")
            campos[chave] = v

        def tecla(pai, rotulo, chave):
            """Campo de atalho. Vazio aparece como 'unset', como na referência."""
            r = ctk.CTkFrame(pai, fg_color="transparent"); r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=rotulo, width=105, font=FONT_SMALL,
                         anchor="e").pack(side="left", padx=(0, 6))
            atual = cfg.get(chave, "")
            v = tk.StringVar(value=atual if atual else "unset")
            ctk.CTkEntry(r, textvariable=v, width=70, font=FONT_SMALL,
                         justify="center").pack(side="left")
            campos[chave] = v

        def marcar(pai, rotulo, chave):
            v = ctk.BooleanVar(value=bool(cfg.get(chave)))
            ctk.CTkCheckBox(pai, text=rotulo, variable=v,
                            font=FONT_SMALL).pack(anchor="w", pady=1)
            campos[chave] = v

        def deslizar(pai, rotulo, chave, cor):
            """Limiar de poção: barra colorida + slider, como na referência."""
            r = ctk.CTkFrame(pai, fg_color="transparent"); r.pack(fill="x", pady=4)
            v = tk.IntVar(value=int(cfg.get(chave, 30)))
            etiqueta = ctk.CTkLabel(r, text=f"{rotulo}: {v.get()}%", width=110,
                                    font=FONT_SMALL, fg_color=cor, corner_radius=4)
            etiqueta.pack(side="left", padx=(0, 10))
            ctk.CTkSlider(
                r, from_=0, to=100, variable=v, width=150,
                command=lambda _x, lb=etiqueta, var=v, rt=rotulo: lb.configure(
                    text=f"{rt}: {int(var.get())}%"
                ),
            ).pack(side="left")
            campos[chave] = v

        # Papel atual do personagem. Fica fora do build() porque o
        # formulario e RECONSTRUIDO ao alternar: o reseter usa uma tela
        # completamente diferente, nao a mesma com campos escondidos.
        estado = {"reseter": bool(cfg.get("reseter"))}

        def build(d):
            for w in d.winfo_children():
                w.destroy()
            campos.clear()

            sessoes = self.controller.get_sessions()
            eu = sessoes.get(label, {}).get("display", label)

            ctk.CTkLabel(d, text=f"Configurando: {eu}", font=FONT_SMALL,
                         text_color=BLUE).pack(anchor="w", padx=14, pady=(8, 0))

            def bloco_team(pai):
                """
                Vinculo da dupla -- a unica parte que os dois papeis
                compartilham.
                """
                g = grupo(pai, "Team")
                texto(g, "Member Name", "member_name", largura=160)

                linha = ctk.CTkFrame(g, fg_color="transparent")
                linha.pack(fill="x", pady=2)

                v_reseter = ctk.BooleanVar(value=estado["reseter"])
                v_leave = ctk.BooleanVar(value=bool(cfg.get("leave_team", True)))
                campos["reseter"] = v_reseter
                campos["leave_team"] = v_leave

                def alternar():
                    estado["reseter"] = v_reseter.get()
                    build(d)

                ctk.CTkCheckBox(linha, text="Reseter", variable=v_reseter,
                                font=FONT_SMALL,
                                command=alternar).pack(side="left", padx=(0, 12))
                ctk.CTkCheckBox(linha, text="Leave Team", variable=v_leave,
                                font=FONT_SMALL).pack(side="left")

            # =================================================
            # Reseter: so o vinculo. Sem skills, rota nem pocoes.
            # =================================================
            if estado["reseter"]:
                painel = ctk.CTkFrame(d, fg_color="transparent")
                painel.pack(fill="both", expand=True, padx=8, pady=4)

                bloco_team(painel)

                ctk.CTkLabel(
                    painel,
                    text=("Este personagem so entra e sai do team.\n\n"
                          "E a formacao do grupo que reseta a cave e devolve\n"
                          "o boss -- por isso ele nao precisa de skills, rota\n"
                          "nem pocoes.\n\n"
                          "Em 'Member Name' vai o nome do personagem que FAZ\n"
                          "a BC, e la no BC dele o 'Member Name' tem que ser\n"
                          "este aqui."),
                    font=ctk.CTkFont(size=10), text_color=TEXT3, justify="left",
                ).pack(anchor="w", padx=10, pady=(6, 0))

                ctk.CTkButton(d, text="Save", font=FONT_SMALL, width=100,
                              command=lambda: self._save_bc(campos, label, d)).pack(pady=8)
                return

            # =================================================
            # Runner: o ciclo completo, nas 4 abas.
            # =================================================
            abas = ctk.CTkTabview(d, fg_color="transparent", height=440)
            abas.pack(fill="both", expand=True, padx=8, pady=(4, 0))
            for titulo in ("Main", "Shortcuts", "Potions", "Stats"):
                abas.add(titulo)

            # ---------------- Main ----------------
            main = ctk.CTkScrollableFrame(abas.tab("Main"), fg_color="transparent")
            main.pack(fill="both", expand=True)

            bloco_team(main)

            g = grupo(main, "General")
            texto(g, "Return to Stone every (runs)", "runs_por_ciclo", largura=50)
            texto(g, "Initial Selling Slot", "slot_inicial_venda", largura=50)
            marcar(g, "Buy Return Charm after selling", "comprar_return_charm")
            marcar(g, "Get Treasure Box", "pegar_treasure_box")
            marcar(g, "Manual Pick (clica no corpo do boss)", "manual_pick")

            g = grupo(main, "Route")
            v_rota = tk.StringVar(value=cfg.get("rota", "standard"))
            ctk.CTkRadioButton(g, text="Standard (direto pro boss)", value="standard",
                               variable=v_rota, font=FONT_SMALL).pack(anchor="w", pady=1)
            ctk.CTkRadioButton(g, text="Safe (mata as Gun Witches antes)", value="safe",
                               variable=v_rota, font=FONT_SMALL).pack(anchor="w", pady=1)
            campos["rota"] = v_rota
            marcar(g, "Lure Powerfuls (mobs do corredor)", "lure_powerfuls")
            marcar(g, "Heal Before Second Phase", "heal_antes_segunda_fase")

            g = grupo(main, "Misc")
            texto(g, "Usar AOE ate mana (%)", "aoe_ate_mana", largura=50)

            g = grupo(main, "Etapas do ciclo")
            marcar(g, "Comprar pocao antes de ir", "comprar_pot")
            marcar(g, "Vender ao voltar", "vender")
            marcar(g, "Abrir as bags de courage", "usar_courage")
            marcar(g, "Repetir o ciclo indefinidamente", "repetir_ciclo")

            # ---------------- Shortcuts ----------------
            atalhos = ctk.CTkScrollableFrame(abas.tab("Shortcuts"), fg_color="transparent")
            atalhos.pack(fill="both", expand=True)

            g = grupo(atalhos, "Skills")
            v_ataques = []
            atuais = cfg.get("attack_keys", [])
            for i in range(3):
                r = ctk.CTkFrame(g, fg_color="transparent"); r.pack(fill="x", pady=2)
                ctk.CTkLabel(r, text=f"Attack {i+1}", width=105, font=FONT_SMALL,
                             anchor="e").pack(side="left", padx=(0, 6))
                v = tk.StringVar(value=atuais[i] if i < len(atuais) else "unset")
                ctk.CTkEntry(r, textvariable=v, width=70, font=FONT_SMALL,
                             justify="center").pack(side="left")
                v_ataques.append(v)
            campos["attack_keys"] = v_ataques
            tecla(g, "Attack AOE", "aoe_key")
            tecla(g, "Super Skill", "super_skill_key")
            tecla(g, "Buff", "buff_key")
            tecla(g, "Break Soul", "break_soul_key")
            tecla(g, "Healing Spell", "healing_spell_key")

            g = grupo(atalhos, "General")
            tecla(g, "Mount", "mount_key")
            tecla(g, "Speed Skill", "speed_skill_key")
            tecla(g, "Summon Pet", "summon_pet_key")
            tecla(g, "Pet Food", "pet_food_key")
            tecla(g, "Stone Charm", "stone_charm_key")
            tecla(g, "Inventario", "inventory_key")
            tecla(g, "Painel de team", "team_key")

            g = grupo(atalhos, "Potions")
            tecla(g, "HP", "hp_potion_key")
            tecla(g, "Battle HP", "battle_hp_key")
            tecla(g, "Mana", "mana_potion_key")
            tecla(g, "Battle Mana", "battle_mana_key")

            ctk.CTkLabel(
                atalhos, text="Deixe 'unset' pra nao usar o item/skill.",
                font=ctk.CTkFont(size=10), text_color=TEXT3,
            ).pack(anchor="w", pady=(2, 0))

            # ---------------- Potions ----------------
            pocoes = ctk.CTkScrollableFrame(abas.tab("Potions"), fg_color="transparent")
            pocoes.pack(fill="both", expand=True)

            ctk.CTkLabel(
                pocoes,
                text="O BC cuida da propria vida: nao precisa dos\ncards Potion nem Fairy ligados.",
                font=ctk.CTkFont(size=10), text_color=TEXT3, justify="left",
            ).pack(anchor="w", pady=(0, 6))

            g = grupo(pocoes, "Potions")
            deslizar(g, "HP", "hp_potion_pct", "#7F1D1D")
            deslizar(g, "MP", "mana_potion_pct", "#1E3A8A")

            g = grupo(pocoes, "Battle Potions")
            deslizar(g, "HP", "battle_hp_pct", "#7F1D1D")
            deslizar(g, "MP", "battle_mana_pct", "#1E3A8A")

            g = grupo(pocoes, "Fairy self-heal -> Healing Spell")
            deslizar(g, "HP", "fairy_heal_pct", "#7F1D1D")

            # ---------------- Stats ----------------
            estat = ctk.CTkScrollableFrame(abas.tab("Stats"), fg_color="transparent")
            estat.pack(fill="both", expand=True)
            self._build_bc_stats(estat, campos, cfg)

            ctk.CTkButton(d, text="Save", font=FONT_SMALL, width=100,
                          command=lambda: self._save_bc(campos, label, d)).pack(pady=8)

        self._cfg_window("BC", 470, 590, build)

    def _build_bc_stats(self, pai, campos, cfg):
        """
        Aba Stats. Le os contadores do script vivo da conta selecionada;
        sem sessao rodando, mostra zeros.
        """
        from src.services.bot.scripts.bc import BCStats

        stats = self._bc_stats_da_sessao()

        if stats is None:
            ctk.CTkLabel(pai, text="Nenhuma sessao com BC rodando.",
                         font=FONT_SMALL, text_color=TEXT3).pack(pady=(0, 6))
            stats = BCStats()

        def caixa(rotulo, valor):
            f = ctk.CTkFrame(pai, fg_color=CARD, corner_radius=6,
                             border_width=1, border_color="#1A2540")
            f.pack(fill="x", pady=3, padx=2)
            ctk.CTkLabel(f, text=rotulo, font=ctk.CTkFont(size=10),
                         text_color=TEXT3).pack(anchor="w", padx=8, pady=(4, 0))
            ctk.CTkLabel(f, text=str(valor), font=FONT_TEXT,
                         text_color=TEXT).pack(anchor="w", padx=8, pady=(0, 6))

        caixa("Runs", stats.runs)
        caixa("Success", stats.sucessos)
        caixa("Fail", stats.falhas)
        caixa("Run Time", BCStats.formatar(stats.run_atual))
        caixa("Last Run Time", BCStats.formatar(stats.tempo_ultima_run))
        caixa("Total Running Time", BCStats.formatar_longo(stats.tempo_total))
        caixa("Courage Badge", stats.courage)

        ctk.CTkButton(pai, text="Reset Stats", font=FONT_SMALL, width=110,
                      fg_color="transparent", border_width=1, border_color=TEXT3,
                      command=self._reset_bc_stats).pack(pady=(8, 4))

        v = ctk.BooleanVar(value=bool(cfg.get("auto_reset_stats", True)))
        ctk.CTkCheckBox(pai, text="Auto Reset Stats ao iniciar o bot",
                        variable=v, font=FONT_SMALL).pack(anchor="w")
        campos["auto_reset_stats"] = v

    def _bc_stats_da_sessao(self):
        """Contadores do BC da conta selecionada, ou None se nao houver."""
        engine = self.controller.get_bot_engine(self._selected_window)
        if engine is None:
            return None
        for script in engine.scripts:
            if getattr(script, "name", "") == "BC":
                return getattr(script, "stats", None)
        return None

    def _reset_bc_stats(self):
        stats = self._bc_stats_da_sessao()
        if stats is None:
            messagebox.showinfo("Stats", "Nenhuma sessao com BC rodando.")
            return
        stats.zerar()
        logger.info("Stats do BC zerados")

    def _save_bc(self, campos, label, d):
        cfg = self._bc_config_da_conta(label)

        def limpar_tecla(valor: str) -> str:
            """'unset' e vazio significam a mesma coisa: sem atalho."""
            valor = (valor or "").strip()
            return "" if valor.lower() == "unset" else valor

        # O formulario do reseter tem SO o bloco Team, entao todo campo
        # daqui pra baixo e lido apenas se estiver presente. Sem isso,
        # salvar como reseter estouraria KeyError.
        if "attack_keys" in campos:
            ataques = [limpar_tecla(v.get()) for v in campos["attack_keys"]]
            cfg["attack_keys"] = [a for a in ataques if a] or list(
                BC_DEFAULT_CONFIG["attack_keys"]
            )

        for chave in ("aoe_key", "super_skill_key", "buff_key", "break_soul_key",
                      "healing_spell_key", "mount_key", "speed_skill_key",
                      "summon_pet_key", "pet_food_key", "stone_charm_key",
                      "inventory_key", "team_key", "hp_potion_key",
                      "mana_potion_key", "battle_hp_key", "battle_mana_key"):
            if chave in campos:
                cfg[chave] = limpar_tecla(campos[chave].get())

        cfg["member_name"] = campos["member_name"].get().strip()

        if "rota" in campos:
            cfg["rota"] = campos["rota"].get()

        for chave in ("reseter", "leave_team", "comprar_return_charm",
                      "pegar_treasure_box", "manual_pick", "lure_powerfuls",
                      "heal_antes_segunda_fase", "comprar_pot", "vender",
                      "usar_courage", "repetir_ciclo", "auto_reset_stats"):
            if chave in campos:
                cfg[chave] = bool(campos[chave].get())

        for chave in ("hp_potion_pct", "mana_potion_pct", "battle_hp_pct",
                      "battle_mana_pct", "fairy_heal_pct"):
            if chave in campos:
                cfg[chave] = int(campos[chave].get())

        for chave, conversor, minimo in (
            ("runs_por_ciclo", int, 1),
            ("slot_inicial_venda", int, 1),
            ("aoe_ate_mana", int, 0),
        ):
            if chave not in campos:
                continue
            try:
                cfg[chave] = max(minimo, conversor(str(campos[chave].get()).strip()))
            except (TypeError, ValueError):
                # Campo com lixo digitado: mantem o valor anterior em vez
                # de gravar algo que quebraria o roteiro.
                logger.warning("Valor invalido para '%s'; mantendo o anterior", chave)

        if cfg["reseter"]:
            logger.info(
                "Config do BC de '%s' salva: RESETER, parceiro '%s'",
                label, cfg["member_name"],
            )
        else:
            logger.info(
                "Config do BC de '%s' salva: rota=%s, %s run(s) por ciclo",
                label, cfg["rota"], cfg["runs_por_ciclo"],
            )

        aviso = self._conferir_vinculo_bc(label, cfg)
        d.destroy()

        if aviso:
            messagebox.showwarning("Vínculo do BC", aviso)

    def _conferir_vinculo_bc(self, label: str, cfg: dict) -> str:
        """
        Confere o vínculo da dupla e devolve um aviso, ou "" se estiver ok.

        A dupla se reconhece por nomes CRUZADOS: o runner aponta pro
        reseter e o reseter aponta de volta pro runner. Sem isso não dá
        pra saber quem forma par com quem quando há vários clients
        abertos.

        Só avisa -- não impede de salvar. O parceiro pode simplesmente
        ainda não estar logado.
        """
        parceiro_nome = (cfg.get("member_name") or "").strip()

        if not parceiro_nome:
            return ("Sem 'Member Name' não há dupla: o BC precisa de um "
                    "parceiro pra formar e desfazer o team, que é o que "
                    "reseta a cave.")

        sessoes = self.controller.get_sessions()
        eu = sessoes.get(label, {}).get("display", label)

        parceiro_label = next(
            (l for l, s in sessoes.items()
             if s.get("display", l).strip().lower() == parceiro_nome.lower()),
            None,
        )

        if parceiro_label is None:
            return (f"'{parceiro_nome}' não está logado agora. O vínculo só "
                    f"pode ser conferido com os dois clients abertos.")

        cfg_parceiro = self._bc_configs.get(parceiro_label)

        if cfg_parceiro is None:
            return f"'{parceiro_nome}' ainda não tem o BC configurado."

        problemas = []

        if bool(cfg_parceiro.get("reseter")) == bool(cfg.get("reseter")):
            papel = "reseter" if cfg.get("reseter") else "runner"
            problemas.append(
                f"os dois estão marcados como {papel} — um tem que ser o "
                f"reseter e o outro não."
            )

        nome_de_volta = (cfg_parceiro.get("member_name") or "").strip()
        if nome_de_volta.lower() != eu.lower():
            mostrado = nome_de_volta or "(vazio)"
            problemas.append(
                f"'{parceiro_nome}' aponta para '{mostrado}' em vez de '{eu}'."
            )

        if problemas:
            return "Vínculo incompleto: " + " E ".join(problemas)

        return ""

    # ============================================================
    # LOGIN / WINDOWS / PERSISTENCE / POLLING / BOT ENGINE
    # ============================================================
    def _open_login(self):
        if not hasattr(self, "_login_win") or not self._login_win or not self._login_win.winfo_exists():
            self._login_win = self._create_login_win()
        else: self._login_win.deiconify(); self._login_win.lift(); self._login_win.focus_force()

    def _create_login_win(self):
        d = ctk.CTkToplevel(self.root); d.title("Login — Contas"); d.geometry("620x480")
        d.configure(fg_color=BG); d.resizable(False, False); d.transient(self.root)
        d.protocol("WM_DELETE_WINDOW", lambda: setattr(self, "_login_win", None) or d.destroy())
        self.root.update_idletasks(); pw,ph = self.root.winfo_width(), self.root.winfo_height()
        px,py = self.root.winfo_x(), self.root.winfo_y()
        d.geometry(f"620x480+{px+(pw-620)//2}+{py+(ph-480)//2}")

        f = ctk.CTkFrame(d, fg_color="transparent"); f.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(f, text="Contas", font=FONT_H3, text_color=TEXT).pack(anchor="w")
        ctk.CTkFrame(f, height=1, fg_color="#1A2540").pack(fill="x", pady=(4, 10))

        # Larguras de coluna compartilhadas entre cabeçalho e linhas,
        # pra tudo alinhar certinho.
        COL_CHECK, COL_LABEL, COL_SERVER, COL_USER, COL_SLOT = 26, 110, 120, 130, 70

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", padx=4)
        ctk.CTkLabel(header, text="", width=COL_CHECK).pack(side="left")
        for text, w in (("APELIDO", COL_LABEL), ("SERVIDOR", COL_SERVER),
                        ("USUÁRIO", COL_USER), ("PERSONAGEM", COL_SLOT)):
            ctk.CTkLabel(header, text=text, width=w, font=FONT_SMALL, text_color=TEXT3,
                        anchor="w").pack(side="left", padx=4)

        table = ctk.CTkScrollableFrame(f, fg_color="transparent", height=300)
        table.pack(fill="both", expand=True, pady=(6, 4))

        btn_row = ctk.CTkFrame(f, fg_color="transparent"); btn_row.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(btn_row, text="+ Add Account", font=FONT_SMALL, fg_color=GREEN,
                     hover_color="#1B9E4B", command=lambda: self._add_account(table)).pack(side="left")

        def refresh():
            for w in table.winfo_children(): w.destroy()
            if not hasattr(self, "_account_index"): self._account_index = {}
            if not hasattr(self, "_login_vars"): self._login_vars = {}
            if not self.accounts:
                ctk.CTkLabel(table, text="Nenhuma conta cadastrada ainda", font=FONT_SMALL,
                            text_color=TEXT3).pack(expand=True, pady=40)
                return
            for idx, acc in enumerate(self.accounts):
                self._account_index[acc.label] = idx
                if acc.label not in self._login_vars: self._login_vars[acc.label] = ctk.BooleanVar(value=False)
                var = self._login_vars[acc.label]

                row = ctk.CTkFrame(table, fg_color=CARD, corner_radius=6,
                                   border_width=1, border_color="#1A2540")
                row.pack(fill="x", pady=3)
                inner = ctk.CTkFrame(row, fg_color="transparent")
                inner.pack(fill="x", padx=4, pady=6)

                ctk.CTkCheckBox(inner, text="", variable=var, width=COL_CHECK,
                               command=lambda l=acc.label: self._on_login_toggle(l)).pack(side="left")
                ctk.CTkLabel(inner, text=acc.label, width=COL_LABEL, font=FONT_SMALL,
                            text_color=TEXT, anchor="w").pack(side="left", padx=4)
                ctk.CTkLabel(inner, text=acc.server_name or "—", width=COL_SERVER, font=FONT_SMALL,
                            text_color=TEXT2, anchor="w").pack(side="left", padx=4)
                ctk.CTkLabel(inner, text=acc.username, width=COL_USER, font=FONT_SMALL,
                            text_color=TEXT2, anchor="w").pack(side="left", padx=4)
                ctk.CTkLabel(inner, text=acc.character_slot, width=COL_SLOT, font=FONT_SMALL,
                            text_color=TEXT2, anchor="w").pack(side="left", padx=4)

                ctk.CTkButton(inner, text="Remover", width=64, height=22, font=FONT_SMALL,
                             fg_color="transparent", border_width=1, border_color=RED,
                             text_color=RED, hover_color=HOVER,
                             command=lambda a=acc: self._remove_account(a, refresh)).pack(side="right", padx=(4, 0))
                ctk.CTkButton(inner, text="Editar", width=56, height=22, font=FONT_SMALL,
                             fg_color="transparent", border_width=1, border_color=TEXT3,
                             text_color=TEXT2, hover_color=HOVER,
                             command=lambda a=acc: self._edit_account(a, refresh)).pack(side="right")
        refresh()
        d._refresh = refresh
        return d

    def _add_account(self, table):
        dlg = AccountDialog(self.root, "Add Account")
        if dlg.result: self.accounts.append(dlg.result); save_accounts(self.accounts)
        if hasattr(self, "_login_win") and self._login_win and hasattr(self._login_win, "_refresh"):
            self._login_win._refresh()

    def _edit_account(self, acc, refresh):
        idx = self._account_index.get(acc.label, 0)
        dlg = AccountDialog(self.root, "Edit Account", self.accounts[idx])
        if dlg.result:
            old = acc.label; self.accounts[idx] = dlg.result; save_accounts(self.accounts)
            if dlg.result.label != old: self._stop_login_thread(old)
            refresh()
            if dlg.result.auto_login: self._start_login_thread(dlg.result.label)

    def _remove_account(self, acc, refresh):
        if not messagebox.askyesno("Remove", f"Remove {acc.label}?"): return
        self._stop_login_thread(acc.label)
        idx = self._account_index.get(acc.label)
        if idx is not None: del self.accounts[idx]
        save_accounts(self.accounts); refresh()

    def _on_login_toggle(self, label):
        if not hasattr(self, "_login_vars"): return
        var = self._login_vars.get(label)
        if var is None: return
        if var.get(): self._start_login_thread(label)
        else: self._stop_login_thread(label)

    def _open_config(self):
        if not hasattr(self, "_config_win") or not self._config_win or not self._config_win.winfo_exists():
            d = ctk.CTkToplevel(self.root); d.title("Settings"); d.geometry("500x200")
            d.configure(fg_color=BG); d.resizable(False, False); d.transient(self.root)
            d.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "_config_win", None), self._save_client_path(), d.destroy()))
            self.root.update_idletasks(); pw,ph = self.root.winfo_width(), self.root.winfo_height()
            px,py = self.root.winfo_x(), self.root.winfo_y()
            d.geometry(f"500x200+{px+(pw-500)//2}+{py+(ph-200)//2}")
            f = ctk.CTkFrame(d, fg_color="transparent"); f.pack(fill="both", expand=True, padx=16, pady=16)
            ctk.CTkLabel(f, text="Settings", font=FONT_H3, text_color=TEXT).pack(anchor="w", pady=(0,8))
            ctk.CTkFrame(f, height=1, fg_color="#1A2540").pack(fill="x", pady=4)
            r = ctk.CTkFrame(f, fg_color="transparent"); r.pack(fill="x", pady=4)
            ctk.CTkLabel(r, text="Client:", font=FONT_SMALL, width=60).pack(side="left")
            ctk.CTkEntry(r, textvariable=self._client_path, font=FONT_SMALL).pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkButton(r, text="Browse", font=FONT_SMALL, width=70, command=lambda: self._browse_client()).pack(side="left")
            self._config_win = d
        else: self._config_win.deiconify(); self._config_win.lift(); self._config_win.focus_force()

    def _browse_client(self):
        p = filedialog.askopenfilename(title="Select client", filetypes=[("Executables","*.exe;*.bat;*.cmd"),("All","*.*")])
        if p: self._client_path.set(p)

    def _show_pricing(self):
        d = ctk.CTkToplevel(self.root); d.title("Pricing"); d.configure(fg_color=BG)
        d.resizable(False,False); d.transient(self.root)
        self.root.update_idletasks(); pw,ph = self.root.winfo_width(), self.root.winfo_height()
        px,py = self.root.winfo_x(), self.root.winfo_y()
        d.geometry(f"360x320+{px+(pw-360)//2}+{py+(ph-320)//2}")
        f = ctk.CTkFrame(d, fg_color="transparent"); f.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(f, text="Plans", font=FONT_H3, text_color=TEXT).pack(pady=(0,12))
        for tier, color, items in [("Free",GREEN,["Login","Basic configs","1 account"]),
                                    ("Premium",BLUE,["Multi accounts","All scripts","Profiles","Priority updates"])]:
            ctk.CTkLabel(f, text=tier, font=ctk.CTkFont(weight="bold"), text_color=color).pack(anchor="w")
            for i in items: ctk.CTkLabel(f, text=f"  - {i}", font=FONT_SMALL, text_color=TEXT2).pack(anchor="w")
            ctk.CTkFrame(f, height=8, fg_color="transparent").pack()
        ctk.CTkLabel(f, text="Contact: contato@loginto.app", font=FONT_SMALL, text_color=TEXT3).pack(pady=(8,0))
        ctk.CTkButton(f, text="Close", command=d.destroy).pack(pady=(8,0))
        d.grab_set(); d.wait_window()

    def _show_help(self):
        d = ctk.CTkToplevel(self.root); d.title("Help"); d.configure(fg_color=BG)
        d.resizable(False,False); d.transient(self.root)
        self.root.update_idletasks(); pw,ph = self.root.winfo_width(), self.root.winfo_height()
        px,py = self.root.winfo_x(), self.root.winfo_y()
        d.geometry(f"300x200+{px+(pw-300)//2}+{py+(ph-200)//2}")
        f = ctk.CTkFrame(d, fg_color="transparent"); f.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(f, text="Auto Login TO", font=FONT_H3, text_color=TEXT).pack()
        ctk.CTkLabel(f, text="v0.3.0", font=FONT_SMALL, text_color=TEXT3).pack()
        ctk.CTkLabel(f, text="Automation for Talisman Online", font=FONT_SMALL, text_color=TEXT2).pack(pady=(8,0))
        ctk.CTkButton(f, text="Close", command=d.destroy).pack(pady=(12,0))
        d.grab_set(); d.wait_window()

    def _load_client_path(self):
        if not GUI_SETTINGS_FILE.exists(): return
        try:
            data = json.loads(GUI_SETTINGS_FILE.read_text(encoding="utf-8"))
            self._client_path.set(data.get("client_path", _DEFAULTS.client_path))
        except: pass

    def _save_client_path(self):
        try: GUI_SETTINGS_FILE.write_text(json.dumps({"client_path":self._client_path.get()}, indent=2, ensure_ascii=False), encoding="utf-8")
        except: pass

    def _on_close(self):
        self._save_client_path()
        for ev in list(self._stop_events.values()): ev.set()
        if hasattr(self, "_memory_readers"):
            for mr in self._memory_readers.values():
                try: mr.close()
                except: pass
        self.root.destroy()

    # ============================================================
    # POLLING
    # ============================================================
    def _poll_loop(self):
        sessions = self.controller.state.get_all_sessions()
        online = 0
        existing = set(self._client_cards.keys()); current = set(sessions.keys())
        for label in current - existing:
            s = sessions[label]; display = s.get("display", label)
            card = ctk.CTkFrame(self._clients_scroll, fg_color=CARD, corner_radius=8, border_width=1, border_color="#1A2540")
            card.pack(fill="x", pady=2, padx=2)
            hdr = ctk.CTkFrame(card, fg_color="transparent"); hdr.pack(fill="x", padx=8, pady=(6,0))
            name_lbl = ctk.CTkLabel(hdr, text=display, font=FONT_SMALL, text_color=TEXT); name_lbl.pack(side="left")
            dot = ctk.CTkLabel(hdr, text="\u25CF", font=ctk.CTkFont(size=8), text_color=TEXT3); dot.pack(side="right")
            hp_bar = ctk.CTkProgressBar(card, height=5, progress_color=GREEN); hp_bar.pack(fill="x", padx=8, pady=(2,0)); hp_bar.set(0)
            mp_bar = ctk.CTkProgressBar(card, height=5, progress_color=BLUE); mp_bar.pack(fill="x", padx=8, pady=2); mp_bar.set(0)
            self._client_cards[label] = {"frame":card,"dot":dot,"hp":hp_bar,"mp":mp_bar,"name_lbl":name_lbl}

            # Clique único: seleciona a conta (define qual conta os
            # cards de SCRIPTS à esquerda estão editando).
            # Duplo clique: traz a janela do jogo dessa conta pra frente.
            # Precisa bindar em todos os sub-widgets, não só no frame,
            # porque cliques em widgets filhos não propagam pro pai.
            for widget in (card, hdr, name_lbl, dot):
                widget.bind("<Button-1>", lambda e, l=label: self._select_client_card(l))
                widget.bind("<Double-Button-1>", lambda e, l=label: self._focus_client_window(l))

        for label in existing - current:
            c = self._client_cards.pop(label)
            c["frame"].destroy()

        if self._client_cards:
            for w in self._clients_scroll.winfo_children():
                if isinstance(w, ctk.CTkLabel): w.pack_forget(); break

        for label, info in sessions.items():
            cd = self._client_cards.get(label)
            if not cd: continue
            pid = info.get("pid")
            if pid:
                try:
                    mr = self._get_memory_reader(label, pid)
                    if mr:
                        cd["hp"].set(mr.hp_pct/100.0); cd["mp"].set(mr.mana_pct/100.0)
                        # Verde = script rodando, azul = online mas parado
                        cd["dot"].configure(text_color=GREEN if info.get("scripts_running") else BLUE)
                        online += 1
                except: pass

        self._ind_online.configure(text=f"{online} Online")
        scripts = sum(1 for v in self._widget_states.values() if v)
        self._ind_scripts.configure(text=f"{scripts} Scripts")
        self._refresh_bot_toggle_button()
        self.root.after(500, self._poll_loop)

    def _select_client_card(self, label: str):
        """
        Seleciona qual conta os cards de SCRIPTS (à esquerda) estão
        editando. Atualiza o destaque visual do card e o indicador de
        texto acima da lista de scripts.
        """
        # Remove destaque do card selecionado anteriormente
        prev = self._client_cards.get(self._selected_window)
        if prev:
            prev["frame"].configure(border_color="#1A2540", border_width=1)

        self._selected_window = label

        card = self._client_cards.get(label)
        if card:
            card["frame"].configure(border_color=BLUE, border_width=2)

        sessions = self.controller.get_sessions()
        display = sessions.get(label, {}).get("display", label)
        self._editing_label.configure(
            text=f"Editando: {display}", text_color=TEXT2
        )

        self._refresh_bot_toggle_button()

    def _on_session_event(self, label: str, **_ignored):
        """
        Chamado pelo EventBus quando uma sessão conecta/desconecta.
        """
        logger.debug("Sessão atualizada: %s", label)

    def _on_bot_state_event(self, label: str):
        """
        Chamado pelo EventBus quando um script liga/desliga (evento
        'bot.started'/'bot.stopped'). Pode vir de qualquer thread --
        só agenda a atualização real do widget na thread principal.
        """
        logger.debug("Estado dos scripts atualizado: %s", label)
        self.root.after(0, self._refresh_bot_toggle_button)

    def _has_enabled_scripts(self, label: str) -> bool:
        """
        Verdadeiro se ao menos um script está ligado (switch do card)
        para a conta indicada.
        """
        vars_for_label = self._feature_vars.get(label, {})
        return any(v.get() for v in vars_for_label.values())

    def _refresh_bot_toggle_button(self):
        """
        Atualiza o texto/estado do botão Start/Stop Scripts conforme
        a conta selecionada e se o motor de scripts dela já está
        rodando ou não.

        Enquanto rodando, o botão sempre fica clicável (pra permitir
        parar). Parado, só fica clicável se houver ao menos um script
        ligado -- não faz sentido "iniciar" sem nenhum script ativo.
        """

        label = self._selected_window

        if not label:
            self._bot_toggle_btn.configure(state="disabled", text="Start Scripts", fg_color=GREEN)
            return

        running = self.controller.is_running(label)

        if running:
            self._bot_toggle_btn.configure(state="normal", text="Stop Scripts", fg_color="#8b0000", hover_color="#a00000")
        else:
            state = "normal" if self._has_enabled_scripts(label) else "disabled"
            self._bot_toggle_btn.configure(state=state, text="Start Scripts", fg_color=GREEN, hover_color="#1B9E4B")

    def _toggle_bot_for_selected(self):
        """
        Liga ou desliga os scripts habilitados para a conta atualmente
        selecionada (o card com destaque azul).
        """

        label = self._selected_window

        if not label:
            return

        running = self.controller.is_running(label)

        if running:
            self._stop_bot_for_window(label)
        else:
            self._start_bot_for_window(label)

        self._refresh_bot_toggle_button()

    def _focus_client_window(self, label: str):
        """
        Traz a janela do jogo dessa conta pra frente. Também seleciona
        o card (duplo clique implica clique).
        """
        self._select_client_card(label)

        sessions = self.controller.get_sessions()
        hwnd = sessions.get(label, {}).get("hwnd")

        if not hwnd:
            return

        self.controller.focus_window(hwnd)

    def _get_memory_reader(self, label, pid):
        return self.controller.get_memory_reader(label, pid)

    # ============================================================
    # LOGIN / SCAN / BOT ENGINE
    # ============================================================
    def _auto_start_accounts(self):
        if not hasattr(self, "_account_index"): self._account_index = {}
        for idx, acc in enumerate(self.accounts): self._account_index[acc.label] = idx
        for acc in self.accounts:
            if acc.auto_login: self._start_login_thread(acc.label)

    def _scan_for_game_windows(self):
        ws = self.controller.window_service
        existing = self.controller.get_sessions()
        for label, info in list(existing.items()):
            if label.startswith("ext_") and info.get("hwnd"):
                if not win32gui.IsWindow(info["hwnd"]): self.controller.unregister_session(label)
        all_hwnds = ws._list_windows()
        tracked = {s["hwnd"] for s in existing.values() if s.get("hwnd")}
        for hwnd in all_hwnds:
            if hwnd in tracked: continue
            pid = ws._get_window_pid(hwnd)
            if not pid: continue
            try:
                mr = MemoryReader(pid); name = mr.char_name; mr.close()
                if name:
                    self.controller.rename_window(hwnd, name)
                    self.controller.register_session(f"ext_{hwnd}", hwnd, pid, display=name)
            except: pass
        self.root.after(5000, self._scan_for_game_windows)

    def _start_login_thread(self, label):
        if not hasattr(self, "_account_index"): return
        if label not in self._account_index: return
        if label in self._stop_events and not self._stop_events[label].is_set(): return
        cp = self._client_path.get().strip()
        if not cp: return
        self._save_client_path()
        se = threading.Event(); self._stop_events[label] = se
        acc = self.accounts[self._account_index[label]]
        threading.Thread(target=self._run_account_loop, args=(acc, cp, se), daemon=True).start()

    def _stop_login_thread(self, label):
        ev = self._stop_events.pop(label, None)
        if ev: ev.set()

    def _run_account_loop(self, account, client_path, stop_event):
        # Marca a thread inteira como pertencente a esta conta: dai em
        # diante, TODA linha logada aqui dentro -- inclusive a que vier
        # de dentro dos workflows -- sai identificada com o apelido.
        try:
            with session_context(account.label):
                self._account_loop_body(account, client_path, stop_event)
        finally:
            self._on_account_finished(account.label)

    def _account_loop_body(self, account, client_path, stop_event):
        while not stop_event.is_set():
            app = None
            try:
                s = replace(Settings(), username=account.username, password=account.password,
                           server_name=account.server_name, character_slot=account.character_slot,
                           client_path=client_path, account_label=account.label)
                app = Application(settings=s); app.start()
                hwnd = app.container.session.hwnd; pid = app.container.session.pid
                if hwnd is None: raise RuntimeError("No window")
                cn = account.label
                if pid:
                    try: tmp = MemoryReader(pid); cn = tmp.char_name or account.label; tmp.close()
                    except Exception: logger.debug("Nao foi possivel ler o nome do personagem", exc_info=True)
                self.controller.register_session(account.label, hwnd, pid, display=cn)
                self.controller.rename_window(hwnd, cn)
                logger.info("Conta conectada como '%s' (hwnd=%s)", cn, hwnd)
                while not stop_event.is_set():
                    if not win32gui.IsWindow(hwnd): break
                    time.sleep(2.0)
            except Exception:
                logger.exception("Falha no ciclo da conta")
                if stop_event.wait(5.0): break
            finally:
                self.controller.unregister_session(account.label)
                if app:
                    try: app.shutdown()
                    except Exception: logger.exception("Falha ao encerrar a Application")

    def _on_account_finished(self, label):
        self.controller.forget_session(label)

    def _bc_config_da_conta(self, label: str | None) -> dict:
        """
        Config do BC de UMA conta, criando na primeira vez.

        Diferente dos outros scripts, a do BC NÃO pode ser global: numa
        dupla, um personagem é o que roda a BC e o outro é o reseter --
        com config compartilhada seria impossível marcar só um deles.
        """
        if not label:
            # Sem conta selecionada, devolve um rascunho descartável em
            # vez de None, pra o diálogo nunca abrir vazio.
            return dict(BC_DEFAULT_CONFIG)

        return self._bc_configs.setdefault(label, dict(BC_DEFAULT_CONFIG))

    def _current_script_configs(self, label: str | None = None):
        """
        Configuração atual de cada script, editada pelos diálogos que
        abrem no botão de engrenagem de cada ScriptCard. É estado de
        apresentação (a GUI é quem edita), por
        isso continua vivendo aqui -- o Controller só recebe e repassa
        pros scripts na hora de ligar o motor.

        'label' define de qual conta vem a config do BC. Os demais
        scripts continuam com config global.
        """
        return {
            "pet": getattr(self, "_pet_config", {}),
            "attack": getattr(self, "_attack_config", {}),
            "potion": getattr(self, "_potion_config", {}),
            "buff": getattr(self, "_buff_config", {}),
            "helper": getattr(self, "_helper_config", {}),
            "fairy": getattr(self, "_fairy_config", {}),
            "revive": getattr(self, "_revive_config", {}),
            "bc": self._bc_config_da_conta(label),
        }

    def _start_bot_for_window(self, label):
        if not self._has_enabled_scripts(label):
            messagebox.showwarning(
                "Nenhum script ativo",
                "Ligue pelo menos um script (Attack, Potion, etc.) antes de iniciar."
            )
            return
        sessions = self.controller.get_sessions(); s = sessions.get(label)
        if not s or not s.get("hwnd"): return
        hwnd = s["hwnd"]; pid = s.get("pid")
        self.controller.start_scripts(
            label, hwnd, pid,
            self._feature_vars.get(label) if hasattr(self, "_feature_vars") else {},
            self._current_script_configs(label),
        )

    def _stop_bot_for_window(self, label):
        self.controller.stop_scripts(label)

    def run(self): self.root.mainloop()