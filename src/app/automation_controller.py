from __future__ import annotations

import win32api
import win32con
import win32gui
import win32process

from src.infrastructure.window.service import WindowService
from src.infrastructure.vision.service import VisionService
from src.infrastructure.input.service import InputService
from src.services.game.game_reader import GameReader
from src.services.game.memory_reader import MemoryReader
from src.services.bot.bot_engine import BotEngine
from src.services.bot.script_registry import ScriptRegistry


class AutomationController:
    """
    Único ponto de comunicação entre a Presentation Layer (GUI) e o
    núcleo de automação (Automation Engine + Infrastructure Layer),
    conforme definido em .project/architecture/01_Architecture.md:

        GUI -> AutomationController -> Automation Engine -> GameClient
        -> Services -> Sistema Operacional

    A GUI nunca deve construir ou acessar diretamente WindowService,
    VisionService, InputService, GameClient ou BotEngine -- toda
    comunicação passa por aqui.

    Mantém as ÚNICAS instâncias compartilhadas de WindowService/
    VisionService/InputService do processo (reaproveitadas por todas
    as sessões/scripts), e um BotEngine por sessão (uma conta logada).
    """

    def __init__(self):

        # Serviços de infraestrutura -- instância única, compartilhada
        # entre todas as sessões. São stateless em relação a qual
        # janela estão operando (recebem o hwnd explicitamente em cada
        # chamada), então é seguro compartilhar.
        self.window_service = WindowService()
        self.vision_service = VisionService(window_service=self.window_service)
        self.input_service = InputService()

        self.game_reader = GameReader()

        self._bot_engines: dict[str, BotEngine] = {}
        self._memory_readers: dict[str, MemoryReader] = {}
        self._memory_reader_failed: set[str] = set()

    # =====================================================
    # Bot Engine (scripts de gameplay)
    # =====================================================

    def get_or_create_bot_engine(self, label: str, script_configs: dict) -> BotEngine:
        """
        Retorna o BotEngine da sessão, criando (e registrando todos os
        scripts disponíveis) na primeira vez.

        'script_configs' é um dict {"pet": {...}, "attack": {...}, ...}
        com a configuração atual de cada script -- essa configuração é
        responsabilidade da GUI (é estado de apresentação/edição), o
        Controller só a repassa para o script correspondente.
        """

        if label not in self._bot_engines:

            engine = BotEngine()

            for descriptor in ScriptRegistry.all():
                config = script_configs.get(descriptor.key, {}) if descriptor.has_config else None
                engine.register(ScriptRegistry.create_instance(descriptor.key, config))

            self._bot_engines[label] = engine

        return self._bot_engines[label]

    def start_scripts(self, label: str, hwnd: int, pid: int | None,
                       feature_vars: dict, script_configs: dict) -> bool:
        """
        Liga os scripts habilitados (feature_vars) para a sessão.
        Retorna False se a sessão não tiver uma janela válida.
        """

        if not hwnd:
            return False

        engine = self.get_or_create_bot_engine(label, script_configs)

        if engine.is_running:
            return True

        memory_reader = self.get_memory_reader(label, pid) if pid else None

        engine.start(
            hwnd,
            self.input_service,
            self.vision_service,
            self.window_service,
            self.game_reader,
            memory_reader,
            feature_vars,
        )

        return True

    def stop_scripts(self, label: str):

        engine = self._bot_engines.get(label)

        if engine:
            engine.stop()

    def is_running(self, label: str) -> bool:

        engine = self._bot_engines.get(label)

        return bool(engine and engine.is_running)

    # =====================================================
    # Leitura de memória
    # =====================================================

    def get_memory_reader(self, label: str, pid: int) -> MemoryReader | None:

        if label in self._memory_reader_failed:
            return None

        if label not in self._memory_readers:
            try:
                self._memory_readers[label] = MemoryReader(pid)
            except Exception:
                self._memory_reader_failed.add(label)
                return None

        return self._memory_readers[label]

    def forget_session(self, label: str):
        """
        Limpa qualquer estado (bot engine, memory reader) associado a
        uma sessão que não existe mais (conta desconectada/removida).
        """

        engine = self._bot_engines.pop(label, None)
        if engine:
            engine.stop()

        self._memory_readers.pop(label, None)
        self._memory_reader_failed.discard(label)

    # =====================================================
    # Janela (foco, renomeação)
    # =====================================================

    def focus_window(self, hwnd: int):
        """
        Traz uma janela pra primeiro plano. Ver comentário em
        _bring_window_to_front sobre a restrição do Windows contra
        "roubo" de foco.
        """

        self._bring_window_to_front(hwnd)

    def rename_window(self, hwnd: int, title: str):

        try:
            self.window_service.set_title_for_hwnd(hwnd, title)
        except Exception as e:
            print(f"[AutomationController] Aviso: não foi possível renomear a janela ({e})")

    @staticmethod
    def _bring_window_to_front(hwnd: int):
        """
        O Windows restringe qual processo pode roubar o foco
        (SetForegroundWindow "puro" costuma falhar silenciosamente se
        a nossa própria janela não está em primeiro plano) -- por isso
        usamos o truque de anexar a thread de input à thread da janela
        em foco antes de chamar.
        """

        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            win32gui.SetForegroundWindow(hwnd)
            return
        except Exception:
            pass

        try:
            fg_hwnd = win32gui.GetForegroundWindow()
            fg_thread, _ = win32process.GetWindowThreadProcessId(fg_hwnd)
            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
            current_thread = win32api.GetCurrentThreadId()

            win32process.AttachThreadInput(current_thread, fg_thread, True)
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
            finally:
                win32process.AttachThreadInput(current_thread, fg_thread, False)
        except Exception as e:
            print(f"[AutomationController] Aviso: não foi possível focar a janela ({e})")