# ADR-004

# Scripts longos como roteiro de passos

Status

Aceito

---

# Contexto

Os macros antigos do jogo (BC, compra de poção, venda) são sequências
lineares de vários minutos, com centenas de cliques em coordenadas
fixas e esperas entre eles.

O BC completo soma ~650 cliques e mais de 6 minutos de espera
declarada.

---

# Problema

O `tick()` de um script roda no laço compartilhado do `BotEngine`, ao
lado dos outros scripts da mesma conta.

Um script que bloqueie a thread por 6 minutos impede a `Potion` de
rodar — e o personagem morre no boss.

Traduzir os macros linha a linha, com `time.sleep()`, produziria
exatamente isso.

Havia ainda um segundo problema: centenas de coordenadas fixas
espalhadas pela lógica. Elas são o que mais envelhece — qualquer patch
na UI do jogo exige recalibrar tudo.

---

# Decisão

O roteiro vira uma **lista de passos declarativa**, e um `StepRunner`
guarda em que passo está.

Cada `tick()` executa no máximo um passo e devolve o controle.

Uma espera não dorme: anota um prazo, e os ticks seguintes apenas
verificam se venceu.

---

# Estrutura

`src/services/bot/step_runner.py`

↓

`Step` (dado imutável) + `StepRunner` (estado da execução)

`src/services/bot/scripts/bc_steps.py`

↓

O roteiro como DADO: coordenadas, esperas, ordem

`src/services/bot/scripts/bc.py`

↓

Máquina de estados: qual fase montar em seguida

---

# Tipos de passo

Diretos: `left`, `right`, `double_right`, `key`, `key_down`, `key_up`

De espera: `wait`, `wait_color`

De decisão: `skip_if_color`, `retry_until_color`

De laço com condição: `attack_until_dead`, `use_all_items`

Escape: `call`, para lógica que não vira dado

---

# Repetições

`repeat()` expande na MONTAGEM do roteiro, não em tempo de execução.

As repetições dos macros têm contagem constante, então não precisam de
controle de fluxo — expandir mantém o runner simples.

---

# Melhorias sobre os macros originais

Os macros tinham 2 verificações em ~650 ações. O resto contava
segundos e torcia.

`retry_until_color` substitui o `while_not` **com limite**. O original
podia ficar preso para sempre.

`attack_until_dead` lê a vida do alvo, em vez do `repeat 130` cego. Se
o boss cai antes, para; se demora mais, continua.

`use_all_items` acha o item por template e repete enquanto encontrar.
Não se sabe quantas bags o boss dropou, então contar repetições fixas
erra para os dois lados.

---

# Consequências

Scripts longos não bloqueiam mais o motor.

As coordenadas ficam num arquivo de dados: recalibrar é editar uma
tabela.

Um passo que falha é registrado e pulado — não congela o roteiro.

Todo passo de espera com condição tem timeout: seguir sem confirmação
é ruim, travar é pior.

---

# Alternativa descartada

Rodar scripts longos em thread própria, com `sleep` livre.

Descartada porque multiplicaria as threads por sessão, exigiria
sincronizar o acesso ao mesmo `hwnd` e tornaria o "parar o script"
dependente de interromper uma thread no meio de uma espera.

---

# Situação

Aceito.
