class LoginWorkflow:

    def __init__(self, client, settings, logger=None):
        self.client = client
        self.settings = settings
        self.logger = logger

    def execute(self):
        self.connect()
        self.login()

    def connect(self):
        self.client.connect(
            title_substring=self.settings.WINDOW_TITLE,
            timeout=self.settings.TIMEOUT_LOGIN_SCREEN,
        )

    def login(self):

        print("Aguardando tela de login...")

        template = self.client.load_template("campo_usuario")

        pos = self.client.wait_template(
            template,
            timeout=self.settings.TIMEOUT_LOGIN_SCREEN,
            threshold=self.settings.MATCH_THRESHOLD,
        )

        if not pos:
            raise TimeoutError(
                "Tela de login não apareceu."
            )

        x, y = pos

        self.client.clear(x, y)

        self.client.type(
            self.settings.USERNAME
        )

        senha = self.client.load_template(
            "campo_senha"
        )

        pos = self.client.find_template(
            senha,
            threshold=self.settings.MATCH_THRESHOLD,
        )

        if not pos:
            raise RuntimeError(
                "Campo de senha não encontrado."
            )

        x, y = pos

        self.client.clear(x, y)

        self.client.type(
            self.settings.PASSWORD
        )

        entrar = self.client.load_template(
            "botao_entrar"
        )

        pos = self.client.find_template(
            entrar,
            threshold=self.settings.MATCH_THRESHOLD,
        )

        if not pos:
            raise RuntimeError(
                "Botão Entrar não encontrado."
            )

        self.client.click(*pos)