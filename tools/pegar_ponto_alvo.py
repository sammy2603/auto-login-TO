# -*- coding: utf-8 -*-
"""
Descobre o ponto de tela de um NPC/mob: voce clica nele, a ferramenta
diz onde foi.

Por que assim e nao "olhar a imagem e estimar": o clique no cenario e
ambiguo (personagem por cima, efeito de luz, mob empilhado), e um
palpite errado so aparece na hora em que o bot ja esta rodando. Aqui a
confirmacao vem da MEMORIA -- o ponto so e registrado quando o alvo
selecionado muda de verdade.

O numero que sai daqui e coordenada da CLIENT AREA, que e a que os
passos do roteiro usam.

Uso:
    python tools/pegar_ponto_alvo.py Tomyris
    python tools/pegar_ponto_alvo.py Tomyris 60     # 60 segundos

Deixe rodando, clique no alvo quantas vezes quiser (da pra conferir se
o ponto se repete) e encerre com Ctrl+C ou espere o tempo acabar.
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import win32api
import win32gui

import config
from src.infrastructure.window.service import WindowService
from src.services.game.memory_reader import MemoryReader


def main():
    titulo = sys.argv[1] if len(sys.argv) > 1 else config.WINDOW_TITLE
    duracao = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

    ws = WindowService()

    try:
        hwnd = ws.connect(title_substring=titulo, timeout=10)
    except Exception as e:
        print(f"Janela '{titulo}' nao encontrada: {e}")
        sys.exit(1)

    print(f"Janela: {win32gui.GetWindowText(hwnd)!r} (hwnd {hwnd})")

    reader = MemoryReader(ws._get_window_pid(hwnd))

    print(f"Clique nos alvos. Registrando por {int(duracao)}s (Ctrl+C encerra).")
    print()

    fim = time.time() + duracao

    # VK_LBUTTON / VK_RBUTTON
    BOTOES = {0x01: "esquerdo", 0x02: "direito"}
    antes = {vk: False for vk in BOTOES}

    try:
        while time.time() < fim:
            # Registra pelo CLIQUE, nao pela mudanca do nome do alvo.
            # Esperar o nome mudar perde o caso de reclicar no mesmo NPC
            # (nao muda nada, nao registra nada) -- e ai a ferramenta
            # parece quebrada quando so nao houve transicao.
            for vk, nome in BOTOES.items():
                agora = win32api.GetAsyncKeyState(vk) < 0

                if agora and not antes[vk]:
                    x, y = win32gui.ScreenToClient(
                        hwnd, win32gui.GetCursorPos()
                    )
                    # O jogo leva alguns quadros pra registrar a selecao.
                    time.sleep(0.4)
                    alvo = reader.target_name or "(nada)"
                    print(f"  {nome:9s} ({x}, {y})  ->  {alvo}", flush=True)

                antes[vk] = agora

            time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        reader.close()

    print()
    print("Fim.")


if __name__ == "__main__":
    main()
