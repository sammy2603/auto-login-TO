# -*- coding: utf-8 -*-
"""
Handler de logging que escreve no console da GUI.

Mora em src/ui/ (nao na infraestrutura) porque conhece Tkinter, e a
camada de infraestrutura nao pode depender da interface. O
LoggingService so recebe este handler pronto, via add_handler().

Substitui o antigo LogRedirector, que trocava sys.stdout por um objeto
proprio e prefixava as linhas mapeando thread -> apelido da conta. Isso
funcionava, mas: capturava TUDO que fosse impresso no processo
(inclusive de terceiros), nao tinha nivel, e obrigava a restaurar o
sys.stdout na mao quando a ultima conta terminava.
"""

from __future__ import annotations

import logging
import tkinter


class TextboxLogHandler(logging.Handler):
    """
    Escreve cada registro num CTkTextbox.

    Sobre threads: emit() e chamado da thread que logou (conta, bot,
    etc), mas Tkinter so pode ser tocado pela thread principal. Por
    isso o trabalho real e agendado com widget.after(0, ...), que e
    justamente o que o LogRedirector ja fazia.
    """

    def __init__(self, textbox, max_lines: int = 2000):
        super().__init__()
        self._textbox = textbox
        self._max_lines = max_lines

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)
            return

        try:
            self._textbox.after(0, self._append, message + "\n")
        except (tkinter.TclError, RuntimeError):
            # Janela ja destruida (fechando o app) ou loop do Tk fora
            # do ar. Perder log nessa fase e aceitavel -- derrubar a
            # thread que estava logando, nao.
            pass

    def _append(self, text: str) -> None:
        try:
            self._textbox.configure(state="normal")
            self._textbox.insert("end", text)
            self._trim()
            self._textbox.yview_moveto(1.0)
            self._textbox.configure(state="disabled")
        except tkinter.TclError:
            pass

    def _trim(self) -> None:
        """
        Descarta as linhas mais antigas.

        O LogRedirector nao fazia isso: numa sessao de horas com varias
        contas, o textbox crescia sem limite e so parava de crescer
        quando o app fechava.
        """
        try:
            total = int(self._textbox.index("end-1c").split(".")[0])
        except (tkinter.TclError, ValueError):
            return

        if total > self._max_lines:
            self._textbox.delete("1.0", f"{total - self._max_lines}.0")
