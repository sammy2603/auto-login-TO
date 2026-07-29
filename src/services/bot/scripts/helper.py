from __future__ import annotations


class HelperScript:
    """
    Script auxiliar — executa acoes a cada X mobs mortos.

    3 slots de acao com keybind, enable e delay.
    Cada acao pode rodar a cada X kills.
    """

    name = "Helper"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._last_run: dict[int, float] = {}
        self._last_kill_count = 0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()

        kill_count = getattr(char_info, "kill_count", 0)
        slots = self._config.get("slots", [])
        acted = False

        for i, slot in enumerate(slots):
            if not slot.get("enabled") or not slot.get("key"):
                continue
            every = slot.get("every_kills", 10)
            delay_ms = slot.get("delay_ms", 500)

            if every > 0 and kill_count > 0 and kill_count % every == 0 and kill_count != self._last_kill_count:
                key = slot["key"]
                input_service.press_key(hwnd, key)
                time.sleep(delay_ms / 1000.0)
                acted = True

        self._last_kill_count = kill_count
        return acted
