from __future__ import annotations


class DeleteScript:
    """
    Deleta itens indesejados do inventario.

    Stub — requer navegacao de inventario via template matching,
    o que e complexo e especifico do jogo.
    """

    name = "Delete"

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        return False
