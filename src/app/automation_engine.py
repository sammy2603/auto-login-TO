from src.domain.exceptions import ServerConnectionInterrupted
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class AutomationEngine:
    """
    Responsável por orquestrar os workflows da aplicação.
    """

    def __init__(
        self,
        login_workflow,
        server_workflow,
        character_workflow,
        max_connection_retries: int = 5,
    ):
        self.login_workflow = login_workflow
        self.server_workflow = server_workflow
        self.character_workflow = character_workflow
        self.max_connection_retries = max_connection_retries

    def run(self):

        logger.info("Automation Engine iniciado.")

        self.login_workflow.execute()

        self._run_server_and_character()

        logger.info("Fluxo de login concluído.")

    def _run_server_and_character(self):
        """
        Roda a seleção de servidor + entrada com o personagem.

        Se a conexão for interrompida (servidor indisponível, volta
        pra tela de login), refaz o login e tenta de novo, até o
        limite de tentativas configurado.
        """

        attempt = 0

        while True:

            try:
                self.server_workflow.execute()
                self.character_workflow.execute()
                return

            except ServerConnectionInterrupted as exc:

                attempt += 1

                logger.warning("%s", exc)

                if attempt > self.max_connection_retries:
                    logger.error(
                        "Número máximo de tentativas (%s) excedido. Desistindo.",
                        self.max_connection_retries,
                    )
                    raise

                logger.info(
                    "Tentando novamente (%s/%s)...",
                    attempt,
                    self.max_connection_retries,
                )

                self.login_workflow.retry_login()