"""開発用エントリ: `kronos-py/backend` で `python app.py` を実行して API を起動する。

`src` を import パスに追加するため、事前に `PYTHONPATH=src` を付けなくてよい。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent
_SRC = _BACKEND_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> None:
    import uvicorn

    host = os.environ.get("KRONOS_HOST", "127.0.0.1")
    port = int(os.environ.get("KRONOS_PORT", "8000"))
    reload = os.environ.get("KRONOS_RELOAD", "1").lower() not in ("0", "false", "no")

    uvicorn.run(
        "kronos_py.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
