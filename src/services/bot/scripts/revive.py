from __future__ import annotations


class ReviveScript:
    """
    Revive — detecta morte e tenta ressuscitar (Jackstraw ou voltar ao spot).
    """

    name = "Revive"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._last_check = 0.0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()
        if now - self._last_check < 5.0:
            return False
        self._last_check = now

        if char_info and char_info.hp_pct <= 0:
            cfg = self._config
            jack_key = cfg.get("jackstraw_key", "")
            if jack_key:
                input_service.press_key(hwnd, jack_key)
            # Espera e tenta voltar
            import time as _time
            _time.sleep(1)
            # Pressiona OK em popups
            input_service.press_key(hwnd, "ENTER")
            return True
        return False
