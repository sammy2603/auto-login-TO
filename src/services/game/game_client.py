from __future__ import annotations

import time

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
        launcher,
    ):
        self.window = window_service
        self.vision = vision_service
        self.input = input_service
        self.launcher = launcher

    # =====================================================
    # Window
    # =====================================================
    def launch(self, client_path: str):
        self.launcher.launch(client_path)

    def fill_text(
            self,
            position,
            text: str,
            click_delay: float = 0.25,
            clear_delay: float = 0.15,
        ):
            """
            Preenche um campo de texto.
    
            Fluxo:
    
                clique
                    ↓
                espera
                    ↓
                limpa
                    ↓
                espera
                    ↓
                digita
            """
    
            x, y = position
    
            self.click(x, y)
    
            time.sleep(click_delay)
    
            self.clear(x, y)
    
            time.sleep(clear_delay)
    
            self.type_text(text)
            
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
    # =====================================================
# Input
# =====================================================

import time


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