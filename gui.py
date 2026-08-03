"""
Ponto de entrada da interface gráfica.

Uso: python gui.py

(Para a versão puramente por terminal, sem interface, continue usando
python main.py -- ambos funcionam, escolha o que preferir.)
"""

from src.infrastructure.logging import LoggingService
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    # Antes de construir a janela: a MainWindow anexa o console dela
    # como handler, e handler sem logging configurado nao recebe nada.
    LoggingService.setup()

    app = MainWindow()
    app.run()
