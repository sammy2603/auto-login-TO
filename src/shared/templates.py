class LoginTemplates:
    """
    Templates utilizados durante o login.
    """

    USERNAME = "campo_usuario"
    PASSWORD = "campo_senha"
    LOGIN_BUTTON = "botao_entrar"


class ServerTemplates:
    """
    Templates utilizados na seleção de servidor.
    """

    CONFIRM_BUTTON = "botao_confirmar_servidor"

    @staticmethod
    def server(server_name: str) -> str:
        """
        Retorna o template correspondente ao servidor configurado.

        Exemplo:
            servidor_360
            servidor_pvp
            servidor_test
        """
        return f"servidor_{server_name}"


class CharacterTemplates:
    """
    Templates da tela de seleção de personagem.

    (Será utilizado na próxima etapa.)
    """

    ENTER_GAME_BUTTON = "botao_entrar_jogo"


class GameTemplates:
    """
    Templates utilizados para confirmar que o jogo carregou.
    """

    HUD = "tela_jogo_carregada"


# Não existe ErrorTemplates: as mensagens de erro do client não são
# reconhecidas por imagem. São muitas, e todas levam à mesma ação --
# ESC pra fechar e tentar de novo (ver BaseWorkflow.dismiss_dialogs).
# O que decide o fluxo é a tela que a gente ESPERAVA ver aparecer.