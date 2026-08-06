"""
Testes do script de BC.

O foco é a máquina de estados do ciclo -- em especial o laço de runs,
que é a parte configurável nova: matar o boss e, em vez de voltar pra
cidade, resetar o team e repetir N vezes.

O roteiro em si (as ~650 coordenadas) não é testado clique a clique;
o que se garante é que as fases montam, encadeiam e usam as teclas
configuradas.
"""

import json

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
                  "inventory_key", "esconder_jogadores_key", "runs_por_ciclo", "rota",
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


def test_reseter_comeca_e_fica_na_propria_fase():
    """
    O reseter não percorre o ciclo: não prepara, não viaja, não luta.
    Fica em laço aceitando o convite até o card ser desligado.
    """
    bc = BCScript({"reseter": True})

    assert bc.fase == BCScript.FASE_RESETER
    assert bc._proxima_fase() == BCScript.FASE_RESETER


def test_reseter_continua_reseter_depois_do_reset():
    """Religar o card não pode jogar o reseter no roteiro do runner."""
    bc = BCScript({"reseter": True})
    bc.reset()

    assert bc.fase == BCScript.FASE_RESETER


def test_roteiro_do_reseter_so_aceita_convite():
    bc = BCScript({"reseter": True})
    passos = bc._montar_reseter()

    assert [p.kind for p in passos] == ["click_template", "wait"]
    assert passos[0].args[0] == "botao_aceitar_team"


def test_convite_ausente_nao_derruba_o_reseter():
    """
    Ficar sem convite é o estado NORMAL -- o reseter passa a run inteira
    esperando. O passo tem que desistir em silêncio, não avisar.
    """
    passos = bc_steps.aceitar_team(DEFAULT_CONFIG)
    obrigatorio = passos[0].args[4]

    assert obrigatorio is False


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


def test_usa_a_tecla_de_esconder_jogadores_configurada():
    cfg = {**DEFAULT_CONFIG, "esconder_jogadores_key": "F5"}
    assert bc_steps.ajustes_iniciais(cfg)[0].args == ("F5",)


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


def test_esconder_jogadores_e_segurada_e_nunca_solta():
    """
    Soltar traz os jogadores de volta, então o roteiro não pode ter
    key_up nenhum. Não prende tecla de verdade: o input vai por
    PostMessage para o hwnd daquele cliente, então "segurar" é só nunca
    postar o WM_KEYUP.
    """
    passos = bc_steps.ajustes_iniciais(DEFAULT_CONFIG)

    assert passos[0].kind == "key_down"
    assert [p for p in bc_steps.sair_do_team(DEFAULT_CONFIG)
            if p.kind == "key_up"] == []


def test_anda_ate_a_coordenada_antes_de_falar_com_o_npc():
    """
    A ordem é o que importa: chegar (coordenada do mundo), endireitar a
    câmera e só então clicar no NPC. Clicar antes de chegar erra sempre.
    """
    for passos, destino in (
        (bc_steps.entrar_na_cave(DEFAULT_CONFIG), DEFAULT_CONFIG["npc_entrada_parada"]),
        (bc_steps.sair_da_cave(DEFAULT_CONFIG), DEFAULT_CONFIG["npc_saida_pos"]),
    ):
        # Duas passadas de caminhada e a conferencia: walk_to desiste no
        # timeout, e seguir para um clique de TELA com o personagem
        # parado longe garante clique no vazio (aconteceu). A segunda
        # passada sai de graca quando a primeira chegou.
        assert [p.kind for p in passos[:5]] == [
            "walk_to", "walk_to", "wait_position", "wait", "camera"]
        assert passos[0].args[:2] == destino
        assert passos[1].args[:2] == destino
        assert passos[2].args[:2] == destino
        # A parada precisa assentar antes do clique: disparado no
        # instante da chegada, o clique sai antes do NPC estar no lugar
        # final da tela.
        assert passos[3].args == (DEFAULT_CONFIG["espera_pos_chegada"],)
        assert passos[4].args == (
            DEFAULT_CONFIG["camera_zoom"],
            DEFAULT_CONFIG["camera_rotacao"],
            DEFAULT_CONFIG["camera_angulo"],
        )


def test_entrada_abre_o_dialogo_no_ponto_calibrado():
    """
    O NPC tem animação idle -- procurá-lo por imagem oscilou de 0.14 a
    0.93 no mesmo lugar. Com posição fixa e câmera resetada ele cai
    sempre no mesmo ponto da tela; o que se procura por imagem é a
    opção do diálogo, que é interface e não anima.
    """
    passos = bc_steps.entrar_na_cave(DEFAULT_CONFIG)

    # Direito SIMPLES: duplo direito seleciona o NPC sem abrir dialogo.
    dialogo = [p for p in passos if p.kind == "right"]
    pontos = DEFAULT_CONFIG["npc_entrada_tela"]
    assert dialogo[0].args == tuple(pontos[0]), "o ponto medido vem primeiro"

    # Cada ponto que sobra e uma tentativa, e entre elas ha um pulo que
    # descarta as restantes assim que o dialogo abrir. Sem isso o
    # roteiro clicaria nos cinco pontos mesmo tendo acertado no
    # primeiro -- e o clique extra cai no dialogo ja aberto.
    esperados = [tuple(ponto) for ponto in pontos]
    tentativas = [tuple(p.args) for p in passos
                  if p.kind == "right" and tuple(p.args) in set(esperados)]

    # A tentativa INTEIRA se repete (cave_entry_attempts), entao os
    # pontos aparecem uma vez por rodada -- basta conferir a primeira.
    assert tentativas[:len(esperados)] == esperados

    pulos = [p for p in passos if p.kind == "skip_if_template"
             and p.args[0] == DEFAULT_CONFIG["template_enter_bc"]]
    assert len(pulos) == (len(pontos) - 1) * DEFAULT_CONFIG["cave_entry_attempts"]

    opcoes = [p for p in passos if p.kind == "click_template"
              and p.args[0] == "enter_bc"]
    assert opcoes, "faltou escolher a opção de entrar"


def test_saida_sem_ponto_calibrado_procura_o_npc_por_imagem():
    """Plano B enquanto o ponto de tela lá dentro não foi medido."""
    passos = bc_steps.sair_da_cave({**DEFAULT_CONFIG, "npc_saida_tela": None})

    templates = [p.args[0] for p in passos if p.kind == "click_template"]
    assert DEFAULT_CONFIG["template_npc_saida"] in templates
    assert DEFAULT_CONFIG["template_leave_bc"] in templates


def test_saida_com_ponto_calibrado_clica_direto():
    passos = bc_steps.sair_da_cave({**DEFAULT_CONFIG, "npc_saida_tela": (500, 400)})

    assert any(p.kind == "right" and p.args == (500, 400) for p in passos)


def test_camera_escreve_os_tres_valores_e_nao_so_o_angulo():
    """
    O botão de view reset do jogo, que era o que o macro clicava,
    devolve o ângulo padrão mas NÃO devolve o zoom -- e os clients
    usados aqui têm o limite de zoom liberado. Com o zoom livre, dois
    clients "resetados" mostram o mesmo NPC em pixels diferentes, e todo
    clique de tela sai deslocado. Por isso os três valores são escritos.
    """
    passo = bc_steps.fixar_camera(DEFAULT_CONFIG)[0]

    assert passo.kind == "camera"
    assert len(passo.args) == 3


def test_rota_do_mapa_espera_parar_entre_um_clique_e_outro():
    """
    Cada trecho do mapa-múndi leva o tempo que levar. Clicar por cima de
    uma caminhada em curso a CANCELA -- então entre dois cliques o que
    segura o roteiro é a coordenada parar de mudar, não um sleep.
    """
    passos = bc_steps.walk_by_world_map(
        {**DEFAULT_CONFIG, "cave_map_clicks": [(100, 200), (300, 400)]},
        [(100, 200), (300, 400)],
    )

    tipos = [p.kind for p in passos]

    # abre o mapa, dois cliques com espera, fecha o mapa
    assert tipos[0] == "key" and tipos[-2] == "key"
    assert tipos.count("wait_stopped") == 2
    assert [p.args for p in passos if p.kind == "right"] == [(100, 200), (300, 400)]


def test_sem_rota_gravada_a_ida_pra_cave_e_so_minimapa():
    """
    Enquanto os cliques de mapa não forem gravados, o passo some inteiro
    em vez de virar clique no vazio.
    """
    passos = bc_steps.ir_para_cave(
        {**DEFAULT_CONFIG, "cave_map_clicks": [], "cave_waypoints": []})

    assert [p.kind for p in passos] == ["walk_to"]


def test_leave_team_desligado_nao_faz_nada():
    """
    Quem sai do team é o runner, dentro da cave. Com a opção desligada
    não sobra passo nenhum: antes sobrava o key_up da tecla que o
    preparo segurava, e essa tecla virou um toque só.
    """
    assert bc_steps.sair_do_team({**DEFAULT_CONFIG, "leave_team": False}) == []


def test_leave_team_ligado_desfaz_o_grupo():
    passos = bc_steps.sair_do_team({**DEFAULT_CONFIG, "leave_team": True})
    assert any(p.note == "sai do team" for p in passos)


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


# =====================================================
# pos_npc -- catalogo de NPCs, com o config como reserva
# =====================================================

def catalogo_temp(tmp_path, dados):
    caminho = tmp_path / "npcs.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


def test_pos_npc_usa_o_catalogo_quando_o_mapa_esta_capturado(tmp_path):
    cfg = {
        "npc_entrada_mapa": "White Bear Village",
        "npc_entrada_nome": "Skull Herald",
        "npc_entrada_pos": (0, 0),
        "npcs_catalogo": catalogo_temp(
            tmp_path, {"White Bear Village": {"Skull Herald": [[1395, -636]]}}
        ),
    }

    assert bc_steps.pos_npc(cfg, "npc_entrada") == (1395, -636)


def test_pos_npc_cai_no_literal_quando_o_mapa_nao_foi_capturado(tmp_path):
    """Catalogo faltando nao pode quebrar a run."""
    cfg = {
        "npc_entrada_mapa": "Mapa Nunca Capturado",
        "npc_entrada_nome": "Skull Herald",
        "npc_entrada_pos": (1395, -636),
        "npcs_catalogo": catalogo_temp(tmp_path, {}),
    }

    assert bc_steps.pos_npc(cfg, "npc_entrada") == (1395, -636)


def test_pos_npc_cai_no_literal_sem_mapa_configurado(tmp_path):
    """E o caso do NPC de dentro da cave: nome sim, mapa ainda nao."""
    cfg = {
        "npc_saida_nome": "Skull Herald",
        "npc_saida_pos": (82, -396),
        "npcs_catalogo": catalogo_temp(
            tmp_path, {"White Bear Village": {"Skull Herald": [[1395, -636]]}}
        ),
    }

    assert bc_steps.pos_npc(cfg, "npc_saida") == (82, -396)


def test_config_do_bc_resolve_a_entrada_pelo_catalogo(tmp_path):
    """
    Guarda contra o erro silencioso: mapa/nome no config que nao casam
    com o catalogo passariam despercebidos, porque o literal cobre.
    """
    cfg = dict(DEFAULT_CONFIG)
    # Sem ponto de parada medido: e o caso em que o catalogo responde.
    cfg.pop("npc_entrada_parada")
    cfg["npcs_catalogo"] = catalogo_temp(
        tmp_path,
        {cfg["npc_entrada_mapa"]: {cfg["npc_entrada_nome"]: [[1395, -636]]}},
    )

    assert bc_steps.pos_npc(cfg, "npc_entrada") == (1395, -636)


def test_ponto_de_parada_medido_vence_o_catalogo(tmp_path):
    """
    O catalogo guarda a coordenada DO NPC, lida do painel Surrounding.
    A caminhada precisa de outra coisa: onde o PERSONAGEM para para
    clicar nele. Andar para cima da coordenada do NPC deixou o
    personagem um passo fora e o clique de tela passou ao lado -- foi
    assim que a entrada na cave falhou no jogo.
    """
    cfg = dict(DEFAULT_CONFIG)
    cfg["npcs_catalogo"] = catalogo_temp(
        tmp_path,
        {cfg["npc_entrada_mapa"]: {cfg["npc_entrada_nome"]: [[1395, -636]]}},
    )

    assert bc_steps.pos_npc(cfg, "npc_entrada") == cfg["npc_entrada_parada"]


# =====================================================
# Preparo condicional (pet, cidade, montaria, regeneração)
# =====================================================
#
# O erro clássico aqui é o pular_se contar errado: sobra ou falta um
# passo e o roteiro executa metade do bloco que deveria ter pulado.
# Todo teste abaixo confere a contagem, não só o conteúdo.


class CharFalso:
    def __init__(self, **kw):
        self.hp_pct = kw.get("hp_pct", 100.0)
        self.resource_pct = kw.get("resource_pct", 100.0)
        self.pet_alive = kw.get("pet_alive", True)
        self.location = kw.get("location", "Stone City")
        self.mounted = kw.get("mounted", False)


def salta_o_bloco_inteiro(passos):
    """O primeiro passo tem que pular exatamente o resto do bloco."""
    return passos[0].kind == "skip_if" and passos[0].args[1] == len(passos) - 1


def test_garantir_pet_pula_o_bloco_inteiro_quando_tem_pet():
    passos = bc_steps.garantir_pet(DEFAULT_CONFIG)

    assert salta_o_bloco_inteiro(passos)
    assert passos[0].args[0](CharFalso(pet_alive=True)) is True
    assert passos[0].args[0](CharFalso(pet_alive=False)) is False
    assert passos[1].args == (DEFAULT_CONFIG["summon_pet_key"],)


def test_garantir_cidade_so_usa_o_charm_fora_da_cidade():
    passos = bc_steps.garantir_cidade(DEFAULT_CONFIG)
    condicao = passos[0].args[0]

    assert salta_o_bloco_inteiro(passos)
    assert condicao(CharFalso(location="Stone City")) is True
    assert condicao(CharFalso(location="Ghost Din Woods")) is False
    assert passos[1].args == (DEFAULT_CONFIG["stone_charm_key"],)


def test_qualquer_sub_area_da_cidade_conta_como_estar_la():
    """
    location traz a SUB-ÁREA, não o mapa: White Bear Village e Ghost Din
    Woods são o mesmo mapa. Comparar com um nome único faria o
    personagem no mapa certo, em outro canto, queimar um Return Charm.
    """
    cfg = {**DEFAULT_CONFIG, "areas_da_cidade": ["Stone City", "Praca Leste"]}
    condicao = bc_steps.garantir_cidade(cfg)[0].args[0]

    assert condicao(CharFalso(location="Stone City")) is True
    assert condicao(CharFalso(location="Praca Leste")) is True
    assert condicao(CharFalso(location="Ghost Din Woods")) is False


def test_montar_se_preciso_nao_desmonta_quem_ja_esta_montado():
    """A tecla é toggle: apertar montado desmontaria."""
    passos = bc_steps.montar_se_preciso(DEFAULT_CONFIG)
    condicao = passos[0].args[0]

    assert salta_o_bloco_inteiro(passos)
    assert condicao(CharFalso(mounted=True)) is True
    assert condicao(CharFalso(mounted=False)) is False


def test_espera_de_regeneracao_usa_os_limiares_configurados():
    cfg = {**DEFAULT_CONFIG, "hp_min_para_seguir": 100.0,
           "mana_min_para_seguir": 90.0}
    condicao = bc_steps.esperar_hp_e_mana(cfg)[0].args[0]

    assert condicao(CharFalso(hp_pct=100.0, resource_pct=90.0)) is True
    assert condicao(CharFalso(hp_pct=100.0, resource_pct=89.9)) is False
    assert condicao(CharFalso(hp_pct=99.0, resource_pct=100.0)) is False


def test_sem_sit_key_espera_em_pe():
    """Sem tecla confirmada no jogo, não inventa: espera de pé."""
    passos = bc_steps.esperar_hp_e_mana({**DEFAULT_CONFIG, "sit_key": ""})

    assert [p.kind for p in passos] == ["skip_if", "wait_until"]


def test_com_sit_key_desmonta_senta_e_volta_a_montar():
    cfg = {**DEFAULT_CONFIG, "sit_key": "R"}
    passos = bc_steps.esperar_hp_e_mana(cfg)
    teclas = [p.args[0] for p in passos if p.kind == "key"]

    assert salta_o_bloco_inteiro(passos)
    assert teclas == [cfg["mount_key"], "R", "R", cfg["mount_key"]]
    assert [p.kind for p in passos].count("wait_until") == 1


def test_preparo_segue_a_ordem_do_fluxo():
    """
    Ordem que importa: o Return Charm antes da caminhada (coordenada de
    mundo só vale dentro do mapa certo) e a espera de HP/mana no NPC de
    teleporte, não no de venda.
    """
    bc = BCScript()
    passos = bc._montar_preparo()
    notas = [p.note for p in passos if p.note]

    def antes(a, b):
        pos = lambda alvo: next(i for i, n in enumerate(notas) if alvo in n)
        return pos(a) < pos(b)

    assert antes("escondendo os outros jogadores", "zoom out do minimapa")
    assert antes("zoom out do minimapa", "volta pra Stone City")
    assert antes("volta pra Stone City", f'anda ate {DEFAULT_CONFIG["npc_venda_pos"]}')
    assert antes(f'anda ate {DEFAULT_CONFIG["npc_venda_pos"]}',
                 f'anda ate {DEFAULT_CONFIG["npc_teleporte_pos"]}')
    assert antes(f'anda ate {DEFAULT_CONFIG["npc_teleporte_pos"]}', "espera HP")


# =====================================================
# Venda -- grade, slot protegido e confirmação
# =====================================================

def test_slot_de_venda_calcula_a_grade():
    """Geometria medida: origem (452,292), passo 35x36, 6 colunas."""
    cfg = DEFAULT_CONFIG

    assert bc_steps.slot_de_venda(cfg, 1) == (452, 292)
    assert bc_steps.slot_de_venda(cfg, 2) == (487, 292)
    assert bc_steps.slot_de_venda(cfg, 6) == (627, 292)
    assert bc_steps.slot_de_venda(cfg, 7) == (452, 328)   # quebra de linha
    assert bc_steps.slot_de_venda(cfg, 13) == (452, 364)


def test_slot_zero_ou_negativo_cai_no_primeiro():
    """Config errada não pode virar clique fora da janela."""
    assert bc_steps.slot_de_venda(DEFAULT_CONFIG, 0) == (452, 292)
    assert bc_steps.slot_de_venda(DEFAULT_CONFIG, -5) == (452, 292)


def test_venda_bate_sempre_no_mesmo_slot():
    """
    A grade se reordena a cada venda -- medido: vendido o slot 1, o item
    do slot 2 desce para ele. Andar pela grade pularia itens.
    """
    cfg = {**DEFAULT_CONFIG, "slot_inicial_venda": 5, "max_itens_vendidos": 4}
    alvo = bc_steps.slot_de_venda(cfg, 5)

    cliques = [p.args for p in bc_steps.vender(cfg)
               if p.kind == "left" and p.note.startswith("move")]

    assert cliques == [alvo] * 4


def test_slot_inicial_protege_o_comeco_da_bag():
    """É como o usuário guarda poção de HP e mana."""
    cfg = {**DEFAULT_CONFIG, "slot_inicial_venda": 3}

    cliques = {p.args for p in bc_steps.vender(cfg)
               if p.kind == "left" and p.note.startswith("move")}

    assert cliques == {bc_steps.slot_de_venda(cfg, 3)}
    assert bc_steps.slot_de_venda(cfg, 1) not in cliques
    assert bc_steps.slot_de_venda(cfg, 2) not in cliques


def test_confirmacao_de_item_precioso_nao_e_obrigatoria():
    """
    Item comum não abre caixa nenhuma. Marcar o clique como obrigatório
    encheria o log de falha a cada item comum vendido.
    """
    passos = [p for p in bc_steps.vender(DEFAULT_CONFIG)
              if p.kind == "click_template"
              and p.args[0] == DEFAULT_CONFIG["template_ok_venda"]]

    assert passos
    assert all(p.args[4] is False for p in passos)


def test_abrir_dialogo_desiste_quando_o_dialogo_ja_apareceu():
    """
    O nome flutuante do NPC de venda não casa como template, então a
    prova de que o clique acertou é o próprio diálogo.
    """
    cfg = {**DEFAULT_CONFIG, "pontos_do_npc": [(1, 2), (3, 4), (5, 6)]}
    passos = bc_steps.abrir_dialogo_npc(cfg, "opcao_sell_item")
    pulos = [p for p in passos if p.kind == "skip_if_template"]

    # um pulo por tentativa, menos a última (não há o que pular depois)
    assert len(pulos) == 2
    # O pulo tem que parar EXATAMENTE no fim do bloco. A versão anterior
    # pulava um a mais e engolia o primeiro passo de quem chamou -- na
    # venda, o clique em 'Sell Item'.
    assert pulos[0].args[1] == len(passos) - passos.index(pulos[0]) - 1
    assert pulos[1].args[1] == len(passos) - passos.index(pulos[1]) - 1


def test_pulo_do_dialogo_nao_engole_o_passo_seguinte():
    """
    Regressão: o bloco de abrir o diálogo é concatenado com o que vem
    depois. Pular um passo a mais come o primeiro passo de quem chamou,
    e o sintoma aparece longe da causa -- o diálogo abria e a janela de
    venda nunca aparecia, sem erro nenhum.
    """
    cfg = {**DEFAULT_CONFIG, "pontos_do_npc": [(1, 2), (3, 4)]}
    abertura = bc_steps.abrir_dialogo_npc(cfg, "opcao_sell_item")
    sentinela = bc_steps.wait(9.99, note="passo de quem chamou")
    roteiro = abertura + [sentinela]

    for pulo in (p for p in abertura if p.kind == "skip_if_template"):
        destino = roteiro.index(pulo) + pulo.args[1] + 1
        assert roteiro[destino] is sentinela


def test_venda_efetiva_antes_de_fechar_a_janela():
    """
    Regressão cara: o duplo-clique só MOVE o item para a cesta. Sem o
    clique no botão que efetiva, o passo de fechar desfaz tudo e devolve
    os itens para a bag -- e o sintoma era "não vendeu", sem erro nenhum.
    """
    passos = bc_steps.vender(DEFAULT_CONFIG)
    kinds = [(p.kind, p.args[0] if p.args else None) for p in passos]

    efetiva = kinds.index(("click_template", DEFAULT_CONFIG["template_confirmar_venda"]))
    fecha = kinds.index(("click_template", DEFAULT_CONFIG["template_fechar_venda"]))

    assert efetiva < fecha, "efetivar tem que vir antes de fechar"
    assert passos[efetiva].args[4] is True, "efetivar a venda é obrigatório"


def test_ida_pra_cave_percorre_os_waypoints_e_fecha_no_npc():
    """
    Um walk_to único pro NPC tenta cortar reto e para na parede -- a rota
    real contorna pelo leste (x chega a 1415) antes de descer. Os
    waypoints trazem o desvio embutido, porque foram CAMINHADOS e não
    calculados. O último passo é o único com tolerância apertada: é a
    posição exata dele que faz o NPC cair sempre no mesmo pixel da tela.
    """
    passos = bc_steps.ir_para_cave(DEFAULT_CONFIG)

    assert all(p.kind == "walk_to" for p in passos)
    assert len(passos) == len(DEFAULT_CONFIG["cave_waypoints"]) + 1

    destinos = [p.args[:2] for p in passos]
    assert destinos[:-1] == DEFAULT_CONFIG["cave_waypoints"]
    assert destinos[-1] == DEFAULT_CONFIG["npc_entrada_parada"]

    # índice 6 é a tolerância (ver a tupla montada em walk_to)
    assert passos[0].args[6] == DEFAULT_CONFIG["waypoint_tolerance"]
    assert passos[-1].args[6] == DEFAULT_CONFIG["tolerancia_posicao"]


def test_entrada_insiste_o_bastante_pra_instancia_cheia():
    """
    Medido no bot de referência: com a instância lotada ele repetiu o
    diálogo por 62 s sem entrar. Com 3 tentativas o roteiro desistia em
    segundos e seguia como se estivesse dentro -- o resto da run
    acontecia do lado de fora da cave.
    """
    passos = bc_steps.entrar_na_cave(DEFAULT_CONFIG)

    # Cada tentativa que sobra é seguida de um skip que descarta as
    # restantes assim que o pixel confirmar que entrou.
    skips = [p for p in passos if p.kind == "skip_if_color"]

    assert DEFAULT_CONFIG["cave_entry_attempts"] >= 20
    assert len(skips) == DEFAULT_CONFIG["cave_entry_attempts"] - 1
