"""
Templates utilizados pelo sistema de visão.

Os nomes NÃO possuem extensão ".png".
A responsabilidade de localizar o arquivo é do VisionService.
"""


class LoginTemplates:
    USERNAME = "campo_usuario"
    PASSWORD = "campo_senha"
    LOGIN_BUTTON = "botao_entrar"


class ServerTemplates:
    SERVER_LIST = "lista_servidores"
    SERVER_CONFIRM = "botao_confirmar_servidor"


class CharacterTemplates:
    CHARACTER_LIST = "lista_personagens"
    ENTER_GAME = "botao_entrar_jogo"


class HudTemplates:
    HP_BAR = "hud_hp"
    MP_BAR = "hud_mp"