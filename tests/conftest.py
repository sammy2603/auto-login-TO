"""
Fixtures compartilhadas.

Nota: SessionRegistry guarda estado em atributos de CLASSE
(_sessions/_observers/_event_bus), então ele é global ao processo --
sem limpar entre os testes, um teste vaza sessões e observers pro
seguinte. Como a classe não expõe um reset público, a fixture abaixo
mexe nos atributos privados de propósito.
"""

import pytest

from src.ui.session_registry import SessionRegistry


def _reset_session_registry():
    SessionRegistry._sessions.clear()
    SessionRegistry._observers.clear()
    SessionRegistry._event_bus = None


@pytest.fixture(autouse=True)
def clean_session_registry():
    _reset_session_registry()
    yield
    _reset_session_registry()


class Flag:
    """
    Dublê de ctk.BooleanVar. O BotEngine só chama .get() nas flags de
    feature, então qualquer objeto com .get() serve -- isso mantém os
    testes livres de Tkinter (que exige display e um root window).
    """

    def __init__(self, value: bool = False):
        self._value = value

    def get(self) -> bool:
        return self._value

    def set(self, value: bool):
        self._value = value


class SpyScript:
    """Script que só registra quantas vezes foi executado."""

    def __init__(self, name: str):
        self.name = name
        self.ticks = 0

    def tick(self, hwnd, screenshot, char_info, target_info,
             input_service, vision_service, window_service) -> bool:
        self.ticks += 1
        return False
