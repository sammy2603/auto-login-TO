from __future__ import annotations

import json, sys, threading, time, tkinter as tk
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import win32gui, win32process

from src.app.application import Application
from src.config.settings import Settings
from src.services.license.service import LicenseService
from src.services.game.game_reader import GameReader
from src.services.game.memory_reader import MemoryReader
from src.services.bot.bot_engine import BotEngine
from src.services.bot.scripts.attack import AttackScript
from src.services.bot.scripts.potion import PotionScript
from src.services.bot.scripts.pet_food import PetScript as PetFoodScript
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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# Paleta
BG = "#080B14"; PANEL = "#0F1525"; CARD = "#141C2F"; HOVER = "#1B2640"
TEXT = "#E8EEF9"; TEXT2 = "#95A7C8"; TEXT3 = "#5D6A84"
GREEN = "#22C55E"; BLUE = "#4F8CFF"; YELLOW = "#FACC15"; RED = "#FF4D4F"
PURPLE = "#A855F7"; CYAN = "#38BDF8"

COLORS = {"Attack": RED, "Potion": GREEN, "Pet": PURPLE, "Buff": YELLOW,
          "Helper": BLUE, "Fairy": PURPLE, "Revive": RED, "Delete": TEXT3,
          "BC": CYAN, "Hollow": PURPLE, "Sell": YELLOW, "DR Lure": PURPLE}

ICONS = {"Attack": "\u2694", "Potion": "\u2697", "Pet": "\u2665", "Buff": "\u21E7",
         "Helper": "\u2699", "Fairy": "\u2726", "Revive": "\u2715", "Delete": "\u2717",
         "BC": "\u25C6", "Hollow": "\u25CE", "Sell": "\u25C8", "DR Lure": "\u25C9"}

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

class LogRedirector:
    def __init__(self, widgets, original):
        self.widgets = widgets if isinstance(widgets, list) else [widgets]
        self.original = original
        self._labels: dict[int, str] = {}; self._buffers: dict[int, str] = {}
        self._lock = threading.Lock()
    def register(self, label):
        with self._lock: self._labels[threading.get_ident()] = label
    def unregister(self):
        with self._lock: self._labels.pop(threading.get_ident(), None); self._buffers.pop(threading.get_ident(), None)
    def write(self, text):
        self.original.write(text)
        ident = threading.get_ident()
        with self._lock:
            label = self._labels.get(ident)
            buf = self._buffers.get(ident, "") + text
            lines = []
            while "\n" in buf: line, buf = buf.split("\n", 1); lines.append(line)
            self._buffers[ident] = buf
        for line in lines:
            prefixed = f"[{label}] {line}" if label else line
            for w in self.widgets:
                w.after(0, self._append, w, prefixed + "\n")
    def _append(self, w, t):
        w.configure(state="normal"); w.insert("end", t); w.yview_moveto(1.0); w.configure(state="disabled")
    def flush(self): self.original.flush()

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
    FEATURES = ["Attack", "Potion", "Pet", "Buff", "Helper", "Fairy",
                "Revive", "Delete", "BC", "Hollow", "Sell", "DR Lure"]

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Auto Login TO")
        self.root.geometry("1200x740")
        self.root.configure(fg_color=BG)
        _init_fonts()

        self.accounts = load_accounts()
        self._active_threads = 0; self._active_lock = threading.Lock()
        self._stop_events: dict[str, threading.Event] = {}
        self._feature_vars: dict[str, dict[str, ctk.BooleanVar]] = {}
        self._widget_states: dict[str, bool] = {}
        self._client_path = tk.StringVar(value=_DEFAULTS.client_path)
        self._license = LicenseService()
        self._game_reader = GameReader()
        self._selected_window: str | None = None
        self._client_cards: dict[str, any] = {}
        self._kill_track: dict = {}
        self._script_cards: dict[str, ScriptCard] = {}
        self._login_win = None; self._config_win = None

        self._build_top_bar()
        self._build_layout()
        self._build_bottom_bar()

        self.log_redirector = LogRedirector(self._console, sys.stdout)

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
        if win and hasattr(self, "_feature_vars") and win in self._feature_vars:
            if name not in self._feature_vars[win]:
                self._feature_vars[win][name] = ctk.BooleanVar(value=False)
            self._feature_vars[win][name].set(enabled)
        if name in self._script_cards:
            self._script_cards[name].set_enabled(enabled)

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
        sessions = SessionRegistry.get_all()
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

    # ============================================================
    # LOGIN / WINDOWS / PERSISTENCE / POLLING / BOT ENGINE
    # ============================================================
    def _open_login(self):
        if not hasattr(self, "_login_win") or not self._login_win or not self._login_win.winfo_exists():
            self._login_win = self._create_login_win()
        else: self._login_win.deiconify(); self._login_win.lift(); self._login_win.focus_force()

    def _create_login_win(self):
        d = ctk.CTkToplevel(self.root); d.title("Login — Contas"); d.geometry("520x440")
        d.configure(fg_color=BG); d.resizable(False, False); d.transient(self.root)
        d.protocol("WM_DELETE_WINDOW", lambda: setattr(self, "_login_win", None) or d.destroy())
        self.root.update_idletasks(); pw,ph = self.root.winfo_width(), self.root.winfo_height()
        px,py = self.root.winfo_x(), self.root.winfo_y()
        d.geometry(f"520x440+{px+(pw-520)//2}+{py+(ph-440)//2}")
        f = ctk.CTkFrame(d, fg_color="transparent"); f.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(f, text="Accounts", font=FONT_H3, text_color=TEXT).pack(anchor="w")
        ctk.CTkFrame(f, height=1, fg_color="#1A2540").pack(fill="x", pady=4)
        table = ctk.CTkScrollableFrame(f, fg_color="transparent", height=280); table.pack(fill="both", expand=True, pady=4)
        btn_row = ctk.CTkFrame(f, fg_color="transparent"); btn_row.pack(fill="x", pady=(4,0))
        ctk.CTkButton(btn_row, text="Add Account", font=FONT_SMALL, command=lambda: self._add_account(table)).pack(side="left")

        def refresh():
            for w in table.winfo_children(): w.destroy()
            if not hasattr(self, "_account_index"): self._account_index = {}
            if not hasattr(self, "_login_vars"): self._login_vars = {}
            if not self.accounts:
                ctk.CTkLabel(table, text="No accounts", font=FONT_SMALL, text_color=TEXT3).pack(expand=True, pady=30)
                return
            for idx, acc in enumerate(self.accounts):
                self._account_index[acc.label] = idx
                if acc.label not in self._login_vars: self._login_vars[acc.label] = ctk.BooleanVar(value=False)
                row = ctk.CTkFrame(table, fg_color="transparent"); row.pack(fill="x", pady=1)
                var = self._login_vars[acc.label]
                ctk.CTkCheckBox(row, text="", variable=var, width=20,
                               command=lambda l=acc.label: self._on_login_toggle(l)).pack(side="left")
                ctk.CTkLabel(row, text=acc.label, width=80, font=FONT_SMALL).pack(side="left", padx=4)
                ctk.CTkLabel(row, text=acc.server_name, width=90, font=FONT_SMALL, text_color=TEXT2).pack(side="left", padx=4)
                ctk.CTkLabel(row, text=acc.username, width=90, font=FONT_SMALL, text_color=TEXT2).pack(side="left", padx=4)
                ctk.CTkButton(row, text="E", width=24, height=20, font=ctk.CTkFont(size=9), fg_color="transparent", border_width=1,
                             command=lambda a=acc: self._edit_account(a, refresh)).pack(side="right", padx=2)
                ctk.CTkButton(row, text="X", width=24, height=20, font=ctk.CTkFont(size=9), fg_color="transparent", border_width=1,
                             command=lambda a=acc: self._remove_account(a, refresh)).pack(side="right")
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
        sessions = SessionRegistry.get_all()
        online = 0
        existing = set(self._client_cards.keys()); current = set(sessions.keys())
        for label in current - existing:
            s = sessions[label]; display = s.get("display", label)
            card = ctk.CTkFrame(self._clients_scroll, fg_color=CARD, corner_radius=8, border_width=1, border_color="#1A2540")
            card.pack(fill="x", pady=2, padx=2)
            hdr = ctk.CTkFrame(card, fg_color="transparent"); hdr.pack(fill="x", padx=8, pady=(6,0))
            ctk.CTkLabel(hdr, text=display, font=FONT_SMALL, text_color=TEXT).pack(side="left")
            dot = ctk.CTkLabel(hdr, text="\u25CF", font=ctk.CTkFont(size=8), text_color=TEXT3); dot.pack(side="right")
            hp_bar = ctk.CTkProgressBar(card, height=5, progress_color=GREEN); hp_bar.pack(fill="x", padx=8, pady=(2,0)); hp_bar.set(0)
            mp_bar = ctk.CTkProgressBar(card, height=5, progress_color=BLUE); mp_bar.pack(fill="x", padx=8, pady=2); mp_bar.set(0)
            self._client_cards[label] = {"frame":card,"dot":dot,"hp":hp_bar,"mp":mp_bar}

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
                        cd["dot"].configure(text_color=GREEN); online += 1
                except: pass

        self._ind_online.configure(text=f"{online} Online")
        scripts = sum(1 for v in self._widget_states.values() if v)
        self._ind_scripts.configure(text=f"{scripts} Scripts")
        self.root.after(500, self._poll_loop)

    def _get_memory_reader(self, label, pid):
        if not hasattr(self, "_memory_readers"): self._memory_readers = {}; self._mr_failed = set()
        if label in self._mr_failed: return None
        if label not in self._memory_readers:
            try: self._memory_readers[label] = MemoryReader(pid)
            except: self._mr_failed.add(label); return None
        return self._memory_readers[label]

    # ============================================================
    # LOGIN / SCAN / BOT ENGINE
    # ============================================================
    def _auto_start_accounts(self):
        if not hasattr(self, "_account_index"): self._account_index = {}
        for idx, acc in enumerate(self.accounts): self._account_index[acc.label] = idx
        for acc in self.accounts:
            if acc.auto_login: self._start_login_thread(acc.label)

    def _scan_for_game_windows(self):
        from src.infrastructure.window.service import WindowService
        ws = WindowService()
        existing = SessionRegistry.get_all()
        for label, info in list(existing.items()):
            if label.startswith("ext_") and info.get("hwnd"):
                if not win32gui.IsWindow(info["hwnd"]): SessionRegistry.unregister(label)
        all_hwnds = ws._list_windows()
        tracked = {s["hwnd"] for s in existing.values() if s.get("hwnd")}
        for hwnd in all_hwnds:
            if hwnd in tracked: continue
            pid = ws._get_window_pid(hwnd)
            if not pid: continue
            try:
                mr = MemoryReader(pid); name = mr.char_name; mr.close()
                if name:
                    try: win32gui.SetWindowText(hwnd, name)
                    except: pass
                    SessionRegistry.register(f"ext_{hwnd}", hwnd, pid, display=name)
            except: pass
        self.root.after(5000, self._scan_for_game_windows)

    def _start_login_thread(self, label):
        if not hasattr(self, "_account_index"): return
        if label not in self._account_index: return
        if label in self._stop_events and not self._stop_events[label].is_set(): return
        cp = self._client_path.get().strip()
        if not cp: return
        self._save_client_path()
        with self._active_lock:
            if self._active_threads == 0: sys.stdout = self.log_redirector
            self._active_threads += 1
        se = threading.Event(); self._stop_events[label] = se
        acc = self.accounts[self._account_index[label]]
        threading.Thread(target=self._run_account_loop, args=(acc, cp, se), daemon=True).start()

    def _stop_login_thread(self, label):
        ev = self._stop_events.pop(label, None)
        if ev: ev.set()

    def _run_account_loop(self, account, client_path, stop_event):
        self.log_redirector.register(account.label)
        try:
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
                        except: pass
                    SessionRegistry.register(account.label, hwnd, pid, display=cn)
                    try: win32gui.SetWindowText(hwnd, cn)
                    except: pass
                    while not stop_event.is_set():
                        if not win32gui.IsWindow(hwnd): break
                        time.sleep(2.0)
                except Exception as e:
                    print(f"[{account.label}] Error: {e}")
                    if stop_event.wait(5.0): break
                finally:
                    SessionRegistry.unregister(account.label)
                    if app:
                        try: app.shutdown()
                        except: pass
        finally:
            self.log_redirector.unregister()
            self._on_account_finished(account.label)

    def _on_account_finished(self, label):
        self._stop_bot_for_window(label)
        if hasattr(self, "_memory_readers"):
            self._memory_readers.pop(label, None)
            if hasattr(self, "_mr_failed"): self._mr_failed.discard(label)
        with self._active_lock:
            self._active_threads -= 1
            if self._active_threads <= 0:
                self.root.after(0, lambda: setattr(sys, "stdout", self.log_redirector.original))

    def _get_or_create_bot_engine(self, label):
        if not hasattr(self, "_bot_engines"): self._bot_engines = {}
        if label not in self._bot_engines:
            engine = BotEngine()
            engine.register(PetFoodScript(config=getattr(self,"_pet_config",{})))
            engine.register(AttackScript(config=getattr(self,"_attack_config",{})))
            engine.register(PotionScript(config=getattr(self,"_potion_config",{})))
            engine.register(BuffScript(config=getattr(self,"_buff_config",{})))
            engine.register(HelperScript(config=getattr(self,"_helper_config",{})))
            engine.register(FairyScript(config=getattr(self,"_fairy_config",{})))
            engine.register(ReviveScript(config=getattr(self,"_revive_config",{})))
            engine.register(DeleteScript()); engine.register(BCScript())
            engine.register(HollowScript()); engine.register(SellScript()); engine.register(DRLureScript())
            self._bot_engines[label] = engine
        return self._bot_engines[label]

    def _start_bot_for_window(self, label):
        sessions = SessionRegistry.get_all(); s = sessions.get(label)
        if not s or not s.get("hwnd"): return
        hwnd = s["hwnd"]; pid = s.get("pid")
        engine = self._get_or_create_bot_engine(label)
        if engine.is_running: return
        from src.infrastructure.window.service import WindowService
        from src.infrastructure.vision.service import VisionService
        from src.infrastructure.input.service import InputService
        ws = WindowService(); vs = VisionService(window_service=ws); ins = InputService()
        mr = self._get_memory_reader(label, pid) if pid else None
        engine.start(hwnd, ins, vs, ws, self._game_reader, mr,
                     self._feature_vars.get(label) if hasattr(self,"_feature_vars") else {})

    def _stop_bot_for_window(self, label):
        if not hasattr(self, "_bot_engines"): return
        engine = self._bot_engines.get(label)
        if engine: engine.stop()

    def run(self): self.root.mainloop()
