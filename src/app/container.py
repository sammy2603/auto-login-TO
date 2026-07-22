from __future__ import annotations

from src.config.settings import Settings

from src.infrastructure.window.service import WindowService
from src.infrastructure.vision.service import VisionService
from src.infrastructure.input.service import InputService

from src.services.game.game_client import GameClient

from src.domain.workflows.login_workflow import LoginWorkflow

from src.app.automation_engine import AutomationEngine


class ServiceContainer:
    """
    Composition Root da aplicação.

    Responsável por criar e conectar todas as dependências.
    """

    def __init__(self):

        # ------------------------------------------------------------------
        # Configurações
        # ------------------------------------------------------------------

        self.settings = Settings()

        # ------------------------------------------------------------------
        # Infraestrutura
        # ------------------------------------------------------------------

        self.window = WindowService()
        self.vision = VisionService()
        self.input = InputService()

        # ------------------------------------------------------------------
        # Cliente do jogo
        # ------------------------------------------------------------------

        self.game_client = GameClient(
            window_service=self.window,
            vision_service=self.vision,
            input_service=self.input,
        )

        # ------------------------------------------------------------------
        # Workflows
        # ------------------------------------------------------------------

        self.login_workflow = LoginWorkflow(
            client=self.game_client,
            settings=self.settings,
        )

        # ------------------------------------------------------------------
        # Engine
        # ------------------------------------------------------------------

        self.engine = AutomationEngine(
            login_workflow=self.login_workflow
        )