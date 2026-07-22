from __future__ import annotations

from typing import Optional

from .exceptions import WindowNotFoundError

# -------------------------------------------------------------------------
# Camada de compatibilidade com o código legado.
#
# Enquanto a migração não é concluída, o WindowService delega as operações
# para window_utils.py. Futuramente esse arquivo poderá ser removido sem que
# o restante da aplicação precise ser alterado.
# -------------------------------------------------------------------------

from window_utils import (
    capture_window,
    find_window,
    get_client_size,
    wait_for_window,
)


class WindowService:
    """
    Serviço responsável pela comunicação com a janela do jogo.

    Esta classe encapsula toda interação relacionada ao HWND da aplicação.
    Nenhuma outra parte do sistema deve acessar diretamente window_utils.py.
    """

    def __init__(self):
        self._hwnd: Optional[int] = None

    @property
    def hwnd(self) -> int:
        """
        Retorna o HWND atualmente conectado.

        Raises:
            RuntimeError: Caso nenhuma janela tenha sido conectada.
        """
        if self._hwnd is None:
            raise RuntimeError("Nenhuma janela conectada.")

        return self._hwnd

    def connect(
        self,
        title_substring: str,
        timeout: float = 30.0,
    ) -> int:
        """
        Aguarda a janela do jogo aparecer e realiza a conexão.

        Args:
            title_substring: Parte do título da janela.
            timeout: Tempo máximo de espera.

        Returns:
            HWND da janela encontrada.

        Raises:
            WindowNotFoundError:
                Caso a janela não seja localizada.
        """

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

    def disconnect(self) -> None:
        """
        Desconecta da janela atual.
        """
        self._hwnd = None

    def is_connected(self) -> bool:
        """
        Indica se existe uma janela conectada.
        """
        return self._hwnd is not None

    def find(self, title_substring: str) -> Optional[int]:
        """
        Procura uma janela sem alterar o estado interno do serviço.
        """
        return find_window(title_substring)

    def capture(self):
        """
        Captura a client area da janela conectada.
        """
        return capture_window(self.hwnd)

    def client_size(self) -> tuple[int, int]:
        """
        Retorna o tamanho da client area da janela.
        """
        return get_client_size(self.hwnd)