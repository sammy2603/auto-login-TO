# -*- coding: utf-8 -*-
"""
Configuracoes centrais da aplicacao.
Fonte unica da verdade para todos os valores de configuracao.

Nao depende de mais nada alem das variaveis de ambiente (.env).
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_TEMPLATES_DIR = str(Path(__file__).resolve().parents[2] / "templates")


@dataclass(frozen=True)
class Settings:
    """
    Configuracoes imutaveis da aplicacao.

    Todos os valores possuem defaults razoaveis e podem ser
    sobrescritos no momento da construcao (ex: pela GUI ao logar
    uma conta especifica).
    """

    # --- Caminho do executavel do client ---
    client_path: str = (
        r"C:\Users\Sammy\Documents\TalismanOnline - 360\start.bat"
    )

    # --- Titulo (ou parte do titulo) da janela do jogo ---
    window_title: str = "Talisman Online"

    # --- Resolucao alvo (fixa) ---
    target_width: int = 1024
    target_height: int = 768

    # --- Credenciais (via .env) ---
    username: str = os.environ.get("TALISMAN_USER", "")
    password: str = os.environ.get("TALISMAN_PASS", "")

    # --- Nome do servidor (usado para nomear o template) ---
    server_name: str = "White Horse"

    # --- Pasta de templates (caminho absoluto) ---
    templates_dir: str = _TEMPLATES_DIR

    # --- Confianca minima no template matching (0 a 1) ---
    match_threshold: float = 0.85

    # --- Timeouts (segundos) ---
    timeout_login_screen: float = 30.0
    timeout_server_selection: float = 20.0
    timeout_game_load: float = 30.0
    timeout_queue: float = 1800.0

    # --- Tentativas em caso de conexao interrompida ---
    max_connection_retries: int = 5
    max_ip_retries: int = 10

    # --- Slot de personagem: LEFT, CENTER ou RIGHT ---
    character_slot: str = "RIGHT"

    # --- Apelido da conta (preenche a janela, exibido nos logs) ---
    account_label: str = ""
