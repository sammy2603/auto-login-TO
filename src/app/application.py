from src.app.container import ServiceContainer
from src.app.automation_engine import AutomationEngine


class Application:

    def __init__(self):
        self.container = ServiceContainer()
        self.engine = AutomationEngine(self.container)

    def start(self):
        print("Inicializando aplicação...")
        self.engine.run()

    def shutdown(self):
        print("Finalizando aplicação...")