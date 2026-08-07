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

from src.services.game import npcs
from src.services.bot.step_runner import (
    Step,
    attack_until_dead,
    camera,
    click_template,
    double_right,
    esperar_parado,
    key,
    key_down,
    pular_se,
    pular_se_template,
    esperar_template,
    esperar_ate,
    left,
    repeat,
    retry_until,
    right,
    use_all_items,
    wait,
    wait_position,
    walk_to,
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
    """
    Esconde os outros jogadores e ajusta a camera.

    A tecla (F12 por padrao) some com os PERSONAGENS da tela, deixando
    so os NPCs. E o que faz os cliques de chao e a busca por template
    pararem de competir com jogador parado em cima do NPC.

    A tecla precisa ficar SEGURADA: soltar traz os jogadores de volta.
    Por isso key_down sem key_up nenhum no roteiro.

    Segurar aqui nao prende tecla de verdade. O InputService manda
    WM_KEYDOWN por PostMessage para o hwnd daquele cliente
    (infrastructure/input/service.py), entao "segurar" e so nunca
    postar o WM_KEYUP: nada vaza para outros clientes nem para o
    desktop, e varios scripts rodam juntos sem disputar a tecla.

    Jogador humano consegue o mesmo efeito segurando F12 e apertando
    Enter (o chat rouba o foco e o jogo nao ve o release). Aqui esse
    truque nao serve para nada -- e uma volta para enganar teclado
    fisico, e nos simplesmente nao mandamos o release.

    O nome antigo era "painel de team", que nao e o que a tecla faz.
    """
    return [
        key_down(cfg["esconder_jogadores_key"],
                 note="segura escondendo os outros jogadores"),
        *normalizar_zoom_minimapa(cfg),
        # O macro clicava em (864, 55), o botao de reset de camera do
        # jogo. Escrever os tres floats na memoria cobre mais: o botao
        # nao devolve o zoom, e o zoom e o que muda entre clients aqui.
        *fixar_camera(cfg),
        wait(0.5),
    ]


def normalizar_zoom_minimapa(cfg) -> list[Step]:
    """
    Leva o zoom do minimapa sempre ao MESMO nivel, seja qual for o que
    estiver valendo.

    Isto sustenta 'cave_click_route' inteira: um pixel do minimapa e um
    deslocamento relativo, e quanto mundo cabe em cada pixel e
    justamente o zoom. Rota gravada num nivel e executada em outro anda
    a distancia errada em cada clique -- o erro nao aparece no primeiro,
    aparece acumulado no fim.

    O metodo e saturar e voltar: clicar o bastante para BATER no extremo
    (dali em diante o clique nao faz nada) e entao voltar um numero fixo
    de cliques. Nao depende de saber onde o zoom estava, que e a
    informacao que nao se tem.

    Medido no jogo: do minimo ao maximo sao 4 cliques, ou seja 5 niveis.
    Por isso a saturacao usa 4 e nao 3 -- com 3, quem comecasse no
    extremo oposto pararia um nivel antes e a volta cairia no nivel
    errado. Clique a mais no extremo e inofensivo; clique a menos nao e.

    Os dois botoes se chamam aqui 'satura' e 'volta', e nao 'zoom in' e
    'zoom out', porque para este passo tanto faz qual e qual -- so
    precisam ser OPOSTOS. Os nomes anteriores nao eram so feios: o
    pixel rotulado 'zoom out' era na verdade o botao de zoom in, e o
    passo dava os seis cliques todos pro mesmo lado.
    """
    satura = cfg.get("minimapa_zoom_satura_pos")
    volta = cfg.get("minimapa_zoom_volta_pos")
    if not satura or not volta:
        return []

    return [
        *repeat(cfg.get("minimapa_zoom_satura_clicks", 4),
                [left(*satura, note="satura o zoom do minimapa num extremo")]),
        *repeat(cfg.get("minimapa_zoom_volta_clicks", 2),
                [left(*volta, note="volta pro nivel de zoom da rota")]),
    ]


def garantir_pet(cfg) -> list[Step]:
    """
    Invoca o pet se ele nao estiver ativo.

    Decide pela memoria (pet_alive), nao por pixel: o icone do pet muda
    de lugar conforme a UI, o booleano nao.
    """
    invocar = [
        key(cfg["summon_pet_key"], note="invoca o pet"),
        wait(cfg.get("espera_pet", 2.0)),
    ]
    return [
        pular_se(lambda ci: bool(ci.pet_alive), len(invocar),
                 note="pet ja esta ativo"),
        *invocar,
    ]


def garantir_cidade(cfg) -> list[Step]:
    """
    Volta para a cidade com o Return Charm, se ja nao estiver la.

    Sem isto o roteiro sairia andando para a coordenada do NPC de venda
    a partir de qualquer mapa -- e coordenada de mundo de um mapa nao
    quer dizer nada em outro.
    """
    # LISTA de sub-areas, e nao um nome so: o que a memoria devolve em
    # location e a SUB-AREA, nao o mapa (White Bear Village e Ghost Din
    # Woods sao o mesmo mapa, Vast Mountain). Comparar com um nome unico
    # faria o personagem no mapa certo, em outro canto, ler "nao estou
    # na cidade" e queimar um Return Charm a toa.
    areas = cfg["areas_da_cidade"]
    volta = voltar_para_stone(cfg)
    return [
        pular_se(lambda ci: ci.location in areas, len(volta),
                 note=f"ja esta em {'/'.join(areas)}"),
        *volta,
    ]


def montar_se_preciso(cfg) -> list[Step]:
    """Monta so se estiver desmontado -- a tecla e toggle."""
    passos = montar(cfg)
    return [
        pular_se(lambda ci: ci.mounted, len(passos), note="ja esta montado"),
        *passos,
    ]


def ir_ate_npc(cfg, chave: str) -> list[Step]:
    """Caminhada ate um NPC do catalogo (ver pos_npc)."""
    return andar_ate(cfg, pos_npc(cfg, chave))


def esperar_hp_e_mana(cfg) -> list[Step]:
    """
    Segura o roteiro ate HP e mana chegarem no minimo configurado,
    sentando para acelerar a regeneracao.

    Sentar exige desmontar. Os dois passos sao condicionais e nao
    toggles cegos: se a montaria tivesse falhado antes, um toggle cego
    montaria aqui e o personagem chegaria desmontado no teleporte --
    exatamente o contrario do que se queria.

    Sem sit_key configurada, espera em pe: regenera mais devagar, mas
    nao inventa tecla.
    """
    hp_min = cfg.get("hp_min_para_seguir", 100.0)
    mana_min = cfg.get("mana_min_para_seguir", 90.0)

    def pronto(ci):
        return ci.hp_pct >= hp_min and ci.resource_pct >= mana_min

    espera = esperar_ate(
        pronto,
        timeout=cfg.get("timeout_regen", 300.0),
        note=f"espera HP >= {hp_min}% e mana >= {mana_min}%",
    )

    sit_key = cfg.get("sit_key")
    if not sit_key:
        descanso = [espera]
    else:
        descanso = [
            pular_se(lambda ci: not ci.mounted, 2, note="ja esta desmontado"),
            key(cfg["mount_key"], note="desmonta para sentar"),
            wait(1.0),
            key(sit_key, note="senta para regenerar"),
            espera,
            key(sit_key, note="levanta"),
            wait(0.5),
            pular_se(lambda ci: ci.mounted, 2, note="ja esta montado"),
            key(cfg["mount_key"], note="monta de novo"),
            wait(cfg.get("espera_mount", 2.0)),
        ]

    return [
        pular_se(pronto, len(descanso), note="HP e mana ja estao no minimo"),
        *descanso,
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
    """
    Teleporte para Ghost Din Woods, pelo NPC de transporte.

    Substitui a sequencia gravada do macro (8 cliques no minimapa mais
    um clique fixo de confirmacao), que vinha de outro trajeto e erraria
    agora que a chegada e por coordenada.

    Duas ancoras de imagem, e nenhuma coordenada fixa:

    1. O NOME flutuante do NPC. O Transport Fay anda -- medido, saiu de
       (455,430) para (485,470) entre duas capturas -- e o sprite dele e
       animado, nao casa em threshold nenhum (0.85, 0.75, 0.65 todos
       falharam). Ja o nome e texto, sempre igual. Dai ancorar no nome e
       clicar deslocado para baixo, no corpo: medido, +45px abre o
       dialogo e +30px nao.
    2. A LINHA do destino dentro do dialogo. A lista muda de tamanho
       conforme o nivel do personagem (cada destino tem um Level minimo)
       e ainda rola, entao coordenada fixa funcionaria neste char e
       erraria no proximo.

    O threshold do nome e mais frouxo (0.72) porque o texto e desenhado
    por cima do cenario, que muda atras dele.
    """
    return [
        click_template(
            cfg["template_npc_teleporte"],
            botao="double_right",
            threshold=cfg.get("threshold_nome_npc", 0.72),
            deslocamento=(0, cfg.get("deslocamento_corpo_npc", 45)),
            timeout=cfg.get("timeout_npc_teleporte", 15.0),
            note="abre o dialogo do NPC de transporte",
        ),
        wait(1.5),
        click_template(
            cfg["template_destino"],
            timeout=cfg.get("timeout_destino", 10.0),
            note="escolhe Ghost Din Woods",
        ),
        wait(cfg.get("espera_teleporte", 6.0)),
    ]


# =====================================================
# Comercio
# =====================================================

def comprar_pot(cfg) -> list[Step]:
    """
    Compra de pocoes: 16 rodadas de 24 cliques no item.

    Vem do macro 'comprar pot'. O macro original segurava a tecla F12
    durante todo o processo, o que nao faz sentido: F12 e o toggle de
    esconder jogadores, apertado uma vez no preparo.
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


def slot_de_venda(cfg, indice: int) -> tuple[int, int]:
    """
    Centro do slot 'indice' (1-based) na grade da janela de venda.

    Geometria medida no ver.6400: origem (452, 292), passo 35x36, 6
    colunas. Conferida por variancia -- com dois itens na bag, os slots
    1 e 2 deram ~5000 e os vazios entre 2 e 9.
    """
    ox, oy = cfg["venda_origem"]
    px, py = cfg["venda_passo"]
    colunas = cfg["venda_colunas"]
    i = max(1, indice) - 1
    return ox + (i % colunas) * px, oy + (i // colunas) * py


def abrir_dialogo_npc(cfg, prova: str, pontos=None) -> list[Step]:
    """
    Duplo-clique-direito no NPC, tentando alguns pontos ate o dialogo
    abrir.

    O NPC de venda nao serve para a ancora de texto que resolveu o
    teleporte: o nome flutuante dele so aparece em certas condicoes
    (conferido -- nao casa em 0.85, 0.72 nem 0.65 com a tela parada).

    Entao a prova de que o clique acertou e o PROPRIO DIALOGO: tenta um
    ponto, olha se o elemento 'prova' apareceu, e so tenta o proximo se
    nao apareceu. Isso tambem cobre o caso de outro jogador passar na
    frente na hora errada.

    Clique direito NAO move o personagem neste jogo -- so o esquerdo
    move. Entao tentativa que erra o NPC nao custa deslocamento; custa
    so o tempo da espera.
    """
    pontos = pontos or cfg["pontos_do_npc"]
    passos: list[Step] = []
    for n, (x, y) in enumerate(pontos):
        # Quantos passos faltam ate o fim do bloco: cada tentativa que
        # sobra custa 3 passos (clique, espera, pulo), MENOS a ultima,
        # que nao leva pulo -- nao ha o que pular depois dela.
        #
        # A conta errada aqui ((k)*3) pulava um passo A MAIS e engolia o
        # primeiro passo de quem chamou: na venda, era justamente o
        # clique em 'Sell Item'. Sintoma: o dialogo abria, a janela de
        # venda nunca aparecia, e nada acusava erro.
        faltam = len(pontos) - n - 1
        restantes = 3 * faltam - 1 if faltam else 0
        passos += [
            # Clique direito SIMPLES. O duplo veio dos macros antigos e
            # nunca foi medido: conferido no jogo, o simples abre o
            # dialogo igual.
            right(x, y, note=f"tenta abrir o dialogo em ({x},{y})"),
            wait(cfg.get("espera_dialogo", 1.5)),
        ]
        if restantes:
            passos.append(
                pular_se_template(prova, restantes, note="dialogo ja abriu")
            )
    return passos


def comprar_return_charm(cfg) -> list[Step]:
    """
    Compra um Return Charm no NPC de venda.

    O charm e o que devolve o personagem para a cidade no ciclo
    seguinte, entao comprar antes de sair e o que evita a run comecar
    sem saida.

    Mesma anatomia da venda, e pelas mesmas medicoes: clique direito
    SIMPLES abre o dialogo, a janela demora a preencher a grade, e o
    clique no item so MOVE para o carrinho -- quem efetiva e o botao
    'Buy'. Sem ele, fechar a janela desfaz tudo.

    O item entra por TEMPLATE do icone, e nao por posicao na grade: o
    estoque do NPC tem duas paginas e nada garante a ordem entre
    versoes. O icone casa em 0.9, entao a margem e folgada.
    """
    return [
        *abrir_dialogo_npc(cfg, cfg["template_opcao_comprar"]),
        click_template(cfg["template_opcao_comprar"], note="abre a loja"),
        esperar_template(cfg["template_janela_compra"],
                         timeout=cfg.get("timeout_janela_compra", 10.0),
                         note="espera a loja abrir"),
        wait(cfg.get("espera_grade", 1.5), note="deixa a grade preencher"),
        click_template(cfg["template_item_charm"],
                       note="poe o Return Charm no carrinho"),
        wait(0.6),
        click_template(cfg["template_confirmar_compra"],
                       timeout=cfg.get("timeout_confirmar_compra", 5.0),
                       note="efetiva a compra"),
        wait(cfg.get("espera_pos_venda", 1.5)),
        key("ESC", note="fecha a loja"),
        wait(0.5),
    ]


def vender(cfg) -> list[Step]:
    """
    Venda a partir de um slot configuravel.

    O macro antigo dava 12 cliques em dois pontos fixos e ainda carregava
    a navegacao de mapa que hoje e feita por coordenada. Fora isso,
    vendia o que estivesse no slot, sem criterio.

    Duas coisas medidas no jogo desenham este passo:

    1. **O clique no item MOVE para a cesta**, nao vende. Quem
       efetiva e o botao 'Sell'. Custou caro descobrir: sem o clique
       final, o passo de fechar (Cancel) DESFAZIA tudo e devolvia os
       itens para a bag -- e a leitura ingenua era "nao vendeu".
       Provado pelo ouro lido da memoria: 6788596 antes, 6788597 depois.
    2. **A grade se reordena a cada movimentacao.** Movido o item de um
       slot, o seguinte desce para a posicao dele -- conferido por
       variancia: o slot 1 continuou ocupado e o 2 esvaziou. Por isso o
       roteiro bate SEMPRE NO MESMO SLOT, em vez de andar pela grade.

    Dai o 'slot_inicial_venda' proteger o inicio da bag: itens antes
    dele nunca sao tocados, que e como o usuario guarda pocao de HP e
    mana.

    Item "precioso" abre uma caixa de confirmacao AO MOVER. O clique no
    Ok e obrigatorio=False de proposito: item comum nao abre caixa
    nenhuma, e ai o passo desiste em silencio em vez de acusar falha.
    """
    slot = slot_de_venda(cfg, cfg["slot_inicial_venda"])
    vender_um = [
        # Clique esquerdo SIMPLES: conferido no jogo, abre a caixa de
        # confirmacao do mesmo jeito que o duplo-direito herdado.
        left(*slot, note="move para a cesta o primeiro slot liberado"),
        wait(cfg.get("espera_venda", 0.8)),
        click_template(
            cfg["template_ok_venda"],
            timeout=cfg.get("timeout_confirmacao", 2.0),
            obrigatorio=False,
            note="confirma item precioso, se a caixa aparecer",
        ),
    ]
    return [
        *abrir_dialogo_npc(cfg, cfg["template_opcao_vender"]),
        click_template(cfg["template_opcao_vender"], note="abre a lista de venda"),
        # Espera a JANELA, e nao um tempo fixo. A primeira versao dormia
        # 1,5s aqui; quando a janela demorava mais, o duplo-clique do
        # slot caia no dialogo atras e nada era vendido -- sem erro.
        esperar_template(cfg["template_janela_venda"],
                         timeout=cfg.get("timeout_janela_venda", 10.0),
                         note="espera a janela de venda abrir"),
        # A moldura aparece ANTES da grade preencher. Sem esta folga o
        # duplo-clique cai em slot ainda vazio e nada e vendido -- que e
        # por que funcionava na mao (segundos depois) e falhava no
        # runner (0,15s depois).
        wait(cfg.get("espera_grade", 1.5), note="deixa a grade preencher"),
        *repeat(cfg.get("max_itens_vendidos", 20), vender_um),
        # EFETIVA a venda. Sem este clique a cesta fica cheia e o passo
        # seguinte, que fecha a janela, desfaz tudo.
        click_template(cfg["template_confirmar_venda"],
                       timeout=cfg.get("timeout_confirmar_venda", 5.0),
                       note="efetiva a venda"),
        wait(cfg.get("espera_pos_venda", 1.5)),
        click_template(cfg["template_fechar_venda"], obrigatorio=False,
                       note="fecha a janela de venda"),
        wait(0.5),
    ]


# =====================================================
# Coordenada de NPC
# =====================================================

def pos_npc(cfg, chave: str):
    """
    Coordenada do NPC: catalogo primeiro, literal do config como
    reserva.

    'chave' e o prefixo usado no config ('npc_entrada', 'npc_saida'),
    que casa com o trio <chave>_mapa / <chave>_nome / <chave>_pos.

    O catalogo (npcs.json, capturado do painel Surrounding) e a fonte
    porque e ele que escala: cada script novo que precise de um NPC --
    vender em Stone City, por exemplo -- ganha a coordenada sem ninguem
    anotar nada a mao.

    O literal fica como reserva e nao como legado: mapa que ninguem
    capturou ainda, ou NPC que o painel nao lista, continuam
    funcionando. Sem isso, catalogo faltando viraria run quebrada.
    """
    # POSICAO DE PARADA vence tudo. O catalogo guarda a coordenada DO
    # NPC, lida do painel Surrounding; o que a caminhada precisa e onde o
    # PERSONAGEM tem que ficar para clicar nele -- e os dois nao
    # coincidem. Quando existe um ponto de parada medido no jogo, ele e
    # a resposta, e nem catalogo nem estimativa entram na conversa.
    parada = cfg.get(f"{chave}_parada")
    if parada:
        return parada

    mapa = cfg.get(f"{chave}_mapa")
    nome = cfg.get(f"{chave}_nome")
    if mapa and nome:
        caminho = cfg.get("npcs_catalogo") or npcs.CATALOGO
        achado = npcs.coordenada(mapa, nome, caminho)
        if achado:
            return achado
    return cfg[f"{chave}_pos"]


# =====================================================
# Ida ate a cave
# =====================================================

def ir_para_cave(cfg) -> list[Step]:
    """
    Vai ate o Skull Herald da entrada pelo MAPA ABERTO (tecla M).

    Pixel do mapa aberto e destino ABSOLUTO: nao depende de onde o
    personagem esta, nem do zoom do minimapa, nem da velocidade dele --
    e erro de um clique nao se soma ao seguinte. E o que o bot de
    referencia faz neste trecho.

    Tres abordagens caíram antes desta, e vale saber por que, porque
    todas pareciam razoaveis:

    1. Waypoints de coordenada de mundo: parava num ponto diferente a
       cada corrida, e a variacao ia inteira pro clique final.
    2. Cliques no minimapa: pixel de minimapa e deslocamento RELATIVO,
       entao dependia do zoom (calibrado depois) e do ponto de partida
       de cada clique -- erro de um entrava no seguinte.
    3. Os mesmos cliques reproduzindo o tempo gravado: exigia velocidade
       identica entre gravar e rodar. Montaria, buff ou lag desalinhavam
       a rota toda.

    'cave_map_clicks' e gravado com tools/gravar_rota.py --mapa. O
    tempo que vem junto de cada ponto e ignorado: com destino absoluto,
    esperar chegar e sempre correto.
    """
    return walk_by_world_map(cfg, cfg.get("cave_map_clicks") or [])


def fixar_camera(cfg) -> list[Step]:
    """
    Fixa a camera escrevendo zoom, rotacao e angulo na memoria.

    Existe pra proteger os cliques de CHAO e de NPC: eles sao
    coordenadas de TELA, e onde o NPC aparece na tela depende dos tres
    valores. Basta o jogador (ou um clique perdido) girar a camera ou
    rolar o zoom pra eles cairem ao lado do alvo.

    Substituiu o clique no botao de view reset do jogo, que era o que o
    macro fazia. O botao devolve o angulo padrao mas NAO devolve o
    zoom -- e os clients usados aqui tem o limite de zoom liberado, ou
    seja, "resetado" nao quer dizer a mesma coisa em dois clients.
    Escrever os tres valores torna o ponto de tela reproduzivel.

    Falhar aqui nao para o roteiro -- seguir com a camera torta ainda
    tem chance de dar certo, parar ali nao tem --, mas AVISA. Sem o
    aviso, o sintoma aparece so la na frente, num clique que erra o
    alvo sem explicacao.
    """
    return [
        camera(
            zoom=cfg.get("camera_zoom", 380.0),
            rotacao=cfg.get("camera_rotacao", 0.0),
            angulo=cfg.get("camera_angulo", 40.0),
            note="fixa a camera",
        ),
        wait(cfg.get("espera_camera", 0.5)),
    ]


def walk_by_world_map(cfg, pontos) -> list[Step]:
    """
    Deslocamento longo pelo MAPA-MUNDI (tecla M), e nao pelo minimapa.

    O minimapa so alcanca o que esta perto: alvo fora do raio vira
    clique na borda, e o resto da caminhada acaba entregue ao
    pathfinding do jogo, que anda por estrada. O mapa-mundi cobre a area
    inteira, entao dois ou tres cliques certos cortam o trajeto reto --
    que e a razao de existir deste passo.

    'pontos' sao pixels DA JANELA DO MAPA ABERTO, gravados com
    tools/gravar_rota.py --mapa. Nao da pra calcular: a projecao do
    mapa nao tem a escala do minimapa e muda de mapa para mapa.

    Entre um clique e o outro espera o personagem PARAR, e nao um tempo
    fixo: cada trecho leva o que levar, e clicar por cima de uma
    caminhada em curso a cancela.
    """
    if not pontos:
        return []

    tecla = cfg.get("map_key", "M")
    passos: list[Step] = [
        key(tecla, note="abre o mapa-mundi"),
        wait(cfg.get("map_open_delay", 1.0)),
    ]
    for x, y, *_ in pontos:
        # O tempo que o gravador anota junto e ignorado aqui: no mapa
        # aberto o pixel e destino absoluto, entao esperar chegar e
        # sempre correto -- e nao ha o que reproduzir de timing.
        passos += [
            right(x, y, note=f"clique no mapa ({x},{y})"),
            wait(0.5, note="deixa a caminhada comecar"),
            esperar_parado(timeout=cfg.get("map_leg_timeout", 90.0),
                           note="espera chegar no ponto"),
        ]
    passos += [
        key(tecla, note="fecha o mapa-mundi"),
        wait(0.5),
    ]
    return passos


def andar_ate(cfg, destino, tolerancia=None, varredura_apos=None,
              timeout=None) -> list[Step]:
    """
    Caminhada por coordenada do MUNDO, cortando reto pelo minimapa.

    Substitui listas de cliques gravados: aquelas eram cegas -- nao
    sabiam se tinham chegado, e qualquer empurrao no caminho jogava o
    resto da sequencia fora. Aqui o alvo e a coordenada, e o passo so
    termina quando a memoria diz que chegou.

    Nao usa o pathfinding do jogo de proposito: ele anda por passagens
    "de verdade" e custa tempo de farm.
    """
    return [
        walk_to(
            *destino,
            centro=cfg["minimapa_centro"],
            raio=cfg["minimapa_raio"],
            escala=cfg["minimapa_escala"],
            tolerancia=(tolerancia if tolerancia is not None
                        else cfg.get("tolerancia_posicao", 5)),
            varredura_apos=(varredura_apos if varredura_apos is not None
                            else cfg.get("varredura_apos", 3)),
            timeout=(timeout if timeout is not None
                     else cfg.get("timeout_chegada", 60.0)),
            note=f"anda ate {destino}",
        ),
    ]


def arrive_exactly(cfg, destino) -> list[Step]:
    """
    Caminhada ate o destino, SEGUNDA passada, e conferencia.

    Motivo: o walk_to desiste no timeout e devolve o controle -- e
    proposital, travar o ciclo numa caminhada e pior. So que o passo
    seguinte aqui e clique em NPC, coordenada de TELA: seguir com o
    personagem parado longe garante clique no vazio. Medido no jogo:
    foi exatamente assim que a entrada falhou.

    A segunda passada nao e desperdicio. Se a primeira chegou, ela sai
    de graca -- walk_to comeca conferindo a distancia e termina no
    primeiro tick. Se a primeira estourou o tempo, a segunda recomeca
    de muito mais perto, com prazo cheio.

    O wait_position no fim nao corrige nada, so REGISTRA: se nem a
    segunda passada chegou, o aviso no log diz onde o personagem parou,
    que e a informacao que faltava pra entender a falha.
    """
    tolerancia = cfg.get("tolerancia_chegada", 5)
    # Varredura DESLIGADA e prazo curto neste passo. A varredura serve
    # pra contornar obstaculo no meio da rota; no ponto de chegada ela
    # so espalha o personagem -- medido em 2026-08-06: dois timeouts de
    # 60 s girando em circulo antes de parar, por acaso, num lugar de
    # onde o clique funcionou. Perto do destino, nao conseguir fechar
    # nao e estar preso: e o clique de minimapa chegando no limite.
    sem_varredura = 10 ** 6
    prazo = cfg.get("timeout_chegada_final", 20.0)
    return [
        *andar_ate(cfg, destino, tolerancia, sem_varredura, prazo),
        *andar_ate(cfg, destino, tolerancia, sem_varredura, prazo),
        wait_position(
            *destino,
            tolerancia=tolerancia,
            timeout=cfg.get("timeout_conferencia", 10.0),
            note=f"confere que esta em {destino} antes de clicar",
        ),
        wait(cfg.get("espera_pos_chegada", 0.5),
             note="deixa a parada assentar antes de clicar"),
    ]


def falar_com_npc(cfg, destino, ponto_na_tela, template_opcao) -> list[Step]:
    """
    Vai ate um NPC e escolhe uma opcao do dialogo dele.

    A confirmacao de que a interacao deu certo e o DIALOGO abrir, e nao
    a selecao do NPC: clicar num NPC nao preenche a estrutura de alvo
    que a gente le da memoria (essa e do alvo de combate -- mob entra,
    NPC nao). Ja o item de dialogo e interface: alto contraste, sem
    animacao nem iluminacao por cima, que e onde template matching e
    forte.

    Com o personagem no pe do NPC e a camera fixada, o NPC cai perto do
    mesmo ponto da tela -- por isso a ancora e coordenada e nao busca
    por imagem, que no corpo do NPC oscila com a animacao idle (medido:
    0.14 a 0.93 no mesmo lugar).

    "Perto" e nao "no mesmo": a caminhada termina dentro de uma
    tolerancia, nao num pixel, e cada unidade de mundo de sobra desloca
    o NPC na tela. Por isso 'ponto_na_tela' pode ser uma LISTA: tenta um
    ponto, olha se o dialogo abriu, e so entao tenta o proximo. A prova
    e o proprio dialogo, do mesmo jeito que no NPC de venda -- clique
    direito nao move o personagem neste jogo, entao tentativa que erra
    custa tempo e mais nada.

    Sem ponto calibrado, cai no plano B: procura o proprio NPC por
    template.
    """
    return [
        *arrive_exactly(cfg, destino),
        *fixar_camera(cfg),
        *dialogo_do_npc(cfg, ponto_na_tela, template_opcao),
    ]


def dialogo_do_npc(cfg, ponto_na_tela, template_opcao) -> list[Step]:
    """
    So a conversa: abre o dialogo e escolhe a opcao, sem sair do lugar.

    Separado de falar_com_npc porque a entrada na cave precisa REPETIR
    esta parte sem repetir a caminhada. Com instancia cheia a tentativa
    falha estando o personagem no lugar certo -- refazer caminhada e
    camera a cada tentativa era o grosso do tempo perdido entre uma e
    outra.
    """
    passos: list[Step] = []

    # Direito SIMPLES: e o que abre a interacao com NPC. Duplo direito
    # (que e o de mover/interagir com o cenario) seleciona o NPC e nao
    # abre dialogo nenhum -- foi o que travou o primeiro teste.
    if ponto_na_tela:
        pontos = (list(ponto_na_tela)
                  if isinstance(ponto_na_tela[0], (list, tuple))
                  else [tuple(ponto_na_tela)])
        passos += abrir_dialogo_npc(cfg, template_opcao, pontos)
    else:
        passos += [
            click_template(cfg["template_npc_saida"], botao="right",
                           timeout=cfg.get("timeout_npc_saida", 20.0),
                           note="acha e fala com o NPC"),
            wait(1.5, note="abre o dialogo"),
        ]

    passos.append(
        click_template(template_opcao,
                       timeout=cfg.get("timeout_npc_saida", 20.0),
                       note="escolhe a opcao")
    )

    return passos


def entrar_na_cave(cfg) -> list[Step]:
    """
    Entrada na cave, com retentativa.

    E o unico ponto dos macros com realimentacao real: o original
    repetia num 'while_not' ate o pixel (945,148) ficar verde. Aqui a
    retentativa tem LIMITE -- o original podia ficar preso pra sempre.

    A caminhada e a camera acontecem UMA vez, fora do laco; so a
    conversa se repete. A versao anterior repetia a tentativa inteira,
    e havia motivo: naquela epoca a entrada falhava porque o personagem
    nao chegava no lugar certo. Com a ida pela rota do MAPA ABERTO isso
    deixou de ser a falha comum -- o que sobra e instancia cheia, e ai o
    personagem esta no lugar certo e refazer a caminhada so gasta os
    segundos que separam uma tentativa da seguinte.

    Confirmacao por MEMORIA, nao por pixel. O macro antigo olhava o
    pixel (945,148) esperando verde puro; medido em 2026-08-06 com o
    personagem comprovadamente DENTRO da cave, aquele pixel lia
    0x2E3D1E. A checagem dava "nao entrou" estando dentro, e o roteiro
    refazia a tentativa inteira de dentro da cave.

    'location' responde a mesma pergunta sem depender de iluminacao, de
    foco da janela nem de o elemento estar desenhado no quadro: dentro
    da cave ele le 'Bewitcher Cave'.
    """
    areas = cfg.get("areas_da_cave", ["Bewitcher Cave"])
    entrou = lambda ci: ci.location in areas   # noqa: E731

    tentativa = [
        *dialogo_do_npc(cfg, cfg.get("npc_entrada_tela"),
                        cfg["template_enter_bc"]),
        # Espera a MUDANCA DE AREA, nao um tempo fixo. O wait(10.0) que
        # estava aqui cobrava os 10 s inteiros em toda tentativa, mesmo
        # nas que nao entravam -- era o grosso do tempo perdido com
        # instancia cheia. Entrou: segue na hora. Nao entrou: gasta o
        # timeout e tenta de novo.
        esperar_ate(entrou, timeout=cfg.get("timeout_carrega_cave", 8.0),
                    note="espera a cave carregar"),
    ]

    return [
        *arrive_exactly(cfg, pos_npc(cfg, "npc_entrada")),
        *fixar_camera(cfg),
        *retry_until(tentativa, entrou, vezes=cfg["cave_entry_attempts"]),
    ]


def sair_do_team(cfg) -> list[Step]:
    """
    Solta o painel de team e, se 'leave_team' estiver ligado, desfaz o
    grupo.

    Quem sai do team e o RUNNER, ja dentro da cave: e o lado que a gente
    controla no meio do roteiro, sem precisar sincronizar com o client
    do reseter. O efeito na cave e o mesmo -- o grupo deixa de existir
    de qualquer jeito.

    Nao ha nada a soltar aqui: a tecla de esconder jogadores e um
    toggle apertado uma vez no preparo, nao uma tecla segurada.
    """
    if not cfg.get("leave_team", True):
        return []

    return [
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
    return [
        *falar_com_npc(
            cfg,
            pos_npc(cfg, "npc_saida"),
            cfg.get("npc_saida_tela"),
            cfg["template_leave_bc"],
        ),
        wait(cfg.get("espera_teleporte", 6.0), note="teleporta"),
    ]


# =====================================================
# Reseter -- o outro lado da dupla
# =====================================================

def aceitar_team(cfg) -> list[Step]:
    """
    O roteiro INTEIRO do reseter: aceitar o convite do runner.

    Ele nao entra na cave, nao anda e nao luta. So existe pra o grupo
    poder ser formado -- e formar o grupo e o que reseta a cave e
    devolve o boss. Quem desfaz o team e o runner, la dentro (ver
    'sair_do_team'), entao aqui nao ha nada a fazer alem de aceitar de
    novo na proxima run.

    O botao e achado por IMAGEM: o popup de convite nao aparece sempre
    no mesmo lugar, e clicar as cegas erraria. Precisa do recorte
    'botao_aceitar_team.png' em templates/.

    'obrigatorio=False' porque a ausencia do convite e o estado NORMAL:
    o reseter passa a maior parte do tempo esperando o runner terminar
    a run. No timeout o passo desiste em silencio e a fase remonta --
    e isso que faz o laco de espera, sem bloquear o tick.
    """
    return [
        click_template(
            cfg["template_aceitar_team"],
            timeout=cfg.get("timeout_convite", 60.0),
            obrigatorio=False,
            note="aceita o convite de team",
        ),
        wait(cfg.get("intervalo_convite", 2.0)),
    ]


def voltar_para_stone(cfg) -> list[Step]:
    return [
        key(cfg["stone_charm_key"], note="volta pra Stone City"),
        wait(4.0),
    ]
