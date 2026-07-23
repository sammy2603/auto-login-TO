from __future__ import annotations

from input_utils import (
    click_at,
    type_text,
    clear_field,
)


class InputService:
    """
    Serviço responsável por enviar entradas de mouse e teclado
    para a janela do jogo.

    Atualmente atua como um adaptador para o módulo legado
    `input_utils.py`.
    """

    def click(
        self,
        hwnd,
        x: int,
        y: int,
    ) -> None:
        """
        Realiza um clique na posição informada.
        """
        click_at(hwnd, x, y)

    def type_text(
        self,
        hwnd,
        text: str,
    ) -> None:
        """
        Digita um texto utilizando mensagens do Windows.
        """
        type_text(hwnd, text)

    def clear(
        self,
        hwnd,
        x: int,
        y: int,
    ) -> None:
        """
        Limpa o conteúdo de um campo de texto.
        """
        clear_field(hwnd, x, y)

    def press_key(
        self,
        hwnd,
        key,
    ) -> None:
        """
        Pressiona uma tecla.

        Implementação futura.
        """
        raise NotImplementedError(
            "press_key ainda não implementado."
        )