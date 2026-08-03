"""
Testes do motor de passos.

O ponto mais importante: NADA pode bloquear. O BC é uma sequência de
vários minutos rodando no mesmo loop que a Potion — se um passo de
espera dormir a thread, o personagem morre por não tomar poção.
"""

import time

import pytest

from src.services.bot.step_runner import (
    Step,
    StepContext,
    StepRunner,
    attack_until_dead,
    call,
    double_right,
    key,
    key_down,
    key_up,
    left,
    repeat,
    retry_until_color,
    right,
    skip_if_color,
    wait,
    wait_color,
)


class FakeInput:
    def __init__(self):
        self.acoes = []

    def click(self, hwnd, x, y):
        self.acoes.append(("left", x, y))

    def right_click(self, hwnd, x, y):
        self.acoes.append(("right", x, y))

    def double_right_click(self, hwnd, x, y):
        self.acoes.append(("double_right", x, y))

    def press_key(self, hwnd, k):
        self.acoes.append(("key", k))

    def key_down(self, hwnd, k):
        self.acoes.append(("key_down", k))

    def key_up(self, hwnd, k):
        self.acoes.append(("key_up", k))


class FakeVision:
    def __init__(self, combina=False):
        self.combina = combina
        self.consultas = 0

    def pixel_matches(self, hwnd, x, y, color, tolerance=10):
        self.consultas += 1
        return self.combina


class FakeTarget:
    def __init__(self, name="Boss", hp_pct=100.0):
        self.name = name
        self.hp_pct = hp_pct


@pytest.fixture
def entrada():
    return FakeInput()


def contexto(entrada, vision=None, target=None):
    return StepContext(
        hwnd=1, input_service=entrada,
        vision_service=vision, target_info=target,
    )


def rodar_ate_terminar(runner, ctx, limite=500):
    """Roda ticks até o roteiro acabar. Devolve quantos ticks levou."""
    for n in range(limite):
        if runner.finished:
            return n
        runner.tick(ctx)
    raise AssertionError("roteiro não terminou dentro do limite")


# ==========================================================
# Passos básicos
# ==========================================================

def test_executa_um_passo_por_tick(entrada):
    runner = StepRunner([left(1, 2), left(3, 4), left(5, 6)])
    ctx = contexto(entrada)

    runner.tick(ctx)
    assert entrada.acoes == [("left", 1, 2)]

    runner.tick(ctx)
    assert entrada.acoes == [("left", 1, 2), ("left", 3, 4)]


def test_cada_tipo_de_clique_chama_o_metodo_certo(entrada):
    runner = StepRunner([left(1, 1), right(2, 2), double_right(3, 3)])
    ctx = contexto(entrada)
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [
        ("left", 1, 1), ("right", 2, 2), ("double_right", 3, 3),
    ]


def test_teclas(entrada):
    runner = StepRunner([key("3"), key_down("F12"), key_up("F12")])
    ctx = contexto(entrada)
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [
        ("key", "3"), ("key_down", "F12"), ("key_up", "F12"),
    ]


def test_finished_no_fim(entrada):
    runner = StepRunner([left(1, 1)])
    ctx = contexto(entrada)
    assert runner.finished is False
    runner.tick(ctx)
    assert runner.finished is True


def test_tick_apos_terminar_nao_age(entrada):
    runner = StepRunner([left(1, 1)])
    ctx = contexto(entrada)
    runner.tick(ctx)
    assert runner.tick(ctx) is False
    assert len(entrada.acoes) == 1


def test_reset_volta_ao_inicio(entrada):
    runner = StepRunner([left(1, 1), left(2, 2)])
    ctx = contexto(entrada)
    rodar_ate_terminar(runner, ctx)

    runner.reset()
    assert runner.finished is False
    assert runner.index == 0


def test_roteiro_vazio_ja_nasce_terminado(entrada):
    assert StepRunner([]).finished is True


# ==========================================================
# Espera não-bloqueante -- o ponto crítico
# ==========================================================

def test_wait_nao_bloqueia_a_thread(entrada):
    """
    O teste que mais importa: um wait de 10s não pode dormir. Se
    dormisse, este teste levaria 10 segundos.
    """
    runner = StepRunner([wait(10.0), left(1, 1)])
    ctx = contexto(entrada)

    inicio = time.time()
    for _ in range(20):
        runner.tick(ctx)
    decorrido = time.time() - inicio

    assert decorrido < 0.5, "o passo de espera bloqueou a thread"
    assert runner.finished is False
    assert entrada.acoes == []


def test_wait_libera_depois_do_prazo(entrada):
    runner = StepRunner([wait(0.05), left(1, 1)])
    ctx = contexto(entrada)

    runner.tick(ctx)
    assert entrada.acoes == []

    time.sleep(0.06)
    runner.tick(ctx)   # vence a espera
    runner.tick(ctx)   # executa o clique

    assert entrada.acoes == [("left", 1, 1)]


def test_varios_ticks_durante_a_espera_nao_avancam(entrada):
    runner = StepRunner([wait(5.0), left(1, 1)])
    ctx = contexto(entrada)
    for _ in range(10):
        runner.tick(ctx)
    assert runner.index == 0


# ==========================================================
# wait_color -- o "while_not" dos macros
# ==========================================================

def test_wait_color_espera_a_cor_aparecer(entrada):
    vision = FakeVision(combina=False)
    runner = StepRunner([wait_color(945, 148, 65280, timeout=5.0), left(1, 1)])
    ctx = contexto(entrada, vision=vision)

    for _ in range(5):
        runner.tick(ctx)
    assert runner.finished is False
    assert entrada.acoes == []

    vision.combina = True
    runner.tick(ctx)
    runner.tick(ctx)
    assert entrada.acoes == [("left", 1, 1)]


def test_wait_color_desiste_no_timeout_em_vez_de_travar(entrada):
    """
    O macro original ficava preso no while_not pra sempre. Seguir sem a
    confirmação é ruim; travar é pior.
    """
    vision = FakeVision(combina=False)
    runner = StepRunner([wait_color(1, 1, 65280, timeout=0.05), left(9, 9)])
    ctx = contexto(entrada, vision=vision)

    runner.tick(ctx)
    time.sleep(0.06)
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 9, 9)]


def test_wait_color_sem_vision_service_pula(entrada):
    runner = StepRunner([wait_color(1, 1, 65280), left(1, 1)])
    ctx = contexto(entrada, vision=None)
    rodar_ate_terminar(runner, ctx)
    assert entrada.acoes == [("left", 1, 1)]


# ==========================================================
# attack_until_dead -- substitui o "repeat 130"
# ==========================================================

def test_ataca_enquanto_o_alvo_esta_vivo(entrada):
    alvo = FakeTarget(hp_pct=100.0)
    runner = StepRunner([attack_until_dead(["1", "2"], skill_interval=0.0)])
    ctx = contexto(entrada, target=alvo)

    for _ in range(4):
        runner.tick(ctx)

    assert ("key", "TAB") in entrada.acoes
    assert runner.finished is False


def test_para_quando_o_alvo_morre(entrada):
    """
    O macro repetia 130 vezes independentemente. Aqui, morreu o boss,
    o passo termina -- não desperdiça 2 minutos batendo no vazio.
    """
    alvo = FakeTarget(hp_pct=100.0)
    runner = StepRunner([attack_until_dead(["1"], skill_interval=0.0), left(7, 7)])
    ctx = contexto(entrada, target=alvo)

    runner.tick(ctx)
    runner.tick(ctx)

    alvo.hp_pct = 0.0
    rodar_ate_terminar(runner, ctx)

    assert ("left", 7, 7) in entrada.acoes


def test_ataque_respeita_o_timeout(entrada):
    alvo = FakeTarget(hp_pct=100.0)
    runner = StepRunner([
        attack_until_dead(["1"], timeout=0.05, skill_interval=0.0),
        left(7, 7),
    ])
    ctx = contexto(entrada, target=alvo)

    runner.tick(ctx)
    time.sleep(0.06)
    rodar_ate_terminar(runner, ctx)

    assert ("left", 7, 7) in entrada.acoes


def test_ataque_sem_skills_nao_trava(entrada):
    runner = StepRunner([attack_until_dead([], skill_interval=0.0)])
    ctx = contexto(entrada, target=FakeTarget())
    rodar_ate_terminar(runner, ctx)


# ==========================================================
# repeat e call
# ==========================================================

def test_repeat_expande_na_montagem():
    passos = repeat(3, [left(1, 1)])
    assert len(passos) == 3
    assert all(p.kind == "left" for p in passos)


def test_repeat_preserva_a_ordem_do_bloco():
    passos = repeat(2, [left(1, 1), right(2, 2)])
    assert [p.kind for p in passos] == ["left", "right", "left", "right"]


def test_call_delega_ao_script(entrada):
    chamadas = []

    def acao(ctx):
        chamadas.append(ctx)
        return True

    runner = StepRunner([call(acao)])
    ctx = contexto(entrada)
    rodar_ate_terminar(runner, ctx)

    assert len(chamadas) == 1


def test_call_que_devolve_false_repete(entrada):
    estado = {"n": 0}

    def acao(ctx):
        estado["n"] += 1
        return estado["n"] >= 3

    runner = StepRunner([call(acao)])
    ctx = contexto(entrada)
    rodar_ate_terminar(runner, ctx)

    assert estado["n"] == 3


# ==========================================================
# Robustez
# ==========================================================

def test_passo_que_falha_nao_trava_o_roteiro(entrada):
    """
    Um clique que exploda (janela fechou, por exemplo) não pode
    congelar o BC no meio da cave.
    """
    class InputQuebrado(FakeInput):
        def click(self, hwnd, x, y):
            if (x, y) == (2, 2):
                raise RuntimeError("boom")
            super().click(hwnd, x, y)

    quebrado = InputQuebrado()
    runner = StepRunner([left(1, 1), left(2, 2), left(3, 3)])
    ctx = contexto(quebrado)
    rodar_ate_terminar(runner, ctx)

    assert quebrado.acoes == [("left", 1, 1), ("left", 3, 3)]


def test_passo_desconhecido_e_pulado(entrada):
    runner = StepRunner([Step("nao_existe"), left(1, 1)])
    ctx = contexto(entrada)
    rodar_ate_terminar(runner, ctx)
    assert entrada.acoes == [("left", 1, 1)]


def test_skip_if_color_pula_quando_a_cor_esta_la(entrada):
    runner = StepRunner([
        skip_if_color(1, 1, 65280, 2),
        left(1, 1),   # pulado
        left(2, 2),   # pulado
        left(3, 3),
    ])
    ctx = contexto(entrada, vision=FakeVision(combina=True))
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 3, 3)]


def test_skip_if_color_nao_pula_quando_a_cor_falta(entrada):
    runner = StepRunner([
        skip_if_color(1, 1, 65280, 2),
        left(1, 1),
        left(2, 2),
    ])
    ctx = contexto(entrada, vision=FakeVision(combina=False))
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 1, 1), ("left", 2, 2)]


def test_retry_until_color_para_na_primeira_tentativa_que_da_certo(entrada):
    """
    Substitui o 'while_not' do macro de entrar na cave: deu certo na
    primeira, não repete as outras duas.
    """
    runner = StepRunner(retry_until_color([left(5, 5)], 945, 148, 65280, vezes=3))
    ctx = contexto(entrada, vision=FakeVision(combina=True))
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 5, 5)]


def test_retry_until_color_esgota_as_tentativas_se_nunca_der_certo(entrada):
    """Com limite -- o macro original ficava preso pra sempre."""
    runner = StepRunner(retry_until_color([left(5, 5)], 945, 148, 65280, vezes=3))
    ctx = contexto(entrada, vision=FakeVision(combina=False))
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 5, 5)] * 3


def test_progress_reporta_a_posicao(entrada):
    runner = StepRunner([left(1, 1), left(2, 2)])
    ctx = contexto(entrada)
    assert runner.progress == "0/2"
    runner.tick(ctx)
    assert runner.progress == "1/2"
