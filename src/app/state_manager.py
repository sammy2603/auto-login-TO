from __future__ import annotations

from src.ui.session_registry import SessionRegistry


class StateManager:
    """
    Fonte única de consulta pro estado "ao vivo" de cada sessão (conta
    logada), terceiro dos "Próximos Componentes" listados em
    01_Architecture.md.

    Não guarda estado por conta própria -- é uma fachada de consulta
    que combina as fontes que já existem (SessionRegistry para dados
    de conexão, AutomationController para saber se os scripts estão
    rodando), pra quem precisa de uma visão completa de uma sessão não
    precisar combinar as duas manualmente toda vez (o que hoje
    acontece espalhado pela GUI).
    """

    def __init__(self, controller: "AutomationController"):
        self._controller = controller

    def get_session(self, label: str) -> dict | None:
        """
        Retorna o estado combinado de uma sessão, ou None se ela não
        existir (conta não conectada/desconectada).
        """

        session = SessionRegistry.get_all().get(label)

        if not session:
            return None

        return self._merge(label, session)

    def get_all_sessions(self) -> dict[str, dict]:
        """
        Retorna o estado combinado de todas as sessões ativas.
        """

        return {
            label: self._merge(label, session)
            for label, session in SessionRegistry.get_all().items()
        }

    def _merge(self, label: str, session: dict) -> dict:
        return {
            **session,
            "label": label,
            "scripts_running": self._controller.is_running(label),
        }