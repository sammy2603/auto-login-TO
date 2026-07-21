from src.app.automation_engine import AutomationEngine


class Application:

    def __init__(self):
        self.engine = AutomationEngine()

    def initialize(self):
        print("Initializing application...")

    def start(self):
        self.initialize()
        self.engine.run()

    def shutdown(self):
        print("Application closed.")