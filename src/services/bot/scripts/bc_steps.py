# -*- coding: utf-8 -*-
"""
Roteiro do BC (Bewitcher Cave) como DADOS.

Traduzido dos macros antigos. As coordenadas ficam aqui, separadas da
logica, porque sao o que mais envelhece: qualquer patch que mexa na UI
do jogo exige recalibrar, e isso tem que ser editar uma tabela, nao
cacar chamadas de clique no meio do codigo.

TODAS as coordenadas assumem client area de 1024x768 -- e a resolucao
que os macros originais usavam (valores vao de x=15 a x=997, y=52 a
y=714) e a que o Settings.target_width/height ja fixa.

As teclas NAO estao aqui: vem da configuracao do usuario, via o dict
passado em cada funcao. Ver DEFAULT_CONFIG em bc.py.
"""

from __future__ import annotations

from src.services.bot.step_runner import (
    Step,
    attack_until_dead,
    click_template,
    double_right,
    key,
    key_down,
    key_up,
    left,
    repeat,
    retry_until_color,
    right,
    use_all_items,
    wait,
    wait_position,
)

# Cor que o macro usava pra confirmar "entrou na cave" (pixel 945,148).
# 65280 == 0x00FF00 lido como RGB = verde puro; e o unico dos tres
# valores herdados que casa com uma cor obvia. Configuravel mesmo
# assim, porque o formato original nao esta documentado.
COR_DENTRO_DA_CAVE = 0x00FF00
PIXEL_DENTRO_DA_CAVE = (945, 148)


# =====================================================
# Preparo
# =====================================================

def ajustes_iniciais(cfg) -> list[Step]:
    """Abre o painel de team e ajusta a camera."""
    return [
        key_down(cfg["team_key"], note="segura o painel de team aberto"),
        *repeat(3, [left(997, 97, note="zoom/camera")]),
        left(864, 55),
        wait(0.5),
    ]


def convidar_team(cfg) -> list[Step]:
    return [
        left(15, 496, note="abre a lista"),
        wait(0.5),
        left(439, 334, note="convida"),
        wait(0.5),
    ]


def montar(cfg) -> list[Step]:
    return [
        key(cfg["mount_key"], note="monta"),
        wait(3.0),
    ]


def ir_para_ghost(cfg) -> list[Step]:
    """Caminhada ate o ghost -- cliques no minimapa."""
    return [
        double_right(507, 472), double_right(463, 474), double_right(463, 474),
        double_right(479, 482), double_right(457, 467), double_right(516, 478),
        double_right(454, 469), double_right(456, 439),
        wait(0.1),
        left(303, 592, note="confirma"),
        wait(2.0),
    ]


# =====================================================
# Comercio
# =====================================================

def comprar_pot(cfg) -> list[Step]:
    """
    Compra de pocoes: 16 rodadas de 24 cliques no item.

    Vem do macro 'comprar pot', que segura o team_key durante todo o
    processo -- mantido igual.
    """
    rodada = [
        right(481, 387), right(494, 423), right(490, 403),
        right(483, 351), right(495, 393),
        wait(0.5),
        left(300, 398, note="abre a loja"),
        wait(0.5),
        *repeat(cfg["compras_por_rodada"], [left(199, 325, note="compra")]),
        wait(0.5),
        left(190, 713, note="fecha"),
    ]
    return repeat(cfg["rodadas_de_compra"], rodada)


def vender(cfg) -> list[Step]:
    """Ciclo de venda: abre menu, navega ate o NPC, vende."""
    return [
        left(974, 55), wait(1.0),
        left(597, 391), wait(1.0),
        left(378, 328), wait(1.0),
        left(607, 164), wait(5.0),

        double_right(477, 345), double_right(466, 391), double_right(510, 384),
        double_right(481, 427), double_right(488, 330), double_right(513, 373),
        double_right(465, 377), double_right(459, 371), double_right(522, 398),
        wait(1.0),
        left(269, 396, note="abre a loja"),
        wait(1.0),
        *repeat(6, [left(450, 326), left(445, 325)]),
        left(488, 714, note="fecha"),
        wait(0.5),
    ]


# =====================================================
# Ida ate a cave
# =====================================================

def ir_para_cave(cfg) -> list[Step]:
    return [
        left(978, 56), wait(0.5),
        left(594, 415), wait(0.5),
        *repeat(5, [left(359, 273), wait(5.0)]),
        left(407, 537),
        wait(0.5),
    ]


def entrar_na_cave(cfg) -> list[Step]:
    """
    Entrada na cave, com retentativa.

    E o unico ponto dos macros com realimentacao real: o original
    repetia num 'while_not' ate o pixel (945,148) ficar verde. Aqui a
    retentativa tem LIMITE -- o original podia ficar preso pra sempre.
    """
    tentativa = [
        double_right(467, 417), double_right(471, 394), double_right(479, 377),
        double_right(479, 362), double_right(486, 390), double_right(479, 393),
        double_right(508, 405),
        wait(1.0),
        left(266, 366, note="confirma a entrada"),
        wait(10.0),
    ]

    return retry_until_color(
        tentativa,
        *PIXEL_DENTRO_DA_CAVE,
        cfg.get("cor_dentro_da_cave", COR_DENTRO_DA_CAVE),
        vezes=cfg["tentativas_de_entrada"],
    )


def sair_do_team(cfg) -> list[Step]:
    return [
        key_up(cfg["team_key"], note="solta o painel de team"),
        right(50, 52),
        wait(0.5),
        left(104, 94, note="sai do team"),
        wait(0.5),
    ]


# =====================================================
# Dentro da cave
# =====================================================

# As 75 caminhadas do macro. Sao cliques no MINIMAPA (canto superior
# direito -- x entre 861 e 970, y entre 58 e 166), nao no chao, o que e
# uma boa noticia: minimapa nao depende do angulo da camera.
_CAMINHO_CAVE = [
    (874, 105), (883, 78), (871, 98), (883, 74), (908, 76), (885, 79),
    (884, 78), (915, 70), (901, 83), (885, 85), (864, 108), (870, 142),
    (873, 152), (863, 96), (865, 89), (868, 116), (871, 125), (861, 101),
    (868, 130), (877, 152), (880, 159), (894, 163), (914, 164), (887, 165),
    (888, 157), (906, 144), (955, 146), (948, 157), (956, 152), (959, 145),
    (905, 163), (892, 164), (958, 148), (958, 144), (955, 152), (950, 158),
    (940, 161), (964, 122), (970, 110), (964, 92), (938, 63), (905, 78),
    (951, 89), (968, 103), (951, 157), (948, 157), (967, 124), (970, 91),
    (950, 72), (957, 80), (944, 65), (921, 67), (928, 71), (884, 76),
    (883, 75), (874, 84), (869, 115), (861, 117), (884, 111), (923, 68),
    (918, 75), (863, 114), (869, 113), (876, 116), (874, 116), (919, 166),
    (918, 166), (961, 115), (915, 144), (915, 153), (963, 112), (940, 113),
    (964, 113), (917, 58), (888, 116), (895, 116),
]


def andar_na_cave(cfg) -> list[Step]:
    passos: list[Step] = []
    for x, y in _CAMINHO_CAVE:
        passos.append(right(x, y))
        passos.append(wait(cfg["intervalo_caminhada"]))
    return passos


# Sequencia de aproximacao do NPC, repetida na retentativa do macro.
_APROXIMA_NPC = [
    (230, 202), (219, 296), (227, 193), (198, 241), (223, 293),
    (293, 256), (119, 237), (233, 299), (255, 308), (219, 185),
]


def entrar_no_npc(cfg) -> list[Step]:
    return [
        double_right(390, 321),
        *[double_right(x, y) for x, y in _APROXIMA_NPC],
        double_right(387, 331),
        double_right(285, 266),
        wait(1.0),
        double_right(239, 263),
        *[double_right(x, y) for x, y in _APROXIMA_NPC],
        double_right(216, 223),
        double_right(285, 266),
        wait(1.0),
        left(278, 332, note="fala com o NPC"),
        wait(4.0),
    ]


def caminho_boss(cfg) -> list[Step]:
    return [
        left(680, 475),
        wait(2.0),
        right(879, 112),
        wait(1.0),
        *repeat(9, [right(887, 114), wait(1.0)]),
        key(cfg["mount_key"], note="desmonta antes de lutar"),
        wait(0.5),
    ]


def _skills_de_ataque(cfg) -> list[str]:
    """
    Teclas de ataque efetivas.

    O AOE entra na rotacao junto: a condicao de mana ('usar AOE
    enquanto a mana estiver acima de N%') e avaliada pelo runner a cada
    ciclo, nao aqui -- por isso ele vai como skill condicional.
    """
    teclas = [k for k in cfg.get("attack_keys", []) if k]
    return teclas or ["1"]


def limpar_powerfuls(cfg) -> list[Step]:
    """
    Os Powerfuls sao os mobs das duas fileiras do corredor da sala do
    boss -- uma em cada parede.

    So entra no roteiro se 'lure_powerfuls' estiver ligado; do
    contrario o personagem passa direto pelo corredor.
    """
    if not cfg.get("lure_powerfuls"):
        return []

    return repeat(cfg["powerfuls"], [
        attack_until_dead(
            _skills_de_ataque(cfg),
            timeout=cfg["timeout_mob"],
            skill_interval=cfg["intervalo_skill"],
            aoe_key=cfg.get("aoe_key"),
            aoe_ate_mana=cfg.get("aoe_ate_mana"),
            note="Powerful do corredor",
        ),
    ])


def matar_gun_witches(cfg) -> list[Step]:
    """
    Gun Witches sao os guardas em frente ao boss -- a ultima defesa da
    sala.

    So na rota 'safe'. Na 'standard' o personagem vai direto pro boss,
    que e mais rapido e mais arriscado.
    """
    if cfg.get("rota") != "safe":
        return []

    return repeat(cfg["gun_witches"], [
        attack_until_dead(
            _skills_de_ataque(cfg),
            timeout=cfg["timeout_mob"],
            skill_interval=cfg["intervalo_skill"],
            aoe_key=cfg.get("aoe_key"),
            aoe_ate_mana=cfg.get("aoe_ate_mana"),
            note="Gun Witch",
        ),
    ])


def atacar_boss(cfg) -> list[Step]:
    """
    Substitui o 'repeat 130 {tab, 3, wait 1s}' do macro.

    O original batia 130 vezes independentemente do que acontecesse:
    se o boss morresse antes, desperdicava minutos; se demorasse mais,
    desistia no meio. Aqui le a vida do alvo.

    O boss tem DUAS fases. Se 'heal_antes_segunda_fase' estiver ligado,
    cura entre elas antes de seguir.
    """
    passos: list[Step] = []

    # Break Soul reduz a defesa do inimigo. So existe pra quem tem
    # mount de combine maximo (+12), entao e opcional.
    if cfg.get("break_soul_key"):
        passos.append(key(cfg["break_soul_key"], note="Break Soul (debuff de defesa)"))
        passos.append(wait(0.5))

    if cfg.get("buff_key"):
        passos.append(key(cfg["buff_key"], note="buff antes do boss"))
        passos.append(wait(0.5))

    ataque = attack_until_dead(
        _skills_de_ataque(cfg),
        timeout=cfg["timeout_boss"],
        skill_interval=cfg["intervalo_skill"],
        aoe_key=cfg.get("aoe_key"),
        aoe_ate_mana=cfg.get("aoe_ate_mana"),
        super_key=cfg.get("super_skill_key"),
        note="ataca ate o boss cair",
    )

    passos.append(ataque)

    if cfg.get("heal_antes_segunda_fase") and cfg.get("healing_spell_key"):
        passos.append(key(cfg["healing_spell_key"], note="cura antes da segunda fase"))
        passos.append(wait(1.0))
        # A segunda fase e outro alvo/estado: ataca de novo.
        passos.append(ataque)

    return passos


def lotear_boss(cfg) -> list[Step]:
    """
    Manual Pick: clica no corpo do boss pra lotear.

    Serve pra quem nao tem pet com loot automatico. A posicao do corpo
    nao veio de nenhum macro -- precisa de calibracao no jogo.
    """
    if not cfg.get("manual_pick"):
        return []

    return [
        wait(1.0, note="espera o corpo assentar"),
        *repeat(3, [
            right(*cfg["corpo_do_boss_pos"], note="loota o corpo do boss"),
            wait(0.5),
        ]),
    ]


def abrir_treasure_box(cfg) -> list[Step]:
    """
    A Treasure Box fica no limite final da sala do boss: clique direito
    e espera o casting. Depois de aberta, NASCEM MOBS -- por isso o
    roteiro ja segue lutando.

    A posicao da caixa nao veio de nenhum macro; precisa de calibracao.
    """
    if not cfg.get("pegar_treasure_box"):
        return []

    return [
        right(*cfg["treasure_box_pos"], note="abre a Treasure Box"),
        wait(cfg["casting_treasure_box"], note="espera o casting"),
        *repeat(cfg["mobs_do_treasure_box"], [
            attack_until_dead(
                _skills_de_ataque(cfg),
                timeout=cfg["timeout_mob"],
                skill_interval=cfg["intervalo_skill"],
                aoe_key=cfg.get("aoe_key"),
                aoe_ate_mana=cfg.get("aoe_ate_mana"),
                note="mob nascido da Treasure Box",
            ),
        ]),
    ]


def usar_courage(cfg) -> list[Step]:
    """
    Abre o inventario e abre TODAS as bags de courage dropadas.

    O macro procurava por COR (5391624, formato nao documentado) e usava
    UMA vez. Aqui e por template matching, e repete enquanto achar --
    nao se sabe de antemao quantas bags cairam, entao contar repeticoes
    fixas erra pros dois lados.

    Precisa do recorte 'courage_bag.png' em templates/. Sem ele, o
    VisionService avisa uma vez e o passo termina sem fazer nada, em vez
    de derrubar o ciclo.
    """
    if not cfg.get("usar_courage"):
        return []

    return [
        key(cfg["inventory_key"], note="abre o inventario"),
        wait(1.0),
        use_all_items(
            cfg["courage_template"],
            region=cfg.get("inventario_regiao"),
            maximo=cfg["max_courage"],
            note="abre as bags de courage",
        ),
        wait(0.5),
        key(cfg["inventory_key"], note="fecha o inventario"),
        wait(1.0),
    ]


def sair_da_cave(cfg) -> list[Step]:
    """
    Sai da cave pelo NPC que aparece depois do boss (Skull Herald), que
    teleporta de volta pro NPC de entrada.

    E o que viabiliza repetir a run sem passar pela cidade: sair e
    voltar desfaz e refaz o team, e e isso que reseta a cave e devolve
    o boss.

    O item de dialogo e achado por IMAGEM, nao por coordenada fixa: a
    caixa de dialogo do NPC nao aparece sempre no mesmo lugar, e clicar
    as cegas erraria.
    """
    passos: list[Step] = []

    # Se houver coordenada do NPC, confirma a chegada pela posicao lida
    # da memoria em vez de contar segundos.
    npc = cfg.get("npc_saida_pos")
    if npc:
        passos.append(
            wait_position(*npc, tolerancia=cfg.get("tolerancia_posicao", 8),
                          timeout=cfg.get("timeout_chegada", 60.0),
                          note="chega perto da Skull Herald")
        )

    passos += [
        click_template(cfg["template_npc_saida"], botao="double_right",
                       timeout=cfg.get("timeout_npc_saida", 20.0),
                       note="fala com a Skull Herald"),
        wait(1.5, note="abre o dialogo"),
        click_template(cfg["template_leave_bc"],
                       timeout=cfg.get("timeout_npc_saida", 20.0),
                       note="escolhe 'Leave BC'"),
        wait(cfg.get("espera_teleporte", 6.0), note="teleporta"),
    ]

    return passos


def voltar_para_stone(cfg) -> list[Step]:
    return [
        key(cfg["stone_charm_key"], note="volta pra Stone City"),
        wait(4.0),
    ]
