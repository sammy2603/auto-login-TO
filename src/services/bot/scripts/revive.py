from __future__ import annotations


class ReviveScript:
    """Detecta morte e usa ressureicao. Stub — requer template de morte."""

    name = "Revive"
    REVIVE_KEY = "0"
    COOLDOWN = 10.0

    def __init__(self):
        self._last_check = 0.0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()

        # So verifica a cada 3 segundos
        if now - self._last_check < 3.0:
            return False
        self._last_check = now

        # Heuristica: HP 0% = provavelmente morto
        # Em producao, usar template matching para confirmar tela de morte
        if char_info.hp_pct <= 0:
            input_service.press_key(hwnd, self.REVIVE_KEY)
            return True

        return False
