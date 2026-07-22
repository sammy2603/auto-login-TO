from __future__ import annotations

from src.app.container import ServiceContainer


class Application:
    """
    Ponto de entrada da aplicação.

    Responsável por inicializar os componentes principais e controlar
    o ciclo de vida da aplicação.
    """

    def __init__(self):
        self.container = ServiceContainer()

    def start(self):
        """
        Inicia a aplicação.
        """
        print("Inicializando aplicação...")

        self.container.engine.run()

    def shutdown(self):
        """
        Liberação de recursos da aplicação.
        """

        print("Finalizando aplicação...")

        # Futuramente:
        #
        # self.container.window_service.disconnect()
        # self.container.logger.close()
        #
        # etc.