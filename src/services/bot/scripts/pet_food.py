from __future__ import annotations


class PetScript:
    """
    Script do Pet — prioridade maxima.

    1. Se pet nao esta ativo → usa keybind do Pet para invocar
    2. A cada intervalo configurado (5-50 min) → usa Pet Food
    3. Timer zera quando o bot para/reinicia
    """

    name = "Pet"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._last_food = 0.0
        self._start_time = 0.0

    @property
    def _pet_key(self) -> str:
        return self._config.get("pet_key", "7")

    @property
    def _food_key(self) -> str:
        return self._config.get("food_key", "3")

    @property
    def _interval_sec(self) -> float:
        return self._config.get("interval_min", 30) * 60.0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()

        # Marca inicio na primeira execucao (timer zera aqui)
        if self._start_time == 0:
            self._start_time = now
            self._last_food = 0  # forca usar food imediatamente

        # Se nao tem memoria do pet, nao faz nada
        pet_alive = getattr(char_info, "pet_alive", None)
        if pet_alive is None:
            return False

        # Pet nao esta ativo → invocar
        if not pet_alive:
            key = self._pet_key
            if key:
                input_service.press_key(hwnd, key)
            return True

        # Pet vivo — verificar se precisa alimentar
        elapsed = now - self._start_time
        last = self._last_food

        # Primeiro uso ou passou o intervalo
        if last == 0 or (elapsed - last) >= self._interval_sec:
            key = self._food_key
            if key:
                input_service.press_key(hwnd, key)
            self._last_food = elapsed
            return True

        return False
