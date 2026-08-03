from __future__ import annotations

import threading
from typing import Callable

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class EventBus:
    """
    Barramento de eventos simples (publish/subscribe), thread-safe.

    Permite que componentes do núcleo de automação (AutomationController,
    BotEngine, workflows) comuniquem mudanças de estado sem precisar
    conhecer quem está do outro lado (GUI, logger, etc), reduzindo o
    acoplamento e a necessidade de polling pra tudo.

    IMPORTANTE sobre threads: publish() pode ser chamado de QUALQUER
    thread (scripts e contas rodam em threads próprias). Os callbacks
    inscritos são executados NA MESMA THREAD que chamou publish() --
    ou seja, se o assinante for uma interface gráfica (Tkinter), ele é
    responsável por agendar a atualização real de widgets de volta pra
    thread principal (ex: via root.after(0, ...)), já que bibliotecas
    de GUI geralmente não são thread-safe.
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_name: str, callback: Callable):
        with self._lock:
            self._subscribers.setdefault(event_name, []).append(callback)

    def unsubscribe(self, event_name: str, callback: Callable):
        with self._lock:
            callbacks = self._subscribers.get(event_name)
            if callbacks and callback in callbacks:
                callbacks.remove(callback)

    def publish(self, event_name: str, **data):
        """
        Notifica todos os assinantes de 'event_name', passando 'data'
        como argumentos nomeados. Um assinante que lança exceção não
        derruba os demais nem quem publicou o evento -- só loga o erro.
        """

        with self._lock:
            callbacks = list(self._subscribers.get(event_name, []))

        for callback in callbacks:
            try:
                callback(**data)
            except Exception:
                logger.exception("Erro no assinante de '%s'", event_name)