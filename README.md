# Bot de Login - Talisman Online

Automatiza abrir o client, logar, selecionar servidor e entrar no jogo,
**sem mover o mouse físico nem usar o teclado real** — os cliques e a
digitação são enviados diretamente para a janela do jogo via mensagens
do Windows (`PostMessage`).

## 1. Instalação

Windows, Python 3.10+:

```bash
pip install -r requirements.txt
```

## 2. Configuração inicial

1. Abra `config.py` e ajuste:
   - `CLIENT_PATH`: caminho completo do `.exe` do Talisman Online.
   - `SERVER_NAME`: nome/identificador do servidor que você quer selecionar.

2. Descubra o título exato da janela do jogo (com ele aberto):
   ```bash
   python tools/find_window_title.py
   ```
   Copie o título encontrado para `WINDOW_TITLE` em `config.py`.

3. Defina usuário e senha como variáveis de ambiente (não deixe no código):
   ```bash
   set TALISMAN_USER=seu_usuario
   set TALISMAN_PASS=sua_senha
   ```

## 3. Teste se o jogo aceita cliques simulados

Antes de configurar tudo, confirme que o Talisman Online reage a cliques
enviados via `PostMessage` (alguns jogos com captura de input exclusiva
ignoram isso):

```bash
python tools/test_click.py 400 300
```

Se o jogo reagir visivelmente (campo destacado, cursor piscando, etc.),
seguimos com essa abordagem. Se não reagir a nada, me avise — nesse caso
precisamos de um fallback com cursor real (`pyautogui`), que aí sim move
o mouse fisicamente durante a automação.

## 4. Capturar os templates (imagens de referência)

O bot reconhece a tela por comparação de imagem. Você precisa gerar
recortes PNG dos elementos:

1. Abra o jogo manualmente até a tela de login.
2. Rode:
   ```bash
   python tools/capture_screenshot.py login.png
   ```
3. Abra `login.png` em um editor de imagem (Paint, GIMP, etc.) e recorte:
   - o campo de usuário → salve como `templates/campo_usuario.png`
   - o campo de senha → `templates/campo_senha.png`
   - o botão de entrar → `templates/botao_entrar.png`
4. Repita o processo na tela de seleção de servidor, salvando:
   - o botão do servidor desejado → `templates/servidor_<SERVER_NAME>.png`
     (o nome deve bater com `config.SERVER_NAME`)
   - se houver botão de confirmação extra → `templates/botao_confirmar_servidor.png`
5. E na tela já dentro do jogo, capture algum elemento fixo (ex: um ícone
   de HUD) → `templates/tela_jogo_carregada.png`

Dica: recortes pequenos e com bastante contraste/detalhe (ícones, texto
com fundo distinto) funcionam melhor que áreas lisas ou muito grandes.

## 5. Rodar o bot

```bash
python main.py
```

## Estrutura do projeto

```
talisman_bot/
├── config.py           # configurações (caminhos, credenciais, thresholds)
├── window_utils.py      # localizar janela e capturar tela sem usar o mouse
├── vision.py             # reconhecimento de imagem (OpenCV)
├── input_utils.py       # clique e digitação via PostMessage
├── main.py                # fluxo principal (login -> servidor -> jogo)
├── templates/            # imagens de referência (você gera essas)
└── tools/
    ├── find_window_title.py
    ├── capture_screenshot.py
    └── test_click.py
```

## Observações importantes

- **Resolução fixa 1024x768**: os templates foram pensados para essa
  resolução. Se o client abrir em outra resolução, force isso na
  configuração de vídeo do jogo antes de rodar o bot.
- **PostMessage x cursor real**: essa abordagem não interfere no seu
  uso do PC porque não move nada fisicamente. A limitação é que só
  funciona se o jogo processar mensagens do Windows normalmente (comum
  em jogos GDI/DirectX clássicos, que costuma ser o caso de clients
  mais antigos como esse).
- **Ajuste de thresholds**: se o reconhecimento falhar com frequência,
  diminua `MATCH_THRESHOLD` em `config.py` (ex: de 0.85 para 0.75) ou
  refaça os recortes dos templates com mais precisão.
