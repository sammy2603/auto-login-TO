class ServerConnectionInterrupted(Exception):
    """
    Levantada quando o jogo mostra o popup de "conexão interrompida"
    após a seleção de servidor, o que retorna o client para a tela de
    login.

    Quem capturar essa exceção deve refazer o login e a seleção de
    servidor -- o client não precisa ser relançado, só reconectado ao
    fluxo de login.
    """
    pass