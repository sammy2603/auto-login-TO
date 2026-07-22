from pathlib import Path

from vision import (
    load_template,
    locate_template_in_window,
    wait_for_template,
)


class VisionService:
    """
    Adaptador para o módulo legado vision.py.

    Esta classe não implementa algoritmos de visão computacional.
    Ela apenas fornece uma interface orientada a objetos para o restante
    da aplicação.
    """

    TEMPLATES_DIR = Path("templates")

    def load_template(self, name: str):
        """
        Carrega um template pelo nome.

        Exemplo:
            load_template("campo_usuario")
        """
        path = self.TEMPLATES_DIR / f"{name}.png"
        return load_template(str(path))

    def find_template(
        self,
        hwnd,
        template,
        threshold: float = 0.90,
    ):
        """
        Localiza um template na janela.
        """
        return locate_template_in_window(
            hwnd=hwnd,
            template=template,
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
        Aguarda até que um template apareça.
        """
        return wait_for_template(
            hwnd=hwnd,
            template=template,
            timeout=timeout,
            threshold=threshold,
        )