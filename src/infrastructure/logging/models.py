# -*- coding: utf-8 -*-
"""
Contexto de sessao do logging.

O problema: quase tudo neste projeto roda em thread propria -- cada
conta tem a sua (_run_account_loop) e cada BotEngine tambem
(BotEngine._loop). Sem contexto, uma linha solta ("Erro no script
'Attack'") nao diz de QUAL das contas logadas ela veio, o que com 3
clients abertos e inutil.

A solucao e a mesma ideia que o LogRedirector antigo usava (mapear
thread -> apelido da conta), mas sem sequestrar o sys.stdout: um
ContextVar guarda o rotulo e um filtro injeta esse rotulo em todo
record que passa. Formatters e handlers so leem record.session.

Sobre ContextVar e threads: uma thread nova comeca com contexto VAZIO,
nao herda o da thread que a criou. E exatamente o que queremos -- cada
thread de conta declara a sua no inicio, sem vazar pras outras.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager

# Rotulo da sessao (apelido da conta) associado ao fluxo atual.
# Vazio = mensagem do proprio app, nao de uma conta especifica.
_session_label: contextvars.ContextVar[str] = contextvars.ContextVar(
    "session_label", default=""
)

# Usado no lugar do rotulo quando a mensagem nao pertence a nenhuma
# conta (startup, licenca, GUI).
NO_SESSION = "app"


def set_session(label: str) -> contextvars.Token:
    """
    Marca o fluxo atual como pertencente a uma conta. Chamar no INICIO
    da thread da conta. Retorna o token pra quem quiser desfazer.
    """
    return _session_label.set(label or "")


def reset_session(token: contextvars.Token) -> None:
    _session_label.reset(token)


def get_session() -> str:
    """Rotulo da sessao atual, ou string vazia se nao houver."""
    return _session_label.get()


@contextmanager
def session_context(label: str):
    """
    Versao com 'with': todo log emitido dentro do bloco carrega o
    rotulo, e o valor anterior volta ao sair -- inclusive se o bloco
    levantar excecao.
    """
    token = set_session(label)
    try:
        yield
    finally:
        reset_session(token)


class SessionFilter:
    """
    Injeta 'session' em todo LogRecord.

    E um filtro no sentido do logging (tem .filter() e sempre retorna
    True), mas nao herda de logging.Filter de proposito: aqui ele so
    ENRIQUECE o record, nunca descarta nada -- herdar sugeriria que
    filtra.

    Sem isso, um formatter que use %(session)s quebra com KeyError nos
    records vindos de bibliotecas de terceiros, que obviamente nao
    conhecem esse campo.
    """

    def filter(self, record) -> bool:
        if not getattr(record, "session", ""):
            record.session = get_session() or NO_SESSION
        return True
