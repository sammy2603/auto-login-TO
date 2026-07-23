from dataclasses import dataclass

import config


@dataclass(frozen=True)
class Settings:
    """
    Configurações da aplicação.

    Atualmente utiliza o módulo legado config.py
    como fonte dos valores.
    """

    client_path: str = config.CLIENT_PATH

    window_title: str = config.WINDOW_TITLE

    username: str = config.USERNAME
    password: str = config.PASSWORD

    match_threshold: float = config.MATCH_THRESHOLD

    timeout_login_screen: float = config.TIMEOUT_LOGIN_SCREEN

    timeout_server_selection: float = config.TIMEOUT_SERVER_SCREEN

    timeout_game_load: float = config.TIMEOUT_ENTER_GAME

    server_name: str = config.SERVER_NAME