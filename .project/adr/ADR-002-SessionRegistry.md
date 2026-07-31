# ADR-002

# Toda automação é baseada em Sessões

Status

Aceito

---

# Contexto

Inicialmente o sistema trabalhava diretamente com GameClient.

Com a introdução do suporte a múltiplos clientes tornou-se necessário um novo nível de abstração.

---

# Problema

GameClient representa apenas comunicação com o jogo.

Ele não representa:

- personagem;
- servidor;
- configurações;
- scripts ativos;
- estado.

---

# Decisão

Toda automação será baseada em GameSession.

GameSession representa um cliente completo.

Ela torna-se a unidade principal da plataforma.

---

# Estrutura

GameSession

↓

Process

↓

HWND

↓

Account

↓

Character

↓

Scripts

↓

Configuration

↓

Statistics

↓

State

---

# Consequências

Todo Script trabalha sobre uma Sessão.

Toda configuração pertence à Sessão.

A GUI sempre edita a Sessão ativa.

Nunca diretamente o GameClient.

---

# Benefícios

✔ Excelente suporte a múltiplos clientes.

✔ Perfis independentes.

✔ Estatísticas independentes.

✔ Configuração por personagem.

✔ Escalabilidade.

---

# Situação

Aceito.