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

    # Mapa de teclas para scan codes (necessario para alguns jogos)
    _SCAN_MAP = {
        "TAB": 0x0F,
        "ENTER": 0x1C,
        "ESC": 0x01,
        "UP": 0x48,
        "DOWN": 0x50,
        "LEFT": 0x4B,
        "RIGHT": 0x4D,
        " ": 0x39,      # space
        "0": 0x0B, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05,
        "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09, "9": 0x0A,
        "A": 0x1E, "B": 0x30, "C": 0x2E, "D": 0x20, "E": 0x12,
        "F": 0x21, "G": 0x22, "H": 0x23, "I": 0x17, "J": 0x24,
        "K": 0x25, "L": 0x26, "M": 0x32, "N": 0x31, "O": 0x18,
        "P": 0x19, "Q": 0x10, "R": 0x13, "S": 0x1F, "T": 0x14,
        "U": 0x16, "V": 0x2F, "W": 0x11, "X": 0x2D, "Y": 0x15,
        "Z": 0x2C,
    }

    def press_key(self, hwnd, key, delay: float = 0.05):
        """
        Pressiona uma tecla. Aceita:
        - Chave simbolica (ex: "TAB", "ENTER")
        - Codigo de tecla virtual (int)
        - Caractere unico (ex: "1", "a", "F5")
        """

        if isinstance(key, int):
            vk_code = key
            scan = 0
        elif isinstance(key, str) and len(key) == 1:
            vk_code = ord(key.upper()) if key.isalpha() else ord(key)
            scan = self._SCAN_MAP.get(key.upper(), 0)
        else:
            key_upper = key.upper() if isinstance(key, str) else key
            vk_code = _VK_MAP.get(key_upper, key_upper)
            scan = self._SCAN_MAP.get(key_upper, 0)

        if not isinstance(vk_code, int):
            raise ValueError(f"Tecla não reconhecida: {key!r}")

        # lparam com scan code (bits 16-23) + repeat (0) + flags
        lparam = (scan << 16) | 0x0001

        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, lparam | 0xC0000000)

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