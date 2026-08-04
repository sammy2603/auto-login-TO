# -*- coding: utf-8 -*-
"""
Servidores do jogo.

Fonte unica da lista. A GUI monta o dropdown a partir daqui, entao
adicionar um servidor novo e acrescentar UMA linha nesta lista -- nenhum
outro arquivo precisa saber quais servidores existem.

IMPORTANTE: cada servidor precisa do seu recorte em
templates/servidor_<nome>.png, porque a selecao na tela de servidores e
feita por template matching (ver ServerTemplates.server). Sem o
template, o login falha com TimeoutError depois de esperar o timeout
inteiro. Use tools/calibrar.py pra capturar.
"""

from __future__ import annotations

import os

SERVERS = [
    "Sky Ice",
    "White Horse",
    "Tiger Fish",
    "All Stars",
    "Light in the Darkness",
]

_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "templates",
)


def template_name(server: str) -> str:
    """Nome do template (sem extensao) do servidor."""
    return f"servidor_{server}"


def has_template(server: str, templates_dir: str | None = None) -> bool:
    """
    Verdadeiro se o recorte do servidor existe.

    A GUI usa isto pra avisar, no proprio dropdown, quais servidores
    ainda nao dao pra usar -- descobrir isso so na hora do login, depois
    de esperar o timeout, seria bem pior.
    """
    pasta = templates_dir or _TEMPLATES_DIR
    return os.path.exists(os.path.join(pasta, f"{template_name(server)}.png"))


def missing_templates(templates_dir: str | None = None) -> list[str]:
    """Servidores da lista que ainda nao tem recorte."""
    return [s for s in SERVERS if not has_template(s, templates_dir)]
