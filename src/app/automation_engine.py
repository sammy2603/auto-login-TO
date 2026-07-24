class AutomationEngine:
    """
    Responsável por orquestrar os workflows da aplicação.
    """

    def __init__(
        self,
        login_workflow,
        server_workflow,
    ):
        self.login_workflow = login_workflow
        self.server_workflow = server_workflow

    def run(self):

        print("Automation Engine iniciado.")

        self.login_workflow.execute()

        self.server_workflow.execute()

        print("Fluxo de login concluído.")