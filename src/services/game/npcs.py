# -*- coding: utf-8 -*-
"""
Catalogo de NPCs por mapa, capturado do painel Surrounding.

Existe porque NPC de mapa nao anda: nome e coordenada sao fixos. Varrer
a memoria a cada run e refazer trabalho para obter sempre a mesma
resposta -- e a varredura custa ~0,6 s e exige que o painel tenha sido
aberto naquele mapa. Aqui a leitura de memoria vira CAPTURA (uma vez,
pela ferramenta) e o bot passa a ler arquivo.

Captura:
    python tools/pegar_coordenada_npc.py --salvar --pid <cliente>

O arquivo e versionado de proposito, igual aos templates: e ativo de
runtime, nao cache descartavel. Perde-lo significa voltar no jogo e
reabrir o painel em cada mapa.
"""

from __future__ import annotations

import json
from pathlib import Path

CATALOGO = Path(__file__).resolve().parents[3] / "npcs.json"


def carregar(caminho: Path = CATALOGO) -> dict[str, dict[str, list[list[int]]]]:
    """
    Catalogo inteiro: {mapa: {nome: [[x, y], ...]}}.

    O valor e LISTA de coordenadas porque o mesmo nome aparece mais de
    uma vez no mapa -- 'Transport Fay' fica em (847,-607) e em
    (1372,-417) em White Bear Village. Guardar so uma perderia NPC em
    silencio.

    Arquivo ausente ou corrompido devolve {}.
    """
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def coordenadas(mapa: str, nome: str,
                caminho: Path = CATALOGO) -> list[tuple[int, int]]:
    """
    Todas as coordenadas que casam, casando por PEDACO do nome e sem
    diferenciar maiuscula -- 'skull' acha 'Skull Herald'. Mesma regra do
    filtro da ferramenta, para nao existirem duas formas de escrever o
    mesmo nome.
    """
    alvo = (nome or "").strip().lower()
    if not alvo:
        return []
    saida = []
    for npc, pontos in carregar(caminho).get(mapa, {}).items():
        if alvo in npc.lower():
            saida.extend((x, y) for x, y in pontos)
    return saida


def coordenada(mapa: str, nome: str,
               caminho: Path = CATALOGO) -> tuple[int, int] | None:
    """
    A PRIMEIRA coordenada que casa, na ordem em que o painel listou.

    None quando o mapa nao foi capturado ou o NPC nao esta nele. Quem
    chama decide o que fazer; devolver (0, 0) mandaria o bot andar para
    o canto do mapa.

    Com NPC repetido (ha varios), "a primeira" e escolha arbitraria --
    use coordenadas() quando importar qual das copias.
    """
    achados = coordenadas(mapa, nome, caminho)
    return achados[0] if achados else None


def salvar(mapa: str, entradas: list[tuple[str, int, int]],
           caminho: Path = CATALOGO) -> int:
    """
    Grava as entradas de UM mapa, preservando os demais.

    O mapa capturado e substituido por inteiro, e nao mesclado: se um
    NPC sumiu do painel, ele tem de sumir do catalogo tambem -- mesclar
    guardaria NPC que nao existe mais e ninguem descobriria.

    Devolve quantos NOMES foram gravados (um nome pode ter varias
    coordenadas). Entrada vazia NAO apaga o que
    ja existe: lista vazia quase sempre e painel que nunca foi aberto
    naquele mapa, e apagar por causa disso seria perder captura boa.
    """
    if not entradas:
        return 0
    dados = carregar(caminho)
    mapeado: dict[str, list[list[int]]] = {}
    for nome, x, y in entradas:
        pontos = mapeado.setdefault(nome, [])
        if [x, y] not in pontos:
            pontos.append([x, y])
    dados[mapa] = mapeado
    caminho.write_text(
        json.dumps(dados, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return len(dados[mapa])
