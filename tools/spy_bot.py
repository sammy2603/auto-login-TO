# -*- coding: utf-8 -*-
"""
Observa o que outro bot faz com o client, sem tocar no client.

Serve pra uma pergunta so: quando aquele bot "usa o link do Surrounding
sem abrir o painel", o que esta acontecendo por baixo? Ha tres respostas
possiveis, e cada uma deixa uma marca diferente:

1. INJECAO DE CODIGO -- ele carrega um DLL dentro do processo do jogo e
   chama a funcao do cliente direto. Marca: um modulo estranho na lista
   de modulos do processo, ou um depurador anexado.
2. ESCRITA DE MEMORIA -- ele escreve a posicao (ou o destino do
   pathfind) direto. Marca: a coordenada SALTA, em vez de variar de
   pouco em pouco. Personagem andando muda x,y devagar; escrita
   teleporta.
3. UI DE VERDADE, so que rapida -- ele abre o painel, clica no link e
   fecha em poucos quadros, rapido demais pro olho. Marca: o bloco de
   texto do Surrounding e reescrito pouco antes da caminhada comecar.
   Fechar o painel NAO limpa esse bloco (medido, ver PONTEIROS.md), mas
   RE-ABRIR reescreve ele -- e essa reescrita que denuncia.

Nenhuma das tres exige injetar nada, nem no jogo nem no bot: tudo sai de
ReadProcessMemory e da lista de modulos, que e o mesmo acesso que o
nosso proprio leitor ja usa.

Como usar:

    python tools/spy_bot.py --pid 39392 --out stone_city.csv

Deixe rodando, mande o outro bot fazer o trecho de Stone City, e pare
com Ctrl+C. O console mostra so os EVENTOS (salto de posicao, painel
reescrito, modulo novo); o CSV guarda a amostragem inteira, pra conferir
a linha do tempo depois.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import os
import sys
import time
from ctypes import wintypes

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import win32api
import win32con
import win32process

from src.services.game.memory_reader import MemoryReader

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SAMPLE_INTERVAL = 0.05      # 20 Hz -- passo de caminhada nao escapa
PANEL_INTERVAL = 2.0        # a varredura do painel custa ~1 s
MODULE_INTERVAL = 2.0       # conferir modulos novos e barato
# Medido na propria gravacao de 2026-08-06: personagem montado anda a
# 20-28 unidades/s. O criterio e VELOCIDADE e nao distancia porque a
# varredura do painel cega o amostrador por ~0,65 s -- por distancia,
# uma caminhada normal atravessando esse buraco viraria falso "salto".
WALK_SPEED_LIMIT = 60.0     # unidades/s
ROUTE_STEP = 10             # unidades entre dois pontos da rota resumida


def loaded_modules(pid: int) -> set[str]:
    """
    Caminho de todos os modulos carregados no processo.

    Nao adianta comparar com uma lista fixa do que o Windows carrega: o
    que interessa e o que aparece DEPOIS do outro bot conectar, entao a
    comparacao e sempre contra a foto da largada.
    """
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False, pid,
        )
    except Exception as erro:
        print(f"Nao consegui listar modulos: {erro}")
        return set()

    try:
        return {
            win32process.GetModuleFileNameEx(handle, modulo)
            for modulo in win32process.EnumProcessModules(handle)
        }
    finally:
        win32api.CloseHandle(handle)


def debugger_attached(pid: int) -> bool:
    """
    Depurador anexado ao processo do jogo.

    E o outro jeito de chamar funcao do cliente sem DLL proprio: parar o
    processo num ponto e mexer no contexto. Deixa esta marca.
    """
    handle = kernel32.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        presente = wintypes.BOOL()
        if not kernel32.CheckRemoteDebuggerPresent(
            wintypes.HANDLE(handle), ctypes.byref(presente)
        ):
            return False
        return bool(presente.value)
    finally:
        kernel32.CloseHandle(handle)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Observa as acoes de outro bot sobre o client")
    parser.add_argument("--pid", type=int, required=True,
                        help="PID do CLIENT do jogo, nao o do bot")
    parser.add_argument("--out", default="spy_bot.csv")
    parser.add_argument("--route-step", type=float, default=ROUTE_STEP,
                        help="unidades de mundo entre dois pontos da rota "
                             "resumida. O padrao (10) serve pra trecho longo; "
                             "pra aproximacao final use 2 ou 3, senao o "
                             "ultimo ponto cai longe do destino")
    parser.add_argument("--panel-interval", type=float, default=PANEL_INTERVAL,
                        help="segundos entre duas varreduras do painel "
                             "Surrounding (cada varredura custa ~1 s). "
                             "0 desliga: a amostragem fica limpa em 20 Hz, "
                             "que e o que se quer quando o objetivo e "
                             "reconstruir o trajeto")
    args = parser.parse_args()

    reader = MemoryReader(args.pid)

    baseline_modules = loaded_modules(args.pid)
    print(f"Modulos na largada: {len(baseline_modules)}")
    if debugger_attached(args.pid):
        print("!! DEPURADOR ANEXADO ao client -- ja e prova de injecao")

    # Foto inicial do painel: a lista que estiver la agora vem do ultimo
    # render, possivelmente de antes deste teste. O que vale e a MUDANCA
    # daqui pra frente.
    panel_npcs = reader.npcs_ao_redor() if args.panel_interval > 0 else []
    if args.panel_interval > 0:
        print(f"Painel Surrounding na largada: {len(panel_npcs)} NPCs")
        if not panel_npcs:
            print("   (zero = o bloco nao existe neste client. Abra o painel "
                  "uma vez a mao antes de gravar, senao 'painel nunca "
                  "reescrito' nao prova nada)")
    else:
        print("Varredura do painel DESLIGADA -- amostragem limpa em 20 Hz")
    print("\nGravando. Rode o outro bot agora; Ctrl+C para terminar.\n")

    arquivo = open(args.out, "w", newline="", encoding="utf-8")
    escritor = csv.writer(arquivo)
    escritor.writerow([
        "t", "dt", "x", "y", "delta", "speed", "location", "dialog_open",
        "bag_open", "target", "panel_size", "event",
    ])

    inicio = time.time()
    previous = None
    previous_time = None
    next_panel_scan = time.time()
    next_module_check = time.time()
    route = []

    try:
        while True:
            agora = time.time()
            evento = ""

            x, y = reader.x, reader.y
            delta = 0.0
            speed = 0.0
            if previous is not None:
                delta = ((x - previous[0]) ** 2 + (y - previous[1]) ** 2) ** 0.5
                dt = max(agora - previous_time, 1e-6)
                speed = delta / dt
                if speed > WALK_SPEED_LIMIT:
                    # Rapido demais pra ser caminhada: ou o jogo
                    # teleportou (troca de mapa, item), ou alguem
                    # escreveu a coordenada.
                    evento = f"SALTO {delta:.0f} unidades a {speed:.0f} u/s"
            dt = agora - previous_time if previous_time else 0.0
            previous = (x, y)
            previous_time = agora

            # Rota resumida: um ponto a cada ROUTE_STEP unidades. E o que
            # vira lista de waypoints pro nosso proprio roteiro.
            if not route or ((x - route[-1][0]) ** 2
                             + (y - route[-1][1]) ** 2) ** 0.5 >= args.route_step:
                route.append((x, y))

            if agora >= next_module_check:
                next_module_check = agora + MODULE_INTERVAL
                novos = loaded_modules(args.pid) - baseline_modules
                if novos:
                    baseline_modules |= novos
                    for caminho in novos:
                        evento = (evento + " | " if evento else "") +                             f"MODULO NOVO: {caminho}"

            if args.panel_interval > 0 and agora >= next_panel_scan:
                anterior = panel_npcs
                panel_npcs = reader.npcs_ao_redor()
                if panel_npcs != anterior:
                    # O bloco so e reescrito quando o painel RENDERIZA.
                    # Mudou = o painel foi aberto, visivel ou nao.
                    evento = (evento + " | " if evento else "") + \
                        f"PAINEL reescrito ({len(anterior)} -> {len(panel_npcs)})"
                next_panel_scan = agora + args.panel_interval

                novos = loaded_modules(args.pid) - baseline_modules
                if novos:
                    baseline_modules |= novos
                    for caminho in novos:
                        evento = (evento + " | " if evento else "") + \
                            f"MODULO NOVO: {caminho}"

            escritor.writerow([
                f"{agora - inicio:.2f}", f"{dt:.3f}", x, y, f"{delta:.1f}",
                f"{speed:.1f}", reader.location, int(reader.dialog_open),
                int(reader.bag_open), reader.target_name, len(panel_npcs),
                evento,
            ])

            if evento:
                print(f"  [{agora - inicio:7.2f}s] ({x},{y}) {evento}")

            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        arquivo.close()
        reader.close()

    print(f"\nLinha do tempo em {args.out}")

    if len(route) > 1:
        print(f"\nRota percorrida ({len(route)} pontos, 1 a cada "
              f"{args.route_step:g} unidades) -- pronta pra colar:\n")
        for ponto in route:
            print(f"        {ponto},")
        # O ultimo ponto e o que mais importa numa gravacao de
        # aproximacao: e onde o personagem de fato parou, e e ele que
        # vira o destino final do roteiro.
        print(f"\n    parou em: {route[-1]}")

    print(
        "Leitura: painel reescrito ANTES da caminhada = ele usa a UI de "
        "verdade, so que rapido. Caminhada sem painel reescrito e sem salto "
        "= chamada direta de funcao do cliente. Salto de posicao = escrita "
        "de memoria."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
