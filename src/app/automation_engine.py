from src.domain.workflows.login_workflow import LoginWorkflow


class AutomationEngine:

    def __init__(self):
        self.login_workflow = LoginWorkflow()

    def run(self):
        print("Automation Engine initialized.")
        self.login_workflow.execute()