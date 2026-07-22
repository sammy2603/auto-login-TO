class AutomationEngine:

    def __init__(self, login_workflow):
        self.login_workflow = login_workflow

    def run(self):
        self.logger.info("Automation Engine iniciado.")
        self.login_workflow.execute()