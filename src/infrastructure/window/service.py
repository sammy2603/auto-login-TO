from __future__ import annotations

import ctypes
import threading
import time
from typing import Optional

import numpy as np
import win32con
import win32gui
import win32process
import win32ui

from .exceptions import WindowNotFoundError

# Acesso direto à função nativa do Windows, evita depender de versões
# do pywin32 que não expõem win32gui.PrintWindow.
_user32 = ctypes.windll.user32


class WindowService:
    """
    Serviço responsável pela comunicação com a janela do jogo.

    Toda a aplicação deve conversar apenas com esta classe.

    Implementação nativa (sem depender de módulos legados na raiz do
    projeto): localiza janelas via EnumWindows, captura o conteúdo da
    client area via PrintWindow (sem usar o mouse físico nem precisar
    que a janela esteja em primeiro plano).
    """

    # Trava COMPARTILHADA entre todas as instâncias (nível de classe).
    # Necessária pra rodar múltiplas contas em paralelo: se dois clients
    # abrirem quase ao mesmo tempo, o método de detecção (comparar
    # janelas antes/depois) poderia "roubar" a janela de outra conta.
    # A trava garante que só uma conta por vez fica no trecho crítico
    # de detectar sua própria janela nova -- o resto do fluxo de cada
    # conta continua rodando em paralelo normalmente.
    _new_window_lock = threading.Lock()

    def __init__(self):
        self._hwnd: Optional[int] = None

    # =====================================================
    # Propriedades
    # =====================================================

    @property
    def hwnd(self) -> int:

        if self._hwnd is None:
            raise RuntimeError(
                "Nenhuma janela conectada."
            )

        return self._hwnd

    # =====================================================
    # Conexão
    # =====================================================

    def connect_new_window(
        self,
        timeout: float = 30.0,
    ) -> tuple[int, int]:
        """
        Aguarda o surgimento de uma nova janela (comparando a lista de
        janelas visíveis antes/depois). Necessário porque launchers
        baseados em .bat costumam iniciar o executável real via
        "start", que roda como um processo separado com PID diferente
        do processo rastreado inicialmente.

        Retorna:
            (hwnd, pid)
        """

        with WindowService._new_window_lock:

            previous_windows = self._list_windows()

            hwnd = self._wait_for_new_window(
                previous_windows,
                timeout=timeout,
            )

        if hwnd is None:
            raise WindowNotFoundError(
                "Nenhuma nova janela foi encontrada."
            )

        self._hwnd = hwnd

        pid = self._get_window_pid(hwnd)

        return hwnd, pid

    def connect(
        self,
        title_substring: str | None = None,
        pid: int | None = None,
        timeout: float = 30.0,
    ) -> int:
        """
        Conecta a uma janela.

        Pode localizar por:
            - título (compatibilidade)
            - PID (novo modelo)
        """

        if pid is not None:

            hwnd = self._wait_for_window_by_pid(
                pid=pid,
                timeout=timeout,
            )

            if hwnd is None:
                raise WindowNotFoundError(
                    f"Não foi possível localizar uma janela para o PID {pid}."
                )

        else:

            if title_substring is None:
                raise ValueError(
                    "title_substring ou pid devem ser informados."
                )

            hwnd = self._wait_for_window(
                title_substring,
                timeout=timeout,
            )

            if hwnd is None:
                raise WindowNotFoundError(
                    f"Não foi possível localizar a janela '{title_substring}'."
                )

        self._hwnd = hwnd

        return hwnd

    def disconnect(self):

        self._hwnd = None

    def is_connected(self):

        return self._hwnd is not None

    # =====================================================
    # Busca
    # =====================================================

    def find(
        self,
        title_substring: str,
    ) -> Optional[int]:

        return self._find_window(title_substring)

    def find_by_pid(
        self,
        pid: int,
    ) -> Optional[int]:

        return self._find_window_by_pid(pid)

    # =====================================================
    # Captura
    # =====================================================

    def capture(self):
        """
        Captura a client area da janela atualmente conectada.
        """

        return self.capture_hwnd(self.hwnd)

    def capture_hwnd(self, hwnd) -> np.ndarray:
        """
        Captura o conteúdo da client area de QUALQUER janela (não
        precisa ser a conectada), usando a API PrintWindow do Windows.
        Não move o mouse, não precisa que a janela esteja em primeiro
        plano nem visível na tela (funciona até minimizada, em muitos
        casos).

        Retorna uma imagem no formato BGR (compatível com OpenCV).
        """

        width, height = self._get_client_size(hwnd)

        if width <= 0 or height <= 0:
            raise RuntimeError(
                "Janela com dimensões inválidas "
                "(pode estar minimizada sem suporte a PrintWindow)."
            )

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        # PW_CLIENTONLY (0x1) + PW_RENDERFULLCONTENT (0x2) = 3
        # PW_CLIENTONLY é essencial: sem ele, o PrintWindow captura a
        # janela inteira (incluindo barra de título/bordas), o que
        # desalinha as coordenadas encontradas pelo template matching
        # com as coordenadas reais da client area usadas nos cliques.
        _user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

        bmp_info = save_bitmap.GetInfo()
        bmp_bits = save_bitmap.GetBitmapBits(True)

        img = np.frombuffer(bmp_bits, dtype=np.uint8)
        img.shape = (bmp_info["bmHeight"], bmp_info["bmWidth"], 4)  # BGRA

        # Limpeza dos recursos do GDI
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        return img[:, :, :3]  # remove canal alpha, retorna BGR

    def client_size(self):

        return self._get_client_size(self.hwnd)

    # =====================================================
    # Implementação interna (Win32)
    # =====================================================

    @staticmethod
    def _get_client_size(hwnd):
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        return right - left, bottom - top

    @staticmethod
    def _find_window(title_substring: str):
        """
        Procura a primeira janela cujo título contenha
        'title_substring'. Retorna o handle (HWND) ou None.
        """
        result = {"hwnd": None}

        def _callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title_substring.lower() in title.lower():
                    result["hwnd"] = hwnd
                    return False
            return True

        win32gui.EnumWindows(_callback, None)
        return result["hwnd"]

    @staticmethod
    def _find_window_by_pid(pid: int):
        """
        Procura a primeira janela visível pertencente ao PID informado.
        """
        result = {"hwnd": None}

        def _callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if window_pid == pid:
                result["hwnd"] = hwnd
                return False
            return True

        win32gui.EnumWindows(_callback, None)
        return result["hwnd"]

    def _wait_for_window(
        self,
        title_substring: str,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ):
        start = time.time()
        while time.time() - start < timeout:
            hwnd = self._find_window(title_substring)
            if hwnd:
                return hwnd
            time.sleep(poll_interval)
        return None

    def _wait_for_window_by_pid(
        self,
        pid: int,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ):
        start = time.time()
        while time.time() - start < timeout:
            hwnd = self._find_window_by_pid(pid)
            if hwnd:
                return hwnd
            time.sleep(poll_interval)
        return None

    @staticmethod
    def _list_windows():
        """
        Retorna todos os HWND visíveis com título.
        """
        windows = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if not title.strip():
                return True
            windows.append(hwnd)
            return True

        win32gui.EnumWindows(callback, None)
        return windows

    def _wait_for_new_window(
        self,
        previous_windows,
        timeout=30.0,
        poll_interval=0.25,
    ):
        start = time.time()
        previous = set(previous_windows)

        while time.time() - start < timeout:
            current = set(self._list_windows())
            diff = current - previous
            if diff:
                return diff.pop()
            time.sleep(poll_interval)

        return None

    @staticmethod
    def _get_window_pid(hwnd):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid