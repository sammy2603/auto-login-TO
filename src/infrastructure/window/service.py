from __future__ import annotations

from typing import Optional

from .exceptions import WindowNotFoundError

from window_utils import (
    capture_window,
    find_window,
    find_window_by_pid,
    get_client_size,
    get_window_pid,
    list_windows,
    wait_for_new_window,
    wait_for_window,
    wait_for_window_by_pid,
)


class WindowService:
    """
    Serviço responsável pela comunicação com a janela do jogo.

    Toda a aplicação deve conversar apenas com esta classe.
    """

    def __init__(self):
        self._hwnd: Optional[int] = None

    # =====================================================
    # Propriedades
    # =====================================================

    @property
    def hwnd(self) -> int:

        if self._hwnd is None:
            raise RuntimeError(
                "Nenhuma janela conectada."
            )

        return self._hwnd

    # =====================================================
    # Conexão
    # =====================================================

    def connect_new_window(
        self,
        timeout: float = 30.0,
    ) -> tuple[int, int]:
        """
        Aguarda o surgimento de uma nova janela.

        Retorna:
            (hwnd, pid)
        """

        previous_windows = list_windows()

        hwnd = wait_for_new_window(
            previous_windows,
            timeout=timeout,
        )

        if hwnd is None:
            raise WindowNotFoundError(
                "Nenhuma nova janela foi encontrada."
            )

        self._hwnd = hwnd

        pid = get_window_pid(hwnd)

        return hwnd, pid

    def connect(
        self,
        title_substring: str | None = None,
        pid: int | None = None,
        timeout: float = 30.0,
    ) -> int:
        """
        Conecta a uma janela.

        Pode localizar por:
            - título (compatibilidade)
            - PID (novo modelo)
        """

        if pid is not None:

            hwnd = wait_for_window_by_pid(
                pid=pid,
                timeout=timeout,
            )

            if hwnd is None:
                raise WindowNotFoundError(
                    f"Não foi possível localizar uma janela para o PID {pid}."
                )

        else:

            if title_substring is None:
                raise ValueError(
                    "title_substring ou pid devem ser informados."
                )

            hwnd = wait_for_window(
                title_substring,
                timeout=timeout,
            )

            if hwnd is None:
                raise WindowNotFoundError(
                    f"Não foi possível localizar a janela '{title_substring}'."
                )

        self._hwnd = hwnd

        return hwnd

    def disconnect(self):

        self._hwnd = None

    def is_connected(self):

        return self._hwnd is not None

    # =====================================================
    # Busca
    # =====================================================

    def find(
        self,
        title_substring: str,
    ) -> Optional[int]:

        return find_window(title_substring)

    def find_by_pid(
        self,
        pid: int,
    ) -> Optional[int]:

        return find_window_by_pid(pid)

    # =====================================================
    # Captura
    # =====================================================

    def capture(self):

        return capture_window(self.hwnd)

    def client_size(self):

        return get_client_size(self.hwnd)