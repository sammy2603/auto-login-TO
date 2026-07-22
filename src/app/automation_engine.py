from __future__ import annotations


class AutomationEngine:
    """
    Responsável por orquestrar os workflows da aplicação.

    O Engine não contém regras de negócio.
    Ele apenas executa os workflows registrados.
    """

    def __init__(self, login_workflow, logger=None):
        self.login_workflow = login_workflow
        self.logger = logger

    def run(self):
        print("Automation Engine iniciado.")

        self.login_workflow.execute()