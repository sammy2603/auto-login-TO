# -*- coding: utf-8 -*-
"""
Logging da aplicacao.

Uso tipico num modulo qualquer:

    from src.infrastructure.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Sessao registrada: %s", label)

E, na thread de uma conta, pra que toda linha saia identificada:

    from src.infrastructure.logging import session_context

    with session_context(account.label):
        ...
"""

from src.infrastructure.logging.models import (
    NO_SESSION,
    SessionFilter,
    get_session,
    reset_session,
    session_context,
    set_session,
)
from src.infrastructure.logging.service import (
    LoggingService,
    get_logger,
)

__all__ = [
    "LoggingService",
    "get_logger",
    "session_context",
    "set_session",
    "reset_session",
    "get_session",
    "SessionFilter",
    "NO_SESSION",
]
