"""
Testes do login e da espera de fila.

As duas regras que importam aqui não são sobre cliques, são sobre
DESISTIR:

- o login não desiste: se a tela de servidores não veio, ESC no que
  estiver na frente e preenche de novo, quantas vezes for preciso;
- a fila não desiste: espera indefinidamente, porque fila de servidor
  dura horas e qualquer timeout transformaria espera normal em erro.

O que sai daqui quebrado é um bot que fica parado numa tela de popup ou
que morre sozinho depois de meia hora de fila.
"""

import contextlib

import pytest

from src.config.settings import Settings
from src.domain.exceptions import ServerConnectionInterrupted
from src.domain.workflows import base_workflow
from src.domain.workflows.character_workflow import CharacterWorkflow
from src.domain.workflows.login_workflow import LoginWorkflow

SERVIDOR = "White Horse"

POSICOES = {
    "campo_usuario": (100, 100),
    "campo_senha": (100, 140),
    "botao_entrar": (100, 200),
    f"servidor_{SERVIDOR}": (300, 300),
    "botao_entrar_jogo": (400, 400),
    "tela_jogo_carregada": (500, 500),
}

TELA_DE_LOGIN = {"campo_usuario", "campo_senha", "botao_entrar"}


class FakeClient:
    """
    Dublê do GameClient: enxerga um conjunto de templates 'visíveis'.

    O teste muda esse conjunto pra simular a troca de tela -- é assim
    que se reproduz "clicou em Entrar e continuamos na mesma tela".
    """

    def __init__(self, visiveis=(), ao_clicar=None):
        self.visiveis = set(visiveis)
        self.ao_clicar = ao_clicar or (lambda cliente, posicao: None)
        self.acoes = []
        self.tentativas = 0
        self.launch_lock = contextlib.nullcontext()

    # --- vision ---

    def find_template(self, template, threshold=None):
        if template not in self.visiveis:
            return None
        return POSICOES[template]

    def wait_template(self, template, timeout=None, threshold=None):
        return self.find_template(template)

    def template_exists(self, template, threshold=None):
        return template in self.visiveis

    # --- input ---

    def click_position(self, posicao):
        self.acoes.append(("click", posicao))
        self.ao_clicar(self, posicao)

    def fill_field(self, posicao, texto):
        self.acoes.append(("fill", texto))

    def clear_field(self, posicao):
        self.acoes.append(("clear",))

    def clear_current_field(self, max_chars=30):
        self.acoes.append(("clear",))

    def write(self, texto):
        self.acoes.append(("write", texto))

    def press_key(self, tecla):
        self.acoes.append(("key", tecla))

    # --- diversos ---

    def rename_window(self, titulo):
        pass

    def wait(self, segundos):
        pass


def settings():
    return Settings(
        username="conta",
        password="senha",
        server_name=SERVIDOR,
        account_label="Bot1",
    )


def entra_na_tentativa(numero: int):
    """
    Devolve um callback que só faz a tela de servidores aparecer no
    N-ésimo clique em Entrar -- as anteriores falham.
    """

    def ao_clicar(cliente, posicao):
        if posicao != POSICOES["botao_entrar"]:
            return
        cliente.tentativas += 1
        if cliente.tentativas >= numero:
            cliente.visiveis.add(f"servidor_{SERVIDOR}")

    return ao_clicar


@pytest.fixture(autouse=True)
def sem_dormir(monkeypatch):
    """
    A espera paciente dorme 3s entre tentativas. Nos testes isso só
    deixaria a suíte lenta -- o que se verifica é quantas voltas o laço
    dá, não quanto tempo cada uma leva.
    """
    monkeypatch.setattr(base_workflow.time, "sleep", lambda _: None)


def cliques_em(acoes, template):
    return [a for a in acoes if a == ("click", POSICOES[template])]


# ==========================================================
# Login -- laço até a tela de servidores
# ==========================================================

def test_login_repete_ate_a_tela_de_servidores_aparecer():
    """Duas tentativas falham, a terceira passa. Não pode desistir."""
    cliente = FakeClient(TELA_DE_LOGIN, ao_clicar=entra_na_tentativa(3))

    LoginWorkflow(cliente, settings()).login_until_server_screen()

    assert cliente.tentativas == 3
    assert len(cliques_em(cliente.acoes, "botao_entrar")) == 3


def test_cada_tentativa_preenche_as_credenciais_de_novo():
    cliente = FakeClient(TELA_DE_LOGIN, ao_clicar=entra_na_tentativa(2))

    LoginWorkflow(cliente, settings()).login_until_server_screen()

    assert cliente.acoes.count(("fill", "conta")) == 2
    assert cliente.acoes.count(("write", "senha")) == 2


def test_tentativa_que_falha_aperta_esc():
    """
    Nenhum template de mensagem de erro: o que estiver na frente sai
    com ESC, seja qual for o popup.
    """
    cliente = FakeClient(TELA_DE_LOGIN, ao_clicar=entra_na_tentativa(2))

    LoginWorkflow(cliente, settings()).login_until_server_screen()

    assert ("key", "ESC") in cliente.acoes


def test_login_de_primeira_nao_aperta_esc():
    cliente = FakeClient(TELA_DE_LOGIN, ao_clicar=entra_na_tentativa(1))

    LoginWorkflow(cliente, settings()).login_until_server_screen()

    assert ("key", "ESC") not in cliente.acoes


def test_senha_e_limpa_antes_de_digitar():
    """
    Numa retentativa a senha anterior ainda está no campo. Sem limpar,
    as duas iriam juntas -- e o campo é mascarado, então ninguém veria.
    """
    cliente = FakeClient(TELA_DE_LOGIN, ao_clicar=entra_na_tentativa(2))

    LoginWorkflow(cliente, settings()).login_until_server_screen()

    for indice, acao in enumerate(cliente.acoes):
        if acao == ("write", "senha"):
            assert ("clear",) in cliente.acoes[:indice], (
                "digitou a senha sem limpar o campo antes"
            )


# ==========================================================
# Fila -- espera indefinida
# ==========================================================

def test_fila_espera_sem_timeout():
    """
    O botão de entrar no jogo só aparece depois de muitas verificações.
    Com timeout, uma fila longa viraria erro; sem ele, é só esperar.
    """
    cliente = FakeClient()
    workflow = CharacterWorkflow(cliente, settings())

    consultas = {"n": 0}
    original = cliente.find_template

    def find_template(template, threshold=None):
        consultas["n"] += 1
        if consultas["n"] >= 40:
            cliente.visiveis.add("botao_entrar_jogo")
        return original(template, threshold=threshold)

    cliente.find_template = find_template

    workflow.wait_character_screen()

    assert workflow.enter_game_button == POSICOES["botao_entrar_jogo"]


def test_volta_para_a_tela_de_login_interrompe_a_espera():
    """
    Esperar pra sempre só vale enquanto ainda dá pra entrar. Se o jogo
    voltou pro login, o servidor caiu -- é caso de refazer o login, não
    de continuar esperando.
    """
    cliente = FakeClient({"campo_usuario"})
    workflow = CharacterWorkflow(cliente, settings())

    with pytest.raises(ServerConnectionInterrupted):
        workflow.wait_character_screen()

    assert ("key", "ESC") in cliente.acoes
