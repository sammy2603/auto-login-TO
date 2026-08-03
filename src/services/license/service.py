from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

LICENSE_FILE = Path(__file__).resolve().parents[3] / "license.json"

# Chave secreta usada para assinar as licenças (em produção,
# use uma chave forte e não a inclua no código público).
_SECRET = "LoginTO-2026-secret-key"


@dataclass
class LicenseInfo:
    key: str = ""
    status: str = "demo"  # demo, active, expired
    days_remaining: int = 0
    tier: str = "free"  # free, premium
    issued_at: float = 0.0
    expires_at: float = 0.0
    validated: bool = False


class LicenseService:
    """
    Serviço de licenciamento.

    - Chaves demo são aceitas sem validação (30 dias a partir do
      primeiro uso).
    - Chaves premium são validadas por hash com prazo embutido.
    - Estado persistido em license.json.
    """

    DEMO_DAYS = 30

    def __init__(self):
        self._info = LicenseInfo()
        self._load()

    # =====================================================
    # API pública
    # =====================================================

    @property
    def info(self) -> LicenseInfo:
        return self._info

    @property
    def is_active(self) -> bool:
        return self._info.status in ("demo", "active")

    @property
    def days_remaining(self) -> int:
        return max(0, self._info.days_remaining)

    def activate(self, key: str) -> tuple[bool, str]:
        """
        Tenta ativar uma chave. Retorna (sucesso, mensagem).
        """

        key = key.strip().upper()

        if not key:
            return False, "Chave vazia."

        if key == "DEMO":
            return self._activate_demo()

        return self._validate_premium_key(key)

    def check(self):
        """
        Verifica se a licença ainda é válida.
        Deve ser chamado na inicialização e periodicamente.
        """

        if self._info.status == "demo":
            elapsed = time.time() - self._info.issued_at
            remaining = self.DEMO_DAYS - int(elapsed / 86400)
            self._info.days_remaining = max(0, remaining)
            if remaining <= 0:
                self._info.status = "expired"

        elif self._info.status == "active":
            remaining = int((self._info.expires_at - time.time()) / 86400)
            self._info.days_remaining = max(0, remaining)
            if remaining <= 0:
                self._info.status = "expired"

        self._save()

    def days_left(self) -> int:
        self.check()
        return self.days_remaining

    # =====================================================
    # Ativação
    # =====================================================

    def _activate_demo(self) -> tuple[bool, str]:
        now = time.time()
        self._info = LicenseInfo(
            key="DEMO",
            status="demo",
            days_remaining=self.DEMO_DAYS,
            tier="free",
            issued_at=now,
            expires_at=now + self.DEMO_DAYS * 86400,
            validated=True,
        )
        self._save()
        return True, f"Modo demo ativado ({self.DEMO_DAYS} dias)."

    def _validate_premium_key(self, key: str) -> tuple[bool, str]:
        """
        Valida uma chave premium.

        Formato esperado: TO-YYYYMMDD-HASH
        Onde HASH = SHA256(YYYYMMDD + _SECRET)[:8]
        """

        parts = key.split("-")
        if len(parts) != 3 or parts[0] != "TO":
            return False, "Formato de chave invalido."

        date_str = parts[1]
        provided_hash = parts[2]

        if len(date_str) != 8 or not date_str.isdigit():
            return False, "Data invalida na chave."

        expected = hashlib.sha256(
            (date_str + _SECRET).encode()
        ).hexdigest()[:8].upper()

        if provided_hash.upper() != expected:
            return False, "Chave invalida."

        # Converte a data de expiração
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            import datetime
            exp_date = datetime.datetime(year, month, day)
            expires_at = exp_date.timestamp()
        except ValueError:
            return False, "Data de expiracao invalida."

        if time.time() > expires_at:
            return False, "Chave expirada."

        now = time.time()
        remaining = int((expires_at - now) / 86400)

        self._info = LicenseInfo(
            key=key,
            status="active",
            days_remaining=remaining,
            tier="premium",
            issued_at=now,
            expires_at=expires_at,
            validated=True,
        )
        self._save()

        return True, f"Licenca premium ativada ({remaining} dias restantes)."

    # =====================================================
    # Persistência
    # =====================================================

    def _load(self):
        if not LICENSE_FILE.exists():
            return

        try:
            data = json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
            self._info = LicenseInfo(
                key=data.get("key", ""),
                status=data.get("status", "demo"),
                days_remaining=data.get("days_remaining", 0),
                tier=data.get("tier", "free"),
                issued_at=data.get("issued_at", 0.0),
                expires_at=data.get("expires_at", 0.0),
                validated=data.get("validated", False),
            )
        except Exception:
            pass

    def _save(self):
        try:
            LICENSE_FILE.write_text(
                json.dumps(
                    {
                        "key": self._info.key,
                        "status": self._info.status,
                        "days_remaining": self._info.days_remaining,
                        "tier": self._info.tier,
                        "issued_at": self._info.issued_at,
                        "expires_at": self._info.expires_at,
                        "validated": self._info.validated,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            logger.warning("Nao foi possivel salvar a licenca", exc_info=True)
