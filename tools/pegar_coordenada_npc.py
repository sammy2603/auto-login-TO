# -*- coding: utf-8 -*-
"""
Coordenada de mundo dos NPCs-objetivo das missoes ativas.

Devolve a linha pronta pra colar no DEFAULT_CONFIG do BC, sem anotar a
coordenada a mao.

LIMITE, e ele e grande: a fonte e o rastreador de missoes, nao o painel
Surrounding. So aparece NPC ligado a uma missao ATIVA do personagem --
NPC qualquer, como a Skull Herald, nunca vai estar aqui. Ver
.project/context/PONTEIROS.md.

A distancia em metros e do ultimo render, nao do instante da leitura.
A coordenada nao sofre com isso, que e fixa.

Com varias contas abertas, diga qual cliente com --pid: sem isso vale o
primeiro client.exe encontrado, que pode ser um que nem terminou de
logar.

Uso:
    python tools/pegar_coordenada_npc.py             # lista tudo
    python tools/pegar_coordenada_npc.py eagle       # filtra por nome
    python tools/pegar_coordenada_npc.py eagle --pid 38640
    python tools/pegar_coordenada_npc.py --autoteste
"""

import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.dirname(__file__))

from comparar_ponteiros import achar_pid, caminho_processo


def filtrar(entradas, termo):
    """Casa por pedaco do nome, sem diferenciar maiuscula."""
    if not termo:
        return list(entradas)
    alvo = termo.strip().lower()
    return [e for e in entradas if alvo in e[0].lower()]


def outros_clientes(pid_usado):
    """PIDs de outros client.exe abertos, para o recado de erro."""
    import win32gui
    import win32process

    achados = {}

    def visitar(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd).strip():
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            caminho = caminho_processo(pid)
            if (caminho and os.path.basename(caminho).lower() == "client.exe"
                    and pid != pid_usado):
                achados[pid] = win32gui.GetWindowText(hwnd).strip()
        return True

    win32gui.EnumWindows(visitar, None)
    return achados


def imprimir(entradas, termo, pid=None):
    if not entradas:
        print(f"  Nenhum NPC{f' com {termo!r}' if termo else ''} na lista.")
        print("  A fonte e o rastreador de MISSOES: so aparece NPC de")
        print("  missao ativa deste personagem, nunca um NPC qualquer.")
        for outro, titulo in outros_clientes(pid).items():
            print(f"  Ha outro cliente aberto: --pid {outro}  ({titulo[:40]})")
        return

    print(f"  {'nome':34s} {'coordenada':>16s}   dist")
    print("  " + "-" * 60)
    for nome, x, y, dist in entradas:
        print(f"  {nome:34s} {f'({x}, {y})':>16s}   {dist} m")

    print("\n  Pronto pra colar no DEFAULT_CONFIG:")
    for nome, x, y, _ in entradas:
        print(f'    # {nome}\n    "npc_..._pos": ({x}, {y}),')


def autoteste():
    amostra = [
        ("Skull Herald", 1395, -636, 12),
        ("Courage Merchant", 231, -517, 1269),
        ("Buddha Slave (right-click me)", 380, 1125, 214),
    ]
    assert filtrar(amostra, "skull") == [amostra[0]]
    assert filtrar(amostra, "SKULL") == [amostra[0]]        # sem case
    assert filtrar(amostra, " skull ") == [amostra[0]]      # com espaco
    assert filtrar(amostra, "herald") == [amostra[0]]       # pedaco do meio
    assert filtrar(amostra, "right-click") == [amostra[2]]  # nome com pontuacao
    assert filtrar(amostra, "") == amostra                  # sem termo, tudo
    assert filtrar(amostra, None) == amostra
    assert filtrar(amostra, "nao existe") == []
    assert filtrar([], "skull") == []
    print("autoteste ok")


def main():
    ap = argparse.ArgumentParser(description="Coordenada de NPC pelo Surrounding")
    ap.add_argument("nome", nargs="?", default="", help="pedaco do nome do NPC")
    ap.add_argument("--pid", type=int, help="cliente alvo, com varias contas abertas")
    ap.add_argument("--autoteste", action="store_true", help="valida o filtro, sem jogo")
    args = ap.parse_args()

    if args.autoteste:
        autoteste()
        return

    pid = args.pid or achar_pid()
    if not pid:
        sys.exit(1)

    from src.services.game.memory_reader import MemoryReader

    mr = MemoryReader(pid)
    try:
        imprimir(filtrar(mr.objetivos_de_missao(), args.nome), args.nome, pid)
    finally:
        mr.close()


if __name__ == "__main__":
    main()
