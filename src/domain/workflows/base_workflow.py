import time


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
        offset=(0, 0),
    ):
        """
        Aguarda um template aparecer. Se 'offset' for informado, soma
        (dx, dy) à posição encontrada antes de retornar -- útil quando
        o template recortado é um rótulo/borda ao lado do campo real.
        """

        if timeout is None:
            timeout = self.settings.timeout_login_screen

        position = self.client.wait_template(
            template,
            timeout=timeout,
            threshold=self.settings.match_threshold,
        )

        if position is None:
            return None

        return self._apply_offset(position, offset)

    def find_template(
        self,
        template,
        offset=(0, 0),
    ):
        """
        Procura um template. Se 'offset' for informado, soma (dx, dy)
        à posição encontrada antes de retornar.
        """

        position = self.client.find_template(
            template,
            threshold=self.settings.match_threshold,
        )

        if position is None:
            return None

        return self._apply_offset(position, offset)

    @staticmethod
    def _apply_offset(position, offset):
        x, y = position
        dx, dy = offset
        return (x + dx, y + dy)

    def wait_template_patient(
        self,
        template,
        timeout,
        offset=(0, 0),
        poll_interval=3.0,
        heartbeat_interval=15.0,
        waiting_message="Ainda aguardando...",
    ):
        """
        Espera um template aparecer, mas de forma "paciente": feita
        pra esperas longas e incertas (ex: fila de servidor), onde não
        faz sentido ficar tentando a cada 0.5s nem falhar rápido.

        Loga uma mensagem periódica (a cada 'heartbeat_interval'
        segundos) pra deixar claro que o bot ainda está rodando, não
        travado.
        """

        start = time.time()
        last_heartbeat = start

        while True:
            position = self.find_template(template, offset=offset)

            if position:
                return position

            now = time.time()
            elapsed = now - start

            if elapsed >= timeout:
                return None

            if now - last_heartbeat >= heartbeat_interval:
                self.log(
                    f"{waiting_message} ({int(elapsed)}s decorridos, "
                    f"timeout em {int(timeout)}s)"
                )
                last_heartbeat = now

            time.sleep(poll_interval)

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

    def clear_current(
        self,
        max_chars: int = 30,
    ):
        """
        Limpa o campo que já está com foco, sem clicar (útil após TAB).
        """

        self.client.clear_current_field(
            max_chars=max_chars,
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