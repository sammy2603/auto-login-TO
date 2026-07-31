# Auto Login TO

# Software Architecture Document

Versão: 1.0

Status: Oficial

---

# 1. Objetivo

Este documento define oficialmente a arquitetura do Auto Login TO.

Toda implementação futura deverá respeitar os princípios aqui estabelecidos.

A arquitetura foi projetada para garantir:

- modularidade;
- escalabilidade;
- baixo acoplamento;
- alta coesão;
- facilidade de manutenção.

---

# 2. Visão Geral

O Auto Login TO é dividido em três grandes camadas.

                Presentation

                      │

                      ▼

             Automation Engine

                      │

                      ▼

              Infrastructure

Cada camada possui responsabilidades bem definidas.

Nenhuma camada deve assumir responsabilidades pertencentes a outra.

---

# 3. Camadas

## Presentation Layer

Responsável pela interface gráfica.

Contém:

- MainWindow
- Widgets
- Dialogs
- Themes
- Controllers

Responsabilidades:

- apresentar informações;
- receber ações do usuário;
- encaminhar comandos ao Controller.

Nunca:

- localizar templates;
- enviar teclas;
- clicar no jogo;
- executar workflows.

---

## Automation Layer

Representa o núcleo do software.

É responsável por:

- gerenciamento das sessões;
- execução de scripts;
- workflows;
- gerenciamento de estado;
- automações.

Esta camada representa a inteligência do sistema.

---

## Infrastructure Layer

Responsável pela comunicação com o mundo externo.

Inclui:

WindowService

VisionService

InputService

GameClient

GameLauncher

Filesystem

License

Telemetry

Updater

Não contém regras de negócio.

---

# 4. Fluxo de Comunicação

A comunicação oficial do sistema segue o fluxo abaixo.

GUI

↓

AutomationController

↓

Automation Engine

↓

GameClient

↓

Services

↓

Sistema Operacional

Comunicações diretas entre GUI e Services não são permitidas.

---

# 5. Game Session

A menor unidade funcional do sistema é uma Sessão.

Uma Sessão representa exatamente um cliente do jogo.

Cada sessão possui:

- Processo
- PID
- HWND
- Conta
- Personagem
- Servidor
- Scripts
- Configurações
- Estado

Toda configuração pertence à Sessão.

---

# 6. Scripts

Scripts representam módulos independentes da plataforma.

Exemplos:

- Login
- Buff
- Loot
- Farm
- Party
- Merchant

Cada Script contém:

Descriptor

Configuration

Workflow

Executor

Widget

State

Nenhum Script deve depender diretamente de outro Script.

---

# 7. Workflows

Workflows representam fluxos de execução.

Exemplo:

Login Workflow

↓

Abrir Cliente

↓

Conectar Janela

↓

Esperar Login

↓

Preencher Usuário

↓

Preencher Senha

↓

Entrar

Cada Workflow possui responsabilidade única.

---

# 8. GameClient

GameClient representa a fachada oficial de interação com o jogo.

Nenhum Workflow deve acessar diretamente:

WindowService

VisionService

InputService

Launcher

Toda comunicação deve acontecer através do GameClient.

---

# 9. Services

Os Services encapsulam operações específicas.

Cada Service possui responsabilidade única.

Exemplo:

WindowService

↓

Janela

VisionService

↓

Visão Computacional

InputService

↓

Mouse e Teclado

Launcher

↓

Inicialização

---

# 10. Estado

Todo estado do sistema deverá possuir um único responsável.

Exemplo:

Sessão Ativa

↓

SessionRegistry

Configurações

↓

SettingsManager

Scripts

↓

ScriptRegistry

Estado Global

↓

StateManager

---

# 11. Princípios Arquiteturais

O projeto adota oficialmente os seguintes princípios.

Single Responsibility

Dependency Injection

Low Coupling

High Cohesion

Composition over Inheritance

Single Source of Truth

---

# 12. Regras

É proibido:

GUI acessar VisionService.

GUI acessar WindowService.

GUI acessar InputService.

GUI acessar Workflows.

GUI acessar diretamente GameClient.

---

É obrigatório:

Toda comunicação passar pelo Controller.

---

# 13. Escalabilidade

A arquitetura foi projetada para suportar:

- múltiplos clientes;
- múltiplos scripts;
- múltiplos perfis;
- plugins;
- marketplace;
- scheduler.

Sem alterações estruturais.

---

# 14. Próximos Componentes

Os seguintes componentes fazem parte da arquitetura oficial.

AutomationController

StateManager

EventBus

ScriptRegistry

WorkflowRegistry

TaskScheduler

PluginManager

---

Fim do Documento.