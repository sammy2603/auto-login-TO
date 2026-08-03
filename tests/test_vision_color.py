"""
Testes da verificação por cor do VisionService.

O macro antigo do BC usava cor de pixel como única realimentação em
~650 ações -- em particular o `while_not 945,148 <verde>` que retenta
entrar na cave até funcionar. É o padrão que vale generalizar.

Nenhum teste abre janela: o WindowService é substituído por um dublê
que devolve uma imagem sintética.
"""

import numpy as np
import pytest

from src.infrastructure.vision.service import VisionService

VERMELHO = (255, 0, 0)
VERDE = (0, 255, 0)
AZUL = (0, 0, 255)


class FakeWindowService:
    """Devolve sempre a mesma imagem. Captura é BGR, como no OpenCV."""

    def __init__(self, imagem):
        self.imagem = imagem

    def capture_hwnd(self, hwnd):
        return self.imagem


def tela(largura=100, altura=50, fundo=(0, 0, 0)):
    """Cria uma imagem BGR preenchida com 'fundo' (dado em RGB)."""
    r, g, b = fundo
    img = np.zeros((altura, largura, 3), dtype=np.uint8)
    img[:, :] = (b, g, r)
    return img


def servico(imagem):
    return VisionService(window_service=FakeWindowService(imagem))


# ==========================================================
# Conversão de cor
# ==========================================================

def test_to_rgb_aceita_tupla():
    assert VisionService._to_rgb((10, 20, 30)) == (10, 20, 30)


def test_to_rgb_aceita_int():
    assert VisionService._to_rgb(0xFF8000) == (255, 128, 0)


def test_to_rgb_verde_puro():
    """65280 == 0x00FF00: o valor que o macro usa pra 'entrou na cave'."""
    assert VisionService._to_rgb(65280) == (0, 255, 0)


def test_to_rgb_rejeita_lixo():
    with pytest.raises(ValueError):
        VisionService._to_rgb("verde")

    with pytest.raises(ValueError):
        VisionService._to_rgb((1, 2))


# ==========================================================
# pixel_rgb
# ==========================================================

def test_pixel_rgb_converte_de_bgr_para_rgb():
    """
    A captura vem BGR do OpenCV, mas a API pública fala RGB. Trocar os
    canais aqui daria um erro silencioso e difícil de achar.
    """
    img = tela(fundo=VERMELHO)
    assert servico(img).pixel_rgb(1, 5, 5) == (255, 0, 0)


def test_pixel_rgb_fora_dos_limites_retorna_none():
    img = tela(largura=10, altura=10)
    s = servico(img)
    assert s.pixel_rgb(1, 50, 5) is None
    assert s.pixel_rgb(1, 5, 50) is None
    assert s.pixel_rgb(1, -1, 5) is None


def test_pixel_rgb_sem_captura_retorna_none():
    assert servico(None).pixel_rgb(1, 0, 0) is None


# ==========================================================
# pixel_matches
# ==========================================================

def test_pixel_matches_exato():
    assert servico(tela(fundo=VERDE)).pixel_matches(1, 5, 5, VERDE) is True


def test_pixel_matches_aceita_int():
    assert servico(tela(fundo=VERDE)).pixel_matches(1, 5, 5, 65280) is True


def test_pixel_matches_cor_diferente():
    assert servico(tela(fundo=VERMELHO)).pixel_matches(1, 5, 5, VERDE) is False


def test_pixel_matches_dentro_da_tolerancia():
    """
    Anti-aliasing e brilho fazem a cor variar. Exigir igualdade exata
    faz a verificação falhar de forma intermitente -- pior que não ter.
    """
    quase = servico(tela(fundo=(0, 250, 0)))
    assert quase.pixel_matches(1, 5, 5, VERDE, tolerance=10) is True
    assert quase.pixel_matches(1, 5, 5, VERDE, tolerance=2) is False


def test_pixel_matches_fora_da_tela_e_falso():
    assert servico(tela(largura=10, altura=10)).pixel_matches(1, 99, 99, VERDE) is False


# ==========================================================
# find_color
# ==========================================================

def test_find_color_encontra_e_devolve_x_y():
    img = tela()
    img[30, 70] = (0, 255, 0)  # BGR de verde, na linha 30 coluna 70
    assert servico(img).find_color(1, VERDE) == (70, 30)


def test_find_color_ausente_retorna_none():
    assert servico(tela()).find_color(1, VERDE) is None


def test_find_color_respeita_a_regiao():
    img = tela()
    img[10, 10] = (0, 255, 0)

    s = servico(img)
    assert s.find_color(1, VERDE, region=(0, 0, 50, 50)) == (10, 10)
    assert s.find_color(1, VERDE, region=(60, 0, 100, 50)) is None


def test_find_color_devolve_coordenada_da_janela_nao_da_regiao():
    """
    Dentro do recorte o pixel está em (5, 5); na janela, em (65, 25).
    Devolver a coordenada da região faria o clique cair no lugar errado.
    """
    img = tela()
    img[25, 65] = (0, 255, 0)
    assert servico(img).find_color(1, VERDE, region=(60, 20, 100, 50)) == (65, 25)


def test_find_color_regiao_invalida_retorna_none():
    img = tela()
    img[10, 10] = (0, 255, 0)
    s = servico(img)
    assert s.find_color(1, VERDE, region=(50, 50, 10, 10)) is None


def test_find_color_regiao_e_recortada_aos_limites():
    """Região maior que a tela não pode estourar índice."""
    img = tela(largura=100, altura=50)
    img[10, 10] = (0, 255, 0)
    assert servico(img).find_color(1, VERDE, region=(0, 0, 9999, 9999)) == (10, 10)


def test_find_color_sem_captura_retorna_none():
    assert servico(None).find_color(1, VERDE) is None


# ==========================================================
# Busca de template por região
# ==========================================================
#
# Usada pra achar a bag de courage só dentro do inventário: procurar na
# tela toda aumenta a chance de casar com algo parecido em outro canto.

def _icone():
    """
    Padrão 10x10 com quatro quadrantes de cores diferentes.

    Precisa ter variância: TM_CCOEFF_NORMED é degenerado com template
    de cor uniforme (correlação indefinida), e casa em qualquer lugar
    -- inclusive num fundo liso.
    """
    patch = np.zeros((10, 10, 3), dtype=np.uint8)
    patch[:5, :5] = (255, 0, 0)
    patch[:5, 5:] = (0, 255, 0)
    patch[5:, :5] = (0, 0, 255)
    patch[5:, 5:] = (255, 255, 255)
    return patch


def _servico_com_template(imagem, template, tmp_path):
    import cv2

    cv2.imwrite(str(tmp_path / "alvo.png"), template)
    return VisionService(
        window_service=FakeWindowService(imagem),
        templates_dir=str(tmp_path),
    )


def _tela_com_icone(x, y, largura=200, altura=100):
    img = tela(largura=largura, altura=altura)
    icone = _icone()
    img[y:y + 10, x:x + 10] = icone
    return img


def test_locate_in_window_acha_sem_regiao(tmp_path):
    img = _tela_com_icone(120, 50)
    s = _servico_com_template(img, _icone(), tmp_path)
    assert s.locate_in_window(1, "alvo", threshold=0.8) is not None


def test_locate_in_window_devolve_coordenada_da_janela(tmp_path):
    """
    Achou dentro do recorte, mas a coordenada devolvida tem que ser a
    da janela -- senão o clique cai no lugar errado.
    """
    img = _tela_com_icone(120, 50)
    s = _servico_com_template(img, _icone(), tmp_path)

    pos = s.locate_in_window(1, "alvo", threshold=0.8, region=(100, 40, 200, 100))

    assert pos is not None
    x, y = pos
    assert 118 <= x <= 132, f"x={x} fora do esperado"
    assert 48 <= y <= 62, f"y={y} fora do esperado"


def test_locate_in_window_regiao_sem_o_alvo_retorna_none(tmp_path):
    img = _tela_com_icone(120, 50)
    s = _servico_com_template(img, _icone(), tmp_path)
    assert s.locate_in_window(1, "alvo", threshold=0.9, region=(0, 0, 50, 50)) is None


def test_locate_in_window_template_maior_que_a_regiao_nao_quebra(tmp_path):
    """matchTemplate levanta se o template não couber; tratamos como não achou."""
    img = tela(largura=200, altura=100)
    template = np.zeros((40, 40, 3), dtype=np.uint8)
    template[:20, :20] = (255, 0, 0)

    s = _servico_com_template(img, template, tmp_path)
    assert s.locate_in_window(1, "alvo", region=(0, 0, 20, 20)) is None


def test_locate_in_window_sem_captura_retorna_none(tmp_path):
    import cv2

    cv2.imwrite(str(tmp_path / "alvo.png"), np.zeros((5, 5, 3), dtype=np.uint8))
    s = VisionService(window_service=FakeWindowService(None), templates_dir=str(tmp_path))
    assert s.locate_in_window(1, "alvo") is None


def test_find_template_com_template_ausente_avisa_e_segue(tmp_path):
    """
    Sem templates/courage_bag.png capturado, o passo do courage não pode
    derrubar o ciclo do BC.
    """
    s = VisionService(window_service=FakeWindowService(tela()), templates_dir=str(tmp_path))
    assert s.find_template(1, "nao_existe") is None
