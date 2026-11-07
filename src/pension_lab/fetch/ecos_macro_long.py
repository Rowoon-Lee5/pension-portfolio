"""한국은행 ECOS 장기 거시 — 원/달러(IMF기 1990~)·국고채 만기별·CD·CPI·기준금리.
실행: python -m pension_lab.fetch.ecos_macro_long  (백그라운드)
⚠ECOS 통계표/항목 코드는 개정될 수 있음 → 각 시리즈 성공/실패를 로그. 실패는 코드 재확인 대상(단정 금지).
"""
from __future__ import annotations
import warnings
import requests
import pandas as pd
from .. import paths
from ._env import load as env
warnings.filterwarnings("ignore")


def _ecos(stat: str, cycle: str, start: str, end: str, item: str) -> pd.Series:
    key = env("ECOS_API_KEY")
    if not key:
        raise RuntimeError("ECOS_API_KEY 없음(.env)")
    u = f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/100000/{stat}/{cycle}/{start}/{end}/{item}"
    js = requests.get(u, timeout=90).json()
    if "StatisticSearch" not in js:
        raise RuntimeError(str(js)[:120])          # 에러메시지(코드오류 등) 노출
    rows = js["StatisticSearch"]["row"]
    s = pd.Series({r["TIME"]: float(r["DATA_VALUE"]) for r in rows if r["DATA_VALUE"] not in ("", "-")})
    s.index = pd.to_datetime(s.index, format="%Y%m%d" if cycle == "D" else "%Y%m")
    return s.sort_index()


# (파일명, 통계표, 주기, 시작, 항목코드) — IMF기 포함 최장. 코드 실패시 로그.
JOBS = [
    ("ecos_usdkrw_long",   "731Y001", "D", "19900101", "0000001", paths.MACRO),      # 원/달러 매매기준율
    ("ecos_ktb3y_long",    "817Y002", "D", "19950101", "010200000", paths.BOND_KR),  # 국고채(3년)
    ("ecos_ktb5y_long",    "817Y002", "D", "20000101", "010200001", paths.BOND_KR),  # 국고채(5년)
    ("ecos_ktb10y_long",   "817Y002", "D", "20000101", "010210000", paths.BOND_KR),  # 국고채(10년)
    ("ecos_cd91_long",     "817Y002", "D", "19910101", "010502000", paths.BOND_KR),  # CD(91일)
    ("ecos_call_long",     "817Y002", "D", "19900101", "010101000", paths.BOND_KR),  # 콜금리(익일)
    ("ecos_cpi_long",      "901Y009", "M", "199001",   "0",         paths.MACRO),    # 소비자물가 총지수
    ("ecos_baserate_long", "722Y001", "D", "19990101", "0101000",   paths.BOND_KR),  # 한국은행 기준금리
]


# 주기별 종료일자 형식 (ERROR-101 방지: 월간은 6자리, 일간은 8자리)
_END = {"D": "20261231", "M": "202612", "Q": "2026Q4", "A": "2026"}


def run() -> None:
    ok, fail = [], []
    for name, stat, cyc, start, item, out in JOBS:
        out.mkdir(parents=True, exist_ok=True)
        try:
            s = _ecos(stat, cyc, start, _END[cyc], item)
            s.index.name = "date"
            s.rename(name).to_csv(out / f"{name}.csv", encoding="utf-8-sig")
            ok.append(f"{name}: {len(s)}행 {str(s.index.min())[:7]}~{str(s.index.max())[:7]}")
        except Exception as e:
            fail.append(f"{name}: 실패 [{stat}/{item}] {str(e)[:80]}")
    print("=== ECOS 장기거시 취득 ===")
    for x in ok: print("[ok]", x)
    for x in fail: print("[FAIL]", x)


if __name__ == "__main__":
    run()
