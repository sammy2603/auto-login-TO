from __future__ import annotations

import os
import time
from pathlib import Path

import cv2
import numpy as np

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


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
            logger.warning(
                "Template '%s.png' não existe em '%s'. Ignorando essa "
                "verificação até o arquivo ser criado.",
                template,
                self.templates_dir,
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
        region=None,
    ):
        """
        Captura a janela e procura o template nela. Retorna (x, y) em
        coordenadas relativas à client area, ou None.

        'region' é (x1, y1, x2, y2) e limita a busca a um recorte --
        útil pra procurar um ícone só dentro do inventário, por
        exemplo. Sem ela, procura na janela toda, o que aumenta a
        chance de casar com algo parecido em outro canto da tela.
        """

        screenshot = self.window.capture_hwnd(hwnd)

        if screenshot is None:
            return None

        template = self.load_template(template_name)

        offset_x, offset_y = 0, 0

        if region:
            height, width = screenshot.shape[:2]
            x1, y1, x2, y2 = region
            x1 = max(0, min(int(x1), width))
            y1 = max(0, min(int(y1), height))
            x2 = max(0, min(int(x2), width))
            y2 = max(0, min(int(y2), height))

            if x1 >= x2 or y1 >= y2:
                return None

            screenshot = screenshot[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1

        # Template maior que a área de busca faz o matchTemplate
        # levantar; tratar como "não encontrado" é o comportamento útil.
        if (template.shape[0] > screenshot.shape[0]
                or template.shape[1] > screenshot.shape[1]):
            return None

        match = self.locate_on_screenshot(screenshot, template, threshold)

        if match:
            x, y, _confidence = match
            return x + offset_x, y + offset_y

        return None

    # =====================================================
    # Busca (API usada pelo GameClient)
    # =====================================================

    def find_template(
        self,
        hwnd,
        template,
        threshold: float = 0.90,
        region=None,
    ):
        try:
            return self.locate_in_window(
                hwnd=hwnd,
                template_name=template,
                threshold=threshold,
                region=region,
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

    # =====================================================
    # Cor
    # =====================================================
    #
    # Os macros antigos verificavam estado do jogo por COR de pixel, em
    # vez de template. É mais frágil que template matching (muda com
    # tema, brilho, compressão), então prefira template quando der --
    # mas para coisas sem recorte pronto, como "o ícone do mapa ficou
    # verde", é o que existe.
    #
    # Convenção de cor aqui: tupla (R, G, B) ou int 0xRRGGBB. Os
    # macros antigos usavam inteiros num formato não documentado (ex:
    # 65280, 64511), que PODE ser BGR ou RGB565 -- converta e confira
    # contra o jogo antes de confiar num número herdado.

    @staticmethod
    def _to_rgb(color) -> tuple[int, int, int]:
        """Aceita (R, G, B) ou int 0xRRGGBB e devolve a tupla."""

        if isinstance(color, (tuple, list)):
            if len(color) != 3:
                raise ValueError(f"Cor deve ter 3 componentes: {color!r}")
            return tuple(int(c) for c in color)

        if isinstance(color, int):
            return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)

        raise ValueError(f"Cor não reconhecida: {color!r}")

    def pixel_rgb(self, hwnd, x: int, y: int):
        """
        Cor (R, G, B) do pixel (x, y) da janela, ou None se estiver
        fora dos limites da captura.
        """

        screenshot = self.window.capture_hwnd(hwnd)

        if screenshot is None:
            return None

        height, width = screenshot.shape[:2]

        if not (0 <= x < width and 0 <= y < height):
            return None

        # OpenCV entrega BGR; a API pública deste módulo fala RGB.
        blue, green, red = screenshot[y, x][:3]

        return int(red), int(green), int(blue)

    def pixel_matches(self, hwnd, x: int, y: int, color, tolerance: int = 10) -> bool:
        """
        Verdadeiro se o pixel (x, y) está próximo de 'color'.

        A tolerância existe porque o jogo tem anti-aliasing e leve
        variação de brilho -- exigir igualdade exata faz a verificação
        falhar de forma intermitente, que é pior que não verificar.
        """

        actual = self.pixel_rgb(hwnd, x, y)

        if actual is None:
            return False

        expected = self._to_rgb(color)

        return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))

    def find_color(self, hwnd, color, region=None, tolerance: int = 10):
        """
        Procura a primeira ocorrência de uma cor e devolve (x, y) em
        coordenadas da JANELA, ou None.

        'region' é (x1, y1, x2, y2); sem ela, procura na janela toda.
        Equivale ao 'findcolor' dos macros antigos.
        """

        screenshot = self.window.capture_hwnd(hwnd)

        if screenshot is None:
            return None

        height, width = screenshot.shape[:2]

        if region:
            x1, y1, x2, y2 = region
            x1 = max(0, min(int(x1), width))
            y1 = max(0, min(int(y1), height))
            x2 = max(0, min(int(x2), width))
            y2 = max(0, min(int(y2), height))
            if x1 >= x2 or y1 >= y2:
                return None
            area = screenshot[y1:y2, x1:x2]
        else:
            x1, y1 = 0, 0
            area = screenshot

        red, green, blue = self._to_rgb(color)
        target = np.array([blue, green, red], dtype=np.int16)  # captura é BGR

        diff = np.abs(area.astype(np.int16)[:, :, :3] - target)
        hits = np.argwhere(np.all(diff <= tolerance, axis=2))

        if hits.size == 0:
            return None

        # argwhere devolve (linha, coluna) = (y, x); somar o canto da
        # região converte de volta pra coordenada da janela.
        first_y, first_x = hits[0]

        return int(first_x) + x1, int(first_y) + y1