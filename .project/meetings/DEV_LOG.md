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

### Concluído — BC: config completa espelhando a referência

- **Correção de nome:** BC é **Bewitcher** Cave, não Battle Cave. Eu
  tinha assumido errado; corrigido em 7 lugares (código e docs).
- O usuário mostrou a UI de um bot de referência, com 4 abas (Main,
  Shortcuts, Potions, Stats). São ~44 campos contra os 17 que eu tinha.
  O diálogo agora espelha essa estrutura.
- **Conhecimento de domínio registrado** (não estava em lugar nenhum):
  - **Gun Witches**: mobs em frente ao boss, última defesa da sala.
    Rota "safe" mata antes de encarar o boss.
  - **Powerfuls**: mobs das duas fileiras do corredor da sala, uma em
    cada parede.
  - **Treasure Box**: caixa no limite final da sala; clique direito e
    espera o casting. **Nascem mobs depois de aberta** -- o roteiro já
    segue lutando.
  - **Manual Pick**: pra quem não tem pet com loot automático; clica no
    corpo do boss pra lotear.
  - **Break Soul**: skill de quem tem mount de combine máximo (+12);
    debuff que reduz a defesa do inimigo.
  - **O boss tem DUAS fases** -- daí a opção de curar entre elas.
  - **Passive Opt. foi descartada** de propósito: seria ficar de TAB
    limpando a sala inteira, em vez de matar só o boss e os guardas.
- **O BC agora cuida da própria vida**: poções normais, battle potions
  e self-heal de Fairy, cada um com limiar. Fica FORA do roteiro de
  passos e roda a cada tick, porque precisar de poção acontece a
  qualquer momento, não num passo específico -- se dependesse da vez,
  o personagem morreria esperando. É o que completa a independência que
  o usuário pediu: não precisa dos cards Potion nem Fairy ligados.
- **AOE por mana**: a skill de AOE só entra na rotação enquanto a mana
  estiver acima do limite. Custa caro, e ficar sem mana no meio do boss
  é pior que matar devagar.
- **Aba Stats**: runs, sucesso/falha, tempo da run atual, da última e
  total, contagem de Courage Badge, botão de reset e auto-reset. Os
  contadores vivem no script (quem sabe que uma run começou é a máquina
  de estados); a GUI só lê, via `get_bot_engine()` -- que NÃO cria
  engine, pra abrir o diálogo não ter efeito colateral.
- Bug que um teste pegou: renomeei `stone_key` → `stone_charm_key` no
  config mas o `voltar_para_stone` ficou com o nome antigo. Daria
  KeyError só na hora de rodar no jogo. Virou trava estrutural:
  `test_toda_chave_lida_pelo_roteiro_existe_no_default` varre o
  `bc_steps.py` atrás de `cfg["x"]` e confere contra o DEFAULT_CONFIG.
- 211 testes no total.

**Ainda pendente:**

- `treasure_box_pos` e `corpo_do_boss_pos` são **palpites centrados na
  tela** -- nenhum macro cobria essas etapas. Precisam de calibração.
- O NPC de saída da cave (nome e coordenadas).
- Nada testado contra o jogo real.

Status:
🟡 Implementado, aguardando teste no jogo

### Concluído — BC (Bewitcher Cave) e o motor de passos

- O BC deixou de ser stub. Traduzidos os 4 macros antigos (~650
  cliques) num ciclo configurável. Ver `ADR-004-Motor-de-Passos.md`.
- **Os macros não eram Lua** -- eram de um gravador de macros
  (`left x,y`, `double_right`, `send_down {f12}`, `findcolor`). Não
  precisou de interpretador; foi tradução conceitual.
- **Motor de passos** (`step_runner.py`): o roteiro virou lista
  declarativa e o runner guarda em que passo está. Cada tick executa um
  passo. Espera não dorme -- anota prazo. É o que permite os ~6 minutos
  do BC sem travar a Potion.
- **Roteiro como dado** (`bc_steps.py`): as coordenadas são o que mais
  envelhece, então ficam numa tabela, longe da lógica.
- **Ciclo configurável**: preparo → [run → reset] ×N → retorno. Ao
  matar o boss, sai pelo NPC que aparece (teleporta pro NPC de entrada)
  e repete a run; só depois da última volta pra cidade e vende.
- **Auto-contido por decisão do usuário**: o BC não conversa com os
  outros scripts nem depende deles. Tem as próprias 4 skills e teclas.
  Ligar o card Attack junto é escolha de quem usa -- o BC não
  interfere nem avisa. Mesma regra vale pro DR Lure.
- **Courage por template matching**, não por cor. O macro procurava a
  cor 5391624 (formato não documentado) e usava UMA vez. Agora acha o
  ícone e repete enquanto encontrar -- não se sabe quantas bags o boss
  dropou, então contagem fixa erra pros dois lados. Precisa do recorte
  `templates/courage_bag.png`.
- Primitivas novas que faltavam: clique direito e duplo-direito (87%
  do macro), `key_down`/`key_up`/`held_key`, F1–F12 (`press_key("F12")`
  levantava ValueError), e checagem de cor de pixel/região.
- Diálogo de configuração na GUI: 4 skills, mount, stone, inventário,
  team, runs por ciclo, repetir, e liga/desliga de comprar/vender/
  courage.
- Achados que os testes pegaram:
  - Eu vinha citando "~75 caminhadas"; o teste falhou com 76.
    Conferido contra o arquivo original: são **76**, e a transcrição
    está idêntica. O errado era minha estimativa.
  - `test_create_instance_ignora_config_de_quem_nao_declara` usava o
    `bc` como exemplo de `has_config=False`. Ao mudar o BC pra
    `True`, o teste continuou passando **sem testar nada** -- trocado
    pro `hollow`.
  - Fixture de template matching com cor uniforme casava em qualquer
    lugar: `TM_CCOEFF_NORMED` é degenerado com variância zero. O
    template de teste passou a ter padrão.
- 67 testes novos (180 no total).

**Pendente:**

- O NPC de saída da cave: o usuário confirmou que existe e teleporta
  pro NPC de entrada, mas o nome e as coordenadas ainda não. A fase de
  `reset` hoje só reconstitui o team.
- As cores herdadas 64511 e 5391624 não foram reaproveitadas -- formato
  não documentado.
- Nada foi testado contra o jogo real. Todas as ~650 coordenadas vêm
  dos macros e assumem 1024x768.

Status:
🟡 Implementado, aguardando teste no jogo

### Concluído — Logger estruturado

- Fecha o item "Logger estruturado" da Fase 3. Ver `ADR-003-Logging.md`
  pro raciocínio completo.
- Saíram 23 `print()` de 10 arquivos; entrou o `logging` da stdlib sob
  a raiz `loginto`, com console + arquivo rotativo (`logs/loginto.log`,
  2 MB × 5, gitignored).
- **Contexto de sessão via `contextvars`**: cada thread de conta abre um
  `session_context(label)` e toda linha logada lá dentro sai
  identificada -- inclusive as que vêm de dentro dos workflows. Um
  `SessionFilter` injeta o campo em todo record.
- O `LogRedirector` foi removido. Ele trocava `sys.stdout` por um
  objeto próprio, o que capturava tudo que fosse impresso no processo
  (inclusive de terceiros) e obrigava a restaurar o stdout na mão,
  contando threads ativas (`_active_threads`/`_active_lock`, também
  removidos). No lugar entrou `src/ui/log_handler.py`, um
  `logging.Handler` de verdade -- o console da GUI virou apenas mais um
  destino.
- Ganhos que não existiam antes:
  - **Traceback completo** nas falhas. O `print(f"...: {e}")` mostrava
    só a mensagem e perdia a pilha, que é justamente o que se precisa.
  - **As threads do BotEngine agora se identificam.** O LogRedirector
    só registrava as threads de conta; log de script saía sem rótulo.
    `BotEngine.start()` passou a aceitar `session_label`.
  - **O console da GUI descarta linhas antigas** (2000). Antes crescia
    sem limite numa sessão longa.
  - **Persistência.** Antes, fechou o app, perdeu o log -- e é depois de
    horas rodando que se precisa investigar.
- `BaseWorkflow` já tinha o ponto de injeção pronto (`__init__` aceitava
  `logger`, `log()` fazia `self.logger.info()`), mas ninguém nunca
  passava um logger, então caía sempre no `print` de fallback. Agora o
  default é `get_logger(f"workflows.{ClassName}")`: preserva a
  identidade que o prefixo dava e mantém a injeção pra teste.
- Achado durante os testes: um teste que chamava `set_session()` sem
  desfazer vazava o rótulo pros testes seguintes, e o sintoma era
  confuso (falhava um teste sem relação com sessão, só porque herdou o
  rótulo). Resolvido com fixture `autouse` no `conftest.py`, na mesma
  linha da que já limpa o `SessionRegistry`.
- 19 testes novos (73 no total). O de threads concorrentes usa
  `threading.Barrier` pra garantir sobreposição real, não confiar em
  sorte de escalonamento.
- **Não testado automaticamente:** o `TextboxLogHandler` em si, porque
  exige Tkinter com display. A validação foi por leitura e por um smoke
  test do caminho completo (BotEngine → filtro → arquivo) sem a GUI.
  Vale conferir o console rodando `python gui.py`.

Status:
🟢 Funcionando

### Concluído — Remoção do código morto da UI

- Removidos `src/ui/widgets/sidebar.py` (Sidebar) e
  `src/ui/widgets/right_panel.py` (RightPanel). Nada no sistema os
  importava -- as únicas ocorrências dos nomes eram as próprias
  definições de classe, uma docstring e entradas históricas deste log.
- Por que incomodavam: ambos tinham lógica PRÓPRIA de Start/Stop
  (`RightPanel._on_action`, `RightPanel._update_action_btn`,
  `Sidebar._toggle`). No diagnóstico do bug acima, a leitura natural é
  supor que são a UI de verdade e investigar ali -- mas quem monta a
  tela é o `main_window.py` direto.
- O diretório `src/ui/widgets/` foi removido junto: ficou vazio, e
  nunca chegou a ter `__init__.py` (não era nem um pacote de fato).
- Duas docstrings obsoletas corrigidas no caminho:
  - `session_registry.py` dizia que "o RightPanel observa mudanças para
    exibir a lista de janelas abertas" -- quem faz isso hoje é o
    polling em `MainWindow._poll_loop`, via
    `AutomationController.state`.
  - `main_window._current_script_configs` dizia que as configs são
    "editadas via os diálogos da sidebar" -- hoje são editadas pelos
    diálogos que abrem no botão de engrenagem de cada `ScriptCard`.
- Verificação: 54 testes passando, `compileall` OK, e
  `import src.ui.main_window` funcionando -- prova direta de que nada
  dependia dos módulos removidos.

Status:
🟢 Funcionando

### Observações pendentes (não tratadas nesta rodada)

- Existem DUAS pastas de ADR: `.project/adr/` (ADR-001, ADR-002 e agora
  ADR-003) e `.project/decisions/` (ADR-0001, com numeração de 4
  dígitos, mais o template e o DECISIONS.md). Convém unificar antes que
  a divergência cresça.
- 5 scripts continuam stubs que retornam `False`: BC, Sell, Hollow,
  Delete e DR Lure.
- `DR Lure` foi REDUZIDO a stub de propósito. A implementação anterior
  (apertar a tecla "8" a cada 30s) não correspondia ao que o script
  deve fazer: manter distância de determinados bosses e conduzi-los
  pelo mapa segurando o aggro, pra que outros personagens ataquem em
  segurança (kiting). Aguarda implementação externa -- vai exigir
  controle de movimento e leitura contínua da distância até o boss,
  que nenhum script faz hoje.

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