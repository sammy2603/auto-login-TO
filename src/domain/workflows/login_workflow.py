from __future__ import annotations


class LoginWorkflow:
    """
    Workflow responsável pelo processo completo de login.

    Este workflow descreve apenas as regras de negócio.
    Toda interação com o jogo é realizada através do GameClient.
    """

    def __init__(self, client, settings, logger=None):
        self.client = client
        self.settings = settings
        self.logger = logger

    # ------------------------------------------------------------------
    # Fluxo principal
    # ------------------------------------------------------------------

    def execute(self):
        self.connect()
        self.wait_login_screen()
        self.fill_username()
        self.fill_password()
        self.click_login()

    # ------------------------------------------------------------------
    # Etapas
    # ------------------------------------------------------------------

    def connect(self):
        print("Conectando à janela do jogo...")

        self.client.connect(
            title_substring=self.settings.WINDOW_TITLE,
            timeout=self.settings.TIMEOUT_LOGIN_SCREEN,
        )

    def wait_login_screen(self):
        print("Aguardando tela de login...")

        self.username_field = self.client.load_template(
            "campo_usuario"
        )

        pos = self.client.wait_template(
            self.username_field,
            timeout=self.settings.TIMEOUT_LOGIN_SCREEN,
            threshold=self.settings.MATCH_THRESHOLD,
        )

        if pos is None:
            raise TimeoutError(
                "Tela de login não apareceu."
            )

    def fill_username(self):
        print("Preenchendo usuário...")

        pos = self.client.find_template(
            self.username_field,
            threshold=self.settings.MATCH_THRESHOLD,
        )

        if pos is None:
            raise RuntimeError(
                "Campo de usuário não encontrado."
            )

        x, y = pos

        self.client.clear(x, y)
        self.client.type_text(
            self.settings.USERNAME
        )

    def fill_password(self):
        print("Preenchendo senha...")

        template = self.client.load_template(
            "campo_senha"
        )

        pos = self.client.find_template(
            template,
            threshold=self.settings.MATCH_THRESHOLD,
        )

        if pos is None:
            raise RuntimeError(
                "Campo de senha não encontrado."
            )

        x, y = pos

        self.client.clear(x, y)
        self.client.type_text(
            self.settings.PASSWORD
        )

    def click_login(self):
        print("Clicando em Entrar...")

        template = self.client.load_template(
            "botao_entrar"
        )

        pos = self.client.find_template(
            template,
            threshold=self.settings.MATCH_THRESHOLD,
        )

        if pos is None:
            raise RuntimeError(
                "Botão Entrar não encontrado."
            )

        self.client.click(*pos)