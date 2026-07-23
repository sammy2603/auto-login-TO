"""
Estados conhecidos do cliente do jogo.

No futuro o GameClient poderá perguntar:

client.is_screen(Screens.LOGIN)
"""


class Screens:

    LOGIN = "login"

    SERVER_SELECTION = "server_selection"

    CHARACTER_SELECTION = "character_selection"

    GAME = "game"