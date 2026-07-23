from __future__ import annotations

import os
import subprocess


class GameLauncher:
    """
    Responsável por iniciar o cliente do jogo.
    """

    def launch(self, client_path: str) -> None:
        """
        Inicia o launcher do jogo.
        """

        client_dir = os.path.dirname(client_path)

        subprocess.Popen(
            f'"{client_path}"',
            cwd=client_dir,
            shell=True,
        )