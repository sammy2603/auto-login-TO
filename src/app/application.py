from __future__ import annotations

from src.app.container import ServiceContainer
from src.config.settings import Settings


class Application:
    """
    Ponto de entrada da aplicação.

    Responsável por inicializar os componentes principais e controlar
    o ciclo de vida da aplicação.
    """

    def __init__(self, settings: Settings | None = None):
        self.container = ServiceContainer(settings=settings)

    def start(self):
        """
        Inicia a aplicação.
        """

        self.container.engine.run()

    def shutdown(self):
        """
        Liberação de recursos da aplicação.
        """

        print("Finalizando aplicação...")
        pass
        # Futuramente:
        #
        # self.container.window_service.disconnect()
        # self.container.logger.close()
        #
        # etc.