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

    python tools/gravar_rota.py --janela Tomyris

O nome e um PEDACO do titulo da janela (mesma busca que o resto do
projeto usa), e nao o PID: o PID muda toda vez que o cliente reabre, e
ter que caca-lo antes de cada gravacao so atrapalha. O PID sai do
proprio hwnd, que e o que o MemoryReader precisa.

Deixe rodando, clique com o BOTAO DIREITO no minimapa fazendo o
trajeto, e pare com Ctrl+C. Sai uma lista pronta pra colar no
DEFAULT_CONFIG, com o pixel de cada clique e a coordenada de mundo onde
o personagem parou depois dele.

Grava so clique DENTRO da area do minimapa: clique no mundo e movimento
comum e nao faz parte da rota.

Para o MAPA-MUNDI (tecla M), que e como se cortam os trajetos longos
sem passar por estrada:

    python tools/gravar_rota.py --janela Tomyris --mapa

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
import win32process

from src.infrastructure.window.service import WindowService
from src.services.game.memory_reader import MemoryReader

VK_RBUTTON = 0x02


def dentro_do_minimapa(x: int, y: int, center, radius: int) -> bool:
    """O minimapa e circular; canto do retangulo nao conta."""
    dx, dy = x - center[0], y - center[1]
    return (dx * dx + dy * dy) <= radius * radius


# Removida a antiga esperar_parar: ela BLOQUEAVA o laco por ate 20 s
# esperando o personagem chegar, e nesse intervalo GetAsyncKeyState nao
# era lido -- todo clique dado durante a caminhada sumia sem deixar
# rastro. Quem clica encadeado (que e como se joga) perdia a maioria.
#
# Hoje o laco nunca bloqueia: o destino de um clique e simplesmente a
# posicao lida no instante do clique SEGUINTE, que e exatamente o ponto
# de partida dele. Sem espera, sem clique perdido, e a origem gravada
# passa a ser a origem real.


def main():
    ap = argparse.ArgumentParser(
        description="Grava rota de minimapa ou de mapa-mundi")
    ap.add_argument("--janela", required=True,
                    help="pedaco do titulo da janela do cliente")
    # A flag continua em portugues -- e o que esta documentado e no dedo
    # de quem usa; o atributo vai pra ingles junto com o resto do codigo.
    # 'dest' e o que separa a interface do identificador.
    ap.add_argument("--centro", dest="center", type=int, nargs=2,
                    default=(915, 112))
    ap.add_argument("--raio", dest="radius", type=int, default=60)
    ap.add_argument(
        "--mapa", action="store_true",
        help="grava cliques no MAPA-MUNDI aberto (tecla M) em vez do "
             "minimapa: aceita clique em qualquer ponto da janela",
    )
    args = ap.parse_args()

    hwnd = WindowService().find(args.janela)
    if not hwnd:
        print(f"Nenhuma janela com '{args.janela}' no titulo")
        return 1

    # O MemoryReader abre o processo pelo PID, entao ele ainda e
    # necessario -- so nao precisa vir digitado: o hwnd ja o carrega.
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    print(f"Janela '{win32gui.GetWindowText(hwnd)}' (PID {pid})")

    mr = MemoryReader(pid)
    onde = "MAPA-MUNDI aberto (tecla M)" if args.mapa else "minimapa"
    print(f"Gravando em {mr.location}. Clique com o botao DIREITO no "
          f"{onde}; Ctrl+C para terminar.\n")

    rota = []
    pressionado = False
    descartados = 0
    try:
        while True:
            agora = win32api.GetAsyncKeyState(VK_RBUTTON) < 0
            if agora and not pressionado:
                x, y = win32gui.ScreenToClient(hwnd, win32gui.GetCursorPos())
                # No mapa-mundi nao ha area a filtrar: a janela ocupa
                # boa parte da tela e o clique util pode cair em
                # qualquer canto dela.
                if args.mapa or dentro_do_minimapa(x, y, args.center, args.radius):
                    origem = (mr.x, mr.y)
                    instante = time.time()
                    # O clique anterior so agora sabe onde terminou: e
                    # aqui que o personagem estava quando o proximo
                    # partiu. E tambem quanto tempo o trecho levou --
                    # que e o que o roteiro tem que reproduzir.
                    if rota:
                        rota[-1]["destino"] = origem
                        rota[-1]["dt"] = round(instante - rota[-1]["t"], 2)
                    rota.append({"x": x, "y": y, "origem": origem,
                                 "t": instante, "destino": None, "dt": None})
                    print(f"  {len(rota):2}. clique ({x}, {y})  de {origem}")
                else:
                    # Descarte silencioso escondia centro/raio errados:
                    # a rota saia curta e ninguem sabia por que.
                    descartados += 1
                    print(f"  -- clique ({x}, {y}) FORA do minimapa "
                          f"(centro {tuple(args.center)}, raio {args.radius})")
            pressionado = agora
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass

    if rota:
        # O ultimo clique fecha com a posicao de agora: o Ctrl+C vem
        # depois de o personagem ter chegado.
        rota[-1]["destino"] = (mr.x, mr.y)
        rota[-1]["dt"] = round(time.time() - rota[-1]["t"], 2)
    mr.close()

    if not rota:
        print(f"\nNenhum clique no {onde} foi gravado"
              f" ({descartados} descartados por cairem fora).")
        return 0

    print(f"\n{len(rota)} cliques gravados, {descartados} descartados.")
    print("Pronto pra colar no DEFAULT_CONFIG:\n")
    print('    "cave_map_clicks": [' if args.mapa else '    "cave_click_route": [')
    for c in rota:
        print(f"        ({c['x']}, {c['y']}, {c['dt']}),"
              f"   # {c['origem']} -> {c['destino']}")
    print("    ],")
    return 0


if __name__ == "__main__":
    sys.exit(main())
