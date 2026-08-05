# -*- coding: utf-8 -*-
"""
Testes do parser do painel Surrounding.

E a unica parte do MemoryReader que da para exercitar sem o jogo
aberto -- e e onde mora o risco: o texto vem de marcacao de UI que
muda entre versoes do cliente.

Amostras copiadas do cliente ver.6400.
"""

from src.services.game.memory_reader import MemoryReader


parse = MemoryReader.parse_objetivos


def item(nome, x, y, dist):
    return f'<Item type="TEXT" text="{nome} [{x},{y}] ({dist} m)" color="#ff00ff00" />'


def test_extrai_nome_coordenada_e_distancia():
    texto = item("Courage Merchant", 231, -517, 1269)

    assert parse(texto) == [("Courage Merchant", 231, -517, 1269)]


def test_coordenada_negativa_nos_dois_eixos():
    texto = item("Mount Admin", -239, -519, 1270)

    assert parse(texto) == [("Mount Admin", -239, -519, 1270)]


def test_deduplica_preservando_a_ordem():
    """
    O buffer traz a mesma entrada a cada passada de renderizacao --
    medido no jogo: 8 copias seguidas de 'Gem Trader'.
    """
    texto = "".join([
        item("Gem Trader", 245, -520, 1270),
        item("Gem Trader", 245, -520, 1270),
        item("Gem Dealer", 244, -523, 1274),
        item("Gem Trader", 245, -520, 1270),
    ])

    assert parse(texto) == [
        ("Gem Trader", 245, -520, 1270),
        ("Gem Dealer", 244, -523, 1274),
    ]


def test_nome_com_parenteses_nao_confunde_a_distancia():
    """'Buddha Slave (right-click me)' existe no jogo e tem parenteses."""
    texto = item("Buddha Slave (right-click me)", 380, 1125, 214)

    assert parse(texto) == [("Buddha Slave (right-click me)", 380, 1125, 214)]


def test_ignora_o_template_de_formato():
    """
    O cliente guarda o printf do proprio texto. Casar com ele daria
    NPC fantasma -- foi o que enganou a primeira busca por colchetes.
    """
    texto = '<Item text="%s%s [%d,%d] (%d m)" color="#%08x" />'

    assert parse(texto) == []


def test_ignora_item_sem_coordenada():
    """Cabecalhos do painel ('Stone City') nao sao NPC."""
    texto = ('<Item text="Stone City" color="#ffffffff" />'
             + item("White Eagle", 138, 492, 421))

    assert parse(texto) == [("White Eagle", 138, 492, 421)]


def test_descarta_entrada_cortada_no_fim_do_buffer():
    """A leitura tem teto de bytes; a ultima entrada pode vir partida."""
    texto = item("Little Monk", 131, 540, 388) + '<Item text="White Eag'

    assert parse(texto) == [("Little Monk", 131, 540, 388)]


def test_tira_espaco_em_volta_do_nome():
    texto = '<Item text="  Flower Faerie  [280,-537] (1283 m)" />'

    assert parse(texto) == [("Flower Faerie", 280, -537, 1283)]


def test_texto_vazio_ou_ausente():
    assert parse("") == []
    assert parse(None) == []


def test_xml_inteiro_como_vem_do_jogo():
    texto = (
        '\x08<?xml version="1.0" encoding="UTF-8"?><UiRichText><Line><Items>'
        '<Item text="Stone City" color="#ffffffff" /></Items></Line><Line>'
        '<Items><Item text="  " />'
        + item("Buddhist Novice Shan", 373, 1114, 205)
        + '</Items></Line><Line><Items><Item text="  " />'
        + item("Talisman Fairy (right-click me)", 385, 1122, 212)
        + '</Items></Line></UiRichText>'
    )

    assert parse(texto) == [
        ("Buddhist Novice Shan", 373, 1114, 205),
        ("Talisman Fairy (right-click me)", 385, 1122, 212),
    ]
