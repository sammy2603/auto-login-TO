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
# Dialogo de conta
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

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Talisman Online - Auto Login")
        self.root.geometry("960x650")
        self.root.minsize(800, 520)

        self.accounts: list[Account] = load_accounts()
        self._active_threads = 0
        self._active_lock = threading.Lock()
        self._stop_events: dict[str, threading.Event] = {}
        self._login_vars: dict[str, tk.BooleanVar] = {}
        self._account_index: dict[str, int] = {}
        self._client_path = tk.StringVar(value=_DEFAULTS.client_path)
        self._license = LicenseService()

        # Leitor de dados do jogo (regioes calibraveis via config)
        self._game_reader = GameReader()

        # Per-window state para o Dashboard
        self._selected_window: str | None = None
        self._feature_vars: dict[str, dict[str, tk.BooleanVar]] = {}
        self._widget_states: dict[str, bool] = {}

        self._setup_theme()
        self._build_top_bar()

        # Container principal (casca vazia, 3 colunas)
        self._build_main_shell()

        # Conteudo central (notebook, abas, home, dashboard)
        self.log_redirector = None
        self._build_center_frames()
        self._build_home_content()

        # Paineis laterais (sidebar + right panel — precisam
        # do notebook pronto no centro)
        self._build_side_panels()

        self._build_status_bar()

        self._load_saved_client_path()
        self._rebuild_login_table()

        self.root.after(500, self._auto_start_accounts)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # =====================================================
    # Tema escuro
    # =====================================================

    def _setup_theme(self):
        style = ttk.Style()
        # Tenta usar um tema escuro se disponivel
        available = style.theme_names()
        for preferred in ("clam", "alt", "default"):
            if preferred in available:
                style.theme_use(preferred)
                break

        BG = "#2a2a2a"
        FG = "#cccccc"
        self.root.configure(bg=BG)

        style.configure(".", background=BG, foreground=FG)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TButton", background="#3a3a3a", foreground=FG)
        style.map("TButton", background=[("active", "#4a4a4a")])
        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", background="#3a3a3a", foreground=FG)
        style.map("TNotebook.Tab", background=[("selected", "#4a4a4a")])

        # Estilo para botao selecionado na sidebar
        style.configure("Accent.TButton", background="#1a5c2a", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#1e6e32")])

    # =====================================================
    # Barra superior
    # =====================================================

    def _build_top_bar(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=(8, 0))

        self._top_buttons: dict[str, ttk.Button] = {}

        for label in ("List", "Config", "Login", "Pricing", "Help"):
            btn = ttk.Button(top, text=label, command=lambda l=label: self._on_top_bar(l))
            btn.pack(side="left", padx=2)
            self._top_buttons[label] = btn

        # Separador
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=8, pady=4)

    def _on_top_bar(self, label: str):
        """Callback dos botoes da barra superior."""
        if label == "Login":
            self.notebook.select(self._home_tab_id)
            self.sidebar._select("Home")
        elif label == "Config":
            self.notebook.select(self._config_tab_id)
        elif label == "Help":
            self._show_help_dialog()
        elif label == "Pricing":
            self._show_pricing_dialog()
        elif label == "List":
            self._toggle_window_list()

    def _toggle_window_list(self):
        """Alterna entre ordenado e livre para as janelas no painel direito."""
        # Fase 2: ordenar por indice ou deixar livre
        messagebox.showinfo("List", "Ordenacao de janelas sera implementada em breve.")

    # =====================================================
    # Dialogs: Pricing e Help
    # =====================================================

    def _show_pricing_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Pricing")
        dialog.resizable(False, False)
        dialog.transient(self.root)

        frame = ttk.Frame(dialog, padding=20)
        frame.pack()

        ttk.Label(frame, text="Planos", font=("", 14, "bold")).pack(pady=(0, 16))

        # Free
        free = ttk.LabelFrame(frame, text="Gratuito", padding=12)
        free.pack(fill="x", pady=4)
        for item in [
            "Login automatico",
            "Configuracoes basicas",
            "1 conta simultanea",
        ]:
            ttk.Label(free, text=f"  • {item}").pack(anchor="w")

        # Premium
        premium = ttk.LabelFrame(frame, text="Premium", padding=12)
        premium.pack(fill="x", pady=4)
        for item in [
            "Multiplas contas simultaneas",
            "Todos os scripts de automacao",
            "Perfis personalizados",
            "Atualizacoes prioritarias",
            "Suporte dedicado",
        ]:
            ttk.Label(premium, text=f"  • {item}").pack(anchor="w")

        ttk.Label(
            frame,
            text="Contato: contato@loginto.app",
            foreground="#888888",
        ).pack(pady=(16, 0))

        ttk.Button(frame, text="Fechar", command=dialog.destroy).pack(pady=(12, 0))

        dialog.grab_set()
        dialog.wait_window()

    def _show_help_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Help / Sobre")
        dialog.resizable(False, False)
        dialog.transient(self.root)

        frame = ttk.Frame(dialog, padding=20)
        frame.pack()

        ttk.Label(frame, text="Auto Login TO", font=("", 14, "bold")).pack()
        ttk.Label(frame, text="Versao 0.2.0", foreground="#888888").pack(pady=(2, 12))

        ttk.Label(frame, text="Automatizacao de login para Talisman Online").pack()

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=12)

        ttk.Button(
            frame,
            text="Verificar Atualizacao",
            command=self._check_for_updates,
        ).pack(pady=(0, 8))

        ttk.Button(frame, text="Fechar", command=dialog.destroy).pack()

        dialog.grab_set()
        dialog.wait_window()

    def _check_for_updates(self):
        """Verifica se ha uma nova versao disponivel no GitHub."""
        try:
            import urllib.request
            import json

            url = (
                "https://api.github.com/repos/anomalyco/opencode/"
                "releases/latest"
            )
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("User-Agent", "LoginTO-UpdateChecker")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                latest = data.get("tag_name", "")

            if latest:
                messagebox.showinfo(
                    "Atualizacao",
                    f"Ultima versao disponivel: {latest}\n"
                    f"Versao atual: 0.2.0\n\n"
                    f"A atualizacao manual e necessaria por enquanto.",
                )
            else:
                messagebox.showinfo("Atualizacao", "Nao foi possivel verificar.")
        except Exception as e:
            messagebox.showinfo("Atualizacao", f"Erro ao verificar: {e}")

    # =====================================================
    # Bot Engine
    # =====================================================

    def _get_or_create_bot_engine(self, label: str) -> BotEngine:
        """Retorna o BotEngine para a janela, criando se necessario."""

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
        """Inicia o bot para a janela especificada."""

        sessions = SessionRegistry.get_all()
        session = sessions.get(label)
        if session is None or not session.get("hwnd"):
            print(f"[GUI] Nao ha janela ativa para '{label}'.")
            return

        hwnd = session["hwnd"]

        engine = self._get_or_create_bot_engine(label)
        if engine.is_running:
            return

        # Cria servicos para esta janela
        from src.infrastructure.window.service import WindowService
        from src.infrastructure.vision.service import VisionService
        from src.infrastructure.input.service import InputService

        ws = WindowService()
        vs = VisionService(window_service=ws)
        ins = InputService()

        engine.start(hwnd, ins, vs, ws, self._game_reader)

    def _stop_bot_for_window(self, label: str):
        """Para o bot para a janela especificada."""

        if not hasattr(self, "_bot_engines"):
            return

        engine = self._bot_engines.get(label)
        if engine:
            engine.stop()

    # =====================================================
    # Area principal (3 colunas)
    # =====================================================

    def _build_main_shell(self):
        """Cria o layout de 3 colunas com o centro vazio."""
        self._main_pw = ttk.PanedWindow(self.root, orient="horizontal")
        self._main_pw.pack(fill="both", expand=True, padx=8, pady=4)

        # Centro (vazio, preenchido depois)
        self.center_frame = ttk.Frame(self._main_pw)
        self._main_pw.add(self.center_frame, weight=1)

    def _build_side_panels(self):
        """Adiciona sidebar e painel direito ao redor do centro."""

        # --- Sidebar esquerda ---
        sidebar_frame = ttk.Frame(self._main_pw, width=130)
        self._main_pw.insert(0, sidebar_frame, weight=0)

        self.sidebar = Sidebar(sidebar_frame, on_select=self._on_sidebar_select)
        self.sidebar.pack(fill="both", expand=True)

        # --- Painel direito ---
        right_frame = ttk.Frame(self._main_pw, width=190)
        self._main_pw.add(right_frame, weight=0)

        self.right_panel = RightPanel(
            right_frame,
            on_select=self._on_right_panel_select,
            on_action=self._on_right_panel_action,
        )
        self.right_panel.pack(fill="both", expand=True)

    # =====================================================
    # Conteudo central (abas / frames)
    # =====================================================

    def _build_center_frames(self):
        """Cria o notebook central com as paginas principais."""
        self.notebook = ttk.Notebook(self.center_frame)
        self.notebook.pack(fill="both", expand=True)

        # Tab 0: Home (login)
        self._home_frame = ttk.Frame(self.notebook)
        self.notebook.add(self._home_frame, text="Home")
        self._home_tab_id = 0

        # Tab 1: Config
        self._config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self._config_frame, text="Config")
        self._config_tab_id = 1

        # Tab 2: Dashboard (Attack, Potion, etc.)
        self._dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self._dashboard_frame, text="Dashboard")
        self._dashboard_tab_id = 2

        # Tab 3: Key (licenca)
        self._key_frame = ttk.Frame(self.notebook)
        self.notebook.add(self._key_frame, text="Key")
        self._key_tab_id = 3

        self._build_config_content()
        self._build_dashboard_content()
        self._build_key_content()

        self.notebook.select(self._home_tab_id)

    def _build_config_content(self):
        """Conteudo da aba Config."""
        frame = ttk.Frame(self._config_frame, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Configuracoes", font=("", 11, "bold")).pack(anchor="w", pady=(0, 12))

        # Client path
        row1 = ttk.Frame(frame)
        row1.pack(fill="x", pady=4)
        ttk.Label(row1, text="Client:").pack(side="left")
        ttk.Entry(row1, textvariable=self._client_path, width=50).pack(side="left", padx=(8, 4))
        ttk.Button(row1, text="Procurar", command=self._browse_client_path).pack(side="left")

        ttk.Label(
            frame,
            text="Demais configuracoes ficam em config.py e .env",
            foreground="#888888",
        ).pack(anchor="w", pady=(16, 0))

    # =====================================================
    # Secao Home — login
    # =====================================================

    def _build_home_content(self):
        """Conteudo da aba Home: login + log."""

        self._home_frame.columnconfigure(0, weight=1)
        self._home_frame.rowconfigure(1, weight=1)

        # --- Tabela de contas com checkboxes ---
        table_container = ttk.Frame(self._home_frame)
        table_container.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        table_container.columnconfigure(0, weight=1)

        # Cabecalho + scroll
        self._login_canvas = tk.Canvas(table_container, highlightthickness=0, bg="#2a2a2a")
        self._login_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self._login_canvas.yview)
        self._login_inner = ttk.Frame(self._login_canvas)

        self._login_inner.bind(
            "<Configure>",
            lambda e: self._login_canvas.configure(scrollregion=self._login_canvas.bbox("all")),
        )
        self._login_canvas.create_window((0, 0), window=self._login_inner, anchor="nw")
        self._login_canvas.configure(yscrollcommand=self._login_scrollbar.set)

        self._login_canvas.pack(side="left", fill="both", expand=True)
        self._login_scrollbar.pack(side="right", fill="y")

        # Botoes de gerenciamento
        btn_row = ttk.Frame(self._home_frame)
        btn_row.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 4))
        ttk.Button(btn_row, text="Adicionar Conta", command=self._on_add_account).pack(side="left")

        # --- Log ---
        log_frame = ttk.Frame(self._home_frame)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 4))
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        ttk.Label(log_frame, text="Log:", font=("", 9, "bold")).grid(row=0, column=0, sticky="w")

        text_frame = ttk.Frame(log_frame)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        log_scroll = ttk.Scrollbar(text_frame)
        log_scroll.grid(row=0, column=1, sticky="ns")

        self.log_text = tk.Text(
            text_frame,
            state="disabled",
            wrap="word",
            yscrollcommand=log_scroll.set,
            height=8,
            bg="#1e1e1e",
            fg="#cccccc",
            insertbackground="#cccccc",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll.config(command=self.log_text.yview)

        self.log_redirector = MultiAccountLogRedirector(self.log_text, sys.stdout)

        self._home_frame.rowconfigure(3, weight=1)

    def _rebuild_login_table(self):
        """Reconstroi a tabela de contas com checkboxes."""

        for widget in self._login_inner.winfo_children():
            widget.destroy()

        old_checked = {label for label, var in self._login_vars.items() if var.get()}
        self._login_vars.clear()
        self._account_index.clear()

        if not self.accounts:
            ttk.Label(
                self._login_inner,
                text="Nenhuma conta cadastrada.\nClique em 'Adicionar Conta' para comecar.",
                justify="center",
            ).pack(expand=True, pady=20)
            return

        # Cabecalho
        hdr = ttk.Frame(self._login_inner)
        hdr.pack(fill="x", pady=(4, 4))
        ttk.Label(hdr, text="Conta", font=("", 9, "bold"), width=16, anchor="w").pack(side="left")
        ttk.Label(hdr, text="Servidor", font=("", 9, "bold"), width=18, anchor="w").pack(side="left", padx=(8, 0))
        ttk.Label(hdr, text="Usuario", font=("", 9, "bold"), width=18, anchor="w").pack(side="left", padx=(8, 0))
        ttk.Separator(self._login_inner, orient="horizontal").pack(fill="x", pady=(0, 4))

        for idx, account in enumerate(self.accounts):
            self._account_index[account.label] = idx

            row = ttk.Frame(self._login_inner)
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

            # Botao de editar / remover inline
            ttk.Button(row, text="✎", width=3, command=lambda a=account: self._on_edit_inline(a)).pack(side="right", padx=(4, 0))
            ttk.Button(row, text="✕", width=3, command=lambda a=account: self._on_remove_inline(a)).pack(side="right")

    # =====================================================
    # Centro: outras secoes (placeholder)
    # =====================================================

    def _on_sidebar_select(self, label: str):
        """Callback do Sidebar — alterna a aba do notebook."""
        if label == "Home":
            self.notebook.select(self._home_tab_id)
        elif label == "Config":
            self.notebook.select(self._config_tab_id)
        elif label == "Key":
            self.notebook.select(self._key_tab_id)
        else:
            # Attack, Potion, Pet Food, etc. — abre Dashboard
            self.notebook.select(self._dashboard_tab_id)
            self._highlight_feature(label)

    # =====================================================
    # Dashboard (Attack, Potion, etc.)
    # =====================================================

    FEATURES = [
        "Attack", "Potion", "Pet Food", "Buff",
        "Helper", "Fairy", "Revive", "Delete",
        "BC", "Hollow", "Sell", "DR Lure",
    ]

    def _build_dashboard_content(self):
        """Conteudo da aba Dashboard: Char Info, Target Info,
        checkboxes de funcoes por janela e log."""

        self._dashboard_frame.columnconfigure(0, weight=1)
        self._dashboard_frame.rowconfigure(3, weight=1)

        # --- Char Info ---
        char_frame = ttk.LabelFrame(self._dashboard_frame, text="Char Info", padding=8)
        char_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        char_frame.columnconfigure(1, weight=1)

        ttk.Label(char_frame, text="HP:", width=10).grid(row=0, column=0, sticky="w")
        self._char_hp_bar = ttk.Progressbar(char_frame, length=200, mode="determinate")
        self._char_hp_bar.grid(row=0, column=1, sticky="ew", padx=(4, 4))
        self._char_hp_label = ttk.Label(char_frame, text="---", width=6)
        self._char_hp_label.grid(row=0, column=2)

        ttk.Label(char_frame, text="Recurso:", width=10).grid(row=1, column=0, sticky="w")
        self._char_res_bar = ttk.Progressbar(char_frame, length=200, mode="determinate")
        self._char_res_bar.grid(row=1, column=1, sticky="ew", padx=(4, 4))
        self._char_res_label = ttk.Label(char_frame, text="---", width=6)
        self._char_res_label.grid(row=1, column=2)

        # --- Target Info ---
        target_frame = ttk.LabelFrame(self._dashboard_frame, text="Target Info", padding=8)
        target_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        target_frame.columnconfigure(1, weight=1)

        ttk.Label(target_frame, text="HP:", width=10).grid(row=0, column=0, sticky="w")
        self._target_hp_bar = ttk.Progressbar(target_frame, length=200, mode="determinate")
        self._target_hp_bar.grid(row=0, column=1, sticky="ew", padx=(4, 4))
        self._target_hp_label = ttk.Label(target_frame, text="---", width=6)
        self._target_hp_label.grid(row=0, column=2)

        ttk.Label(target_frame, text="Nome:", width=10).grid(row=1, column=0, sticky="w")
        self._target_name_label = ttk.Label(target_frame, text="---")
        self._target_name_label.grid(row=1, column=1, sticky="w", padx=(4, 0))

        # --- Feature Checkboxes ---
        func_frame = ttk.LabelFrame(self._dashboard_frame, text="Funcoes", padding=8)
        func_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=4)

        self._feature_check_frame = ttk.Frame(func_frame)
        self._feature_check_frame.pack(fill="x")

        self._feature_widgets: dict[str, ttk.Checkbutton] = {}
        self._feature_highlight_labels: dict[str, ttk.Label] = {}

        half = len(self.FEATURES) // 2
        left_col = ttk.Frame(self._feature_check_frame)
        left_col.pack(side="left", fill="x", expand=True)
        right_col = ttk.Frame(self._feature_check_frame)
        right_col.pack(side="left", fill="x", expand=True, padx=(24, 0))

        for i, feature in enumerate(self.FEATURES):
            parent = left_col if i < half else right_col

            row = ttk.Frame(parent)
            row.pack(fill="x", pady=2)

            hl = ttk.Label(row, text="  ", width=3)
            hl.pack(side="left")
            self._feature_highlight_labels[feature] = hl

            cb = ttk.Checkbutton(row, text=feature, state="disabled")
            cb.pack(side="left")
            self._feature_widgets[feature] = cb

        # --- Status da janela selecionada ---
        self._dashboard_status = ttk.Label(
            self._dashboard_frame,
            text="Selecione uma janela no painel direito para configurar as funcoes.",
            foreground="#888888",
        )
        self._dashboard_status.grid(row=4, column=0, sticky="ew", padx=8, pady=2)

        # --- Dashboard Log ---
        log_frame = ttk.LabelFrame(self._dashboard_frame, text="Log da Janela", padding=4)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(4, 8))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        text_frame = ttk.Frame(log_frame)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        dlog_scroll = ttk.Scrollbar(text_frame)
        dlog_scroll.grid(row=0, column=1, sticky="ns")

        self._dashboard_log = tk.Text(
            text_frame,
            state="disabled",
            wrap="word",
            yscrollcommand=dlog_scroll.set,
            height=6,
            bg="#1e1e1e",
            fg="#cccccc",
            insertbackground="#cccccc",
        )
        self._dashboard_log.grid(row=0, column=0, sticky="nsew")
        dlog_scroll.config(command=self._dashboard_log.yview)

    def _ensure_window_state(self, label: str):
        """Garante que existe estado para a janela informada."""
        if label not in self._feature_vars:
            self._feature_vars[label] = {
                f: tk.BooleanVar(value=False) for f in self.FEATURES
            }
            self._widget_states[label] = False

    def _on_right_panel_select(self, label: str):
        """Callback do RightPanel quando uma janela e selecionada."""
        self._selected_window = label
        self._ensure_window_state(label)
        self._refresh_dashboard()
        self._start_dashboard_poll()

    def _on_right_panel_action(self, label: str):
        """Callback do RightPanel quando Start/Stop e pressionado."""
        running = self.right_panel.running
        self._widget_states[label] = running

        if running:
            self._start_bot_for_window(label)
            status = "INICIADO"
        else:
            self._stop_bot_for_window(label)
            status = "PARADO"

        self._dashboard_log_append(
            f"[{label}] Bot {status}.\n"
        )

        self._refresh_dashboard()

    def _refresh_dashboard(self):
        """Atualiza o Dashboard com os dados da janela selecionada."""

        label = self._selected_window

        if label is None or label not in self._feature_vars:
            self._dashboard_status.configure(
                text="Selecione uma janela no painel direito para configurar as funcoes."
            )
            for feature in self.FEATURES:
                self._feature_widgets[feature].configure(state="disabled")
                self._feature_highlight_labels[feature].configure(text="  ")
            self._char_hp_bar.configure(value=0)
            self._char_hp_label.configure(text="---")
            self._char_res_bar.configure(value=0)
            self._char_res_label.configure(text="---")
            self._target_hp_bar.configure(value=0)
            self._target_hp_label.configure(text="---")
            self._target_name_label.configure(text="---")
            return

        running = self._widget_states.get(label, False)
        self._dashboard_status.configure(
            text=f"Janela: {label}  |  Status: {'ATIVO' if running else 'PARADO'}"
        )

        # Habilita checkboxes e conecta com os vars
        for feature in self.FEATURES:
            cb = self._feature_widgets[feature]
            var = self._feature_vars[label][feature]
            cb.configure(state="normal", variable=var)

    def _highlight_feature(self, feature: str):
        """Destaca uma feature no Dashboard (pisca o indicador)."""
        if feature not in self._feature_highlight_labels:
            return

        hl = self._feature_highlight_labels[feature]
        hl.configure(text="▶")

        def _clear():
            hl.configure(text="  ")

        self.root.after(2000, _clear)

    def _start_dashboard_poll(self):
        """Inicia o loop de leitura de dados do jogo."""
        self._poll_dashboard()

    def _poll_dashboard(self):
        """Le dados do jogo e atualiza o Dashboard (chamada periodica)."""

        label = self._selected_window

        if label is None or not self._widget_states.get(label, False):
            # Nao ha janela selecionada ou bot nao esta rodando
            return

        # Tenta obter o HWND da sessao ativa
        sessions = SessionRegistry.get_all()
        session = sessions.get(label)
        if session is None:
            return

        hwnd = session.get("hwnd")
        if hwnd is None:
            return

        try:
            # Captura a janela e le os dados
            from src.infrastructure.window.service import WindowService
            ws = WindowService()
            screenshot = ws.capture_hwnd(hwnd)

            char_info = self._game_reader.read_char_info(screenshot)
            target_info = self._game_reader.read_target_info(screenshot)

            # Atualiza as barras
            self._char_hp_bar.configure(value=char_info.hp_pct)
            self._char_hp_label.configure(text=f"{char_info.hp_pct:.0f}%")
            self._char_res_bar.configure(value=char_info.resource_pct)
            self._char_res_label.configure(text=f"{char_info.resource_pct:.0f}%")
            self._target_hp_bar.configure(value=target_info.hp_pct)
            self._target_hp_label.configure(text=f"{target_info.hp_pct:.0f}%")
            self._target_name_label.configure(text=target_info.name or "---")

        except Exception:
            pass

        # Agenda proxima leitura
        if self._widget_states.get(label, False):
            self.root.after(1000, self._poll_dashboard)

    def _dashboard_log_append(self, text: str):
        """Adiciona texto ao log do dashboard."""
        self._dashboard_log.configure(state="normal")
        self._dashboard_log.insert("end", text)
        self._dashboard_log.see("end")
        self._dashboard_log.configure(state="disabled")

    # =====================================================
    # Aba Key (licenciamento)
    # =====================================================

    def _build_key_content(self):
        """Conteudo da aba Key: ativacao de licenca."""

        frame = ttk.Frame(self._key_frame, padding=24)
        frame.pack(expand=True)

        ttk.Label(frame, text="Licenciamento", font=("", 14, "bold")).pack(pady=(0, 16))

        # Chave
        key_row = ttk.Frame(frame)
        key_row.pack(fill="x", pady=4)
        ttk.Label(key_row, text="Chave:", width=8).pack(side="left")
        self._license_key_var = tk.StringVar()
        ttk.Entry(key_row, textvariable=self._license_key_var, width=28).pack(side="left", padx=(8, 8))
        ttk.Button(key_row, text="Validar", command=self._on_validate_license).pack(side="left")

        # Demo
        ttk.Button(
            frame, text="Usar modo Demo (30 dias gratuitos)",
            command=self._on_activate_demo,
        ).pack(pady=(12, 20))

        # Status
        self._license_status_frame = ttk.LabelFrame(frame, text="Status", padding=12)
        self._license_status_frame.pack(fill="x")

        self._license_status_text = ttk.Label(
            self._license_status_frame,
            text="",
            font=("", 10),
        )
        self._license_status_text.pack(anchor="w")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(16, 4))

        ttk.Label(
            frame,
            text="Adquira sua licenca: contato@loginto.app",
            foreground="#888888",
        ).pack()

        self._refresh_license_status()

    def _refresh_license_status(self):
        """Atualiza o status da licenca na aba Key e na barra inferior."""

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
            foreground=color,
        )

        # Barra de status (pode ainda nao existir na primeira chamada)
        if hasattr(self, "_license_label"):
            self._license_label.configure(
                text=f"Licenca: {tier} ({days}d)",
                foreground=color,
            )

    def _on_validate_license(self):
        """Valida a chave inserida pelo usuario."""
        key = self._license_key_var.get().strip()
        if not key:
            messagebox.showwarning("Chave vazia", "Insira uma chave de licenca.")
            return

        success, msg = self._license.activate(key)
        if success:
            messagebox.showinfo("Licenca ativada", msg)
        else:
            messagebox.showerror("Erro", msg)

        self._license_key_var.set("")
        self._refresh_license_status()

    def _on_activate_demo(self):
        """Ativa o modo de demonstracao."""
        success, msg = self._license.activate("DEMO")
        if success:
            messagebox.showinfo("Modo Demo", msg)
        self._refresh_license_status()

    def _build_status_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=(0, 4))

        self._license_label = ttk.Label(bar, text="Licenca: ...", foreground="#888888")
        self._license_label.pack(side="right")

        # Atualiza com dados reais
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
    # Login / relogging (threads)
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
                    print(f"[{account.label}] Login concluido com sucesso!")

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
        print(f"[{label}] Monitorando janela (hwnd={hwnd})...")
        while not stop_event.is_set():
            if not win32gui.IsWindow(hwnd):
                print(f"[{label}] Janela fechada. Reiniciando login...")
                return
            time.sleep(2.0)

    def _on_account_finished(self, label: str):
        def _uncheck():
            var = self._login_vars.get(label)
            if var:
                var.set(False)
        self.root.after(0, _uncheck)

        # Para o bot engine se estiver rodando
        self._stop_bot_for_window(label)

        with self._active_lock:
            self._active_threads -= 1
            remaining = self._active_threads

        if remaining <= 0:
            self.root.after(0, self._restore_stdout)

    def _restore_stdout(self):
        sys.stdout = self.log_redirector.original

    # =====================================================
    # Auto-login
    # =====================================================

    def _auto_start_accounts(self):
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
