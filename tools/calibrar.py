# -*- coding: utf-8 -*-
"""
Calibrador visual: pega coordenadas e recorta templates da janela do
jogo, com o mouse.

Era a ferramenta que faltava. capture_screenshot.py salva a tela inteira
e debug_templates.py confere um template pronto -- mas nao havia como
descobrir a COORDENADA de um ponto nem gerar o recorte, que e
exatamente o que o BC precisa (botao de aceitar convite, Treasure Box,
corpo do boss, icone da bag de courage).

A captura usa PrintWindow: NAO move o mouse nem exige a janela em
primeiro plano. Da pra jogar normalmente enquanto calibra.

Uso:
    python tools/calibrar.py                    # conecta pelo titulo padrao
    python tools/calibrar.py "Tomyris"          # conecta por outro titulo
    python tools/calibrar.py --arquivo tela.png # trabalha sobre um PNG

Na janela que abrir:
    mover o mouse    mostra a coordenada embaixo do cursor
    clique simples   fixa a coordenada e imprime no terminal
    arrastar         desenha o retangulo do recorte
    S                salva o recorte em templates/ (pede o nome)
    R                recaptura a janela do jogo
    G                liga/desliga a grade de 50px
    Z                amplia/reduz a lupa 4x no canto
    ESC ou Q         sai
"""

from __future__ import annotations

import os
import sys

import cv2
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import config  # noqa: E402
from src.infrastructure.window.service import WindowService  # noqa: E402

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
JANELA = "Calibrador -- S salva recorte | R recaptura | G grade | Z lupa | Q sai"

VERDE = (0, 255, 0)
AMARELO = (0, 255, 255)
CINZA = (90, 90, 90)


class Calibrador:

    def __init__(self, imagem, recapturar=None):
        self.base = imagem
        self.recapturar = recapturar
        self.cursor = (0, 0)
        self.fixado = None
        self.inicio_arrasto = None
        self.retangulo = None
        self.grade = False
        self.lupa = True

    # -------------------------------------------------
    # Mouse
    # -------------------------------------------------

    def ao_mouse(self, evento, x, y, _flags, _param):
        self.cursor = (x, y)

        if evento == cv2.EVENT_LBUTTONDOWN:
            self.inicio_arrasto = (x, y)
            self.retangulo = None

        elif evento == cv2.EVENT_MOUSEMOVE and self.inicio_arrasto:
            self.retangulo = self._normalizar(self.inicio_arrasto, (x, y))

        elif evento == cv2.EVENT_LBUTTONUP:
            if self.inicio_arrasto:
                x1, y1 = self.inicio_arrasto
                # Arrasto curto e clique, nao recorte.
                if abs(x - x1) < 4 and abs(y - y1) < 4:
                    self.retangulo = None
                    self.fixado = (x, y)
                    print(f"  ponto: ({x}, {y})")
                else:
                    self.retangulo = self._normalizar(self.inicio_arrasto, (x, y))
                    rx, ry, rw, rh = self.retangulo
                    print(f"  regiao: ({rx}, {ry}, {rx + rw}, {ry + rh})  "
                          f"[{rw}x{rh}]  -- S pra salvar como template")
            self.inicio_arrasto = None

    @staticmethod
    def _normalizar(p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        return (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    # -------------------------------------------------
    # Desenho
    # -------------------------------------------------

    def render(self):
        quadro = self.base.copy()
        altura, largura = quadro.shape[:2]
        x, y = self.cursor

        if self.grade:
            for gx in range(0, largura, 50):
                cv2.line(quadro, (gx, 0), (gx, altura), CINZA, 1)
            for gy in range(0, altura, 50):
                cv2.line(quadro, (0, gy), (largura, gy), CINZA, 1)

        # Mira
        cv2.line(quadro, (x, 0), (x, altura), VERDE, 1)
        cv2.line(quadro, (0, y), (largura, y), VERDE, 1)

        if self.retangulo:
            rx, ry, rw, rh = self.retangulo
            cv2.rectangle(quadro, (rx, ry), (rx + rw, ry + rh), AMARELO, 2)

        if self.fixado:
            cv2.circle(quadro, self.fixado, 5, AMARELO, 2)

        self._desenhar_hud(quadro, x, y)

        if self.lupa:
            self._desenhar_lupa(quadro, x, y)

        return quadro

    def _desenhar_hud(self, quadro, x, y):
        cor = self._cor_em(x, y)
        texto = f"({x}, {y})"
        if cor is not None:
            r, g, b = cor
            texto += f"  RGB({r},{g},{b})  0x{r:02X}{g:02X}{b:02X}"
        if self.retangulo:
            rx, ry, rw, rh = self.retangulo
            texto += f"  |  regiao ({rx},{ry},{rx+rw},{ry+rh}) {rw}x{rh}"

        cv2.rectangle(quadro, (0, 0), (quadro.shape[1], 26), (0, 0, 0), -1)
        cv2.putText(quadro, texto, (8, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    def _cor_em(self, x, y):
        altura, largura = self.base.shape[:2]
        if not (0 <= x < largura and 0 <= y < altura):
            return None
        b, g, r = self.base[y, x][:3]
        return int(r), int(g), int(b)

    def _desenhar_lupa(self, quadro, x, y, radius=20, scale=4):
        """Amplia a vizinhanca do cursor, pra acertar o pixel exato."""
        altura, largura = self.base.shape[:2]
        x1, y1 = max(0, x - radius), max(0, y - radius)
        x2, y2 = min(largura, x + radius), min(altura, y + radius)

        if x2 - x1 < 2 or y2 - y1 < 2:
            return

        recorte = self.base[y1:y2, x1:x2]
        ampliado = cv2.resize(
            recorte, ((x2 - x1) * scale, (y2 - y1) * scale),
            interpolation=cv2.INTER_NEAREST,
        )

        lh, lw = ampliado.shape[:2]
        # Canto oposto ao cursor, pra lupa nao tapar o que se olha.
        px = largura - lw - 10 if x < largura // 2 else 10
        py = 36

        if py + lh > altura or lw > largura:
            return

        quadro[py:py + lh, px:px + lw] = ampliado
        cv2.rectangle(quadro, (px, py), (px + lw, py + lh), AMARELO, 1)
        cv2.line(quadro, (px + lw // 2, py), (px + lw // 2, py + lh), VERDE, 1)
        cv2.line(quadro, (px, py + lh // 2), (px + lw, py + lh // 2), VERDE, 1)

    # -------------------------------------------------
    # Salvar
    # -------------------------------------------------

    def salvar_recorte(self):
        if not self.retangulo:
            print("  [!] arraste um retangulo antes de salvar")
            return

        rx, ry, rw, rh = self.retangulo

        if rw < 4 or rh < 4:
            print("  [!] recorte pequeno demais")
            return

        nome = input("  nome do template (sem .png): ").strip()
        if not nome:
            print("  [!] cancelado")
            return

        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        caminho = os.path.join(TEMPLATES_DIR, f"{nome}.png")

        if os.path.exists(caminho):
            if input(f"  '{nome}.png' ja existe. Sobrescrever? [s/N] ").strip().lower() != "s":
                print("  [!] cancelado")
                return

        cv2.imwrite(caminho, self.base[ry:ry + rh, rx:rx + rw])
        print(f"  [ok] salvo: templates/{nome}.png  ({rw}x{rh})")
        print(f"       regiao de busca sugerida: ({rx}, {ry}, {rx + rw}, {ry + rh})")

    # -------------------------------------------------
    # Laco
    # -------------------------------------------------

    def rodar(self):
        cv2.namedWindow(JANELA, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(JANELA, self.ao_mouse)

        while True:
            cv2.imshow(JANELA, self.render())
            tecla = cv2.waitKey(30) & 0xFF

            if tecla in (27, ord("q"), ord("Q")):
                break
            if tecla in (ord("s"), ord("S")):
                self.salvar_recorte()
            elif tecla in (ord("g"), ord("G")):
                self.grade = not self.grade
            elif tecla in (ord("z"), ord("Z")):
                self.lupa = not self.lupa
            elif tecla in (ord("r"), ord("R")):
                if self.recapturar is None:
                    print("  [!] modo arquivo: nada pra recapturar")
                else:
                    try:
                        self.base = self.recapturar()
                        print("  [ok] recapturado")
                    except Exception as exc:
                        print(f"  [!] falha ao recapturar: {exc}")

            # Fechar pelo X da janela.
            if cv2.getWindowProperty(JANELA, cv2.WND_PROP_VISIBLE) < 1:
                break

        cv2.destroyAllWindows()


def main():
    args = sys.argv[1:]

    if args and args[0] == "--arquivo":
        if len(args) < 2:
            print("Uso: python tools/calibrar.py --arquivo tela.png")
            return 1
        imagem = cv2.imread(args[1], cv2.IMREAD_COLOR)
        if imagem is None:
            print(f"Nao foi possivel ler '{args[1]}'")
            return 1
        print(f"Trabalhando sobre {args[1]} ({imagem.shape[1]}x{imagem.shape[0]})")
        Calibrador(imagem).rodar()
        return 0

    titulo = args[0] if args else config.WINDOW_TITLE
    window = WindowService()

    try:
        window.connect(title_substring=titulo, timeout=10)
    except Exception as exc:
        print(f"Janela '{titulo}' nao encontrada: {exc}")
        print("Dica: use o titulo do personagem, que o bot renomeia a janela.")
        return 1

    def capturar():
        return window.capture()

    imagem = capturar()
    altura, largura = imagem.shape[:2]

    print(f"Conectado em '{titulo}' -- client area {largura}x{altura}")
    if (largura, altura) != (config.TARGET_WIDTH, config.TARGET_HEIGHT):
        print(f"[!] ATENCAO: o roteiro do BC assume "
              f"{config.TARGET_WIDTH}x{config.TARGET_HEIGHT}. "
              f"Coordenadas tiradas nesta resolucao NAO vao servir.")
    print("Mova o mouse sobre a imagem; clique fixa o ponto; arraste recorta.")

    Calibrador(imagem, recapturar=capturar).rodar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
