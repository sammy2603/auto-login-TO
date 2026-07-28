from __future__ import annotations


class AttackScript:
    """
    Script de ataque com skills configuraveis.

    Cicla pelas teclas configuradas com o delay definido
    pelo usuario (50-250ms entre cada tecla).

    So ataca se houver alvo selecionado e HP do char > 0.
    """

    name = "Attack"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._index = 0
        self._last_key = 0.0

    @property
    def _keys(self) -> list[str]:
        return self._config.get("keys", ["1"])

    @property
    def _speed_ms(self) -> int:
        return self._config.get("speed", 150)

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

        keys = self._keys or ["1"]
        speed = self._speed_ms / 1000.0

        if not target_info or target_info.hp_pct <= 0:
            return False

        if char_info and char_info.hp_pct <= 0:
            return False

        now = time.time()
        if now - self._last_key < speed:
            return False

        if self._index >= len(keys):
            self._index = 0

        key = keys[self._index]
        input_service.press_key(hwnd, key)
        self._index += 1
        self._last_key = now
        return True
