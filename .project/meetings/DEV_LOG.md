## 2026-07-27

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
