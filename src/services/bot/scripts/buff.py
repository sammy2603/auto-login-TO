from __future__ import annotations


class BuffScript:
    """
    Script de Buffs.

    - 3 skills com enable/disable individual
    - Self Buff: reaplica a cada X minutos (1-30)
    - Cicla pelas skills habilitadas com cooldown entre casts
    """

    name = "Buff"

    CAST_COOLDOWN = 2.0  # segundos entre casts de buff

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._last_cast = 0.0
        self._skill_index = 0
        self._last_self_buff = 0.0
        self._start_time = 0.0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()

        if self._start_time == 0:
            self._start_time = now
            self._last_self_buff = 0

        # Self Buff — reaplica a cada X minutos
        sb = self._config.get("self_buff", {})
        if sb.get("enabled"):
            interval = sb.get("interval_min", 15) * 60.0
            elapsed = now - self._start_time
            last = self._last_self_buff
            if last == 0 or (elapsed - last) >= interval:
                # Usa a primeira skill habilitada para self buff
                skills = self._config.get("skills", [])
                for sk in skills:
                    if sk.get("enabled") and sk.get("key"):
                        input_service.press_key(hwnd, sk["key"])
                        self._last_self_buff = elapsed
                        self._last_cast = now
                        return True
                # Se nenhuma skill habilitada, marca como feito
                self._last_self_buff = elapsed

        # Skills normais — cicla com cooldown
        if now - self._last_cast < self.CAST_COOLDOWN:
            return False

        skills = self._config.get("skills", [])
        enabled = [(i, sk) for i, sk in enumerate(skills) if sk.get("enabled") and sk.get("key")]
        if not enabled:
            return False

        self._skill_index = self._skill_index % len(enabled)
        _, sk = enabled[self._skill_index]
        input_service.press_key(hwnd, sk["key"])
        self._skill_index += 1
        self._last_cast = now
        return True
