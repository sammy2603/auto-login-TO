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

        Observação importante: arquivos .bat/.cmd não são executáveis
        Win32 válidos e precisam passar pelo shell (cmd.exe) para rodar.
        Chamá-los com shell=False costuma falhar com
        "WinError 193: %1 não é um aplicativo Win32 válido".
        Por isso, para esses casos usamos shell=True com o caminho
        entre aspas (necessário se houver espaços na pasta).
        """

        client_dir = os.path.dirname(client_path)
        is_script = client_path.lower().endswith((".bat", ".cmd"))

        if is_script:
            process = subprocess.Popen(
                f'"{client_path}"',
                cwd=client_dir,
                shell=True,
            )
        else:
            process = subprocess.Popen(
                [client_path],
                cwd=client_dir,
                shell=False,
            )

        return process