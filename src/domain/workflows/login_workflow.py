import time


class LoginWorkflow:
    """
    Workflow responsável pelo login no jogo.

    Ele orquestra o fluxo de autenticação utilizando apenas
    a API pública do GameClient.
    """

    def __init__(self, client, settings, logger=None):
        self.client = client
        self.settings = settings
        self.logger = logger

        self.username_position = None

    # =====================================================
    # Util
    # =====================================================

    def log(self, message: str):
        if self.logger:
            self.logger.info(message)
        else:
            print(f"[LoginWorkflow] {message}")

    # =====================================================
    # Fluxo principal
    # =====================================================

    def execute(self):
        self.launch_client()
        self.connect()
        self.wait_login_screen()
        self.fill_username()
        self.fill_password()
        self.click_login()

    # =====================================================
    # Cliente
    # =====================================================

    def launch_client(self):

        self.log("Abrindo cliente do jogo...")

        self.client.launch(
            self.settings.client_path
        )

    # =====================================================
    # Janela
    # =====================================================

    def connect(self):

        self.log("Aguardando janela...")

        self.client.connect(
            title_substring=self.settings.window_title,
            timeout=self.settings.timeout_login_screen,
        )

        self.log("Janela encontrada.")

    # =====================================================
    # Tela de Login
    # =====================================================

    def wait_login_screen(self):

        self.log("Aguardando tela de login...")

        pos = self.client.wait_template(
            "campo_usuario",
            timeout=self.settings.timeout_login_screen,
            threshold=self.settings.match_threshold,
        )

        if not pos:
            raise TimeoutError(
                "Tela de login não apareceu."
            )

        self.username_position = pos

        self.log(
            f"Campo usuário localizado em {pos}"
        )

    # =====================================================
    # Usuário
    # =====================================================

    def fill_username(self):

        self.log("Preenchendo usuário...")

        self.client.fill_field(
            self.username_position,
            self.settings.username,
        )

        self.log("Usuário preenchido.")

        time.sleep(0.5)

    # =====================================================
    # Senha
    # =====================================================

    def fill_password(self):

        pos = self.client.find_template(
            "campo_senha",
            threshold=self.settings.match_threshold,
        )

        if not pos:
            raise RuntimeError(
                "Campo de senha não encontrado."
            )

        self.log(
            f"Campo senha localizado em {pos}"
        )

        self.log("Preenchendo senha...")

        self.client.fill_field(
            pos,
            self.settings.password,
        )

        self.log("Senha preenchida.")

        time.sleep(0.5)

    # =====================================================
    # Entrar
    # =====================================================

    def click_login(self):

        pos = self.client.find_template(
            "botao_entrar",
            threshold=self.settings.match_threshold,
        )

        if not pos:
            raise RuntimeError(
                "Botão Entrar não encontrado."
            )

        self.log(
            f"Botão Entrar localizado em {pos}"
        )

        self.log("Clicando em Entrar...")

        self.client.click(*pos)

        time.sleep(0.3)

        self.log("Login enviado.")