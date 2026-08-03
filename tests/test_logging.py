"""
Testes do logging.

O que mais importa aqui é o contexto de sessão: com vários clients
abertos, uma linha sem o rótulo da conta ("Erro no script 'Attack'")
não diz de qual delas veio. E como cada conta roda em thread própria,
o isolamento entre threads é o ponto que pode quebrar silenciosamente.
"""

import logging
import threading

import pytest

from src.infrastructure.logging import (
    NO_SESSION,
    LoggingService,
    SessionFilter,
    get_logger,
    get_session,
    session_context,
    set_session,
)
from src.infrastructure.logging.service import ROOT_LOGGER_NAME


@pytest.fixture
def captured():
    """
    Configura o logging só com um handler em memória e devolve uma
    função que entrega as linhas formatadas.
    """
    import io

    stream = io.StringIO()
    LoggingService.setup(
        level=logging.DEBUG, to_file=False, to_console=False, force=True
    )
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s [%(session)s] %(message)s"))
    LoggingService.add_handler(handler)

    yield lambda: [l for l in stream.getvalue().splitlines() if l]

    LoggingService.remove_handler(handler)


# ==========================================================
# Contexto de sessão
# ==========================================================

def test_sem_contexto_usa_rotulo_de_app(captured):
    get_logger("t").info("oi")
    assert captured() == [f"INFO [{NO_SESSION}] oi"]


def test_dentro_do_contexto_carrega_o_rotulo(captured):
    with session_context("Tomyris"):
        get_logger("t").info("oi")
    assert captured() == ["INFO [Tomyris] oi"]


def test_contexto_e_restaurado_ao_sair(captured):
    with session_context("Tomyris"):
        pass
    get_logger("t").info("depois")
    assert captured() == [f"INFO [{NO_SESSION}] depois"]


def test_contexto_e_restaurado_mesmo_com_excecao(captured):
    with pytest.raises(RuntimeError):
        with session_context("Tomyris"):
            raise RuntimeError("boom")

    get_logger("t").info("depois")
    assert captured() == [f"INFO [{NO_SESSION}] depois"]


def test_contextos_aninhados():
    with session_context("A"):
        assert get_session() == "A"
        with session_context("B"):
            assert get_session() == "B"
        assert get_session() == "A"


def test_rotulo_vazio_cai_no_default(captured):
    with session_context(""):
        get_logger("t").info("oi")
    assert captured() == [f"INFO [{NO_SESSION}] oi"]


def test_threads_nao_compartilham_contexto(captured):
    """
    O ponto crítico: cada conta roda em thread própria. Se o contexto
    vazasse entre elas, os logs de uma conta apareceriam com o nome de
    outra -- pior que não ter rótulo nenhum, porque engana.
    """
    barreira = threading.Barrier(2)

    def worker(label):
        with session_context(label):
            barreira.wait(timeout=5)  # garante sobreposição real
            get_logger("t").info("mensagem")

    threads = [
        threading.Thread(target=worker, args=("ContaA",)),
        threading.Thread(target=worker, args=("ContaB",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    linhas = captured()
    assert sorted(linhas) == [
        "INFO [ContaA] mensagem",
        "INFO [ContaB] mensagem",
    ]


def test_thread_nova_nao_herda_contexto_da_criadora(captured):
    """
    ContextVar não é herdado por threads novas -- é justamente o que
    queremos, e o teste trava esse comportamento.
    """
    resultado = []

    def worker():
        resultado.append(get_session())

    with session_context("Tomyris"):
        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=5)

    assert resultado == [""]


def test_set_session_sem_context_manager(captured):
    set_session("Manual")
    get_logger("t").info("oi")
    assert captured() == ["INFO [Manual] oi"]


# ==========================================================
# SessionFilter
# ==========================================================

def test_filtro_nunca_descarta_record():
    record = logging.LogRecord("x", logging.INFO, "f", 1, "msg", None, None)
    assert SessionFilter().filter(record) is True


def test_filtro_preenche_session_em_record_de_terceiro():
    """
    Records de bibliotecas externas não conhecem o campo 'session'.
    Sem o filtro, um formatter com %(session)s quebraria com KeyError.
    """
    record = logging.LogRecord("x", logging.INFO, "f", 1, "msg", None, None)
    SessionFilter().filter(record)
    assert record.session == NO_SESSION


def test_filtro_respeita_session_ja_definida():
    record = logging.LogRecord("x", logging.INFO, "f", 1, "msg", None, None)
    record.session = "Explicita"
    SessionFilter().filter(record)
    assert record.session == "Explicita"


# ==========================================================
# LoggingService
# ==========================================================

def test_get_logger_monta_a_hierarquia():
    assert get_logger("services.bot").name == f"{ROOT_LOGGER_NAME}.services.bot"
    assert get_logger().name == ROOT_LOGGER_NAME


def test_setup_nao_duplica_handlers():
    """
    Chamar setup duas vezes (GUI e terminal both call it) não pode
    fazer cada linha aparecer duplicada no console.
    """
    LoggingService.setup(to_file=False, to_console=True, force=True)
    antes = len(logging.getLogger(ROOT_LOGGER_NAME).handlers)

    LoggingService.setup(to_file=False, to_console=True, force=True)
    depois = len(logging.getLogger(ROOT_LOGGER_NAME).handlers)

    assert antes == depois


def test_setup_nao_propaga_para_o_root_do_python():
    """
    Sem isso, quem chamar logging.basicConfig() em qualquer lugar
    passa a receber (e duplicar) as mensagens da aplicação.
    """
    LoggingService.setup(to_file=False, to_console=False, force=True)
    assert logging.getLogger(ROOT_LOGGER_NAME).propagate is False


def test_nivel_filtra_mensagens(captured):
    LoggingService.set_level(logging.WARNING)
    try:
        log = get_logger("t")
        log.debug("nao aparece")
        log.info("nao aparece")
        log.warning("aparece")
        assert captured() == [f"WARNING [{NO_SESSION}] aparece"]
    finally:
        LoggingService.set_level(logging.DEBUG)


def test_escreve_em_arquivo(tmp_path):
    destino = tmp_path / "sub" / "teste.log"
    LoggingService.setup(
        level=logging.INFO, to_file=True, to_console=False,
        log_file=destino, force=True,
    )

    with session_context("Tomyris"):
        get_logger("t").info("gravado em disco")

    for handler in logging.getLogger(ROOT_LOGGER_NAME).handlers:
        handler.close()

    conteudo = destino.read_text(encoding="utf-8")
    assert "gravado em disco" in conteudo
    assert "[Tomyris]" in conteudo


def test_falha_ao_abrir_arquivo_nao_impede_o_setup(tmp_path):
    """
    Disco cheio ou pasta sem permissão não pode impedir o app de subir.
    Aqui o caminho é inválido porque um ARQUIVO ocupa o lugar da pasta.
    """
    bloqueio = tmp_path / "bloqueio"
    bloqueio.write_text("nao sou pasta", encoding="utf-8")

    logger = LoggingService.setup(
        to_file=True, to_console=False,
        log_file=bloqueio / "sub" / "x.log", force=True,
    )

    assert logger is not None
    get_logger("t").info("segue funcionando")


def test_exception_registra_o_traceback(captured):
    try:
        raise ValueError("causa raiz")
    except ValueError:
        get_logger("t").exception("falhou")

    saida = "\n".join(captured())
    assert "falhou" in saida
    assert "ValueError: causa raiz" in saida
    assert "Traceback" in saida
