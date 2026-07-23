"""
Centraliza todos os tempos utilizados pelos workflows.

Evita números mágicos espalhados pelo projeto.
"""


class Delays:

    # Após clicar em um campo
    AFTER_CLICK = 0.25

    # Após limpar um campo
    AFTER_CLEAR = 0.15

    # Após preencher um campo
    AFTER_FILL = 0.50

    # Após clicar em Entrar
    AFTER_LOGIN = 0.30

    # Mudança de tela
    SCREEN_TRANSITION = 1.50