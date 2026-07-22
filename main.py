# -*- coding: utf-8 -*-
"""
Bot de login automático - Talisman Online.

Fluxo:
1. Abre o executável do client.
2. Espera a janela aparecer.
3. Espera a tela de login carregar (via reconhecimento de imagem).
4. Preenche usuário e senha (sem usar o mouse/teclado físico).
5. Clica em Entrar.
6. Espera a tela de seleção de servidor.
7. Clica no servidor configurado.
8. Espera confirmar que entrou no jogo.

Rode com: python main.py
"""

import os
import subprocess
import sys
import time

import config
from window_utils import wait_for_window, get_client_size
from vision import wait_for_template, locate_template_in_window
from input_utils import click_at, type_text, clear_field


def log(msg: str):
    print(f"[BOT] {msg}")


def launch_client():
    log(f"Abrindo client: {config.CLIENT_PATH}")
    # Roda o processo com o diretório de trabalho apontando para a pasta
    # do próprio launcher/client. Necessário porque alguns .bat chamam
    # o executável com caminho relativo (ex: "start client.exe ...").
    client_dir = os.path.dirname(config.CLIENT_PATH)
    subprocess.Popen(f'"{config.CLIENT_PATH}"', cwd=client_dir, shell=True)


def ensure_resolution_warning(hwnd):
    width, height = get_client_size(hwnd)
    if (width, height) != (config.TARGET_WIDTH, config.TARGET_HEIGHT):
        log(f"AVISO: resolução da janela é {width}x{height}, "
            f"esperado {config.TARGET_WIDTH}x{config.TARGET_HEIGHT}. "
            f"Os templates podem não bater corretamente.")


def login(self):

    self.logger.info("Aguardando tela de login...")

    template = self.client.load_template(
        "campo_usuario"
    )

    pos = self.client.wait_template(
        template,
        timeout=self.settings.TIMEOUT_LOGIN_SCREEN,
        threshold=self.settings.MATCH_THRESHOLD,
    )

    if pos is None:
        raise TimeoutError(
            "Tela de login não apareceu."
        )


def select_server(hwnd):
    log("Aguardando tela de seleção de servidor...")
    template_name = f"servidor_{config.SERVER_NAME}.png"
    pos = wait_for_template(hwnd, template_name, config.TEMPLATES_DIR,
                             threshold=config.MATCH_THRESHOLD,
                             timeout=config.TIMEOUT_SERVER_SCREEN)
    if not pos:
        raise TimeoutError(f"Tela/servidor não encontrado a tempo ({template_name}).")
    log(f"Selecionando servidor: {config.SERVER_NAME}")
    click_at(hwnd, *pos)

    # Muitos jogos pedem confirmação extra (botão "Entrar no jogo")
    pos_confirmar = locate_template_in_window(hwnd, "botao_confirmar_servidor.png",
                                               config.TEMPLATES_DIR,
                                               threshold=config.MATCH_THRESHOLD)
    if pos_confirmar:
        log("Confirmando entrada no servidor...")
        click_at(hwnd, *pos_confirmar)


def wait_enter_game(hwnd):
    log("Aguardando confirmação de que entrou no jogo...")
    pos = wait_for_template(hwnd, "tela_jogo_carregada.png", config.TEMPLATES_DIR,
                             threshold=config.MATCH_THRESHOLD,
                             timeout=config.TIMEOUT_ENTER_GAME)
    if not pos:
        raise TimeoutError("Não foi possível confirmar que o jogo carregou.")
    log("Login concluído com sucesso!")


def main():
    if not config.USERNAME or not config.PASSWORD:
        log("ERRO: defina TALISMAN_USER e TALISMAN_PASS como variáveis de ambiente antes de rodar.")
        sys.exit(1)

    launch_client()

    hwnd = wait_for_window(config.WINDOW_TITLE, timeout=config.TIMEOUT_LOGIN_SCREEN)
    if not hwnd:
        log("ERRO: janela do jogo não foi encontrada. Verifique config.WINDOW_TITLE.")
        sys.exit(1)

    ensure_resolution_warning(hwnd)

    try:
        login(hwnd)
        time.sleep(1.5)  # margem para transição de tela
        select_server(hwnd)
        wait_enter_game(hwnd)
    except (TimeoutError, RuntimeError) as e:
        log(f"FALHA: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

    