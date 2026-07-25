from src.domain.workflows.base_workflow import BaseWorkflow

from src.shared.templates import CharacterTemplates, GameTemplates
from src.shared.delays import Delays


class CharacterWorkflow(BaseWorkflow):
    """
    Workflow responsável por:
    - Aguardar a fila do servidor (se houver) até a tela de seleção
      de personagem aparecer. Esta etapa pode demorar bastante tempo
      e não deve ser tratada como falha só por estar demorando.
    - Entrar no jogo com o personagem.
    - Confirmar que o jogo efetivamente carregou (HUD visível).
    """

    def __init__(
        self,
        client,
        settings,
        logger=None,
    ):
        super().__init__(
            client,
            settings,
            logger,
        )

        self.enter_game_button = None

    # =====================================================
    # Fluxo principal
    # =====================================================

    def execute(self):

        self.wait_character_screen()

        self.enter_game()

        self.wait_game_loaded()

    # =====================================================
    # Fila / tela de personagem
    # =====================================================

    def wait_character_screen(self):

        self.log(
            "Aguardando tela de seleção de personagem "
            "(pode demorar se houver fila no servidor)..."
        )

        self.enter_game_button = self.wait_template_patient(
            CharacterTemplates.ENTER_GAME_BUTTON,
            timeout=self.settings.timeout_queue,
            poll_interval=Delays.QUEUE_POLL_INTERVAL,
            heartbeat_interval=Delays.QUEUE_HEARTBEAT_INTERVAL,
            waiting_message="Ainda em fila / carregando...",
        )

        if not self.enter_game_button:
            raise TimeoutError(
                "Tela de seleção de personagem não apareceu "
                f"(timeout de fila de {int(self.settings.timeout_queue)}s excedido)."
            )

        self.log(
            f"Botão de entrar no jogo localizado em {self.enter_game_button}"
        )

    # =====================================================
    # Entrar no jogo
    # =====================================================

    def enter_game(self):

        self.log("Entrando no jogo...")

        self.click(
            self.enter_game_button
        )

        self.wait(
            Delays.AFTER_ENTER_GAME
        )

    # =====================================================
    # Confirmação de carregamento
    # =====================================================

    def wait_game_loaded(self):

        self.log("Confirmando que o jogo carregou...")

        hud = self.wait_template(
            GameTemplates.HUD,
            timeout=self.settings.timeout_game_load,
        )

        if not hud:
            raise TimeoutError(
                "Não foi possível confirmar que o jogo carregou "
                "(HUD não encontrado)."
            )

        self.log("Jogo carregado com sucesso!")