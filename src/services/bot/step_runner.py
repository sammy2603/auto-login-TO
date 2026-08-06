# -*- coding: utf-8 -*-
"""
Motor de passos para scripts longos.

O problema: os macros antigos sao sequencias lineares de varios
minutos, cheias de 'wait'. O tick() dos nossos scripts nao pode
bloquear -- ele roda num loop compartilhado com os outros scripts da
mesma conta, entao um BC que segure a thread por 6 minutos impede a
pocao de ser usada e mata o personagem.

A solucao: o roteiro vira uma LISTA DE PASSOS declarativa, e o runner
guarda em que passo esta. Cada tick executa no maximo um passo e
devolve o controle. Uma espera de 2 segundos nao dorme: ela anota um
prazo e os ticks seguintes so verificam se ja venceu.

Vantagem colateral: as centenas de coordenadas viram DADOS, num
arquivo separado. Recalibrar depois de um patch do jogo e editar uma
tabela, nao cacar chamadas de clique no meio da logica.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


# =====================================================
# Passos
# =====================================================

LEFT = "left"                    # clique esquerdo (menus, botoes)
RIGHT = "right"                  # clique direito = MOVIMENTO no jogo
DOUBLE_RIGHT = "double_right"    # duplo direito = interagir/mover
KEY = "key"                      # pressiona e solta
KEY_DOWN = "key_down"            # segura
KEY_UP = "key_up"                # solta
WAIT = "wait"                    # espera nao-bloqueante
WAIT_COLOR = "wait_color"        # espera um pixel ficar de certa cor
SKIP_IF_COLOR = "skip_if_color"  # pula N passos se a cor ja estiver la
CLICK_TEMPLATE = "click_template"  # espera um elemento aparecer e clica nele
WAIT_POSITION = "wait_position"  # espera o personagem chegar numa coordenada
SKIP_IF = "skip_if"              # pula N passos se a MEMORIA disser que sim
SKIP_IF_TEMPLATE = "skip_if_template"  # pula N passos se um elemento ja esta na tela
WAIT_TEMPLATE = "wait_template"   # espera um elemento aparecer, SEM clicar nele
WAIT_UNTIL = "wait_until"        # espera ate a MEMORIA satisfazer a condicao
USE_ALL_ITEMS = "use_all_items"  # acha um item por imagem e usa, ate acabar
ATTACK_UNTIL_DEAD = "attack_until_dead"   # ataca ate o alvo morrer
CLICK_UNTIL_TARGET = "click_until_target"  # clica ate selecionar certo alvo
WALK_TO = "walk_to"              # anda ate uma coordenada do mundo, pelo minimapa
WAIT_STOPPED = "wait_stopped"    # espera o personagem parar de andar
CAMERA = "camera"                # fixa zoom/rotacao/angulo escrevendo na memoria
CALL = "call"                    # delega a um callable do script


@dataclass(frozen=True)
class Step:
    """
    Um passo do roteiro.

    'kind' e uma das constantes acima; 'args' varia por tipo. Frozen
    de proposito: o roteiro e dado imutavel, compartilhado entre
    sessoes -- o estado de execucao vive no runner, nunca no passo.
    """

    kind: str
    args: tuple = ()
    timeout: float = 0.0
    note: str = ""


# Atalhos para montar roteiros de forma legivel no arquivo de dados.
def left(x: int, y: int, note: str = "") -> Step:
    return Step(LEFT, (x, y), note=note)


def right(x: int, y: int, note: str = "") -> Step:
    return Step(RIGHT, (x, y), note=note)


def double_right(x: int, y: int, note: str = "") -> Step:
    return Step(DOUBLE_RIGHT, (x, y), note=note)


def key(k, note: str = "") -> Step:
    return Step(KEY, (k,), note=note)


def key_down(k, note: str = "") -> Step:
    return Step(KEY_DOWN, (k,), note=note)


def key_up(k, note: str = "") -> Step:
    return Step(KEY_UP, (k,), note=note)


def wait(seconds: float, note: str = "") -> Step:
    return Step(WAIT, (seconds,), note=note)


def wait_color(x: int, y: int, color, timeout: float = 60.0,
               tolerance: int = 10, note: str = "") -> Step:
    """
    Espera o pixel (x, y) ficar da cor indicada.

    E o 'while_not' dos macros antigos -- a unica realimentacao real
    que eles tinham. Se estourar o timeout, o runner registra e segue,
    em vez de travar pra sempre.
    """
    return Step(WAIT_COLOR, (x, y, color, tolerance), timeout=timeout, note=note)


def skip_if_color(x: int, y: int, color, steps_ahead: int,
                  tolerance: int = 10, note: str = "") -> Step:
    """
    Pula os proximos 'steps_ahead' passos se o pixel ja estiver da cor
    indicada.

    E como o retry dos macros vira dado: monta-se N tentativas em
    sequencia e, entre elas, um skip que descarta as restantes assim
    que a condicao for satisfeita. Sem isto, so daria pra repetir as
    tentativas cegamente, mesmo depois de ter dado certo.
    """
    return Step(SKIP_IF_COLOR, (x, y, color, tolerance, steps_ahead), note=note)


def retry_until_color(tentativa: list[Step], x: int, y: int, color,
                      vezes: int = 3, tolerance: int = 10) -> list[Step]:
    """
    Repete um bloco ate o pixel (x, y) ficar da cor indicada, no maximo
    'vezes'. Substitui o 'while_not' dos macros -- com limite, pra nao
    ficar preso pra sempre como o original ficava.
    """
    saida: list[Step] = []
    for n in range(vezes):
        restantes = (vezes - n - 1) * (len(tentativa) + 1)
        saida.extend(tentativa)
        if restantes > 0:
            saida.append(skip_if_color(x, y, color, restantes, tolerance))
    return saida


def click_template(template: str, region=None, timeout: float = 20.0,
                   threshold: float = 0.85, botao: str = "left",
                   obrigatorio: bool = True, deslocamento=(0, 0),
                   note: str = "") -> Step:
    """
    Espera um elemento aparecer na tela e clica nele.

    Melhor que coordenada fixa pra coisas que MUDAM DE LUGAR ou que
    demoram a aparecer -- caixa de dialogo de NPC, popup de convite.
    Clicar as cegas nesses casos erra sempre que o jogo desenha a
    janela alguns pixels adiante.

    'obrigatorio=False' faz o passo desistir em silencio no timeout,
    pra elementos que podem simplesmente nao aparecer.

    'deslocamento' clica a (dx, dy) do centro do que foi achado. Serve
    pra ancorar no que e ESTAVEL e clicar no que nao e: o nome flutuante
    de um NPC e texto, sempre igual, enquanto o corpo dele e sprite
    animado que nao casa em threshold nenhum. Medido no Transport Fay --
    ancora no nome, clica 45px abaixo.
    """
    return Step(
        CLICK_TEMPLATE,
        (template, region, threshold, botao, obrigatorio, deslocamento),
        timeout=timeout,
        note=note,
    )


def wait_position(x: int, y: int, tolerancia: int = 5, timeout: float = 60.0,
                  note: str = "") -> Step:
    """
    Espera o personagem chegar perto de uma coordenada DO MUNDO (a
    mesma que o jogo mostra), lida da memoria.

    Substitui esperar N segundos e torcer: se a caminhada foi rapida
    segue antes, se foi lenta espera mais. Os macros antigos nao tinham
    como fazer isso.
    """
    return Step(WAIT_POSITION, (x, y, tolerancia), timeout=timeout, note=note)


def use_all_items(template: str, region=None, maximo: int = 20,
                  intervalo: float = 1.0, threshold: float = 0.85,
                  note: str = "") -> Step:
    """
    Localiza um item pelo icone e usa (duplo-direito), repetindo
    enquanto ainda achar -- ate o limite 'maximo'.

    Serve pras bags dropadas pelo boss: nao se sabe de antemao quantas
    cairam, entao contar repeticoes fixas erra pros dois lados. Aqui,
    'nao achou mais' e a condicao de parada natural.

    Se o template nao existir em templates/, o VisionService avisa uma
    vez e devolve None -- o passo termina sem fazer nada, em vez de
    derrubar o ciclo.
    """
    return Step(
        USE_ALL_ITEMS,
        (template, region, maximo, intervalo, threshold),
        note=note,
    )


def attack_until_dead(skills, timeout: float = 300.0,
                      skill_interval: float = 1.0, aoe_key: str = "",
                      aoe_ate_mana: float | None = None, super_key: str = "",
                      note: str = "") -> Step:
    """
    Cicla as skills ate o alvo morrer.

    Substitui o 'repeat 130' do macro: em vez de contar repeticoes e
    torcer, le a vida do alvo. Se o alvo morrer antes, para antes; se
    demorar mais, continua.

    'aoe_key' entra na rotacao apenas enquanto a mana estiver ACIMA de
    'aoe_ate_mana' -- AOE custa caro, e ficar sem mana no meio do boss
    e pior que matar mais devagar.

    'super_key' e disparada uma vez no inicio, quando informada.
    """
    return Step(
        ATTACK_UNTIL_DEAD,
        (tuple(skills), skill_interval, aoe_key or "", aoe_ate_mana, super_key or ""),
        timeout=timeout,
        note=note,
    )


def walk_to(x: int, y: int, centro=(915, 112), raio: int = 55,
            escala: float = 1.0, tolerancia: int = 2, intervalo: float = 0.5,
            paradas: int = 2, varredura_apos: int = 3,
            timeout: float = 120.0, note: str = "") -> Step:
    """
    Anda ate uma coordenada DO MUNDO clicando no minimapa.

    O minimapa e o mundo em escala e centrado no personagem, entao o
    ponto de clique sai de conta, nao de tabela: pega a diferenca entre
    onde estamos (lida da memoria) e onde queremos chegar, divide pela
    escala e soma ao centro do minimapa. Corta reto pelo mapa, sem o
    pathfinding do jogo -- que anda por passagens "de verdade" e custa
    tempo de farm.

    O eixo y e INVERTIDO: subir no minimapa aumenta o y do mundo.

    E um laco fechado, mas o gatilho e a PARADA do personagem, nao o
    relogio: reclicar no meio da caminhada cancela o trajeto em curso e
    manda o char recomecar de onde estiver -- e o que produzia aquele
    vaivem em volta do destino. Por isso o proximo clique so sai depois
    de 'paradas' leituras seguidas na mesma coordenada. 'intervalo' fica
    so como piso entre dois cliques.

    Alvo fora do raio do minimapa vira clique na BORDA naquela direcao:
    anda o quanto der e a proxima iteracao continua.

    Quando um clique nao tira o personagem do lugar (parede no meio do
    caminho -- acontece, foi medido), o clique seguinte sai desviado
    alguns graus pro lado, alternando, ate destravar. Depois de
    'varredura_apos' cliques presos escala pra uma volta completa de
    cliques em torno do centro: desvio angular tira de parede
    atravessada, mas nao tira de canto -- de canto so se sai andando
    para tras.

    A tolerancia default e 2 e nao 8 porque o destino desta caminhada
    costuma ser o pe de um NPC: o clique nele depois e coordenada de
    TELA, e 8 unidades de mundo de erro ja movem o NPC na tela o
    bastante pro clique passar ao lado.
    """
    return Step(
        WALK_TO,
        (x, y, centro[0], centro[1], raio, escala, tolerancia, intervalo,
         paradas, varredura_apos),
        timeout=timeout,
        note=note,
    )


def esperar_parado(paradas: int = 3, timeout: float = 30.0,
                   note: str = "") -> Step:
    """
    Segura o roteiro ate o personagem parar de andar.

    Um clique de deslocamento longo (mapa-mundi, painel de lugares) nao
    tem duracao previsivel: depende do trajeto. Dormir um tempo fixo
    depois dele ou corta a caminhada no meio ou desperdica segundos em
    toda volta. Aqui a prova de que chegou e a coordenada da memoria
    parar de mudar por 'paradas' leituras seguidas.

    No timeout SEGUE em vez de abortar: parar o ciclo porque uma
    caminhada demorou mais que o esperado custa mais que tentar o passo
    seguinte.
    """
    return Step(WAIT_STOPPED, (paradas,), timeout=timeout, note=note)


def camera(zoom: float = 380.0, rotacao: float = 0.0, angulo: float = 40.0,
           note: str = "") -> Step:
    """
    Fixa a camera escrevendo os tres floats na memoria do cliente.

    Substitui o botao de view reset onde o que importa e o ponto de
    TELA: o botao devolve o angulo padrao mas nao mexe no zoom, e os
    clients usados aqui tem o limite de zoom liberado -- dois clients
    "resetados" mostram o mesmo NPC em pixels diferentes. Com os tres
    valores escritos, coordenada de tela volta a ser reproduzivel entre
    clients e entre sessoes.

    Os defaults (380 / 0 / 40) sao os do bot de referencia. Sem
    'memory' no contexto o passo avisa e segue -- camera errada erra
    cliques, mas parar o ciclo aqui nao conserta nada.
    """
    return Step(CAMERA, (zoom, rotacao, angulo), note=note)


def click_until_target(x: int, y: int, nome: str, timeout: float = 20.0,
                       intervalo: float = 1.0, botao: str = "left",
                       note: str = "") -> Step:
    """
    Clica num ponto ate o alvo selecionado ser o esperado.

    Confirmacao por MEMORIA, nao por imagem: o nome do alvo e lido do
    processo do jogo, entao nao depende de animacao, iluminacao nem do
    fundo do cenario -- que e onde o template matching de NPC quebra.
    Ou o clique selecionou o NPC certo, ou nao selecionou.

    So funciona com o personagem parado num ponto conhecido e a camera
    resetada: e isso que faz o NPC cair sempre no mesmo (x, y) da tela.

    Se estourar o timeout, segue mesmo assim -- os passos seguintes
    falham de forma visivel, o que e melhor que travar o ciclo aqui.
    """
    return Step(
        CLICK_UNTIL_TARGET,
        (x, y, nome, intervalo, botao),
        timeout=timeout,
        note=note,
    )


def pular_se(condicao: Callable, steps_ahead: int, note: str = "") -> Step:
    """
    Pula 'steps_ahead' passos quando a condicao diz que sim.

    A condicao recebe o char_info do tick e devolve bool -- ou seja,
    decide pela MEMORIA. O skip_if_color decide por PIXEL, que serve
    para caixa de dialogo aberta mas nao responde "o pet esta vivo?"
    nem "estou em Stone City?".

    Sem char_info a condicao nao roda e o passo NAO pula: pular por
    falta de leitura executaria o roteiro achando que a condicao estava
    satisfeita, que e o jeito errado de errar.
    """
    return Step(SKIP_IF, (condicao, steps_ahead), note=note)


def esperar_ate(condicao: Callable, timeout: float = 120.0,
                note: str = "") -> Step:
    """
    Segura o roteiro ate a condicao ficar verdadeira, ou ate o timeout.

    Mesma ideia do wait_color, so que lendo memoria: "HP em 100% e mana
    em 90%" e condicao de numero, nao de cor de pixel.

    Vencido o timeout o roteiro SEGUE, e nao aborta: parar o ciclo por
    causa de regeneracao lenta custa mais que entrar na cave com mana
    faltando.
    """
    return Step(WAIT_UNTIL, (condicao,), timeout=timeout, note=note)


def pular_se_template(template: str, steps_ahead: int, threshold: float = 0.85,
                      region=None, note: str = "") -> Step:
    """
    Pula 'steps_ahead' passos se o elemento ja esta na tela.

    E o irmao do skip_if_color para o que nao tem cor caracteristica:
    uma caixa de dialogo se reconhece pelo texto dentro dela, nao por um
    pixel. Serve para "tenta abrir o dialogo; se ja abriu, para de
    tentar".

    Sem vision_service o passo NAO pula -- mesma regra do pular_se: errar
    para o lado de tentar de novo custa um clique, errar para o lado de
    pular quebra o roteiro.
    """
    return Step(SKIP_IF_TEMPLATE, (template, steps_ahead, threshold, region),
                note=note)


def esperar_template(template: str, timeout: float = 15.0,
                     threshold: float = 0.85, region=None,
                     note: str = "") -> Step:
    """
    Espera um elemento aparecer, sem clicar nele.

    O click_template ja espera, mas clica no que achou -- e as vezes o
    que prova "a janela abriu" nao e o que se quer clicar. Esperar com
    tempo fixo no lugar disto foi o que fez a primeira versao da venda
    falhar: o roteiro dormia 1,5s apos pedir a lista, a janela demorava
    mais, e o clique do slot caia no dialogo atras -- sem erro nenhum,
    so sem vender.

    Vencido o timeout o roteiro SEGUE, como o wait_color: os passos
    seguintes erram em cima de tela errada, mas parar o ciclo por causa
    de um frame lento e pior.
    """
    return Step(WAIT_TEMPLATE, (template, threshold, region),
                timeout=timeout, note=note)


def call(fn: Callable, note: str = "") -> Step:
    """Delega a um callable do proprio script (logica que nao vira dado)."""
    return Step(CALL, (fn,), note=note)


def repeat(times: int, steps: list[Step]) -> list[Step]:
    """
    Expande um bloco repetido em passos literais.

    As repeticoes dos macros tem contagem constante, entao nao precisam
    de controle de fluxo em tempo de execucao -- expandir na montagem
    do roteiro mantem o runner simples.
    """
    saida: list[Step] = []
    for _ in range(times):
        saida.extend(steps)
    return saida


# =====================================================
# Contexto
# =====================================================

@dataclass
class StepContext:
    """O que um passo precisa para agir. Montado a cada tick."""

    hwnd: Any
    input_service: Any
    vision_service: Any = None
    char_info: Any = None
    target_info: Any = None
    # Leitor/escritor de memoria daquele cliente. Opcional: so o passo
    # de camera precisa dele -- posicao e vida chegam prontas em
    # char_info, montadas uma vez por tick pelo motor.
    memory: Any = None


# =====================================================
# Runner
# =====================================================

class StepRunner:
    """
    Executa uma lista de passos ao longo de varios ticks.

    Nao dorme: passos de espera anotam um prazo e os ticks seguintes
    apenas verificam se ja venceu.
    """

    def __init__(self, steps: list[Step], name: str = ""):
        self._steps = list(steps)
        self._name = name
        self._index = 0
        self._deadline: float | None = None
        self._step_started: float | None = None
        self._last_action: float = 0.0
        self._usados: int = 0
        self._ultima_posicao: tuple | None = None
        self._sem_progresso: int = 0
        # Leituras seguidas na mesma coordenada -- e o que diz "parou de
        # andar". Distinto de _sem_progresso, que conta CLIQUES que nao
        # tiraram o personagem do lugar.
        self._paradas: int = 0
        self._pos_do_clique: tuple | None = None

    # -------------------------------------------------
    # Estado
    # -------------------------------------------------

    @property
    def finished(self) -> bool:
        return self._index >= len(self._steps)

    @property
    def index(self) -> int:
        return self._index

    @property
    def total(self) -> int:
        return len(self._steps)

    @property
    def progress(self) -> str:
        return f"{self._index}/{len(self._steps)}"

    def reset(self):
        self._index = 0
        self._deadline = None
        self._step_started = None
        self._last_action = 0.0
        self._usados = 0
        self._ultima_posicao = None
        self._sem_progresso = 0
        self._paradas = 0
        self._pos_do_clique = None

    # -------------------------------------------------
    # Execucao
    # -------------------------------------------------

    def tick(self, ctx: StepContext) -> bool:
        """
        Tenta avancar um passo. Devolve True se agiu.

        Nunca bloqueia: se o passo atual e uma espera que ainda nao
        venceu, devolve False na hora e tenta de novo no proximo tick.
        """

        if self.finished:
            return False

        step = self._steps[self._index]

        if self._step_started is None:
            self._step_started = time.time()

        try:
            concluido = self._execute(step, ctx)
        except Exception:
            logger.exception(
                "Falha no passo %s de '%s' (%s)",
                self._index, self._name, step.kind,
            )
            self._advance()
            return True

        if concluido:
            self._advance()

        return True

    def _advance(self):
        self._index += 1
        self._deadline = None
        self._step_started = None
        self._usados = 0
        # Cada passo comeca do zero: sem isto, o instante do ultimo
        # clique de um passo atrasaria o primeiro clique do seguinte.
        self._last_action = 0.0
        self._ultima_posicao = None
        self._sem_progresso = 0
        self._paradas = 0
        self._pos_do_clique = None

    def _timed_out(self, step: Step) -> bool:
        if not step.timeout or self._step_started is None:
            return False
        return (time.time() - self._step_started) >= step.timeout

    def _execute(self, step: Step, ctx: StepContext) -> bool:
        """Devolve True quando o passo terminou."""

        kind = step.kind

        if kind == LEFT:
            x, y = step.args
            ctx.input_service.click(ctx.hwnd, x, y)
            return True

        if kind == RIGHT:
            x, y = step.args
            ctx.input_service.right_click(ctx.hwnd, x, y)
            return True

        if kind == DOUBLE_RIGHT:
            x, y = step.args
            ctx.input_service.double_right_click(ctx.hwnd, x, y)
            return True

        if kind == KEY:
            ctx.input_service.press_key(ctx.hwnd, step.args[0])
            return True

        if kind == KEY_DOWN:
            ctx.input_service.key_down(ctx.hwnd, step.args[0])
            return True

        if kind == KEY_UP:
            ctx.input_service.key_up(ctx.hwnd, step.args[0])
            return True

        if kind == WAIT:
            return self._do_wait(step)

        if kind == WAIT_COLOR:
            return self._do_wait_color(step, ctx)

        if kind == SKIP_IF_COLOR:
            x, y, color, tolerance, adiante = step.args
            if ctx.vision_service is not None and ctx.vision_service.pixel_matches(
                ctx.hwnd, x, y, color, tolerance
            ):
                logger.info("Condicao satisfeita; pulando %s passos", adiante)
                self._index += adiante
            return True

        if kind == SKIP_IF:
            condicao, adiante = step.args
            if ctx.char_info is not None and condicao(ctx.char_info):
                logger.info("Condicao de memoria satisfeita; pulando %s passos",
                            adiante)
                self._index += adiante
            return True

        if kind == WAIT_UNTIL:
            if self._timed_out(step):
                logger.warning("Timeout esperando condicao de memoria: %s",
                               step.note or "sem nota")
                return True
            return ctx.char_info is not None and bool(step.args[0](ctx.char_info))

        if kind == WAIT_TEMPLATE:
            template, threshold, region = step.args
            if ctx.vision_service is None:
                logger.warning("esperar_template sem vision_service; pulando")
                return True
            if ctx.vision_service.find_template(
                ctx.hwnd, template, threshold=threshold, region=region
            ) is not None:
                return True
            if self._timed_out(step):
                logger.warning("'%s' nao apareceu em %ss; seguindo",
                               template, step.timeout)
                return True
            return False

        if kind == SKIP_IF_TEMPLATE:
            template, adiante, threshold, region = step.args
            if ctx.vision_service is not None and ctx.vision_service.find_template(
                ctx.hwnd, template, threshold=threshold, region=region
            ) is not None:
                logger.info("'%s' ja esta na tela; pulando %s passos",
                            template, adiante)
                self._index += adiante
            return True

        if kind == CLICK_TEMPLATE:
            return self._do_click_template(step, ctx)

        if kind == WAIT_POSITION:
            return self._do_wait_position(step, ctx)

        if kind == USE_ALL_ITEMS:
            return self._do_use_all_items(step, ctx)

        if kind == ATTACK_UNTIL_DEAD:
            return self._do_attack(step, ctx)

        if kind == CLICK_UNTIL_TARGET:
            return self._do_click_until_target(step, ctx)

        if kind == WALK_TO:
            return self._do_walk_to(step, ctx)

        if kind == WAIT_STOPPED:
            return self._do_wait_stopped(step, ctx)

        if kind == CAMERA:
            return self._do_camera(step, ctx)

        if kind == CALL:
            return bool(step.args[0](ctx))

        logger.warning("Passo desconhecido, pulando: %s", kind)
        return True

    def _do_wait(self, step: Step) -> bool:
        if self._deadline is None:
            self._deadline = time.time() + step.args[0]
            return False
        return time.time() >= self._deadline

    def _do_wait_color(self, step: Step, ctx: StepContext) -> bool:
        x, y, color, tolerance = step.args

        if ctx.vision_service is None:
            logger.warning("wait_color sem vision_service; pulando")
            return True

        if ctx.vision_service.pixel_matches(ctx.hwnd, x, y, color, tolerance):
            return True

        if self._timed_out(step):
            # Seguir sem a confirmacao e ruim, mas travar pra sempre e
            # pior: o macro original ficava preso no while_not.
            logger.warning(
                "Cor esperada em (%s, %s) nao apareceu em %ss; seguindo mesmo assim",
                x, y, step.timeout,
            )
            return True

        return False

    def _do_click_template(self, step: Step, ctx: StepContext) -> bool:
        template, region, threshold, botao, obrigatorio, deslocamento = step.args

        if ctx.vision_service is None:
            logger.warning("click_template sem vision_service; pulando")
            return True

        posicao = ctx.vision_service.find_template(
            ctx.hwnd, template, threshold=threshold, region=region
        )

        if posicao is not None:
            x, y = posicao[0] + deslocamento[0], posicao[1] + deslocamento[1]
            if botao == "right":
                ctx.input_service.right_click(ctx.hwnd, x, y)
            elif botao == "double_right":
                ctx.input_service.double_right_click(ctx.hwnd, x, y)
            else:
                ctx.input_service.click(ctx.hwnd, x, y)
            logger.info("Clicou em '%s' (%s, %s)", template, x, y)
            return True

        if self._timed_out(step):
            if obrigatorio:
                logger.warning(
                    "'%s' nao apareceu em %ss; seguindo mesmo assim",
                    template, step.timeout,
                )
            return True

        return False

    def _do_wait_position(self, step: Step, ctx: StepContext) -> bool:
        alvo_x, alvo_y, tolerancia = step.args

        if ctx.char_info is None:
            logger.warning("wait_position sem char_info; pulando")
            return True

        x = getattr(ctx.char_info, "x", None)
        y = getattr(ctx.char_info, "y", None)

        if x is None or y is None:
            return True

        if abs(x - alvo_x) <= tolerancia and abs(y - alvo_y) <= tolerancia:
            logger.info("Chegou em (%s, %s)", alvo_x, alvo_y)
            return True

        if self._timed_out(step):
            logger.warning(
                "Nao chegou em (%s, %s) em %ss -- parou em (%s, %s)",
                alvo_x, alvo_y, step.timeout, x, y,
            )
            return True

        return False

    def _do_use_all_items(self, step: Step, ctx: StepContext) -> bool:
        template, region, maximo, intervalo, threshold = step.args

        if ctx.vision_service is None:
            logger.warning("use_all_items sem vision_service; pulando")
            return True

        if self._usados >= maximo:
            logger.info("Limite de %s itens usados atingido", maximo)
            self._usados = 0
            return True

        agora = time.time()

        if self._last_action and agora - self._last_action < intervalo:
            return False

        posicao = ctx.vision_service.find_template(
            ctx.hwnd, template, threshold=threshold, region=region
        )

        if posicao is None:
            if self._usados:
                logger.info("%s item(ns) usado(s)", self._usados)
            self._usados = 0
            self._last_action = 0.0
            return True

        x, y = posicao
        ctx.input_service.double_right_click(ctx.hwnd, x, y)

        self._usados += 1
        self._last_action = agora

        return False

    def _do_walk_to(self, step: Step, ctx: StepContext) -> bool:
        (alvo_x, alvo_y, cx, cy, raio, escala, tolerancia, intervalo,
         paradas, varredura_apos) = step.args

        if ctx.char_info is None:
            logger.warning("walk_to sem leitura de posicao; pulando")
            return True

        atual = (getattr(ctx.char_info, "x", 0), getattr(ctx.char_info, "y", 0))

        dx = alvo_x - atual[0]
        dy = alvo_y - atual[1]

        if math.hypot(dx, dy) <= tolerancia:
            return True

        # O timeout e conferido ANTES dos returns de espera: senao um
        # personagem preso em movimento (empurrado, preso em mob) nunca
        # chegaria ao ponto de reclicar e o passo ficaria eterno.
        if self._timed_out(step):
            logger.warning(
                "Nao chegou em (%s, %s) em %ss (parou em %s); seguindo",
                alvo_x, alvo_y, step.timeout, atual,
            )
            return True

        agora = time.time()

        # Parou de andar? So entao vale reclicar. Reclicar com o
        # personagem em movimento cancela o trajeto em curso.
        if atual == self._ultima_posicao:
            self._paradas += 1
        else:
            self._paradas = 0
            self._ultima_posicao = atual

        primeiro_clique = self._last_action == 0.0

        if not primeiro_clique:
            if self._paradas < paradas:
                return False
            if agora - self._last_action < intervalo:
                return False

        # O clique anterior tirou o personagem do lugar? Se nao, tem
        # parede no caminho -- repetir o mesmo clique daria no mesmo.
        if self._pos_do_clique is not None and atual == self._pos_do_clique:
            self._sem_progresso += 1
        else:
            self._sem_progresso = 0

        # Preso demais pro desvio angular resolver: sacode.
        if self._sem_progresso >= varredura_apos:
            self._varrer_em_circulo(ctx, cx, cy, raio, atual, agora)
            return False

        # Mundo -> pixel. O y inverte: subir no minimapa aumenta o y.
        px = dx / escala
        py = -dy / escala

        if self._sem_progresso:
            # Desvia alternando pros dois lados, abrindo o angulo a cada
            # tentativa presa, ate contornar o obstaculo.
            lado = 1 if self._sem_progresso % 2 else -1
            angulo = math.radians(30 * lado * ((self._sem_progresso + 1) // 2))
            px, py = (px * math.cos(angulo) - py * math.sin(angulo),
                      px * math.sin(angulo) + py * math.cos(angulo))

        # Alvo longe demais pro minimapa: clica na borda, naquela direcao.
        distancia = math.hypot(px, py)
        if distancia > raio:
            px, py = px * raio / distancia, py * raio / distancia

        ctx.input_service.right_click(ctx.hwnd, int(cx + px), int(cy + py))
        self._last_action = agora
        self._pos_do_clique = atual
        # Depois de clicar o personagem TEM que andar: zerar aqui e o
        # que impede o proximo tick de contar como "parado" a mesma
        # leitura que autorizou este clique.
        self._paradas = 0

        return False

    def _varrer_em_circulo(self, ctx: StepContext, cx: int, cy: int,
                           raio: int, atual: tuple, agora: float):
        """
        Ultimo recurso do destravamento: uma volta de cliques em torno do
        centro do minimapa.

        O desvio angular resolve parede ATRAVESSADA no caminho -- ele
        aponta para o lado e contorna. O que ele nao resolve e canto:
        preso entre duas paredes, toda direcao que ainda aponta para o
        alvo esbarra, e abrir o angulo aos poucos so testa o mesmo
        semicirculo. Aqui a volta e completa, incluindo o sentido
        oposto ao destino -- sair andando PARA TRAS costuma ser o unico
        jeito de sair do canto.

        O raio cresce a cada volta presa: perto do centro o clique anda
        pouco, e pouco pode nao ser o bastante pra escapar. Limitado ao
        raio do minimapa, senao o clique cai fora dele e vira clique no
        cenario.

        Oito cliques em rajada, sem esperar entre eles: cada um cancela
        o anterior, e o que vale e o ultimo -- a rajada existe pra que
        as direcoes bloqueadas sejam descartadas de graca e a livre
        prevaleca. Quem confere o resultado e o tick seguinte, que le a
        posicao de novo.
        """
        voltas = self._sem_progresso - 1
        r = min(raio, 10 + 2 * voltas)

        diagonal = int(r * 0.7)
        pontos = [
            (r, 0), (diagonal, -diagonal), (0, -r), (-diagonal, -diagonal),
            (-r, 0), (-diagonal, diagonal), (0, r), (diagonal, diagonal),
        ]

        logger.info(
            "Preso em %s apos %s cliques sem sair do lugar; "
            "varrendo em circulo (raio %s)",
            atual, self._sem_progresso, r,
        )

        for dx, dy in pontos:
            ctx.input_service.right_click(ctx.hwnd, int(cx + dx), int(cy + dy))

        self._last_action = agora
        self._pos_do_clique = atual
        self._paradas = 0

    def _do_wait_stopped(self, step: Step, ctx: StepContext) -> bool:
        (paradas,) = step.args

        if ctx.char_info is None:
            logger.warning("esperar_parado sem leitura de posicao; pulando")
            return True

        atual = (getattr(ctx.char_info, "x", 0), getattr(ctx.char_info, "y", 0))

        if atual == self._ultima_posicao:
            self._paradas += 1
        else:
            self._paradas = 0
            self._ultima_posicao = atual

        if self._paradas >= paradas:
            return True

        if self._timed_out(step):
            logger.warning(
                "Personagem ainda andando depois de %ss (em %s); seguindo",
                step.timeout, atual,
            )
            return True

        return False

    def _do_camera(self, step: Step, ctx: StepContext) -> bool:
        zoom, rotacao, angulo = step.args

        if ctx.memory is None:
            logger.warning("camera sem acesso a memoria; pulando")
            return True

        if not ctx.memory.escrever_camera(zoom, rotacao, angulo):
            logger.warning(
                "Nao foi possivel escrever a camera (zoom=%s rot=%s ang=%s)",
                zoom, rotacao, angulo,
            )

        return True

    def _do_click_until_target(self, step: Step, ctx: StepContext) -> bool:
        x, y, nome, intervalo, botao = step.args

        atual = (getattr(ctx.target_info, "name", "") or "").strip()

        if atual.lower() == nome.strip().lower():
            return True

        agora = time.time()

        # Espaca os cliques: o jogo leva alguns quadros pra registrar a
        # selecao, e clicar a cada tick so empilharia clique em cima de
        # clique sem dar tempo do alvo aparecer na memoria.
        if agora - self._last_action >= intervalo:
            if botao == "right":
                ctx.input_service.right_click(ctx.hwnd, x, y)
            elif botao == "double_right":
                ctx.input_service.double_right_click(ctx.hwnd, x, y)
            else:
                ctx.input_service.click(ctx.hwnd, x, y)
            self._last_action = agora

        if self._timed_out(step):
            logger.warning(
                "Alvo '%s' nao foi selecionado em %ss (alvo atual: %r); "
                "seguindo mesmo assim",
                nome, step.timeout, atual,
            )
            return True

        return False

    def _do_attack(self, step: Step, ctx: StepContext) -> bool:
        skills, intervalo, aoe_key, aoe_ate_mana, super_key = step.args

        alvo_morto = (
            ctx.target_info is None
            or not getattr(ctx.target_info, "name", "")
            or getattr(ctx.target_info, "hp_pct", 0) <= 0
        )

        if alvo_morto and self._step_started is not None:
            # So considera concluido depois de ter batido pelo menos uma
            # vez: no primeiro tick o alvo ainda nem foi selecionado.
            if self._last_action > 0:
                logger.info("Alvo derrubado")
                self._last_action = 0.0
                self._usados = 0
                return True

        if self._timed_out(step):
            logger.warning(
                "Alvo nao caiu em %ss; seguindo pro proximo passo", step.timeout
            )
            self._last_action = 0.0
            self._usados = 0
            return True

        agora = time.time()

        if agora - self._last_action < intervalo:
            return False

        if not skills:
            return True

        # TAB seleciona o alvo mais proximo.
        ctx.input_service.press_key(ctx.hwnd, "TAB")

        # Super skill uma vez so, na abertura.
        if super_key and self._usados == 0:
            ctx.input_service.press_key(ctx.hwnd, super_key)
            self._usados = 1
            self._last_action = agora
            return False

        ctx.input_service.press_key(ctx.hwnd, self._proxima_skill(
            skills, intervalo, aoe_key, aoe_ate_mana, ctx, agora
        ))

        self._last_action = agora

        return False

    @staticmethod
    def _proxima_skill(skills, intervalo, aoe_key, aoe_ate_mana, ctx, agora) -> str:
        """
        Escolhe a tecla desta rodada.

        O AOE so entra enquanto a mana estiver ACIMA do limite: ele
        custa caro, e ficar sem mana no meio do boss e pior que matar
        mais devagar.
        """
        rotacao = list(skills)

        if aoe_key and aoe_ate_mana is not None:
            mana = getattr(ctx.char_info, "resource_pct", 0.0) if ctx.char_info else 0.0
            if mana > aoe_ate_mana:
                rotacao.append(aoe_key)

        indice = int(agora / max(intervalo, 0.01)) % len(rotacao)

        return rotacao[indice]
