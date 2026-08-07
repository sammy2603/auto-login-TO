from src.domain.workflows.base_workflow import BaseWorkflow

from src.shared.templates import LoginTemplates, ServerTemplates
from src.shared.delays import Delays
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

        # Trava compartilhada entre contas: garante que "abrir o
        # client + detectar a janela nova" acontece de forma atômica,
        # mesmo com várias contas rodando em paralelo (evita o bot
        # confundir qual janela pertence a qual conta). O resto do
        # fluxo roda solto, em paralelo com as outras contas.
        with self.client.launch_lock:

            self.launch_client()

            self.connect()

        self.login_until_server_screen()

    # =====================================================
    # Laço de login
    # =====================================================

    def login_until_server_screen(self):
        """
        Preenche as credenciais e clica em Entrar, repetindo até a tela
        de servidores aparecer.

        Não há tratamento por tipo de erro. As mensagens que o client
        pode mostrar são muitas ("Acquiring server IP address", conta em
        uso, servidor em manutenção...) e recortar um template pra cada
        uma é trabalho que nunca acaba -- e que só serve pra chegar na
        mesma conclusão: não passamos da tela de login. Então a checagem
        é uma só (a tela de servidores apareceu?) e o tratamento é um só
        (ESC no que estiver na frente e tentar de novo).

        O laço não tem limite de tentativas de propósito: desistir não
        deixa a conta logada, só deixa o client parado sem ninguém
        olhando.
        """

        attempt = 1

        while True:

            self.wait_login_screen()

            self.fill_username()

            self.fill_password()

            self.click_login()

            if self.server_screen_appeared():
                self.log("Login concluído.")
                return

            self.log(
                f"Tela de servidores não apareceu (tentativa {attempt}). "
                "Fechando diálogos e preenchendo de novo..."
            )

            self.dismiss_dialogs()

            attempt += 1

    def server_screen_appeared(self) -> bool:
        """
        Único sinal de sucesso do login: o servidor configurado apareceu
        na lista.

        É o mesmo template que o ServerWorkflow usa em seguida -- aqui
        ele serve só como "passamos da tela de login", e lá como "clica
        aqui".
        """

        posicao = self.wait_template(
            ServerTemplates.server(self.settings.server_name),
            timeout=self.settings.timeout_server_selection,
        )

        return posicao is not None

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

        self.rename_window()

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

        self.wait(Delays.FIELD_FOCUS_DELAY)

        # Limpa mesmo com o campo em geral já vazio: numa retentativa a
        # senha anterior ainda está lá, e digitar por cima mandaria as
        # duas juntas -- sem dar pra notar, já que o campo é mascarado.
        self.clear_current()

        self.wait(Delays.AFTER_CLEAR)

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
            f"Clicando em Entrar (localizado em {login_button})..."
        )

        self.click(
            login_button
        )

        self.wait(
            Delays.AFTER_LOGIN
        )

        self.log("Login enviado.")

    # =====================================================
    # Retentativa (após conexão interrompida)
    # =====================================================

    def retry_login(self):
        """
        Refaz o login sem reabrir o client nem reconectar à janela --
        usado quando o jogo volta pra tela de login sozinho (ex: após
        um popup de "conexão interrompida"). O client já está aberto e
        a janela já está conectada, só precisamos preencher os campos
        de novo.
        """

        self.log("Refazendo login...")

        self.wait(Delays.SCREEN_TRANSITION)

        self.login_until_server_screen()