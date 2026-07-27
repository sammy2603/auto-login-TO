from __future__ import annotations


class DRLureScript:
    """
    Usa DR Lure para atrair mobs.

    Ativa o item/skill de lure em intervalo regular.
    """

    name = "DR Lure"
    KEY = "8"
    COOLDOWN = 30.0

    def __init__(self):
        self._last_use = 0.0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()
        if now - self._last_use < self.COOLDOWN:
            return False
        input_service.press_key(hwnd, self.KEY)
        self._last_use = now
        return True
