from __future__ import annotations


class AttackScript:
    """
    Script de ataque com skills, filtro de alvo e unstuck.

    Fluxo:
    1. Sem alvo ou alvo morto -> TAB
    2. Alvo vivo -> cicla teclas
    3. Unstuck: se nao atacar por X segundos -> TAB
    """

    name = "Attack"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._index = 0
        self._last_key = 0.0
        self._last_tab = 0.0
        self._started = False
        self._last_attack_time = 0.0

    @property
    def _keys(self) -> list[str]:
        return self._config.get("keys", ["1"])

    @property
    def _speed_ms(self) -> int:
        return self._config.get("speed", 150)

    @property
    def _filter(self) -> dict:
        return self._config.get("target_filter", {"mode": "all", "name": ""})

    @property
    def _unstuck(self) -> dict:
        return self._config.get("unstuck", {"enabled": False, "timeout": 10})

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()

        if char_info and char_info.hp_pct <= 0:
            return False

        if not self._started:
            self._started = True
            self._last_attack_time = now
            input_service.press_key(hwnd, "TAB")
            self._last_tab = now
            return True

        tf = self._filter
        tname = target_info.name if target_info else ""
        mode = tf.get("mode", "all")
        fname = tf.get("name", "")

        if fname:
            if mode == "only" and tname != fname:
                if now - self._last_tab >= 0.3:
                    input_service.press_key(hwnd, "TAB")
                    self._last_tab = now
                return True
            if mode == "exclude" and tname == fname:
                if now - self._last_tab >= 0.3:
                    input_service.press_key(hwnd, "TAB")
                    self._last_tab = now
                return True

        if not target_info or target_info.hp_pct <= 0:
            if now - self._last_tab >= 0.3:
                input_service.press_key(hwnd, "TAB")
                self._last_tab = now
                self._index = 0
            return True

        # Unstuck: sem ataque por X segundos -> troca alvo
        us = self._unstuck
        if us.get("enabled") and self._last_attack_time > 0:
            if now - self._last_attack_time >= us.get("timeout", 10):
                input_service.press_key(hwnd, "TAB")
                self._last_tab = now
                self._last_attack_time = now
                self._index = 0
                return True

        keys = self._keys or ["1"]
        speed = self._speed_ms / 1000.0

        if now - self._last_key < speed:
            return False

        if self._index >= len(keys):
            self._index = 0

        key = keys[self._index]
        input_service.press_key(hwnd, key)
        self._index += 1
        self._last_key = now
        self._last_attack_time = now
        return True
