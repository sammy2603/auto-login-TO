from pathlib import Path

from vision import (
    load_template,
    locate_template_in_window,
    wait_for_template,
)


class VisionService:
    """
    Adaptador para o módulo legado vision.py.

    Responsável exclusivamente pelas operações de visão computacional.
    """

    def __init__(self, templates_dir: str = "templates"):
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

    def load_template(
        self,
        name: str,
    ):
        return load_template(
            f"{name}.png",
            str(self.templates_dir),
        )

    # =====================================================
    # Busca
    # =====================================================

    def find_template(
        self,
        hwnd,
        template,
        threshold: float = 0.90,
    ):
        try:
            return locate_template_in_window(
                hwnd=hwnd,
                template_name=f"{template}.png",
                templates_dir=str(self.templates_dir),
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
    ):
        try:
            return wait_for_template(
                hwnd=hwnd,
                template_name=f"{template}.png",
                templates_dir=str(self.templates_dir),
                timeout=timeout,
                threshold=threshold,
            )
        except FileNotFoundError:
            self._warn_missing_once(template)
            return None