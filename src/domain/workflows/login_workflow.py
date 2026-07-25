from src.domain.workflows.base_workflow import BaseWorkflow

from src.shared.templates import LoginTemplates
from src.shared.delays import Delays
from src.shared.keys import Keys
from src.shared.offsets import FieldOffsets


class LoginWorkflow(BaseWorkflow):
    """
    Workflow responsável por realizar o login no cliente do jogo.

    Este workflow apenas descreve o fluxo.
    Toda interação com o jogo acontece através do GameClient.
    """

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
        self.wait(5)

    # =====================================================
    # Tela de Login
    # =====================================================

    def wait_login_screen(self):

        self.log("Aguardando tela de login...")

        self.username_field = self.wait_template(
            LoginTemplates.USERNAME,
            timeout=self.settings.timeout_login_screen,
            offset=FieldOffsets.USERNAME,
        )

        if not self.username_field:
            raise TimeoutError(
                "Tela de login não apareceu."
            )

        self.log(
            f"Campo usuário localizado em {self.username_field}"
        )

    # =====================================================
    # Usuário
    # =====================================================

    def fill_username(self):

        self.log("Preenchendo usuário...")

        self.client.fill_field(
            self.username_field,
            self.settings.username,
        )

        self.client.wait(
            Delays.AFTER_FILL
        )

        self.log("Usuário preenchido.")

    # =====================================================
    # Senha
    # =====================================================

    def fill_password(self):

        password_field = self.find_template(
            LoginTemplates.PASSWORD,
            offset=FieldOffsets.PASSWORD,
        )

        if not password_field:
            raise RuntimeError(
                "Campo senha não encontrado."
            )

        self.log(
            f"Campo senha localizado em {password_field}"
        )

        self.log("Clicando no campo de senha...")

        self.click(password_field)

        self.wait(Delays.AFTER_CLICK)

        # Não limpamos o campo aqui: ele já começa vazio (tela de login
        # recém-carregada).

        self.log("Preenchendo senha...")

        self.write(self.settings.password)

        self.client.wait(
            Delays.AFTER_FILL
        )

        self.log("Senha preenchida.")

    # =====================================================
    # Entrar
    # =====================================================

    def click_login(self):

        login_button = self.find_template(
            LoginTemplates.LOGIN_BUTTON,
            
        )

        if not login_button:
            raise RuntimeError(
                "Botão Entrar não encontrado."
            )

        self.log(
            f"Botão Entrar localizado em {login_button}"
        )

        self.log("Clicando em Entrar...")

        self.click(
            login_button
        )

        self.wait(
            Delays.AFTER_LOGIN
        )

        self.log("Login enviado.")