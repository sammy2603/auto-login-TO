"""
Testes da lista de servidores.

A seleção na tela de servidores é feita por template matching
(`servidor_<nome>.png`), então um servidor listado sem o recorte falha
no login com TimeoutError -- depois de esperar o timeout inteiro. Daí a
checagem de template fazer parte do módulo, e não ser só detalhe da GUI.
"""

from src.shared.servers import (
    SERVERS,
    has_template,
    missing_templates,
    template_name,
)
from src.shared.templates import ServerTemplates


def test_todos_os_servidores_conhecidos():
    assert SERVERS == [
        "Sky Ice",
        "White Horse",
        "Tiger Fish",
        "All Stars",
        "Light in the Darkness",
    ]


def test_sem_duplicados():
    assert len(SERVERS) == len(set(SERVERS))


def test_nenhum_nome_com_espaco_sobrando():
    """Espaço extra viraria um nome de template que nunca casa."""
    for s in SERVERS:
        assert s == s.strip(), f"'{s}' tem espaço nas pontas"
        assert s, "nome de servidor vazio"


def test_template_name_bate_com_o_usado_no_workflow():
    """
    Se estes dois divergirem, a GUI checa a existência de um arquivo e o
    login procura outro -- e o erro só apareceria no jogo.
    """
    for s in SERVERS:
        assert template_name(s) == ServerTemplates.server(s)


def test_has_template_encontra_o_que_existe(tmp_path):
    (tmp_path / "servidor_Sky Ice.png").write_bytes(b"x")

    assert has_template("Sky Ice", str(tmp_path)) is True
    assert has_template("Tiger Fish", str(tmp_path)) is False


def test_missing_templates_lista_os_que_faltam(tmp_path):
    (tmp_path / "servidor_Sky Ice.png").write_bytes(b"x")

    faltando = missing_templates(str(tmp_path))

    assert "Sky Ice" not in faltando
    assert "Tiger Fish" in faltando
    assert len(faltando) == len(SERVERS) - 1


def test_missing_templates_vazio_quando_tem_todos(tmp_path):
    for s in SERVERS:
        (tmp_path / f"{template_name(s)}.png").write_bytes(b"x")

    assert missing_templates(str(tmp_path)) == []


def test_os_dois_servidores_originais_seguem_com_template():
    """
    Regressão: Sky Ice e White Horse já funcionavam antes do dropdown.
    Se um deles perder o recorte, o login para de funcionar.
    """
    assert has_template("Sky Ice")
    assert has_template("White Horse")
