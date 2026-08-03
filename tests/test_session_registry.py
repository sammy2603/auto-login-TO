"""
Testes do SessionRegistry -- registro das contas conectadas.

Além do CRUD, cobre a deduplicação por HWND (uma janela do jogo não
pode aparecer como duas sessões) e a notificação de observers/EventBus,
que é o que mantém a lista de clients da GUI em dia.
"""

from src.shared.event_bus import EventBus
from src.ui.session_registry import SessionRegistry


def test_register_e_get_all():
    SessionRegistry.register("conta1", hwnd=111, pid=222, display="Guerreiro")

    sessions = SessionRegistry.get_all()
    assert sessions["conta1"] == {
        "hwnd": 111, "pid": 222, "display": "Guerreiro", "running": True,
    }


def test_display_default_e_o_proprio_label():
    SessionRegistry.register("conta1", hwnd=111)
    assert SessionRegistry.get_all()["conta1"]["display"] == "conta1"


def test_unregister_remove_a_sessao():
    SessionRegistry.register("conta1", hwnd=111)
    SessionRegistry.unregister("conta1")
    assert SessionRegistry.get_all() == {}


def test_unregister_de_label_inexistente_nao_quebra():
    SessionRegistry.unregister("nunca_existiu")


def test_get_all_retorna_copia():
    """Mutar o retorno não pode corromper o estado interno do registro."""
    SessionRegistry.register("conta1", hwnd=111)

    SessionRegistry.get_all()["conta1"] = "lixo"

    assert SessionRegistry.get_all()["conta1"]["hwnd"] == 111


def test_registrar_mesmo_hwnd_com_outro_label_remove_o_antigo():
    """
    Deduplicação por HWND: a mesma janela do jogo não pode aparecer
    como duas sessões (acontece quando uma conta reloga e o label
    muda, mas a janela é a mesma).
    """
    SessionRegistry.register("ext_999", hwnd=111, display="detectado")
    SessionRegistry.register("conta_real", hwnd=111, display="Guerreiro")

    sessions = SessionRegistry.get_all()
    assert list(sessions) == ["conta_real"]


def test_reregistrar_mesmo_label_atualiza_no_lugar():
    SessionRegistry.register("conta1", hwnd=111, display="antigo")
    SessionRegistry.register("conta1", hwnd=222, display="novo")

    sessions = SessionRegistry.get_all()
    assert len(sessions) == 1
    assert sessions["conta1"]["hwnd"] == 222
    assert sessions["conta1"]["display"] == "novo"


def test_hwnds_diferentes_convivem():
    SessionRegistry.register("conta1", hwnd=111)
    SessionRegistry.register("conta2", hwnd=222)
    assert set(SessionRegistry.get_all()) == {"conta1", "conta2"}


# ==========================================================
# Observers e EventBus
# ==========================================================

def test_observer_notificado_em_register_e_unregister():
    chamadas = []
    SessionRegistry.observe(lambda: chamadas.append(1))

    SessionRegistry.register("conta1", hwnd=111)
    SessionRegistry.unregister("conta1")

    assert len(chamadas) == 2


def test_observer_que_falha_nao_impede_os_outros():
    """Um observer quebrado (ex: widget já destruído) não derruba os demais."""
    chamadas = []

    def quebrado():
        raise RuntimeError("widget destruído")

    SessionRegistry.observe(quebrado)
    SessionRegistry.observe(lambda: chamadas.append(1))

    SessionRegistry.register("conta1", hwnd=111)

    assert chamadas == [1]


def test_publica_no_event_bus_quando_vinculado():
    bus = EventBus()
    recebidos = []
    bus.subscribe("session.registered", lambda **d: recebidos.append(d))
    SessionRegistry.bind_event_bus(bus)

    SessionRegistry.register("conta1", hwnd=111, pid=222, display="Guerreiro")

    assert recebidos == [
        {"label": "conta1", "hwnd": 111, "pid": 222, "display": "Guerreiro"}
    ]


def test_publica_unregistered_no_event_bus():
    bus = EventBus()
    recebidos = []
    bus.subscribe("session.unregistered", lambda **d: recebidos.append(d))
    SessionRegistry.bind_event_bus(bus)

    SessionRegistry.register("conta1", hwnd=111)
    SessionRegistry.unregister("conta1")

    assert recebidos == [{"label": "conta1"}]


def test_funciona_sem_event_bus_vinculado():
    """O EventBus é opcional -- sem ele o registro segue funcionando."""
    SessionRegistry.register("conta1", hwnd=111)
    assert "conta1" in SessionRegistry.get_all()
