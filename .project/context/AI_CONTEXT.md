# AI_CONTEXT.md

# Contexto para Agentes de IA

Se você está lendo este documento, significa que participará do desenvolvimento do Auto Login TO.

Antes de escrever qualquer linha de código, leia este documento completamente.

Seu objetivo é compreender a filosofia, arquitetura e padrões adotados pelo projeto.

---

# Sobre o Produto

O Auto Login TO é um software desktop voltado para automação de tarefas repetitivas no cliente do jogo TO.

O primeiro módulo desenvolvido é o Login Automático.

Entretanto, o produto foi concebido para crescer e se tornar uma plataforma completa de automação.

Nunca trate este projeto como um simples script.

Sempre pense nele como um produto comercial.

---

# Objetivo

Seu papel é ajudar a desenvolver um software:

- modular;
- escalável;
- documentado;
- fácil de manter.

---

# Filosofia

Antes de implementar qualquer funcionalidade, pergunte:

- Qual problema ela resolve?
- Em qual módulo ela pertence?
- Ela respeita a arquitetura?
- Ela aumenta ou reduz a complexidade?

Caso a implementação aumente a complexidade desnecessariamente, procure uma alternativa melhor.

---

# Arquitetura

Este projeto utiliza Arquitetura em Camadas.

Leia obrigatoriamente:

ARCHITECTURE.md

Antes de alterar qualquer módulo.

---

# Documentação

Considere a documentação como parte do código.

Sempre que criar funcionalidades:

Atualize a documentação.

Nunca deixe código e documentação divergentes.

---

# Organização

Cada módulo deve possuir apenas uma responsabilidade.

Evite arquivos grandes.

Evite funções gigantes.

Prefira pequenas responsabilidades.

---

# Padrão de Código

Prefira:

- código explícito;
- nomes claros;
- tipagem;
- reutilização;
- baixo acoplamento.

Evite:

- duplicação;
- números mágicos;
- lógica espalhada;
- dependências desnecessárias.

---

# Decisões Técnicas

Antes de modificar arquitetura:

Consulte os ADRs.

Caso uma nova decisão importante seja tomada, registre um novo ADR.

Nunca sobrescreva decisões anteriores sem justificativa.

---

# Modelo de Negócio

Lembre-se:

Este produto possui uma versão Free e uma versão Premium.

Ao implementar novas funcionalidades, considere se elas pertencem a:

- Free
- Premium

Evite misturar responsabilidades.

---

# Implementação

Sempre siga este fluxo:

Entender

↓

Planejar

↓

Implementar

↓

Testar

↓

Documentar

Nunca pule etapas.

---

# Comunicação

Explique as decisões.

Justifique mudanças.

Sugira melhorias.

Questione quando necessário.

O objetivo não é apenas escrever código.

O objetivo é melhorar continuamente o produto.

---

# Missão

Ajude a construir um software que possa crescer durante anos sem perder organização, qualidade ou escalabilidade.