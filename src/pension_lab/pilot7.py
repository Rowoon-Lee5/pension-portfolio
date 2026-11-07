"""7개 주제 파일럿 공통 — 월간 수익률·근거 상수·약세장·앞으로 누적수익.

모든 상수 근거: docs/ideas/7주제_파일럿_파라미터근거_20261008.md (괄호 = 대장 절). 자가점검: python -m pension_lab.pilot7
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import io, paths
from .aftertax import CREDIT_LOW, CREDIT_HIGH, PENSION_UNDER70, ETC_TAX, TAX_FINANCIAL  # noqa: F401 (노트북이 P.* 로 씀)

OUT = paths.RESULTS / "pilot7_20261008"
SEED = 20261008
NP = 10_000             # (D2) Finlay & Zorn PDF6 시나리오 수
BEAR = -0.20            # (D2) 약세장: 광범위 지수 20%+ 하락, ≥2개월 — SEC investor.gov 'Bear market'
BEAR_MIN_MONTHS = 2
LOAN = {"신한 연금저축담보 5.00%": 0.0500,   # (B) 신한투자증권 1차, 2026.01.01
        "은행 일반신용 6.33%": 0.0633,        # (B) ECOS 121Y006 BECBLA03051, 2026.08
        "은행 소액 6.55%": 0.0655}            # (B) ECOS 121Y006 BECBLA0301, 2026.08
LOAN_REF_DATE = {"신한 연금저축담보 5.00%": ("2025-12-31", "2025-12-31"),   # 신한 공시 기준일 2026.01.01 → 직전 영업일 CD91
                 "은행 일반신용 6.33%": ("2026-08-01", "2026-08-31"),       # ECOS 2026.08 신규취급 → 같은 달 CD91 평균
                 "은행 소액 6.55%": ("2026-08-01", "2026-08-31")}
LOAN_TERM_M = 12        # (B) 신한 담보대출 기간 365일
LOAN_LTV = 0.50         # (B) 신한 한도 = 펀드평가액 50%
LOAN_MAINT = 1.40       # (B) 신한 담보유지비율 = 대출금액의 140%
CONTRIB_YEAR = 3_420_000  # (B) 금감원 2024 계약당 연간 납입액
CREDIT_CAP = 6_000_000    # (A) §59의3① 연금저축 공제한도
CONTRIB_LIMIT = 18_000_000  # (A) 시행령 §40의2②1 연 납입한도
BD_TER = 0.0017         # (C) KODEX 국고채3년 TER 0.17% (kr_bd는 지수라 보수 미차감)
FEE_PENSION = 0.000042087   # (C) 삼성증권 연금계좌 온라인 ETF = 유관기관 제비용만
FEE_TAXABLE = {"0.015%(저가 온라인)": 0.00015, "0.147216%(대형사 일반)": 0.00147216}  # (C) 금투협·삼성증권
CA_MONTHS = (3, 4, 5, 6)   # (D) Finlay & Zorn 분할 기간
US_END = "2026-08"   # 미국 월 표본 끝(2026-09 부분월 제외)
MIX = {"주식100": 1.0, "60/40": 0.6, "40/60": 0.4}   # (D) Finlay & Zorn·Dichtl
BAND = 0.03                # (D) Dichtl ±3%
GAMMAS = (3, 6, 10)        # (D) Finlay & Zorn CRRA γ
EQ_KR_SHARE = 0.35         # (D2) 가정_전수조사 #4 (T7 재추정 15.2%와 충돌 → T7은 둘 다 그리드)
REENTRY_GRID = (1, 3, 6, 12)   # ⬜결정: 재진입·중단 기간 — 논문 근거 없음(R2), 민감도 그리드만
PRE = "2024-12"            # 2025~26 급등 제외 민감도 끝(감사: 표본 7.9%가 로그성장 46%)


def monthly() -> pd.DataFrame:
    """월말 기준 월수익률: eq(KODEX200 수정주가=TR·보수차감), bd(국고채 TR − ETF TER), us(SPY TR×원달러, 비헤지),
    cash(CD91 전월말 금리 → 룩어헤드 없음), infl(CPI; 마지막 달 결측 가능). 2026-09는 데이터 끝(9/23)까지의 부분월."""
    lv = lambda n: io.asset_series(n).resample("ME").last()
    r = pd.DataFrame({
        "eq": lv("kr_eq").pct_change(fill_method=None),
        "bd": lv("kr_bd").pct_change(fill_method=None) - BD_TER / 12,
        "us": (lv("us_eq") * lv("usdkrw")).pct_change(fill_method=None),
        "cash": lv("cd91").shift(1) / 100 / 12,
        "infl": lv("cpi").pct_change(fill_method=None),
    })
    return r.dropna(subset=["eq", "bd", "us", "cash"])


def kospi200_px() -> pd.Series:
    """KOSPI200 가격지수 월수익(1990~) — 약세장 '상태' 판정용(SEC 정의 = 광범위 지수)."""
    p = pd.read_csv(paths.EQUITY_KR / "idx_kospi200.csv", parse_dates=["날짜"]).set_index("날짜")["종가"]
    return p.resample("ME").last().pct_change(fill_method=None).dropna()


def div_monthly(index: pd.DatetimeIndex, taxable: bool = True) -> pd.Series:
    """KODEX200 월별 분배율(배당락 월에 그대로, 표본 밖 분배 제외). taxable=True면 과세표준 기준(일반계좌 15.4% 과세용)."""
    d = pd.read_csv(paths.EQUITY_KR / "kodex200_dist_web.csv")
    rate = d["dist_rate_pct_분배율"] / 100
    if taxable:
        rate = rate * d["dist_after_tax_과표기준"] / d["dist_per_share_주당분배금"]
    m = pd.to_datetime(d["exdiv_date_배당락일"].astype(str)) + pd.offsets.MonthEnd(0)
    return rate.groupby(m.values).sum().reindex(index, fill_value=0.0)


def drawdown(ret: pd.Series) -> pd.Series:
    """시작 원금 1도 고점으로 침(첫 달 급락 반영; bootstrap.mdd_from_returns와 같은 규칙)."""
    lvl = (1 + ret).cumprod()
    return lvl / lvl.cummax().clip(lower=1.0) - 1


def first_bear(R: np.ndarray) -> np.ndarray:
    """(n,T) 경로별 첫 약세장 '행동월'(판정 월말 다음 달; 마지막 달 판정이면 T, 없으면 T+1). 시작 원금 1 포함."""
    n, T = R.shape
    lvl = np.c_[np.ones(n), np.cumprod(1 + R, axis=1)]; peak = np.maximum.accumulate(lvl, axis=1)
    t = np.arange(T + 1); ppos = np.maximum.accumulate(np.where(lvl >= peak, t, 0), axis=1)
    hit = (lvl / peak - 1 <= BEAR) & (t - ppos >= BEAR_MIN_MONTHS)
    return np.where(hit.any(1), hit.argmax(1), T + 1)  # lvl 인덱스 j = j번째 달 말 → 행동월(0기준) = j


def bear_starts(ret: pd.Series) -> list[pd.Timestamp]:
    """약세장 진입 판정월(월말). 새 고점 회복 뒤에만 다음 사건. first_bear와 같은 규칙."""
    if ret.empty:
        return []
    out, R = [], ret.to_numpy(float)
    i = 0
    while i < len(R):
        j = int(first_bear(R[None, i:])[0])
        if j > len(R) - i:
            break
        out.append(ret.index[i + j - 1])
        lvl = np.cumprod(1 + R[i + j:]); base = np.prod(1 + R[i:i + j])   # 판정 이후 이전 고점 회복 시점부터 다시
        pk = np.max(np.r_[1.0, np.cumprod(1 + R[i:i + j])])
        rec = np.flatnonzero(base * lvl >= pk)
        if not len(rec):
            break
        i = i + j + rec[0] + 1
    return out


def fwd(x: pd.Series, n: int, lag: int = 0) -> pd.Series:
    """s월말 결정 → s+lag+1..s+n 누적배수(시작 s로 정렬)."""
    return np.exp(np.log1p(x).rolling(n - lag).sum()).shift(-n).dropna()


def pw_block(x) -> float:
    """Politis–White(2004)+Patton 등(2009) 자동 평균블록(stationary, Dichtl PDF13). 1 미만은 1."""
    from arch.bootstrap import optimal_block_length
    return max(1.0, float(optimal_block_length(np.asarray(x, float))["stationary"].iloc[0]))


def mix_ret(r: pd.DataFrame, w_eq: float, eq: str = "eq") -> pd.Series:
    """매월 목표비중 리밸런싱(주식 w_eq, 나머지 bd). 월초 비중 → 월수익."""
    return w_eq * r[eq] + (1 - w_eq) * r["bd"]


def cer(W: np.ndarray, g: float) -> float:
    """CRRA 확실성등가 (Finlay & Zorn 부록3): E[W^(1−γ)]^(1/(1−γ))."""
    return float(np.mean(np.asarray(W, float) ** (1 - g)) ** (1 / (1 - g)))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; c = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n); m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return (m - c, m + c)


# ── 표본 확장(2026-10-08 회원 요청: 짧은 표본·적은 사건 보완) ──────────────────────────
def par_bond_tr(y_pct: pd.Series, n_years: float, freq: int = 2) -> pd.Series:
    """만기수익률(%) 월별 → 액면채 월 총수익. Swinkels(2019) 근사(synthbond.py와 같은 식) TR = y_{t-1}/12 − MD·Δy + ½·C·Δy²,
    단 MD·C를 상수 가정 대신 '액면채(쿠폰=수익률, 연 freq회 이자)' 현금흐름으로 매달 정확히 계산(근거 없는 상수 회피)."""
    y = y_pct.astype(float) / 100
    k = np.arange(1, int(round(n_years * freq)) + 1)
    def md_c(yy):
        c, d = yy / freq, (1 + yy / freq) ** -k.astype(float)
        cf = np.full(len(k), c); cf[-1] += 1; pv = cf * d; P = pv.sum()
        t = k / freq; D = (t * pv).sum() / P
        return D / (1 + yy / freq), (t * (t + 1 / freq) * pv).sum() / (P * (1 + yy / freq) ** 2)
    mc = np.array([md_c(v) if np.isfinite(v) else (np.nan, np.nan) for v in y.shift(1).values]); dy = y.diff()   # Swinkels: MD·C는 y_{t−1}
    return (y.shift(1) / 12 - mc[:, 0] * dy + 0.5 * mc[:, 1] * dy ** 2).dropna()


def loan_spread() -> dict:
    """대출 가산폭 = 2026 대출금리 − 그 금리 기준시점의 CD91(일별, %) — '그때 단기금리 + 가산폭' 민감도용(회원 결정 2026-10-08)."""
    cd = io.asset_series("cd91")
    return {k: LOAN[k] - float(cd.loc[a:b].mean()) / 100 for k, (a, b) in LOAN_REF_DATE.items()}


def sp500_monthend() -> pd.Series:
    """S&P500 월말 종가(1965~2023-06 yfinance, 2023-07~ FDR; 일별 → 월말). Shiller는 월평균이라 월말 종가로 교체(4차 감사)."""
    s = pd.read_csv(paths.EQUITY_GLOBAL / "sp500_price_yf_1965.csv", parse_dates=["date"]).set_index("date")["close"].resample("ME").last()
    # 6차 감사: 2023-07~2026-08 연장(FDR S&P500 종가, 같은 지수 수준) — 2026-09는 부분월이라 제외
    fdr = pd.read_csv(paths.EQUITY_GLOBAL / "sp500_fdr.csv", index_col=0, parse_dates=True).iloc[:, 0].resample("ME").last()
    return pd.concat([s.loc[:"2023-06"], fdr.loc["2023-07":US_END]])


def us_tr_monthend() -> pd.Series:
    """미국 월 총수익(USD) = (월말종가_t + Shiller D_t/12)/월말종가_{t−1} − 1. D = Shiller 연환산 배당(1차 자료; 분기 배당을 월로 보간한 값이라 배당 부분에 미세한 보간 미래정보 ⚠)."""
    C = sp500_monthend(); D = shiller_raw()["D"]
    sh = ((C + D.reindex(C.index) / 12) / C.shift(1) - 1).dropna().loc[:"2023-06"]
    # Shiller D 끝(2023-06) 이후: S&P500 총수익지수(^SP500TR, yfinance) 월말 수익(6차 감사 연장)
    tr = pd.read_csv(paths.EQUITY_GLOBAL / "sp500tr_yf_1988.csv", index_col=0, parse_dates=True).iloc[:, 0].resample("ME").last().pct_change(fill_method=None)
    return pd.concat([sh, tr.loc["2023-07":US_END]])


def div_tax_ratio() -> float:
    """KODEX200 분배금 중 과세표준 비율(과표기준 ÷ 주당분배금)의 평균 — 배당수익률로 일반계좌 분배 과세를 할 때 쓰는 자료 기반 비율."""
    d = pd.read_csv(paths.EQUITY_KR / "kodex200_dist_web.csv")
    return float((d["dist_after_tax_과표기준"] / d["dist_per_share_주당분배금"]).mean())


def us_div_yield(index: pd.DatetimeIndex) -> pd.Series:
    """미국주식 월 배당수익(소수) = Shiller D_t/12 ÷ 전월말 S&P 종가(FDR 1984~2026 → yfinance 1965~ 앞부분).
    Shiller D는 2023-06까지 → 2023-07~2026-08은 ^SP500TR − S&P500 가격 월수익, 그 뒤(부분월)만 직전값. 일반계좌 해외주식형 ETF 분배금 15.4% 과세용."""
    fdr = pd.read_csv(paths.EQUITY_GLOBAL / "sp500_fdr.csv", index_col=0, parse_dates=True).iloc[:, 0].resample("ME").last()
    C = pd.concat([sp500_monthend().loc[:"1984-11"], fdr.loc["1984-12":]])
    D = shiller_raw()["D"].dropna().reindex(C.index)
    dy = (D / 12 / C.shift(1)).loc[:"2023-06"]
    # Shiller D 끝 이후: 총수익지수 월수익 − 가격 월수익(= 그 달 배당 ÷ 전월말 가격, 6차 감사: 전에는 마지막 값 고정)
    tr = pd.read_csv(paths.EQUITY_GLOBAL / "sp500tr_yf_1988.csv", index_col=0, parse_dates=True).iloc[:, 0].resample("ME").last()
    ext = (tr.pct_change(fill_method=None) - fdr.pct_change(fill_method=None)).clip(lower=0).loc["2023-07":US_END]
    return pd.concat([dy, ext]).reindex(index).ffill()


def dg_econ() -> pd.DataFrame:
    """DataGuide 6 경제 항목(2026-10-09 추출, dataguide/kospi_k200_tr_1980.xlsx Sheet2 → dg_econ_divyield_rates_19900101.csv):
    평균배당수익률(가중·전종목, 월, %) 1990-01~, CD91 일별 1994-06~, 국민주택1종5년 일별 1993-07~, 국고3년 일별 1995-05~, 회사채 AA- 3년, 국고5년 (%)."""
    return pd.read_csv(paths.DATA_ROOT / "dataguide" / "dg_econ_divyield_rates_19900101.csv", parse_dates=["date"]).set_index("date")


def kr_div_yield(pre2000: str = "dataguide") -> pd.Series:
    """KOSPI200 월 배당수익(소수, 월) — 2000~ KRX 일별 배당수익률 월평균/12(중간 결측은 직전값).
    1990~1999: 'dataguide'(기본) = DataGuide 유가증권시장 평균배당수익률(가중·전종목, 월)/12 — 2000~2026 겹침에서 KOSPI200 배당수익률과 상관 0.94·비율 중앙값 1.02;
    'zero'(하한) / 'early2000s'(2000~04 실측 평균)는 민감도용."""
    px = kospi200_px()
    fd = pd.read_csv(paths.EQUITY_KR / "idx_kospi200_fundamental.csv", parse_dates=["날짜"]).set_index("날짜")["배당수익률"]
    dy = (fd.replace(0, np.nan).resample("ME").mean() / 100 / 12).reindex(px.index)
    dy.loc["2000-01":] = dy.loc["2000-01":].ffill()
    if pre2000 == "dataguide":
        m = dg_econ()["mkt_divyield_pct"].dropna(); m.index = m.index + pd.offsets.MonthEnd(0)
        dy.loc[:"1999-12"] = (m.groupby(level=0).last() / 100 / 12).reindex(dy.loc[:"1999-12"].index).ffill()
    else:
        dy.loc[:"1999-12"] = 0.0 if pre2000 == "zero" else float(dy.loc["2000-01":"2004-12"].mean())
    return dy


def kospi_px_1980() -> pd.Series:
    """코스피 종합 가격지수 월말(1980-01~, DataGuide 6 I.001 종가지수 일별 → dataguide/dg_kospi_k200_tr_daily_19800104.csv, 2026-10-09 추출).
    배당 미포함(1990 이전 배당 자료 없음) → 주식 수익 과소 ⚠."""
    d = pd.read_csv(paths.DATA_ROOT / "dataguide" / "dg_kospi_k200_tr_daily_19800104.csv", index_col=0, parse_dates=True)["kospi"].dropna()
    return d.resample("ME").last()


def _kr_bond_long(vol_adj: bool = False) -> pd.Series:
    """한국 채권 월 총수익(TER 전) → par_bond_tr: 국민주택1종 5년 ECOS 월평균(~1993-07) · 국민주택 5년 DataGuide 일별 월말
    (1993-08~1998-11) · 국고채3년 DataGuide 일별 월말(1998-12~2004-06), 2004-07~ 실제 국고채 TR.
    국고3년 1995~98은 고시성 금리라 장기 고정(1997-06~11 11.65, 1997-12~1998-03 15.00; 월말 무변동 1997년 67%) → 위기 변동성 과소 →
    시장 금리가 움직이는 국민주택5년(무변동 1997 17%)을 1998-11까지 씀(6차 감사 🟠). 1998-12 이후 국고3년 월말값은 ECOS 일별과 최대 0.05%p 차.
    vol_adj=True면 월평균 금리 구간(~1993-07)의 평균 대비 편차를
    '월말/월평균 금리로 만든 합성 TR의 표준편차 비'(국고3년 1998-12~ 겹침: ECOS 일별 월말 vs ECOS 월평균)로 확대."""
    me = lambda s: s.set_axis(s.index + pd.offsets.MonthEnd(0))
    nh = me(pd.read_csv(paths.BOND_KR / "ecos_nhb5y_monthly_1987.csv", index_col=0, parse_dates=True).iloc[:, 0])
    k3 = me(pd.read_csv(paths.BOND_KR / "ecos_ktb3y_monthly_1995.csv", index_col=0, parse_dates=True).iloc[:, 0])
    k3d = pd.read_csv(paths.BOND_KR / "ecos_ktb3y_long.csv", index_col=0, parse_dates=True).iloc[:, 0].resample("ME").last()
    dg = dg_econ(); nhd = dg["nhb5y_pct"].dropna().resample("ME").last(); k3g = dg["ktb3y_pct"].dropna().resample("ME").last()
    avg = par_bond_tr(nh, 5).loc[:"1993-07"]
    end = pd.concat([par_bond_tr(nhd, 5).loc["1993-08":"1998-11"], par_bond_tr(k3g, 3).loc["1998-12":"2004-06"]])
    if vol_adj:
        ov = slice("1998-12", "2026-08")
        ratio = par_bond_tr(k3d, 3).loc[ov].std() / par_bond_tr(k3, 3).loc[ov].std()
        avg = avg.mean() + ratio * (avg - avg.mean())
    act = io.asset_series("kr_bd").resample("ME").last().pct_change(fill_method=None).loc["2004-07":]
    return pd.concat([avg, end, act])


def monthly_kr_long(pre2000: str = "dataguide", bond_vol_adj: bool = False) -> pd.DataFrame:
    """한국 1991-04~ 월수익(현금이 전월말 금리라 첫 달 1991-04). eq = KOSPI200 가격 + kr_div_yield(pre2000) − KODEX200 보수 0.15%/12(대장 C; ETF 없던 시기에도 차감 = 보수적).
    bd = _kr_bond_long(bond_vol_adj) − TER. cash = CD91(1991~1994-05 ECOS 월, 1994-06~ DataGuide·ECOS 일별 월말), 전월말 금리. infl = CPI.
    us = 월말 S&P + Shiller 배당(~1999) → SPY TR(2000~), ×원달러 월말."""
    px = kospi200_px()
    eq = px + kr_div_yield(pre2000) - 0.0015 / 12
    bd = _kr_bond_long(bond_vol_adj) - BD_TER / 12
    me = lambda s: s.set_axis(s.index + pd.offsets.MonthEnd(0))
    sr = pd.read_csv(paths.BOND_KR / "ecos_shortrate_monthly_1989_1996.csv", parse_dates=["date"]).set_index("date")["cd91_monthly"]
    cdg = dg_econ()["cd91_pct"].dropna().resample("ME").last()
    cd = pd.concat([me(sr.dropna()).loc[:"1994-05"], cdg.loc["1994-06":"1994-12"], io.asset_series("cd91").resample("ME").last().loc["1995-01":]])   # 1994-06~ DataGuide 일별 월말
    cash = (cd.shift(1) / 1200)
    infl = io.asset_series("cpi").resample("ME").last().pct_change(fill_method=None)
    fx = io.asset_series("usdkrw").resample("ME").last()
    us_usd = pd.concat([us_tr_monthend().loc[:"1999-12"], io.asset_series("us_eq").resample("ME").last().pct_change(fill_method=None).loc["2000-01":]])
    us = (1 + us_usd) * (fx / fx.shift(1)).reindex(us_usd.index) - 1
    r = pd.DataFrame({"eq": eq, "bd": bd, "us": us, "cash": cash, "infl": infl})
    r = r.loc["1991-03":].dropna(subset=["eq", "bd", "us", "cash", "infl"])
    full = pd.date_range(r.index[0], r.index[-1], freq="ME")
    assert len(full) == len(r), f"월 누락: {full.difference(r.index)[:5].tolist()}"
    return r


def shiller_raw() -> pd.DataFrame:
    """Shiller ie_data 원자료: P(월평균 가격), D(연환산 배당), CPI, B(월 국채 총수익 배수, 열 17)."""
    x = pd.read_excel(paths.EQUITY_GLOBAL / "shiller_ie_data_20260928.xls", sheet_name="Data", header=None, skiprows=8)
    x = x[pd.to_numeric(x[0], errors="coerce").notna()]
    dt = pd.to_datetime(x[0].map(lambda v: f"{int(v)}-{int(round((v % 1) * 100)):02d}")) + pd.offsets.MonthEnd(0)
    return pd.DataFrame({k: pd.to_numeric(x[i], errors="coerce").set_axis(dt) for k, i in (("P", 1), ("D", 2), ("CPI", 4), ("B", 17))})


def shiller_monthly() -> pd.DataFrame:
    """미국 Shiller(1871~) 월: eq = (P_t + D_t/12)/P_{t−1} − 1 (월평균 가격 ⚠), bd = Shiller 월 국채 총수익(열 17), infl = CPI."""
    x = shiller_raw()
    return pd.DataFrame({"eq": (x.P + x.D / 12) / x.P.shift(1) - 1, "bd": x.B - 1, "infl": x.CPI / x.CPI.shift(1) - 1})


def us_px_monthend() -> pd.Series:
    """미국 약세장 판정용 가격 월수익: S&P500 월말 종가(1965-01~2026-08)."""
    return sp500_monthend().pct_change(fill_method=None).dropna()


def monthly_us_long() -> pd.DataFrame:
    """미국 1965-02~2026-08 월(USD): eq = 월말 종가 + Shiller 배당(us_tr_monthend), bd·infl = Shiller(열 17·4), 현금 FRED DTB3(전월말).
    (4차 감사: 1965~2023 Shiller 월평균 가격은 연변동성 12.5%·AC1 0.22, 월말 종가는 15.1%·0.005 → 월말 종가로 교체)"""
    sh = shiller_monthly()
    tb = pd.to_numeric(pd.read_csv(paths.MACRO / "fred_dtb3.csv", index_col=0, parse_dates=True)["DTB3"], errors="coerce").resample("ME").last()
    # 2023-07~ 연장(6차 감사): bd = 미 국채 7-10년 ETF(IEF) 월말 수익(Shiller 10년 국채와 가장 가까운 만기), infl = FRED CPIAUCSL
    # (2025-10은 BLS 미발표(셧다운) → 9월·11월 사이 2개월 변화를 기하 균등 분할; Shiller CPI는 비계절조정, CPIAUCSL은 계절조정 ⚠ 미세 차)
    ief = io.asset_series("us_bd_mid").resample("ME").last().pct_change(fill_method=None)
    cpi = pd.read_csv(paths.MACRO / "fred_cpiaucsl.csv", index_col=0, parse_dates=True).iloc[:, 0]
    cpi = cpi.set_axis(cpi.index + pd.offsets.MonthEnd(0)).asfreq("ME")
    cpi = np.exp(np.log(cpi).interpolate(limit_area="inside"))
    bd = pd.concat([sh["bd"].loc[:"2023-06"], ief.loc["2023-07":US_END]])
    infl = pd.concat([sh["infl"].loc[:"2023-06"], cpi.pct_change(fill_method=None).loc["2023-07":US_END]])
    out = pd.DataFrame({"eq": us_tr_monthend(), "bd": bd, "infl": infl, "cash": tb.shift(1) / 1200}).dropna()
    assert (out.index.to_period("M").to_series().diff().dropna().apply(lambda d: d.n) == 1).all(), "US 월 표본 끊김"
    return out


def jst_panel() -> dict:
    """JST R6 연간(1870~2020) → 나라·연속구간별 월수익(연 수익을 12개월 균등 분할 ⚠ — 연중 낙폭 없음 → 월 단위 '행동 시점' 분석엔 부적합, 수준 지표 전용).
    eq_tr·bond_tr·bill_rate(소수 총수익), cpi → infl. ACO처럼 결측으로 끊긴 구간을 모두 별도 조각('ISO_k')으로 남김(전쟁·붕괴 구간 포함)."""
    d = pd.read_excel(paths.EQUITY_GLOBAL / "jst" / "JSTdatasetR6.xlsx")
    out = {}
    for iso, g in d.groupby("iso"):
        g = g.set_index("year")[["eq_tr", "bond_tr", "bill_rate", "cpi"]]
        g = g.assign(infl=g["cpi"] / g["cpi"].shift(1) - 1)[["eq_tr", "bond_tr", "bill_rate", "infl"]].dropna()
        if g.empty:
            continue
        cut = np.r_[0, np.flatnonzero(np.diff(g.index.values) != 1) + 1, len(g)]
        for k, (a0, b0) in enumerate(zip(cut[:-1], cut[1:])):
            seg = g.iloc[a0:b0]
            m = {c: np.repeat((1 + seg[c].values) ** (1 / 12) - 1, 12) for c in seg.columns}
            out[f"{iso}_{k}"] = pd.DataFrame({"eq": m["eq_tr"], "bd": m["bond_tr"], "cash": m["bill_rate"], "infl": m["infl"]})
    return out


def french_panel(need_infl: bool = True, with_us: bool = True) -> dict:
    """Kenneth French 국제 국가 포트폴리오(MSCI 1975~2006, Bloomberg 2007~; 'Value-Weight Dollar Returns, All 4 Data Items Not Reqd'의 Mkt) 월수익(USD).
    결측(−99.99)으로 끊긴 구간은 별도 조각(12개월 미만 조각 제외). cash = 미 1개월 T-bill(F-F RF), infl = 미 CPI(FRED CPIAUCSL) → 달러 투자자의 실질.
    with_us: 미국(1975~, 월말 종가 + Shiller 배당)을 같은 RF·CPI로 추가. need_infl=False면 CPI 결측(FRED 2025-10 공백)으로 조각을 끊지 않음(실질 환산 안 쓰는 T5용)."""
    d = paths.EQUITY_GLOBAL / "french_intl"
    rf = pd.read_csv(paths.EQUITY_GLOBAL / "french" / "F-F_Research_Data_Factors.csv", skiprows=3, index_col=0)
    ix = rf.index.astype(str).str.strip(); keep = ix.str.fullmatch(r"\d{6}")
    rf = pd.Series(pd.to_numeric(rf["RF"][keep]).values / 100, index=pd.to_datetime(ix[keep], format="%Y%m") + pd.offsets.MonthEnd(0))
    cpi = pd.read_csv(paths.MACRO / "fred_cpiaucsl.csv", index_col=0, parse_dates=True).iloc[:, 0]
    infl = cpi.set_axis(cpi.index + pd.offsets.MonthEnd(0)).pct_change(fill_method=None)
    out = {}
    series = {}
    for f in sorted(d.glob("*.Dat")):
        rows = []
        for ln in f.read_text().splitlines()[4:]:
            t = ln.split()
            if len(t) < 2 or not (t[0].isdigit() and len(t[0]) == 6):
                break
            rows.append((t[0], float(t[1])))
        s = pd.Series([v for _, v in rows], index=pd.to_datetime([k for k, _ in rows], format="%Y%m") + pd.offsets.MonthEnd(0))
        series[f.stem] = s.where(s > -99).div(100)
    if with_us:
        series["USA"] = us_tr_monthend().loc["1975-01":]
    for name, s in series.items():
        df = pd.DataFrame({"eq": s, "cash": rf.reindex(s.index), "infl": infl.reindex(s.index)})
        if not need_infl: df = df.assign(infl=df["infl"].fillna(0.0))       # infl 미사용 용도: 공백이 조각을 끊지 않게(값은 쓰지 말 것)
        ok = df.notna().all(1).to_numpy().astype(int); edges = np.flatnonzero(np.diff(np.r_[0, ok, 0]))
        for k, (a0, b0) in enumerate(zip(edges[::2], edges[1::2])):
            if b0 - a0 >= 12:
                out[f"{name}_{k}"] = df.iloc[a0:b0]
    return out


def _french_table(f, title: str) -> pd.Series:
    """French .Dat 파일에서 제목(title)이 처음 나오는 표의 Mkt 열(월, %→소수, −99.99 → NaN)."""
    lines = f.read_text().splitlines(); i = next(k for k, ln in enumerate(lines) if title in ln) + 3
    rows = []
    for ln in lines[i:]:
        t = ln.split()
        if len(t) < 2 or not (t[0].isdigit() and len(t[0]) == 6):
            break
        rows.append((t[0], float(t[1])))
    s = pd.Series([v for _, v in rows], index=pd.to_datetime([k for k, _ in rows], format="%Y%m") + pd.offsets.MonthEnd(0))
    return s.where(s > -99).div(100)


OECD_ISO = {"Austria": "AT", "Belgium": "BE", "Canada": "CA", "Denmark": "DK", "Finland": "FI", "France": "FR", "Germany": "DE", "Ireland": "IE",
            "Italy": "IT", "Japan": "JP", "Nethrlnd": "NL", "Norway": "NO", "Spain": "ES", "Sweden": "SE", "Swtzrlnd": "CH", "UK": "GB", "USA": "US"}


_ISO3 = {"AT": "AUT", "BE": "BEL", "CA": "CAN", "DK": "DNK", "FI": "FIN", "FR": "FRA", "DE": "DEU", "IE": "IRL", "IT": "ITA", "JP": "JPN",
         "NL": "NLD", "NO": "NOR", "ES": "ESP", "SE": "SWE", "CH": "CHE", "GB": "GBR", "US": "USA"}


def oecd_cpi_ext(fr: pd.DataFrame) -> pd.DataFrame:
    """현지 CPI 월 전월비(소수), 나라별 이어붙이기(2026-10-09, 남은 한계 보완): ① FRED CPALTT01..M657N(~2024-02/03, 일본 ~2021-06)
    → ② OECD Data Explorer SDMX 'N·IX·_T·N·_Z' 지수 전월비(~2025-12, 일부 2026-08; 2015~ 겹침 전월비 상관 0.978~1.000, 14개국 동일·AT·GB·JP 최대차 0.10~0.16%p)
    → ③ BIS 장기 CPI(WS_LONG_CPI, 2010=100, ~2026-07/08; ①과 상관 0.976~1.000, 소수 둘째 자리 반올림이라 무변동 달 최대 14%).
    ①이 끝난 다음 달부터 ②, ②가 없는 달은 ③. 지수 안쪽 빈 달은 로그 선형보간(미국 2025-10)."""
    sd = pd.read_csv(paths.MACRO / "oecd_sdmx_cpi_raw_20261009.csv", usecols=["REF_AREA", "METHODOLOGY", "UNIT_MEASURE", "EXPENDITURE", "ADJUSTMENT", "TRANSFORMATION", "TIME_PERIOD", "OBS_VALUE"])
    sd = sd[(sd.METHODOLOGY == "N") & (sd.UNIT_MEASURE == "IX") & (sd.EXPENDITURE == "_T") & (sd.ADJUSTMENT == "N") & (sd.TRANSFORMATION == "_Z")]
    sd = sd.pivot_table(index="TIME_PERIOD", columns="REF_AREA", values="OBS_VALUE"); sd.index = pd.to_datetime(sd.index) + pd.offsets.MonthEnd(0)
    bi = pd.read_csv(paths.MACRO / "bis_long_cpi_monthly_20261009.csv").pivot_table(index="TIME_PERIOD", columns="REF_AREA", values="OBS_VALUE")
    bi.index = pd.to_datetime(bi.index) + pd.offsets.MonthEnd(0)
    out = {}
    for i2, i3 in _ISO3.items():
        # 월 빈도로 맞춘 뒤, 안쪽 빈 달(미국 2025-10 BLS 미발표 등)만 로그 지수 선형보간(앞뒤 변화를 기하 균등분할 — monthly_us_long과 같은 처리)
        mpct = lambda z: np.exp(np.log(z.asfreq("ME")).interpolate(limit_area="inside")).pct_change(fill_method=None)
        a = (fr[f"CPALTT01{i2}M657N"] / 100).dropna()
        b = mpct(sd[i3].dropna()) if i3 in sd else pd.Series(dtype=float)
        c = mpct(bi[i2].dropna())
        x = a.reindex(a.index.union(b.index).union(c.index))
        after = x.index > a.index.max()                                       # ① 끝 다음 달부터: ② 우선, ② 빈 달은 ③
        x[after] = b.reindex(x.index)[after].fillna(c.reindex(x.index)[after])
        out[i2] = x.dropna()
    return pd.DataFrame(out)


def oecd_local_panel() -> dict:
    """현지통화 다국가 월 패널(ACO처럼 각국 투자자의 현지 실질): eq = French 'Value-Weight Local Returns, All 4 Not Reqd' Mkt(미국은 월말 종가+Shiller 배당),
    bd = OECD 장기(10년) 국채금리 IRLTLT01 → par_bond_tr(10년)(월평균 금리 ⚠ 평활), cash = OECD 3개월 금리 IR3TIB01 전월값/12,
    infl = 현지 CPI 전월비(oecd_cpi_ext: FRED CPALTT01 → OECD SDMX → BIS, 2026-07/08까지). 월별 CPI가 없는 호주·뉴질랜드, OECD 금리가 없는 홍콩·말레이시아·싱가포르 제외.
    모든 열이 있는 연속 구간만 조각(12개월 이상)."""
    fr = pd.concat([pd.read_csv(f, index_col=0, parse_dates=True) for f in sorted(paths.MACRO.glob("fred_oecd_*.csv"))], axis=1)
    fr = fr.set_axis(fr.index + pd.offsets.MonthEnd(0)); cpi = oecd_cpi_ext(fr)
    d = paths.EQUITY_GLOBAL / "french_intl"; out = {}
    for stem, iso in OECD_ISO.items():
        eq = us_tr_monthend().loc["1975-01":] if iso == "US" else _french_table(d / f"{stem}.Dat", "Value-Weight Local  Returns      All 4 Data Items Not Reqd")
        y = fr[f"IRLTLT01{iso}M156N"].dropna()
        df = pd.DataFrame({"eq": eq, "bd": par_bond_tr(y, 10), "cash": fr[f"IR3TIB01{iso}M156N"].shift(1) / 1200,
                           "infl": cpi[iso]}).loc[eq.index[0]:]
        ok = df.notna().all(1).to_numpy().astype(int); edges = np.flatnonzero(np.diff(np.r_[0, ok, 0]))
        for k, (a0, b0) in enumerate(zip(edges[::2], edges[1::2])):
            if b0 - a0 >= 12:
                out[f"{stem}_{k}"] = df.iloc[a0:b0]
    return out


def tdf_ext_universe() -> pd.DataFrame:
    """확장 TDF 표본(5개 운용사 외 14개사): KOFIA 투자설명서 공시 글라이드(glidepath_disclosed_web_kr_others.csv, 운용사 원문 1차) 중
    상품명에 목표연도가 있고 위험자산비중 값이 있는 행. -> long [code, manager, vintage, years_rel_target, risky_pct, capped]. 'T−5' = 목표 5년 전.
    공시값 '≤80'·'≤40'(상한 표기, 교보 T−30~T−20·IBK T0 등 14행)은 상한값 N으로 읽고 capped=True(6차 감사 🟠: 전에는 NaN으로 빠져 외삽됨).
    값이 아예 없는 트러스톤 3개·DB 2040은 제외 → 14개사."""
    g = pd.read_csv(paths.FUND_TDF / "glidepath_disclosed_web_kr_others.csv")
    g = g.assign(code=g["source_url"].str.extract(r"표준코드 (K\w{11})")[0],
                 vintage=pd.to_numeric(g["product"].str.extract(r"(20\d\d)")[0], errors="coerce"),
                 years_rel_target=pd.to_numeric(g["target_year_or_years_to_target"].str.extract(r"T([+-]?\d+)?")[0].fillna("0"), errors="coerce"),
                 risky_pct=pd.to_numeric(g["risky_pct"].astype(str).str.replace("≤", "", regex=False).str.strip(), errors="coerce"),
                 capped=g["risky_pct"].astype(str).str.contains("≤", regex=False))
    return g.dropna(subset=["code", "vintage", "years_rel_target", "risky_pct"])[["code", "manager", "vintage", "years_rel_target", "risky_pct", "capped"]]


def tdf_ext_nav() -> pd.DataFrame:
    """확장 표본 정제 기준가(설정일~): KOFIA 전 기간 재취득(fetch.kofia_navfull ext, 2026-10-08) → 같은 정제 규칙 v3(notebooks/A_nav_clean_v3 ext)
    = processed/nav_tdfext_clean_v3_20260928.csv. 2022~ 겹침 구간에서 이전 정제본과 일간수익 99.96% 일치(48,280행 중, 6차 감사 재현). wide."""
    d = pd.read_csv(paths.PROCESSED / "nav_tdfext_clean_v3_20260928.csv", usecols=["date", "fund_code", "segment_id", "nav_clean"], parse_dates=["date"])
    d = d[d["fund_code"].isin(set(tdf_ext_universe()["code"]))].sort_values(["fund_code", "date"])
    # 정제본은 조각(segment_id)끼리 잇지 않는 설계 + 장기 공백(>14일) 뒤 재시작 → 조각 경계를 가로지르면 재설정이 가짜 손실(교보 2050 −14.7% 등).
    # 펀드별로 '조각 변경 또는 14일 넘는 공백'에서 끊고 가장 긴 연속 구간만 씀(6차 감사 🔴, 해당 5개 펀드).
    g = d.groupby("fund_code")
    run = ((g["segment_id"].diff().fillna(0) != 0) | (g["date"].diff().dt.days > 14)).astype(int).groupby(d["fund_code"]).cumsum()
    d = d.assign(run=run.to_numpy())
    best = d.groupby(["fund_code", "run"]).size().reset_index(name="n").sort_values("n").groupby("fund_code").tail(1)
    d = d.merge(best[["fund_code", "run"]], on=["fund_code", "run"])
    return d.pivot_table(index="date", columns="fund_code", values="nav_clean").sort_index()


def tdf_ext_fee(code: str, idx, kind: str = "nav") -> float:
    """확장 표본 펀드의 '기준가에 이미 빠진' 연 보수(소수)를 월 idx 평균으로: 클래스·단일 펀드 = 합성 총보수·비용(fee_pct),
    종류형 운용펀드 코드(61개) = 합성 − 총보수(fee_underlying_pct; 피투자펀드 보수 등). 운용펀드 기준가에는 클래스 총보수(운용·판매·수탁·사무)가
    안 빠짐 — 같은 펀드 운용 vs 클래스 기준가 18쌍의 연 수익 격차가 클래스 총보수와 일치(흥국 2050 0.293 vs 0.295 등, 7차 감사).
    → 운용펀드 코드의 'TDF − 직접형' 차이에는 투자자가 실제로 내는 클래스 총보수가 빠져 있음 ⚠. 출처: KOFIA 투자설명서·간이투자설명서
    (fetch.tdfext_fee_extract → raw/fund_tdf/tdfext_fee_kofia_20261009.csv). 기간 밖 달은 NaN."""
    f = pd.read_csv(paths.FUND_TDF / "tdfext_fee_kofia_20261009.csv", parse_dates=["start", "end"])
    # kind="nav": 기준가에 이미 빠진 보수 / kind="investor_extra": 연금 클래스 투자자가 기준가 밖에서 더 내는 몫
    #   = 운용펀드 코드: 연금 클래스 합성 − 합성−총보수(=연금 클래스 총보수), 클래스·단일 코드: 0
    f = f[f["standardCd"] == code]
    if kind == "nav":
        f = f.assign(v=f["fee_pct"].fillna(f["fee_underlying_pct"]))
    else:
        f = f.assign(v=np.where(f["fee_pct"].notna(), 0.0, f["pension_class_synthetic_pct"] - f["fee_underlying_pct"]))
    vals = [f.loc[(f["start"] <= t) & (f["end"] >= t), "v"] for t in pd.DatetimeIndex(idx)]
    return float(np.nanmean([v.iloc[0] if len(v) else np.nan for v in vals])) / 100


ACWI_SPLIT = {"US_EQ": 0.64, "DM_EXUS_EQ": 0.26, "EM_EQ": 0.10}   # GLOBAL_EQ 배분: MSCI ACWI 지역 비중 근사(2025 팩트시트, 미국 약 64%·신흥 약 10%)


KRW_ETF = r"^(한국투자\s*)?(ACE|RISE|KODEX|TIGER|KBSTAR|SOL|HANARO|ARIRANG|PLUS|KOSEF|KIWOOM)"


def tdf_holdings_weights() -> pd.DataFrame:
    """운용사 분기 자산운용보고서(fetch.mgmt_report_tdf, 2026-10-09)의 보유종목 → 자산군 비중(룩스루).
    보유종목은 상위 10개·자산 5% 초과만 실려 합계가 50~100% → 실린 종목만 다시 100%로(나머지 처리는 T7 hold_diy의 rem 판본; covered 열 = 실린 비중 %).
    보고서마다 'mother'(모펀드 룩스루)와 'fund' 중 실린 비중이 큰 쪽을 씀(미래에셋은 fund = 모펀드별 비중 100%) — 단 행이 전부 제외 자산군인 level은
    다른 level이 있으면 건너뜀(2026-10-10 수정). 같은 표에 두 번 나온 종목은 큰 값.
    자산군: holding_class_map_20261009.csv(종목명 → KR_EQ·US_EQ·DM_EXUS_EQ·EM_EQ·GLOBAL_EQ·KR_BD·GLOBAL_BD·CASH·ALT·MIXED·OTHER_NONASSET, 환헤지 H/UH/unknown).
    10차 감사 반영: ① 원화 상장 해외 ETF(KODEX·TIGER·ACE… 이름에 (H) 없음)는 hedge='KRW'(외화자산이 아니라 펀드 환헤지 대상이 아님 → 항상 비헤지)
    ② 금(ACE 금현물·iShares Gold)은 cls='GOLD'로 금 가격(USD)×환율 대용(ACE 금현물은 'KRW'), 맥쿼리인프라(코스피 상장 주식)는 KR_EQ
    ③ 나머지 대체·혼합·비자산(리츠·글로벌 부동산·혼합형 모펀드·미수금)은 대응 수익률이 없어 빼고 재정규화(빠진 비중 excluded 열).
    GLOBAL_EQ는 ACWI_SPLIT로 나눔. -> long [code, period_end, cls, hedge, krw_listed, w, covered, excluded]."""
    d = paths.FUND_TDF / "mgmt_reports"
    h = pd.read_csv(d / "holdings_20261009.csv"); m = pd.read_csv(d / "holding_class_map_20261009.csv")
    h = h[h["level"].isin(["fund", "mother"])].merge(m[["holding_name", "asset_class", "fx_hedge"]], on="holding_name", how="left")
    h = h.groupby(["code", "period_end", "level", "holding_name", "asset_class", "fx_hedge"], dropna=False)["weight_pct"].max().reset_index()
    nm = h["holding_name"].astype(str)
    gold = (h["asset_class"] == "ALT") & nm.str.contains("금현물|GOLD", case=False)
    h.loc[gold, "asset_class"] = "GOLD"
    h.loc[nm.str.contains("맥쿼리인프라"), "asset_class"] = "KR_EQ"
    drop = ["ALT", "MIXED", "OTHER_NONASSET"]
    # level 선택: 쓸 수 있는 행(제외 자산군·미분류 아님)이 하나라도 있는 level 중 실린 비중 최대. 전부 제외뿐인 level(파싱 잔재 등)은
    # 다른 level이 있으면 고르지 않음(한국투자 2050 2022-06~2023-06 fund 레벨 'MIXED 100' 1행 → mother 정상 10종목, 주제1 실현가능성 감사 M1).
    cov = h.assign(ok=~h["asset_class"].isin(drop) & h["asset_class"].notna()).groupby(["code", "period_end", "level"]).agg(weight_pct=("weight_pct", "sum"), ok=("ok", "any")).reset_index()
    best = cov.sort_values(["ok", "weight_pct"]).groupby(["code", "period_end"]).tail(1)
    h = h.merge(best[["code", "period_end", "level"]], on=["code", "period_end", "level"])
    nm = h["holding_name"].astype(str)
    krw = nm.str.match(KRW_ETF) & ~nm.str.contains(r"\(H\)") & h["asset_class"].isin(["US_EQ", "DM_EXUS_EQ", "EM_EQ", "GLOBAL_EQ", "GLOBAL_BD", "GOLD"])
    h.loc[krw, "fx_hedge"] = "KRW"
    h["krw_listed"] = nm.str.match(KRW_ETF) | nm.str.contains("금현물")                            # 원화 상장(통화별 표에서 원화로 잡힘; (H) 포함) — 12차 감사
    rows = []
    for (c, pe), g in h.groupby(["code", "period_end"]):
        tot = g["weight_pct"].sum(); exc = g.loc[g["asset_class"].isin(drop) | g["asset_class"].isna(), "weight_pct"].sum()
        g = g[~g["asset_class"].isin(drop) & g["asset_class"].notna()]
        for _, r in g.iterrows():
            fh = r["fx_hedge"]
            hed = fh if fh in ("H", "UH", "KRW") else ("NA" if (pd.isna(fh) or fh == "NA") else "unknown")
            parts = ACWI_SPLIT.items() if r["asset_class"] == "GLOBAL_EQ" else [(r["asset_class"], 1.0)]
            for cls, sh in parts:
                rows.append({"code": c, "period_end": pd.Timestamp(str(int(pe))), "cls": cls, "hedge": hed, "krw_listed": bool(r["krw_listed"]), "w": r["weight_pct"] * sh, "covered": tot, "excluded": exc})
    out = pd.DataFrame(rows)
    out["w"] = out["w"] / out.groupby(["code", "period_end"])["w"].transform("sum")
    return out


def gold_monthly_usd() -> pd.Series:
    """금 USD 종가(raw/commodity/gold_long.xlsx, 2000-08~) 월말 수익률(월말 정규화 인덱스). 원화 비헤지 = (1+이것)(1+환율변화)−1."""
    g = pd.read_excel(paths.COMMODITY / "gold_long.xlsx", parse_dates=["date"]).set_index("date")["gold_usd_close"].dropna()
    g = g.resample("ME").last().pct_change().dropna(); g.index = g.index.normalize()
    return g


def pooled_paths(panel: dict, cols: list, n: int, T: int, mean_block: float, seed: int) -> list:
    """Anarkulova·Cederburg·O'Doherty(PDF17) 풀링 stationary bootstrap: 시작점 = 전체 나라-월 관측에서 균등 추출(관측 수 비례),
    블록 길이 기하분포(평균 mean_block), 조각 끝에 닿으면 '무작위 조각의 처음'으로 이어감. 반환: cols 순서의 (n,T) 배열 목록."""
    arrs = [df[cols].to_numpy(float) for df in panel.values()]; lens = np.array([len(a) for a in arrs])
    flat = np.concatenate(arrs); off = np.r_[0, np.cumsum(lens)[:-1]]; ends = off + lens; N = len(flat)
    seg_of = np.repeat(np.arange(len(arrs)), lens)
    rng = np.random.default_rng(seed); p = 1 / mean_block
    pos = np.empty((n, T), dtype=np.int64); g = rng.integers(N, size=n)
    for t in range(T):
        if t > 0:
            new = rng.random(n) < p
            nxt = g + 1; over = nxt >= ends[seg_of[g]]
            g = np.where(new, rng.integers(N, size=n), np.where(over, off[rng.integers(len(arrs), size=n)], nxt))
        pos[:, t] = g
    out = flat[pos]
    return [out[:, :, k] for k in range(len(cols))]


def samples(us_col: bool = False) -> dict:
    """표본 묶음: 기본(KR 2004~, CPI 없는 부분월 제외), 확장(KR 1991~), 미국(US 1965~ 월말 종가, USD — 한국 세제·금리를 미국 수익률에 적용한 반사실 ⚠). us_col=True면 'us' 열 있는 표본만."""
    out = {"KR 2004~": monthly().dropna(subset=["infl"]), "KR 1991~": monthly_kr_long()}
    if not us_col:
        out["US 1965~"] = monthly_us_long()
    return out


def mc_se(p, n: int):
    """부트스트랩 확률의 몬테카를로 표준오차 √(p(1−p)/n)."""
    return np.sqrt(np.asarray(p, float) * (1 - np.asarray(p, float)) / n)


def hac_t(x) -> dict:
    """평균의 Newey–West HAC t검정(대역폭 floor(4(T/100)^(2/9)), Newey & West 1994 규칙)."""
    import statsmodels.api as sm
    a = np.asarray(pd.Series(x).dropna(), float); T = len(a); L = int(np.floor(4 * (T / 100) ** (2 / 9)))
    f = sm.OLS(a, np.ones(T)).fit(cov_type="HAC", cov_kwds={"maxlags": L})
    return {"mean": float(f.params[0]), "se": float(f.bse[0]), "t": float(f.tvalues[0]), "p": float(f.pvalues[0]), "T": T, "lags": L}


def holm(pvals) -> np.ndarray:
    """Holm(1979) 단계하강 보정 p값."""
    p = np.asarray(pvals, float); o = np.argsort(p); m = len(p)
    adj = np.maximum.accumulate((m - np.arange(m)) * p[o]).clip(max=1.0)
    out = np.empty(m); out[o] = adj
    return out


if __name__ == "__main__":
    ix = lambda n: pd.date_range("2000", periods=n, freq="ME")
    s = pd.Series([0.0, -0.25, -0.01, 0.40, 0.10, -0.15, -0.10, 0.0], index=ix(8))
    assert bear_starts(s) == [s.index[2], s.index[6]], bear_starts(s)          # 2개월 조건·회복 뒤 재무장
    assert bear_starts(pd.Series([-0.25, -0.01, 0.0], index=ix(3))) == [ix(3)[1]]  # 첫 달 급락(시작 1 고점)
    assert bear_starts(pd.Series([], dtype=float)) == []
    rng = np.random.default_rng(0); R = rng.normal(0.005, 0.07, (300, 120))
    fb = first_bear(R)
    for k in range(300):
        b = bear_starts(pd.Series(R[k], index=ix(120)))
        assert (fb[k] == 121) == (not b) and (not b or ix(120).get_loc(b[0]) + 1 == fb[k])
    assert bear_starts(pd.Series([0.0, -0.15, -0.1], index=ix(3))) == [ix(3)[2]]   # 마지막 달 판정도 잡음
    assert abs(drawdown(pd.Series([-0.3, 0.1])).min() + 0.3) < 1e-12
    assert abs(fwd(pd.Series([0.1, 0.2, 0.3], index=ix(3)), 2).iloc[0] - 1.2 * 1.3) < 1e-12
    assert np.allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    pan = {"a": pd.DataFrame({"x": [1., 2, 3]}), "b": pd.DataFrame({"x": [10., 20]})}
    X = pooled_paths(pan, ["x"], 500, 6, 1e9, 1)[0]                            # 블록 무한대: 조각 안에서만 +1, 끝나면 조각 처음으로
    for row in X:
        for u, v in zip(row[:-1], row[1:]):
            assert (v == u + 1 and u not in (3.,)) or (v == u + 10 and u == 10.) or (v in (1., 10.) and u in (3., 20.)), row
    assert abs(par_bond_tr(pd.Series([5.0, 5.0, 5.0], index=ix(3)), 3).iloc[-1] - 0.05 / 12) < 1e-12
    print("pilot7 self-check ok")
