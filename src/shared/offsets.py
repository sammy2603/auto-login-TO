"""
Alguns templates são recortados sobre um rótulo ou borda ao lado do
campo real (isso é proposital: rótulos/bordas não mudam de aparência
como o conteúdo interno da caixa de texto, o que deixa o
reconhecimento mais estável).

Quando isso acontece, o ponto encontrado pelo template matching não é
o ponto certo pra clicar -- precisa de um deslocamento (offset) fixo
em pixels pra chegar até o centro real da caixa de texto.

Formato: (dx, dy) -- deslocamento a partir do centro do template
encontrado. Positivo = direita/baixo. Negativo = esquerda/cima.

Ajuste esses valores comparando, na imagem gerada por
tools/debug_templates.py, a posição do retângulo (o template
encontrado) com a posição real da caixa de texto clicável.
"""


class FieldOffsets:

    # Ajuste conforme a distância real entre o rótulo/borda recortado
    # e o centro da caixa de texto na tela de login.
    USERNAME = (60, 0)

    PASSWORD = (60, 0)