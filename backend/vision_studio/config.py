from __future__ import annotations

import os


def cors_allow_origins() -> list[str]:
    raw = os.environ.get("VISION_STUDIO_CORS_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["*"]
