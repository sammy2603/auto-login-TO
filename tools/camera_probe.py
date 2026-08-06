# -*- coding: utf-8 -*-
"""
Descobre QUAL estrutura de camera o cliente usa de verdade.

O problema que motivou: escrever zoom/rotacao/angulo na base que o
PONTEIROS.md documenta (0x01170054) muda a memoria e NAO muda a tela. E
o cliente tambem nao reescreve o que gravamos -- ou seja, aquela
estrutura nao e a que o renderizador le a cada quadro.

O criterio aqui nao e "onde tem um float plausivel", que foi o que
levou ao endereco errado: e QUAL endereco MUDA quando o jogador mexe na
camera. Camera viva acompanha a mao; copia nao acompanha.

Duas candidatas de largada -- a nossa e a do bot de referencia, que usa
outra base com os mesmos offsets. Nada impede que as duas estejam
erradas neste cliente (o seu tem o limite de zoom liberado, e essa
modificacao pode ter mexido no arranjo).

Uso:

    python tools/camera_probe.py --pid 840

Deixe rodando os 15 s e, durante esse tempo, GIRE a camera e ROLE o
zoom no jogo. No fim ele diz quais campos variaram e quanto.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.services.game.memory_reader import MemoryReader, _rpm_float, _rpm_int

# Base nossa (PONTEIROS.md) e a do RamoraBOT. Os offsets sao os mesmos
# nas duas, o que sugere a mesma classe em enderecos diferentes -- uma
# provavelmente e a camera ativa e a outra uma copia.
CANDIDATE_BASES = {
    "nossa   0x01170054": 0x01170054,
    "ramora  0x0116FFF4": 0x0116FFF4,
}

# Alem dos tres conhecidos, alguns vizinhos: se a estrutura mudou de
# layout entre versoes, o campo certo tende a estar ao lado.
OFFSETS = (0x54, 0x58, 0x5C, 0x60, 0x64, 0x68, 0x6C, 0x70)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descobre qual estrutura de camera o cliente usa")
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--seconds", type=float, default=15.0)
    args = parser.parse_args()

    reader = MemoryReader(args.pid)

    resolved = {}
    for rotulo, base_addr in CANDIDATE_BASES.items():
        ponteiro = _rpm_int(reader._hProcess, base_addr, 4)
        resolved[rotulo] = ponteiro
        estado = f"-> 0x{ponteiro:08X}" if ponteiro else "NAO RESOLVE"
        print(f"{rotulo}  {estado}")

    if not any(resolved.values()):
        print("\nNenhuma das bases resolve. O cliente mudou de versao.")
        reader.close()
        return 1

    print(f"\nMEXA NA CAMERA AGORA -- gire e role o zoom por {args.seconds:.0f} s\n")

    # Guarda min/max de cada campo: variacao e o unico sinal que
    # interessa. Valor absoluto nao diz nada -- copia parada tambem tem
    # numero plausivel.
    faixas: dict[tuple[str, int], list[float]] = {}
    fim = time.time() + args.seconds

    while time.time() < fim:
        for rotulo, ponteiro in resolved.items():
            if not ponteiro:
                continue
            for offset in OFFSETS:
                valor = _rpm_float(reader._hProcess, ponteiro + offset)
                chave = (rotulo, offset)
                if chave not in faixas:
                    faixas[chave] = [valor, valor]
                else:
                    faixas[chave][0] = min(faixas[chave][0], valor)
                    faixas[chave][1] = max(faixas[chave][1], valor)
        time.sleep(0.05)

    print("Campos que VARIARAM (esses sao a camera viva):\n")
    achou = False
    for (rotulo, offset), (menor, maior) in sorted(faixas.items()):
        variacao = maior - menor
        if variacao > 0.01:
            achou = True
            print(f"  {rotulo}  +0x{offset:02X}  "
                  f"{menor:10.2f} -> {maior:10.2f}   (delta {variacao:.2f})")

    if not achou:
        print("  NENHUM. Ou a camera nao foi movida durante a medicao, ou o\n"
              "  cliente guarda a camera em outro lugar -- nesse caso o\n"
              "  caminho e o scan de valor desconhecido descrito no\n"
              "  PONTEIROS.md, secao 'Receita do scan de valor desconhecido'.")

    print("\nCampos PARADOS (copia, ou nada a ver com camera):")
    for (rotulo, offset), (menor, maior) in sorted(faixas.items()):
        if maior - menor <= 0.01:
            print(f"  {rotulo}  +0x{offset:02X}  {menor:10.2f}")

    reader.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
