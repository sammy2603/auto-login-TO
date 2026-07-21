from src.domain.workflows.login_workflow import LoginWorkflow


class AutomationEngine:

    def __init__(self, container):
        self.login_workflow = LoginWorkflow(
            container.game_client
        )

    def run(self):
        print("Automation Engine iniciado.")
        self.login_workflow.execute()