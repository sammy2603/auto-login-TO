# -*- coding: utf-8 -*-
"""
Lista todas as janelas visíveis abertas no momento, com seus títulos.
Rode isso com o client do jogo já aberto para descobrir o título exato
que deve ir em config.WINDOW_TITLE.

Uso: python tools/find_window_title.py
"""

import win32gui


def list_windows():
    windows = []

    def _callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                windows.append(title)
        return True

    win32gui.EnumWindows(_callback, None)
    return windows


if __name__ == "__main__":
    for t in list_windows():
        print(t)
