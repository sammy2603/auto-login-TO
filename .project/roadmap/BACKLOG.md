FASE 2 - Migracao do Codigo Legado (CONCLUIDA)

[x] Inicializacao da aplicacao
[x] Conexao com a janela
[x] Login
[x] Selecao de servidor
[x] Entrada no jogo
[x] Remover dependencia direta do main.py
[x] Remover window_utils.py, vision.py, input_utils.py

FASE 3 - Melhorias (EM ANDAMENTO)

[x] Interface grafica (3 paineis: sidebar, centro, direito)
[x] Login com relogging automatico
[x] Auto-login na abertura do bot
[x] Migracao do config.py para src/config/
[x] Dashboard com Char Info, Target Info, checkboxes de funcoes
[x] Per-window state para checkboxes e Start/Stop
[x] SessionRegistry thread-safe
[x] Licenciamento (Key, validacao, demo, status bar)
[x] GameReader (leitura de HP/recurso por analise de pixels)
[x] Dashboard polling (1s) para leitura em tempo real
[x] Logger estruturado (logging + contexto de sessao + arquivo
    rotativo) - ver ADR-003
[x] Testes do nucleo de automacao (BotEngine, ScriptRegistry,
    SessionRegistry, StateManager, EventBus, logging) - 73 testes
[ ] Testes dos workflows (login/servidor/personagem) e da GUI
[ ] Sistema de plugins
[ ] Scripts reais do bot (Attack, Potion, Pet Food, etc.)

FASE 4 - Proximas implementacoes

[ ] Calibracao das regioes de HP/resource com o jogo real
[ ] Sistema de atualizacao (Help > check update)
[ ] Pricing (informacoes de contato/valores)
[ ] Gerenciamento de perfis de conta
[ ] Suporte a mais de 2 contas simultaneas
