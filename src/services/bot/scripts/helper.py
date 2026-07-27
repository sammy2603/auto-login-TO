from __future__ import annotations


class HelperScript:
    """
    Script auxiliar generico.

    Stub — o comportamento exato depende do jogo.
    Pode incluir: seguir lider, coletar drops, buffar party, etc.
    """

    name = "Helper"

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        # Placeholder — sera implementado conforme necessidade
        return False
