from vision import (
    load_template,
    locate_template_in_window,
    wait_for_template,
)


class VisionService:
    """
    Responsável pelas operações de visão computacional.
    """

    def load_template(self, path: str):
        return load_template(path)

    def find_template(self, hwnd, template):
        return locate_template_in_window(
            hwnd=hwnd,
            template=template,
        )

    def wait_template(
        self,
        hwnd,
        template,
        timeout=30,
        threshold=0.9,
    ):
        return wait_for_template(
            hwnd=hwnd,
            template=template,
            timeout=timeout,
            threshold=threshold,
        )