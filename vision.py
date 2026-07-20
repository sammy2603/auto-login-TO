# -*- coding: utf-8 -*-
"""
Reconhecimento de elementos de tela via template matching (OpenCV).
Cada "template" é um recorte (PNG) de um botão/campo/ícone do jogo.
"""

import os
import time
import cv2
import numpy as np

from window_utils import capture_window


def load_template(name: str, templates_dir: str):
    path = os.path.join(templates_dir, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template não encontrado: {path}")
    template = cv2.imread(path, cv2.IMREAD_COLOR)
    if template is None:
        raise ValueError(f"Não foi possível ler o template: {path}")
    return template


def locate_on_screenshot(screenshot: np.ndarray, template: np.ndarray, threshold: float = 0.85):
    """
    Procura 'template' dentro de 'screenshot'.
    Retorna (x, y, confianca) do CENTRO do match, ou None se não achar.
    """
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        h, w = template.shape[:2]
        center_x = max_loc[0] + w // 2
        center_y = max_loc[1] + h // 2
        return center_x, center_y, max_val
    return None


def locate_template_in_window(hwnd, template_name: str, templates_dir: str, threshold: float = 0.85):
    """Captura a janela e procura o template nela. Retorna (x, y) em
    coordenadas relativas à client area, ou None."""
    screenshot = capture_window(hwnd)
    template = load_template(template_name, templates_dir)
    match = locate_on_screenshot(screenshot, template, threshold)
    if match:
        x, y, _confidence = match
        return x, y
    return None


def wait_for_template(hwnd, template_name: str, templates_dir: str,
                       threshold: float = 0.85, timeout: float = 30.0,
                       poll_interval: float = 0.5):
    """Espera até o template aparecer na janela (útil para aguardar telas
    carregarem). Retorna (x, y) assim que encontrar, ou None se der timeout."""
    start = time.time()
    while time.time() - start < timeout:
        pos = locate_template_in_window(hwnd, template_name, templates_dir, threshold)
        if pos:
            return pos
        time.sleep(poll_interval)
    return None
