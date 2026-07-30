from __future__ import annotations
import math


class AttackScript:
    """
    Script de ataque com skills, filtro, unstuck e spot area.

    Spot: salva posicao inicial, se distancia > range -> para de atacar
    e retorna ao spot (TAB para alvos proximos do spot).
    """

    name = "Attack"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._index = 0
        self._last_key = 0.0
        self._last_tab = 0.0
        self._started = False
        self._last_attack_time = 0.0
        self._spot_x: int | None = None
        self._spot_y: int | None = None

    @property
    def _keys(self) -> list[str]:
        return self._config.get("keys", ["1"])

    @property
    def _speed_ms(self) -> int:
        return self._config.get("speed", 150)

    @property
    def _filter(self) -> dict:
        return self._config.get("target_filter", {"mode": "all", "name": ""})

    def _check_target_list(self, tname: str) -> bool:
        """Retorna True se deve atacar este alvo, False se deve pular."""
        tl = self._config.get("target_list", [])
        if not tl:
            return True  # lista vazia = atacar todos

        for item in tl:
            if item["name"] == tname:
                return item["mode"] == "attack"
        # Se tem lista mas o nome nao esta nela, verifica o modo padrao
        # Se a lista so tem "attack", ignora os que nao estao na lista
        # Se a lista so tem "ignore", ataca os que nao estao na lista
        has_attack = any(i["mode"] == "attack" for i in tl)
        has_ignore = any(i["mode"] == "ignore" for i in tl)
        if has_attack and not has_ignore:
            return False  # so ataca os da lista
        return True  # ignora so os da lista, ataca o resto

    @property
    def _unstuck(self) -> dict:
        return self._config.get("unstuck", {"enabled": False, "timeout": 10})

    @property
    def _spot(self) -> dict:
        return self._config.get("spot", {"enabled": False, "distance": 20})

    def _dist_to_spot(self, x: int, y: int) -> float:
        if self._spot_x is None:
            return 0
        return math.sqrt((x - self._spot_x) ** 2 + (y - self._spot_y) ** 2)

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()

        if char_info and char_info.hp_pct <= 0:
            return False

        if not self._started:
            self._started = True
            self._last_attack_time = now
            # Salva posicao do spot
            sp = self._spot
            if sp.get("enabled") and char_info:
                self._spot_x = char_info.x
                self._spot_y = char_info.y
            input_service.press_key(hwnd, "TAB")
            self._last_tab = now
            return True

        # Spot: verifica distancia
        sp = self._spot
        if sp.get("enabled") and self._spot_x is not None and char_info:
            dist = self._dist_to_spot(char_info.x, char_info.y)
            if dist > sp.get("distance", 20):
                # Muito longe — para de atacar, volta pro spot
                return False  # Nao ataca, deixa o char voltar

        # Target list
        tname = target_info.name if target_info else ""
        if not self._check_target_list(tname):
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
