# -*- coding: utf-8 -*-
"""
Scanner de memoria — acha offsets apos atualizacao do jogo.
Uso: python tools/scan_memory.py
"""

import sys, os, ctypes, struct, time
from ctypes import wintypes

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import win32gui, win32process, config
from src.infrastructure.window.service import WindowService

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

SCAN_RANGES = [
    (0x00400000, 0x01000000),
    (0x01000000, 0x02000000),
    (0x02000000, 0x04000000),
    (0x04000000, 0x08000000),
    (0x08000000, 0x10000000),
    (0x10000000, 0x18000000),
    (0x20000000, 0x28000000),
    (0x2F000000, 0x31000000),
]


class MemoryScanner:

    def __init__(self, pid):
        self._hp = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not self._hp:
            raise RuntimeError(f"OpenProcess falhou. Erro: {ctypes.get_last_error()}")
        self._results = []
        print(f"Processo PID={pid} aberto.")

    def close(self):
        if self._hp: kernel32.CloseHandle(self._hp)

    def scan_int(self, value, size=4):
        target = struct.pack("<I", value & 0xFFFFFFFF)[:size]
        self._scan_raw(target)

    def scan_string(self, text):
        # UTF-8
        print("UTF-8...")
        self._scan_raw(text.encode("utf-8") + b"\x00")
        # UTF-16
        print("UTF-16...")
        self._scan_raw(text.encode("utf-16-le") + b"\x00\x00")

    def scan_float(self, value):
        self._scan_raw(struct.pack("<f", value))

    def refine(self, value, size=4):
        target = struct.pack("<I", value & 0xFFFFFFFF)[:size]
        buf = ctypes.create_string_buffer(len(target))
        read = ctypes.c_size_t()
        new = []
        for addr in self._results:
            if kernel32.ReadProcessMemory(wintypes.HANDLE(self._hp), wintypes.LPCVOID(addr), buf, len(target), ctypes.byref(read)):
                if buf.raw[:len(target)] == target:
                    new.append(addr)
        removed = len(self._results) - len(new)
        self._results = new
        print(f"  {removed} removidos, {len(new)} restantes.")
        for r in new[:30]: print(f"    0x{r:08X}")
        if len(new) > 30: print(f"    ... +{len(new)-30}")

    def _scan_raw(self, target):
        results = []
        block = 65536
        buf = ctypes.create_string_buffer(block)
        read = ctypes.c_size_t()
        total = 0

        for start, end in SCAN_RANGES:
            addr = start
            last = time.time()
            while addr < end:
                # Progresso
                now = time.time()
                if now - last > 1.5:
                    pct = (addr - start) / (end - start) * 100
                    print(f"  0x{start:08X}: {pct:.0f}%  ({total} encontrados)")
                    last = now

                ok = kernel32.ReadProcessMemory(wintypes.HANDLE(self._hp), wintypes.LPCVOID(addr), buf, block, ctypes.byref(read))
                if ok:
                    data = buf.raw[:read.value]
                    pos = 0
                    while True:
                        idx = data.find(target, pos)
                        if idx < 0: break
                        results.append(addr + idx)
                        total += 1
                        pos = idx + 1
                    addr += block
                else:
                    addr += 0x10000  # pula pagina nao mapeada

        self._results = results
        print(f"\n  Total: {total} encontrados.")
        for r in results[:30]: print(f"    0x{r:08X}")
        if len(results) > 30: print(f"    ... +{len(results)-30}")

    def pointer_scan(self, target_addr, max_off=0x2000):
        print(f"\nPonteiros para 0x{target_addr:08X}...")
        results = []
        block = 65536
        buf = ctypes.create_string_buffer(block)
        read = ctypes.c_size_t()

        for start, end in [(0x00400000, 0x01400000)]:
            addr = start
            while addr < end:
                ok = kernel32.ReadProcessMemory(wintypes.HANDLE(self._hp), wintypes.LPCVOID(addr), buf, block, ctypes.byref(read))
                if ok:
                    data = buf.raw[:read.value]
                    for i in range(0, len(data) - 3, 4):
                        val = struct.unpack_from("<I", data, i)[0]
                        diff = val - target_addr
                        if -max_off <= diff <= max_off and val != 0:
                            results.append((addr + i, val, diff))
                    addr += block
                else:
                    addr += 0x10000

        static = [r for r in results if 0x400000 <= r[0] <= 0x1FFFFFFF]
        print(f"  {len(static)} estaticos:")
        for ptr, val, diff in static[:40]:
            print(f"    0x{ptr:08X} -> 0x{val:08X}  (+{diff:#x})")
        if len(static) > 40: print(f"    ... +{len(static)-40}")
        return results


def main():
    print("Memory Scanner")
    ws = WindowService()

    # Encontra janela
    try:
        hwnd = ws.connect(title_substring=config.WINDOW_TITLE, timeout=3)
    except Exception:
        hwnds = WindowService._list_windows()
        hwnd = next((h for h in hwnds if win32gui.GetWindowText(h).strip()), None)
    if not hwnd:
        print("Nenhuma janela. Abra o jogo."); sys.exit(1)

    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    print(f"PID={pid}")
    s = MemoryScanner(pid)

    while True:
        print(f"\n{'='*50}\nResultados: {len(s._results)}")
        print("1. Inteiro  2. String  3. Refinar  4. Pointer scan  5. Sair")
        c = input("> ").strip()

        if c == "1":
            v = input("Valor: ").strip()
            sz = input("Tamanho (1/2/4) [4]: ").strip() or "4"
            s.scan_int(int(v), int(sz))
        elif c == "2":
            s.scan_string(input("Texto: ").strip())
        elif c == "3":
            if not s._results: print("Scan primeiro."); continue
            v = input("Novo valor: ").strip()
            sz = input("Tamanho [4]: ").strip() or "4"
            s.refine(int(v), int(sz))
        elif c == "4":
            try: s.pointer_scan(int(input("Endereco (ex: 0xABCD): ").strip(), 16))
            except ValueError: print("Invalido.")
        elif c == "5":
            break

    s.close()


if __name__ == "__main__":
    main()
