from __future__ import annotations

import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent
deps = backend / ".deps"
sys.path.insert(0, str(deps))
sys.path.insert(0, str(backend))

import uvicorn


if __name__ == "__main__":
    try:
        reload = "--reload" in sys.argv
        host = os.environ.get("VISION_STUDIO_HOST", "127.0.0.1")
        port = int(os.environ.get("VISION_STUDIO_PORT", "8000"))
        uvicorn.run("vision_studio.main:app", host=host, port=port, reload=reload, reload_dirs=[str(backend)] if reload else None)
    except Exception as exc:
        (backend / "serve.err.log").write_text(repr(exc), encoding="utf-8")
        raise
