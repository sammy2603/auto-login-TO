class BaseWorkflow:
    """
    Classe base para todos os workflows da aplicação.

    Centraliza funcionalidades compartilhadas entre os fluxos,
    mantendo os workflows focados apenas na regra de negócio.
    """

    def __init__(
        self,
        client,
        settings,
        logger=None,
    ):
        self.client = client
        self.settings = settings
        self.logger = logger

    # =====================================================
    # Logging
    # =====================================================

    def log(self, message: str):
        """
        Escreve uma mensagem de log.
        """
        if self.logger:
            self.logger.info(message)
        else:
            print(f"[{self.__class__.__name__}] {message}")

    # =====================================================
    # Tempo
    # =====================================================

    def wait(self, seconds: float):
        """
        Aguarda um intervalo.
        """
        self.client.wait(seconds)

    # =====================================================
    # Vision
    # =====================================================

    def wait_template(
        self,
        template,
        timeout=None,
    ):
        """
        Aguarda um template aparecer.
        """

        if timeout is None:
            timeout = self.settings.timeout_login_screen

        return self.client.wait_template(
            template,
            timeout=timeout,
            threshold=self.settings.match_threshold,
        )

    def find_template(
        self,
        template,
    ):
        """
        Procura um template.
        """

        return self.client.find_template(
            template,
            threshold=self.settings.match_threshold,
        )

    def template_exists(
        self,
        template,
    ):
        """
        Verifica se um template existe.
        """

        return self.client.template_exists(
            template,
            threshold=self.settings.match_threshold,
        )

    # =====================================================
    # Input
    # =====================================================

    def fill(
        self,
        position,
        text,
    ):
        """
        Preenche um campo.
        """

        self.client.fill_field(
            position,
            text,
        )

    def click(
        self,
        position,
    ):
        """
        Clica em uma posição.
        """

        self.client.click_position(
            position,
        )

    def write(
        self,
        text,
    ):
        """
        Digita um texto.
        """

        self.client.write(text)

    def press_key(
        self,
        key,
    ):
        """
        Pressiona uma tecla.
        """

        self.client.press_key(key)