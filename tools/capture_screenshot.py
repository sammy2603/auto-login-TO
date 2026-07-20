# -*- coding: utf-8 -*-
"""
Captura a janela do jogo (usando a mesma técnica do bot, sem mexer no
mouse) e salva como PNG. Use essa imagem para recortar os templates
(campo_usuario.png, botao_entrar.png, etc.) com qualquer editor de imagem
(Paint, GIMP, etc.) e salve os recortes na pasta templates/.

Uso: python tools/capture_screenshot.py nome_do_arquivo.png
"""

import sys
import os
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import config
from window_utils import wait_for_window, capture_window


def main():
    if len(sys.argv) < 2:
        print("Uso: python tools/capture_screenshot.py nome_do_arquivo.png")
        sys.exit(1)

    output_name = sys.argv[1]

    hwnd = wait_for_window(config.WINDOW_TITLE, timeout=10)
    if not hwnd:
        print(f"Janela '{config.WINDOW_TITLE}' não encontrada. "
              f"Abra o jogo primeiro ou ajuste config.WINDOW_TITLE.")
        sys.exit(1)

    img = capture_window(hwnd)
    cv2.imwrite(output_name, img)
    print(f"Screenshot salvo em: {output_name}")


if __name__ == "__main__":
    main()
