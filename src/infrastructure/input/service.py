from __future__ import annotations

import time
from contextlib import contextmanager

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
    "SPACE": win32con.VK_SPACE,
    "BACKSPACE": win32con.VK_BACK,
}

# F1..F12 -- os codigos virtuais sao contiguos (VK_F1 = 0x70).
for _n in range(1, 13):
    _VK_MAP[f"F{_n}"] = win32con.VK_F1 + (_n - 1)


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

    def right_click(self, hwnd, x: int, y: int, delay: float = 0.05):
        """
        Clique DIREITO em (x, y).

        No Talisman é o botão de movimento: clicar com o direito no
        chão ou no minimapa manda o personagem andar até lá.
        """

        lparam = self._make_lparam(x, y)

        win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lparam)

    def double_right_click(self, hwnd, x: int, y: int, delay: float = 0.05):
        """
        Duplo clique direito em (x, y).

        Manda o WM_RBUTTONDBLCLK explicitamente além dos dois cliques:
        janelas com a flag CS_DBLCLKS esperam essa mensagem, e só
        repetir dois RBUTTONDOWN seguidos não equivale a um duplo
        clique de verdade pra elas.
        """

        lparam = self._make_lparam(x, y)

        win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_RBUTTONDBLCLK, win32con.MK_RBUTTON, lparam)
        time.sleep(delay)
        win32api.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lparam)

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
        "SPACE": 0x39, "BACKSPACE": 0x0E,
        "F1": 0x3B, "F2": 0x3C, "F3": 0x3D, "F4": 0x3E, "F5": 0x3F,
        "F6": 0x40, "F7": 0x41, "F8": 0x42, "F9": 0x43, "F10": 0x44,
        "F11": 0x57, "F12": 0x58,
    }

    def _resolve_key(self, key) -> tuple[int, int]:
        """
        Traduz a tecla para (codigo virtual, scan code).

        Aceita codigo virtual (int), caractere unico ("1", "a") ou nome
        simbolico ("TAB", "F12", "ENTER").
        """

        if isinstance(key, int):
            return key, 0

        if isinstance(key, str) and len(key) == 1:
            vk = ord(key.upper()) if key.isalpha() else ord(key)
            return vk, self._SCAN_MAP.get(key.upper(), 0)

        key_upper = key.upper() if isinstance(key, str) else key
        vk = _VK_MAP.get(key_upper)

        if not isinstance(vk, int):
            raise ValueError(f"Tecla não reconhecida: {key!r}")

        return vk, self._SCAN_MAP.get(key_upper, 0)

    def key_down(self, hwnd, key):
        """
        Segura uma tecla, sem soltar.

        Existe pro caso do 'send_down {f12}' dos macros antigos, em que
        uma tecla fica pressionada enquanto várias outras ações
        acontecem. Quem chama é responsável por chamar key_up() depois
        -- de preferência num 'finally', pra tecla não ficar presa se
        algo falhar no meio.
        """

        vk_code, scan = self._resolve_key(key)
        lparam = (scan << 16) | 0x0001
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, lparam)

    def key_up(self, hwnd, key):
        """Solta uma tecla segurada por key_down()."""

        vk_code, scan = self._resolve_key(key)
        lparam = (scan << 16) | 0x0001
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, lparam | 0xC0000000)

    @contextmanager
    def held_key(self, hwnd, key):
        """
        Segura a tecla durante o bloco e solta ao sair, inclusive se
        houver exceção:

            with input_service.held_key(hwnd, "F12"):
                ...
        """

        self.key_down(hwnd, key)
        try:
            yield
        finally:
            self.key_up(hwnd, key)

    def press_key(self, hwnd, key, delay: float = 0.05):
        """
        Pressiona e solta uma tecla. Aceita:
        - Chave simbolica (ex: "TAB", "ENTER", "F12")
        - Codigo de tecla virtual (int)
        - Caractere unico (ex: "1", "a")
        """

        self.key_down(hwnd, key)
        time.sleep(delay)
        self.key_up(hwnd, key)

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