from __future__ import annotations


class GameClient:
    """
    Fachada responsável por expor operações de alto nível para interação
    com o cliente do jogo.

    O GameClient não implementa regras de negócio. Ele apenas coordena
    WindowService, VisionService e InputService.
    """

    def __init__(
        self,
        window_service,
        vision_service,
        input_service,
    ):
        self.window = window_service
        self.vision = vision_service
        self.input = input_service

    # =====================================================
    # Window
    # =====================================================

    def connect(
        self,
        title_substring: str,
        timeout: float = 30.0,
    ):
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

    def load_template(self, name: str):
        return self.vision.load_template(name)

    def find_template(
        self,
        template,
        threshold: float = 0.90,
    ):
        return self.vision.find_template(
            hwnd=self.hwnd,
            template=template,
            threshold=threshold,
        )

    def wait_template(
        self,
        template,
        timeout: float = 30.0,
        threshold: float = 0.90,
    ):
        return self.vision.wait_template(
            hwnd=self.hwnd,
            template=template,
            timeout=timeout,
            threshold=threshold,
        )

    # =====================================================
    # Input
    # =====================================================

    def click(self, x: int, y: int):
        return self.input.click(self.hwnd, x, y)

    def type_text(self, text: str):
        return self.input.type(self.hwnd, text)

    def clear(self, x: int, y: int):
        return self.input.clear(self.hwnd, x, y)

    def press_key(self, key):
        return self.input.press_key(self.hwnd, key)

    def is_connected(self):
        return self.window.is_connected()