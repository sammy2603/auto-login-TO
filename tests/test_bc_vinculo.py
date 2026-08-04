"""
Testes do vínculo da dupla do BC.

A mecânica: a cave reseta quando o team é desfeito e refeito. Por isso
são necessários DOIS personagens -- um que faz a BC (runner) e outro
que só entra e sai do grupo (reseter).

Os dois se reconhecem por nomes CRUZADOS: o runner aponta pro reseter e
o reseter aponta de volta pro runner. Sem isso não há como saber quem
forma par com quem quando vários clients estão abertos.

A lógica de vínculo mora na MainWindow (é estado de apresentação), mas
instanciar a janela exigiria Tkinter com display. Os testes abaixo
exercitam os métodos ligados a uma instância mínima, sem construir a
GUI.
"""

import pytest

from src.services.bot.scripts.bc import DEFAULT_CONFIG
from src.ui.main_window import MainWindow


class FakeController:
    def __init__(self, sessoes):
        self._sessoes = sessoes

    def get_sessions(self):
        return self._sessoes


class JanelaFalsa:
    """
    Instância mínima com só o que os métodos de vínculo usam.

    Usar __new__ evitaria o __init__ da MainWindow (que abre janela),
    mas ainda assim carregaria estado demais; um objeto próprio com os
    métodos ligados é mais honesto sobre a dependência real.
    """

    def __init__(self, sessoes, configs):
        self.controller = FakeController(sessoes)
        self._bc_configs = configs
        self._selected_window = None

    # Métodos sob teste, emprestados da MainWindow.
    _bc_config_da_conta = MainWindow._bc_config_da_conta
    _conferir_vinculo_bc = MainWindow._conferir_vinculo_bc
    _current_script_configs = MainWindow._current_script_configs


def sessoes(*nomes):
    return {n: {"display": n, "hwnd": 1} for n in nomes}


def cfg(**extra):
    return {**DEFAULT_CONFIG, **extra}


# ==========================================================
# Config por conta
# ==========================================================
#
# Era global antes, o que tornava o recurso IMPOSSÍVEL: não dava pra
# ter Bot1 como runner e Bot2 como reseter ao mesmo tempo.

def test_cada_conta_tem_a_propria_config():
    j = JanelaFalsa(sessoes("Bot1", "Bot2"), {})

    c1 = j._bc_config_da_conta("Bot1")
    c2 = j._bc_config_da_conta("Bot2")

    c1["reseter"] = False
    c2["reseter"] = True

    assert j._bc_config_da_conta("Bot1")["reseter"] is False
    assert j._bc_config_da_conta("Bot2")["reseter"] is True


def test_config_da_conta_e_estavel_entre_chamadas():
    j = JanelaFalsa(sessoes("Bot1"), {})
    assert j._bc_config_da_conta("Bot1") is j._bc_config_da_conta("Bot1")


def test_sem_conta_devolve_rascunho_descartavel():
    """Não pode devolver None -- o diálogo abriria vazio."""
    j = JanelaFalsa({}, {})
    rascunho = j._bc_config_da_conta(None)

    assert rascunho == DEFAULT_CONFIG
    assert j._bc_configs == {}, "rascunho não pode virar config de conta"


def test_script_configs_entrega_a_config_da_conta_pedida():
    j = JanelaFalsa(sessoes("Bot1", "Bot2"), {
        "Bot1": cfg(reseter=False),
        "Bot2": cfg(reseter=True),
    })

    assert j._current_script_configs("Bot1")["bc"]["reseter"] is False
    assert j._current_script_configs("Bot2")["bc"]["reseter"] is True


# ==========================================================
# Vínculo
# ==========================================================

def test_dupla_bem_formada_nao_avisa():
    """Bot1 roda a BC e aponta pro Bot2; Bot2 é reseter e aponta de volta."""
    configs = {
        "Bot1": cfg(member_name="Bot2", reseter=False),
        "Bot2": cfg(member_name="Bot1", reseter=True),
    }
    j = JanelaFalsa(sessoes("Bot1", "Bot2"), configs)

    assert j._conferir_vinculo_bc("Bot1", configs["Bot1"]) == ""
    assert j._conferir_vinculo_bc("Bot2", configs["Bot2"]) == ""


def test_sem_member_name_avisa():
    configs = {"Bot1": cfg(member_name="")}
    j = JanelaFalsa(sessoes("Bot1"), configs)

    aviso = j._conferir_vinculo_bc("Bot1", configs["Bot1"])
    assert "dupla" in aviso.lower()


def test_parceiro_nao_logado_avisa_sem_acusar_erro():
    """
    O parceiro pode simplesmente não estar aberto ainda -- isso não é
    configuração errada.
    """
    configs = {"Bot1": cfg(member_name="Bot2")}
    j = JanelaFalsa(sessoes("Bot1"), configs)

    aviso = j._conferir_vinculo_bc("Bot1", configs["Bot1"])
    assert "não está logado" in aviso


def test_parceiro_sem_bc_configurado_avisa():
    configs = {"Bot1": cfg(member_name="Bot2")}
    j = JanelaFalsa(sessoes("Bot1", "Bot2"), configs)

    aviso = j._conferir_vinculo_bc("Bot1", configs["Bot1"])
    assert "ainda não tem o BC configurado" in aviso


def test_os_dois_como_runner_avisa():
    """Ninguém reseta a cave se os dois quiserem fazer a BC."""
    configs = {
        "Bot1": cfg(member_name="Bot2", reseter=False),
        "Bot2": cfg(member_name="Bot1", reseter=False),
    }
    j = JanelaFalsa(sessoes("Bot1", "Bot2"), configs)

    aviso = j._conferir_vinculo_bc("Bot1", configs["Bot1"])
    assert "runner" in aviso


def test_os_dois_como_reseter_avisa():
    configs = {
        "Bot1": cfg(member_name="Bot2", reseter=True),
        "Bot2": cfg(member_name="Bot1", reseter=True),
    }
    j = JanelaFalsa(sessoes("Bot1", "Bot2"), configs)

    aviso = j._conferir_vinculo_bc("Bot1", configs["Bot1"])
    assert "reseter" in aviso


def test_nome_cruzado_errado_avisa_e_mostra_para_quem_aponta():
    """
    Bot1 aponta pro Bot2, mas o Bot2 aponta pra um terceiro. O aviso
    precisa dizer PRA QUEM ele aponta, senão não dá pra corrigir.
    """
    configs = {
        "Bot1": cfg(member_name="Bot2", reseter=False),
        "Bot2": cfg(member_name="Bot3", reseter=True),
    }
    j = JanelaFalsa(sessoes("Bot1", "Bot2", "Bot3"), configs)

    aviso = j._conferir_vinculo_bc("Bot1", configs["Bot1"])
    assert "Bot3" in aviso and "Bot1" in aviso


def test_parceiro_com_member_name_vazio_avisa_legivel():
    configs = {
        "Bot1": cfg(member_name="Bot2", reseter=False),
        "Bot2": cfg(member_name="", reseter=True),
    }
    j = JanelaFalsa(sessoes("Bot1", "Bot2"), configs)

    aviso = j._conferir_vinculo_bc("Bot1", configs["Bot1"])
    assert "(vazio)" in aviso


def test_nome_do_parceiro_ignora_maiusculas_e_espacos():
    configs = {
        "Bot1": cfg(member_name="  bot2  ", reseter=False),
        "Bot2": cfg(member_name="BOT1", reseter=True),
    }
    j = JanelaFalsa(sessoes("Bot1", "Bot2"), configs)

    assert j._conferir_vinculo_bc("Bot1", configs["Bot1"]) == ""


def test_dois_problemas_aparecem_juntos():
    """Papel errado E nome cruzado errado ao mesmo tempo."""
    configs = {
        "Bot1": cfg(member_name="Bot2", reseter=True),
        "Bot2": cfg(member_name="Bot3", reseter=True),
    }
    j = JanelaFalsa(sessoes("Bot1", "Bot2", "Bot3"), configs)

    aviso = j._conferir_vinculo_bc("Bot1", configs["Bot1"])
    assert "reseter" in aviso and "Bot3" in aviso
