"""
Testes do InputService.

Foco nas primitivas adicionadas para o BC: clique direito (que é o
botão de MOVIMENTO no jogo, e responde por 87% das ações do macro
original), segurar tecla e as teclas F.

Nenhum teste abre janela: as mensagens do Windows são interceptadas
substituindo win32api.PostMessage, então o que se verifica é
exatamente a sequência de mensagens que sairia.
"""

import pytest
import win32con

from src.infrastructure.input import service as input_module
from src.infrastructure.input.service import InputService

HWND = 4242


@pytest.fixture
def posted(monkeypatch):
    """Captura as mensagens que seriam enviadas, em ordem."""
    registro = []

    def fake_post(hwnd, msg, wparam, lparam):
        registro.append((hwnd, msg, wparam, lparam))

    monkeypatch.setattr(input_module.win32api, "PostMessage", fake_post)
    monkeypatch.setattr(input_module.time, "sleep", lambda _s: None)
    return registro


def mensagens(registro):
    return [m for _h, m, _w, _l in registro]


# ==========================================================
# Resolução de teclas
# ==========================================================

@pytest.mark.parametrize("tecla,vk", [
    ("F1", win32con.VK_F1),
    ("F12", win32con.VK_F12),
    ("TAB", win32con.VK_TAB),
    ("ENTER", win32con.VK_RETURN),
    ("SPACE", win32con.VK_SPACE),
])
def test_teclas_simbolicas(tecla, vk):
    assert InputService()._resolve_key(tecla)[0] == vk


def test_f12_agora_resolve():
    """
    Regressão: o macro do BC segura F12 o tempo todo, e antes disto
    press_key('F12') levantava ValueError -- a tecla simplesmente não
    existia no mapa.
    """
    vk, scan = InputService()._resolve_key("F12")
    assert vk == win32con.VK_F12
    assert scan == 0x58


def test_todas_as_teclas_f_resolvem():
    servico = InputService()
    for n in range(1, 13):
        vk, scan = servico._resolve_key(f"F{n}")
        assert vk == win32con.VK_F1 + (n - 1)
        assert scan != 0, f"F{n} sem scan code"


def test_caractere_unico():
    vk, scan = InputService()._resolve_key("3")
    assert vk == ord("3")
    assert scan == 0x04


def test_letra_e_normalizada_para_maiuscula():
    assert InputService()._resolve_key("i") == InputService()._resolve_key("I")


def test_codigo_virtual_int_passa_direto():
    assert InputService()._resolve_key(win32con.VK_BACK) == (win32con.VK_BACK, 0)


def test_tecla_desconhecida_levanta():
    with pytest.raises(ValueError):
        InputService()._resolve_key("NAOEXISTE")


# ==========================================================
# Mouse
# ==========================================================

def test_click_usa_botao_esquerdo(posted):
    InputService().click(HWND, 10, 20)
    assert mensagens(posted) == [
        win32con.WM_MOUSEMOVE,
        win32con.WM_LBUTTONDOWN,
        win32con.WM_LBUTTONUP,
    ]


def test_right_click_usa_botao_direito(posted):
    InputService().right_click(HWND, 10, 20)
    assert mensagens(posted) == [
        win32con.WM_MOUSEMOVE,
        win32con.WM_RBUTTONDOWN,
        win32con.WM_RBUTTONUP,
    ]


def test_double_right_click_envia_dblclk(posted):
    """
    Janelas com CS_DBLCLKS esperam a mensagem WM_RBUTTONDBLCLK; só
    repetir dois RBUTTONDOWN não equivale a um duplo clique pra elas.
    """
    InputService().double_right_click(HWND, 10, 20)
    assert win32con.WM_RBUTTONDBLCLK in mensagens(posted)


def test_coordenadas_vao_no_lparam(posted):
    InputService().right_click(HWND, 874, 105)
    _hwnd, _msg, _wparam, lparam = posted[0]
    assert lparam & 0xFFFF == 874
    assert (lparam >> 16) & 0xFFFF == 105


def test_click_vai_para_o_hwnd_pedido(posted):
    InputService().right_click(HWND, 1, 2)
    assert all(h == HWND for h, _m, _w, _l in posted)


# ==========================================================
# Segurar tecla
# ==========================================================

def test_key_down_nao_solta(posted):
    InputService().key_down(HWND, "F12")
    assert mensagens(posted) == [win32con.WM_KEYDOWN]


def test_key_up_solta(posted):
    InputService().key_up(HWND, "F12")
    assert mensagens(posted) == [win32con.WM_KEYUP]


def test_press_key_faz_down_e_up(posted):
    InputService().press_key(HWND, "3")
    assert mensagens(posted) == [win32con.WM_KEYDOWN, win32con.WM_KEYUP]


def test_held_key_solta_ao_sair(posted):
    with InputService().held_key(HWND, "F12"):
        assert mensagens(posted) == [win32con.WM_KEYDOWN]
    assert mensagens(posted) == [win32con.WM_KEYDOWN, win32con.WM_KEYUP]


def test_held_key_solta_mesmo_com_excecao(posted):
    """
    Tecla presa é pior que tecla não pressionada: o jogo fica com a
    janela de team aberta (ou pior) até alguém notar.
    """
    with pytest.raises(RuntimeError):
        with InputService().held_key(HWND, "F12"):
            raise RuntimeError("boom")

    assert mensagens(posted) == [win32con.WM_KEYDOWN, win32con.WM_KEYUP]
