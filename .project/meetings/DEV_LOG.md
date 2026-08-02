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