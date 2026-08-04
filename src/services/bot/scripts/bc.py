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
    "member_name": "",
    # Marca este client como o que reconstitui o team entre as runs.
    "reseter": False,

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
    "team_key": "F12",

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
    "comprar_pot": True,
    "vender": True,
    "usar_courage": True,
    "repetir_ciclo": False,

    # =========================================================
    # Ajustes finos
    # =========================================================
    "rodadas_de_compra": 16,
    "compras_por_rodada": 24,
    "tentativas_de_entrada": 3,
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
        self.stats = BCStats()
        self._ultimo_consumo = 0.0

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
        self._ultimo_consumo = 0.0

        if self._config.get("auto_reset_stats"):
            self.stats.zerar()

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

            logger.info("Fase '%s' iniciada (%s passos)", self._fase, len(passos))

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
        )

        agiu = self._runner.tick(ctx)

        if self._runner.finished:
            self._fase = self._proxima_fase()
            self._runner = None

        return agiu
