# -*- coding: utf-8 -*-
"""
Debug: captura a janela atual, procura um (ou todos) os templates da
pasta templates/ e desenha um retângulo + a confiança do match, salvando
como PNG. Use isso pra confirmar visualmente se cada template está
batendo no lugar certo ANTES de rodar o fluxo completo.

Uso:
    python tools/debug_templates.py                  # testa todos os templates
    python tools/debug_templates.py campo_usuario.png # testa só um
"""

import sys
import os
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import config
from window_utils import wait_for_window, capture_window
from vision import load_template, locate_on_screenshot


def debug_one(screenshot, template_name, output_dir):
    template = load_template(template_name, config.TEMPLATES_DIR)
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    h, w = template.shape[:2]
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)

    annotated = screenshot.copy()
    color = (0, 255, 0) if max_val >= config.MATCH_THRESHOLD else (0, 0, 255)
    cv2.rectangle(annotated, top_left, bottom_right, color, 2)
    label = f"{template_name}: {max_val:.2f}"
    cv2.putText(annotated, label, (top_left[0], max(top_left[1] - 8, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    status = "OK" if max_val >= config.MATCH_THRESHOLD else "BAIXA CONFIANCA"
    print(f"[{status}] {template_name}: confianca={max_val:.3f} "
          f"(threshold={config.MATCH_THRESHOLD}) posicao_centro=({top_left[0]+w//2}, {top_left[1]+h//2})")

    out_path = os.path.join(output_dir, f"debug_{template_name}")
    cv2.imwrite(out_path, annotated)
    return out_path


def main():
    hwnd = wait_for_window(config.WINDOW_TITLE, timeout=10)
    if not hwnd:
        print(f"Janela '{config.WINDOW_TITLE}' não encontrada.")
        sys.exit(1)

    screenshot = capture_window(hwnd)
    output_dir = os.getcwd()

    if len(sys.argv) > 1:
        names = [sys.argv[1]]
    else:
        names = [f for f in os.listdir(config.TEMPLATES_DIR) if f.lower().endswith(".png")]

    if not names:
        print("Nenhum template encontrado em", config.TEMPLATES_DIR)
        sys.exit(1)

    for name in names:
        try:
            out_path = debug_one(screenshot, name, output_dir)
            print(f"  -> salvo em {out_path}")
        except Exception as e:
            print(f"[ERRO] {name}: {e}")


if __name__ == "__main__":
    main()
