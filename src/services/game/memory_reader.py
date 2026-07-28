from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

import win32api
import win32process
import win32con
import win32gui


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# =====================================================
# ReadProcessMemory wrapper
# =====================================================

def _rpm_int(hProcess: int, address: int, size: int, signed: bool = False) -> int:
    """Le N bytes de um endereco e retorna como inteiro."""
    buf = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(
        wintypes.HANDLE(hProcess),
        wintypes.LPCVOID(address),
        buf,
        size,
        ctypes.byref(bytes_read),
    ):
        return 0
    return int.from_bytes(buf.raw[:size], "little", signed=signed)


def _rpm_float(hProcess: int, address: int) -> float:
    """Le 4 bytes como float."""
    buf = ctypes.create_string_buffer(4)
    bytes_read = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(
        wintypes.HANDLE(hProcess),
        wintypes.LPCVOID(address),
        buf,
        4,
        ctypes.byref(bytes_read),
    ):
        return 0.0
    return ctypes.c_float.from_buffer_copy(buf.raw[:4]).value


def _rpm_string(hProcess: int, address: int, max_len: int = 64) -> str:
    """Le uma string terminada em null."""
    buf = ctypes.create_string_buffer(max_len)
    bytes_read = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(
        wintypes.HANDLE(hProcess),
        wintypes.LPCVOID(address),
        buf,
        max_len,
        ctypes.byref(bytes_read),
    ):
        return ""
    raw = buf.raw[: bytes_read.value]
    null_pos = raw.find(b"\x00")
    if null_pos >= 0:
        raw = raw[:null_pos]
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


# =====================================================
# MemoryReader — leitura de memoria do Talisman Online
# =====================================================

class MemoryReader:
    """
    Le dados do jogo diretamente da memoria do processo.

    Baseado nos offsets do pointers.lua do SSCBot.
    """

    CLIENT_BASE = 0x00400000

    # Ponteiros base
    CHAR_BASE = 0x011450EC
    TARGET_BASE = 0x012CE2E0
    SPLIT_BASE = 0x012CE2E0
    XP_BASE = 0x011396A0
    TEAM_SIZE_BASE = 0x0106D328

    def __init__(self, pid: int):
        self._pid = pid
        self._hProcess: int | None = None
        self._open()

    def _open(self):
        """Abre o processo com acesso de leitura."""
        self._hProcess = kernel32.OpenProcess(
            win32con.PROCESS_VM_READ,
            False,
            self._pid,
        )
        if not self._hProcess:
            raise RuntimeError(
                f"Nao foi possivel abrir o processo PID={self._pid}. "
                f"Erro: {ctypes.get_last_error()}"
            )

    def close(self):
        if self._hProcess:
            kernel32.CloseHandle(self._hProcess)
            self._hProcess = None

    def __del__(self):
        self.close()

    # =====================================================
    # Helpers de leitura
    # =====================================================

    def _read_ptr(self, address: int, offset: int = 0) -> int:
        """Le um ponteiro (dword) e aplica offset."""
        base = _rpm_int(self._hProcess, address, 4)
        if base == 0:
            return 0
        return base + offset

    def _follow_chain(self, base_addr: int, offsets: list[int]) -> int:
        """Segue uma cadeia de ponteiros + offsets e retorna o
        endereco final."""
        ptr = _rpm_int(self._hProcess, base_addr, 4)
        if ptr == 0:
            return 0
        for off in offsets[:-1]:
            ptr = _rpm_int(self._hProcess, ptr + off, 4)
            if ptr == 0:
                return 0
        return ptr + offsets[-1]

    # =====================================================
    # Char Info
    # =====================================================

    @property
    def hp(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x3B8), 4)

    @property
    def max_hp(self) -> int:
        hp = _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0xDC), 4)
        hp_buff = _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0xE0), 4)
        hp += hp_buff
        plus = _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0xE4), 1)
        if plus >= 100:
            plus -= 100
        if plus > 1:
            hp = int((hp * plus) / 100 + hp)
        return hp

    @property
    def hp_pct(self) -> float:
        max_val = self.max_hp
        if max_val == 0:
            return 0.0
        return (self.hp / max_val) * 100.0

    @property
    def mana(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x3BC), 4)

    @property
    def max_mana(self) -> int:
        mana = _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x6EC), 4)
        mana_buff = _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x6F0), 4)
        return mana + mana_buff

    @property
    def mana_pct(self) -> float:
        max_val = self.max_mana
        if max_val == 0:
            return 0.0
        return (self.mana / max_val) * 100.0

    @property
    def level(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x3C4), 2)

    @property
    def char_name(self) -> str:
        addr = self._read_ptr(self.CHAR_BASE, 0xBC)
        name = _rpm_string(self._hProcess, addr, 30)
        if name and name.isascii() and name.replace(" ", "").isalnum():
            return name
        str_ptr = _rpm_int(self._hProcess, addr, 4)
        if str_ptr:
            return _rpm_string(self._hProcess, str_ptr, 30)
        return name

    @property
    def x(self) -> int:
        val = _rpm_float(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x810)) / 20.0
        return int(val) if val >= 0 else int(val) - 1 if val < 0 else int(val)

    @property
    def y(self) -> int:
        val = _rpm_float(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x814)) / 20.0
        return int(val) if val >= 0 else int(val) - 1 if val < 0 else int(val)

    @property
    def in_battle(self) -> bool:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x854), 1) == 1

    @property
    def is_mounted(self) -> bool:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x8B0), 4) != 0

    @property
    def pet_alive(self) -> bool:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x10A8), 4) != 0

    @property
    def breakpoint(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x3E0), 4)

    @property
    def location(self) -> str:
        chain = [self.CHAR_BASE, 0x7F8, 0xF4, 0x44C]
        addr = self._follow_chain(self.CHAR_BASE, [0x7F8, 0xF4, 0x44C])
        if addr == 0:
            return ""
        loc = _rpm_string(self._hProcess, addr, 51)
        if loc and loc.replace(" ", "").replace("'", "").isalnum():
            return loc
        str_ptr = _rpm_int(self._hProcess, addr, 4)
        if str_ptr:
            return _rpm_string(self._hProcess, str_ptr, 51)
        return loc

    # =====================================================
    # Target
    # =====================================================

    @property
    def target_selected(self) -> bool:
        chain = [self.CLIENT_BASE + 0x00EC05C8, 0xD0, 0x2DC, 0x24, 0xC10]
        addr = self._follow_chain(chain[0], chain[1:])
        return _rpm_int(self._hProcess, addr, 1) == 1 if addr else False

    @property
    def target_hp(self) -> int:
        chain = [self.TARGET_BASE, 0x18, 0x59C, 0x0, 0xC, 0x1F4, 0x15C, 0x480]
        addr = self._follow_chain(chain[0], chain[1:])
        return _rpm_int(self._hProcess, addr, 2) if addr else 0

    @property
    def target_hp_pct(self) -> float:
        hp = self.target_hp
        if hp == 0:
            return 0.0
        return (hp / 597.0) * 100.0  # 597 = HP cheio do alvo

    @property
    def target_name(self) -> str:
        chain = [self.TARGET_BASE, 0x18, 0xB1C, 0x0, 0xC, 0xD9C, 0x9AC]
        addr = self._follow_chain(chain[0], chain[1:])
        if addr == 0:
            return ""
        name = _rpm_string(self._hProcess, addr, 51)
        if name and name.replace(" ", "").replace("'", "").isalnum():
            return name
        str_ptr = _rpm_int(self._hProcess, addr, 4)
        if str_ptr:
            return _rpm_string(self._hProcess, str_ptr, 51)
        return name

    @property
    def target_dead(self) -> bool:
        return self.target_hp == 0

    # =====================================================
    # Outros
    # =====================================================

    @property
    def team_size(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.TEAM_SIZE_BASE, 0x3D8), 4)

    @property
    def is_sitting(self) -> bool:
        return _rpm_int(self._hProcess, 0x305F08B8, 4) == 200

    @property
    def is_channeling(self) -> bool:
        return _rpm_int(
            self._hProcess,
            self._read_ptr(self.CLIENT_BASE + 0x00D3537C, 0x10),
            4,
        ) == 24

    @property
    def notification(self) -> bool:
        return _rpm_int(self._hProcess, self.CLIENT_BASE + 0xD7097C, 4) == 1

    @property
    def confirm_box(self) -> bool:
        return _rpm_int(self._hProcess, 0x012CE35C, 4) == 1

    @property
    def xp_pct(self) -> float:
        chain = [0xF0, 0x80, 0x28, 0x60, 0x5C, 0x228, 0x3EFC]
        addr = self._follow_chain(self.XP_BASE, chain)
        if addr == 0:
            return 0.0
        xp_str = _rpm_string(self._hProcess, addr, 10)
        try:
            return float(xp_str.replace("%", "").strip())
        except ValueError:
            return 0.0

    @property
    def dialog_open(self) -> bool:
        chain = [0x0117B27C, 0x70, 0x56C, 0xC, 0x4, 0x42C, 0x1F8, 0x240]
        addr = self._follow_chain(chain[0], chain[1:])
        return _rpm_int(self._hProcess, addr, 4) == 16775 if addr else False

    @property
    def bag_open(self) -> bool:
        chain = [self.SPLIT_BASE, 0x18, 0x5C4, 0x0, 0xC, 0x1F8, 0x42C, 0xBA0]
        addr = self._follow_chain(chain[0], chain[1:])
        return _rpm_int(self._hProcess, addr, 4) == 903 if addr else False

    @property
    def loot_window(self) -> bool:
        return _rpm_int(self._hProcess, 0x0105B958, 4) == 1
