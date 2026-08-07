# Migração dos identificadores para inglês

**Regra**: identificadores em inglês; comentários, docstrings e arquivos
de contexto em português. Isso vale para funções, parâmetros, variáveis,
chaves de configuração, nomes de teste e nomes de template.

**Por que em fatias e não numa passada**: `bc_steps.py` tem 31 funções
das quais o resto do roteiro depende, e `step_runner.py` exporta os
nomes que aparecem em toda chamada de passo. Renomear tudo de uma vez dá
um diff que ninguém revisa e que, se estiver errado num ponto, esconde o
erro no meio de outros mil. Cada fatia abaixo fecha com a suíte verde.

## Levantamento (2026-08-06)

40 funções e 7 parâmetros em `src/` com nome em português, além das ~80
chaves do `DEFAULT_CONFIG`, das variáveis locais e dos nomes de teste.

| arquivo | funções | parâmetros |
|---|---|---|
| `src/services/bot/scripts/bc_steps.py` | 31 | 0 |
| `src/services/bot/step_runner.py` | 5 | 3 |
| `src/services/game/memory_reader.py` | 2 | 1 |
| `src/ui/main_window.py` | 2 | 0 |
| `src/services/game/npcs.py` | 0 | 2 |
| `src/services/bot/scripts/bc.py` | 0 | 1 |

## Ordem das fatias

A ordem é de baixo para cima: quem é importado por mais gente vai
primeiro, senão a fatia de cima renomeia e a de baixo desfaz.

1. **`step_runner.py`** — o motor. Funções (`esperar_parado`,
   `esperar_ate`, `pular_se`, `pular_se_template`, `esperar_template`,
   `retry_until_color`) e os parâmetros nomeados que aparecem em toda
   chamada (`tolerancia`, `centro`, `raio`, `escala`, `tentativa`,
   `vezes`, `condicao`).
2. **`memory_reader.py` e `npcs.py`** — leitura de memória e catálogo.
3. **`bc_steps.py`** — as 31 funções de passo.
4. **`bc.py`** — chaves do `DEFAULT_CONFIG`. É a fatia mais arriscada:
   o teste de trava estrutural (`test_bc_script.py`) confere que toda
   chave lida existe no dicionário, então chave renomeada num lado e não
   no outro aparece na suíte — mas só se a suíte rodar.
5. **`tools/`** e **nomes de teste**.
6. **`src/ui/`**.

## Cuidados

- **Strings não são identificadores**: `"Bewitcher Cave"`, `"Stone City"`
  e os nomes de template (`enter_bc`) são dados do jogo ou nomes de
  arquivo em `templates/`. Renomear template exige renomear o `.png`.
- **`kind` dos passos** (`"walk_to"`, `"wait_stopped"`, ...) já está em
  inglês e é comparado por string em `step_runner` e nos testes.
- **Coordenadas e medições** ficam como estão: são dados medidos no jogo,
  não código.
- Cada fatia roda `python -m pytest tests/ -q` antes do commit.
