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
| `class_id` | CHAR+`0x3C8` | lê 722 no Monk, 0 no Wizard — offset mudou, ver abaixo |
| todas as bases `ramora` | — | 0, lixo, ou cadeia quebra |

### Recuperado pelo rebase de 0x60

ENTIDADES e SUR estavam mortas só porque eram os endereços do build do
RamoraBOT. Somando os mesmos `0x60` das outras bases, voltam a resolver:

| Base | Endereço novo | Prova |
|---|---|---|
| ENTIDADES | `0x012C0628` | `target_select` alterna 1 ↔ 0 ao selecionar e dar Esc |
| SUR | `0x012CE33C` | cadeia resolve para um `EvUiForm` |
| CAMERA | `0x01170054` | rot 241.4°, ângulo 60.0°, zoom 164.0 |

**As três bases dadas como mortas eram apenas os endereços do build
anterior.** Nenhuma exigia scan: bastava somar `0x60`.

A CAMERA custou caro por um erro de método. A primeira sonda varreu o
entorno da base e exigiu float não-nulo; o zoom lia `0` naquele
instante, então ela foi descartada como perdida e só voltou depois de um
scan de valor completo — que no fim apontou para `0x01170054`, isto é,
exatamente `0x0116FFF4 + 0x60`. Lição: ao sondar uma base, o critério é
**a cadeia resolver**, nunca o valor parecer bonito.

**SUR tem uma ressalva.** A cadeia resolve, mas o `+0x64` do RamoraBOT
caía no meio do texto e devolvia um fragmento (`"t "`). No `ver.6400` o
texto está no próprio objeto, cadeia `[0x18, 0x8C, 0x3C]` — e o que ele
traz é o *form* da própria posição:

```
EvUiForm (13722200)...Scarp [392,889]...
```

Ou seja, mapa e coordenada **do personagem**.

As strings da UI são **UTF-8**, não UTF-16 — um scan por `text="` em
UTF-16LE devolve zero ocorrências.

**A lista de NPCs do painel Surrounding foi encontrada depois** — ver a
seção "SURROUNDING" mais abaixo. O que achamos primeiro por pointer scan
e chegamos a rotular como Surrounding é outra coisa (o rastreador de
missões, na seção seguinte), e a confusão custou tempo.

### MISSOES — os NPCs-objetivo das missões ativas

Base `0x0150C314`, cadeia `[0xA0, 0xA0]`. Entrega o XML de um
`UiRichText` onde cada linha sai como:

```
text="Courage Merchant [231,-517] (1269 m)" color="#ff00ff00" hlink="String:task:locate?px=231&py=-517..."
```

Exposto em `MemoryReader.objetivos_de_missao()`, que devolve
`(nome, x, y, distância)` já deduplicado — o buffer repete a mesma
entrada a cada passada de renderização.

**Isto não é o painel Surrounding**, apesar de ter sido batizado assim
quando apareceu. É o rastreador de missões. O que denuncia:

- o buffer vem **agrupado por mapa** (`Stone City`, `Green Scarp`,
  `Sky Village`) e, dentro de cada um, por **nome de quest**
  (`Drive Away the Apes`, `Strength of White Eagle (0/1)`);
- cada linha carrega um `hlink="String:task:locate?..."`;
- só lista NPC ligado a uma **missão ativa** do personagem.

Duas consequências que importam na prática:

1. **NPC qualquer nunca vai estar aqui.** Buscar `skull` devolve vazio
   mesmo com o personagem no mapa certo, porque a Skull Herald não é
   objetivo de missão. Para NPC arbitrário a fonte é o painel
   Surrounding de verdade — seção abaixo.
2. **A distância é do último render.** Medido: o personagem andou de
   `(392, 889)` para `(392, 1004)` e os metros não mudaram nem um
   dígito. A coordenada do NPC não sofre com isso, que é fixa; a
   distância e a composição da lista sim.

Como usar:

```
python tools/pegar_coordenada_npc.py eagle --pid <cliente>
```

Com várias contas abertas o `--pid` é obrigatório na prática — sem ele
vale o primeiro `client.exe`, que pode ser um que nem terminou de logar.

Lição de método: a cadeia resolver e o conteúdo parecer certo não provam
que o campo é o que você acha que é. O teste que desmascarou foi mudar o
estado do jogo (andar) e reler — se nada muda, ou a leitura é cache, ou
o campo não é o que se supunha. Aqui era as duas coisas.

Outros três estáticos convergem para o mesmo buffer e servem de reserva
caso este morra numa atualização:

| Estático | Offsets |
|---|---|
| `0x0150C314` | `[0xA0, 0xA0]` |
| `0x00F3FED4` | `[0xD8, 0xA0]` |
| `0x015109F4` | `[0x88, 0xA0]` |
| `0x01510A24` | `[0x4C, 0xA0]` |

Verificado: fechar e reabrir o painel não muda o endereço do buffer nem
o conteúdo — as quatro cadeias seguem convergindo em `0x30db9520` com as
mesmas 10 entradas.

Como foi achada: scan pelo literal `text="` filtrado por `[x,y]` com
dígitos reais (o template `[%d,%d]` também casa e engana), depois busca
reversa em níveis — em cada nível, procurar na memória um dword valendo
`alvo - offset`. Nível 1 deu 22 donos, nenhum estático; nível 2 deu 293
donos, quatro deles na faixa do módulo.

### SURROUNDING — todos os NPCs do mapa

O painel Surrounding lista **todos** os NPCs do mapa atual, sejam de
missão ou não. Cada linha sai assim:

```
<Item type="TEXT" hlink="String:task:locate?px=1395&py=-636&hint=Skull Herald&mapid=1" text="Skull Herald [1395,-636]"></Item>
```

Mesma marcação do rastreador de missões, **sem a distância em metros**.
Exposto em `MemoryReader.npcs_ao_redor()` → `(nome, x, y)` deduplicado.

**Não há cadeia de ponteiros para ele — a fonte é varredura.** O bloco
é achado pelo marcador `String:task:locate?px=`, ficando com o maior
bloco encontrado (o render mais recente; os antigos sobrevivem na heap
com listas menores). Custa ~0,6 s por leitura, o que serve para anotar
coordenada e **não** para laço de bot.

Por que varredura e não cadeia — isto é o registro de uma tentativa que
falhou: a busca reversa em dois níveis deu três estáticos
(`0x004AB3B8` `[0x3A0]+0x200`, `0x0090F17C` `[0x4C]`, `0x00F04948`
`[0xD4]+0xFC`) e os três resolviam certo, com 33, 24 e 24 entradas.
**Todos morreram ao fechar e reabrir o painel** — o painel realoca, e
as cadeias passaram a apontar para lixo binário. Eram donos ocasionais
daquela alocação, não o caminho do objeto de UI. O marcador não tem
esse problema: acha o bloco onde ele estiver.

**`location` é a SUB-ÁREA, não o mapa.** `White Bear Village` e
`Ghost Din Woods` são lugares diferentes dentro de um mesmo mapa,
`Vast Mountain` — e o painel lista os NPCs do **mapa inteiro**, igual
nos dois. Consequências que ainda **não** estão corrigidas no código:

- o `npcs.json` é gravado com `mr.location` como chave, ou seja, com
  nome de sub-área. Capturar da outra sub-área grava uma segunda
  entrada com conteúdo idêntico, e a busca falha quando o personagem
  está numa sub-área diferente da que foi capturada;
- `bc_steps.garantir_cidade` compara `location` com `"Stone City"`.
  Se essa cidade tiver sub-áreas, estar no mapa certo em outro canto
  lê "não estou na cidade" e gasta um Return Charm à toa.

Isso também explica a Skull Herald aparecer em `(1395,-636)` na
captura feita de White Bear Village enquanto um personagem parado em
Ghost Din Woods lê `(1395,-635)`: é **o mesmo NPC**, não duas cópias.

**Não há identificador de mapa fácil, e o `mapid` do hlink não é um.**
Medido: `mapid=1` tanto nas linhas de Stone City quanto nas de Vast
Mountain — é tipo de link, não mapa. O objeto de onde sai o `location`
(`CHAR + [0x7F8, 0xF4] + 0x44C`) também só tem o nome da sub-área;
logo depois dele sobra lixo do mapa anterior (`'ods'`, resto de
`Ghost Din Woods`), ou seja, buffer reaproveitado e não campo
separado.

Por isso o catálogo continua indexado por **sub-área**, e a comparação
de "estou na cidade?" virou **lista de sub-áreas** (`areas_da_cidade`
no config do BC). Capturar de duas sub-áreas do mesmo mapa grava duas
entradas idênticas — alguns KB — e isso custa menos que uma caçada de
ponteiro para um problema que não atrapalha.

**Armadilha medida:** fechar o painel NÃO limpa o bloco — com ele
fechado, as mesmas 33 entradas continuam sendo achadas. A regra real é
"o painel precisa ter sido aberto **pelo menos uma vez neste mapa**".
Quem troca de mapa sem reabrir o painel recebe a lista do mapa
anterior, com cara de válida.

Conferido com o `DudePY` em *White Bear Village*: a Skull Herald da
entrada da BC sai como `(1395, -636)` — exatamente o `npc_entrada_pos`
que estava anotado à mão no `bc.py`. A anotação estava certa, e agora
tem fonte em memória confirmando.

Detalhe do scan que economiza tempo: filtrar por blocos com 20+
entradas no formato `text="Nome [x,y]"` separa a lista dos objetos de
definição de NPC (`table_npc_4334`), que também contêm o nome mas
nenhuma coordenada.

Lição de método que se repetiu: **buscar o endereço exato do buffer não
acha dono nenhum** — o ponteiro guardado aponta para o objeto que
contém a string, não para a string. A busca reversa só funciona
procurando dwords na faixa `alvo - offset`.

### Classe (profession) — CHAR+`0xD4`

O `0x3C8` herdado das duas fontes morreu: lê 722 no Monk e 0 no Wizard.
A tabela de IDs também mudou — em toda a struct (`0x0`–`0x8000`) não
existe offset que valha 10 no Monk e 4 no Wizard ao mesmo tempo.

O campo vivo é **`CHAR+0xD4`, um byte**, e o vizinho `CHAR+0xD5` é o
gênero (`1` = feminino). Lidos juntos como dword, uma personagem feminina
dá `256`, que é só o byte de gênero na parte alta.

| Personagem | Classe | `+0xD4` | `+0xD5` |
|---|---|---|---|
| DudePY | Monk | 1 | 0 |
| TestpY | Wizard female | 0 | 1 |
| FrostGuy | Wizard male | 0 | 0 |
| Nord | Assassin | 2 | 0 |
| HealASF | Fairy | 3 | 1 |
| BeastHit | Tamer | 4 | 1 |

**A classe não muda com o gênero**: Wizard male e female leem `0` nos
dois. Tabela completa: `0` Wizard, `1` Monk, `2` Assassin, `3` Fairy,
`4` Tamer — as cinco conferidas com um personagem de cada.

Como foi achado, e o que economizou tempo: quatro clientes abertos ao
mesmo tempo, um dump da struct por personagem, e um filtro de três
condições — mesmo valor nos dois Wizard, valor diferente no Monk e no
Assassin, e estável ao reler quatro segundos depois. Sobrou o bloco de
atributos base (`0xEC`, `0xF4`, `0x118`, que variam com o level e não
servem) e o `0xD4`.

Dois personagens não bastavam: com só Monk e Wizard, 64 offsets passavam
no filtro. O que corta de verdade é o **par da mesma classe com gênero
diferente** — ele elimina tudo que é aparência — somado a um terceiro de
classe distinta. O `0xD4` ainda se confirma por repetir em `+0x474`, o
mesmo delta `0x3A0` do bloco de atributos, ou seja, faz parte do
registro do personagem.

### CAMERA: unidades e layout

Base `0x01170054`, todos `float` no objeto apontado:

| Offset | Campo | Valor medido |
|---|---|---|
| `0x5C` | rotação | 241.40 (graus, 0–360) |
| `0x60` | ângulo | 60.00 (graus) |
| `0x64` | zoom | 164.00 |
| `0x68` | zoom espelhado | 164.00 — provável alvo da interpolação |

### Receita do scan de valor desconhecido

Serviu para a CAMERA e serve para qualquer campo controlado pelo
jogador. Um snapshot de todos os floats plausíveis, depois refinamento:

| Ação no jogo | Filtro | Sobreviventes |
|---|---|---|
| — | foto inicial | 49.153.297 |
| rolar o zoom | mudou | 271.106 |
| nada | igual (×2) | 170.483 |
| rolar o zoom | mudou | 7.901 |
| nada | igual | 7.512 |
| girar a câmera | igual | 2.793 |
| rolar o zoom | mudou | 906 |

O que fechou não foi mais refinamento por valor, e sim o **filtro
estrutural**: para cada sobrevivente `S` e cada offset plausível,
procurar na faixa estática (`< 0x02000000`) um dword valendo `S - off`.
Só um resultado tinha a cara certa, e era o offset `0x64` que o
RamoraBOT já documentava.

Ordem que economiza tempo: aplicar o evento discriminante **primeiro**.
Começar filtrando ruído com o jogo parado é lento e corta pouco — a
primeira passada ociosa levou minutos para derrubar 1% dos candidatos,
enquanto uma rolada de zoom cortou 99,4%.

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
| `0xD4` | classe (profession) | byte | `0` Wizard, `1` Monk, `2` Assassin, `3` Fairy, `4` Tamer |
| `0xD5` | gênero | byte | `1` = feminino |
| `0x290` | sentado | byte | `200` = sentado |
| `0x3B8` | HP atual | int | |
| `0x3BC` | mana atual | int | |
| `0x3C4` | level | word | `loginto` lê 2 bytes, `ramora` 1 |
| `0x3C8` | class ID (build antigo) | word | 2 Assassin, 3 Tamer, 4 Wizard, 5 Fairy, 10 Monk — **morto no `ver.6400`** |
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

## ALVO — `0x0107D410`, a entidade selecionada

Estático que aponta **direto para a entidade do alvo**. Entidade e
personagem são a **mesma struct**: nome em `+0xBC`, HP em `+0x3B8`,
level em `+0x3C4`, x/y em `+0x810`/`+0x814` — os offsets do CHAR.

```
0x0107D410 -> entidade -> +0xBC 'Transport Fay'  +0x3B8 100  +0x3C4 8  (178,-518)
```

Isto substitui as cadeias de UI do `TARGET_BASE`. Elas **não são
portáveis entre clientes**: medido no mesmo build, com dois clients
abertos, a cadeia `[0x18, 0xB1C, 0x0, 0xC, 0xD9C, 0x9AC]` resolve
inteira num e morre no salto `+0xD9C` no outro —

```
DudePY   0x04C5A308 -> 0x1471E018 -> 0x100D01F8 -> 0x13604438 -> 0x136339A8 -> 0x13634BB0
Tomyris  0x04BB5568 -> 0x39BD0A28 -> 0x1035E940 -> 0x3ADB8810 -> 0x343D72E8 -> 0x00000000
```

O que difere entre os dois é o **arranjo da UI** (painéis de bag
abertos, barra de skills), não a versão do jogo. Cadeia que passa pelo
gerenciador de janelas herda o layout da UI; esta não passa.

**O booleano de alvo do `ramora` não serve.** `ENTIDADES +
[0xD0, 0x2DC, 0x24, 0xC10]` lê `1` em cliente sem alvo nenhum. O objeto
no fim dessa cadeia é o marcador de seleção do chão — as strings dentro
dele são `eff_cursorground02` e `cursorground_r`. Ele nunca soube quem
era o alvo.

**Limite conhecido:** o ponteiro guarda o **último** alvo. Medido: com
Esc, continua apontando para a mesma entidade. Ponteiro zero prova
"nunca teve alvo"; ponteiro cheio não prova "tem alvo agora". Falta
achar o campo de seleção atual.

Como foi achada: procurar o nome do alvo (`Transport Fay`) na memória
exigindo que `+0x810 / 20` batesse com a coordenada que o jogo mostrava
— isso isola a entidade entre as várias cópias do nome. Depois, busca
reversa pelo endereço dela: 15 donos, **um** deles estático.

Isso também resolve o `search_id()` do RamoraBOT, que varria
`0xCE00`–`0xEFFFFFF` de 4 em 4 bytes para obter X/Y do alvo: a
coordenada está no próprio objeto, a uma leitura de distância.

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
   servidor. Daí só a câmera ter sido portada:
   `MemoryReader.escrever_camera()` escreve os três floats da base
   `0x01170054` e é a única escrita do app. Serve aos cliques de tela —
   o botão de view reset do jogo devolve o ângulo mas não o zoom, e os
   clients usados aqui têm o limite de zoom liberado.

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
