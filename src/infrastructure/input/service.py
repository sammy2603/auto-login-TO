from __future__ import annotations

import win32con

from input_utils import (
    click_at,
    type_text,
    clear_field,
    clear_current_field,
    press_key as _press_key,
)

# Mapa de teclas simbólicas (src/shared/keys.py -> Keys.TAB, Keys.ENTER...)
# para os códigos de tecla virtual do Windows usados pelo input_utils.
_VK_MAP = {
    "ENTER": win32con.VK_RETURN,
    "ESC": win32con.VK_ESCAPE,
    "TAB": win32con.VK_TAB,
    "UP": win32con.VK_UP,
    "DOWN": win32con.VK_DOWN,
    "LEFT": win32con.VK_LEFT,
    "RIGHT": win32con.VK_RIGHT,
}


class InputService:
    """
        Adaptador responsável por enviar entradas de mouse e teclado
        para a janela do jogo.

        Encapsula o módulo legado input_utils.py até que ele seja
        substituído por uma implementação própria.
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
        Limpa o conteúdo de um campo de texto (clicando nele primeiro).
        """
        clear_field(hwnd, x, y)

    def clear_current(
        self,
        hwnd,
        max_chars: int = 30,
    ) -> None:
        """
        Limpa o campo que já está com foco, sem clicar em nenhuma
        posição (útil após navegar com TAB).
        """
        clear_current_field(hwnd, max_chars=max_chars)

    def press_key(
        self,
        hwnd,
        key,
    ) -> None:
        """
        Pressiona uma tecla. Aceita tanto a chave simbólica (ex: "TAB",
        vinda de src.shared.keys.Keys) quanto um código de tecla
        virtual (int) diretamente.
        """
        vk_code = _VK_MAP.get(key, key) if isinstance(key, str) else key

        if not isinstance(vk_code, int):
            raise ValueError(f"Tecla não reconhecida: {key!r}")

        _press_key(hwnd, vk_code)