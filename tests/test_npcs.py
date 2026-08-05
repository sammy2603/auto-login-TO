# -*- coding: utf-8 -*-
"""
Testes do catalogo de NPCs por mapa.

Nenhum toca no npcs.json de verdade: tudo em tmp_path. Um teste que
escreve no catalogo versionado apagaria captura feita dentro do jogo.
"""

import json

from src.services.game.npcs import carregar, coordenada, coordenadas, salvar


def catalogo(tmp_path, dados):
    caminho = tmp_path / "npcs.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


def test_coordenada_por_pedaco_do_nome_sem_case(tmp_path):
    c = catalogo(tmp_path, {"White Bear Village": {"Skull Herald": [[1395, -636]]}})

    assert coordenada("White Bear Village", "skull", c) == (1395, -636)
    assert coordenada("White Bear Village", "HERALD", c) == (1395, -636)
    assert coordenada("White Bear Village", " skull ", c) == (1395, -636)


def test_coordenada_negativa_sobrevive_ao_json(tmp_path):
    c = catalogo(tmp_path, {"Green Scarp": {"Mount Admin": [[-239, -519]]}})

    assert coordenada("Green Scarp", "mount", c) == (-239, -519)


def test_mapa_ou_npc_ausente_devolve_none(tmp_path):
    c = catalogo(tmp_path, {"White Bear Village": {"Skull Herald": [[1395, -636]]}})

    assert coordenada("Green Scarp", "skull", c) is None
    assert coordenada("White Bear Village", "auctioneer", c) is None
    assert coordenada("White Bear Village", "", c) is None


def test_arquivo_ausente_ou_corrompido_nao_explode(tmp_path):
    assert carregar(tmp_path / "nao_existe.json") == {}

    ruim = tmp_path / "npcs.json"
    ruim.write_text("{isto nao e json", encoding="utf-8")
    assert carregar(ruim) == {}
    assert coordenada("qualquer", "skull", ruim) is None


def test_salvar_preserva_os_outros_mapas(tmp_path):
    c = catalogo(tmp_path, {"Green Scarp": {"Mount Admin": [[-239, -519]]}})

    salvar("White Bear Village", [("Skull Herald", 1395, -636)], c)

    assert coordenada("Green Scarp", "mount", c) == (-239, -519)
    assert coordenada("White Bear Village", "skull", c) == (1395, -636)


def test_salvar_substitui_o_mapa_inteiro(tmp_path):
    """NPC que sumiu do painel tem de sumir do catalogo."""
    c = catalogo(tmp_path, {"Stone City": {"Velho": [[1, 2]], "Some": [[3, 4]]}})

    salvar("Stone City", [("Velho", 1, 2)], c)

    assert carregar(c)["Stone City"] == {"Velho": [[1, 2]]}


def test_salvar_lista_vazia_nao_apaga_captura_boa(tmp_path):
    """Lista vazia quase sempre e painel que nunca foi aberto."""
    c = catalogo(tmp_path, {"Stone City": {"Velho": [[1, 2]]}})

    assert salvar("Stone City", [], c) == 0
    assert coordenada("Stone City", "velho", c) == (1, 2)


def test_npc_repetido_guarda_as_duas_coordenadas(tmp_path):
    """
    'Transport Fay' aparece duas vezes em White Bear Village. Guardar so
    uma perderia NPC em silencio -- foi o que a primeira versao fez.
    """
    c = tmp_path / "npcs.json"

    salvar("White Bear Village", [
        ("Transport Fay", 847, -607),
        ("Transport Fay", 1372, -417),
    ], c)

    assert coordenadas("White Bear Village", "transport", c) == [
        (847, -607), (1372, -417),
    ]
    assert coordenada("White Bear Village", "transport", c) == (847, -607)


def test_entrada_duplicada_nao_vira_coordenada_repetida(tmp_path):
    """O buffer repete a mesma linha a cada render."""
    c = tmp_path / "npcs.json"

    salvar("Stone City", [("Velho", 1, 2), ("Velho", 1, 2)], c)

    assert coordenadas("Stone City", "velho", c) == [(1, 2)]
