"""
Estados conhecidos do cliente do jogo.

No futuro o GameClient poderá perguntar:

client.is_screen(Screens.LOGIN)
"""


class Screens:

    LOGIN = "Login"

    SERVER_SELECTION = "Server Selection"

    CHARACTER_SELECTION = "Character Selection"

    GAME = "Game"

    DISCONNECTED = "Disconnected"