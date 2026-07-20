# -*- coding: utf-8 -*-
"""
Funções para localizar a janela do jogo e capturar o conteúdo dela
SEM usar o cursor do mouse e SEM precisar que a janela esteja em foco/visível.

Usa a API PrintWindow do Windows, que renderiza a janela diretamente
num bitmap em memória.
"""

import ctypes
import time
import numpy as np
import win32gui
import win32ui
import win32con
import win32api

# Acesso direto à função nativa do Windows, evita depender de versões
# do pywin32 que não expõem win32gui.PrintWindow.
_user32 = ctypes.windll.user32


def find_window(title_substring: str):
    """Procura a primeira janela cujo título contenha 'title_substring'.
    Retorna o handle (HWND) ou None se não encontrar."""
    result = {"hwnd": None}

    def _callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title_substring.lower() in title.lower():
                result["hwnd"] = hwnd
                return False  # para a enumeração
        return True

    win32gui.EnumWindows(_callback, None)
    return result["hwnd"]


def wait_for_window(title_substring: str, timeout: float = 30.0, poll_interval: float = 0.5):
    """Espera a janela aparecer, sem travar indefinidamente."""
    start = time.time()
    while time.time() - start < timeout:
        hwnd = find_window(title_substring)
        if hwnd:
            return hwnd
        time.sleep(poll_interval)
    return None


def get_client_size(hwnd):
    """Retorna (largura, altura) da área útil (client area) da janela."""
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    return right - left, bottom - top


def capture_window(hwnd) -> np.ndarray:
    """
    Captura o conteúdo da client area da janela usando PrintWindow.
    Não move o mouse, não precisa que a janela esteja em primeiro plano
    nem visível na tela (funciona até minimizada, em muitos casos).

    Retorna uma imagem no formato BGR (compatível com OpenCV).
    """
    width, height = get_client_size(hwnd)
    if width <= 0 or height <= 0:
        raise RuntimeError("Janela com dimensões inválidas (pode estar minimizada sem suporte a PrintWindow).")

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()

    save_bitmap = win32ui.CreateBitmap()
    save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(save_bitmap)

    # PW_CLIENTONLY (0x1) + PW_RENDERFULLCONTENT (0x2) = 3
    # PW_CLIENTONLY é essencial: sem ele, o PrintWindow captura a janela
    # inteira (incluindo barra de título/bordas), o que desalinha as
    # coordenadas encontradas pelo template matching com as coordenadas
    # reais da client area usadas nos cliques.
    result = _user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

    bmp_info = save_bitmap.GetInfo()
    bmp_bits = save_bitmap.GetBitmapBits(True)

    img = np.frombuffer(bmp_bits, dtype=np.uint8)
    img.shape = (bmp_info["bmHeight"], bmp_info["bmWidth"], 4)  # BGRA

    # Limpeza dos recursos do GDI
    win32gui.DeleteObject(save_bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)

    if result != 1:
        # Em alguns jogos com renderização DirectX exclusiva, PrintWindow pode
        # retornar uma imagem preta. Nesse caso, é necessário um fallback via
        # captura de tela real (menos ideal, pois exige a janela visível).
        pass

    return img[:, :, :3]  # remove canal alpha, retorna BGR