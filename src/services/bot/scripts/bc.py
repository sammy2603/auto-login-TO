# -*- coding: utf-8 -*-
"""
Battle Cave -- ciclo completo.

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

from src.infrastructure.logging import get_logger
from src.services.bot.scripts import bc_steps
from src.services.bot.step_runner import StepContext, StepRunner

logger = get_logger(__name__)


DEFAULT_CONFIG = {
    # --- Teclas (todas a criterio do usuario) ---
    "skills": ["1", "2", "3", "4"],
    "mount_key": "0",
    "stone_key": "9",
    "inventory_key": "I",
    "team_key": "F12",

    # --- Ciclo ---
    # Quantas runs na cave antes de voltar de fato pra cidade. Com 1,
    # volta logo apos o primeiro boss (comportamento do macro
    # original). Acima disso, reseta o team e repete a run.
    "runs_por_ciclo": 1,
    "repetir_ciclo": False,

    # --- Etapas opcionais ---
    "comprar_pot": True,
    "vender": True,
    "usar_courage": True,

    # --- Ajustes finos ---
    "rodadas_de_compra": 16,
    "compras_por_rodada": 24,
    "tentativas_de_entrada": 3,
    "intervalo_caminhada": 2.0,
    "intervalo_skill": 1.0,
    "timeout_boss": 300.0,

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
}


class BCScript:
    """
    Battle Cave -- entra na cave, mata o boss e volta.

    O roteiro vive em bc_steps.py como dados; aqui fica so a maquina de
    estados que decide qual fase montar em seguida.
    """

    name = "BC"

    FASE_PREPARO = "preparo"
    FASE_RUN = "run"
    FASE_RESET = "reset"
    FASE_RETORNO = "retorno"
    FASE_FIM = "fim"

    _MONTADORES = {
        FASE_PREPARO: "_montar_preparo",
        FASE_RUN: "_montar_run",
        FASE_RESET: "_montar_reset",
        FASE_RETORNO: "_montar_retorno",
    }

    def __init__(self, config: dict | None = None):
        self._config = {**DEFAULT_CONFIG, **(config or {})}
        self._fase = self.FASE_PREPARO
        self._runner: StepRunner | None = None
        self._runs_feitas = 0
        self._anunciou_fim = False

    # =====================================================
    # Configuracao / estado
    # =====================================================

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
        self._fase = self.FASE_PREPARO
        self._runner = None
        self._runs_feitas = 0
        self._anunciou_fim = False

    # =====================================================
    # Montagem das fases
    # =====================================================

    def _montar_preparo(self) -> list:
        cfg = self._config
        passos = []
        passos += bc_steps.ajustes_iniciais(cfg)
        passos += bc_steps.convidar_team(cfg)
        passos += bc_steps.montar(cfg)
        passos += bc_steps.ir_para_ghost(cfg)

        if cfg.get("comprar_pot"):
            passos += bc_steps.comprar_pot(cfg)

        if cfg.get("vender"):
            passos += bc_steps.vender(cfg)

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
        passos += bc_steps.atacar_boss(cfg)
        passos += bc_steps.usar_courage(cfg)
        return passos

    def _montar_reset(self) -> list:
        """
        Entre uma run e outra: reconstitui o team pra entrar de novo,
        sem passar pela cidade.
        """
        cfg = self._config
        return [
            *bc_steps.ajustes_iniciais(cfg),
            *bc_steps.convidar_team(cfg),
        ]

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
        if self._fase == self.FASE_PREPARO:
            return self.FASE_RUN

        if self._fase == self.FASE_RUN:
            self._runs_feitas += 1
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
            logger.info("Fase '%s' iniciada (%s passos)", self._fase, len(passos))

        return True

    # =====================================================
    # Protocolo BotScript
    # =====================================================

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:

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
        )

        agiu = self._runner.tick(ctx)

        if self._runner.finished:
            self._fase = self._proxima_fase()
            self._runner = None

        return agiu
