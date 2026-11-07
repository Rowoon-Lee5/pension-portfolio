"""바탕화면 .env 단일출처에서 API 키 읽기 (프로젝트 내 시크릿 생성 금지)."""
from __future__ import annotations
import os
import re
from pathlib import Path

_ENV_CANDIDATES = [
    Path.home() / "OneDrive" / "바탕 화면" / ".env",
    Path.home() / "Desktop" / ".env",
    Path.home() / "OneDrive" / "Desktop" / ".env",
]


def load(key: str) -> str | None:
    """.env 또는 환경변수에서 key 값. 없으면 None."""
    if os.environ.get(key):
        return os.environ[key]
    for p in _ENV_CANDIDATES:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r'\s*([A-Za-z0-9_]+)\s*=\s*"?([^"\r\n]+)"?', line)
            if m and m.group(1) == key:
                return m.group(2).strip()
    return None
