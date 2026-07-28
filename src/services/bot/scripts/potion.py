from __future__ import annotations


class PotionScript:
    """
    Script de pocoes configuravel.

    Usa a tecla de pocao quando HP do personagem
    cai abaixo do threshold configurado.
    """

    name = "Potion"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._last_use = 0.0

    @property
    def _key(self) -> str:
        return self._config.get("key", "2")

    @property
    def _hp_threshold(self) -> float:
        return self._config.get("hp_threshold", 55)

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

        if char_info.hp_pct >= self._hp_threshold:
            return False

        if now - self._last_use < 5.0:
            return False

        input_service.press_key(hwnd, self._key)
        self._last_use = now
        return True
