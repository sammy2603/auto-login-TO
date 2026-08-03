from __future__ import annotations

import time
import threading
from typing import Protocol

from src.infrastructure.logging import get_logger, session_context

logger = get_logger(__name__)


class BotScript(Protocol):
    name: str

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool: ...


class BotEngine:

    def __init__(self):
        self._scripts: list[BotScript] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def register(self, script: BotScript):
        with self._lock:
            self._scripts.append(script)

    def unregister(self, script: BotScript):
        with self._lock:
            if script in self._scripts:
                self._scripts.remove(script)

    def start(self, hwnd, input_service, vision_service, window_service,
              game_reader, memory_reader=None, feature_enabled=None,
              session_label: str = ""):
        if self._running:
            return
        self._running = True
        self._session_label = session_label
        self._thread = threading.Thread(
            target=self._loop,
            args=(hwnd, input_service, vision_service, window_service,
                  game_reader, memory_reader, feature_enabled or {}),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def is_script_enabled(script_name: str, feature_enabled: dict) -> bool:
        """
        Um script só roda se houver uma flag registrada pra ele E ela
        estiver ligada.

        Ausência de flag significa DESLIGADO (default seguro). Tratar
        "sem estado registrado" como ligado já fez todo script -- Attack
        inclusive -- rodar com o switch do card desligado.
        """
        var = feature_enabled.get(script_name)
        return var is not None and bool(var.get())

    def _loop(self, hwnd, input_service, vision_service, window_service,
              game_reader, memory_reader, feature_enabled):
        # A thread do motor e propria, entao comeca sem contexto: sem
        # isto, todo log de script sairia sem dizer de qual conta veio.
        with session_context(getattr(self, "_session_label", "")):
            self._run(hwnd, input_service, vision_service, window_service,
                      game_reader, memory_reader, feature_enabled)

    def _run(self, hwnd, input_service, vision_service, window_service,
             game_reader, memory_reader, feature_enabled):
        logger.info("Motor de scripts iniciado (hwnd=%s)", hwnd)

        from src.services.game.game_reader import CharInfo, TargetInfo

        while self._running:
            char_info = CharInfo()
            target_info = TargetInfo()

            if memory_reader:
                try:
                    char_info.hp_pct = memory_reader.hp_pct
                    char_info.resource_pct = memory_reader.mana_pct
                    char_info.in_battle = memory_reader.in_battle
                    char_info.pet_alive = memory_reader.pet_alive
                    char_info.x = memory_reader.x
                    char_info.y = memory_reader.y
                    target_info.hp_pct = memory_reader.target_hp_pct
                    target_info.name = memory_reader.target_name
                except Exception:
                    pass

            # Kill count do dashboard
            if hasattr(self, "_kill_track_cb") and self._kill_track_cb:
                char_info.kill_count = self._kill_track_cb()

            if char_info.hp_pct == 0 and char_info.resource_pct == 0:
                try:
                    screenshot = window_service.capture_hwnd(hwnd)
                    char_info = game_reader.read_char_info(screenshot)
                    char_info.in_battle = False
                    target_info = game_reader.read_target_info(screenshot)
                except Exception:
                    time.sleep(0.5)
                    continue

            with self._lock:
                scripts = list(self._scripts)

            for script in scripts:
                if not self._running:
                    break
                if not self.is_script_enabled(script.name, feature_enabled):
                    continue
                try:
                    acted = script.tick(
                        hwnd=hwnd, screenshot=None,
                        char_info=char_info, target_info=target_info,
                        input_service=input_service,
                        vision_service=vision_service,
                        window_service=window_service,
                    )
                    if acted:
                        time.sleep(0.1)
                except Exception:
                    logger.exception("Erro no script '%s'", script.name)

            time.sleep(0.4)

        logger.info("Motor de scripts parado (hwnd=%s)", hwnd)
