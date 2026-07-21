from src.domain.workflows.base_workflow import BaseWorkflow
from src.services.game.game_client import GameClient


class LoginWorkflow(BaseWorkflow):

    def __init__(self, client: GameClient):
        self.client = client

    def execute(self):

        self.client.connect()
        print(self.client.hwnd)


        self.client.login()

        self.client.select_server()

        self.client.wait_game_loaded()