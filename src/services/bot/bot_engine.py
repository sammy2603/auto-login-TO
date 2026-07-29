from __future__ import annotations

import time
import threading
from typing import Protocol


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
              game_reader, memory_reader=None, feature_enabled=None):
        if self._running:
            return
        self._running = True
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

    def _loop(self, hwnd, input_service, vision_service, window_service,
              game_reader, memory_reader, feature_enabled):
        print(f"[BotEngine] Iniciado para hwnd={hwnd}")

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
                    target_info.hp_pct = memory_reader.target_hp_pct
                    target_info.name = memory_reader.target_name
                except Exception:
                    pass

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
                var = feature_enabled.get(script.name)
                if var is not None and not var.get():
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
                except Exception as e:
                    print(f"[BotEngine] Erro no script '{script.name}': {e}")

            time.sleep(0.4)

        print(f"[BotEngine] Parado para hwnd={hwnd}")
