from __future__ import annotations


class SellScript:
    """
    Vende itens para NPC.

    Stub — requer navegacao ate NPC, abertura de loja,
    selecao de itens, confirmacao.
    """

    name = "Sell"

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        return False
