"""데이터 경로 한 곳 정의. 하드코딩 금지 — 여기만 고치면 전체 반영.

루트: 환경변수 PENSION_DATA_ROOT (없으면 이 저장소의 data/ — 공개 원자료만 있음, DATA_SOURCES.md)
raw/ 는 원자료(불변), processed/ 는 파생, dataguide/ 는 FnGuide 추출본.
"""
from __future__ import annotations
import os
from pathlib import Path

DATA_ROOT = Path(os.environ.get("PENSION_DATA_ROOT", Path(__file__).resolve().parents[2] / "data"))
RAW = DATA_ROOT / "raw"
PROCESSED = DATA_ROOT / "processed"
DATAGUIDE = DATA_ROOT / "dataguide"
RESULTS = DATA_ROOT / "results"

# raw 하위 자산군 폴더
EQUITY_KR = RAW / "equity_kr"
EQUITY_GLOBAL = RAW / "equity_global"
BOND_KR = RAW / "bond_kr"
BOND_INDEX = RAW / "bond_index"
BOND_GLOBAL = RAW / "bond_global"
REAL_ESTATE = RAW / "real_estate"
COMMODITY = RAW / "commodity"
MACRO = RAW / "macro_fx_vol"
FUND_TDF = RAW / "fund_tdf"


def ensure_dirs() -> None:
    for p in (PROCESSED, RESULTS):
        p.mkdir(parents=True, exist_ok=True)


def exists() -> bool:
    """데이터 루트가 실제로 있는지 (테스트 skip 판단용)."""
    return DATA_ROOT.exists()
