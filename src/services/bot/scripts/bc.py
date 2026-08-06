# -*- coding: utf-8 -*-
"""
Bewitcher Cave -- ciclo completo.

Auto-contido de proposito: nao conversa com os outros scripts nem
depende deles. Tem as proprias skills, as proprias teclas e o proprio
ataque. Ligar o card Attack junto e escolha do usuario -- este script
nao interfere nem avisa.

Estrutura do ciclo:

    preparo (team, mount, compra, venda, viagem)
        |
        v
    LOOP de 'runs_por_ciclo':
        entrar na cave -> andar -> NPC -> boss -> atacar -> courage
        se ainda faltam runs: reseta o team e repete
        |
        v
    volta pra Stone City -> ciclo de venda

Nada disso bloqueia: o roteiro e uma lista de passos e o StepRunner
avanca um por tick. Assim a Potion continua rodando durante os ~6
minutos da run, o que e a diferenca entre farmar e morrer no boss.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from src.infrastructure.logging import get_logger
from src.services.bot.scripts import bc_steps
from src.services.bot.step_runner import StepContext, StepRunner

logger = get_logger(__name__)


# Tecla nao atribuida. A referencia mostra "unset" e usa [ESC] pra
# limpar; aqui e string vazia, e todo passo que dependeria dela e
# simplesmente omitido do roteiro.
UNSET = ""


DEFAULT_CONFIG = {
    # =========================================================
    # Main / Team
    # =========================================================
    # Nome do personagem que forma dupla com este. O vinculo e CRUZADO:
    # o runner aponta pro reseter e o reseter aponta de volta pro runner.
    # Sem isso nao da pra saber quem forma par com quem quando ha varios
    # clients abertos.
    "member_name": "",
    # Este personagem e o RESETER da dupla: nao faz a BC, so aceita o
    # convite de team. E a formacao do grupo que reseta a cave e devolve
    # o boss, entao ele nao precisa de skills, rota nem pocoes -- e o
    # roteiro dele e uma fase so, em laco.
    "reseter": False,
    # Recorte do botao de aceitar convite. Por imagem porque o popup nao
    # aparece sempre no mesmo lugar.
    "template_aceitar_team": "botao_aceitar_team",
    # Quanto o reseter espera por um convite antes de remontar a fase.
    # Nao e limite de nada: so o tamanho de cada volta do laco de espera.
    "timeout_convite": 60.0,
    "intervalo_convite": 2.0,
    # Desfazer o team e o RUNNER que faz, assim que entra na cave -- e o
    # client que ja esta no meio do roteiro, entao nao precisa de nenhuma
    # sincronizacao com o client do reseter. Desligar so faz sentido pra
    # quem quer manter o grupo por outro motivo.
    "leave_team": True,

    # =========================================================
    # Main / General
    # =========================================================
    # Quantas runs na cave antes de voltar de fato pra cidade. Ao matar
    # o boss, sai pelo NPC (que teleporta pro NPC de entrada) e repete;
    # so depois da ultima volta pra Stone City e vende.
    "runs_por_ciclo": 5,
    "slot_inicial_venda": 1,
    "comprar_return_charm": True,
    "pegar_treasure_box": False,
    # Pro caso do pet nao ter loot automatico: clica no corpo do boss.
    "manual_pick": False,

    # =========================================================
    # Main / Route
    # =========================================================
    # "standard" = direto pro boss.
    # "safe"     = mata as Gun Witches (guardas em frente ao boss)
    #              antes de encarar ele.
    "rota": "standard",
    # Powerfuls sao os mobs das duas fileiras do corredor da sala.
    "lure_powerfuls": False,
    # O boss tem duas fases; cura antes de entrar na segunda.
    "heal_antes_segunda_fase": False,

    # =========================================================
    # Main / Misc
    # =========================================================
    # Usa a skill de AOE enquanto a mana estiver acima deste percentual.
    "aoe_ate_mana": 30,

    # =========================================================
    # Shortcuts / Skills
    # =========================================================
    "attack_keys": ["1", "2", "3"],
    "aoe_key": "3",
    "super_skill_key": UNSET,
    "buff_key": UNSET,
    # Debuff de defesa; so existe pra quem tem mount de combine maximo.
    "break_soul_key": UNSET,
    "healing_spell_key": UNSET,

    # =========================================================
    # Shortcuts / General
    # =========================================================
    "mount_key": "0",
    "speed_skill_key": "9",
    "summon_pet_key": "7",
    "pet_food_key": "6",
    "stone_charm_key": "8",
    "inventory_key": "I",
    # F12 no jogo esconde os outros PERSONAGENS, deixando so os
    # NPCs -- menos poluicao na tela para os cliques de chao e a
    # busca por template. E toggle: um toque basta.
    "esconder_jogadores_key": "F12",

    # =========================================================
    # Shortcuts / Potions  +  limiares
    # =========================================================
    # O BC cuida da propria vida: nao depende do card Potion nem do
    # Fairy estarem ligados.
    "hp_potion_key": UNSET,
    "mana_potion_key": UNSET,
    "battle_hp_key": UNSET,
    "battle_mana_key": UNSET,
    "hp_potion_pct": 90,
    "mana_potion_pct": 30,
    "battle_hp_pct": 30,
    "battle_mana_pct": 30,
    "fairy_heal_pct": 30,
    # Espaco minimo entre dois usos de item, pra nao gastar a mochila
    # inteira num pico de dano.
    "intervalo_pocao": 1.5,

    # =========================================================
    # Stats
    # =========================================================
    "auto_reset_stats": True,

    # =========================================================
    # Etapas opcionais
    # =========================================================
    # Desligado: comprar_pot ainda e o macro antigo, com 16 rodadas de
    # cliques gravados em posicoes fixas, de outro NPC e outro
    # trajeto. Ligar hoje so produz cliques no vazio.
    "comprar_pot": False,
    "vender": True,
    "usar_courage": True,
    "repetir_ciclo": False,

    # =========================================================
    # Ajustes finos
    # =========================================================
    "rodadas_de_compra": 16,
    "compras_por_rodada": 24,
    # 20, e nao 3. Medido em 2026-08-06 observando o bot de referencia:
    # com a instancia LOTADA (o cenario tem limite de gente), ele ficou
    # 62 s no NPC repetindo o dialogo num ciclo de ~1,1 s e ainda assim
    # nao entrou. Com 3 tentativas o roteiro desistia em segundos e
    # seguia como se tivesse entrado -- e o resto da run acontecia do
    # lado de fora da cave.
    "cave_entry_attempts": 20,
    "intervalo_caminhada": 2.0,
    "intervalo_skill": 1.0,
    "timeout_boss": 300.0,
    "gun_witches": 2,
    "powerfuls": 4,
    "timeout_mob": 90.0,
    "casting_treasure_box": 6.0,
    "mobs_do_treasure_box": 3,

    # --- Courage (bag dropada pelo boss) ---
    # Achado por template matching: e um icone fixo, sem escala nem
    # rotacao, que e o caso ideal pro matchTemplate. Precisa do recorte
    # em templates/courage_bag.png.
    "courage_template": "courage_bag",
    "max_courage": 20,
    # Recorte do inventario (x1, y1, x2, y2) pra limitar a busca e
    # evitar casar com algo parecido em outro canto da tela. None
    # procura na janela toda.
    "inventario_regiao": None,

    # --- Camera ---
    # Escrita direto na memoria (base CAMERA, ver PONTEIROS.md).
    #
    # Confirmado no jogo em 2026-08-06: a camera muda na tela.
    #
    # A primeira versao escrevia so o zoom ATUAL (+0x64) e nao mudava
    # nada. O que faltava era o zoom ALVO (+0x68): o cliente interpola o
    # atual em direcao ao alvo, entao escrever so o atual era desfeito
    # na primeira atualizacao de camera. Achado com tools/camera_probe.py,
    # que mede QUAL endereco varia quando o jogador mexe na camera --
    # criterio que separa camera viva de copia.
    #
    # Isto importa porque a camera SAI do lugar durante a run (medido:
    # comecou padrao, chegou torta na cave) e clique em NPC e coordenada
    # de TELA. Sem endireitar antes, o clique passa ao lado.
    "camera_zoom": 380.0,
    "camera_rotacao": 0.0,
    "camera_angulo": 40.0,
    "espera_camera": 0.5,

    # --- Mapa-mundi ---
    # Trecho longo do trajeto: o minimapa so alcanca o que esta perto, e
    # alvo fora do raio dele vira clique na borda -- o que devolve a
    # escolha do caminho ao pathfinding do jogo, que anda por estrada.
    # Alguns cliques no mapa-mundi cortam reto.
    #
    # cave_map_clicks: pixels da JANELA DO MAPA ABERTO. Continua aqui
    # como alternativa, mas hoje esta vazio -- a rota em coordenada de
    # MUNDO abaixo cobre o mesmo trecho sem depender de pixel de tela.
    "cave_map_clicks": [],
    "map_key": "M",
    "map_open_delay": 1.0,
    "map_leg_timeout": 90.0,

    # --- Rota Ghost Din Woods -> Skull Herald ---
    # Capturada em 2026-08-06 com tools/spy_bot.py, gravando o trajeto do
    # bot de referencia: 217 unidades em 14,9 s, coordenada de mundo lida
    # da memoria a 20 Hz e decimada a um ponto a cada 10 unidades.
    #
    # NAO e linha reta de proposito: a barriga pro leste ate x=1415 e a
    # volta pro oeste contornam um obstaculo. Cortar reto daqui trava o
    # personagem nele -- que era o sintoma de "anda e da voltas".
    #
    # Sao breadcrumbs, nao destinos: a tolerancia deles e folgada
    # (waypoint_tolerance), e so o ultimo passo, o do NPC, fecha com
    # tolerancia apertada.
    # Os cinco ultimos vieram de outra gravacao: o personagem levado
    # pelo link do Surrounding, que encosta no NPC de verdade. A emenda
    # cai em (1388, -585) -- o waypoint da rota antiga mais proximo do
    # inicio do trecho novo (4,1 unidades).
    #
    # O trecho novo foi RALEADO de 3 para >=9 unidades de espacamento.
    # Nao e perda de precisao, e o que faz o waypoint existir: com
    # tolerancia 5, um alvo a 3 unidades ja nasce alcancado e o passo
    # termina sem o personagem sair do lugar.
    "cave_waypoints": [
        (1378, -426), (1384, -434), (1391, -442), (1398, -451),
        (1405, -460), (1407, -471), (1409, -481), (1410, -492),
        (1412, -502), (1413, -513), (1415, -523), (1411, -533),
        (1407, -544), (1403, -555), (1398, -566), (1393, -575),
        (1388, -585),
        (1385, -591), (1387, -600), (1389, -609), (1391, -619),
        # Origem do clique fixo, e por isso um waypoint explicito: o
        # pixel gravado foi medido a partir DAQUI. Deixar a entrega ao
        # acaso (o passo anterior para em ~(1388,-620)) transferiria a
        # diferenca inteira para o destino, unidade por unidade.
        (1391, -625),
    ],
    # A rota calculada TERMINA em (1391,-619) -- na pratica o
    # personagem para em (1388,-620), e foi esse o ponto escolhido no
    # jogo como entrega: consistente entre corridas e longe de parede.
    #
    # Daqui ate o NPC sao CLIQUES FIXOS no minimapa, e nao mais conta.
    # O minimapa e centrado no personagem, entao um pixel fixo e um
    # deslocamento relativo fixo: partindo sempre do mesmo lugar, chega
    # sempre no mesmo lugar. Isso dispensa escala, centro e tolerancia
    # -- as tres coisas que erraram nesta parte do trajeto.
    #
    # O preco: depende do ponto de partida ser repetivel. Variacao na
    # entrega vira variacao igual no destino, unidade por unidade.
    #
    # VAZIO ate serem gravados: com o personagem em (1388,-620), rodar
    # 'python tools/gravar_rota.py --pid N --centro 914 114 --raio 72'
    # e clicar no minimapa ate o NPC. Enquanto estiver vazio, o roteiro
    # cai no walk_to de sempre.
    "cave_final_clicks": [
        # Gravado em 2026-08-06 partindo de (1391,-625): chega em
        # (1395,-636), o pe do Skull Herald. Um clique so.
        (929, 145),
    ],
    "espera_clique_final": 0.5,
    "waypoint_tolerance": 10,
    "waypoint_timeout": 45.0,

    # --- Minimapa ---
    # O minimapa e o mundo em escala, centrado no personagem: e o que
    # permite converter "quero chegar em (x, y)" num ponto de clique.
    # Medido neste client -- clique direito no minimapa e comparacao da
    # posicao lida da memoria antes e depois.
    "minimapa_centro": (915, 112),
    # 72 px, MEDIDO na captura por deteccao de circulo (HoughCircles em
    # parada_atual.png deu centro (914,114) e raio 72; o centro
    # confirmou o config, o raio nao). Estava em 55, chutado, o que
    # truncava clique que podia ir mais longe.
    #
    # Com a escala medida, 72 px sao ~27 unidades de alcance por clique.
    "minimapa_raio": 72,
    # Unidades de mundo por pixel. MEDIDA em 2026-08-06 com o minimapa
    # aproximado: cinco cliques gravados com tools/gravar_rota.py e
    # ajuste por minimos quadrados sobre os offsets >= 10 px (offset
    # menor cai na zona morta e contamina a conta). Deu 0,495.
    #
    # Estava em 1.0, chutado, e era o erro por tras de tudo: o walk_to
    # pedia METADE do deslocamento necessario a cada clique. O laco
    # compensava reclicando, ate o resto cair abaixo da zona morta -- e
    # ai travava, a ~4 unidades do alvo. Era esse o sintoma perseguido
    # a sessao inteira.
    #
    # Refeita com o centro medido (914,114): o eixo Y da 0,375 / 0,350 /
    # 0,375 / 0,370 nas quatro amostras -- consistente. O eixo X da 0,80
    # / 0,50 / 0,28 / 0,00, que NAO e dispersao de medicao: aquele
    # trecho e um corredor norte-sul e o personagem nao consegue se
    # deslocar em x ali. As amostras de X mediram parede, nao escala.
    "minimapa_escala": 0.37,

    # --- Entrada da cave (NPC "Skull Herald", do lado de fora) ---
    # Coordenada do MUNDO (a mesma que o jogo mostra) e ponto na TELA
    # com o personagem no pe dele e a camera resetada. O ponto de tela
    # foi medido clicando no NPC e conferindo onde o clique caiu.
    # --- Cidade: venda, compra do charm e teleporte ---
    # LISTA, porque char_info.location traz a SUB-AREA e nao o mapa:
    # White Bear Village e Ghost Din Woods sao o mesmo mapa (Vast
    # Mountain). Estar em qualquer sub-area listada conta como "ja
    # estou na cidade"; fora delas, o roteiro usa o Return Charm.
    # Se Stone City tiver mais sub-areas, e so acrescentar aqui.
    "areas_da_cidade": ["Stone City"],
    # --- Janela de venda ---
    # Geometria da grade, medida no ver.6400 e conferida por variancia
    # (slots com item deram ~5000; vazios, entre 2 e 9).
    "venda_origem": (452, 292),
    "venda_passo": (35, 36),
    "venda_colunas": 6,
    # A grade se REORDENA a cada venda: o item seguinte desce para o
    # slot que esvaziou. Por isso o roteiro bate sempre no mesmo slot, e
    # tudo antes deste indice fica intocado -- e como o usuario protege
    # pocao de HP e mana.
    "max_itens_vendidos": 20,
    "espera_venda": 0.8,
    "timeout_confirmacao": 2.0,
    # Ancoras da venda. O NPC nao entra por template: o nome flutuante
    # dele so aparece em certas condicoes, entao o roteiro tenta alguns
    # pontos e usa o PROPRIO DIALOGO como prova de que acertou.
    # Medido um a um no Rich Man: estes tres abrem o dialogo. O ponto
    # (490,390), que estava primeiro, NAO abre -- passa ao lado do
    # sprite.
    "pontos_do_npc": [(480, 385), (470, 400), (510, 395), (490, 420)],
    "espera_dialogo": 1.5,
    "template_opcao_vender": "opcao_sell_item",
    "template_opcao_comprar": "opcao_purchase_item",
    "template_janela_compra": "janela_buy",
    "timeout_janela_compra": 10.0,
    # O item entra por template do icone: o estoque do NPC tem duas
    # paginas e nada garante a ordem. O icone casa em 0.9.
    "template_item_charm": "item_return_charm",
    "template_confirmar_compra": "botao_buy",
    "timeout_confirmar_compra": 5.0,
    "template_janela_venda": "janela_sell",
    "timeout_janela_venda": 10.0,
    "espera_grade": 1.5,
    "template_ok_venda": "botao_ok_venda",
    # O duplo-clique so MOVE o item para a cesta; este botao efetiva.
    "template_confirmar_venda": "botao_sell",
    "timeout_confirmar_venda": 5.0,
    "espera_pos_venda": 1.5,
    "template_fechar_venda": "botao_cancel",
    "npc_venda_mapa": "Stone City",
    "npc_venda_nome": "Rich Man",
    "npc_venda_pos": (153, -493),
    # Ancoras de imagem do teleporte. O NOME flutuante do NPC em vez do
    # sprite: ele anda e e animado, o texto nao. O clique vai deslocado
    # para baixo, no corpo -- medido, +45px abre o dialogo e +30 nao.
    "template_npc_teleporte": "label_transport_fay",
    "threshold_nome_npc": 0.72,
    "deslocamento_corpo_npc": 45,
    "timeout_npc_teleporte": 15.0,
    # Linha do destino dentro do dialogo. Por template porque a lista
    # muda de tamanho conforme o nivel do personagem e ainda rola.
    "template_destino": "destino_ghost_din_woods",
    "timeout_destino": 10.0,
    "npc_teleporte_mapa": "Stone City",
    "npc_teleporte_nome": "Transport Fay",
    "npc_teleporte_pos": (178, -518),

    # Espera de regeneracao, ao lado do NPC de teleporte.
    "hp_min_para_seguir": 100.0,
    "mana_min_para_seguir": 90.0,
    "timeout_regen": 300.0,
    # X e o padrao do jogo para sentar. Sentar regenera mais rapido, e
    # e so por isso que o roteiro desmonta antes da espera. Vazio aqui
    # significa "espera em pe": o bloco de sentar some inteiro.
    "sit_key": "X",
    "espera_pet": 3.0,
    "espera_mount": 3.0,

    # Mapa + nome sao a fonte: pos_npc() resolve pelo npcs.json,
    # capturado do painel Surrounding. A coordenada literal fica como
    # reserva, para o caso de o catalogo nao ter esse mapa ainda.
    "npc_entrada_mapa": "White Bear Village",
    "npc_entrada_nome": "Skull Herald",
    "npc_entrada_pos": (1395, -636),
    # Onde o PERSONAGEM para para falar com ele.
    #
    # (1393, -636), medido a mao no jogo: e a posicao de onde o clique
    # no NPC funciona. Nao confundir com a coordenada DO NPC, que o
    # catalogo npcs.json guarda como (1395, -636) -- parar em cima dela
    # deixou o personagem fora do angulo de clique nas tres corridas de
    # 2026-08-06.
    "npc_entrada_parada": (1395, -636),
    # Depois de chegar, antes de clicar: o personagem ainda esta
    # assentando a animacao de parada quando o passo seguinte comeca, e
    # clique disparado nesse instante sai antes do NPC estar no lugar
    # final da tela.
    "espera_pos_chegada": 0.5,
    # LISTA e nao ponto unico: a caminhada para dentro de uma
    # tolerancia, nao num pixel, e cada unidade de mundo de sobra
    # desloca o NPC na tela. O primeiro e o ponto medido; os outros o
    # cercam. Roteiro tenta um, confere se o dialogo abriu, e so entao
    # tenta o proximo -- clique direito nao move o personagem, entao
    # tentativa que erra custa so o tempo da espera.
    "npc_entrada_tela": [(479, 410), (479, 396), (466, 410),
                         (492, 410), (479, 424)],
    "template_enter_bc": "enter_bc",

    # --- Saida da cave (NPC "Skull Herald") ---
    # Mesmo NPC, do lado de dentro. O ponto de tela ainda nao foi
    # calibrado la dentro; None faz cair na busca por template.
    "npc_saida_tela": None,
    # Aparece depois que o boss morre e teleporta de volta pro NPC de
    # entrada. E o que permite repetir a run sem passar pela cidade.
    # A coordenada e do MUNDO (a mesma que o jogo mostra), lida da
    # memoria -- nao e posicao de tela.
    # Sem mapa aqui: o nome do mapa de DENTRO da cave ainda nao foi
    # lido no jogo. Assim que for, basta capturar com
    # 'pegar_coordenada_npc.py --salvar' la dentro e por o nome em
    # "npc_saida_mapa" -- o literal abaixo vira reserva sozinho.
    "npc_saida_nome": "Skull Herald",
    "npc_saida_pos": (82, -396),
    "template_npc_saida": "skull_herald",
    "template_leave_bc": "leave_bc",
    # 5. Nao e escolha de gosto, e o piso do metodo: o clique de
    # caminhada e no MINIMAPA, e o ponto clicado fica a (alvo - atual)
    # pixels do centro. Faltando 2 unidades, o clique sai a 2 px do
    # centro -- em cima do proprio personagem, e o jogo ignora.
    #
    # Medido em 2026-08-06: com tolerancia 2 o personagem parava a ~13
    # unidades do alvo e nao fechava nunca. Pior, o walk_to lia isso
    # como travamento e disparava a varredura circular, que o mandava
    # passear -- o vaivem que aparecia no log.
    #
    # As unidades que sobram sao absorvidas pelos varios pontos de
    # clique no NPC (npc_entrada_tela), que e o lugar certo pra tratar
    # essa folga: clique direito nao move o personagem, entao tentar
    # cinco pontos custa tempo e nada mais.
    "tolerancia_posicao": 5,
    # Tolerancia do passo final. Voltou para 5 depois da medicao de
    # 2026-08-06: com 2, o walk_to gastou DOIS timeouts de 60 s parado
    # em (1389,-633) tentando alcancar (1393,-636) e nunca fechou.
    #
    # E limite do metodo, nao de ajuste: o clique de caminhada sai a
    # (alvo - atual) pixels do centro do minimapa, entao faltando 4
    # unidades ele cai praticamente em cima do personagem e o jogo
    # ignora. Insistir custa 2 minutos por run e nao entrega nada.
    #
    # Quem absorve as unidades que sobram e a lista de pontos de clique
    # no NPC -- e ela deu conta: na mesma corrida, o dialogo abriu no
    # segundo ponto com o personagem em (1396,-633).
    # 3: logo acima da zona morta medida (~5 px = 2,5 unidades). Abaixo
    # dela o clique cai em cima do proprio personagem e o jogo ignora --
    # era o que fazia o passo gastar o timeout sem sair do lugar.
    "tolerancia_chegada": 3,
    "timeout_chegada": 60.0,
    # Prazo do passo final, curto de proposito: ele nao tem obstaculo
    # pra contornar, so os ultimos metros. Se nao fechou em 20 s, nao
    # vai fechar -- insistir e o que fazia a run perder minutos.
    "timeout_chegada_final": 20.0,
    # Conferencia de chegada: nao corrige, so registra onde parou.
    "timeout_conferencia": 10.0,
    "timeout_npc_saida": 20.0,
    "espera_teleporte": 6.0,

    # --- Posicoes que ainda precisam de calibracao no jogo ---
    # Nenhum dos macros antigos cobria estas etapas, entao os valores
    # abaixo sao PALPITES centrados na tela. Conferir antes de usar.
    "treasure_box_pos": (512, 300),
    "corpo_do_boss_pos": (512, 384),
}


@dataclass
class BCStats:
    """
    Contadores da aba Stats.

    Vivem no script (uma instancia por sessao), nao na GUI: quem sabe
    que uma run comecou ou terminou e a maquina de estados. A interface
    so le.
    """

    runs: int = 0
    sucessos: int = 0
    falhas: int = 0
    courage: int = 0
    tempo_ultima_run: float = 0.0
    tempo_total: float = 0.0
    _inicio_run: float | None = None

    def iniciar_run(self):
        self._inicio_run = time.time()

    def encerrar_run(self, sucesso: bool):
        if self._inicio_run is not None:
            duracao = time.time() - self._inicio_run
            self.tempo_ultima_run = duracao
            self.tempo_total += duracao
            self._inicio_run = None

        self.runs += 1
        if sucesso:
            self.sucessos += 1
        else:
            self.falhas += 1

    @property
    def run_atual(self) -> float:
        if self._inicio_run is None:
            return 0.0
        return time.time() - self._inicio_run

    def zerar(self):
        self.runs = 0
        self.sucessos = 0
        self.falhas = 0
        self.courage = 0
        self.tempo_ultima_run = 0.0
        self.tempo_total = 0.0
        self._inicio_run = None

    @staticmethod
    def formatar(segundos: float) -> str:
        """'0h 9m 19s', como na referencia."""
        total = int(segundos)
        return f"{total // 3600}h {(total % 3600) // 60}m {total % 60}s"

    @staticmethod
    def formatar_longo(segundos: float) -> str:
        """'0d 0h 31m 59s', usado no tempo total."""
        total = int(segundos)
        dias, resto = divmod(total, 86400)
        horas, resto = divmod(resto, 3600)
        return f"{dias}d {horas}h {resto // 60}m {resto % 60}s"


class BCScript:
    """
    Bewitcher Cave -- entra na cave, mata o boss e volta.

    O roteiro vive em bc_steps.py como dados; aqui fica so a maquina de
    estados que decide qual fase montar em seguida.
    """

    name = "BC"

    FASE_PREPARO = "preparo"
    FASE_RUN = "run"
    FASE_RESET = "reset"
    FASE_RETORNO = "retorno"
    # Fase unica do reseter: ele nao percorre o ciclo, fica nela em laco.
    FASE_RESETER = "reseter"
    FASE_FIM = "fim"

    _MONTADORES = {
        FASE_PREPARO: "_montar_preparo",
        FASE_RUN: "_montar_run",
        FASE_RESET: "_montar_reset",
        FASE_RETORNO: "_montar_retorno",
        FASE_RESETER: "_montar_reseter",
    }

    def __init__(self, config: dict | None = None):
        self._config = {**DEFAULT_CONFIG, **(config or {})}
        self._fase = self._fase_inicial()
        self._runner: StepRunner | None = None
        self._runs_feitas = 0
        self._anunciou_fim = False
        self.stats = BCStats()
        self._ultimo_consumo = 0.0
        self._memoria = None
        self._memoria_hwnd = None

    # =====================================================
    # Configuracao / estado
    # =====================================================

    def _fase_inicial(self) -> str:
        """
        O papel decide o roteiro inteiro, nao um passo dele.

        Por isso a bifurcacao acontece aqui, na primeira fase, e nao
        espalhada em 'if reseter' dentro do ciclo: o reseter nunca entra
        no preparo, nunca viaja e nunca luta.
        """
        if self._config.get("reseter"):
            logger.info("BC em modo RESETER: so aceita convite de team")
            return self.FASE_RESETER
        return self.FASE_PREPARO

    @property
    def config(self) -> dict:
        return self._config

    @property
    def fase(self) -> str:
        return self._fase

    @property
    def runs_feitas(self) -> int:
        return self._runs_feitas

    def reset(self):
        """Volta o script ao inicio (usado ao religar o card)."""
        self._fase = self._fase_inicial()
        self._runner = None
        self._runs_feitas = 0
        self._anunciou_fim = False
        self._ultimo_consumo = 0.0

        if self._config.get("auto_reset_stats"):
            self.stats.zerar()

    def _memoria_do_client(self, hwnd):
        """
        Leitor/escritor de memoria daquele cliente, criado sob demanda.

        O motor ja monta char_info a cada tick, entao ler daqui seria
        redundante -- o que falta e ESCREVER: fixar a camera. Como o
        protocolo tick() nao passa o memory_reader do motor (mudaria a
        assinatura dos doze scripts por causa de um passo so), este abre
        o proprio handle a partir do hwnd.

        Falha de abertura nao derruba o ciclo: devolve None, e o passo
        de camera avisa e segue.
        """
        if self._memoria is not None and self._memoria_hwnd == hwnd:
            return self._memoria

        try:
            import win32process

            from src.services.game.memory_reader import MemoryReader

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            self._memoria = MemoryReader(pid)
            self._memoria_hwnd = hwnd
        except Exception:
            logger.warning("Sem acesso a memoria do client; camera nao sera fixada")
            self._memoria = None

        return self._memoria

    # =====================================================
    # Sobrevivencia -- roda a cada tick, fora do roteiro
    # =====================================================

    def _cuidar_da_vida(self, hwnd, char_info, input_service) -> bool:
        """
        Poções e self-heal, verificados a CADA tick.

        Fica fora do roteiro de passos de proposito: precisar de poção
        é um evento que acontece a qualquer momento, não num ponto
        específico da sequência. Se dependesse do passo atual, o
        personagem morreria esperando a vez.

        É também o que torna o BC independente: não precisa do card
        Potion nem do Fairy ligados.
        """

        if char_info is None:
            return False

        agora = time.time()

        if agora - self._ultimo_consumo < self._config["intervalo_pocao"]:
            return False

        cfg = self._config
        hp = getattr(char_info, "hp_pct", 100.0)
        mp = getattr(char_info, "resource_pct", 100.0)
        em_batalha = bool(getattr(char_info, "in_battle", False))

        # Morto não toma poção -- evita queimar item na tela de morte.
        if hp <= 0:
            return False

        # Em batalha o jogo exige as versões "battle" dos itens.
        if em_batalha:
            candidatos = [
                (cfg["battle_hp_key"], hp, cfg["battle_hp_pct"], "battle HP"),
                (cfg["battle_mana_key"], mp, cfg["battle_mana_pct"], "battle mana"),
            ]
        else:
            candidatos = [
                (cfg["hp_potion_key"], hp, cfg["hp_potion_pct"], "HP"),
                (cfg["mana_potion_key"], mp, cfg["mana_potion_pct"], "mana"),
            ]

        # Self-heal da Fairy: alternativa à poção quando a vida cai em
        # combate, e a única opção se as battle pots estiverem unset.
        if em_batalha and cfg["healing_spell_key"]:
            candidatos.append(
                (cfg["healing_spell_key"], hp, cfg["fairy_heal_pct"], "self-heal")
            )

        for tecla, valor, limite, rotulo in candidatos:
            if not tecla:
                continue
            if valor > limite:
                continue

            input_service.press_key(hwnd, tecla)
            self._ultimo_consumo = agora
            logger.debug("Usou %s (%.0f%% <= %s%%)", rotulo, valor, limite)
            return True

        return False

    # =====================================================
    # Montagem das fases
    # =====================================================

    def _montar_preparo(self) -> list:
        """
        Preparo, na ordem em que o fluxo foi especificado.

        A ordem nao e arbitraria: o Return Charm vem ANTES da caminhada
        porque coordenada de mundo so quer dizer alguma coisa dentro do
        mapa certo; e a espera de HP/mana fica no NPC de teleporte, e
        nao no de venda, para a regeneracao correr enquanto o
        personagem ja esta onde precisa estar depois.
        """
        cfg = self._config
        passos = []
        passos += bc_steps.ajustes_iniciais(cfg)      # esconder + zoom + camera
        passos += bc_steps.garantir_pet(cfg)
        passos += bc_steps.garantir_cidade(cfg)       # Return Charm se preciso
        passos += bc_steps.convidar_team(cfg)
        passos += bc_steps.montar_se_preciso(cfg)
        passos += bc_steps.ir_ate_npc(cfg, "npc_venda")

        if cfg.get("comprar_return_charm"):
            passos += bc_steps.comprar_return_charm(cfg)

        if cfg.get("comprar_pot"):
            passos += bc_steps.comprar_pot(cfg)

        if cfg.get("vender"):
            passos += bc_steps.vender(cfg)

        passos += bc_steps.ir_ate_npc(cfg, "npc_teleporte")
        passos += bc_steps.esperar_hp_e_mana(cfg)
        passos += bc_steps.ir_para_ghost(cfg)         # dialogo do Transport Fay
        passos += bc_steps.ir_para_cave(cfg)
        return passos

    def _montar_run(self) -> list:
        cfg = self._config
        passos = []
        passos += bc_steps.entrar_na_cave(cfg)
        passos += bc_steps.sair_do_team(cfg)
        passos += bc_steps.andar_na_cave(cfg)
        passos += bc_steps.entrar_no_npc(cfg)
        passos += bc_steps.caminho_boss(cfg)
        # Corredor da sala: as duas fileiras de Powerfuls.
        passos += bc_steps.limpar_powerfuls(cfg)
        # Rota safe: derruba os guardas antes de encarar o boss.
        passos += bc_steps.matar_gun_witches(cfg)
        passos += bc_steps.atacar_boss(cfg)
        passos += bc_steps.lotear_boss(cfg)
        passos += bc_steps.abrir_treasure_box(cfg)
        passos += bc_steps.usar_courage(cfg)
        return passos

    def _montar_reset(self) -> list:
        """
        Entre uma run e outra: sai pela Skull Herald e reconstitui o
        team, sem passar pela cidade.

        Sair e refazer o grupo e o que RESETA a cave -- e por isso que o
        reseter existe.
        """
        cfg = self._config
        return [
            *bc_steps.sair_da_cave(cfg),
            *bc_steps.ajustes_iniciais(cfg),
            *bc_steps.convidar_team(cfg),
        ]

    def _montar_reseter(self) -> list:
        """
        Uma volta do laco de espera do reseter.

        A fase termina rapido de proposito: quando o convite nao vem no
        timeout, ela e remontada e espera de novo. Isso mantem o tick
        curto -- o card do reseter nao trava os outros scripts da conta.
        """
        return list(bc_steps.aceitar_team(self._config))

    def _montar_retorno(self) -> list:
        cfg = self._config
        passos = list(bc_steps.voltar_para_stone(cfg))

        if cfg.get("vender"):
            passos += bc_steps.vender(cfg)

        return passos

    # =====================================================
    # Maquina de estados
    # =====================================================

    def _proxima_fase(self) -> str:
        # O reseter nao tem ciclo: volta pra propria fase e espera o
        # convite seguinte. So para quando o usuario desliga o card.
        if self._fase == self.FASE_RESETER:
            return self.FASE_RESETER

        if self._fase == self.FASE_PREPARO:
            return self.FASE_RUN

        if self._fase == self.FASE_RUN:
            self._runs_feitas += 1
            # Sem leitura confiavel de "o boss morreu mesmo", uma run
            # que chegou ao fim do roteiro conta como sucesso. Quando
            # houver como confirmar o drop, e aqui que muda.
            self.stats.encerrar_run(sucesso=True)
            faltam = self._config["runs_por_ciclo"] - self._runs_feitas
            if faltam > 0:
                logger.info(
                    "Run %s/%s concluida; resetando o team pra proxima",
                    self._runs_feitas, self._config["runs_por_ciclo"],
                )
                return self.FASE_RESET
            logger.info("Runs concluidas; voltando pra Stone City")
            return self.FASE_RETORNO

        if self._fase == self.FASE_RESET:
            return self.FASE_RUN

        if self._fase == self.FASE_RETORNO:
            if self._config.get("repetir_ciclo"):
                logger.info("Ciclo concluido; recomecando")
                self._runs_feitas = 0
                return self.FASE_PREPARO
            return self.FASE_FIM

        return self.FASE_FIM

    def _garantir_runner(self) -> bool:
        """Monta o roteiro da fase atual se ainda nao houver. False no fim."""

        if self._fase == self.FASE_FIM:
            return False

        if self._runner is None:
            montador = getattr(self, self._MONTADORES[self._fase])
            passos = montador()
            self._runner = StepRunner(passos, name=f"BC/{self._fase}")

            if self._fase == self.FASE_RUN:
                self.stats.iniciar_run()

            # O laco do reseter remonta a cada timeout de convite; em
            # info isso viraria uma linha por minuto, pra sempre.
            registrar = (logger.debug if self._fase == self.FASE_RESETER
                         else logger.info)
            registrar("Fase '%s' iniciada (%s passos)", self._fase, len(passos))

        return True

    # =====================================================
    # Protocolo BotScript
    # =====================================================

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:

        # Sobrevivencia vem ANTES do roteiro: se o personagem esta
        # morrendo, poção é mais urgente que o próximo clique.
        if self._cuidar_da_vida(hwnd, char_info, input_service):
            return True

        if not self._garantir_runner():
            if not self._anunciou_fim:
                logger.info("Ciclo do BC terminado")
                self._anunciou_fim = True
            return False

        ctx = StepContext(
            hwnd=hwnd,
            input_service=input_service,
            vision_service=vision_service,
            char_info=char_info,
            target_info=target_info,
            memory=self._memoria_do_client(hwnd),
        )

        agiu = self._runner.tick(ctx)

        if self._runner.finished:
            self._fase = self._proxima_fase()
            self._runner = None

        return agiu
