from __future__ import annotations


class AttackScript:
    """
    Script de ataque automatico.

    Estrategia:
    1. Se ha alvo com HP > 0, ataca (tecla de ataque ou skill)
    2. Se nao ha alvo, procura o alvo mais proximo (Tab)
    3. Se HP do personagem esta baixo, nao ataca (aguarda Potion)

    Nota: este script e um exemplo. As teclas, templates e
    coordenadas precisam ser calibradas para cada cliente.
    """

    name = "Attack"

    # Tecla virtual de ataque (ajustar conforme o jogo)
    ATTACK_KEY = "1"

    # Abaixo de qual % de HP o script para de atacar
    MIN_HP_PCT = 25.0

    # Tempo minimo entre ataques (segundos)
    ATTACK_COOLDOWN = 1.5

    def __init__(self):
        self._last_attack = 0.0
        self._last_tab = 0.0

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

        now = time.time()

        # Seguranca: nao ataca se HP muito baixo
        if char_info.hp_pct < self.MIN_HP_PCT:
            return False

        # Se tem alvo com HP > 0, ataca
        if target_info.hp_pct > 0:
            if now - self._last_attack >= self.ATTACK_COOLDOWN:
                input_service.press_key(hwnd, self.ATTACK_KEY)
                self._last_attack = now
                return True
            return False

        # Se nao tem alvo, procura (Tab)
        if now - self._last_tab >= 1.0:
            input_service.press_key(hwnd, "TAB")
            self._last_tab = now
            return True

        return False
