# -*- coding: utf-8 -*-
"""
Manda UM clique no minimapa e mede pra onde o personagem foi.

Existe pra separar duas causas que se confundem quando a rota gravada
nao se repete na execucao:

  a) o clique ENVIADO nao cai no mesmo lugar que o clique FISICO da
     gravacao (coordenada, foco, zoom diferente);
  b) o clique cai certo, e o que diverge e o acumulo ao longo da rota
     (timing, ponto de partida).

Gravar e rodar produzem o mesmo dado -- origem, pixel, destino --, entao
da pra comparar linha a linha com a saida do gravar_rota.py.

Uso:

    python tools/testar_clique_minimapa.py --janela Tomyris --pixel 947 149

Com o personagem no mesmo ponto de partida da gravacao. Compare o
destino impresso com o comentario da linha correspondente em
cave_click_route.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import win32gui
import win32process

from src.infrastructure.input.service import InputService
from src.infrastructure.window.service import WindowService
from src.services.game.memory_reader import MemoryReader


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Mede o deslocamento de um clique no minimapa")
    ap.add_argument("--janela", required=True)
    ap.add_argument("--pixel", type=int, nargs=2, required=True,
                    metavar=("X", "Y"))
    ap.add_argument("--segundos", type=float, default=3.0,
                    help="quanto esperar antes de ler o destino")
    args = ap.parse_args()

    hwnd = WindowService().find(args.janela)
    if not hwnd:
        print(f"Nenhuma janela com '{args.janela}' no titulo")
        return 1

    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    print(f"Janela '{win32gui.GetWindowText(hwnd)}' (PID {pid})")
    print(f"GetClientRect: {win32gui.GetClientRect(hwnd)}")

    mr = MemoryReader(pid)
    x, y = args.pixel
    origem = (mr.x, mr.y)

    InputService().right_click(hwnd, x, y)
    time.sleep(args.segundos)

    destino = (mr.x, mr.y)
    mr.close()

    dx, dy = destino[0] - origem[0], destino[1] - origem[1]
    print(f"\nclique ({x}, {y})  {origem} -> {destino}")
    print(f"deslocamento: ({dx:+}, {dy:+})  |  "
          f"{(dx * dx + dy * dy) ** 0.5:.1f} unidades")
    if origem == destino:
        print("NAO SAIU DO LUGAR: o clique nao chegou, ou caiu fora do minimapa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
