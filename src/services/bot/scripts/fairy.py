from __future__ import annotations


class FairyScript:
    """
    Script da Fairy — self heal + team support.
    """

    name = "Fairy"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._last_skill = 0.0
        self._skill_index = 0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()

        cfg = self._config
        skills = cfg.get("skills", [{"key": "8", "enabled": True}, {"key": "9", "enabled": False}, {"key": "0", "enabled": False}])
        self_heal = cfg.get("self_heal", {"enabled": False, "hp_pct": 50})

        if self_heal.get("enabled") and char_info and char_info.hp_pct <= self_heal.get("hp_pct", 50):
            heal_key = cfg.get("heal_key", "8")
            if heal_key and now - self._last_skill >= 2.0:
                input_service.press_key(hwnd, heal_key)
                self._last_skill = now
                return True

        if now - self._last_skill < 2.0:
            return False

        enabled = [(i, s) for i, s in enumerate(skills) if s.get("enabled") and s.get("key")]
        if not enabled:
            return False

        self._skill_index %= len(enabled)
        _, sk = enabled[self._skill_index]
        input_service.press_key(hwnd, sk["key"])
        self._skill_index += 1
        self._last_skill = now
        return True
