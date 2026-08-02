import threading
from typing import Callable


class SessionRegistry:
    """
    Registro thread-safe das sessoes ativas do jogo.

    Cada conta logada registra seu HWND aqui. O RightPanel
    observa mudancas para exibir a lista de janelas abertas.

    Também publica eventos no EventBus compartilhado (se vinculado via
    bind_event_bus), pra quem preferir reagir a mudanças específicas
    ("session.registered"/"session.unregistered") em vez de usar o
    observer genérico "algo mudou" (observe/_notify).
    """

    _sessions: dict[str, dict] = {}
    _lock = threading.Lock()
    _observers: list[Callable[[], None]] = []
    _event_bus = None

    @classmethod
    def bind_event_bus(cls, event_bus):
        cls._event_bus = event_bus

    @classmethod
    def register(cls, label: str, hwnd: int, pid: int | None = None,
                 display: str | None = None):
        """Registra uma sessao ativa. Remove duplicatas pelo HWND."""
        with cls._lock:
            # Remove qualquer entrada existente com o mesmo HWND
            to_remove = [
                k for k, v in cls._sessions.items()
                if v.get("hwnd") == hwnd and k != label
            ]
            for k in to_remove:
                del cls._sessions[k]

            cls._sessions[label] = {
                "hwnd": hwnd,
                "pid": pid,
                "display": display or label,
                "running": True,
            }
        cls._notify()
        if cls._event_bus:
            cls._event_bus.publish("session.registered", label=label, hwnd=hwnd, pid=pid, display=display or label)

    @classmethod
    def unregister(cls, label: str):
        """Remove uma sessao."""
        with cls._lock:
            cls._sessions.pop(label, None)
        cls._notify()
        if cls._event_bus:
            cls._event_bus.publish("session.unregistered", label=label)

    @classmethod
    def get_all(cls) -> dict[str, dict]:
        """Retorna copia das sessoes ativas."""
        with cls._lock:
            return dict(cls._sessions)

    @classmethod
    def observe(cls, callback: Callable[[], None]):
        """Registra callback chamado quando sessoes mudam."""
        cls._observers.append(callback)

    @classmethod
    def _notify(cls):
        for cb in cls._observers:
            try:
                cb()
            except Exception:
                pass