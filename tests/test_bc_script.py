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
from src.services.bot.scripts.bc import DEFAULT_CONFIG, BCScript, BCStats
from src.services.bot.step_runner import StepContext


class FakeChar:
    def __init__(self, hp_pct=100.0, resource_pct=100.0, in_battle=False):
        self.hp_pct = hp_pct
        self.resource_pct = resource_pct
        self.in_battle = in_battle


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
    for chave in ("attack_keys", "aoe_key", "mount_key", "stone_charm_key",
                  "inventory_key", "team_key", "runs_por_ciclo", "rota",
                  "hp_potion_key", "fairy_heal_pct"):
        assert chave in bc.config


def test_tres_ataques_mais_aoe_por_padrao():
    """A referência separa Attack 1/2/3 do Attack AOE."""
    assert len(BCScript().config["attack_keys"]) == 3
    assert BCScript().config["aoe_key"]


def test_config_do_usuario_sobrescreve_o_default():
    bc = BCScript({"mount_key": "5", "attack_keys": ["7", "8"]})
    assert bc.config["mount_key"] == "5"
    assert bc.config["attack_keys"] == ["7", "8"]
    # o que não foi informado continua com o default
    assert bc.config["stone_charm_key"] == DEFAULT_CONFIG["stone_charm_key"]


def test_toda_chave_lida_pelo_roteiro_existe_no_default():
    """
    Trava estrutural: se bc_steps lê cfg["x"] e "x" não está no
    DEFAULT_CONFIG, o roteiro quebra com KeyError só na hora de rodar
    no jogo. Já aconteceu num rename (stone_key -> stone_charm_key).

    Só cobre acesso direto cfg["x"]; cfg.get("x", padrao) é opcional
    por definição.
    """
    import re
    from pathlib import Path

    fonte = Path("src/services/bot/scripts/bc_steps.py").read_text(encoding="utf-8")
    obrigatorias = set(re.findall(r'cfg\["([a-z_]+)"\]', fonte))

    faltando = sorted(c for c in obrigatorias if c not in DEFAULT_CONFIG)
    assert not faltando, f"chaves lidas mas ausentes do DEFAULT_CONFIG: {faltando}"


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
    passos = bc_steps.voltar_para_stone({**DEFAULT_CONFIG, "stone_charm_key": "8"})
    assert passos[0].args == ("8",)


def test_usa_a_tecla_de_team_configurada():
    cfg = {**DEFAULT_CONFIG, "team_key": "F5"}
    assert bc_steps.ajustes_iniciais(cfg)[0].args == ("F5",)
    assert bc_steps.sair_do_team(cfg)[0].args == ("F5",)


def test_ataque_recebe_as_skills_configuradas():
    cfg = {**DEFAULT_CONFIG, "attack_keys": ["a", "b"],
           "break_soul_key": "", "buff_key": ""}
    passos = bc_steps.atacar_boss(cfg)
    skills = passos[0].args[0]
    assert skills == ("a", "b")


def test_break_soul_entra_antes_do_ataque_quando_configurado():
    """Só existe pra quem tem mount de combine máximo, então é opcional."""
    com = bc_steps.atacar_boss({**DEFAULT_CONFIG, "break_soul_key": "B"})
    sem = bc_steps.atacar_boss({**DEFAULT_CONFIG, "break_soul_key": ""})

    assert com[0].kind == "key" and com[0].args == ("B",)
    assert len(com) > len(sem)


def test_segunda_fase_do_boss_adiciona_cura_e_novo_ataque():
    cfg = {**DEFAULT_CONFIG, "heal_antes_segunda_fase": True,
           "healing_spell_key": "H", "break_soul_key": "", "buff_key": ""}
    passos = bc_steps.atacar_boss(cfg)

    ataques = [p for p in passos if p.kind == "attack_until_dead"]
    assert len(ataques) == 2, "as duas fases do boss precisam de dois ataques"
    assert any(p.kind == "key" and p.args == ("H",) for p in passos)


def test_sem_healing_spell_nao_ha_segunda_fase():
    """Ligar a opção sem ter a tecla não pode gerar passo inválido."""
    cfg = {**DEFAULT_CONFIG, "heal_antes_segunda_fase": True,
           "healing_spell_key": "", "break_soul_key": "", "buff_key": ""}
    passos = bc_steps.atacar_boss(cfg)
    assert len([p for p in passos if p.kind == "attack_until_dead"]) == 1


# ==========================================================
# Rota e etapas opcionais
# ==========================================================

def test_rota_standard_nao_mata_gun_witches():
    assert bc_steps.matar_gun_witches({**DEFAULT_CONFIG, "rota": "standard"}) == []


def test_rota_safe_mata_as_gun_witches():
    """Gun Witches são os guardas em frente ao boss."""
    passos = bc_steps.matar_gun_witches({**DEFAULT_CONFIG, "rota": "safe",
                                         "gun_witches": 2})
    assert len([p for p in passos if p.kind == "attack_until_dead"]) == 2


def test_powerfuls_so_com_a_opcao_ligada():
    assert bc_steps.limpar_powerfuls({**DEFAULT_CONFIG, "lure_powerfuls": False}) == []

    passos = bc_steps.limpar_powerfuls({**DEFAULT_CONFIG, "lure_powerfuls": True,
                                        "powerfuls": 4})
    assert len([p for p in passos if p.kind == "attack_until_dead"]) == 4


def test_treasure_box_abre_e_luta_com_o_que_nasce():
    """Depois de aberta, nascem mobs -- o roteiro precisa segui-los."""
    assert bc_steps.abrir_treasure_box({**DEFAULT_CONFIG,
                                        "pegar_treasure_box": False}) == []

    passos = bc_steps.abrir_treasure_box({**DEFAULT_CONFIG,
                                          "pegar_treasure_box": True,
                                          "mobs_do_treasure_box": 3})
    assert passos[0].kind == "right", "a caixa abre com clique direito"
    assert len([p for p in passos if p.kind == "attack_until_dead"]) == 3


def test_manual_pick_so_com_a_opcao_ligada():
    """Só serve pra quem não tem pet com loot automático."""
    assert bc_steps.lotear_boss({**DEFAULT_CONFIG, "manual_pick": False}) == []
    assert bc_steps.lotear_boss({**DEFAULT_CONFIG, "manual_pick": True}) != []


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


# ==========================================================
# Poções e self-heal -- o BC cuida da própria vida
# ==========================================================
#
# Esta é a parte que torna o BC independente: não precisa dos cards
# Potion nem Fairy ligados. E fica FORA do roteiro de passos porque
# precisar de poção acontece a qualquer momento, não num passo
# específico -- se dependesse da vez, o personagem morria esperando.

def _bc_com_pocoes(**extra):
    return BCScript({
        "hp_potion_key": "5", "mana_potion_key": "6",
        "battle_hp_key": "7", "battle_mana_key": "8",
        "healing_spell_key": "H",
        "hp_potion_pct": 90, "mana_potion_pct": 30,
        "battle_hp_pct": 30, "battle_mana_pct": 30,
        "fairy_heal_pct": 50,
        "intervalo_pocao": 0.0,
        **extra,
    })


def test_toma_pocao_de_hp_fora_de_batalha():
    bc = _bc_com_pocoes()
    entrada = FakeInput()

    bc._cuidar_da_vida(1, FakeChar(hp_pct=50.0), entrada)

    assert ("key", "5") in entrada.acoes


def test_nao_toma_pocao_com_vida_cheia():
    bc = _bc_com_pocoes()
    entrada = FakeInput()

    bc._cuidar_da_vida(1, FakeChar(hp_pct=100.0, resource_pct=100.0), entrada)

    assert entrada.acoes == []


def test_em_batalha_usa_a_battle_potion():
    """O jogo exige a versão 'battle' do item durante o combate."""
    bc = _bc_com_pocoes()
    entrada = FakeInput()

    bc._cuidar_da_vida(1, FakeChar(hp_pct=20.0, in_battle=True), entrada)

    assert ("key", "7") in entrada.acoes
    assert ("key", "5") not in entrada.acoes


def test_self_heal_da_fairy_entra_em_batalha():
    """Sem battle pot configurada, o self-heal é a única saída."""
    bc = _bc_com_pocoes(battle_hp_key="", battle_mana_key="")
    entrada = FakeInput()

    bc._cuidar_da_vida(1, FakeChar(hp_pct=40.0, in_battle=True), entrada)

    assert ("key", "H") in entrada.acoes


def test_tecla_unset_e_ignorada():
    """'unset' na referência = sem tecla; o item simplesmente não é usado."""
    bc = _bc_com_pocoes(hp_potion_key="", mana_potion_key="")
    entrada = FakeInput()

    bc._cuidar_da_vida(1, FakeChar(hp_pct=10.0), entrada)

    assert entrada.acoes == []


def test_personagem_morto_nao_gasta_pocao():
    bc = _bc_com_pocoes()
    entrada = FakeInput()

    bc._cuidar_da_vida(1, FakeChar(hp_pct=0.0), entrada)

    assert entrada.acoes == []


def test_intervalo_evita_gastar_a_mochila_num_pico_de_dano():
    bc = _bc_com_pocoes(intervalo_pocao=10.0)
    entrada = FakeInput()
    char = FakeChar(hp_pct=10.0)

    for _ in range(5):
        bc._cuidar_da_vida(1, char, entrada)

    assert len(entrada.acoes) == 1


def test_sem_char_info_nao_quebra():
    assert _bc_com_pocoes()._cuidar_da_vida(1, None, FakeInput()) is False


def test_pocao_tem_prioridade_sobre_o_roteiro():
    """
    Se o personagem está morrendo, poção vem antes do próximo clique da
    sequência.
    """
    bc = _bc_com_pocoes()
    entrada = FakeInput()

    bc.tick(hwnd=1, screenshot=None, char_info=FakeChar(hp_pct=10.0),
            target_info=None, input_service=entrada,
            vision_service=None, window_service=None)

    assert entrada.acoes == [("key", "5")]


# ==========================================================
# Stats
# ==========================================================

def test_stats_comeca_zerado():
    s = BCStats()
    assert (s.runs, s.sucessos, s.falhas, s.courage) == (0, 0, 0, 0)


def test_stats_conta_sucesso_e_falha():
    s = BCStats()
    s.iniciar_run(); s.encerrar_run(sucesso=True)
    s.iniciar_run(); s.encerrar_run(sucesso=False)

    assert s.runs == 2
    assert s.sucessos == 1
    assert s.falhas == 1


def test_stats_acumula_tempo():
    s = BCStats()
    s.iniciar_run()
    s.encerrar_run(sucesso=True)

    assert s.tempo_ultima_run >= 0
    assert s.tempo_total >= s.tempo_ultima_run


def test_stats_zerar():
    s = BCStats()
    s.iniciar_run(); s.encerrar_run(sucesso=True)
    s.courage = 5
    s.zerar()

    assert (s.runs, s.sucessos, s.courage, s.tempo_total) == (0, 0, 0, 0.0)


@pytest.mark.parametrize("segundos,esperado", [
    (0, "0h 0m 0s"),
    (559, "0h 9m 19s"),
    (1359, "0h 22m 39s"),
])
def test_stats_formata_como_a_referencia(segundos, esperado):
    assert BCStats.formatar(segundos) == esperado


def test_stats_formato_longo_inclui_dias():
    assert BCStats.formatar_longo(1919) == "0d 0h 31m 59s"


def test_run_incrementa_os_stats():
    bc = BCScript({"runs_por_ciclo": 2})
    bc._fase = BCScript.FASE_RUN
    bc._proxima_fase()

    assert bc.stats.runs == 1
    assert bc.stats.sucessos == 1


def test_auto_reset_zera_os_stats_ao_religar():
    bc = BCScript({"auto_reset_stats": True})
    bc.stats.runs = 7
    bc.reset()
    assert bc.stats.runs == 0


def test_sem_auto_reset_os_stats_sobrevivem():
    bc = BCScript({"auto_reset_stats": False})
    bc.stats.runs = 7
    bc.reset()
    assert bc.stats.runs == 7


def test_tick_no_fim_do_ciclo_nao_age():
    bc = BCScript()
    bc._fase = BCScript.FASE_FIM
    entrada = FakeInput()

    agiu = bc.tick(hwnd=1, screenshot=None, char_info=None, target_info=None,
                   input_service=entrada, vision_service=None, window_service=None)

    assert agiu is False
    assert entrada.acoes == []


# ==========================================================
# Acessores usados pela aba Stats
# ==========================================================

def test_controller_devolve_engine_existente_sem_criar():
    """
    A GUI lê os contadores pelo engine da sessão. Não pode CRIAR um
    engine só por abrir o diálogo -- isso registraria scripts e mudaria
    o estado da conta sem ninguém ter pedido.
    """
    from src.app.automation_controller import AutomationController

    controller = AutomationController()

    assert controller.get_bot_engine("nao_existe") is None
    assert controller.get_bot_engine(None) is None
    assert controller._bot_engines == {}, "não podia ter criado engine nenhum"


def test_bot_engine_expoe_copia_dos_scripts():
    """
    Quem inspeciona de fora não pode alterar o registro sem passar por
    register/unregister.
    """
    from src.services.bot.bot_engine import BotEngine

    engine = BotEngine()
    script = BCScript()
    engine.register(script)

    exposta = engine.scripts
    assert script in exposta

    exposta.clear()
    assert script in engine.scripts, "a lista interna foi alterada de fora"
