# -*- coding: utf-8 -*-
"""
Roda um TRECHO do roteiro do BC no client de verdade.

Existe pra testar um pedaco sem ligar o ciclo inteiro: da pra rodar so
"vai ate a cave e entra" e ver onde quebra, em vez de descobrir isso
junto com preparo, compra, venda e boss.

E o mesmo StepRunner que o bot usa, com os mesmos servicos -- entao o
que acontecer aqui e o que vai acontecer no ciclo. ELE MEXE NO JOGO:
clica, anda e entra na cave.

Uso:
    python tools/rodar_passos.py Tomyris ir_para_cave entrar_na_cave
    python tools/rodar_passos.py Tomyris sair_da_cave

Cada passo e impresso quando comeca. Ctrl+C interrompe.
"""

import os
import sys
import time
from types import SimpleNamespace

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import config
from src.infrastructure.logging.service import LoggingService
from src.infrastructure.input.service import InputService
from src.infrastructure.vision.service import VisionService
from src.infrastructure.window.service import WindowService
from src.services.bot.scripts import bc_steps
from src.services.bot.scripts.bc import DEFAULT_CONFIG
from src.services.bot.step_runner import StepContext, StepRunner
from src.services.game.memory_reader import MemoryReader


def montar(nomes, cfg):
    passos = []
    for nome in nomes:
        fabrica = getattr(bc_steps, nome, None)
        if fabrica is None:
            print(f"Trecho desconhecido: {nome}")
            sys.exit(1)
        trecho = fabrica(cfg)
        print(f"  {nome}: {len(trecho)} passos")
        passos += trecho
    return passos


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    titulo, nomes = sys.argv[1], sys.argv[2:]
    cfg = DEFAULT_CONFIG

    # Sem isto os avisos do runner nao aparecem em lugar nenhum -- e sao
    # eles que dizem POR QUE um passo falhou ("nao chegou em (x,y),
    # parou em (a,b)", "preso, varrendo em circulo"). Diagnosticar sem
    # eles e adivinhar; foi o que aconteceu por varias rodadas.
    LoggingService.setup(to_file=False, to_console=True, force=True)

    ws = WindowService()
    hwnd = ws.connect(title_substring=titulo, timeout=10)
    print(f"Janela: {titulo!r} (hwnd {hwnd})")

    reader = MemoryReader(ws._get_window_pid(hwnd))
    entrada = InputService()
    visao = VisionService(window_service=ws, templates_dir=config.TEMPLATES_DIR)

    print("Montando o roteiro:")
    runner = StepRunner(montar(nomes, cfg), name="teste")

    print()
    ultimo = -1

    try:
        while not runner.finished:
            # char_info precisa de x/y: e o que o walk_to usa pra saber
            # se ja chegou. Sem isso ele pula o passo inteiro.
            char = SimpleNamespace(
                x=reader.x, y=reader.y,
                hp_pct=reader.hp_pct, resource_pct=reader.mana_pct,
                in_battle=reader.in_battle,
            )
            alvo = SimpleNamespace(
                name=reader.target_name, hp_pct=reader.target_hp_pct,
            )

            if runner.index != ultimo:
                passo = runner._steps[runner.index]
                nota = f" -- {passo.note}" if passo.note else ""
                print(f"[{runner.progress}] {passo.kind}{nota} "
                      f"| char={(char.x, char.y)}", flush=True)
                ultimo = runner.index

            runner.tick(StepContext(
                hwnd=hwnd, input_service=entrada,
                vision_service=visao, char_info=char, target_info=alvo,
                # O passo de camera ESCREVE na memoria. Sem isto aqui ele
                # avisa e pula, e o trecho roda com a camera do jeito que
                # estiver -- justamente o que invalida clique de tela.
                memory=reader,
            ))

            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        reader.close()

    print("\nFim do trecho.")


if __name__ == "__main__":
    main()
