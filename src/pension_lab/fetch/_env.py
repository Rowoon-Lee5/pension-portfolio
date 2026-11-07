"""API 키는 환경변수에서만 읽는다(저장소 안에 시크릿을 두지 않음)."""
from __future__ import annotations
import os


def load(key: str) -> str | None:
    """환경변수 key 값. 없으면 None."""
    return os.environ.get(key) or None
