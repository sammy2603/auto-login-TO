from __future__ import annotations

import sys

from src.app.application import Application


def main() -> int:
    app = Application()

    try:
        app.start()
        return 0

    except KeyboardInterrupt:
        print("\nAplicação interrompida pelo usuário.")
        return 1

    except Exception as exc:
        print(f"\nErro durante a execução: {exc}")
        return 1

    finally:
        app.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())