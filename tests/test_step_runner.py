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
    click_template,
    click_until_target,
    skip_if_color,
    walk_to,
    use_all_items,
    wait_position,
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
    def __init__(self, combina=False, achados=None):
        self.combina = combina
        self.consultas = 0
        # Lista de posições a devolver em chamadas sucessivas de
        # find_template; None significa "não achei mais".
        self.achados = list(achados or [])
        self.buscas = []

    def pixel_matches(self, hwnd, x, y, color, tolerance=10):
        self.consultas += 1
        return self.combina

    def find_template(self, hwnd, template, threshold=0.85, region=None):
        self.buscas.append((template, region))
        if self.achados:
            return self.achados.pop(0)
        return None


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


# ==========================================================
# walk_to -- andar até uma coordenada do mundo pelo minimapa
# ==========================================================
#
# O minimapa é o mundo em escala, centrado no personagem. Medido no
# jogo: ~1 unidade de mundo por pixel, com o y INVERTIDO -- subir no
# minimapa aumenta o y. Laço fechado: relê a posição e reclica, então
# escala aproximada só custa iteração, não destino errado.

class FakeChar:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y


def contexto_char(entrada, char):
    return StepContext(hwnd=1, input_service=entrada, char_info=char)


def test_chegou_no_alvo_nao_clica(entrada):
    char = FakeChar(100, 100)
    runner = StepRunner([walk_to(103, 98, tolerancia=8)])

    rodar_ate_terminar(runner, contexto_char(entrada, char))

    assert entrada.acoes == []


def test_projeta_o_alvo_no_minimapa_com_y_invertido(entrada):
    """Alvo 20 ao norte e 10 a leste: clique acima e à direita do centro."""
    char = FakeChar(1000, -500)
    runner = StepRunner([walk_to(1010, -480, centro=(915, 112), raio=55,
                                 escala=1.0, tolerancia=2, intervalo=0.0)])

    runner.tick(contexto_char(entrada, char))

    assert entrada.acoes == [("right", 925, 92)]


def test_alvo_fora_do_raio_clica_na_borda(entrada):
    """Longe demais pro minimapa: anda o que der na direção certa."""
    char = FakeChar(0, 0)
    runner = StepRunner([walk_to(1000, 0, centro=(915, 112), raio=55,
                                 escala=1.0, tolerancia=2, intervalo=0.0)])

    runner.tick(contexto_char(entrada, char))

    (_, x, y), = entrada.acoes
    assert (x, y) == (915 + 55, 112), "devia parar na borda, não fora do minimapa"


def test_parede_no_caminho_faz_o_clique_desviar(entrada):
    """
    Medido no jogo: um clique reto pode mover ZERO por causa de parede.
    Repetir o mesmo clique daria no mesmo, então o seguinte sai torto.
    """
    char = FakeChar(1000, -500)
    runner = StepRunner([walk_to(1000, -400, centro=(915, 112), raio=55,
                                 escala=1.0, tolerancia=2, intervalo=0.0)])
    ctx = contexto_char(entrada, char)

    runner.tick(ctx)   # primeiro clique, reto
    runner.tick(ctx)   # personagem não saiu do lugar -> desvia

    assert len(entrada.acoes) == 2
    assert entrada.acoes[0] != entrada.acoes[1]


def test_desiste_no_timeout(entrada):
    char = FakeChar(0, 0)
    runner = StepRunner([walk_to(999, 999, tolerancia=2, intervalo=0.0,
                                 timeout=0.05)])
    ctx = contexto_char(entrada, char)

    runner.tick(ctx)
    time.sleep(0.06)
    runner.tick(ctx)

    assert runner.finished


def test_sem_leitura_de_posicao_nao_trava_o_roteiro(entrada):
    runner = StepRunner([walk_to(10, 10)])

    rodar_ate_terminar(runner, StepContext(hwnd=1, input_service=entrada))

    assert entrada.acoes == []


# ==========================================================
# click_until_target -- selecionar NPC pelo nome lido da memória
# ==========================================================
#
# Confirmar a seleção pela memória e não por imagem é o ponto: o NPC
# tem animação idle e o cenário muda de um ponto pro outro, então
# template matching nele oscila. O nome do alvo, não.

def test_para_assim_que_o_alvo_certo_esta_selecionado(entrada):
    runner = StepRunner([click_until_target(400, 300, "Skull Herald")])
    ctx = contexto(entrada, target=FakeTarget(name="Skull Herald"))

    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [], "já estava selecionado, não precisava clicar"


def test_clica_ate_o_alvo_certo_aparecer(entrada):
    alvo = FakeTarget(name="")
    runner = StepRunner([click_until_target(400, 300, "Skull Herald",
                                            intervalo=0.0)])
    ctx = contexto(entrada, target=alvo)

    runner.tick(ctx)
    runner.tick(ctx)
    assert not runner.finished, "sem o alvo certo, não pode seguir"

    alvo.name = "Skull Herald"
    runner.tick(ctx)

    assert runner.finished
    assert entrada.acoes == [("left", 400, 300), ("left", 400, 300)]


def test_alvo_errado_nao_conta(entrada):
    """Clicou e pegou o mob ao lado -- continua tentando."""
    runner = StepRunner([click_until_target(400, 300, "Skull Herald",
                                            intervalo=0.0)])
    ctx = contexto(entrada, target=FakeTarget(name="Gun Witch"))

    runner.tick(ctx)

    assert not runner.finished


def test_nome_do_alvo_ignora_maiusculas_e_espacos(entrada):
    runner = StepRunner([click_until_target(400, 300, "skull herald")])
    ctx = contexto(entrada, target=FakeTarget(name="  Skull Herald  "))

    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == []


def test_desiste_no_timeout_em_vez_de_travar_o_ciclo(entrada):
    """Preso aqui pra sempre é pior que seguir e falhar visivelmente."""
    runner = StepRunner([click_until_target(400, 300, "Skull Herald",
                                            timeout=0.05, intervalo=0.0)])
    ctx = contexto(entrada, target=FakeTarget(name=""))

    runner.tick(ctx)
    time.sleep(0.06)
    runner.tick(ctx)

    assert runner.finished


# ==========================================================
# use_all_items -- as bags de courage
# ==========================================================

def test_usa_todas_as_bags_encontradas(entrada):
    """
    Não se sabe quantas bags o boss dropou; 'não achei mais' é a
    condição de parada. Contar repetições fixas erraria pros dois lados.
    """
    vision = FakeVision(achados=[(100, 200), (110, 200), (120, 200)])
    runner = StepRunner([use_all_items("courage_bag", intervalo=0.0)])
    ctx = contexto(entrada, vision=vision)
    rodar_ate_terminar(runner, ctx)

    usos = [a for a in entrada.acoes if a[0] == "double_right"]
    assert usos == [
        ("double_right", 100, 200),
        ("double_right", 110, 200),
        ("double_right", 120, 200),
    ]


def test_sem_bag_nenhuma_termina_sem_agir(entrada):
    vision = FakeVision(achados=[])
    runner = StepRunner([use_all_items("courage_bag", intervalo=0.0), left(1, 1)])
    ctx = contexto(entrada, vision=vision)
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 1, 1)]


def test_respeita_o_limite_maximo(entrada):
    """Template que casa sempre não pode gerar laço infinito."""
    vision = FakeVision(achados=[(1, 1)] * 500)
    runner = StepRunner([use_all_items("courage_bag", maximo=5, intervalo=0.0)])
    ctx = contexto(entrada, vision=vision)
    rodar_ate_terminar(runner, ctx)

    assert len([a for a in entrada.acoes if a[0] == "double_right"]) == 5


def test_repassa_a_regiao_de_busca(entrada):
    """
    Limitar ao inventário evita casar com algo parecido em outro canto
    da tela.
    """
    vision = FakeVision(achados=[])
    regiao = (10, 20, 300, 400)
    runner = StepRunner([use_all_items("courage_bag", region=regiao, intervalo=0.0)])
    ctx = contexto(entrada, vision=vision)
    rodar_ate_terminar(runner, ctx)

    assert vision.buscas == [("courage_bag", regiao)]


def test_use_all_items_sem_vision_service_pula(entrada):
    runner = StepRunner([use_all_items("courage_bag"), left(1, 1)])
    ctx = contexto(entrada, vision=None)
    rodar_ate_terminar(runner, ctx)
    assert entrada.acoes == [("left", 1, 1)]


def test_progress_reporta_a_posicao(entrada):
    runner = StepRunner([left(1, 1), left(2, 2)])
    ctx = contexto(entrada)
    assert runner.progress == "0/2"
    runner.tick(ctx)
    assert runner.progress == "1/2"


# ==========================================================
# click_template e wait_position
# ==========================================================
#
# Usados na saída da cave pela Skull Herald: a caixa de diálogo do NPC
# não aparece sempre no mesmo lugar, então clicar às cegas erraria.

def test_click_template_clica_onde_achou(entrada):
    vision = FakeVision(achados=[(300, 200)])
    runner = StepRunner([click_template("leave_bc")])
    ctx = contexto(entrada, vision=vision)
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 300, 200)]


def test_click_template_respeita_o_botao_pedido(entrada):
    vision = FakeVision(achados=[(50, 60)])
    runner = StepRunner([click_template("skull_herald", botao="double_right")])
    ctx = contexto(entrada, vision=vision)
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("double_right", 50, 60)]


def test_click_template_espera_o_elemento_aparecer(entrada):
    """O diálogo do NPC demora; não pode desistir no primeiro tick."""
    vision = FakeVision(achados=[])
    runner = StepRunner([click_template("leave_bc", timeout=5.0)])
    ctx = contexto(entrada, vision=vision)

    for _ in range(3):
        runner.tick(ctx)

    assert entrada.acoes == []
    assert runner.finished is False

    vision.achados = [(10, 20)]
    runner.tick(ctx)
    assert entrada.acoes == [("left", 10, 20)]


def test_click_template_desiste_no_timeout(entrada):
    vision = FakeVision(achados=[])
    runner = StepRunner([click_template("leave_bc", timeout=0.05), left(9, 9)])
    ctx = contexto(entrada, vision=vision)

    runner.tick(ctx)
    time.sleep(0.06)
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 9, 9)]


def test_wait_position_libera_ao_chegar(entrada):
    class Char:
        x, y = 82, -396

    runner = StepRunner([wait_position(82, -396, tolerancia=5), left(1, 1)])
    ctx = StepContext(hwnd=1, input_service=entrada, char_info=Char())
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 1, 1)]


def test_wait_position_aceita_tolerancia():
    """Coordenada do mundo não bate exata; a tolerância é o que a torna usável."""
    class Char:
        x, y = 85, -399

    entrada = FakeInput()
    runner = StepRunner([wait_position(82, -396, tolerancia=5), left(1, 1)])
    ctx = StepContext(hwnd=1, input_service=entrada, char_info=Char())
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 1, 1)]


def test_wait_position_espera_enquanto_longe(entrada):
    class Char:
        x, y = 500, 500

    runner = StepRunner([wait_position(82, -396, timeout=5.0), left(1, 1)])
    ctx = StepContext(hwnd=1, input_service=entrada, char_info=Char())

    for _ in range(5):
        runner.tick(ctx)

    assert entrada.acoes == []


def test_wait_position_desiste_no_timeout(entrada):
    class Char:
        x, y = 500, 500

    runner = StepRunner([wait_position(82, -396, timeout=0.05), left(9, 9)])
    ctx = StepContext(hwnd=1, input_service=entrada, char_info=Char())

    runner.tick(ctx)
    time.sleep(0.06)
    rodar_ate_terminar(runner, ctx)

    assert entrada.acoes == [("left", 9, 9)]


def test_wait_position_sem_char_info_pula(entrada):
    runner = StepRunner([wait_position(82, -396), left(1, 1)])
    ctx = StepContext(hwnd=1, input_service=entrada, char_info=None)
    rodar_ate_terminar(runner, ctx)
    assert entrada.acoes == [("left", 1, 1)]
