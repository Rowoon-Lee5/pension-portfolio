"""월 소비자물가 연장 자료 두 가지: (1) OECD Data Explorer(SDMX) (2) BIS 장기 CPI(WS_LONG_CPI, 일본 등 OECD가 2021-06에 멈춘 나라 포함, 2026-07까지)

(1) OECD Data Explorer(SDMX) 월 소비자물가 — FRED CPALTT01(2024-02/03 종료) 이후를 잇기 위한 1차 자료(2026-10-09).

데이터셋 OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0, 국가 19개(현지통화 패널 17 + 호주·뉴질랜드 확인용), 월(M), 측정 CPI.
나머지 차원은 와일드카드로 받고 저장만 함(전 항목·지수 등 선택은 pilot7에서 명시적으로).
저장: raw/macro_fx_vol/oecd_sdmx_cpi_raw_20261009.csv
실행: python -m pension_lab.fetch.oecd_sdmx_cpi
"""
from __future__ import annotations
import io
import requests
import pandas as pd
from .. import paths

AREAS = "AUT+BEL+CAN+DNK+FIN+FRA+DEU+IRL+ITA+JPN+NLD+NOR+ESP+SWE+CHE+GBR+USA+AUS+NZL"
URL = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
       f"{AREAS}.M..CPI....?startPeriod=2015-01&dimensionAtObservation=AllDimensions&format=csvfilewithlabels")
OUT = paths.MACRO / "oecd_sdmx_cpi_raw_20261009.csv"
BIS_AREAS = "AT+BE+CA+DK+FI+FR+DE+IE+IT+JP+NL+NO+ES+SE+CH+GB+US"
BIS_URL = f"https://stats.bis.org/api/v1/data/WS_LONG_CPI/M.{BIS_AREAS}.628/all?format=csv&startPeriod=2015-01"   # 628 = 지수(2010=100)
BIS_OUT = paths.MACRO / "bis_long_cpi_monthly_20261009.csv"


def run_bis() -> pd.DataFrame:
    r = requests.get(BIS_URL, timeout=120); r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d.to_csv(BIS_OUT, index=False, encoding="utf-8-sig")
    return d


def run() -> pd.DataFrame:
    r = requests.get(URL, timeout=120, headers={"Accept": "application/vnd.sdmx.data+csv; charset=utf-8"})
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d.to_csv(OUT, index=False, encoding="utf-8-sig")
    return d


if __name__ == "__main__":
    import sys
    d = run_bis() if sys.argv[1:] == ["bis"] else run(); print(d.shape); print(d.columns.tolist())
