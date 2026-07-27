from __future__ import annotations


class BuffScript:
    """Mantem buffs ativos no personagem."""

    name = "Buff"
    KEYS = ["4", "5", "6"]  # teclas dos buffs
    COOLDOWN = 60.0  # reaplica a cada 60s
    _index = 0

    def __init__(self):
        self._last_buff = 0.0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()
        if now - self._last_buff < self.COOLDOWN:
            return False

        key = self.KEYS[self._index % len(self.KEYS)]
        self._index += 1
        input_service.press_key(hwnd, key)
        self._last_buff = now
        return True
