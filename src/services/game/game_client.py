from __future__ import annotations

import time


class GameClient:
    """
    Fachada responsável por expor operações de alto nível para interação
    com o cliente do jogo.

    O GameClient não implementa regras de negócio.
    Ele apenas coordena os serviços de infraestrutura.
    """

    def __init__(
        self,
        window_service,
        vision_service,
        input_service,
        launcher,
    ):
        self.window = window_service
        self.vision = vision_service
        self.input = input_service
        self.launcher = launcher

    # =====================================================
    # Launcher
    # =====================================================

    def launch(self, client_path: str):
        """
        Abre o cliente do jogo.
        """
        self.launcher.launch(client_path)

    # =====================================================
    # Window
    # =====================================================

    def connect(
        self,
        title_substring: str,
        timeout: float = 30.0,
    ):
        """
        Conecta à janela do jogo.
        """
        self.window.connect(
            title_substring=title_substring,
            timeout=timeout,
        )

    @property
    def hwnd(self):
        return self.window.hwnd

    def capture(self):
        return self.window.capture()

    def client_size(self):
        return self.window.client_size()

    # =====================================================
    # Vision
    # =====================================================

    def wait_template(
        self,
        template_name: str,
        timeout: float = 30.0,
        threshold: float = 0.90,
    ):
        """
        Aguarda um template aparecer na janela.
        """

        return self.vision.wait_template(
            hwnd=self.hwnd,
            template=template_name,
            timeout=timeout,
            threshold=threshold,
        )

    def find_template(
        self,
        template_name: str,
        threshold: float = 0.90,
    ):
        """
        Procura um template na janela.
        """

        return self.vision.find_template(
            hwnd=self.hwnd,
            template=template_name,
            threshold=threshold,
        )

    # =====================================================
    # Mouse
    # =====================================================

    def click(
        self,
        x: int,
        y: int,
    ):
        self.input.click(
            self.hwnd,
            x,
            y,
        )

    # =====================================================
    # Keyboard
    # =====================================================

    def type_text(
        self,
        text: str,
    ):
        self.input.type_text(
            self.hwnd,
            text,
        )

    def clear(
        self,
        x: int,
        y: int,
    ):
        self.input.clear(
            self.hwnd,
            x,
            y,
        )

    def fill_field(
        self,
        position,
        text: str,
        click_delay: float = 0.25,
        clear_delay: float = 0.15,
    ):
        """
        Realiza todo o fluxo necessário para preencher um campo.
        """

        x, y = position

        self.click(x, y)

        time.sleep(click_delay)

        self.clear(x, y)

        time.sleep(clear_delay)

        self.type_text(text)

    def press_key(
        self,
        key,
    ):
        self.input.press_key(
            self.hwnd,
            key,
        )