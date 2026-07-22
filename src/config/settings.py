from __future__ import annotations

import config


class Settings:
    """
    Centraliza todas as configurações utilizadas pela aplicação.

    Atualmente utiliza o módulo legado config.py como fonte dos valores.
    No futuro, poderá carregar configurações de arquivos, banco de dados
    ou variáveis de ambiente sem impactar o restante da aplicação.
    """

    def __init__(self):
        self.window_title = config.WINDOW_TITLE

        self.username = config.USERNAME
        self.password = config.PASSWORD

        self.match_threshold = config.MATCH_THRESHOLD

        self.timeout_login_screen = config.TIMEOUT_LOGIN_SCREEN
        self.timeout_server_selection = config.TIMEOUT_SERVER_SELECTION
        self.timeout_game_load = config.TIMEOUT_ENTER_GAME

        self.server_name = config.SERVER_NAME