from src.domain.workflows.base_workflow import BaseWorkflow

from src.shared.templates import ServerTemplates
from src.shared.delays import Delays


class ServerWorkflow(BaseWorkflow):
    """
    Workflow responsável pela seleção do servidor.
    """

    def __init__(
        self,
        client,
        settings,
        logger=None,
    ):
        super().__init__(
            client,
            settings,
            logger,
        )

        self.server_position = None

    # =====================================================
    # Fluxo principal
    # =====================================================

    def execute(self):

        self.wait_server_screen()

        self.select_server()

        self.confirm_server()

        self.finish()

    # =====================================================
    # Tela de servidores
    # =====================================================

    def wait_server_screen(self):

        self.log("Aguardando tela de servidores...")

        self.server_position = self.wait_template(
            ServerTemplates.server(
                self.settings.server_name
            ),
            timeout=self.settings.timeout_server_selection,
        )

        if not self.server_position:
            raise TimeoutError(
                f"Servidor '{self.settings.server_name}' não encontrado."
            )

        self.log(
            f"Servidor localizado em {self.server_position}"
        )

    # =====================================================
    # Seleção
    # =====================================================

    def select_server(self):

        self.log(
            f"Selecionando servidor '{self.settings.server_name}'..."
        )

        self.click(
            self.server_position
        )

        self.wait(
            Delays.AFTER_SERVER_SELECT
        )

    # =====================================================
    # Confirmação
    # =====================================================

    def confirm_server(self):

        self.log("Verificando necessidade de confirmação...")

        confirm_button = self.find_template(
            ServerTemplates.CONFIRM_BUTTON
        )

        if not confirm_button:
            self.log("Nenhum botão de confirmação encontrado.")
            return

        self.log(
            f"Botão de confirmação localizado em {confirm_button}"
        )

        self.click(
            confirm_button
        )

        self.wait(
            Delays.AFTER_SERVER_CONFIRM
        )

        self.log("Servidor confirmado.")

    # =====================================================
    # Finalização
    # =====================================================

    def finish(self):

        self.log("Seleção de servidor concluída.")