from __future__ import annotations

from typing import Optional

from window_utils import (
    find_window,
    wait_for_window,
    capture_window,
    get_client_size,
)


class WindowService:
    """
    Responsável pela comunicação com a janela do jogo.
    """

    def __init__(self):
        self._hwnd: Optional[int] = None

    @property
    def hwnd(self) -> int:
        if self._hwnd is None:
            raise RuntimeError("Nenhuma janela conectada.")
        return self._hwnd

    def connect(
        self,
        title_substring: str,
        timeout: float = 30.0,
    ) -> bool:
        """
        Procura e conecta à janela do jogo.
        """
        from .exceptions import WindowNotFoundError
        hwnd = wait_for_window(
            title_substring,
            timeout=timeout,
        )

        if hwnd is None:
            raise WindowNotFoundError(
                f"Não foi possível localizar a janela '{title_substring}'."
    )

        self._hwnd = hwnd
        return True

    def disconnect(self):
        self._hwnd = None

    def is_connected(self) -> bool:
        return self._hwnd is not None

    def find(self, title_substring: str):
        return find_window(title_substring)

    def capture(self):
        return capture_window(self.hwnd)

    def client_size(self):
        return get_client_size(self.hwnd)