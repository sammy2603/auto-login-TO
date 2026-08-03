# ADR-003

# Logging estruturado com contexto de sessão

Status

Aceito

---

# Contexto

O projeto usava `print()` espalhado por 23 pontos em 10 arquivos.

A GUI capturava essa saída trocando `sys.stdout` por um objeto próprio
(`LogRedirector`), que bufferizava por thread e prefixava cada linha
com o apelido da conta, mapeando `thread ident -> label`.

Funcionava, mas era o único caminho possível de log.

---

# Problema

O `print()` não oferece:

- níveis (não dá para calar detalhe sem perder erro);
- timestamp;
- origem da mensagem;
- traceback (só a mensagem da exceção, perdendo a pilha);
- persistência — fechou o app, perdeu o log.

E o `LogRedirector` trazia problemas próprios:

- capturava **tudo** que fosse impresso no processo, inclusive de
  bibliotecas de terceiros;
- obrigava a restaurar `sys.stdout` na mão quando a última conta
  terminava, com contagem manual de threads ativas;
- não limitava o crescimento do console;
- não identificava as threads do `BotEngine`, só as de conta.

O ponto mais grave: **sem persistência**. Quando algo quebrava depois
de horas rodando, não havia o que investigar.

---

# Decisão

Adotar o módulo `logging` da biblioteca padrão, com uma árvore de
loggers sob a raiz `loginto`.

O contexto de sessão passa a viajar por `contextvars`, e um filtro
injeta o rótulo em todo `LogRecord`.

---

# Estrutura

`src/infrastructure/logging/models.py`

↓

ContextVar do rótulo + `session_context()` + `SessionFilter`

`src/infrastructure/logging/service.py`

↓

`LoggingService.setup()` — console + arquivo rotativo

`src/ui/log_handler.py`

↓

`TextboxLogHandler` — o console da GUI

---

# Por que ContextVar e não thread-local

Uma thread nova começa com contexto **vazio**: não herda o da thread
que a criou.

É exatamente o comportamento desejado — cada thread de conta declara o
próprio rótulo e não vaza para as outras.

Um vazamento aqui seria pior que não ter rótulo: os logs de uma conta
apareceriam com o nome de outra.

---

# Camadas

A infraestrutura **não** conhece a GUI.

`LoggingService` configura apenas console e arquivo.

Quem quiser exibir log numa interface anexa o próprio handler via
`add_handler()`, que aplica o filtro de sessão automaticamente — deixar
isso a cargo de quem chama faria `%(session)s` quebrar com `KeyError`.

---

# Consequências

Todo módulo pede `get_logger(__name__)`.

Toda thread de conta ou de motor de scripts abre um `session_context`.

O `sys.stdout` deixa de ser sequestrado.

O console da GUI vira apenas mais um destino, ao lado do terminal e do
arquivo.

Logs passam a viver em `logs/loginto.log`, rotacionando em 2 MB com 5
arquivos de retenção.

---

# Benefícios

✔ Níveis: dá para calar detalhe sem perder erro.

✔ Traceback completo nas falhas.

✔ Persistência para investigar depois.

✔ Toda linha identifica a conta de origem, inclusive as do BotEngine —
que antes saíam sem rótulo nenhum.

✔ O console da GUI passa a descartar linhas antigas, em vez de crescer
sem limite.

---

# Situação

Aceito.
