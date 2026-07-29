from __future__ import annotations


class PotionScript:
    """
    Script de pocoes com 4 tipos:

    - HP Potion:   usa fora de batalha se HP < threshold
    - Mana Potion: usa fora de batalha se mana < threshold
    - Battle HP:   usa em batalha se HP < threshold
    - Battle Mana: usa em batalha se mana < threshold
    """

    name = "Potion"

    COOLDOWN = 5.0

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._last_use: dict[str, float] = {}

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        import time
        now = time.time()

        if not char_info:
            return False

        in_battle = getattr(char_info, "in_battle", False)
        acted = False

        for slot, keys in [
            ("hp_potion", ["hp_potion"]),
            ("mana_potion", ["mana_potion"]),
            ("battle_hp", ["battle_hp"]),
            ("battle_mana", ["battle_mana"]),
        ]:
            item = self._config.get(slot, {})
            if not item.get("enabled"):
                continue

            is_battle_slot = slot.startswith("battle_")
            if is_battle_slot != in_battle:
                continue

            key = item.get("key", "")
            if not key:
                continue

            threshold = item.get("threshold", 50)
            is_hp = "hp" in slot

            current_pct = char_info.hp_pct if is_hp else char_info.resource_pct
            if current_pct >= threshold:
                continue

            last = self._last_use.get(slot, 0.0)
            if now - last < self.COOLDOWN:
                continue

            input_service.press_key(hwnd, key)
            self._last_use[slot] = now
            acted = True

        return acted
