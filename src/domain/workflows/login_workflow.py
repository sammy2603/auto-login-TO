from src.domain.workflows.base_workflow import BaseWorkflow
from src.services.game.game_client import GameClient


class LoginWorkflow(BaseWorkflow):

    def __init__(self, client: GameClient):
        self.client = client

    def execute(self):

        self.client.connect()
        print(self.client.client_size())



        self.client.login()

        self.client.select_server()

        self.client.wait_game_loaded()
    
    def wait_template(
        self,
        template,
        timeout=30,
):
        return self.vision.wait_template(
            hwnd=self.hwnd,
            template=template,
            timeout=timeout,
    )