# -*- coding: utf-8 -*-
"""
Coordenada de mundo dos NPCs do mapa atual, pelo painel Surrounding.

Devolve a linha pronta pra colar no DEFAULT_CONFIG do BC, sem anotar a
coordenada a mao.

EXIGE que o painel Surrounding tenha sido ABERTO pelo menos uma vez no
mapa em questao. Fechar o painel nao limpa o bloco, entao trocar de
mapa sem reabrir devolve a lista do mapa ANTERIOR, com cara de valida.

Sem nada no painel, cai no rastreador de missoes, que so conhece NPC de
missao ATIVA -- nunca traz NPC qualquer (uma Skull Herald, por
exemplo). Ver .project/context/PONTEIROS.md.

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
        print("  Abra o painel Surrounding no cliente uma vez neste mapa:")
        print("  sem isso o bloco nao existe, e a reserva (rastreador de")
        print("  missoes) so conhece NPC de missao ativa do personagem.")
        for outro, titulo in outros_clientes(pid).items():
            print(f"  Ha outro cliente aberto: --pid {outro}  ({titulo[:40]})")
        return

    print(f"  {'nome':34s} {'coordenada':>16s}")
    print("  " + "-" * 52)
    for nome, x, y in entradas:
        print(f"  {nome:34s} {f'({x}, {y})':>16s}")

    print("\n  Pronto pra colar no DEFAULT_CONFIG:")
    for nome, x, y in entradas:
        print(f'    # {nome}\n    "npc_..._pos": ({x}, {y}),')


def autoteste():
    amostra = [
        ("Skull Herald", 1395, -636),
        ("Courage Merchant", 231, -517),
        ("Buddha Slave (right-click me)", 380, 1125),
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
    ap.add_argument("--salvar", action="store_true",
                    help="grava o mapa atual em npcs.json (catalogo do bot)")
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
        # Painel primeiro: e o unico que conhece NPC que nao e de quest.
        # A reserva so entra quando o painel esta fechado.
        entradas = mr.npcs_ao_redor()
        if not entradas:
            entradas = [(nome, x, y) for nome, x, y, _ in mr.objetivos_de_missao()]

        if args.salvar:
            # Salva o mapa INTEIRO, nao o resultado filtrado: catalogo
            # pela metade e pior que catalogo nenhum, porque parece
            # completo.
            from src.services.game.npcs import CATALOGO, salvar

            mapa = mr.location
            n = salvar(mapa, entradas)
            if n:
                print(f"  {n} NPCs de {mapa!r} gravados em {CATALOGO}")
            else:
                print(f"  Nada a gravar: lista vazia em {mapa!r}.")

        imprimir(filtrar(entradas, args.nome), args.nome, pid)
    finally:
        mr.close()


if __name__ == "__main__":
    main()
