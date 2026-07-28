# -*- coding: utf-8 -*-
"""
Ferramenta de diagnostico para testar leitura de memoria.

Testa todos os pointers do MemoryReader contra o processo
do jogo aberto, exibindo sucesso, valores e erros.

Uso: python tools/test_memory.py
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import ctypes
from ctypes import wintypes

import config
from src.infrastructure.window.service import WindowService
from src.services.game.memory_reader import MemoryReader

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(text):
    return f"{GREEN}{text}{RESET}"


def fail(text):
    return f"{RED}{text}{RESET}"


def warn(text):
    return f"{YELLOW}{text}{RESET}"


def section(title):
    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")


def test_property(mr, name, fmt="{}"):
    """Testa uma propriedade do MemoryReader."""
    try:
        val = getattr(mr, name)
        print(f"  {name:25s} = {ok(str(fmt).format(val))}")
        return True
    except Exception as e:
        print(f"  {name:25s} = {fail(str(e)[:50])}")
        return False


def main():
    print(f"{BOLD}Talisman Online — Diagnostico de Memoria{RESET}")
    print()

    ws = WindowService()

    # 1. Encontrar janela
    print("Procurando janela do jogo...")
    try:
        hwnd = ws.connect(title_substring=config.WINDOW_TITLE, timeout=10)
    except Exception as e:
        print(f"  {fail(f'Janela nao encontrada: {e}')}")
        print("\nAbra o jogo primeiro.")
        sys.exit(1)

    print(f"  {ok('Janela encontrada')}  hwnd={hwnd}")

    # 2. Obter PID
    pid = ws._get_window_pid(hwnd)
    print(f"  PID: {pid}")

    # 3. Testar abertura do processo
    print(f"\nTentando abrir processo PID={pid}...")
    try:
        hProcess = kernel32.OpenProcess(0x0010, False, pid)  # PROCESS_VM_READ
        if not hProcess:
            err = ctypes.get_last_error()
            print(f"  {fail(f'OpenProcess falhou. Erro: {err}')}")
            if err == 5:
                print(f"  {warn('Acesso negado. Execute como administrador.')}")
            elif err == 87:
                print(f"  {warn('Parametro invalido. O processo pode nao existir mais.')}")
            sys.exit(1)

        kernel32.CloseHandle(hProcess)
        print(f"  {ok('Processo aberto com sucesso')}")
    except Exception as e:
        print(f"  {fail(str(e))}")
        sys.exit(1)

    # 4. Criar MemoryReader e testar todas as propriedades
    print(f"\nCriando MemoryReader...")
    try:
        mr = MemoryReader(pid)
        print(f"  {ok('MemoryReader criado')}")
    except Exception as e:
        print(f"  {fail(str(e))}")
        sys.exit(1)

    # ---- Char Info ----
    section("CHAR INFO")

    test_property(mr, "char_name", "{}")
    test_property(mr, "level", "{}")
    test_property(mr, "hp", "{}")
    test_property(mr, "max_hp", "{}")
    test_property(mr, "hp_pct", "{:.1f}%")
    test_property(mr, "mana", "{}")
    test_property(mr, "max_mana", "{}")
    test_property(mr, "mana_pct", "{:.1f}%")
    test_property(mr, "xp_pct", "{:.1f}%")
    test_property(mr, "x", "{}")
    test_property(mr, "y", "{}")
    test_property(mr, "location", "{}")

    # ---- Status ----
    section("STATUS")

    test_property(mr, "in_battle", "{}")
    test_property(mr, "is_mounted", "{}")
    test_property(mr, "pet_alive", "{}")
    test_property(mr, "is_sitting", "{}")
    test_property(mr, "team_size", "{}")
    test_property(mr, "is_channeling", "{}")
    test_property(mr, "breakpoint", "{}")

    # ---- Target ----
    section("TARGET")

    test_property(mr, "target_selected", "{}")
    test_property(mr, "target_hp", "{}")
    test_property(mr, "target_hp_pct", "{:.1f}%")
    test_property(mr, "target_name", "{}")
    test_property(mr, "target_dead", "{}")

    # ---- UI State ----
    section("UI STATE")

    test_property(mr, "dialog_open", "{}")
    test_property(mr, "bag_open", "{}")
    test_property(mr, "loot_window", "{}")
    test_property(mr, "notification", "{}")
    test_property(mr, "confirm_box", "{}")

    mr.close()

    print(f"\n{BOLD}Diagnostico concluido.{RESET}")
    print("Se todos apareceram VERMELHOS: os offsets podem estar desatualizados.")
    print("Se apenas alguns falharam: o jogo pode estar em um estado onde")
    print("esses valores nao estao disponiveis (ex: sem alvo selecionado).")


if __name__ == "__main__":
    main()
