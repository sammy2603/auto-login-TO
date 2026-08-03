# -*- coding: utf-8 -*-
"""
Configuracao central do logging.

Antes disto o projeto usava print() espalhado: sem niveis (nao dava pra
calar detalhe sem perder erro), sem timestamp, sem saber de qual conta
veio cada linha, e sem nada em disco -- fechou o app, perdeu o log.
Justamente o que mais falta quando algo quebra depois de horas rodando.

Camada: isto e infraestrutura, entao NAO conhece a GUI. Quem quiser
exibir log numa interface anexa o proprio handler (ver
src/ui/log_handler.py). Aqui so ficam console e arquivo.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from src.infrastructure.logging.models import SessionFilter

# Raiz da arvore de loggers da aplicacao. Todo modulo pede
# get_logger(__name__), o que produz "loginto.src.services.bot..." e
# permite calar/soltar um subsistema inteiro por prefixo.
ROOT_LOGGER_NAME = "loginto"

LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_FILE = LOG_DIR / "loginto.log"

# Console enxuto (e o que aparece na GUI): hora, nivel, conta, mensagem.
CONSOLE_FORMAT = "%(asctime)s %(levelname)-7s [%(session)s] %(message)s"
CONSOLE_DATE_FORMAT = "%H:%M:%S"

# Arquivo carrega tambem data completa e origem, pra investigar depois.
FILE_FORMAT = (
    "%(asctime)s %(levelname)-7s [%(session)s] %(name)s: %(message)s"
)
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Logger da aplicacao. Passe __name__ pra herdar a hierarquia:

        logger = get_logger(__name__)
    """
    if not name:
        return logging.getLogger(ROOT_LOGGER_NAME)
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


class LoggingService:
    """
    Monta a configuracao de logging do processo.

    Idempotente de proposito: 'setup' pode ser chamado tanto pela GUI
    quanto pelo main.py de terminal, e chamar duas vezes nao pode
    duplicar handlers (o sintoma classico e cada linha aparecer duas
    vezes no console).
    """

    @staticmethod
    def setup(
        level: int = logging.INFO,
        to_file: bool = True,
        to_console: bool = True,
        log_file: Path | None = None,
        force: bool = False,
    ) -> logging.Logger:
        """
        Configura o logger raiz da aplicacao e o devolve.

        'force=True' remonta do zero (usado nos testes).
        """

        global _configured

        logger = logging.getLogger(ROOT_LOGGER_NAME)

        if _configured and not force:
            return logger

        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

        logger.setLevel(level)

        # Nao propaga pro root do Python: quem configurar logging por
        # fora (biblioteca de terceiros, basicConfig) nao deve receber
        # -- nem duplicar -- as mensagens da aplicacao.
        logger.propagate = False

        session_filter = SessionFilter()

        if to_console:
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(
                logging.Formatter(CONSOLE_FORMAT, datefmt=CONSOLE_DATE_FORMAT)
            )
            console.addFilter(session_filter)
            logger.addHandler(console)

        if to_file:
            target = log_file or LOG_FILE
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                # Rotaciona em 2 MB, guardando 5 arquivos: o suficiente
                # pra investigar uma sessao longa sem encher o disco.
                file_handler = logging.handlers.RotatingFileHandler(
                    target,
                    maxBytes=2 * 1024 * 1024,
                    backupCount=5,
                    encoding="utf-8",
                )
                file_handler.setFormatter(
                    logging.Formatter(FILE_FORMAT, datefmt=FILE_DATE_FORMAT)
                )
                file_handler.addFilter(session_filter)
                logger.addHandler(file_handler)
            except OSError as exc:
                # Disco cheio ou pasta sem permissao nao pode impedir o
                # app de subir -- o console ja foi configurado acima.
                logger.warning(
                    "Nao foi possivel abrir o arquivo de log (%s): %s",
                    target,
                    exc,
                )

        _configured = True

        return logger

    @staticmethod
    def add_handler(handler: logging.Handler) -> None:
        """
        Anexa um handler externo (ex: o console da GUI). O filtro de
        sessao e aplicado aqui pra quem chama nao precisar lembrar --
        esquecer disso faz %(session)s quebrar com KeyError.
        """
        handler.addFilter(SessionFilter())
        logging.getLogger(ROOT_LOGGER_NAME).addHandler(handler)

    @staticmethod
    def remove_handler(handler: logging.Handler) -> None:
        logging.getLogger(ROOT_LOGGER_NAME).removeHandler(handler)

    @staticmethod
    def set_level(level: int) -> None:
        logging.getLogger(ROOT_LOGGER_NAME).setLevel(level)
