## 2026-08-03

### Corrigido — scripts rodavam com o switch desligado

- Sintoma: ao selecionar um client e clicar em **Start Scripts**, o
  Attack (e todos os outros) executava mesmo com o switch do card
  desligado -- ou seja, o bot atacava sem ninguém ter pedido.
- Duas causas encadeadas:
  1. `bot_engine.py` tratava a AUSÊNCIA de flag como "ligado por
     padrão" (`if var is not None and not var.get(): continue` --
     quando `var` era `None`, o script rodava).
  2. `main_window._on_script_toggle` nunca criava o dict
     `_feature_vars[win]`, porque a condição `win in self._feature_vars`
     jamais era verdadeira. Nenhum script chegava a ter flag
     registrada, então todos caíam no caso `None` acima.
- Correção: default seguro (sem flag = desligado), `setdefault` no
  toggle, botão **Start Scripts** desabilitado enquanto nenhum script
  estiver ligado, e um messagebox de aviso como guard defensivo em
  `_start_bot_for_window`.
- PR: https://github.com/sammy2603/auto-login-TO/pull/1

Status:
🟢 Funcionando

### Concluído — Suíte de testes do núcleo

- Os 4 arquivos em `tests/` estavam VAZIOS (0 bytes) e o `pytest` não
  estava instalado nem declarado. Cobertura real era zero -- foi
  exatamente por isso que o bug acima passou.
- 54 testes cobrindo `BotEngine`, `ScriptRegistry`, `SessionRegistry`,
  `StateManager` e `EventBus`. Rodam em ~2s, **sem** win32, OpenCV,
  Tkinter ou cliente do jogo aberto.
- Refactor mínimo pra viabilizar: o gating saiu de dentro do `_loop`
  pro método estático `BotEngine.is_script_enabled()`. A regra que
  causou o bug agora é uma função pura, testável direto.
- Os testes de regressão foram VALIDADOS reintroduzindo o bug de
  propósito: 4 falham (incluindo o de integração do loop), 8 passam.
  Teste de regressão que não falha com o bug presente não vale nada.
- Escolhas de teste que valem registro:
  - `conftest.Flag` é um dublê de `ctk.BooleanVar` (só precisa de
    `.get()`), o que mantém a suíte livre de Tkinter -- que exigiria
    display e root window.
  - `SessionRegistry` guarda estado em atributos de CLASSE, então é
    global ao processo. Uma fixture `autouse` limpa
    `_sessions`/`_observers`/`_event_bus` entre os testes, mexendo em
    privados de propósito (não há reset público).
  - `test_name_da_instancia_bate_com_o_display_name` amarra as duas
    pontas do gating: o `script.name` que o engine casa e o
    `display_name` que a GUI usa pra montar as flags. Se divergirem, o
    script nunca liga (ou nunca desliga) -- e nada mais no sistema
    reclamaria.
- `pytest` foi pro novo `requirements-dev.txt` (não pro
  `requirements.txt`) pra manter o runtime enxuto. `pytest.ini` fixa
  `pythonpath = .` e `testpaths = tests`.
- Os 4 arquivos vazios originais (`test_application.py`,
  `test_container.py`, `test_game_client.py`, `test_login_workflow.py`)
  foram MANTIDOS vazios: cobrem workflows/container, que exigem win32 e
  dublês bem mais pesados. Ficam como próximo passo declarado no
  BACKLOG.

Status:
🟢 Funcionando

### Observações pendentes (não tratadas nesta rodada)

- `src/ui/widgets/sidebar.py` e `src/ui/widgets/right_panel.py` são
  **código morto** -- nada os importa. Ambos têm lógica própria de
  Start/Stop, o que atrapalhou o diagnóstico do bug acima (a leitura
  natural é achar que são a UI real, mas quem monta a tela é o
  `main_window.py` direto).
- `AGENTS.md` está desatualizado: a seção "Key files" ainda lista
  `main.py`, `window_utils.py`, `vision.py` e `input_utils.py` como
  arquivos centrais, mas os três últimos foram removidos na Fase 2.
- 4 scripts continuam stubs que retornam `False`: BC, Sell, Hollow,
  Delete.

## 2026-08-01 (4)

### Concluído — StateManager

- Criado `src/app/state_manager.py`: terceiro dos "Próximos
  Componentes" listados em `01_Architecture.md`. Não guarda estado
  por conta própria -- é uma fachada de consulta que combina
  `SessionRegistry` (dados de conexão) com `AutomationController`
  (se os scripts da sessão estão rodando), pra não precisar combinar
  as duas fontes manualmente toda vez.
- `SessionRegistry` ganhou `bind_event_bus()` e agora publica
  `session.registered`/`session.unregistered` no EventBus
  compartilhado, além do observer genérico que já existia
  (`observe`/`_notify`, mantido por compatibilidade).
- `main_window.py`: o polling da lista de clients agora usa
  `controller.state.get_all_sessions()`. O "pontinho" de status de
  cada card passou a diferenciar **online parado** (azul) de
  **online rodando script** (verde) -- antes só existia um estado
  "online", sem indicar se havia algum script ativo.
- Nota de camada: `state_manager.py` (em `src/app/`) importa
  `SessionRegistry` de `src/ui/session_registry.py`. Isso funciona
  (sem import circular) mas é um pouco estranho: SessionRegistry é,
  na prática, mais uma preocupação de aplicação/sessão do que de UI.
  Não movi o arquivo agora pra não arriscar quebrar os vários lugares
  que já importam de lá -- mas vale reavaliar essa localização numa
  limpeza futura.

Status:
🟢 Funcionando

**Atualização (mesmo dia):** fechado o ponto pendente da nota de
camada acima -- os 9 lugares em `main_window.py` que ainda chamavam
`SessionRegistry` diretamente (registro/leitura/remoção de sessão em
`_scan_for_game_windows`, `_run_account_loop`, etc) agora passam por
`AutomationController.register_session()`/`unregister_session()`/
`get_sessions()`. O import direto de `SessionRegistry` foi removido de
`main_window.py` -- a GUI só conversa com o Controller agora, em
qualquer caminho.



### Concluído — EventBus

- Criado `src/shared/event_bus.py`: barramento de eventos simples
  (publish/subscribe), thread-safe, segundo dos "Próximos Componentes"
  listados em `01_Architecture.md`.
- `AutomationController` agora publica `bot.started`/`bot.stopped`
  (ao ligar/desligar scripts) e `session.forgotten` (ao limpar uma
  sessão desconectada).
- `main_window.py` assina esses eventos e atualiza o botão
  Start/Stop **instantaneamente**, em vez de esperar o próximo ciclo
  do polling (até 500ms de atraso antes).
- Escopo desta rodada, de propósito: só os eventos de início/fim de
  script. HP/MP e contagem de online continuam vindo do polling
  existente -- são valores contínuos/amostrados, não fazem sentido
  como evento discreto. Publicar eventos de sessão (conta
  conectada/desconectada) fica como próximo passo natural, se
  precisarmos.

Status:
🟢 Funcionando



### Concluído — ScriptRegistry

- Criado `src/services/bot/script_registry.py`: catálogo central dos
  Scripts da plataforma (`ScriptDescriptor` + `ScriptRegistry`),
  primeiro dos "Próximos Componentes" listados em `01_Architecture.md`.
- Antes: adicionar/remover um script exigia editar manualmente 4
  lugares (`FEATURES`, `COLORS`, `ICONS` em `main_window.py`, e o
  registro hardcoded dentro do `AutomationController`). Agora, é uma
  linha só em `register_builtin_scripts()`.
- `AutomationController.get_or_create_bot_engine()` agora itera
  `ScriptRegistry.all()` em vez de importar/registrar cada script na
  mão.
- `main_window.py` deriva `FEATURES`/`COLORS`/`ICONS` do registro. A
  cor de cada script vem de uma categoria semântica (`combat`,
  `support`, `companion`, etc) definida no descriptor -- o catálogo de
  scripts (camada `services`) continua sem nenhum conhecimento da UI,
  só a GUI traduz categoria -> cor via `CATEGORY_COLORS`.

Status:
🟢 Funcionando

## 2026-08-01

### Concluído — Introdução do AutomationController

- Criado `src/app/automation_controller.py`, único ponto de comunicação
  entre a GUI e o núcleo de automação, conforme `01_Architecture.md`.
- Corrigida violação: `main_window.py` construía `WindowService`,
  `VisionService`, `InputService` e `BotEngine` diretamente dentro de
  `_start_bot_for_window()` toda vez que um script era ligado.
- `AutomationController` agora mantém as instâncias únicas e
  compartilhadas de `WindowService`/`VisionService`/`InputService` do
  processo (stateless em relação a qual janela operam), um `BotEngine`
  por sessão, e centraliza foco de janela (`focus_window`) e
  renomeação (`rename_window`) -- incluindo o fallback de
  `AttachThreadInput` para contornar a restrição do Windows contra
  "roubo" de foco.
- `main_window.py` não importa mais `WindowService`, `VisionService`,
  `InputService`, `BotEngine` nem os scripts individuais -- só
  `AutomationController`.
- Pendências conscientes (não migradas nesta rodada, escopo
  intencionalmente limitado à violação relatada): chamadas pontuais a
  `win32gui.IsWindow()` (checagem trivial de existência) e construção
  direta de `MemoryReader` para *probing* de janelas externas ainda
  recém-detectadas (`_scan_for_game_windows`, `_run_account_loop`).

Status:
🟢 Funcionando



### Concluido — Fase 4: Bot Engine + Pricing + Help
- BotEngine: motor de scripts em loop (thread separada), protocolo BotScript
- Scripts exemplo: Attack (ataca alvo via Tab + tecla 1), Potion (usa pocao
  quando HP < 55%)
- Pricing: dialogo modal com tiers Free/Premium e contato
- Help: dialogo com versao 0.2.0 e botao "Verificar Atualizacao"
  (consulta GitHub Releases)
- Start/Stop conectado ao BotEngine: inicia/para scripts para a janela
  selecionada no painel direito
- Bot engine parado automaticamente ao deslogar/fechar janela

### Proxima etapa
- Calibracao das regioes de HP/resource com o jogo real
- Scripts adicionais (Pet Food, Buff, Helper, Fairy, Revive,
  Delete, BC, Hollow, Sell, DR Lure)
- Tool de calibracao visual para regioes de HP

### Fase 3: Licenciamento + GameReader
- LicenseService: validacao de chave, demo (30d), expiracao, persistencia
- Aba Key: input de chave, status (demo/ativa/expirada), dias, tier
- Status bar com dados reais da licenca
- GameReader: leitura de HP/recurso via analise de pixels
- Dashboard: polling 1s para leitura em tempo real

### Fase 2: Dashboard + Start/Stop
- Aba Dashboard (Char Info, Target Info, Funcoes, Log)
- 12 checkboxes de funcoes com estado por janela
- Sidebar: clica em funcao → abre Dashboard + destaca linha
- RightPanel conectado ao Dashboard e Start/Stop

### Fase 1: Layout 3 paineis
- SessionRegistry, Sidebar (15 itens), RightPanel
- Top bar (List, Config, Login, Pricing, Help)
- Tema escuro, status bar, Home com login/relogging/auto-login

## 2026-07-21

### Commit 0018

- Criado VisionService
- Integrado ao GameClient
- LoginWorkflow nao depende mais de vision.py

Status:
🟢 Funcionando

## 2026-07-20

### Concluido
- Estrutura da aplicacao finalizada.
- ServiceContainer implementado.
- Application implementado.
- AutomationEngine implementado.

### Proxima etapa
- Migrar conexao com a janela para o LoginWorkflow.