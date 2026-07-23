import time


class LoginWorkflow:

    def __init__(self, client, settings, logger=None):
        self.client = client
        self.settings = settings
        self.logger = logger

    def log(self, message: str):
        if self.logger:
            self.logger.info(message)
        else:
            print(f"[LoginWorkflow] {message}")

    def execute(self):
        self.connect()
        self.login()

    def connect(self):

        self.log("Abrindo cliente do jogo...")

        self.client.launch(
            self.settings.client_path
        )

        self.log("Aguardando janela...")

        self.client.connect(
            title_substring=self.settings.window_title,
            timeout=self.settings.timeout_login_screen,
        )

        self.log("Janela encontrada.")

    def login(self):

        self.log("Aguardando tela de login...")

        usuario = self.client.load_template(
            "campo_usuario"
        )

        pos = self.client.wait_template(
            usuario,
            timeout=self.settings.timeout_login_screen,
            threshold=self.settings.match_threshold,
        )

        if not pos:
            raise TimeoutError(
                "Tela de login não apareceu."
            )

        self.log(f"Campo usuário localizado em {pos}")

        self.log("Preenchendo usuário...")

        self.client.fill_text(
            position=pos,
            text=self.settings.username,
        )

        self.log("Usuário preenchido.")

        time.sleep(0.5)

        senha = self.client.load_template(
            "campo_senha"
        )

        pos = self.client.find_template(
            senha,
            threshold=self.settings.match_threshold,
        )

        if not pos:
            raise RuntimeError(
                "Campo de senha não encontrado."
            )

        self.log(f"Campo senha localizado em {pos}")

        self.log("Limpando campo senha...")
        
        self.log("Preenchendo senha...")

        self.client.fill_text(
            position=pos,
            text=self.settings.password,
        )

        self.log("Senha preenchida.")

        time.sleep(0.5)

        entrar = self.client.load_template(
            "botao_entrar"
        )

        pos = self.client.find_template(
            entrar,
            threshold=self.settings.match_threshold,
        )

        if not pos:
            raise RuntimeError(
                "Botão Entrar não encontrado."
            )

        self.log(f"Botão Entrar localizado em {pos}")

        self.log("Clicando em Entrar...")

        self.client.click(*pos)

        time.sleep(0.25)

        self.log("Login enviado.")