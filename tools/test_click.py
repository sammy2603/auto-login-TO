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
from src.infrastructure.window.service import WindowService
from src.infrastructure.input.service import InputService


def main():
    if len(sys.argv) < 3:
        print("Uso: python tools/test_click.py <x> <y>")
        sys.exit(1)

    x, y = int(sys.argv[1]), int(sys.argv[2])

    window = WindowService()
    input_service = InputService()

    try:
        hwnd = window.connect(title_substring=config.WINDOW_TITLE, timeout=10)
    except Exception as e:
        print(f"Janela '{config.WINDOW_TITLE}' não encontrada: {e}")
        sys.exit(1)

    print(f"Clicando em ({x}, {y})... Observe se o jogo reagiu (destacou o campo, abriu cursor, etc.)")
    input_service.click(hwnd, x, y)
    time.sleep(0.5)

    print("Digitando texto de teste: 'teste123'")
    input_service.type_text(hwnd, "teste123")

    print("Se nada aconteceu no jogo, ele provavelmente usa DirectInput/RawInput "
          "e vamos precisar de uma abordagem alternativa (cursor real via pyautogui).")


if __name__ == "__main__":
    main()