# -*- coding: utf-8 -*-
"""
Configurações centrais do bot de login do Talisman Online.
Ajuste os caminhos e o título da janela conforme seu ambiente.
"""

import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (se existir) para o ambiente do processo.
# Deve rodar antes de ler USERNAME/PASSWORD abaixo.
load_dotenv()

# --- Caminho do executável do client ---
CLIENT_PATH = r"C:\Users\Sammy\Documents\TalismanOnline - 360\start.bat"

# --- Título (ou parte do título) da janela do jogo ---
# Use o utilitário tools/find_window_title.py para descobrir o nome exato.
WINDOW_TITLE = "Talisman Online"

# --- Resolução alvo (fixa, conforme combinado) ---
TARGET_WIDTH = 1024
TARGET_HEIGHT = 768

# --- Credenciais ---
# NUNCA deixe usuário/senha hardcoded aqui em produção.
# Recomendado: variáveis de ambiente ou keyring (biblioteca 'keyring').
USERNAME = os.environ.get("TALISMAN_USER", "")
PASSWORD = os.environ.get("TALISMAN_PASS", "")

# --- Nome do servidor a selecionar (usado para nomear o template) ---
SERVER_NAME = "Sky Ice"

# --- Pasta onde ficam as imagens de referência (templates) ---
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# --- Confiança mínima no reconhecimento de imagem (0 a 1) ---
MATCH_THRESHOLD = 0.85

# --- Timeouts (segundos) ---
TIMEOUT_LOGIN_SCREEN = 30
TIMEOUT_SERVER_SCREEN = 20
TIMEOUT_ENTER_GAME = 30# -*- coding: utf-8 -*-
