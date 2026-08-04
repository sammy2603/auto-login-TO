from src.domain.workflows.base_workflow import BaseWorkflow

from src.shared.templates import CharacterTemplates, GameTemplates, LoginTemplates
from src.shared.delays import Delays
from src.shared.character_slots import CHARACTER_SLOT_POSITIONS
from src.domain.exceptions import ServerConnectionInterrupted


class CharacterWorkflow(BaseWorkflow):
    """
    Workflow responsável por:
    - Aguardar a fila do servidor (se houver) até a tela de seleção
      de personagem aparecer. Esta etapa pode demorar bastante tempo
      e não deve ser tratada como falha só por estar demorando.
    - Entrar no jogo com o personagem.
    - Confirmar que o jogo efetivamente carregou (HUD visível).
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

        self.enter_game_button = None

    # =====================================================
    # Fluxo principal
    # =====================================================

    def execute(self):

        self.wait_character_screen()

        self.select_character()

        self.enter_game()

        self.wait_game_loaded()

    # =====================================================
    # Fila / tela de personagem
    # =====================================================

    def wait_character_screen(self):
        """
        Espera SEM LIMITE DE TEMPO.

        Fila de servidor dura o que durar -- às vezes horas. Qualquer
        timeout que a gente escolhesse seria um palpite, e estourá-lo
        transformaria "a fila está longa" (situação normal) em erro,
        derrubando um login que ia dar certo se tivesse esperado mais.
        Então a única pergunta é: o botão de entrar no jogo apareceu?

        A espera não é cega: se a tela de LOGIN reaparecer, o servidor
        caiu e nos jogou pra fora -- aí não adianta esperar, é caso de
        refazer o login. Reconhecemos pelo próprio campo de usuário, sem
        template de mensagem de erro: qual popup apareceu não muda o que
        vamos fazer.
        """

        self.log(
            "Aguardando tela de seleção de personagem "
            "(sem limite de tempo -- a fila do servidor pode durar horas)..."
        )

        label, position = self.wait_for_any_template_patient(
            templates={
                "character_screen": (
                    CharacterTemplates.ENTER_GAME_BUTTON,
                    (0, 0),
                ),
                "login_screen": (
                    LoginTemplates.USERNAME,
                    (0, 0),
                ),
            },
            timeout=None,
            poll_interval=Delays.QUEUE_POLL_INTERVAL,
            heartbeat_interval=Delays.QUEUE_HEARTBEAT_INTERVAL,
            waiting_message="Ainda em fila / carregando...",
        )

        if label == "login_screen":
            self.log(
                "Voltamos pra tela de login: o servidor ficou "
                "indisponível durante a entrada."
            )
            self.dismiss_dialogs()
            raise ServerConnectionInterrupted(
                "Conexão interrompida ao entrar no servidor "
                f"'{self.settings.server_name}'."
            )

        self.enter_game_button = position

        self.log(
            f"Botão de entrar no jogo localizado em {self.enter_game_button}"
        )

    # =====================================================
    # Seleção do personagem (slot esquerda/centro/direita)
    # =====================================================

    def select_character(self):

        slot = self.settings.character_slot

        position = CHARACTER_SLOT_POSITIONS.get(slot)

        if not position:
            raise ValueError(
                f"Slot de personagem inválido: {slot!r}. "
                f"Use um de: {list(CHARACTER_SLOT_POSITIONS.keys())}"
            )

        self.log(
            f"Selecionando personagem (slot {slot}, posição {position})..."
        )

        self.click(position)

        self.wait(Delays.AFTER_CLICK)

    # =====================================================
    # Entrar no jogo
    # =====================================================

    def enter_game(self):

        self.log("Entrando no jogo...")

        self.click(
            self.enter_game_button
        )

        self.wait(
            Delays.AFTER_ENTER_GAME
        )

    # =====================================================
    # Confirmação de carregamento
    # =====================================================

    def wait_game_loaded(self):

        self.log("Confirmando que o jogo carregou...")

        hud = self.wait_template(
            GameTemplates.HUD,
            timeout=self.settings.timeout_game_load,
        )

        if not hud:
            raise TimeoutError(
                "Não foi possível confirmar que o jogo carregou "
                "(HUD não encontrado)."
            )

        # Renomeia de novo aqui: o jogo pode ter reescrito o título em
        # alguma transição entre a seleção de servidor e o carregamento
        # final (tela de personagem, entrada no mundo, etc).
        self.rename_window()

        self.log("Jogo carregado com sucesso!")