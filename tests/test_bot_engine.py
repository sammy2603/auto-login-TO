"""
Testes do BotEngine.

O foco é o gating de scripts: decidir QUAIS scripts rodam a partir das
flags vindas dos switches da GUI. Um default errado aqui fez todo
script rodar com o card desligado -- inclusive o Attack, que ataca de
verdade dentro do jogo. É a lógica mais barata de testar e a de maior
consequência quando quebra.
"""

import time

import pytest

from src.services.bot.bot_engine import BotEngine

from conftest import Flag, SpyScript


def wait_until(predicate, timeout: float = 3.0) -> bool:
    """Espera 'predicate' virar verdadeiro. True se virou, False se estourou."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


class FakeMemoryReader:
    """
    HP/mana diferentes de zero de propósito: com ambos zerados o loop
    cai no fallback de leitura por pixels (captura de tela), que não faz
    sentido num teste sem janela de jogo.
    """

    hp_pct = 80.0
    mana_pct = 60.0
    in_battle = False
    pet_alive = True
    x = 100
    y = 200
    target_hp_pct = 50.0
    target_name = "Mob"


@pytest.fixture
def running_engine():
    """Entrega um engine já parado no teardown, mesmo se o teste falhar."""
    engine = BotEngine()
    yield engine
    engine.stop()


# ==========================================================
# Gating -- regressão do bug do "Start roda script desligado"
# ==========================================================

def test_script_sem_flag_registrada_nao_roda():
    """
    Regressão: a ausência de flag significa DESLIGADO.

    O bug original tratava 'sem flag registrada' como ligado, e como a
    GUI nunca chegava a registrar as flags, TODO script rodava ao
    clicar em Start.
    """
    assert BotEngine.is_script_enabled("Attack", {}) is False


def test_script_com_flag_desligada_nao_roda():
    assert BotEngine.is_script_enabled("Attack", {"Attack": Flag(False)}) is False


def test_script_com_flag_ligada_roda():
    assert BotEngine.is_script_enabled("Attack", {"Attack": Flag(True)}) is True


def test_flag_de_outro_script_nao_habilita():
    """Ligar Potion não pode ligar Attack junto."""
    feature_enabled = {"Potion": Flag(True)}
    assert BotEngine.is_script_enabled("Attack", feature_enabled) is False
    assert BotEngine.is_script_enabled("Potion", feature_enabled) is True


def test_flag_none_explicita_nao_roda():
    """Um valor None registrado na chave não pode ser confundido com ligado."""
    assert BotEngine.is_script_enabled("Attack", {"Attack": None}) is False


# ==========================================================
# Loop
# ==========================================================

def test_loop_executa_somente_scripts_ligados(running_engine):
    """
    Teste de integração do gating: com Attack desligado e Potion
    ligado, só Potion pode ser executado pelo loop.
    """
    attack = SpyScript("Attack")
    potion = SpyScript("Potion")
    running_engine.register(attack)
    running_engine.register(potion)

    running_engine.start(
        hwnd=1234,
        input_service=object(),
        vision_service=object(),
        window_service=object(),
        game_reader=object(),
        memory_reader=FakeMemoryReader(),
        feature_enabled={"Attack": Flag(False), "Potion": Flag(True)},
    )

    # Espera duas voltas do loop: se o Attack fosse rodar, já teria rodado.
    assert wait_until(lambda: potion.ticks >= 2), "o loop não executou o script ligado"
    assert attack.ticks == 0, "script desligado foi executado"


def test_loop_nao_executa_nada_sem_flags(running_engine):
    """Sem nenhuma flag, nenhum script roda -- mas o engine segue vivo."""
    attack = SpyScript("Attack")
    running_engine.register(attack)

    running_engine.start(
        hwnd=1234,
        input_service=object(),
        vision_service=object(),
        window_service=object(),
        game_reader=object(),
        memory_reader=FakeMemoryReader(),
        feature_enabled={},
    )

    time.sleep(1.0)
    assert attack.ticks == 0
    assert running_engine.is_running is True


def test_start_duplicado_nao_cria_segundo_loop(running_engine):
    """Chamar start() com o engine já rodando é no-op, não abre outra thread."""
    args = dict(
        hwnd=1234,
        input_service=object(),
        vision_service=object(),
        window_service=object(),
        game_reader=object(),
        memory_reader=FakeMemoryReader(),
        feature_enabled={},
    )
    running_engine.start(**args)
    first_thread = running_engine._thread

    running_engine.start(**args)
    assert running_engine._thread is first_thread


def test_stop_encerra_o_loop(running_engine):
    running_engine.register(SpyScript("Attack"))
    running_engine.start(
        hwnd=1234,
        input_service=object(),
        vision_service=object(),
        window_service=object(),
        game_reader=object(),
        memory_reader=FakeMemoryReader(),
        feature_enabled={"Attack": Flag(True)},
    )
    assert running_engine.is_running is True

    running_engine.stop()
    assert running_engine.is_running is False
    running_engine._thread.join(timeout=3.0)
    assert running_engine._thread.is_alive() is False


def test_excecao_num_script_nao_derruba_os_outros(running_engine):
    """Um script quebrado não pode matar o loop nem os scripts seguintes."""

    class BrokenScript:
        name = "Attack"

        def tick(self, **kwargs):
            raise RuntimeError("boom")

    potion = SpyScript("Potion")
    running_engine.register(BrokenScript())
    running_engine.register(potion)

    running_engine.start(
        hwnd=1234,
        input_service=object(),
        vision_service=object(),
        window_service=object(),
        game_reader=object(),
        memory_reader=FakeMemoryReader(),
        feature_enabled={"Attack": Flag(True), "Potion": Flag(True)},
    )

    assert wait_until(lambda: potion.ticks >= 2)
    assert running_engine.is_running is True


# ==========================================================
# Registro de scripts
# ==========================================================

def test_register_e_unregister():
    engine = BotEngine()
    script = SpyScript("Attack")

    engine.register(script)
    assert script in engine._scripts

    engine.unregister(script)
    assert script not in engine._scripts


def test_unregister_de_script_ausente_nao_quebra():
    engine = BotEngine()
    engine.unregister(SpyScript("Attack"))  # não deve levantar
