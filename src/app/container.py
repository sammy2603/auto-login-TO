from src.infrastructure.window.service import WindowService
from src.infrastructure.vision.service import VisionService
from src.infrastructure.input.service import InputService
from src.services.game.game_client import GameClient


class ServiceContainer:

    def __init__(self):
        self.window = WindowService()
        self.vision = VisionService()
        self.input = InputService()
        self.license_service = LicenseService()
        self.update_service = UpdateService()
        self.telemetry_service = TelemetryService()

        self.game_client = GameClient(
            window_service=self.window,
            vision_service=self.vision,
            input_service=self.input,
        )
        