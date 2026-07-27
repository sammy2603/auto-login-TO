# -*- coding: utf-8 -*-
"""
Shim de compatibilidade.

As configuracoes agora vivem em src/config/settings.py.
Este arquivo existe apenas para que scripts em tools/ continuem
funcionando sem alteracoes.

Novo codigo deve importar diretamente de src.config.settings:

    from src.config.settings import Settings
"""

from src.config.settings import Settings as _Settings

_defaults = _Settings()

# --- Caminho do executavel do client ---
CLIENT_PATH = _defaults.client_path

# --- Titulo da janela do jogo ---
WINDOW_TITLE = _defaults.window_title

# --- Resolucao alvo ---
TARGET_WIDTH = _defaults.target_width
TARGET_HEIGHT = _defaults.target_height

# --- Credenciais ---
USERNAME = _defaults.username
PASSWORD = _defaults.password

# --- Servidor ---
SERVER_NAME = _defaults.server_name

# --- Templates ---
TEMPLATES_DIR = _defaults.templates_dir

# --- Confianca minima no template matching ---
MATCH_THRESHOLD = _defaults.match_threshold

# --- Timeouts ---
TIMEOUT_LOGIN_SCREEN = _defaults.timeout_login_screen
TIMEOUT_SERVER_SCREEN = _defaults.timeout_server_selection
TIMEOUT_ENTER_GAME = _defaults.timeout_game_load
TIMEOUT_SERVER_QUEUE = _defaults.timeout_queue

# --- Retentativas ---
MAX_CONNECTION_RETRIES = _defaults.max_connection_retries
MAX_IP_RETRIES = _defaults.max_ip_retries

# --- Personagem ---
CHARACTER_SLOT = _defaults.character_slot
