from __future__ import annotations


class PotionScript:
    """
    Script de pocoes automaticas.

    Usa pocao quando o HP do personagem cai abaixo
    de um limiar configuravel.
    """

    name = "Potion"

    POTION_KEY = "2"
    HP_THRESHOLD = 55.0
    COOLDOWN = 5.0

    def __init__(self):
        self._last_use = 0.0

    def tick(
        self,
        hwnd: int,
        screenshot,
        char_info,
        target_info,
        input_service,
        vision_service,
        window_service,
    ) -> bool:
        import time

        now = time.time()

        if char_info.hp_pct >= self.HP_THRESHOLD:
            return False

        if now - self._last_use < self.COOLDOWN:
            return False

        input_service.press_key(hwnd, self.POTION_KEY)
        self._last_use = now
        return True
