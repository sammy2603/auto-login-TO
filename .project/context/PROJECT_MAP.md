# PROJECT MAP

> Mapa de navegação: onde cada coisa mora.
>
> Para o *porquê* das decisões, ver `01_Architecture.md` (arquitetura
> oficial), `PROJECT_CONTEXT.md` (visão do produto) e o
> `.project/meetings/DEV_LOG.md` (histórico).

## Entradas da aplicação

gui.py → MainWindow
(aplicativo gráfico — uso principal)

main.py → Application → AutomationEngine
(login único por terminal, sem interface)

## Fluxo de comunicação

GUI
↓ (única porta de entrada)
AutomationController
↓
BotEngine / AutomationEngine
↓
GameClient
↓
WindowService / VisionService / InputService
↓
Sistema Operacional

Regra: a GUI nunca constrói nem chama Services, GameClient, BotEngine
ou workflows diretamente.

## Presentation

| Componente | Arquivo |
|---|---|
| MainWindow (monta a tela inteira) | `src/ui/main_window.py` |
| ScriptCard (card de script) | `src/ui/main_window.py` |
| SessionRegistry (contas conectadas) | `src/ui/session_registry.py` |

## Automation

| Componente | Arquivo |
|---|---|
| AutomationController (a porta) | `src/app/automation_controller.py` |
| Application (bootstrap) | `src/app/application.py` |
| ServiceContainer (DI) | `src/app/container.py` |
| StateManager (visão combinada) | `src/app/state_manager.py` |
| AutomationEngine (orquestra o login) | `src/app/automation_engine.py` |
| BotEngine (loop de scripts) | `src/services/bot/bot_engine.py` |
| ScriptRegistry (catálogo) | `src/services/bot/script_registry.py` |
| StepRunner (roteiros longos) | `src/services/bot/step_runner.py` |
| EventBus (publish/subscribe) | `src/shared/event_bus.py` |

## Workflows

| Workflow | Arquivo |
|---|---|
| Base | `src/domain/workflows/base_workflow.py` |
| Login | `src/domain/workflows/login_workflow.py` |
| Seleção de servidor | `src/domain/workflows/server_workflow.py` |
| Entrada com personagem | `src/domain/workflows/character_workflow.py` |

## Fachadas e leitura do jogo

| Componente | Arquivo |
|---|---|
| GameClient (fachada oficial) | `src/services/game/game_client.py` |
| GameSession | `src/services/game/game_session.py` |
| MemoryReader (HP/alvo/posição) | `src/services/game/memory_reader.py` |
| GameReader (leitura por pixels) | `src/services/game/game_reader.py` |
| LicenseService | `src/services/license/service.py` |

Catálogo de offsets de memória e o que fazer quando o cliente atualizar:
[`.project/context/PONTEIROS.md`](PONTEIROS.md).

## Infraestrutura

| Serviço | Arquivo |
|---|---|
| WindowService | `src/infrastructure/window/service.py` |
| VisionService | `src/infrastructure/vision/service.py` |
| InputService | `src/infrastructure/input/service.py` |
| LoggingService | `src/infrastructure/logging/service.py` |
| Contexto de sessão do log | `src/infrastructure/logging/models.py` |
| Console da GUI (handler) | `src/ui/log_handler.py` |
| GameLauncher | `src/infrastructure/game/launcher.py` |
| Interfaces (contratos) | `src/core/interfaces/` |

Logging: todo módulo faz `logger = get_logger(__name__)`. Toda thread
de conta ou de motor de scripts abre um `session_context(label)`, pra
que cada linha diga de qual conta veio. Saída em console, em
`logs/loginto.log` (rotativo, gitignored) e no console da GUI. Ver
`ADR-003-Logging.md`.

## Scripts de gameplay

Todos em `src/services/bot/scripts/`, registrados em
`script_registry.py`.

Implementados: attack, potion, pet_food, buff, helper, fairy, revive,
bc

Stubs (retornam `False`): hollow, sell, delete, dr_lure

O **BC** é o único que usa o `StepRunner`: o ciclo dele tem ~900
passos e vários minutos, então o roteiro vive como dado em
`scripts/bc_steps.py` e a máquina de estados em `scripts/bc.py`. Ver
`ADR-004-Motor-de-Passos.md`. Scripts curtos continuam implementando
`tick()` direto.

Para adicionar um script: criar a classe (com `name` e `tick()`,
conforme o protocolo `BotScript`) e adicionar UMA linha em
`register_builtin_scripts()`. O `name` da instância precisa ser igual
ao `display_name` do descriptor.

## Configuração

| O quê | Onde |
|---|---|
| Fonte da verdade (`Settings`) | `src/config/settings.py` |
| Credenciais | `.env` (gitignored) |
| Contas salvas | `accounts.json` (gitignored) |
| Caminho do client | `gui_settings.json` (gitignored) |
| Licença | `license.json` |

`config.py` na raiz é apenas um **shim de compatibilidade** que
re-exporta `Settings` como constantes, mantido para os scripts em
`tools/`. Código novo importa `src.config.settings` direto.

## Estado — quem é dono do quê

| Estado | Dono |
|---|---|
| Sessões ativas | SessionRegistry |
| Visão combinada da sessão | StateManager |
| Catálogo de scripts | ScriptRegistry |
| Configuração | Settings |
| Scripts ligados por conta | `MainWindow._feature_vars` |

## Testes

`tests/` — suíte do núcleo (BotEngine, ScriptRegistry,
SessionRegistry, StateManager, EventBus, logging). Roda sem win32,
OpenCV, Tkinter ou cliente aberto.

Sem cobertura ainda: workflows, container, GUI. Os arquivos
`test_application.py`, `test_container.py`, `test_game_client.py` e
`test_login_workflow.py` existem vazios, reservando o lugar.

## Utilitários

`tools/` — scripts avulsos de depuração: descoberta de janela e
classe, teste de clique e foco, captura de tela, calibração de HP,
varredura de memória, inspeção de controles.
