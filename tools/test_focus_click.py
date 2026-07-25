# -*- coding: utf-8 -*-
"""
Testa se ATIVAR a janela do jogo (trazer para primeiro plano, sem
mexer no cursor do mouse) faz diferença no comportamento do clique
simulado via PostMessage. Alguns jogos ignoram cliques em janelas que
não estão em primeiro plano, mesmo recebendo a mensagem corretamente.

Uso: python tools/test_focus_click.py <x> <y>
"""

import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import win32api
import win32con
import win32gui
import config
from src.infrastructure.window.service import WindowService
from src.infrastructure.input.service import InputService


def gradual_click(hwnd, x: int, y: int, steps: int = 15, step_delay: float = 0.02):
    """
    Simula o cursor se movendo gradualmente até (x, y) via uma
    sequência de WM_MOUSEMOVE, em vez de ir direto pro ponto final.
    Algumas engines só reconhecem o hover/clique corretamente se
    receberem essa sequência de movimento.
    """
    # Ponto de partida arbitrário (canto da client area)
    start_x, start_y = 5, 5

    for i in range(1, steps + 1):
        ix = start_x + (x - start_x) * i // steps
        iy = start_y + (y - start_y) * i // steps
        lparam = InputService._make_lparam(ix, iy)
        win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(step_delay)

    lparam_final = InputService._make_lparam(x, y)
    time.sleep(0.05)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam_final)
    time.sleep(0.05)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam_final)


def main():
    if len(sys.argv) < 3:
        print("Uso: python tools/test_focus_click.py <x> <y>")
        sys.exit(1)

    x, y = int(sys.argv[1]), int(sys.argv[2])

    window = WindowService()
    input_service = InputService()

    try:
        hwnd = window.connect(title_substring=config.WINDOW_TITLE, timeout=10)
    except Exception as e:
        print(f"Janela '{config.WINDOW_TITLE}' não encontrada: {e}")
        sys.exit(1)

    print("Ativando a janela do jogo (sem mexer no cursor)...")
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f"Aviso: não foi possível ativar a janela ({e}). Continuando mesmo assim.")

    time.sleep(0.3)

    print(f"Movendo o cursor simulado gradualmente até ({x}, {y}) e clicando...")
    gradual_click(hwnd, x, y)
    time.sleep(0.3)

    print("Digitando texto de teste: 'testeFOCUS'")
    input_service.type_text(hwnd, "testeFOCUS")

    print("\nObserve no jogo: o texto apareceu no campo certo (onde você clicou)?")
    print("Se sim: o problema era a janela não estar ativa. Se não: não é isso.")


if __name__ == "__main__":
    main()