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
    Não contém regras de negócio e não conhece os workflows da aplicação.
    """

    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)

    # =====================================================
    # Templates
    # =====================================================

    def load_template(self, name: str):
        """
        Carrega um template pelo nome.

        Exemplo:
            load_template("campo_usuario")
        """

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
        """
        Procura um template na janela do jogo.

        Retorna:
            (x, y) ou None
        """

        return locate_template_in_window(
            hwnd=hwnd,
            template_name=template,
            templates_dir=str(self.templates_dir),
            threshold=threshold,
        )

    def wait_template(
        self,
        hwnd,
        template,
        timeout: float = 30.0,
        threshold: float = 0.90,
    ):
        """
        Aguarda um template aparecer na janela.

        Retorna:
            (x, y) ou None
        """

        return wait_for_template(
            hwnd=hwnd,
            template_name=template,
            templates_dir=str(self.templates_dir),
            timeout=timeout,
            threshold=threshold,
        )