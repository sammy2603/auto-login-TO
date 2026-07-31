# ADR-001

# Interface baseada em Cards

Status

Aceito

Data

Julho de 2026

---

# Contexto

Durante a evolução do Auto Login TO surgiram diversas possibilidades para organizar a interface.

As principais alternativas avaliadas foram:

• Interface baseada em menus.

• Interface baseada em abas.

• Interface baseada em árvore.

• Interface baseada em Cards.

O software possui dezenas de scripts independentes.

Cada script possui:

- configurações;
- estado;
- botão ligar/desligar;
- indicadores;
- informações rápidas.

Era necessário escolher um modelo que facilitasse o gerenciamento simultâneo de diversos módulos.

---

# Problema

Menus escondem funcionalidades.

Abas obrigam o usuário a navegar constantemente.

Árvores dificultam descobrir recursos disponíveis.

Além disso, a utilização simultânea de diversos scripts exige visão global da automação.

---

# Decisão

A interface oficial do Auto Login TO será baseada em Cards.

Cada Script será representado por um Card permanente na tela principal.

O usuário poderá:

- visualizar o estado;
- ligar;
- desligar;
- configurar;
- consultar informações.

Tudo sem trocar de tela.

---

# Motivação

Os Cards oferecem:

• acesso imediato;

• baixa curva de aprendizado;

• excelente escalabilidade;

• ótima organização visual.

Além disso, novos Scripts podem ser adicionados automaticamente sem necessidade de alterar a navegação da aplicação.

---

# Consequências

Positivas

✔ Interface extremamente intuitiva.

✔ Escalabilidade natural.

✔ Facilidade para múltiplos scripts.

✔ Excelente experiência para múltiplas contas.

✔ Layout moderno.

Negativas

Maior consumo de espaço vertical.

Necessidade de um bom sistema de scroll.

Necessidade de agrupamento por categorias futuramente.

---

# Regras

Todo Script deve possuir um Card.

Nenhum Script poderá existir apenas em menus.

Menus serão utilizados apenas para:

- Preferências
- Ferramentas
- Ajuda
- Logs
- Sobre

Nunca para funcionalidades principais.

---

# Impacto na Arquitetura

Cada Card representa um módulo.

O Card nunca executa regras de negócio.

Ele apenas representa visualmente o estado do Script.

Toda comunicação acontece através do AutomationController.

---

# Situação

Aceito.

Esta decisão passa a fazer parte da identidade oficial do Auto Login TO.