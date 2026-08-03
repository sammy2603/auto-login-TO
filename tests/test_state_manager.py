"""
Testes do StateManager -- a fachada que combina "dados de conexão"
(SessionRegistry) com "os scripts estão rodando?" (AutomationController)
numa visão só.

O AutomationController real constrói WindowService/VisionService/
InputService (win32, captura de tela), então aqui ele é substituído por
um dublê: o StateManager só depende de .is_running(label).
"""

from src.app.state_manager import StateManager
from src.ui.session_registry import SessionRegistry


class FakeController:
    def __init__(self, running: set[str] | None = None):
        self._running = running or set()

    def is_running(self, label: str) -> bool:
        return label in self._running


def test_get_session_combina_conexao_e_execucao():
    SessionRegistry.register("conta1", hwnd=111, pid=222, display="Guerreiro")
    state = StateManager(FakeController(running={"conta1"}))

    assert state.get_session("conta1") == {
        "hwnd": 111,
        "pid": 222,
        "display": "Guerreiro",
        "running": True,
        "label": "conta1",
        "scripts_running": True,
    }


def test_scripts_running_falso_para_sessao_parada():
    SessionRegistry.register("conta1", hwnd=111)
    state = StateManager(FakeController())

    assert state.get_session("conta1")["scripts_running"] is False


def test_get_session_inexistente_retorna_none():
    state = StateManager(FakeController())
    assert state.get_session("nao_existe") is None


def test_get_all_sessions_traz_todas_com_o_estado_certo():
    SessionRegistry.register("conta1", hwnd=111)
    SessionRegistry.register("conta2", hwnd=222)
    state = StateManager(FakeController(running={"conta2"}))

    sessions = state.get_all_sessions()

    assert set(sessions) == {"conta1", "conta2"}
    assert sessions["conta1"]["scripts_running"] is False
    assert sessions["conta2"]["scripts_running"] is True


def test_get_all_sessions_vazio_quando_nao_ha_sessao():
    state = StateManager(FakeController())
    assert state.get_all_sessions() == {}


def test_label_e_injetado_na_visao_combinada():
    """
    O SessionRegistry guarda o label como CHAVE do dict; o StateManager
    também o coloca dentro do valor, pra quem itera só os valores não
    perder de qual conta o registro é.
    """
    SessionRegistry.register("conta1", hwnd=111)
    state = StateManager(FakeController())

    assert state.get_all_sessions()["conta1"]["label"] == "conta1"


def test_nao_guarda_estado_proprio():
    """
    É uma fachada de consulta: mudou no SessionRegistry, a próxima
    leitura já reflete -- sem cache pra invalidar.
    """
    state = StateManager(FakeController())
    assert state.get_all_sessions() == {}

    SessionRegistry.register("conta1", hwnd=111)
    assert set(state.get_all_sessions()) == {"conta1"}

    SessionRegistry.unregister("conta1")
    assert state.get_all_sessions() == {}


def test_running_da_conexao_e_scripts_running_sao_coisas_diferentes():
    """
    Pegadinha do dict combinado: 'running' vem do SessionRegistry e
    significa "a conta está conectada"; 'scripts_running' significa "o
    bot está atuando". Uma conta pode estar online e parada.
    """
    SessionRegistry.register("conta1", hwnd=111)
    state = StateManager(FakeController())

    session = state.get_session("conta1")
    assert session["running"] is True
    assert session["scripts_running"] is False
