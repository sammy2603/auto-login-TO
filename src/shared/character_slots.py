"""
Posições (x, y) de cada slot de personagem na tela de seleção,
na resolução 1024x768 (client area).

O jogo permite até 3 personagens por conta/servidor, alinhados da
esquerda pra direita. Como os 3 slots ficam em posições fixas na tela
(mudando só o conteúdo, não a posição), usamos coordenadas diretas em
vez de reconhecimento de imagem aqui -- é mais simples e não depende
de cada personagem ter uma aparência reconhecível.

Ajuste esses valores usando tools/debug_slots.py pra calibrar
visualmente antes de usar.
"""


class CharacterSlot:
    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"


CHARACTER_SLOT_POSITIONS = {
    CharacterSlot.LEFT: (370, 650),
    CharacterSlot.CENTER: (512, 650),
    CharacterSlot.RIGHT: (610, 650),
}