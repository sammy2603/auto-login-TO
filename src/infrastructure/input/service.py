from input_utils import (
    click_at,
    type_text,
    clear_field,
)


class InputService:
    """
    Adaptador para o módulo legado input_utils.py.

    Responsável exclusivamente por enviar entradas
    de mouse e teclado para a janela do jogo.
    """

    def click(
        self,
        hwnd,
        x: int,
        y: int,
    ):
        """
        Clica em uma posição da janela.
        """
        click_at(hwnd, x, y)

    def type(
        self,
        hwnd,
        text: str,
    ):
        """
        Digita um texto utilizando mensagens do Windows.
        """
        type_text(hwnd, text)

    def clear(
        self,
        hwnd,
        x: int,
        y: int,
    ):
        """
        Limpa um campo de texto.
        """
        clear_field(hwnd, x, y)

    def press_key(
        self,
        hwnd,
        key,
    ):
        """
        Pressiona uma tecla.

        Ainda será implementado.
        """
        raise NotImplementedError(
            "press_key ainda não implementado."
        )