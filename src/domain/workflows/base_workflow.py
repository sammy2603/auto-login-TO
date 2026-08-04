import time

from src.infrastructure.logging import get_logger
from src.shared.delays import Delays
from src.shared.keys import Keys


class BaseWorkflow:
    """
    Classe base para todos os workflows da aplicação.

    Centraliza funcionalidades compartilhadas entre os fluxos,
    mantendo os workflows focados apenas na regra de negócio.
    """

    def __init__(
        self,
        client,
        settings,
        logger=None,
    ):
        self.client = client
        self.settings = settings

        # 'logger' continua injetável (útil pra teste), mas o default
        # deixou de ser print: cada workflow ganha o seu logger, o que
        # preserva a identidade que o prefixo "[LoginWorkflow]" dava e
        # ainda permite calar um workflow específico por nome.
        self.logger = logger or get_logger(
            f"workflows.{self.__class__.__name__}"
        )

    # =====================================================
    # Logging
    # =====================================================

    def log(self, message: str):
        """
        Escreve uma mensagem de log.
        """
        self.logger.info(message)

    def rename_window(self):
        """
        Renomeia a janela com o apelido da conta. Precisa ser chamado
        de novo depois de qualquer transição de tela em que o próprio
        jogo reescreve o título da janela (ex: ao selecionar servidor),
        já que isso apaga o nome que colocamos antes.
        """

        label = self.settings.account_label or self.settings.username

        self.client.rename_window(
            f"{label}"
        )

    # =====================================================
    # Tempo
    # =====================================================

    def wait(self, seconds: float):
        """
        Aguarda um intervalo.
        """
        self.client.wait(seconds)

    # =====================================================
    # Vision
    # =====================================================

    def wait_template(
        self,
        template,
        timeout=None,
        offset=(0, 0),
    ):
        """
        Aguarda um template aparecer. Se 'offset' for informado, soma
        (dx, dy) à posição encontrada antes de retornar -- útil quando
        o template recortado é um rótulo/borda ao lado do campo real.
        """

        if timeout is None:
            timeout = self.settings.timeout_login_screen

        position = self.client.wait_template(
            template,
            timeout=timeout,
            threshold=self.settings.match_threshold,
        )

        if position is None:
            return None

        return self._apply_offset(position, offset)

    def find_template(
        self,
        template,
        offset=(0, 0),
    ):
        """
        Procura um template. Se 'offset' for informado, soma (dx, dy)
        à posição encontrada antes de retornar.
        """

        position = self.client.find_template(
            template,
            threshold=self.settings.match_threshold,
        )

        if position is None:
            return None

        return self._apply_offset(position, offset)

    @staticmethod
    def _apply_offset(position, offset):
        x, y = position
        dx, dy = offset
        return (x + dx, y + dy)

    def wait_template_patient(
        self,
        template,
        timeout,
        offset=(0, 0),
        poll_interval=3.0,
        heartbeat_interval=15.0,
        waiting_message="Ainda aguardando...",
    ):
        """
        Espera um template aparecer, mas de forma "paciente": feita
        pra esperas longas e incertas (ex: fila de servidor), onde não
        faz sentido ficar tentando a cada 0.5s nem falhar rápido.

        'timeout=None' espera indefinidamente.

        Loga uma mensagem periódica (a cada 'heartbeat_interval'
        segundos) pra deixar claro que o bot ainda está rodando, não
        travado.
        """

        label, position = self.wait_for_any_template_patient(
            {"target": (template, offset)},
            timeout=timeout,
            poll_interval=poll_interval,
            heartbeat_interval=heartbeat_interval,
            waiting_message=waiting_message,
        )

        return position if label else None

    def wait_for_any_template_patient(
        self,
        templates,
        timeout,
        poll_interval=3.0,
        heartbeat_interval=15.0,
        waiting_message="Ainda aguardando...",
    ):
        """
        Como wait_template_patient, mas observa VÁRIOS templates ao
        mesmo tempo -- útil quando mais de uma tela pode aparecer em
        seguida (ex: "chegou na tela de personagem" OU "apareceu um
        popup de erro").

        'templates' é um dict: {label: (template_name, offset)}.

        'timeout=None' espera indefinidamente -- é o caso da fila de
        servidor, que pode durar horas: qualquer limite que a gente
        escolhesse seria arbitrário e transformaria "a fila está longa"
        em erro.

        Retorna (label, position) do primeiro que aparecer, ou
        (None, None) se o timeout for atingido.
        """

        start = time.time()
        last_heartbeat = start

        while True:
            for label, (template_name, offset) in templates.items():
                position = self.find_template(template_name, offset=offset)

                if position:
                    return label, position

            now = time.time()
            elapsed = now - start

            if timeout is not None and elapsed >= timeout:
                return None, None

            if now - last_heartbeat >= heartbeat_interval:
                limite = (
                    "sem limite de tempo" if timeout is None
                    else f"timeout em {int(timeout)}s"
                )
                self.log(
                    f"{waiting_message} ({int(elapsed)}s decorridos, {limite})"
                )
                last_heartbeat = now

            time.sleep(poll_interval)

    def template_exists(
        self,
        template,
    ):
        """
        Verifica se um template existe.
        """

        return self.client.template_exists(
            template,
            threshold=self.settings.match_threshold,
        )

    # =====================================================
    # Input
    # =====================================================

    def fill(
        self,
        position,
        text,
    ):
        """
        Preenche um campo.
        """

        self.client.fill_field(
            position,
            text,
        )

    def clear_current(
        self,
        max_chars: int = 30,
    ):
        """
        Limpa o campo que já está com foco, sem clicar (útil após TAB).
        """

        self.client.clear_current_field(
            max_chars=max_chars,
        )

    def click(
        self,
        position,
    ):
        """
        Clica em uma posição.
        """

        self.client.click_position(
            position,
        )

    def write(
        self,
        text,
    ):
        """
        Digita um texto.
        """

        self.client.write(text)

    def press_key(
        self,
        key,
    ):
        """
        Pressiona uma tecla.
        """

        self.client.press_key(key)

    def dismiss_dialogs(self, times: int = 3):
        """
        Fecha qualquer caixa de diálogo com ESC.

        Substitui ter um template por mensagem de erro: as mensagens do
        client são muitas ("Acquiring server IP address", senha errada,
        conta em uso, servidor cheio...) e recortar cada uma é trabalho
        que nunca termina. ESC fecha todas, e o que interessa não é qual
        popup apareceu -- é que ainda não estamos na tela seguinte.

        Repete algumas vezes porque popups podem vir empilhados; ESC na
        tela de login sem diálogo nenhum não faz nada.
        """

        for _ in range(times):
            self.press_key(Keys.ESC)
            self.wait(Delays.AFTER_CLICK)