from __future__ import annotations


class PetFoodScript:
    """Alimenta o pet periodicamente."""

    name = "Pet Food"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._last_use = 0.0

    @property
    def _key(self) -> str:
        return self._config.get("key", "3")

    @property
    def _interval(self) -> float:
        return self._config.get("interval", 300)

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()
        if now - self._last_use < self._interval:
            return False
        key = self._key
        if not key:
            return False
        input_service.press_key(hwnd, key)
        self._last_use = now
        return True
