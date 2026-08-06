# -*- coding: utf-8 -*-
"""
Grava uma rota de minimapa a partir dos SEUS cliques.

Por que existe: o minimapa e centrado no personagem, entao um pixel nele
e um deslocamento RELATIVO, nao um destino. Calcular esse pixel exigiria
saber centro, raio e escala do minimapa -- e medir a escala andando nao
funciona dentro da cidade, onde o pathfinding contorna predio e falseia
o deslocamento (medido: quatro cliques de 40px deram escalas de 0.00,
0.53, 0.05 e 0.75). Gravar o clique que voce sabe que funciona pula o
problema inteiro.

Como usar:

    python tools/gravar_rota.py --pid 39392

Deixe rodando, clique com o BOTAO DIREITO no minimapa fazendo o
trajeto, e pare com Ctrl+C. Sai uma lista pronta pra colar no
DEFAULT_CONFIG, com o pixel de cada clique e a coordenada de mundo onde
o personagem parou depois dele.

Grava so clique DENTRO da area do minimapa: clique no mundo e movimento
comum e nao faz parte da rota.

Para o MAPA-MUNDI (tecla M), que e como se cortam os trajetos longos
sem passar por estrada:

    python tools/gravar_rota.py --pid 39392 --mapa

Ai nao ha area a filtrar -- a janela do mapa ocupa boa parte da tela --
e a saida ja vem com o nome 'cave_map_clicks'.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import win32api
import win32gui

from src.infrastructure.window.service import WindowService
from src.services.game.memory_reader import MemoryReader

VK_RBUTTON = 0x02


def dentro_do_minimapa(x: int, y: int, centro, raio: int) -> bool:
    """O minimapa e circular; canto do retangulo nao conta."""
    dx, dy = x - centro[0], y - centro[1]
    return (dx * dx + dy * dy) <= raio * raio


def esperar_parar(mr, limite: float = 20.0):
    """Devolve a posicao quando o personagem para de andar."""
    anterior = (mr.x, mr.y)
    fim = time.time() + limite
    while time.time() < fim:
        time.sleep(1.0)
        atual = (mr.x, mr.y)
        if atual == anterior:
            return atual
        anterior = atual
    return anterior


def main():
    ap = argparse.ArgumentParser(
        description="Grava rota de minimapa ou de mapa-mundi")
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--centro", type=int, nargs=2, default=(915, 112))
    ap.add_argument("--raio", type=int, default=60)
    ap.add_argument(
        "--mapa", action="store_true",
        help="grava cliques no MAPA-MUNDI aberto (tecla M) em vez do "
             "minimapa: aceita clique em qualquer ponto da janela",
    )
    args = ap.parse_args()

    hwnd = WindowService().find_by_pid(args.pid)
    if not hwnd:
        print(f"Janela do PID {args.pid} nao encontrada")
        return 1

    mr = MemoryReader(args.pid)
    onde = "MAPA-MUNDI aberto (tecla M)" if args.mapa else "minimapa"
    print(f"Gravando em {mr.location}. Clique com o botao DIREITO no "
          f"{onde}; Ctrl+C para terminar.\n")

    rota = []
    pressionado = False
    try:
        while True:
            agora = win32api.GetAsyncKeyState(VK_RBUTTON) < 0
            if agora and not pressionado:
                x, y = win32gui.ScreenToClient(hwnd, win32gui.GetCursorPos())
                # No mapa-mundi nao ha area a filtrar: a janela ocupa
                # boa parte da tela e o clique util pode cair em
                # qualquer canto dela.
                if args.mapa or dentro_do_minimapa(x, y, args.centro, args.raio):
                    antes = (mr.x, mr.y)
                    # Trecho de mapa-mundi atravessa o mapa inteiro e
                    # passa dos 20s do minimapa com folga.
                    destino = esperar_parar(mr, 90.0 if args.mapa else 20.0)
                    rota.append((x, y, destino))
                    print(f"  {len(rota):2}. clique ({x}, {y})  "
                          f"{antes} -> {destino}")
            pressionado = agora
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        mr.close()

    if not rota:
        print(f"\nNenhum clique no {onde} foi gravado.")
        return 0

    print("\nPronto pra colar no DEFAULT_CONFIG:\n")
    print('    "cave_map_clicks": [' if args.mapa else '    "rota_...": [')
    for x, y, destino in rota:
        print(f"        ({x}, {y}),   # chega em {destino}")
    print("    ],")
    return 0


if __name__ == "__main__":
    sys.exit(main())
