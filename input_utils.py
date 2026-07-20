# -*- coding: utf-8 -*-
"""
Envia clique de mouse e digitação DIRETO para a janela do jogo, via
PostMessage do Windows — sem mover o cursor físico e sem roubar o foco
do teclado do usuário.

IMPORTANTE: essa técnica funciona bem em janelas GDI/DirectX "clássicas".
Se o Talisman Online usar DirectInput/RawInput para capturar cliques,
o jogo pode não reagir a essas mensagens simuladas. Nesse caso, teste
primeiro com um clique isolado (veja tools/test_click.py) antes de
montar o fluxo completo.
"""

import time
import win32api
import win32con
import win32gui


def _make_lparam(x: int, y: int) -> int:
    """Codifica coordenadas (x, y) no formato usado pelas mensagens do Windows."""
    return (y << 16) | (x & 0xFFFF)


def click_at(hwnd, x: int, y: int, delay: float = 0.05):
    """
    Simula um clique esquerdo do mouse nas coordenadas (x, y) da CLIENT
    AREA da janela 'hwnd'. Não move o cursor real.
    """
    lparam = _make_lparam(x, y)

    win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    time.sleep(delay)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(delay)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def type_text(hwnd, text: str, delay: float = 0.03):
    """
    Envia texto caractere por caractere para a janela, via WM_CHAR.
    Não usa o teclado físico, então não interfere no que o usuário
    estiver digitando em outro lugar.
    """
    for char in text:
        win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
        time.sleep(delay)


def press_key(hwnd, vk_code: int, delay: float = 0.05):
    """Envia um key down + key up de uma tecla virtual (ex: win32con.VK_RETURN)."""
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
    time.sleep(delay)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)


def clear_field(hwnd, x: int, y: int, max_chars: int = 30):
    """
    Clica no campo e envia BACKSPACE várias vezes para limpar texto
    pré-existente antes de digitar. Útil para campos de usuário/senha.
    """
    click_at(hwnd, x, y)
    time.sleep(0.1)
    for _ in range(max_chars):
        press_key(hwnd, win32con.VK_BACK, delay=0.01)
