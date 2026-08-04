# -*- coding: utf-8 -*-
"""
Compara os dois conjuntos de ponteiros conhecidos do Talisman Online
lado a lado, contra o cliente rodando.

Fontes:
  loginto  -- src/services/game/memory_reader.py (SSCBot / pointers.lua)
  ramora   -- RamoraBOT/pointers.py (bot descontinuado)

As bases estaticas dos dois conjuntos divergem em 0x60 na maioria dos
campos: sao builds diferentes do cliente. Este script le os dois e diz
qual produz valores sensatos, para nao ficarmos chutando offset.

Se os DOIS derem lixo, o jogo atualizou e as bases morreram. Nesse caso
a secao "Bases estaticas" separa "base morta" (0 ou lixo) de "base viva,
offset mudou" (ponteiro plausivel de heap) -- e ai o proximo passo e o
tools/scan_memory.py para reencontrar as bases.

Uso:
    python tools/comparar_ponteiros.py
    python tools/comparar_ponteiros.py --pid 1234
    python tools/comparar_ponteiros.py --autoteste
"""

from __future__ import annotations

import argparse
import ctypes
import os
import re
import string
import sys
from ctypes import wintypes

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Faixa plausivel para um ponteiro de heap em processo 32 bits.
HEAP_MIN = 0x00010000
HEAP_MAX = 0x7FFFFFFF


# =====================================================
# Catalogo
# =====================================================

# Bases estaticas por fonte. Ausencia de chave = a fonte nao conhece
# essa base.
BASES = {
    "CHAR":      {"loginto": 0x0114514C, "ramora": 0x011450EC},
    "TARGET":    {"loginto": 0x012CE340, "ramora": 0x012CE2E0},
    "TEAM":      {"loginto": 0x0106D388, "ramora": 0x0106D328},
    "DIALOGO":   {"loginto": 0x0117B2DC, "ramora": 0x0117B27C},
    "ENTIDADES": {"ramora": 0x012C05C8},   # CLIENT + 0xEC05C8
    "SUR":       {"ramora": 0x012CE2DC},
    "CAMERA":    {"ramora": 0x0116FFF4},
    "XP":        {"loginto": 0x01139700},
}

# Enderecos lidos direto, sem cadeia.
ESTATICOS = {
    "notification": {"loginto": 0x0117097C, "ramora": 0x0117097C},
    "loot_window":  {"loginto": 0x0105B9B8, "ramora": 0x0105B958},
    "confirm_box":  {"loginto": 0x012CE3BC, "ramora": 0x012CE35C},
    "dc":           {"ramora": 0x012CE35C},
    "target_id":    {"ramora": 0x0115CB20},
    "system_menu":  {"ramora": 0x012DC1F5},
    # Endereco absoluto de heap hardcoded no memory_reader atual.
    # Nao e base estatica; esta aqui so para provar que e lixo.
    "sit_hardcoded": {"loginto": 0x305F08B8},
}


def texto_sensato(v):
    if not isinstance(v, str) or not (1 <= len(v) <= 30):
        return False
    permitido = set(string.ascii_letters + string.digits + " '-_.")
    return all(c in permitido for c in v) and any(c.isalnum() for c in v)


def faixa(lo, hi):
    return lambda v: isinstance(v, (int, float)) and lo <= v <= hi


def booleano(*validos):
    return lambda v: v in validos


# (nome, base, offsets, tipo, sanidade, offsets_ramora)
# offsets_ramora so quando a cadeia -- e nao apenas a base -- difere.
CAMPOS = [
    # ---- char ----
    ("char_name",     "CHAR", [0xBC],   "str",   texto_sensato,           None),
    ("level",         "CHAR", [0x3C4],  "word",  faixa(1, 150),           None),
    ("class_id",      "CHAR", [0x3C8],  "word",  faixa(1, 20),            None),
    ("hp",            "CHAR", [0x3B8],  "int",   faixa(0, 500_000),       None),
    ("max_hp_base",   "CHAR", [0xDC],   "int",   faixa(1, 500_000),       None),
    ("hp_buff",       "CHAR", [0xE0],   "int",   faixa(0, 500_000),       None),
    ("hp_plus",       "CHAR", [0xE4],   "byte",  faixa(0, 255),           None),
    ("mana",          "CHAR", [0x3BC],  "int",   faixa(0, 500_000),       None),
    ("max_mana_base", "CHAR", [0x6EC],  "int",   faixa(1, 500_000),       None),
    ("mana_buff",     "CHAR", [0x6F0],  "int",   faixa(0, 500_000),       None),
    ("stamina",       "CHAR", [0x3DC],  "int",   faixa(0, 500_000),       None),
    ("gold",          "CHAR", [0x410],  "int",   faixa(0, 2_000_000_000), None),
    ("x_raw",         "CHAR", [0x810],  "float", faixa(-200_000, 200_000), None),
    ("y_raw",         "CHAR", [0x814],  "float", faixa(-200_000, 200_000), None),
    ("in_battle",     "CHAR", [0x854],  "byte",  booleano(0, 1),          None),
    ("sit",           "CHAR", [0x290],  "byte",  booleano(0, 200),        None),
    ("mount",         "CHAR", [0x8B0],  "int",   faixa(0, 100_000),       None),
    ("pet_alive",     "CHAR", [0x10A8], "int",   faixa(0, 0x7FFFFFFF),    None),
    ("monk_passive",  "CHAR", [0x3E0],  "int",   faixa(0, 100),           None),
    ("sin_passive",   "CHAR", [0x3E4],  "int",   faixa(0, 100),           None),
    ("location",      "CHAR", [0x7F8, 0xF4, 0x44C], "str", texto_sensato, None),
    ("bag_1",         "CHAR", [0x838, 0xC4, 0x0, 0x8, 0x10], "int", faixa(0, 9999), None),
    ("bag_2",         "CHAR", [0x838, 0xC4, 0x4, 0x8, 0x10], "int", faixa(0, 9999), None),

    # ---- target ----
    ("target_hp",   "TARGET", [0x18, 0x59C, 0x0, 0xC, 0x1F4, 0x15C, 0x480],
     "int", faixa(0, 500_000), None),
    ("target_name", "TARGET", [0x18, 0xB1C, 0x0, 0xC, 0xD9C, 0x9AC],
     "str", texto_sensato, [0x18, 0xB1C, 0x0, 0xC, 0x1F8, 0x43C, 0x9AC]),
    ("bag_open",    "TARGET", [0x18, 0x5C4, 0x0, 0xC, 0x1F8, 0x42C, 0xBA0],
     "int", faixa(0, 0x7FFFFFFF), None),
    ("team_name_1", "TARGET", [0x18, 0x77C, 0x0, 0xC, 0x678, 0x8B4, 0x4F4],
     "str", texto_sensato, None),
    ("team_name_2", "TARGET", [0x18, 0x34C, 0x0, 0xC, 0x678, 0x8B4, 0x4F4],
     "str", texto_sensato, None),
    ("team_name_3", "TARGET", [0x18, 0x3F4, 0x0, 0xC, 0x1F4, 0x15C, 0x54],
     "str", texto_sensato, None),
    ("team_name_4", "TARGET", [0x18, 0xA1C, 0x0, 0xC, 0x1F4, 0x54, 0x54],
     "str", texto_sensato, None),

    # ---- team / dialogo / xp ----
    ("team_size", "TEAM",    [0x3D8], "int", faixa(0, 10), None),
    ("dialogo",   "DIALOGO", [0x70, 0x56C, 0xC, 0x4, 0x42C, 0x1F8, 0x240],
     "int", faixa(0, 0x7FFFFFFF), None),
    ("xp_texto",  "XP", [0xF0, 0x80, 0x28, 0x60, 0x5C, 0x228, 0x3EFC],
     "str", texto_sensato, None),

    # ---- so no ramora ----
    ("target_select", "ENTIDADES", [0xD0, 0x2DC, 0x24, 0xC10], "byte",
     booleano(0, 1), None),
    ("loot",          "ENTIDADES", [0xD0, 0x7F4, 0x0, 0x24, 0x40], "int",
     faixa(0, 0x7FFFFFFF), None),
    ("sur_info",      "SUR",    [0x18, 0x8C, 0x3C, 0x64], "str", texto_sensato, None),
    ("camera_zoom",   "CAMERA", [0x64], "float", faixa(-1000, 1000), None),
    ("camera_rot",    "CAMERA", [0x5C], "float", faixa(-1000, 1000), None),
    ("camera_ang",    "CAMERA", [0x60], "float", faixa(-1000, 1000), None),
]

# Constantes-sentinela usadas pelos dois codigos, impressas junto do
# valor lido para conferencia -- em vez de confiar na memoria de quem le.
SENTINELAS = {
    "sit": "200 = sentado",
    "bag_open": "903 = aberta",
    "dialogo": "16775 = dialogo aberto",
    "system_menu": "1610612736 (0x60000000) = menu aberto",
    "loot_window": "1 = janela de loot aberta",
    "target_hp": "codigo antigo assume 597 como HP cheio -- vale so pra um mob",
}


# =====================================================
# Leitura
# =====================================================

class Processo:
    def __init__(self, pid: int):
        self.pid = pid
        self.h = kernel32.OpenProcess(PROCESS_VM_READ, False, pid)
        if not self.h:
            raise RuntimeError(
                f"OpenProcess falhou para PID={pid} "
                f"(erro {ctypes.get_last_error()}). Rode como administrador."
            )

    def close(self):
        if self.h:
            kernel32.CloseHandle(self.h)
            self.h = None

    def bytes(self, address: int, size: int) -> bytes | None:
        if not (0 < address < 0xFFFFFFFF):
            return None
        buf = ctypes.create_string_buffer(size)
        lidos = ctypes.c_size_t()
        ok = kernel32.ReadProcessMemory(
            wintypes.HANDLE(self.h), wintypes.LPCVOID(address),
            buf, size, ctypes.byref(lidos),
        )
        if not ok or lidos.value == 0:
            return None
        return buf.raw[: lidos.value]

    def inteiro(self, address: int, size: int = 4):
        raw = self.bytes(address, size)
        if raw is None or len(raw) < size:
            return None
        return int.from_bytes(raw[:size], "little")

    def flutuante(self, address: int):
        raw = self.bytes(address, 4)
        if raw is None or len(raw) < 4:
            return None
        return ctypes.c_float.from_buffer_copy(raw[:4]).value

    def texto(self, address: int, max_len: int = 51):
        raw = self.bytes(address, max_len)
        if raw is None:
            return None
        return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")

    def seguir(self, base: int, offsets: list[int]):
        """
        Percorre a cadeia. O ultimo offset NAO e desreferenciado --
        mesma semantica de _follow_chain (LoginTO) e de get_pointer
        (Ramora), que sao equivalentes.
        """
        ptr = self.inteiro(base, 4)
        if not ptr:
            return None
        for off in offsets[:-1]:
            ptr = self.inteiro(ptr + off, 4)
            if not ptr:
                return None
        return ptr + offsets[-1]


def ler_campo(proc: Processo, endereco: int, tipo: str):
    """Retorna (valor, nota). Para str tenta no lugar e desreferenciado."""
    if tipo == "int":
        return proc.inteiro(endereco, 4), ""
    if tipo == "word":
        return proc.inteiro(endereco, 2), ""
    if tipo == "byte":
        return proc.inteiro(endereco, 1), ""
    if tipo == "float":
        return proc.flutuante(endereco), ""
    if tipo == "str":
        direto = proc.texto(endereco)
        if texto_sensato(direto):
            return direto, ""
        ponteiro = proc.inteiro(endereco, 4)
        if ponteiro:
            indireto = proc.texto(ponteiro)
            if texto_sensato(indireto):
                return indireto, "via deref"
        return direto, ""
    raise ValueError(f"tipo desconhecido: {tipo}")


# =====================================================
# Saida
# =====================================================

def cor(txt, sano):
    return f"{GREEN}{txt}{RESET}" if sano else f"{RED}{txt}{RESET}"


def resumo_ponteiro(valor):
    if valor is None:
        return "sem leitura"
    if valor == 0:
        return "0 (base morta)"
    if HEAP_MIN <= valor <= HEAP_MAX:
        return f"0x{valor:08X} (heap plausivel)"
    return f"0x{valor:08X} (lixo)"


def formatar(valor):
    if valor is None:
        return "-"
    if isinstance(valor, float):
        return f"{valor:.2f}"
    return str(valor)


def comparar(proc: Processo, fontes: list[str]):
    placar = {f: {"sanos": 0, "total": 0} for f in fontes}
    bases_lidas = {}

    print(f"\n{BOLD}{'campo':16s} {'fonte':8s} {'endereco':12s} {'valor':26s} nota{RESET}")
    print("-" * 92)

    for nome, chave_base, offsets, tipo, sanidade, offsets_ramora in CAMPOS:
        variantes = BASES[chave_base]
        for fonte in fontes:
            if fonte not in variantes:
                continue
            base = variantes[fonte]
            cadeia = offsets_ramora if (fonte == "ramora" and offsets_ramora) else offsets

            bases_lidas.setdefault((chave_base, fonte), proc.inteiro(base, 4))

            endereco = proc.seguir(base, cadeia)
            placar[fonte]["total"] += 1

            if endereco is None:
                print(f"{nome:16s} {fonte:8s} {'-':12s} "
                      f"{cor('cadeia quebrou', False):35s} "
                      f"{DIM}base {resumo_ponteiro(bases_lidas[(chave_base, fonte)])}{RESET}")
                continue

            valor, nota = ler_campo(proc, endereco, tipo)
            sano = valor is not None and sanidade(valor)
            placar[fonte]["sanos"] += int(sano)

            extra = nota
            if nome in SENTINELAS:
                extra = (extra + "; " if extra else "") + SENTINELAS[nome]

            print(f"{nome:16s} {fonte:8s} 0x{endereco:08X}   "
                  f"{cor(formatar(valor)[:24], sano):35s} {DIM}{extra}{RESET}")

    print(f"\n{BOLD}Estaticos (lidos direto, sem cadeia){RESET}")
    print("-" * 92)
    for nome, variantes in ESTATICOS.items():
        for fonte in fontes:
            if fonte not in variantes:
                continue
            endereco = variantes[fonte]
            valor = proc.inteiro(endereco, 4)
            print(f"{nome:16s} {fonte:8s} 0x{endereco:08X}   "
                  f"{formatar(valor):24s} {DIM}{SENTINELAS.get(nome, '')}{RESET}")

    print(f"\n{BOLD}Bases estaticas{RESET}")
    print("-" * 92)
    for (chave_base, fonte), bruto in sorted(bases_lidas.items()):
        print(f"{chave_base:16s} {fonte:8s} 0x{BASES[chave_base][fonte]:08X}   "
              f"-> {resumo_ponteiro(bruto)}")

    print(f"\n{BOLD}Placar{RESET}")
    print("-" * 92)
    for fonte in fontes:
        p = placar[fonte]
        if not p["total"]:
            continue
        pct = 100.0 * p["sanos"] / p["total"]
        print(f"  {fonte:8s} {p['sanos']:3d}/{p['total']:3d} campos sensatos ({pct:.0f}%)")

    vencedor = max(
        (f for f in fontes if placar[f]["total"]),
        key=lambda f: placar[f]["sanos"],
        default=None,
    )
    if vencedor and placar[vencedor]["sanos"] == 0:
        print(f"\n  {RED}Nenhum conjunto produziu valor sensato.{RESET}")
        print("  Olhe 'Bases estaticas': se todas dao 0 ou lixo, o cliente")
        print("  atualizou e as bases precisam ser reencontradas -- use")
        print("  tools/scan_memory.py (scan de valor + pointer scan).")
        print("  Se as bases sao ponteiros plausiveis, so os offsets mudaram.")
    elif vencedor:
        print(f"\n  Conjunto mais consistente: {GREEN}{vencedor}{RESET}")

    return placar


# =====================================================
# Descoberta do processo
# =====================================================

def caminho_processo(pid: int) -> str:
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return ""
    try:
        import win32process
        return win32process.GetModuleFileNameEx(h, 0)
    except Exception:
        return ""
    finally:
        kernel32.CloseHandle(h)


def executaveis_alvo() -> set[str]:
    """
    Nomes de executavel que podem ser o cliente.

    client_path aponta para um .bat launcher ("start client.exe ..."),
    entao o nome do .bat nunca casa com processo nenhum -- e preciso
    extrair o .exe de dentro dele.
    """
    try:
        import config
        caminho = config.CLIENT_PATH
    except Exception:
        return set()

    nomes = {os.path.basename(caminho).lower()}

    if caminho.lower().endswith(".bat") and os.path.isfile(caminho):
        try:
            with open(caminho, "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read()
        except OSError:
            return nomes
        for token in re.findall(r"[\w.\-]+\.exe", conteudo, re.IGNORECASE):
            nomes.add(os.path.basename(token).lower())

    return nomes


def achar_pid() -> int | None:
    """Acha o cliente pelo nome do executavel -- nao depende de offset."""
    import win32gui
    import win32process

    alvos = executaveis_alvo()
    try:
        import config
        titulo_alvo = (config.WINDOW_TITLE or "").lower()
    except Exception:
        titulo_alvo = ""

    candidatos = {}

    def visitar(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        titulo = win32gui.GetWindowText(hwnd)
        if not titulo.strip():
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        candidatos.setdefault(pid, (titulo, caminho_processo(pid)))
        return True

    win32gui.EnumWindows(visitar, None)

    for pid, (titulo, caminho) in candidatos.items():
        if caminho and os.path.basename(caminho).lower() in alvos:
            print(f"  Cliente: '{titulo}' ({os.path.basename(caminho)}) PID={pid}")
            return pid

    # A janela costuma ser renomeada por conta, entao o titulo e so
    # desempate quando o executavel nao bate.
    if titulo_alvo:
        for pid, (titulo, caminho) in candidatos.items():
            if titulo_alvo in titulo.lower():
                print(f"  Cliente por titulo: '{titulo}' PID={pid}")
                return pid

    print(f"  {YELLOW}Nenhum processo bate com {sorted(alvos) or '?'}.{RESET}")
    print("  Janelas visiveis:")
    for pid, (titulo, caminho) in sorted(candidatos.items()):
        print(f"    PID {pid:6d}  {titulo[:40]:40s}  {os.path.basename(caminho or '?')}")
    print("  Rode de novo com --pid <PID>.")
    return None


# =====================================================
# Autoteste (nao precisa do jogo)
# =====================================================

def autoteste():
    assert texto_sensato("Tomyris")
    assert texto_sensato("Skull Herald")
    assert texto_sensato("Bandit's Cave")
    assert not texto_sensato("")
    assert not texto_sensato("\x01\x02\xff")
    assert not texto_sensato("x" * 40)
    assert not texto_sensato(None)
    assert not texto_sensato("!!!")          # sem alfanumerico

    assert faixa(1, 150)(80)
    assert not faixa(1, 150)(0)
    assert not faixa(1, 150)(151)
    assert not faixa(1, 150)(None)

    assert booleano(0, 200)(200)
    assert not booleano(0, 200)(1)

    assert resumo_ponteiro(0) == "0 (base morta)"
    assert "heap" in resumo_ponteiro(0x0A1B2C3D)
    assert "lixo" in resumo_ponteiro(0xFFFFFFF0)
    assert resumo_ponteiro(None) == "sem leitura"

    # O launcher e um .bat; o processo real e o .exe citado dentro dele.
    alvos = executaveis_alvo()
    assert not alvos or all(a.endswith((".exe", ".bat")) for a in alvos), alvos

    fontes_validas = {"loginto", "ramora"}
    for nome, chave_base, offsets, tipo, sanidade, off_ramora in CAMPOS:
        assert chave_base in BASES, f"{nome}: base {chave_base} nao declarada"
        assert BASES[chave_base], f"{chave_base} sem nenhuma fonte"
        assert set(BASES[chave_base]) <= fontes_validas, f"{chave_base}: fonte invalida"
        assert offsets, f"{nome}: cadeia vazia"
        assert tipo in {"int", "word", "byte", "float", "str"}, f"{nome}: tipo {tipo}"
        assert callable(sanidade), f"{nome}: sanidade nao chamavel"
        if off_ramora:
            assert "ramora" in BASES[chave_base], f"{nome}: cadeia ramora sem base ramora"

    nomes = [c[0] for c in CAMPOS]
    assert len(nomes) == len(set(nomes)), "campo duplicado no catalogo"

    for nome, variantes in ESTATICOS.items():
        assert variantes, f"{nome}: sem endereco"
        assert set(variantes) <= fontes_validas, f"{nome}: fonte invalida"

    # A divergencia de 0x60 e o achado central. Se alguem mexer numa base
    # e esquecer a outra, isto avisa.
    for chave in ("CHAR", "TARGET", "TEAM", "DIALOGO"):
        v = BASES[chave]
        assert v["loginto"] - v["ramora"] == 0x60, \
            f"{chave}: divergencia deixou de ser 0x60"

    print("autoteste ok")


def main():
    ap = argparse.ArgumentParser(description="Compara conjuntos de ponteiros")
    ap.add_argument("--pid", type=int, help="PID do cliente")
    ap.add_argument("--fonte", choices=["loginto", "ramora", "ambas"], default="ambas")
    ap.add_argument("--autoteste", action="store_true", help="valida o catalogo, sem jogo")
    args = ap.parse_args()

    if args.autoteste:
        autoteste()
        return

    print(f"{BOLD}Talisman Online -- comparacao de ponteiros{RESET}\n")

    pid = args.pid or achar_pid()
    if not pid:
        sys.exit(1)

    proc = Processo(pid)
    try:
        fontes = ["loginto", "ramora"] if args.fonte == "ambas" else [args.fonte]
        comparar(proc, fontes)
    finally:
        proc.close()


if __name__ == "__main__":
    main()
