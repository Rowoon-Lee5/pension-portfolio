"""데이터 로더 — 노트북마다 재작성하지 말고 여기 import해서 쓸 것.

- load_csv        : date 인덱스 CSV 시계열
- load_dg_series  : FnGuide DataGuide xlsx (14줄 머리말 블록) 에서 계정명 키워드로 컬럼 선택
- asset_series    : 자산군 축약 이름 -> 시계열 (연구 표준 자산묶음)
"""
from __future__ import annotations
import datetime
from pathlib import Path
import pandas as pd
from . import paths

_DATECOLS = {"date", "time", "날짜", "일자"}


def load_csv(path: str | Path, col: str | None = None) -> pd.Series:
    """date 인덱스 + 값 1컬럼 시계열. col 미지정시 가격/값 컬럼 자동선택.

    날짜 컬럼이 이름없는 첫 컬럼(예: FDR 저장본 `,sp500`)이면 첫 컬럼을 날짜로 사용.
    """
    df = pd.read_csv(path)
    dc = next((c for c in df.columns if str(c).lower() in _DATECOLS), df.columns[0])
    df[dc] = pd.to_datetime(df[dc])
    if col and col in df.columns:
        vc = col
    else:
        cand = [c for c in df.columns
                if c != dc and str(c).lower() not in _DATECOLS | {"open", "high", "low", "volume"}]
        vc = cand[0]
    return df.set_index(dc)[vc].sort_index().rename(Path(path).stem)


def load_dg_series(path: str | Path, name_kw: str) -> pd.Series:
    """DataGuide xlsx: 머리말 블록에서 계정명에 name_kw 든 컬럼의 일별 시계열.

    DataGuide 포맷은 상단 ~14줄이 머리말(코드/계정명/주기), 이후 1열=날짜.
    """
    raw = pd.read_excel(path, header=None)
    dstart = next(i for i in range(len(raw))
                  if isinstance(raw.iloc[i, 0], (pd.Timestamp, datetime.datetime)))
    hdr = raw.iloc[:dstart]
    col = next((c for c in range(1, raw.shape[1])
                if name_kw in " ".join(str(x) for x in hdr[c].tolist())), 1)
    d = raw.iloc[dstart:, [0, col]].copy()
    d.columns = ["date", "v"]
    d["date"] = pd.to_datetime(d["date"])
    d["v"] = pd.to_numeric(d["v"], errors="coerce")
    return d.dropna().set_index("date")["v"].sort_index().rename(name_kw)


# 연구 표준 자산묶음 — 축약이름 -> (로더, 인자)
def asset_series(name: str) -> pd.Series:
    """자산군 축약이름으로 총수익(TR) 시계열 반환.

    kr_eq  국내주식(KODEX200 수정주가) / us_eq 미국주식(SPY TR)
    kr_bd  국고채 총수익 / us_bd_mid 미국채7-10y / us_agg 미국종합채권
    gold 금 / usdkrw 환율 / vkospi 변동성 / cpi 물가 ...

    ⭐무료 장기시리즈(FDR·ECOS, IMF/닷컴 포함):
    us_eq_long S&P500 가격지수(1984~) / us_nasdaq_long 나스닥(1984~) / jp_eq 닛케이225(1985~)
    eafe 선진국ex-US(EFA 2001~) / usdkrw 원달러(ECOS 1990~·IMF 포함) / jpykrw 엔원(2003~)
    ktb3y·ktb5y·ktb10y 국고채 만기별 금리 / cd91·call·baserate 단기금리 / cpi 소비자물가(1990~)
    ※ us_eq_long 등 해외지수는 '가격'(배당제외); 총수익은 us_eq(SPY TR 2000~) 사용.
    ※ usdkrw는 IMF기(1997) 포함 장기본(ecos_usdkrw_long)으로 통일 — 구 ecos_usdkrw(2000~)와 중복구간 값 동일(diff 0).
    """
    P = paths
    table = {
        "kr_eq":     lambda: load_dg_series(P.DATAGUIDE / "kodex200_adj.xlsx", "수정주가"),
        "kr_eq_tr":  lambda: load_dg_series(P.DATAGUIDE / "kospi200_tr.xlsx", "종가지수"),
        "us_eq":     lambda: load_csv(P.EQUITY_GLOBAL / "global_us_spy_tr.csv"),
        "kr_bd":     lambda: load_dg_series(P.DATAGUIDE / "bond_tr_index.xlsx", "종가"),
        "us_bd_mid": lambda: load_csv(P.BOND_GLOBAL / "global_ustreasury_mid_ief.csv"),
        "us_bd_long":lambda: load_csv(P.BOND_GLOBAL / "global_ustreasury_long_tlt.csv"),
        "us_agg":    lambda: load_csv(P.BOND_GLOBAL / "global_us_aggbond_agg.csv"),
        "us_tips":   lambda: load_csv(P.BOND_GLOBAL / "global_us_tips_tip.csv"),
        "gold":      lambda: _xlsx(P.COMMODITY / "gold_long.xlsx"),
        "usdkrw":    lambda: load_csv(P.MACRO / "ecos_usdkrw_long.csv"),  # 1990~ IMF 포함(구 ecos_usdkrw 대체)
        "usdkrw_long": lambda: load_csv(P.MACRO / "ecos_usdkrw_long.csv"),
        "vkospi":    lambda: load_dg_series(P.DATAGUIDE / "vkospi.xlsx", "종가지수"),
        "housing":   lambda: load_csv(P.REAL_ESTATE / "kr_housing_price_index.csv"),
        "macquarie": lambda: load_csv(P.REAL_ESTATE / "macquarie_infra_088980.csv"),
        # ── 무료 장기 해외지수(FDR, 가격) ──
        "us_eq_long":     lambda: load_csv(P.EQUITY_GLOBAL / "sp500_fdr.csv"),
        "us_nasdaq_long": lambda: load_csv(P.EQUITY_GLOBAL / "nasdaq_long_fdr.csv"),
        "jp_eq":          lambda: load_csv(P.EQUITY_GLOBAL / "nikkei225_fdr.csv"),
        "eafe":           lambda: load_csv(P.EQUITY_GLOBAL / "msci_eafe_efa_fdr.csv"),
        "jpykrw":         lambda: load_csv(P.MACRO / "jpykrw_fdr.csv"),
        # ── ECOS 장기 금리·물가 ──
        "ktb3y":     lambda: load_csv(P.BOND_KR / "ecos_ktb3y_long.csv"),
        "ktb5y":     lambda: load_csv(P.BOND_KR / "ecos_ktb5y_long.csv"),
        "ktb10y":    lambda: load_csv(P.BOND_KR / "ecos_ktb10y_long.csv"),
        "cd91":      lambda: load_csv(P.BOND_KR / "ecos_cd91_long.csv"),
        "call":      lambda: load_csv(P.BOND_KR / "ecos_call_long.csv"),
        "baserate":  lambda: load_csv(P.BOND_KR / "ecos_baserate_long.csv"),
        "cpi":       lambda: load_csv(P.MACRO / "ecos_cpi_long.csv"),
    }
    if name not in table:
        raise KeyError(f"알 수 없는 자산: {name}. 가능: {sorted(table)}")
    return table[name]()


def _xlsx(path: str | Path, col: str | None = None) -> pd.Series:
    df = pd.read_excel(path)
    dc = next(c for c in df.columns if str(c).lower() in _DATECOLS)
    df[dc] = pd.to_datetime(df[dc])
    vc = col or [c for c in df.columns if str(c).lower() not in _DATECOLS][0]
    return df.set_index(dc)[vc].sort_index().rename(Path(path).stem)


def load_tdf_nav() -> pd.DataFrame:
    """KOFIA TDF 기준가 long -> wide (date x fund_code) DataFrame."""
    df = pd.read_csv(paths.FUND_TDF / "tdf_nav_kofia.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df.pivot_table(index="date", columns="fund_code", values="nav").sort_index()
