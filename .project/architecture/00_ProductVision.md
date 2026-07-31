# Auto Login TO

> Product Vision Document (PVD)

Versão: 1.0

Status: Oficial

---

# 1. Visão

O Auto Login TO é uma plataforma de automação para clientes de jogos MMORPG.

Seu objetivo é oferecer uma solução modular, escalável e profissional para gerenciamento de múltiplos clientes, permitindo que diversas automações sejam executadas de forma organizada, segura e independente.

O projeto não é apenas um Auto Login.

O Auto Login é apenas um dos módulos disponíveis dentro da plataforma.

---

# 2. Missão

Desenvolver a melhor plataforma de automação para jogos baseada em visão computacional, arquitetura modular e experiência de usuário intuitiva.

O software deve ser capaz de controlar dezenas de clientes simultaneamente mantendo simplicidade para o usuário e organização para o desenvolvedor.

---

# 3. Filosofia

O projeto é baseado em cinco pilares.

## Simplicidade

O usuário deve conseguir utilizar o software sem estudar um manual.

As principais funcionalidades devem estar disponíveis na tela principal.

Nenhuma configuração importante deve ficar escondida em menus profundos.

---

## Modularidade

Toda funcionalidade é um módulo independente.

Exemplos:

- Login
- Buff
- Loot
- Farm
- Party
- Merchant
- Scheduler

Cada módulo pode evoluir independentemente dos demais.

---

## Escalabilidade

A arquitetura deve suportar naturalmente:

- uma conta
- cinco contas
- vinte contas
- cem contas

Sem necessidade de alterações estruturais.

---

## Desacoplamento

Cada componente possui uma responsabilidade única.

A comunicação entre módulos acontece através de interfaces bem definidas.

Nenhuma camada deve conhecer detalhes internos de outra camada.

---

## Manutenibilidade

O código deve ser escrito pensando nos próximos cinco anos.

Toda decisão arquitetural deve favorecer manutenção futura ao invés de atalhos de curto prazo.

---

# 4. Objetivos

Os objetivos principais do produto são:

- Automatizar tarefas repetitivas.
- Gerenciar múltiplos clientes.
- Centralizar configurações.
- Reduzir intervenção manual.
- Facilitar criação de novos módulos.
- Permitir expansão através de plugins.

---

# 5. O que o projeto NÃO é

O Auto Login TO não pretende ser:

- Um conjunto de scripts independentes.
- Um bot monolítico.
- Uma coleção de macros.
- Um software focado em apenas um servidor específico.

Toda a arquitetura deve permanecer genérica o suficiente para permitir evolução futura.

---

# 6. Público-alvo

Jogadores que utilizam múltiplos clientes simultaneamente e desejam automatizar tarefas repetitivas de maneira organizada.

Também atende desenvolvedores responsáveis pela evolução da plataforma.

---

# 7. Diferenciais

O projeto diferencia-se por:

- Arquitetura modular.
- Separação clara entre Engine e Interface.
- Sistema baseado em sessões.
- Scripts independentes.
- Interface baseada em Cards.
- Forte preocupação com engenharia de software.

---

# 8. Princípios

Todas as decisões futuras devem respeitar os seguintes princípios.

## GUI representa o estado da Engine.

A interface nunca executa regras de negócio.

---

## Scripts são módulos.

Cada Script possui identidade própria.

---

## Sessões representam clientes.

Toda configuração pertence à Sessão.

---

## A Engine independe da Interface.

A Engine deve continuar funcionando mesmo sem GUI.

---

## O usuário trabalha sobre Sessões.

Nunca diretamente sobre GameClient ou Workflows.

---

# 9. Visão de Longo Prazo

O Auto Login TO deve evoluir para uma plataforma completa de automação contendo:

- Script Engine
- Workflow Engine
- Scheduler
- Sistema de Plugins
- Marketplace
- Atualizador
- Sistema de Licenciamento
- Telemetria
- Perfil por Personagem
- Configuração por Conta

---

# 10. Estado Atual

Versão arquitetural:

Auto Login TO 1.0

Situação:

Em consolidação da arquitetura.

Próximo objetivo:

Concluir estabilização da GUI e introduzir o AutomationController.

---

Fim do Documento.