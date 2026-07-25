from __future__ import annotations

import time

import win32api
import win32con

# Mapa de teclas simbólicas (src/shared/keys.py -> Keys.TAB, Keys.ENTER...)
# para os códigos de tecla virtual do Windows.
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
    Serviço responsável por enviar entradas de mouse e teclado para a
    janela do jogo -- via mensagens do Windows (PostMessage), sem
    mover o cursor físico nem usar o teclado real. Isso garante que a
    automação não interfere no uso do PC pela pessoa.

    IMPORTANTE: essa técnica funciona bem em janelas GDI/DirectX
    "clássicas". Se o jogo usar DirectInput/RawInput para capturar
    cliques, pode não reagir a essas mensagens simuladas.
    """

    # =====================================================
    # Mouse
    # =====================================================

    def click(self, hwnd, x: int, y: int, delay: float = 0.05):
        """
        Simula um clique esquerdo do mouse nas coordenadas (x, y) da
        client area de 'hwnd'. Não move o cursor real.
        """

        lparam = self._make_lparam(x, y)

        win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    # =====================================================
    # Teclado
    # =====================================================

    def type_text(self, hwnd, text: str, delay: float = 0.06):
        """
        Envia texto caractere por caractere para a janela, via
        WM_CHAR. Não usa o teclado físico.
        """

        for char in text:
            win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
            time.sleep(delay)

    def press_key(self, hwnd, key, delay: float = 0.05):
        """
        Pressiona uma tecla. Aceita tanto a chave simbólica (ex: "TAB",
        vinda de src.shared.keys.Keys) quanto um código de tecla
        virtual (int) diretamente.
        """

        vk_code = _VK_MAP.get(key, key) if isinstance(key, str) else key

        if not isinstance(vk_code, int):
            raise ValueError(f"Tecla não reconhecida: {key!r}")

        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)

    # =====================================================
    # Limpeza de campos
    # =====================================================

    def clear(self, hwnd, x: int, y: int, max_chars: int = 30):
        """
        Clica no campo e envia BACKSPACE várias vezes para limpar
        texto pré-existente antes de digitar.
        """

        self.click(hwnd, x, y)
        time.sleep(0.1)

        for _ in range(max_chars):
            self.press_key(hwnd, win32con.VK_BACK, delay=0.01)

    def clear_current(self, hwnd, max_chars: int = 30):
        """
        Limpa o campo que já está com foco (via BACKSPACE), sem clicar
        em nenhuma posição. Útil depois de navegar entre campos com
        TAB, onde clicar de novo poderia tirar o foco do campo certo.
        """

        for _ in range(max_chars):
            self.press_key(hwnd, win32con.VK_BACK, delay=0.01)

    # =====================================================
    # Implementação interna
    # =====================================================

    @staticmethod
    def _make_lparam(x: int, y: int) -> int:
        """
        Codifica coordenadas (x, y) no formato usado pelas mensagens
        do Windows.
        """
        return (y << 16) | (x & 0xFFFF)