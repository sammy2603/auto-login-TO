"""
Testes do EventBus.

O contrato crítico está documentado no próprio módulo: publish() é
chamado de qualquer thread, e um assinante que explode não pode derrubar
quem publicou (na prática, um script do bot) nem os outros assinantes.
"""

import threading

from src.shared.event_bus import EventBus


def test_subscriber_recebe_o_evento_com_os_dados():
    bus = EventBus()
    recebidos = []
    bus.subscribe("bot.started", lambda **d: recebidos.append(d))

    bus.publish("bot.started", label="conta1")

    assert recebidos == [{"label": "conta1"}]


def test_multiplos_subscribers_recebem_todos():
    bus = EventBus()
    chamadas = []
    bus.subscribe("bot.started", lambda **d: chamadas.append("a"))
    bus.subscribe("bot.started", lambda **d: chamadas.append("b"))

    bus.publish("bot.started", label="conta1")

    assert chamadas == ["a", "b"]


def test_subscriber_so_recebe_o_evento_que_assinou():
    bus = EventBus()
    recebidos = []
    bus.subscribe("bot.started", lambda **d: recebidos.append(d))

    bus.publish("bot.stopped", label="conta1")

    assert recebidos == []


def test_publish_sem_subscriber_nao_quebra():
    EventBus().publish("evento.sem.ninguem", x=1)


def test_unsubscribe_para_de_receber():
    bus = EventBus()
    recebidos = []

    def handler(**d):
        recebidos.append(d)

    bus.subscribe("bot.started", handler)
    bus.unsubscribe("bot.started", handler)
    bus.publish("bot.started", label="conta1")

    assert recebidos == []


def test_unsubscribe_de_quem_nao_assinou_nao_quebra():
    bus = EventBus()
    bus.unsubscribe("bot.started", lambda **d: None)


def test_subscriber_que_falha_nao_derruba_os_outros():
    """
    Um assinante quebrado (ex: a GUI mexendo em widget já destruído)
    não pode impedir os demais de receberem nem propagar a exceção pro
    script que publicou.
    """
    bus = EventBus()
    recebidos = []

    def quebrado(**d):
        raise RuntimeError("boom")

    bus.subscribe("bot.started", quebrado)
    bus.subscribe("bot.started", lambda **d: recebidos.append(d))

    bus.publish("bot.started", label="conta1")

    assert recebidos == [{"label": "conta1"}]


def test_publish_de_outra_thread_chega_ao_subscriber():
    bus = EventBus()
    recebidos = []
    bus.subscribe("bot.started", lambda **d: recebidos.append(d))

    t = threading.Thread(target=lambda: bus.publish("bot.started", label="conta1"))
    t.start()
    t.join(timeout=3.0)

    assert recebidos == [{"label": "conta1"}]


def test_subscribe_concorrente_nao_perde_inscricao():
    """O lock precisa segurar 50 inscrições simultâneas sem perder nenhuma."""
    bus = EventBus()
    chamadas = []

    def inscrever():
        bus.subscribe("evento", lambda **d: chamadas.append(1))

    threads = [threading.Thread(target=inscrever) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3.0)

    bus.publish("evento")

    assert len(chamadas) == 50
