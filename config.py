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
SERVER_NAME = "White Horse"

# --- Pasta onde ficam as imagens de referência (templates) ---
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# --- Confiança mínima no reconhecimento de imagem (0 a 1) ---
MATCH_THRESHOLD = 0.85

# --- Timeouts (segundos) ---
TIMEOUT_LOGIN_SCREEN = 30
TIMEOUT_SERVER_SCREEN = 20
TIMEOUT_ENTER_GAME = 30

# Tempo máximo de espera na fila do servidor até a tela de seleção de
# personagem aparecer. Filas podem demorar bastante -- ajuste esse
# valor conforme a experiência real com o servidor usado.
# Padrão: 30 minutos.
TIMEOUT_SERVER_QUEUE = 1800

# Quantas vezes o bot tenta de novo se a conexão for interrompida
# (servidor indisponível) antes de desistir.
MAX_CONNECTION_RETRIES = 5

# Qual personagem selecionar na tela de seleção (a conta pode ter até
# 3, alinhados da esquerda pra direita). Valores: "LEFT", "CENTER" ou
# "RIGHT".
CHARACTER_SLOT = "RIGHT"

# Quantas vezes o bot tenta de novo (clicar OK + Entrar) se o popup
# "Acquiring server IP address" aparecer repetidamente após o login.
MAX_IP_RETRIES = 10