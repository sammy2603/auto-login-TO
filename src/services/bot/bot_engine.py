from __future__ import annotations

import time
import threading
from typing import Protocol


class BotScript(Protocol):
    """Protocolo que todo script de bot deve seguir."""

    name: str

    def tick(
        self,
        hwnd: int,
        screenshot,
        char_info,
        target_info,
        input_service,
        vision_service,
        window_service,
    ) -> bool:
        """
        Executa um ciclo do script.

        Retorna True se realizou alguma acao, False caso contrario.
        """
        ...


class BotEngine:
    """
    Motor que executa os scripts do bot em loop.

    Cada script registrado e executado sequencialmente,
    a cada tick (≈ 0.5s). Scripts podem pular se nao
    houver acao a tomar naquele momento.
    """

    def __init__(self):
        self._scripts: list[BotScript] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def register(self, script: BotScript):
        """Registra um script para execucao."""
        with self._lock:
            self._scripts.append(script)

    def unregister(self, script: BotScript):
        """Remove um script."""
        with self._lock:
            if script in self._scripts:
                self._scripts.remove(script)

    def start(
        self,
        hwnd: int,
        input_service,
        vision_service,
        window_service,
        game_reader,
    ):
        """Inicia o loop de execucao em uma thread separada."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            args=(hwnd, input_service, vision_service, window_service, game_reader),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Para o loop de execucao."""
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def _loop(
        self,
        hwnd,
        input_service,
        vision_service,
        window_service,
        game_reader,
    ):
        print(f"[BotEngine] Iniciado para hwnd={hwnd}")

        while self._running:

            try:
                screenshot = window_service.capture_hwnd(hwnd)
                char_info = game_reader.read_char_info(screenshot)
                target_info = game_reader.read_target_info(screenshot)
            except Exception:
                time.sleep(0.5)
                continue

            with self._lock:
                scripts = list(self._scripts)

            for script in scripts:
                if not self._running:
                    break
                try:
                    acted = script.tick(
                        hwnd=hwnd,
                        screenshot=screenshot,
                        char_info=char_info,
                        target_info=target_info,
                        input_service=input_service,
                        vision_service=vision_service,
                        window_service=window_service,
                    )
                    if acted:
                        time.sleep(0.1)
                except Exception as e:
                    print(f"[BotEngine] Erro no script '{script.name}': {e}")

            time.sleep(0.4)

        print(f"[BotEngine] Parado para hwnd={hwnd}")
