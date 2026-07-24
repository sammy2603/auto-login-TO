from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class GameSession:
    """
    Representa uma instância do cliente do jogo.

    Esta classe armazena o estado da sessão atual.
    Não possui regras de negócio.
    """

    # Processo

    pid: Optional[int] = None

    process = None

    # Janela

    hwnd: Optional[int] = None

    # Dados da conta

    account: Optional[str] = None

    server: Optional[str] = None

    character: Optional[str] = None

    # Identificação

    instance_name: Optional[str] = None

    # Estado

    launched: bool = False

    connected: bool = False

    in_game: bool = False

    def reset(self):

        self.pid = None

        self.process = None

        self.hwnd = None

        self.account = None

        self.server = None

        self.character = None

        self.instance_name = None

        self.launched = False

        self.connected = False

        self.in_game = False