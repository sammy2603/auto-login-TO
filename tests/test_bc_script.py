"""
Testes do script de BC.

O foco é a máquina de estados do ciclo -- em especial o laço de runs,
que é a parte configurável nova: matar o boss e, em vez de voltar pra
cidade, resetar o team e repetir N vezes.

O roteiro em si (as ~650 coordenadas) não é testado clique a clique;
o que se garante é que as fases montam, encadeiam e usam as teclas
configuradas.
"""

import pytest

from src.services.bot.scripts import bc_steps
from src.services.bot.scripts.bc import DEFAULT_CONFIG, BCScript
from src.services.bot.step_runner import StepContext


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


def teclas_usadas(acoes):
    return [k for tipo, k in ((a[0], a[1]) for a in acoes if a[0].startswith("key"))]


# ==========================================================
# Configuração
# ==========================================================

def test_config_default_completa():
    bc = BCScript()
    for chave in ("skills", "mount_key", "stone_key", "inventory_key",
                  "team_key", "runs_por_ciclo"):
        assert chave in bc.config


def test_quatro_skills_por_padrao():
    assert len(BCScript().config["skills"]) == 4


def test_config_do_usuario_sobrescreve_o_default():
    bc = BCScript({"mount_key": "5", "skills": ["7", "8"]})
    assert bc.config["mount_key"] == "5"
    assert bc.config["skills"] == ["7", "8"]
    # o que não foi informado continua com o default
    assert bc.config["stone_key"] == DEFAULT_CONFIG["stone_key"]


def test_config_none_usa_tudo_default():
    assert BCScript(None).config == DEFAULT_CONFIG


# ==========================================================
# Fases e transições
# ==========================================================

def test_comeca_no_preparo():
    assert BCScript().fase == BCScript.FASE_PREPARO


def test_preparo_vai_para_run():
    bc = BCScript()
    bc._fase = BCScript.FASE_PREPARO
    assert bc._proxima_fase() == BCScript.FASE_RUN


def test_com_uma_run_vai_direto_para_o_retorno():
    """runs_por_ciclo=1 reproduz o macro original: mata e volta."""
    bc = BCScript({"runs_por_ciclo": 1})
    bc._fase = BCScript.FASE_RUN
    assert bc._proxima_fase() == BCScript.FASE_RETORNO


def test_com_varias_runs_reseta_o_team_em_vez_de_voltar():
    """
    O comportamento novo que o usuário pediu: em vez de voltar pra
    cidade, sai, reseta o team e entra de novo.
    """
    bc = BCScript({"runs_por_ciclo": 3})
    bc._fase = BCScript.FASE_RUN

    assert bc._proxima_fase() == BCScript.FASE_RESET
    assert bc.runs_feitas == 1


def test_ultima_run_volta_para_a_cidade():
    bc = BCScript({"runs_por_ciclo": 3})
    bc._runs_feitas = 2
    bc._fase = BCScript.FASE_RUN

    assert bc._proxima_fase() == BCScript.FASE_RETORNO
    assert bc.runs_feitas == 3


def test_reset_volta_para_run():
    bc = BCScript({"runs_por_ciclo": 3})
    bc._fase = BCScript.FASE_RESET
    assert bc._proxima_fase() == BCScript.FASE_RUN


def test_retorno_encerra_quando_nao_repete():
    bc = BCScript({"repetir_ciclo": False})
    bc._fase = BCScript.FASE_RETORNO
    assert bc._proxima_fase() == BCScript.FASE_FIM


def test_retorno_recomeca_quando_repete_ciclo():
    bc = BCScript({"repetir_ciclo": True, "runs_por_ciclo": 2})
    bc._runs_feitas = 2
    bc._fase = BCScript.FASE_RETORNO

    assert bc._proxima_fase() == BCScript.FASE_PREPARO
    assert bc.runs_feitas == 0, "o contador de runs precisa zerar no novo ciclo"


def test_ciclo_completo_de_tres_runs():
    """Percorre a máquina inteira e confere a sequência de fases."""
    bc = BCScript({"runs_por_ciclo": 3})
    sequencia = [bc.fase]

    for _ in range(10):
        bc._fase = bc._proxima_fase()
        sequencia.append(bc._fase)
        if bc._fase == BCScript.FASE_FIM:
            break

    assert sequencia == [
        "preparo",
        "run", "reset",
        "run", "reset",
        "run",
        "retorno",
        "fim",
    ]


def test_reset_volta_o_script_ao_inicio():
    bc = BCScript({"runs_por_ciclo": 3})
    bc._fase = BCScript.FASE_RUN
    bc._proxima_fase()

    bc.reset()

    assert bc.fase == BCScript.FASE_PREPARO
    assert bc.runs_feitas == 0


# ==========================================================
# Montagem dos roteiros
# ==========================================================

def test_todas_as_fases_montam_passos():
    bc = BCScript()
    for fase, metodo in BCScript._MONTADORES.items():
        passos = getattr(bc, metodo)()
        assert passos, f"fase '{fase}' montou roteiro vazio"


def test_etapas_opcionais_encurtam_o_preparo():
    completo = BCScript({"comprar_pot": True, "vender": True})
    enxuto = BCScript({"comprar_pot": False, "vender": False})

    assert len(enxuto._montar_preparo()) < len(completo._montar_preparo())


def test_desligar_courage_remove_os_passos():
    assert bc_steps.usar_courage({**DEFAULT_CONFIG, "usar_courage": False}) == []
    assert bc_steps.usar_courage(DEFAULT_CONFIG) != []


def test_caminhada_da_cave_tem_as_76_posicoes():
    """
    O macro tem 76 cliques de caminhada (conferido contra o arquivo
    original); perder um significa parar no meio do caminho.
    """
    assert len(bc_steps._CAMINHO_CAVE) == 76

    passos = bc_steps.andar_na_cave(DEFAULT_CONFIG)
    movimentos = [p for p in passos if p.kind == "right"]
    assert len(movimentos) == 76


def test_caminhada_usa_coordenadas_de_minimapa():
    """
    Todas as posições precisam cair no canto superior direito. Uma
    coordenada fora dessa faixa seria clique no chão -- que depende da
    câmera e mandaria o personagem pro lugar errado.
    """
    for x, y in bc_steps._CAMINHO_CAVE:
        assert 850 <= x <= 1000, f"x={x} fora do minimapa"
        assert 50 <= y <= 180, f"y={y} fora do minimapa"


def test_coordenadas_cabem_na_resolucao_alvo():
    """Todo o roteiro assume 1024x768."""
    bc = BCScript()
    for metodo in BCScript._MONTADORES.values():
        for passo in getattr(bc, metodo)():
            if passo.kind in ("left", "right", "double_right"):
                x, y = passo.args
                assert 0 <= x < 1024, f"{passo.kind} x={x} fora da tela"
                assert 0 <= y < 768, f"{passo.kind} y={y} fora da tela"


# ==========================================================
# As teclas configuradas chegam no jogo
# ==========================================================

def test_usa_a_tecla_de_mount_configurada():
    passos = bc_steps.montar({**DEFAULT_CONFIG, "mount_key": "7"})
    assert passos[0].args == ("7",)


def test_usa_a_tecla_de_stone_configurada():
    passos = bc_steps.voltar_para_stone({**DEFAULT_CONFIG, "stone_key": "8"})
    assert passos[0].args == ("8",)


def test_usa_a_tecla_de_team_configurada():
    cfg = {**DEFAULT_CONFIG, "team_key": "F5"}
    assert bc_steps.ajustes_iniciais(cfg)[0].args == ("F5",)
    assert bc_steps.sair_do_team(cfg)[0].args == ("F5",)


def test_ataque_recebe_as_skills_configuradas():
    passos = bc_steps.atacar_boss({**DEFAULT_CONFIG, "skills": ["a", "b"]})
    skills, _intervalo = passos[0].args
    assert skills == ("a", "b")


def test_team_key_e_segurada_e_solta():
    """
    Segurar sem soltar deixaria o painel de team travado. O preparo
    segura; a saída do team solta.
    """
    cfg = DEFAULT_CONFIG
    assert bc_steps.ajustes_iniciais(cfg)[0].kind == "key_down"
    assert bc_steps.sair_do_team(cfg)[0].kind == "key_up"


# ==========================================================
# tick()
# ==========================================================

def test_tick_avanca_o_roteiro():
    bc = BCScript()
    entrada = FakeInput()

    for _ in range(3):
        bc.tick(hwnd=1, screenshot=None, char_info=None, target_info=None,
                input_service=entrada, vision_service=None, window_service=None)

    assert entrada.acoes, "o tick não executou nenhum passo"


def test_tick_nao_bloqueia():
    """
    O roteiro tem minutos de espera declarada. Se o tick dormisse, a
    Potion não rodaria e o personagem morreria no boss.
    """
    import time

    bc = BCScript()
    entrada = FakeInput()

    inicio = time.time()
    for _ in range(50):
        bc.tick(hwnd=1, screenshot=None, char_info=None, target_info=None,
                input_service=entrada, vision_service=None, window_service=None)

    assert time.time() - inicio < 2.0, "o tick bloqueou"


def test_tick_no_fim_do_ciclo_nao_age():
    bc = BCScript()
    bc._fase = BCScript.FASE_FIM
    entrada = FakeInput()

    agiu = bc.tick(hwnd=1, screenshot=None, char_info=None, target_info=None,
                   input_service=entrada, vision_service=None, window_service=None)

    assert agiu is False
    assert entrada.acoes == []
