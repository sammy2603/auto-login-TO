from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BarRegion:
    """Regiao de uma barra de status (HP, recurso, etc.)."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class CharInfo:
    """Informacoes lidas do personagem."""
    hp_pct: float = 0.0
    resource_pct: float = 0.0
    in_battle: bool = False


@dataclass
class TargetInfo:
    """Informacoes lidas do alvo."""
    hp_pct: float = 0.0
    name: str = ""


class GameReader:
    """
    Le informacoes da janela do jogo (HP, recurso, target).

    Usa analise de pixels para calcular a porcentagem de
    preenchimento das barras de status.

    As regioes das barras precisam ser calibradas com
    ferramentas de debug (capture_screenshot + debug_templates).
    """

    # Cor do HP preenchido (verde) — faixa RGB esperada
    HP_FILL_COLOR_LOWER = np.array([0, 120, 0])
    HP_FILL_COLOR_UPPER = np.array([80, 255, 80])

    # Cor do recurso/MP preenchido (azul)
    RESOURCE_FILL_COLOR_LOWER = np.array([0, 0, 120])
    RESOURCE_FILL_COLOR_UPPER = np.array([80, 120, 255])

    # Cor do fundo vazio da barra (escuro/preto)
    EMPTY_COLOR_UPPER = np.array([60, 60, 60])

    def __init__(
        self,
        char_hp_region: BarRegion | None = None,
        char_resource_region: BarRegion | None = None,
        target_hp_region: BarRegion | None = None,
    ):
        self.char_hp_region = char_hp_region
        self.char_resource_region = char_resource_region
        self.target_hp_region = target_hp_region

    def read_char_info(self, screenshot: np.ndarray) -> CharInfo:
        """Le HP e recurso do personagem."""
        info = CharInfo()

        if self.char_hp_region:
            info.hp_pct = self._read_bar_fill(
                screenshot,
                self.char_hp_region,
                self.HP_FILL_COLOR_LOWER,
                self.HP_FILL_COLOR_UPPER,
            )

        if self.char_resource_region:
            info.resource_pct = self._read_bar_fill(
                screenshot,
                self.char_resource_region,
                self.RESOURCE_FILL_COLOR_LOWER,
                self.RESOURCE_FILL_COLOR_UPPER,
            )

        return info

    def read_target_info(self, screenshot: np.ndarray) -> TargetInfo:
        """Le HP e nome do alvo."""
        info = TargetInfo()

        if self.target_hp_region:
            info.hp_pct = self._read_bar_fill(
                screenshot,
                self.target_hp_region,
                self.HP_FILL_COLOR_LOWER,
                self.HP_FILL_COLOR_UPPER,
            )

        return info

    def _read_bar_fill(
        self,
        screenshot: np.ndarray,
        region: BarRegion,
        color_lower: np.ndarray,
        color_upper: np.ndarray,
    ) -> float:
        """
        Calcula a porcentagem de preenchimento de uma barra
        com base na proporcao de pixels da cor alvo na regiao.
        """

        h, w = screenshot.shape[:2]

        x1 = max(0, region.x)
        y1 = max(0, region.y)
        x2 = min(w, region.x + region.width)
        y2 = min(h, region.y + region.height)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        roi = screenshot[y1:y2, x1:x2]

        # Pixels nao-vazios (mais claros que o fundo escuro)
        non_empty = np.all(roi > self.EMPTY_COLOR_UPPER, axis=2)
        total_bar = non_empty.sum()

        if total_bar == 0:
            return 0.0

        # Pixels da cor alvo (HP verde, recurso azul)
        color_match = (
            np.all(roi >= color_lower, axis=2)
            & np.all(roi <= color_upper, axis=2)
        )
        filled = color_match.sum()

        pct = (filled / total_bar) * 100.0
        return min(100.0, max(0.0, pct))
