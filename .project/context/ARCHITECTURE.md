# ARCHITECTURE.md

# Arquitetura do Auto Login TO

## Objetivo

Este documento descreve a arquitetura oficial do Auto Login TO.

Seu propósito é garantir que todas as funcionalidades futuras sejam implementadas de forma consistente, organizada e escalável.

---

# Filosofia

O Auto Login TO é desenvolvido utilizando uma arquitetura modular baseada em responsabilidades.

Cada componente do sistema possui uma única responsabilidade bem definida.

Essa separação reduz o acoplamento entre módulos e facilita testes, manutenção e evolução do software.

---

# Princípios Arquiteturais

- Responsabilidade única (Single Responsibility Principle)
- Baixo acoplamento
- Alta coesão
- Modularização
- Reutilização
- Facilidade de manutenção
- Facilidade de testes

---

# Arquitetura em Camadas

Presentation Layer

↓

Application Layer

↓

Domain Layer

↓

Infrastructure Layer

---

# Camadas

## Presentation

Responsável pela interação com o usuário.

Exemplos:

- Interface gráfica
- CLI
- Configuração

Esta camada nunca conversa diretamente com a API do Windows.

---

## Application

Responsável por coordenar o funcionamento do software.

Ela contém o Automation Engine.

Esta camada decide:

- quando procurar a janela;
- quando realizar o login;
- quando capturar imagens;
- quando encerrar o processo.

Ela nunca acessa bibliotecas diretamente.

---

## Domain

Contém as regras de negócio.

Exemplos:

- Fluxo de login
- Estados da automação
- Validação
- Perfis

Toda lógica do produto deve ficar aqui.

---

## Infrastructure

Responsável por toda comunicação externa.

Exemplos:

- OpenCV
- PyWin32
- ctypes
- Arquivos
- JSON
- Sistema Operacional

Caso uma biblioteca seja substituída no futuro, apenas esta camada deverá sofrer alterações.

---

# Serviços

O sistema será dividido em serviços especializados.

## Window Service

Responsável por localizar e controlar a janela do jogo.

---

## Input Service

Responsável por enviar teclado e mouse.

---

## Vision Service

Responsável por localizar elementos utilizando imagens.

---

## Config Service

Responsável pelas configurações.

---

## Logger Service

Responsável pelos logs.

---

## License Service

Responsável pela validação das licenças.

---

## Update Service

Responsável pelas atualizações do software.

---

# Automation Engine

O Automation Engine representa o cérebro do sistema.

Ele coordena todos os serviços.

Nenhum serviço deve conhecer outro serviço diretamente.

Toda comunicação deverá passar pelo Engine.

---

# Dependências

A direção das dependências deve seguir esta regra:

Presentation

↓

Application

↓

Domain

↓

Infrastructure

Nunca o contrário.

---

# Objetivo Final

Construir uma plataforma escalável onde novas funcionalidades possam ser adicionadas sem modificar a arquitetura existente.