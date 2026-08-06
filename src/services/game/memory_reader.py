from __future__ import annotations

import ctypes
import re
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


def _wpm_float(hProcess: int, address: int, valor: float) -> bool:
    """Escreve 4 bytes como float. Devolve False se a escrita falhou."""
    buf = ctypes.c_float(valor)
    escritos = ctypes.c_size_t()
    return bool(
        kernel32.WriteProcessMemory(
            wintypes.HANDLE(hProcess),
            wintypes.LPVOID(address),
            ctypes.byref(buf),
            4,
            ctypes.byref(escritos),
        )
    )


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

    # Ponteiros base. Catalogo completo, divergencias entre versoes e
    # procedimento apos atualizacao do cliente:
    # .project/context/PONTEIROS.md
    #
    # Removidos por estarem mortos no cliente ver.6400 (nenhum
    # consumidor no app; comprovado por tools/comparar_ponteiros.py):
    #   XP_BASE  0x01139700  -> le 0, cadeia de xp_pct nunca resolve
    #   notification  0x0117097C -> le um ponteiro, nunca 1
    CHAR_BASE = 0x0114514C
    TARGET_BASE = 0x012CE340
    SPLIT_BASE = 0x012CE340
    TEAM_SIZE_BASE = 0x0106D388
    ENTIDADES_BASE = 0x012C0628
    # Aponta direto para a ENTIDADE do alvo. Substitui as cadeias de UI
    # (TARGET_BASE), que resolviam num cliente e quebravam noutro
    # conforme o arranjo dos paineis -- ver PONTEIROS.md.
    ALVO_BASE = 0x0107D410
    MISSOES_BASE = 0x0150C314
    # Camera: tres floats no mesmo objeto (ver PONTEIROS.md). E a UNICA
    # escrita que este leitor faz, e e local: o servidor nao valida
    # angulo de camera. Escrever aqui substitui o botao de view reset,
    # que so devolve o angulo padrao e nao mexe no zoom -- e o zoom e
    # justamente o que muda de client para client neste servidor, onde
    # os clients tem o limite de zoom liberado.
    CAMERA_BASE = 0x01170054
    CAMERA_ROTACAO = 0x5C
    CAMERA_ANGULO = 0x60
    CAMERA_ZOOM = 0x64
    # Zoom ALVO da interpolacao. Confirmado com tools/camera_probe.py em
    # 2026-08-06: rolando o zoom, +0x64 vai ate 818.89 e +0x68 ate
    # 824.00 -- o atual perseguindo o alvo. Escrever so o atual nao
    # segura; o alvo puxa de volta assim que o cliente atualiza a
    # camera. Os dois juntos e o que fixa.
    CAMERA_ZOOM_TARGET = 0x68
    # Painel Surrounding de verdade -- lista TODOS os NPCs do mapa. Este
    # Painel Surrounding: NAO tem cadeia estatica confiavel. As tres
    # que o pointer scan reverso deu (0x004AB3B8, 0x0090F17C,
    # 0x00F04948) resolviam para o buffer de UMA renderizacao e
    # apontavam para lixo assim que o painel era fechado e reaberto.
    # A fonte e npcs_ao_redor(), que varre a memoria pelo marcador.

    def __init__(self, pid: int):
        self._pid = pid
        self._hProcess: int | None = None
        self._open()

    def _open(self):
        """Abre o processo com acesso de leitura e escrita.

        QUERY_INFORMATION alem de VM_READ porque npcs_ao_redor() precisa
        de VirtualQueryEx para saber quais regioes existem.

        VM_WRITE/VM_OPERATION existem por causa de escrever_camera(), a
        unica escrita daqui. Nao vale para posicao: coordenada e
        validada no servidor, camera nao.
        """
        self._hProcess = kernel32.OpenProcess(
            win32con.PROCESS_VM_READ
            | win32con.PROCESS_QUERY_INFORMATION
            | win32con.PROCESS_VM_WRITE
            | win32con.PROCESS_VM_OPERATION,
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
        val = _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x6EC), 4)
        val += _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x6F0), 4)
        return val

    @property
    def mana_pct(self) -> float:
        max_val = self.max_mana
        if max_val == 0:
            return 0.0
        return (self.mana / max_val) * 100.0

    @property
    def stamina(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x3DC), 4)

    @property
    def max_stamina(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x3F0), 4)

    @property
    def stamina_pct(self) -> float:
        max_val = self.max_stamina
        if max_val == 0:
            return 0.0
        return (self.stamina / max_val) * 100.0

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

    # Tabela do ver.6400, conferida com uma personagem de cada classe. A
    # antiga (10 Monk, 4 Wizard, 2 Assassin, 3 Tamer, 5 Fairy, em +0x3C8)
    # morreu junto com o offset.
    CLASS_NAMES = {0: "Wizard", 1: "Monk", 2: "Assassin", 3: "Fairy", 4: "Tamer"}

    @property
    def class_id(self) -> int:
        """Retorna o ID da classe (BYTE em +0xD4).

        O byte seguinte (+0xD5) e o genero: 1 = feminino. A classe nao
        muda com o genero -- Wizard male e female leem 0 nos dois.
        """
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0xD4), 1)

    @property
    def profession(self) -> str:
        """Retorna o nome da profissao/classe."""
        cid = self.class_id
        return self.CLASS_NAMES.get(cid, f"Class_{cid}")

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
        """Passiva do Monk."""
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x3E0), 4)

    @property
    def sin_combo(self) -> int:
        """Passiva do Assassin (vizinha da do Monk)."""
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x3E4), 4)

    @property
    def gold(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x410), 4)

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

    def _entidade_alvo(self) -> int:
        """
        Endereco da ENTIDADE do alvo, ou 0.

        Entidade e personagem sao a MESMA struct: nome em +0xBC, HP em
        +0x3B8, level em +0x3C4, x/y em +0x810/+0x814 -- exatamente os
        offsets do CHAR. Foi assim que ela foi achada: procurando o nome
        do alvo na memoria e exigindo que +0x810 dividido por 20 batesse
        com a coordenada que o jogo mostrava.

        ATENCAO -- guarda o ULTIMO alvo, nao o atual: depois do Esc o
        ponteiro continua apontando para a mesma entidade. Ponteiro zero
        prova "nunca teve alvo"; ponteiro cheio nao prova "tem alvo
        agora".
        """
        return _rpm_int(self._hProcess, self.ALVO_BASE, 4)

    @property
    def target_selected(self) -> bool:
        """
        Se ha alvo -- na medida do que da para saber hoje.

        O booleano `ENTIDADES + [0xD0, 0x2DC, 0x24, 0xC10]`, herdado do
        RamoraBOT, NAO serve: le 1 em cliente sem alvo nenhum. O objeto
        no fim daquela cadeia e o marcador de selecao do chao
        (eff_cursorground02), nao o alvo.

        # ponytail: so distingue "nunca teve alvo" de "ja teve". Para
        # separar "ainda tem" de "tirou com Esc" falta achar o campo de
        # selecao atual.
        """
        return self._entidade_alvo() != 0

    @property
    def target_hp(self) -> int:
        alvo = self._entidade_alvo()
        return _rpm_int(self._hProcess, alvo + 0x3B8, 4) if alvo else 0

    @property
    def target_hp_pct(self) -> float:
        # Nao existe ponteiro conhecido para o HP maximo do alvo. O
        # divisor 597 herdado do SSCBot era o HP de um mob especifico
        # (confirmado: Little Wild Boar), entao mentia para todo o
        # resto. Os consumidores (attack.py, step_runner) so testam
        # <= 0, ou seja, vivo ou morto.
        # ponytail: vivo = 100%; se algum dia precisarmos da barra real,
        # e preciso achar o offset do HP maximo do alvo.
        return 100.0 if self.target_hp > 0 else 0.0

    @property
    def target_name(self) -> str:
        alvo = self._entidade_alvo()
        return _rpm_string(self._hProcess, alvo + 0xBC, 30) if alvo else ""

    @property
    def target_level(self) -> int:
        alvo = self._entidade_alvo()
        return _rpm_int(self._hProcess, alvo + 0x3C4, 2) if alvo else 0

    @property
    def target_x(self) -> int:
        """Coordenada X do alvo -- o que o search_id() do RamoraBOT
        tentava obter varrendo dezenas de milhoes de enderecos."""
        alvo = self._entidade_alvo()
        return int(_rpm_float(self._hProcess, alvo + 0x810) / 20.0) if alvo else 0

    @property
    def target_y(self) -> int:
        alvo = self._entidade_alvo()
        return int(_rpm_float(self._hProcess, alvo + 0x814) / 20.0) if alvo else 0

    @property
    def target_dead(self) -> bool:
        return self.target_hp == 0

    # =====================================================
    # Outros
    # =====================================================

    # O painel Surrounding e renderizado como um UiRichText; cada linha
    # sai como text="Nome [x,y] (d m)".
    _OBJETIVO = re.compile(
        r'text="([^"]+?)\s*\[(-?\d+),(-?\d+)\]\s*\((\d+) m\)"'
    )

    @staticmethod
    def parse_objetivos(texto: str) -> list[tuple[str, int, int, int]]:
        """
        Extrai (nome, x, y, distancia) do XML do rastreador de missoes.

        Separado da leitura de memoria de proposito: e a unica parte
        testavel sem o jogo aberto, e e onde mora o risco de regressao.

        O buffer repete a mesma entrada a cada passada de renderizacao,
        entao a saida vem deduplicada, preservando a ordem original.
        """
        vistos = set()
        saida = []
        for nome, x, y, dist in MemoryReader._OBJETIVO.findall(texto or ""):
            item = (nome.strip(), int(x), int(y), int(dist))
            if item not in vistos:
                vistos.add(item)
                saida.append(item)
        return saida

    def objetivos_de_missao(self, max_bytes: int = 16384) -> list[tuple[str, int, int, int]]:
        """
        NPCs-objetivo das missoes ativas: (nome, x, y, distancia).

        ATENCAO -- isto NAO e o painel Surrounding, apesar de ter sido
        rotulado assim quando foi descoberto. E o rastreador de missoes:
        o buffer vem agrupado por mapa, cada quest com o NPC que ela
        manda procurar, e cada linha carrega um hlink 'task:locate'.

        Duas consequencias medidas no ver.6400:

        - So aparece NPC ligado a uma missao ATIVA do personagem. NPC
          qualquer (uma Skull Herald, por exemplo) nunca vai estar aqui.
        - A distancia e do ultimo render, nao do instante da leitura:
          andando 115 unidades, os metros nao mudaram. A coordenada do
          NPC nao sofre com isso, que e fixa; a distancia sim.
        """
        addr = self._follow_chain(self.MISSOES_BASE, [0xA0, 0xA0])
        if not addr:
            return []

        buf = ctypes.create_string_buffer(max_bytes)
        lidos = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(
            wintypes.HANDLE(self._hProcess), wintypes.LPCVOID(addr),
            buf, max_bytes, ctypes.byref(lidos),
        ):
            return []

        texto = buf.raw[: lidos.value].split(b"\x00", 1)[0].decode("utf-8", "replace")
        return self.parse_objetivos(texto)

    # Painel Surrounding: mesma marcacao do rastreador de missoes, mas
    # sem a distancia em metros -- sai so text="Nome [x,y]".
    _NPC_SUR = re.compile(r'text="([^"\[]+?)\s*\[(-?\d+),(-?\d+)\]"')

    @staticmethod
    def parse_npcs(texto: str) -> list[tuple[str, int, int]]:
        """
        Extrai (nome, x, y) do XML do painel Surrounding.

        Deduplicado preservando a ordem: o buffer repete a mesma entrada
        a cada passada de renderizacao.
        """
        vistos = set()
        saida = []
        for nome, x, y in MemoryReader._NPC_SUR.findall(texto or ""):
            item = (nome.strip(), int(x), int(y))
            if item not in vistos:
                vistos.add(item)
                saida.append(item)
        return saida

    # Marcador do bloco: toda linha do painel carrega este hlink. E o
    # que separa a lista dos objetos de definicao de NPC, que tambem
    # tem o nome mas nenhuma coordenada.
    _MARCADOR_SUR = b"String:task:locate?px="

    def _regioes(self):
        """Regioes de memoria commitadas e legiveis do processo."""
        class _MBI(ctypes.Structure):
            _fields_ = [
                ("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD),
            ]

        LEGIVEL = (0x02, 0x04, 0x08, 0x20, 0x40, 0x80)
        mbi = _MBI()
        lidos = ctypes.c_size_t()
        endereco = 0
        while endereco < 0x7FFF0000:
            if not kernel32.VirtualQueryEx(
                wintypes.HANDLE(self._hProcess), wintypes.LPCVOID(endereco),
                ctypes.byref(mbi), ctypes.sizeof(mbi),
            ):
                return
            base = mbi.BaseAddress or 0
            tam = mbi.RegionSize
            if mbi.State == 0x1000 and mbi.Protect in LEGIVEL:
                buf = ctypes.create_string_buffer(tam)
                if kernel32.ReadProcessMemory(
                    wintypes.HANDLE(self._hProcess), wintypes.LPCVOID(base),
                    buf, tam, ctypes.byref(lidos),
                ):
                    yield buf.raw[: lidos.value]
            endereco = base + tam

    def npcs_ao_redor(self, minimo: int = 5) -> list[tuple[str, int, int]]:
        """
        Todos os NPCs do mapa atual: (nome, x, y).

        Esta e a fonte para coordenada de NPC QUALQUER -- inclusive os
        que nao tem nada a ver com missao, como a Skull Herald da
        entrada da BC. Nao confundir com objetivos_de_missao(), que le
        outro buffer e so conhece NPC de quest ativa.

        Exige que o painel Surrounding tenha sido ABERTO pelo menos uma
        vez neste mapa. Lista vazia quase sempre quer dizer "o painel
        nunca foi aberto", nao "nao ha NPC".

        ARMADILHA: fechar o painel NAO limpa o bloco -- medido, 33
        entradas continuam sendo achadas com ele fechado. Quem troca de
        mapa sem reabrir o painel recebe a lista do mapa ANTERIOR, com
        cara de valida. Abra o painel no mapa em que voce quer ler.

        Por VARREDURA, e nao por cadeia de ponteiros, de proposito: o
        pointer scan reverso achou tres estaticos que resolviam para o
        buffer de uma renderizacao especifica e passavam a apontar para
        lixo assim que o painel era fechado e reaberto. O marcador nao
        tem esse problema -- acha o bloco onde ele estiver.

        # ponytail: varredura O(memoria do processo), ~1 s. Chamada
        # one-shot para anotar coordenada, nao serve para laco de bot.
        """
        melhor: list[tuple[str, int, int]] = []
        for dados in self._regioes():
            inicio = dados.find(self._MARCADOR_SUR)
            while inicio >= 0:
                ini = dados.rfind(b"\x00", 0, inicio) + 1
                fim = dados.find(b"\x00", inicio)
                bloco = dados[ini:fim if fim >= 0 else len(dados)]
                entradas = self.parse_npcs(bloco.decode("utf-8", "replace"))
                # O bloco mais completo e o render mais recente; os
                # antigos sobrevivem na heap com listas menores.
                if len(entradas) > len(melhor):
                    melhor = entradas
                inicio = dados.find(self._MARCADOR_SUR, max(fim, inicio + 1))
        return melhor if len(melhor) >= minimo else []

    @property
    def team_size(self) -> int:
        return _rpm_int(self._hProcess, self._read_ptr(self.TEAM_SIZE_BASE, 0x3D8), 4)

    @property
    def is_sitting(self) -> bool:
        # O endereco antigo (0x305F08B8) era heap hardcoded e lia sempre
        # 0. CHAR+0x290 vem do RamoraBOT: 100 em pe, 200 sentado,
        # conferido no cliente ver.6400.
        return _rpm_int(self._hProcess, self._read_ptr(self.CHAR_BASE, 0x290), 1) == 200

    @property
    def is_channeling(self) -> bool:
        return _rpm_int(
            self._hProcess,
            self._read_ptr(self.CLIENT_BASE + 0x00D3537C, 0x10),
            4,
        ) == 24

    @property
    def confirm_box(self) -> bool:
        return _rpm_int(self._hProcess, 0x012CE3BC, 4) == 1

    @property
    def dialog_open(self) -> bool:
        chain = [0x0117B2DC, 0x70, 0x56C, 0xC, 0x4, 0x42C, 0x1F8, 0x240]
        addr = self._follow_chain(chain[0], chain[1:])
        return _rpm_int(self._hProcess, addr, 4) == 16775 if addr else False

    @property
    def bag_open(self) -> bool:
        chain = [self.SPLIT_BASE, 0x18, 0x5C4, 0x0, 0xC, 0x1F8, 0x42C, 0xBA0]
        addr = self._follow_chain(chain[0], chain[1:])
        return _rpm_int(self._hProcess, addr, 4) == 903 if addr else False

    @property
    def loot_window(self) -> bool:
        return _rpm_int(self._hProcess, 0x0105B9B8, 4) == 1

    # =====================================================
    # Camera
    # =====================================================

    @property
    def camera(self) -> tuple[float, float, float]:
        """(zoom, rotacao, angulo) -- 0.0 nos tres se a base nao resolver."""
        base = _rpm_int(self._hProcess, self.CAMERA_BASE, 4)
        if base == 0:
            return (0.0, 0.0, 0.0)
        return (
            _rpm_float(self._hProcess, base + self.CAMERA_ZOOM),
            _rpm_float(self._hProcess, base + self.CAMERA_ROTACAO),
            _rpm_float(self._hProcess, base + self.CAMERA_ANGULO),
        )

    def escrever_camera(self, zoom: float, rotacao: float,
                        angulo: float) -> bool:
        """
        Fixa a camera escrevendo os tres floats.

        Existe porque clique de CHAO e clique em NPC sao coordenadas de
        TELA: onde o NPC aparece depende de zoom, rotacao e angulo. O
        botao de view reset do jogo devolve o angulo padrao mas NAO
        devolve o zoom, e os clients usados aqui tem o limite de zoom
        liberado -- ou seja, dois clients no "mesmo" reset mostram o NPC
        em pixels diferentes. Escrever os tres torna o ponto de tela
        reproduzivel.

        Devolve False se a base nao resolveu ou se alguma escrita
        falhou; quem chama decide se isso e fatal (aqui nao e -- o
        roteiro segue e falha visivelmente adiante).
        """
        base = _rpm_int(self._hProcess, self.CAMERA_BASE, 4)
        if base == 0:
            return False
        return all([
            _wpm_float(self._hProcess, base + self.CAMERA_ZOOM, zoom),
            _wpm_float(self._hProcess, base + self.CAMERA_ZOOM_TARGET, zoom),
            _wpm_float(self._hProcess, base + self.CAMERA_ROTACAO, rotacao),
            _wpm_float(self._hProcess, base + self.CAMERA_ANGULO, angulo),
        ])