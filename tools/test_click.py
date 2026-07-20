# -*- coding: utf-8 -*-
"""
Teste isolado: clica numa coordenada específica da janela do jogo,
sem mexer no mouse físico, e digita um texto de teste.

Use isso ANTES de configurar o fluxo completo, para confirmar que o
jogo realmente reage a cliques via PostMessage (nem todo jogo aceita).

Uso: python tools/test_click.py <x> <y>
"""

import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import config
from window_utils import wait_for_window
from input_utils import click_at, type_text


def main():
    if len(sys.argv) < 3:
        print("Uso: python tools/test_click.py <x> <y>")
        sys.exit(1)

    x, y = int(sys.argv[1]), int(sys.argv[2])

    hwnd = wait_for_window(config.WINDOW_TITLE, timeout=10)
    if not hwnd:
        print(f"Janela '{config.WINDOW_TITLE}' não encontrada.")
        sys.exit(1)

    print(f"Clicando em ({x}, {y})... Observe se o jogo reagiu (destacou o campo, abriu cursor, etc.)")
    click_at(hwnd, x, y)
    time.sleep(0.5)

    print("Digitando texto de teste: 'teste123'")
    type_text(hwnd, "teste123")

    print("Se nada aconteceu no jogo, ele provavelmente usa DirectInput/RawInput "
          "e vamos precisar de uma abordagem alternativa (cursor real via pyautogui).")


if __name__ == "__main__":
    main()
