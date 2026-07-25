"""
Centraliza todos os tempos utilizados pelos workflows.

Evita números mágicos espalhados pelo projeto.
"""


class Delays:

    # Após clicar em um campo
    AFTER_CLICK = 0.25

    # Tempo de espera entre clicar num campo de texto e começar a
    # digitar nele. Maior que AFTER_CLICK de propósito: dá margem pro
    # client "assentar" o foco antes da digitação começar, evitando
    # perder os primeiros caracteres (visto acontecer no campo de
    # senha, onde é difícil notar já que o conteúdo fica mascarado).
    FIELD_FOCUS_DELAY = 0.50

    # Após limpar um campo
    AFTER_CLEAR = 0.15

    # Após preencher um campo
    AFTER_FILL = 0.50

    # Após clicar em Entrar
    AFTER_LOGIN = 0.30

    # Após selecionar um servidor
    AFTER_SERVER_SELECT = 0.30

    # Após confirmar a entrada no servidor
    AFTER_SERVER_CONFIRM = 0.30

    # Após clicar para entrar no jogo (tela de personagem)
    AFTER_ENTER_GAME = 0.30

    # Intervalo entre tentativas de reconhecimento durante uma espera
    # longa (ex: fila de servidor). Não precisa ser tão frequente
    # quanto as esperas normais, já que pode durar minutos.
    QUEUE_POLL_INTERVAL = 3.0

    # A cada quantos segundos logamos "ainda aguardando..." durante
    # uma espera longa, para o usuário saber que o bot não travou.
    QUEUE_HEARTBEAT_INTERVAL = 15.0

    # Mudança de tela
    SCREEN_TRANSITION = 1.50