# -*- coding: utf-8 -*-
"""
Captura a janela do jogo (sem mexer no mouse) e salva como PNG. Use
essa imagem para recortar os templates (campo_usuario.png,
botao_entrar.png, etc) com qualquer editor de imagem e salve os
recortes na pasta templates/.

Uso: python tools/capture_screenshot.py nome_do_arquivo.png [titulo]

O 'titulo' e opcional e serve pra capturar um CLIENT ja logado, cuja
janela se chama pelo nome do personagem ("[Tomyris]") e nao pelo
config.WINDOW_TITLE, que e o da tela de login.
"""

import sys
import os
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import config
from src.infrastructure.window.service import WindowService


def main():
    if len(sys.argv) < 2:
        print("Uso: python tools/capture_screenshot.py nome_do_arquivo.png")
        sys.exit(1)

    output_name = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else config.WINDOW_TITLE

    window = WindowService()

    try:
        window.connect(title_substring=title, timeout=10)
    except Exception as e:
        print(f"Janela '{title}' não encontrada: {e}")
        sys.exit(1)

    img = window.capture()
    cv2.imwrite(output_name, img)
    print(f"Screenshot salvo em: {output_name}")


if __name__ == "__main__":
    main()