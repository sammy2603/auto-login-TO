from __future__ import annotations

from src.app.application import Application
from src.infrastructure.logging import LoggingService, get_logger

logger = get_logger(__name__)


def main() -> int:
    LoggingService.setup()

    app = Application()

    try:
        app.start()
        return 0

    except KeyboardInterrupt:
        logger.warning("Aplicação interrompida pelo usuário.")
        return 1

    except Exception:
        logger.exception("Erro durante a execução")
        return 1

    finally:
        app.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
