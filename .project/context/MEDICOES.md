# Medições feitas no jogo

Números que **não se deduzem** — só se medem no cliente rodando. Cada um
traz o método e o que o invalida, porque medida sem procedimento vira
chute na próxima vez que alguém precisar refazê-la.

Regra que originou este arquivo: na sessão de 2026-08-06, o mesmo sintoma
("o clique erra o NPC") recebeu quatro explicações plausíveis e nenhuma
resolveu. O que resolveu foram três medições. **Quando o sintoma for
visual, capture a tela antes de teorizar** — custa um comando.

---

## Minimapa

Todos com o minimapa em **zoom in total**. O zoom muda a escala, e a
escala é o que converte "quero ir a (x,y)" em pixel de clique.

| Grandeza | Valor | Método |
|---|---|---|
| Centro | `(914, 114)` | `HoughCircles` sobre a captura da janela |
| Raio | `72 px` | idem |
| Escala | `0,37 unidades/px` | 5 cliques gravados, ajuste pelo eixo Y |
| Zona morta | `~5 px` ≈ 2,5 unidades | clique mais perto do centro não move o personagem |
| Botão zoom in | `(997, 98)` | recorte da captura |
| Botão zoom out | `(997, 127)` | idem |

**A escala saiu só do eixo Y de propósito.** As amostras de X deram 0,29 a
0,80 — não é dispersão de medição: o trecho era um corredor norte-sul e a
parede travava o deslocamento lateral. As amostras de X mediram parede.
Medir escala exige **campo aberto**, ou um eixo confiável de cada vez.

**O que estava errado antes:** escala em `1.0` e raio em `55`, ambos
chutados. Com escala pela metade, o `walk_to` pedia menos da metade do
deslocamento; o laço compensava reclicando até o resto cair abaixo da
zona morta, e aí travava a ~4 unidades do alvo. Era a causa raiz de todo
o resto.

**Invalida a escala:** mudar o zoom do minimapa; mudar a resolução.
**Pendente:** a escala em zoom out total, que é como o RaaskiBot anda
dentro da cave.

---

## Câmera

Base `0x01170054`, floats no objeto apontado:

| Offset | Campo |
|---|---|
| `+0x5C` | rotação |
| `+0x60` | ângulo |
| `+0x64` | zoom atual |
| `+0x68` | zoom alvo (destino da interpolação) |

**Escrever só o `+0x64` não muda a tela.** O cliente interpola o atual em
direção ao alvo, então o valor era desfeito na primeira atualização de
câmera. Escrever os dois funciona — confirmado no jogo.

Valores usados pelo roteiro: `zoom 380, rotação 0, ângulo 40`. A câmera
padrão do login mede `(380, 0.6, 38.2)`, ou seja, praticamente a mesma.

**Método para achar a estrutura viva:** `tools/camera_probe.py`. O
critério é *qual endereço varia quando o jogador mexe na câmera* — câmera
viva acompanha a mão, cópia não. O critério errado ("onde há um float
plausível") foi o que levou ao endereço errado da primeira vez.

**Por que importa:** clique em NPC é coordenada de TELA. A câmera sai do
lugar durante a run — medido: começou padrão, chegou torta na cave.

---

## Velocidade e deslocamento

| Situação | Valor |
|---|---|
| Caminhada montado, Stone City | 20–28 unidades/s |
| Caminhada montado, Ghost Din Woods | ~14,6 unidades/s |
| Item de teleporte | instantâneo, destino fixo |

Serve para distinguir **caminhada** de **escrita de memória** ao observar
outro bot: deslocamento acima de ~60 u/s não é caminhada. Cuidado com o
falso positivo — teleporte do próprio jogo também é instantâneo, e o
destino fixo é a assinatura dele (ex.: o charm de Stone City sempre
entrega em `(178,-516)`).

---

## Bewitcher Cave — do lado de fora

| O quê | Valor | Observação |
|---|---|---|
| Skull Herald (NPC) | `(1395, -636)` | coordenada DO NPC, vinda do painel Surrounding |
| Parada do personagem | `(1393, -635)` | onde o clique fixo entrega; variação residual ~3 unidades |
| Origem do clique fixo | `(1391, -625)` | waypoint com tolerância própria (3) |
| Clique fixo no minimapa | `(929, 145)` | relativo à origem acima |
| Corpo do NPC na tela | `x 560..630, y 372..467` | com a câmera em 380/0/40 |
| Nome flutuante | `~(597, 363)` | texto verde |

**Coordenada do NPC ≠ posição de parada.** São perguntas diferentes, e o
catálogo `npcs.json` só responde a primeira.

**O valor antigo do clique era `(479,410)`:** o y estava quase certo e o
**x errava por 115 px**. Era onde o pet costuma parar — daí os cliques
acertarem o pet e o diálogo nunca abrir.

**Por que clique fixo no minimapa, e não conta:** o minimapa é centrado no
personagem, então um pixel fixo é um deslocamento relativo fixo. Partindo
sempre do mesmo lugar, chega sempre no mesmo lugar — sem depender de
escala, centro nem tolerância, os três que erraram justamente ali. O
preço é a origem precisar ser repetível: cada unidade de erro nela vira
uma unidade de erro no destino.

---

## Bewitcher Cave — entrada

| O quê | Valor |
|---|---|
| `location` dentro da cave | `'Bewitcher Cave'` |
| Pixel `(945,148)` dentro | `0x2E3D1E` |
| Esperado pelo macro antigo | `0x00FF00` |

**A confirmação por pixel era inválida.** Com o personagem
comprovadamente dentro, ela dizia "não entrou", e o roteiro refazia a
tentativa inteira — caminhada, câmera, diálogo — de dentro da cave.
Trocada por `location`, que não depende de iluminação, de foco da janela
nem de o elemento estar desenhado no quadro.

**Instância cheia é normal:** o cenário tem limite de gente. O bot de
referência insistiu 62 s sem entrar, repetindo o diálogo num ciclo de
~1,1 s. Retry precisa ser dimensionado para isso.

---

## Bewitcher Cave — do lado de dentro

Gravado com o RaaskiBot fazendo a run e `tools/spy_bot.py` observando.

| O quê | Valor |
|---|---|
| Trajeto | entrada `(423,53)` → NPC do altar `(218,45)` |
| Extensão | 1383 unidades, 1162 posições distintas |
| Teleporte do altar | leva a `(187,-406)`, área do boss |
| Waypoints simplificados | 28 (Douglas-Peucker ε=3, espaçamento ≥12) |

O RaaskiBot anda **com o minimapa em zoom out total** aqui dentro,
enquanto por fora usamos zoom in total. Ver a pendência da escala.

---

## Sobre o bot de referência (RaaskiBot)

Observado de fora com `tools/spy_bot.py`, sem injetar nada:

- **Não injeta DLL** — nenhum módulo novo no processo, nenhum depurador.
- **Não escreve posição** — anda de verdade, 217 unidades em 14,9 s no
  trecho até a cave.
- **Não usa o painel Surrounding invisível** — o bloco de texto do painel
  nunca foi reescrito durante a observação.
- Usa cliques de movimento e os **itens de teleporte do jogo**.

A suspeita inicial de escrita de memória veio de um salto instantâneo de
98 unidades. Era o item de teleporte para Stone City, cujo destino fixo
`(178,-515)` está no código do próprio RamoraBOT. **Instantâneo não prova
escrita — confira se a chegada é um destino conhecido de teleporte.**

---

## O que invalida tudo isto

| Evento | O que refazer |
|---|---|
| Atualização do cliente | ponteiros (ver `PONTEIROS.md`), possivelmente offsets de câmera |
| Mudança de zoom do minimapa | escala, e só ela |
| Mudança de resolução | todas as coordenadas de tela e do minimapa |
| Mudança de câmera padrão | pontos de clique em NPC |
| Patch que mexa na UI | pontos de clique de janela, botões de zoom |
