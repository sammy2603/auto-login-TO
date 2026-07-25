from __future__ import annotations

from src.config.settings import Settings

from src.infrastructure.window.service import WindowService
from src.infrastructure.vision.service import VisionService
from src.infrastructure.input.service import InputService
from src.services.game.game_session import GameSession
from src.infrastructure.game.launcher import GameLauncher

from src.services.game.game_client import GameClient

from src.domain.workflows.login_workflow import LoginWorkflow
from src.domain.workflows.server_workflow import ServerWorkflow
from src.domain.workflows.character_workflow import CharacterWorkflow

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
        # Sessão do jogo
        #-----------------------------------------------------------------
      
        self.session = GameSession()

        # ------------------------------------------------------------------
        # Infraestrutura
        # ------------------------------------------------------------------

        self.window = WindowService()
        self.vision = VisionService(window_service=self.window)
        self.input = InputService()
        self.launcher = GameLauncher()

        # ------------------------------------------------------------------
        # Cliente do jogo
        # ------------------------------------------------------------------


        self.game_client = GameClient(
            session=self.session,
            launcher=self.launcher,
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
        self.server_workflow = ServerWorkflow(
            client=self.game_client,
            settings=self.settings,
        )
        self.character_workflow = CharacterWorkflow(
            client=self.game_client,
            settings=self.settings,
        )
        # ------------------------------------------------------------------
        # Engine
        # ------------------------------------------------------------------

        self.engine = AutomationEngine(
            login_workflow=self.login_workflow,
            server_workflow=self.server_workflow,
            character_workflow=self.character_workflow,
            max_connection_retries=self.settings.max_connection_retries,
        )