# -*- coding: utf-8 -*-
"""
Mostra visualmente onde os 3 slots de personagem (esquerda, centro,
direita) estão marcados em src/shared/character_slots.py, sobrepostos
na tela atual do jogo. Use isso na tela de seleção de personagem pra
calibrar as coordenadas antes de rodar o fluxo completo.

Uso: python tools/debug_slots.py
"""

import sys
import os
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import config
from window_utils import wait_for_window, capture_window
from src.shared.character_slots import CHARACTER_SLOT_POSITIONS


def main():
    hwnd = wait_for_window(config.WINDOW_TITLE, timeout=10)
    if not hwnd:
        print(f"Janela '{config.WINDOW_TITLE}' não encontrada.")
        sys.exit(1)

    screenshot = capture_window(hwnd)
    annotated = screenshot.copy()

    for slot, (x, y) in CHARACTER_SLOT_POSITIONS.items():
        cv2.drawMarker(annotated, (x, y), (255, 0, 255),
                        markerType=cv2.MARKER_CROSS, markerSize=24, thickness=3)
        cv2.putText(annotated, slot, (x + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        print(f"{slot}: ({x}, {y})")

    output_path = os.path.join(os.getcwd(), "debug_slots.png")
    cv2.imwrite(output_path, annotated)
    print(f"\nSalvo em: {output_path}")
    print("Abra a imagem e confira se as cruzes caem em cima de cada personagem.")
    print("Se não caírem, ajuste as coordenadas em src/shared/character_slots.py e rode de novo.")


if __name__ == "__main__":
    main()