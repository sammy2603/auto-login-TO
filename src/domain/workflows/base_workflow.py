from src.domain.workflows.base_workflow import BaseWorkflow

import config

from vision import wait_for_template, locate_template_in_window
from input_utils import click_at, type_text, clear_field

def log(msg: str):
    print(f"[BOT] {msg}")

class LoginWorkflow(BaseWorkflow):

    def execute(self, hwnd):
        self.do_login(hwnd)
        self.select_server(hwnd)
        self.wait_enter_game(hwnd)
    
    def do_login(hwnd):
        log("Aguardando tela de login...")
        pos = wait_for_template(hwnd, "campo_usuario.png", config.TEMPLATES_DIR,
                             threshold=config.MATCH_THRESHOLD,
                             timeout=config.TIMEOUT_LOGIN_SCREEN)
        if not pos:
            raise TimeoutError("Tela de login não apareceu a tempo (campo_usuario.png não encontrado).")

        x, y = pos
        log(f"Campo de usuário encontrado em ({x}, {y})")
        clear_field(hwnd, x, y)
        type_text(hwnd, config.USERNAME)

        pos_senha = locate_template_in_window(hwnd, "campo_senha.png", config.TEMPLATES_DIR,
                                            threshold=config.MATCH_THRESHOLD)
        if not pos_senha:
            raise RuntimeError("Campo de senha não encontrado (campo_senha.png).")
        x, y = pos_senha
        log(f"Campo de senha encontrado em ({x}, {y})")
        clear_field(hwnd, x, y)
        type_text(hwnd, config.PASSWORD)

        pos_botao = locate_template_in_window(hwnd, "botao_entrar.png", config.TEMPLATES_DIR,
                                            threshold=config.MATCH_THRESHOLD)
        if not pos_botao:
            raise RuntimeError("Botão de login não encontrado (botao_entrar.png).")
        log("Clicando em Entrar...")
        click_at(hwnd, *pos_botao)

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