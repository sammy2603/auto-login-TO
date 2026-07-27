from __future__ import annotations
import threading
import time


class GameClient:
    """
    Fachada responsável pela interação com o cliente do jogo.

    Os workflows nunca devem acessar diretamente
    WindowService, VisionService, InputService ou GameLauncher.

    Toda interação deve acontecer através desta classe.
    """

    # Trava COMPARTILHADA entre todas as instâncias (nível de classe).
    # Necessária pra rodar várias contas em paralelo: o trecho de
    # "abrir o client + esperar a janela nova aparecer" precisa ser
    # atômico -- se outra conta abrir o client dela no meio dessa
    # espera, o bot pode confundir qual janela pertence a qual conta.
    # O restante do fluxo de cada conta (login, fila, etc) continua
    # rodando em paralelo normalmente; só esse trecho fica serializado.
    launch_lock = threading.Lock()

    def __init__(
        self,
        session,
        launcher,
        window_service,
        vision_service,
        input_service,
    ):
        self.session = session

        self.launcher = launcher
        self.window = window_service
        self.vision = vision_service
        self.input = input_service

    # =====================================================
    # Launcher
    # =====================================================

    def launch(self, client_path):

        process = self.launcher.launch(client_path)

        self.session.process = process

        self.session.pid = process.pid

        self.session.launched = True

        print(f"[GameClient] PID: {self.session.pid}")
        return process

    # =====================================================
    # Window
    # =====================================================

    def connect(
        self,
        title_substring: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Conecta ao cliente do jogo.

        Prioriza detectar a JANELA NOVA que aparece logo após o
        launch. Isso é necessário porque launchers baseados em .bat
        costumam iniciar o executável real via "start", que roda como
        um processo separado com PID diferente do processo rastreado
        em session.pid — nesse caso, conectar pelo PID original nunca
        encontraria a janela do jogo. Ao detectar a janela nova,
        corrigimos session.pid para o PID real do client.

        Caso o launch não tenha acontecido nesta sessão (ex: conexão
        manual/reconexão), cai para os métodos legados por PID ou
        título.
        """

        if self.session.launched and not self.session.connected:

            print(
                "[GameClient] Aguardando nova janela após o lançamento..."
            )

            hwnd, pid = self.window.connect_new_window(
                timeout=timeout,
            )

            self.session.hwnd = hwnd
            self.session.pid = pid  # corrige para o PID real da janela

            self.session.connected = True
            return

        if self.session.pid is not None:

            print(
                f"[GameClient] Conectando pelo PID {self.session.pid}..."
            )

            self.window.connect(
                pid=self.session.pid,
                timeout=timeout,
            )

        else:

            print(
                "[GameClient] Conectando pelo título..."
            )

            self.window.connect(
                title_substring=title_substring,
                timeout=timeout,
            )

        self.session.hwnd = self.window.hwnd
        self.session.connected = True

    @property
    def hwnd(self):

        if self.session.hwnd is None:

            raise RuntimeError(
                "Nenhuma janela conectada."
            )

        return self.session.hwnd

    def capture(self):
        """
        Captura a imagem atual da janela.
        """
        return self.window.capture()

    def client_size(self):
        """
        Retorna o tamanho da área útil da janela.
        """
        return self.window.client_size()

    def rename_window(self, title: str):
        """
        Renomeia a janela conectada. Útil pra diferenciar várias
        contas rodando ao mesmo tempo na barra de tarefas.
        """
        try:
            self.window.set_title(title)
        except Exception as e:
            print(f"[GameClient] Aviso: não foi possível renomear a janela ({e})")

    # =====================================================
    # Vision
    # =====================================================

    def wait_template(
        self,
        template_name: str,
        timeout: float = 30.0,
        threshold: float = 0.90,
    ):
        """
        Aguarda um template aparecer.
        """

        return self.vision.wait_template(
            hwnd=self.hwnd,
            template=template_name,
            timeout=timeout,
            threshold=threshold,
        )

    def find_template(
        self,
        template_name: str,
        threshold: float = 0.90,
    ):
        """
        Procura um template na tela.
        """

        return self.vision.find_template(
            hwnd=self.hwnd,
            template=template_name,
            threshold=threshold,
        )

    def template_exists(
        self,
        template_name: str,
        threshold: float = 0.90,
    ) -> bool:
        """
        Verifica se um template está presente.
        """

        return (
            self.find_template(
                template_name,
                threshold,
            )
            is not None
        )

    # =====================================================
    # Mouse
    # =====================================================

    def click_position(self, position):
        """
        Clica em uma posição da tela.
        """

        x, y = position

        self.input.click(
            self.hwnd,
            x,
            y,
        )

    # =====================================================
    # Keyboard
    # =====================================================

    def write(self, text: str):
        """
        Digita um texto.
        """

        self.input.type_text(
            self.hwnd,
            text,
        )

    def clear_field(self, position):
        """
        Limpa um campo de texto.
        """

        x, y = position

        self.input.clear(
            self.hwnd,
            x,
            y,
        )

    def clear_current_field(self, max_chars: int = 30):
        """
        Limpa o campo que já está com foco (sem clicar em nenhuma
        posição). Útil depois de navegar entre campos com TAB.
        """

        self.input.clear_current(
            self.hwnd,
            max_chars=max_chars,
        )

    def press_key(self, key):
        """
        Pressiona uma tecla.
        """

        self.input.press_key(
            self.hwnd,
            key,
        )

    # =====================================================
    # Helpers
    # =====================================================

    def wait(self, seconds: float):
        """
        Aguarda um intervalo.
        """

        time.sleep(seconds)

    def fill_field(
        self,
        position,
        text: str,
        click_delay: float = 0.40,
        clear_delay: float = 0.30,
    ):
        """
        Fluxo completo para preencher um campo.
        """

        self.click_position(position)

        self.wait(click_delay)

        self.clear_field(position)

        self.wait(clear_delay)

        self.write(text)