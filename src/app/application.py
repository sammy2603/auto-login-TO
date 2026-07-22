from src.app.container import ServiceContainer


class Application:

    def __init__(self):
        self.container = ServiceContainer()

    def start(self):
        self.container.engine.run()

    def shutdown(self):
        """
        Liberação de recursos da aplicação.
        """
        pass