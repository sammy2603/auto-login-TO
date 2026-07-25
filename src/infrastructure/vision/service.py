from __future__ import annotations

import os
import time
from pathlib import Path

import cv2
import numpy as np


class VisionService:
    """
    Serviço responsável pelo reconhecimento de elementos de tela via
    template matching (OpenCV). Cada "template" é um recorte (PNG) de
    um botão/campo/ícone do jogo.

    Depende do WindowService apenas para capturar a imagem da janela
    (self.window.capture_hwnd(hwnd)) -- toda a lógica de visão
    computacional em si vive aqui.
    """

    def __init__(self, window_service, templates_dir: str = "templates"):
        self.window = window_service
        self.templates_dir = Path(templates_dir)
        self._warned_missing = set()

    def _warn_missing_once(self, template: str):
        if template not in self._warned_missing:
            print(
                f"[VisionService] Aviso: template '{template}.png' não "
                f"existe em '{self.templates_dir}'. Ignorando essa "
                f"verificação até o arquivo ser criado."
            )
            self._warned_missing.add(template)

    # =====================================================
    # Templates
    # =====================================================

    def load_template(self, name: str):
        """
        Carrega um template PNG do disco.

        Levanta FileNotFoundError se o arquivo não existir, ou
        ValueError se o arquivo existir mas não puder ser lido como
        imagem.
        """

        path = os.path.join(str(self.templates_dir), f"{name}.png")

        if not os.path.exists(path):
            raise FileNotFoundError(f"Template não encontrado: {path}")

        template = cv2.imread(path, cv2.IMREAD_COLOR)

        if template is None:
            raise ValueError(f"Não foi possível ler o template: {path}")

        return template

    # =====================================================
    # Reconhecimento
    # =====================================================

    @staticmethod
    def locate_on_screenshot(
        screenshot: np.ndarray,
        template: np.ndarray,
        threshold: float = 0.85,
    ):
        """
        Procura 'template' dentro de 'screenshot'.
        Retorna (x, y, confianca) do CENTRO do match, ou None.
        """

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return center_x, center_y, max_val

        return None

    def locate_in_window(
        self,
        hwnd,
        template_name: str,
        threshold: float = 0.85,
    ):
        """
        Captura a janela e procura o template nela. Retorna (x, y) em
        coordenadas relativas à client area, ou None.
        """

        screenshot = self.window.capture_hwnd(hwnd)
        template = self.load_template(template_name)

        match = self.locate_on_screenshot(screenshot, template, threshold)

        if match:
            x, y, _confidence = match
            return x, y

        return None

    # =====================================================
    # Busca (API usada pelo GameClient)
    # =====================================================

    def find_template(
        self,
        hwnd,
        template,
        threshold: float = 0.90,
    ):
        try:
            return self.locate_in_window(
                hwnd=hwnd,
                template_name=template,
                threshold=threshold,
            )
        except FileNotFoundError:
            # Template ainda não foi capturado/criado -- trata como
            # "não encontrado" em vez de derrubar o fluxo inteiro.
            # Importante para templates opcionais (ex: popups de erro
            # que só existem se o usuário já capturou a imagem).
            self._warn_missing_once(template)
            return None

    def wait_template(
        self,
        hwnd,
        template,
        timeout: float = 30.0,
        threshold: float = 0.90,
        poll_interval: float = 0.5,
    ):
        try:
            start = time.time()
            while time.time() - start < timeout:
                pos = self.locate_in_window(
                    hwnd=hwnd,
                    template_name=template,
                    threshold=threshold,
                )
                if pos:
                    return pos
                time.sleep(poll_interval)
            return None
        except FileNotFoundError:
            self._warn_missing_once(template)
            return None