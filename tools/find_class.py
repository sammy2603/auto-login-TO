import ctypes, struct, win32gui, win32process, sys, os
from ctypes import wintypes
sys.path.insert(0, r"C:\Users\Sammy\Documents\LoginTO")
from src.services.game.memory_reader import MemoryReader
from src.infrastructure.window.service import WindowService

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ws = WindowService()
all_w = ws._list_windows()
pid = None
for h in all_w:
    _, tp = win32process.GetWindowThreadProcessId(h)
    hp2 = kernel32.OpenProcess(0x0010, False, tp)
    if hp2: kernel32.CloseHandle(hp2)
    else: continue
    try:
        mr = MemoryReader(tp); n = mr.char_name; mr.close()
        if n: pid = tp; break
    except: pass

if not pid: print('Jogo nao encontrado'); sys.exit(1)

hp = kernel32.OpenProcess(0x0010, False, pid)
buf = ctypes.create_string_buffer(4)
read = ctypes.c_size_t()
r = lambda a: struct.unpack('<I', buf[:4])[0] if kernel32.ReadProcessMemory(wintypes.HANDLE(hp), wintypes.LPCVOID(a), buf, 4, ctypes.byref(read)) else 0
r2 = lambda a: struct.unpack('<H', buf[:2])[0] if kernel32.ReadProcessMemory(wintypes.HANDLE(hp), wintypes.LPCVOID(a), buf, 2, ctypes.byref(read)) else 0
r1 = lambda a: buf.raw[0] if kernel32.ReadProcessMemory(wintypes.HANDLE(hp), wintypes.LPCVOID(a), buf, 1, ctypes.byref(read)) else 0

BASE = 0x0114514C
ptr = r(BASE)

# Procura class ID perto do level (0x3C4 = level 3) e do nome (0x45C)
print('DWORDs perto do nome (0x440-0x480):')
for off in range(0x440, 0x480, 4):
    print(f'  +0x{off:03X} = {r(ptr+off)}')

print()
print('WORDs perto do level (0x3C0-0x3D4):')
for off in range(0x3C0, 0x3D4, 2):
    print(f'  WORD +0x{off:03X} = {r2(ptr+off)}')

print()
print('BYTEs perto do nome (0x440-0x470):')  
for off in range(0x440, 0x470, 1):
    v = r1(ptr+off)
    if 1 <= v <= 6:
        print(f'  BYTE +0x{off:03X} = {v}')

# Tenta ler diretamente dos enderecos Monk como string
print()
print('Strings nos enderecos Monk encontrados:')
for addr in [0x05C07A18, 0x05F6503C, 0x1249E128]:
    buf2 = ctypes.create_string_buffer(32)
    r3 = ctypes.c_size_t()
    if kernel32.ReadProcessMemory(wintypes.HANDLE(hp), wintypes.LPCVOID(addr), buf2, 32, ctypes.byref(r3)):
        s = buf2.raw[:r3.value].split(b'\x00')[0].decode('utf-8', errors='replace')
        print(f'  0x{addr:08X} = "{s}"')

kernel32.CloseHandle(hp)
