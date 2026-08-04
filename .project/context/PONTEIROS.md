# Ponteiros de memória — Talisman Online

Referência consolidada dos endereços de memória conhecidos, para não
refazermos a mesma caça a cada atualização do cliente.

Duas fontes independentes foram cruzadas:

| Fonte | Origem | Onde está |
|---|---|---|
| `loginto` | SSCBot / `pointers.lua` | `src/services/game/memory_reader.py` |
| `ramora` | RamoraBOT (bot descontinuado, código obtido do autor) | não versionado |

Ferramenta que lê os dois lado a lado contra o cliente rodando:

```
python tools/comparar_ponteiros.py               # detecta o cliente pelo executável
python tools/comparar_ponteiros.py --pid N       # PID explícito
python tools/comparar_ponteiros.py --autoteste   # valida o catálogo, sem jogo
```

O catálogo vive dentro dessa ferramenta (`BASES`, `ESTATICOS`, `CAMPOS`).
Este documento explica o que ele significa; a ferramenta é a fonte
executável. Ao atualizar um endereço, atualize os dois.

---

## Verificado no cliente `ver.6400` (2026-08-04)

Rodado com o char `DudePY` em *Piedmont of Green Scarp*, alvo
selecionado, em pé, sem time, sem bag aberta.

**Placar: `loginto` 26/33 campos sensatos. `ramora` 0/38.**

As bases do RamoraBOT são de um build anterior e estão todas mortas
neste cliente. O valor dele é o **catálogo de offsets dentro das
structs** — vários funcionam quando aplicados à base viva do `loginto`.

### Vivo e conferido

| Campo | Valor lido | Nota |
|---|---|---|
| `char_name` | `DudePY` | |
| `level` | 3 | |
| `hp` / `max_hp_base` | 181 / 181 | `hp_plus` = 100 |
| `mana` / `max_mana_base` | 111 / 111 | |
| `stamina` | 100 | |
| `gold` (CHAR+`0x410`) | 48 | **colhido do `ramora`** |
| `x_raw` / `y_raw` | 7850 / 17790 | ÷20 = (392, 889) |
| `location` | `Piedmont of Green Scarp` | via deref |
| `sit` (CHAR+`0x290`) | 100 em pé, 200 sentado | **colhido do `ramora`**, sentinela confirmada |
| `sin_passive` (CHAR+`0x3E4`) | 0 | **colhido do `ramora`** |
| `bag_1` / `bag_2` | 7 / 0 | **colhido do `ramora`** |
| `target_hp` | 597 | |
| `target_name` | `Little Wild Boar` | via deref |
| `bag_open` | 902 fechada | sentinela 903 = aberta, coerente |
| `dialogo` | 16774 fechado | sentinela 16775 = aberto, coerente |
| `team_size` | 0 | |

**`target_hp` = 597 com o alvo `Little Wild Boar`**: prova de que o
divisor 597 herdado do SSCBot era o HP daquele mob, não um máximo
genérico. Corrigido em `memory_reader.py`.

### Morto neste build

| Item | Endereço | Sintoma |
|---|---|---|
| `sit` hardcoded | `0x305F08B8` | lê 0 — era heap, nunca foi base |
| XP | `0x01139700` | lê 0, cadeia nunca resolve |
| `notification` | `0x0117097C` | lê `86581704` (um ponteiro), nunca `1` |
| `class_id` | CHAR+`0x3C8` | lê 760 — offset mudou |
| CAMERA | `0x0116FFF4` | lê 0 |
| todas as bases `ramora` | — | 0, lixo, ou cadeia quebra |

### Recuperado pelo rebase de 0x60

ENTIDADES e SUR estavam mortas só porque eram os endereços do build do
RamoraBOT. Somando os mesmos `0x60` das outras bases, voltam a resolver:

| Base | Endereço novo | Prova |
|---|---|---|
| ENTIDADES | `0x012C0628` | `target_select` alterna 1 ↔ 0 ao selecionar e dar Esc |
| SUR | `0x012CE33C` | cadeia resolve para um `EvUiForm` |

Lição barata: antes de varrer memória, sempre testar o rebase conhecido
no entorno da base morta. Duas das três voltaram sem scan nenhum.

**SUR tem uma ressalva.** A cadeia resolve, mas o `+0x64` do RamoraBOT
caía no meio do texto e devolvia um fragmento (`"t "`). No `ver.6400` o
texto está no próprio objeto, cadeia `[0x18, 0x8C, 0x3C]` — e o que ele
traz é o *form* da própria posição:

```
EvUiForm (13722200)...Scarp [392,889]...
```

Ou seja, mapa e coordenada **do personagem**, não a lista de NPCs do
painel Surrounding. Essa lista existe: um scan pelo literal `text="`
achou 118 entradas renderizadas em heap, como

```
text="Courage Merchant [231,-517] (1269 m)" color="#ff00ff00" hlink="String:task:locate?px=231&py=-517..."
```

mas nenhum dword aponta para o meio delas, e ainda não há cadeia estável
até o início do buffer. Achar isso é o trabalho que falta para
automatizar a coleta de coordenada de NPC.

As strings da UI são **UTF-8**, não UTF-16 — um scan por `text="` em
UTF-16LE devolve zero ocorrências.

### CAMERA continua perdida

O rebase de `0x60` não funciona para `0x0116FFF4`, e varrer `±0x400` em
volta só devolve floats denormais (ruído). Como zoom, rotação e ângulo
são floats que o jogador controla, o caminho é scan por valor com
`tools/scan_memory.py`: dar scan de float, mexer a câmera, refinar,
repetir até sobrar um punhado de endereços.

`sit` hardcoded, XP e `notification` foram **removidos** do
`memory_reader.py`: nenhum consumidor no app e falhavam em silêncio.

As três bases mortas mais caras são CAMERA, ENTIDADES e SUR — é onde
estão o texto do *surrounding* (coordenadas de NPC), o booleano real de
alvo selecionado e a escrita de câmera. Reencontrá-las exige pointer
scan.

Cuidado ao ler a coluna "heap plausível": a base CHAR do `ramora` lê
`0x6E6F6E23`, que cai na faixa de heap mas é texto ASCII (`n o n #`),
não ponteiro. Plausível não é vivo — o veredito é a cadeia resolver.

---

## Achado central: divergência sistemática de 0x60

Quase toda base estática difere exatamente `0x60` entre as duas fontes:

| Base | `loginto` | `ramora` | Δ |
|---|---|---|---|
| CHAR | `0x0114514C` | `0x011450EC` | 0x60 |
| TARGET | `0x012CE340` | `0x012CE2E0` | 0x60 |
| TEAM | `0x0106D388` | `0x0106D328` | 0x60 |
| DIALOGO | `0x0117B2DC` | `0x0117B27C` | 0x60 |
| confirm_box | `0x012CE3BC` | `0x012CE35C` | 0x60 |
| loot_window | `0x0105B9B8` | `0x0105B958` | 0x60 |
| notification | `0x0117097C` | `0x0117097C` | **0** |

São builds diferentes do cliente. `notification` batendo nos dois indica
que um dos conjuntos foi rebaseado à mão e o rebase não foi aplicado a
tudo — ou seja, dentro de um mesmo conjunto pode haver endereço de
geração errada. Não confie em nenhum dos dois sem rodar o comparador.

O autoteste do comparador trava essa relação de 0x60: se alguém mexer em
uma base e esquecer o par dela, o teste acusa.

O offset base do módulo é `0x00400000` (executável 32 bits). Endereços
escritos como `CLIENT + 0x00D450EC` e `0x011450EC` são o mesmo endereço —
as duas notações aparecem misturadas no código original.

---

## CHAR — struct do personagem local

A base contém um ponteiro; todos os campos abaixo são `read(base) + offset`.

| Offset | Campo | Tipo | Observação |
|---|---|---|---|
| `0xBC` | nome | str | string no lugar; às vezes precisa de um deref |
| `0xDC` | HP máximo (base) | int | somar buff e aplicar `plus` |
| `0xE0` | HP de buff | int | |
| `0xE4` | HP `plus` (%) | byte | se ≥ 100, subtrair 100 |
| `0x290` | sentado | byte | `200` = sentado |
| `0x3B8` | HP atual | int | |
| `0x3BC` | mana atual | int | |
| `0x3C4` | level | word | `loginto` lê 2 bytes, `ramora` 1 |
| `0x3C8` | class ID | word | 2 Assassin, 3 Tamer, 4 Wizard, 5 Fairy, 10 Monk |
| `0x3DC` | stamina | int | só `loginto` |
| `0x3E0` | passiva Monk | int | `loginto` chama de `breakpoint` |
| `0x3E4` | passiva Assassin | int | só `ramora` |
| `0x410` | gold | int | só `ramora` |
| `0x6EC` | mana máxima (base) | int | |
| `0x6F0` | mana de buff | int | |
| `0x810` | X | float | dividir por 20 para coordenada de jogo |
| `0x814` | Y | float | idem |
| `0x854` | em combate | byte | `1` = em combate |
| `0x8B0` | montaria | int | ≠ 0 = montado |
| `0x10A8` | pet vivo | int | só `loginto` |
| `0x7F8 → 0xF4 → 0x44C` | nome do mapa | str | |
| `0x838 → 0xC4 → 0x0 → 0x8 → 0x10` | quantidade slot 1 | int | só `ramora` |
| `0x838 → 0xC4 → 0x4 → 0x8 → 0x10` | quantidade slot 2 | int | só `ramora` |

## TARGET / UI — gerenciador de janelas

| Cadeia | Campo | Observação |
|---|---|---|
| `0x18, 0x59C, 0x0, 0xC, 0x1F4, 0x15C, 0x480` | HP do alvo | idêntica nas duas fontes |
| `0x18, 0xB1C, 0x0, 0xC, 0xD9C, 0x9AC` | nome do alvo (`loginto`) | |
| `0x18, 0xB1C, 0x0, 0xC, 0x1F8, 0x43C` `+0x9AC` | nome do alvo (`ramora`) | cauda diferente |
| `0x18, 0x5C4, 0x0, 0xC, 0x1F8, 0x42C, 0xBA0` | bag aberta | `903` = aberta |
| `0x18, 0x77C, 0x0, 0xC, 0x678, 0x8B4` `+0x4F4` | nome do time 1 | só `ramora` |
| `0x18, 0x34C, 0x0, 0xC, 0x678, 0x8B4` `+0x4F4` | nome do time 2 | só `ramora` |
| `0x18, 0x3F4, 0x0, 0xC, 0x1F4, 0x15C` `+0x54` | nome do time 3 | só `ramora` |
| `0x18, 0xA1C, 0x0, 0xC, 0x1F4, 0x54` `+0x54` | nome do time 4 | só `ramora` |

## Bases exclusivas do `ramora`

| Base | Cadeia | Campo |
|---|---|---|
| `0x012C05C8` (ENTIDADES) | `0xD0, 0x2DC, 0x24, 0xC10` | alvo selecionado (byte 0/1) |
| `0x012C05C8` | `0xD0, 0x7F4, 0x0, 0x24, 0x40` | loot no chão |
| `0x012CE2DC` (SUR) | `0x18, 0x8C, 0x3C` `+0x64` | texto do *surrounding* |
| `0x0116FFF4` (CAMERA) | `+0x64` / `+0x5C` / `+0x60` | zoom / rotação / ângulo (float) |

O texto do *surrounding* vem no formato `text="Nome [x,y]"` — é a fonte
das coordenadas de NPC que hoje pegamos à mão (ex.: Skull Herald). Regex
usada no original:

```python
re.search(r'text="([^"]+)\s*\[(-?\d+),(-?\d+)\]"', info)
```

## Endereços lidos direto (sem cadeia)

| Campo | `loginto` | `ramora` | Sentinela |
|---|---|---|---|
| notification | `0x0117097C` | `0x0117097C` | ≥ 1 |
| loot_window | `0x0105B9B8` | `0x0105B958` | `1` = aberta |
| confirm_box | `0x012CE3BC` | `0x012CE35C` | `1` = aberta |
| desconexão | — | `0x012CE35C` | — |
| target ID | — | `0x0115CB20` | — |
| menu de sistema | — | `0x012DC1F5` | `1610612736` (`0x60000000`) |

`ramora` usa **o mesmo endereço** `0x012CE35C` para `DC_POINTER` e
`CONFIRM_BOX_POINTER`. Provável copy-paste; um dos dois está errado.

## Cadeias de XP e diálogo

| Base | Cadeia | Campo |
|---|---|---|
| `0x01139700` (`loginto`) | `0xF0, 0x80, 0x28, 0x60, 0x5C, 0x228, 0x3EFC` | XP como texto `"12.3%"` |
| DIALOGO | `0x70, 0x56C, 0xC, 0x4, 0x42C, 0x1F8, 0x240` | `16775` = diálogo aberto |

---

## Armadilhas conhecidas

1. **Não cachear cadeia resolvida.** O `Pointers.__init__` do RamoraBOT
   percorre todas as cadeias uma vez e guarda o endereço final. Todo
   ponteiro que passa por heap (target, team, bag, diálogo, loot) vira
   lixo assim que o jogo realoca. O `_follow_chain` do `memory_reader.py`
   resolve por leitura — é o comportamento correto, manter.

2. **`is_sitting` do `memory_reader.py` está quebrado.** Lê
   `0x305F08B8` absoluto, que é endereço de heap, não base estática. O
   correto é `CHAR + 0x290`.

3. **`597` como "HP cheio do alvo" está errado nos dois códigos.** É o HP
   de um mob específico. `target_hp_pct` herdou isso e mente para
   qualquer outro alvo.

4. **`search_id()` do RamoraBOT é inviável.** Varre `0xCE00` a
   `0xEFFFFFF` de 4 em 4 bytes procurando o ID do alvo, uma chamada
   `ReadProcessMemory` por endereço: dezenas de milhões de syscalls por
   busca. O objetivo dele — obter X/Y **do alvo** — continua válido, mas
   precisa de outra abordagem (achar a lista de entidades).

5. **Escritas são outro nível de risco.** `write_position()` (teleporte
   por escrita de float em `+0x810`/`+0x814`) e `write_camera()` existem
   no RamoraBOT. A câmera é local e inofensiva; a posição é validada no
   servidor.

6. **`"Offline Account"` como sentinela de erro.** O RamoraBOT devolve
   essa string quando a leitura falha, misturando erro com dado. Ao
   portar qualquer leitor de string, devolva `None` ou `""`.

7. **`x > 0 and math.floor(x) or math.ceil(x)`** — idioma `and/or` que
   quebra quando `floor(x) == 0`: para `0 < x < 1` devolve `ceil(x) == 1`.

8. **HP e nome do alvo sobrevivem ao Esc.** Ao tirar o alvo, as cadeias
   de `target_hp` e `target_name` continuam devolvendo o valor do alvo
   anterior por tempo indefinido — conferido: `597` / `Little Wild Boar`
   com nada selecionado. Só o booleano em ENTIDADES
   (`[0xD0, 0x2DC, 0x24, 0xC10]`) alterna de verdade. Toda leitura de
   alvo tem de passar por ele; era por isso que o `target_selected`
   inferido de `hp > 0 and name` mentia.

---

## Quando o cliente atualizar

1. `python tools/comparar_ponteiros.py` — vê qual conjunto ainda vive.
2. A seção "Bases estáticas" da saída separa os dois cenários:
   - base lê `0` ou lixo → **a base morreu**, precisa ser reencontrada;
   - base lê ponteiro de heap plausível → **base viva, offset mudou**.
3. Para reencontrar: `python tools/scan_memory.py` (scan de valor,
   refino, e *pointer scan* para achar o estático que aponta para a
   struct).
4. Atualize `BASES`/`CAMPOS` em `tools/comparar_ponteiros.py` **e** este
   documento, e rode `--autoteste`.
