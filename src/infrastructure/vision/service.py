from __future__ import annotations

from pathlib import Path

from vision import (
    load_template,
    locate_template_in_window,
    wait_for_template,
)


class VisionService:
    """
    Serviço responsável pelas operações de visão computacional.

    Atualmente adapta o módulo legado `vision.py`.
    """

    TEMPLATES_DIR = Path("templates")

    def load_template(self, name: str) -> str:
        """
        Retorna apenas o nome do template.

        O carregamento real continua sendo feito pelo código legado.
        """

        return f"{name}.png"

    def find_template(
        self,
        hwnd,
        template: str,
        threshold: float = 0.90,
    ):

        return locate_template_in_window(
            hwnd,
            template,
            str(self.TEMPLATES_DIR),
            threshold,
        )

    def wait_template(
        self,
        hwnd,
        template: str,
        timeout: float = 30.0,
        threshold: float = 0.90,
    ):

        return wait_for_template(
            hwnd,
            template,
            str(self.TEMPLATES_DIR),
            threshold,
            timeout,
        )