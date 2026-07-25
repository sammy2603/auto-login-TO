# -*- coding: utf-8 -*-
"""
Diagnóstico: verifica se a janela do jogo possui CONTROLES NATIVOS do
Windows como filhos (EDIT, BUTTON, etc) ou se é tudo desenhado pelo
próprio jogo numa única superfície (sem widgets reais do sistema).

Isso decide a estratégia de automação: se existirem controles nativos,
dá pra mandar texto direto pra eles (muito mais confiável). Se não
existir nada, o jogo desenha tudo sozinho e precisamos de outra
abordagem para trocar o foco entre campos.

Uso: python tools/inspect_controls.py
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import win32gui
import config
from window_utils import wait_for_window


def main():
    hwnd = wait_for_window(config.WINDOW_TITLE, timeout=10)
    if not hwnd:
        print(f"Janela '{config.WINDOW_TITLE}' não encontrada.")
        sys.exit(1)

    print(f"Janela principal: hwnd={hwnd}, classe='{win32gui.GetClassName(hwnd)}'")
    print("Procurando controles filhos (nativos)...\n")

    children = []

    def _callback(child_hwnd, _):
        class_name = win32gui.GetClassName(child_hwnd)
        text = win32gui.GetWindowText(child_hwnd)
        rect = win32gui.GetWindowRect(child_hwnd)
        children.append((child_hwnd, class_name, text, rect))
        return True

    win32gui.EnumChildWindows(hwnd, _callback, None)

    if not children:
        print("NENHUM controle filho encontrado.")
        print("Isso indica que o jogo desenha tudo sozinho (sem widgets nativos do Windows).")
        print("Vamos precisar de uma estratégia diferente pra trocar o foco entre campos.")
    else:
        print(f"Encontrados {len(children)} controle(s) filho(s):\n")
        for hwnd_c, class_name, text, rect in children:
            print(f"  hwnd={hwnd_c} | classe='{class_name}' | texto='{text}' | rect={rect}")
        print("\nSe algum desses for do tipo 'Edit' (ou parecido), são caixas de texto")
        print("nativas -- podemos mandar o texto direto pra elas, sem depender de clique/foco.")


if __name__ == "__main__":
    main()