from __future__ import annotations

import os
import subprocess


class GameLauncher:
    """
    Responsável por iniciar o cliente do jogo.
    """

    def launch(self, client_path: str) -> subprocess.Popen:
        """
        Inicia o cliente do jogo.

        Retorna o processo criado para que a aplicação
        possa acompanhar sua execução.
        """

        client_dir = os.path.dirname(client_path)

        process = subprocess.Popen(
            [client_path],
            cwd=client_dir,
            shell=False,
        )

        return process