from __future__ import annotations


class DRLureScript:
    """
    DR Lure — mantem o personagem a distancia de determinados bosses e
    os conduz pelo mapa segurando o aggro, pra que outros personagens
    ataquem em seguranca (kiting).

    Stub — aguarda implementacao externa. Vai precisar de controle de
    movimento e de leitura continua da distancia ate o boss, coisas que
    os outros scripts ainda nao fazem.
    """

    name = "DR Lure"

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        return False
