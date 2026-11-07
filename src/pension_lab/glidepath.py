"""합성 TDF (글라이드패스). notebooks/synthetic_tdf.ipynb 의 로직 모듈화.

기본값=감사확정(스타일분석 실측 EMPIRICAL_EQUITY·채권100국내·보수0.85·헤지, docs/가정_전수조사.md·DECISION_LOG).
   레벨 정밀매칭엔 지도교수와 캘리브레이션 필요(월간상관 0.87~0.89=방향성 검증). empirical=False 경로(공식 글라이드)는 미사용.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from . import io
from .backtest import TRADING_DAYS


# 스타일분석(Sharpe 1992)으로 실제 KOFIA TDF NAV서 역추정한 빈티지별 주식비중.
# 2025=39%는 KB 공시 39%와 일치(검증). 2055는 데이터 짧아 노이즈.
# 상세: docs/가정_전수조사.md
EMPIRICAL_EQUITY = {2025: 0.39, 2030: 0.51, 2035: 0.58, 2040: 0.63,
                    2045: 0.69, 2050: 0.86, 2055: 0.69}

# KOFIA TDF 35펀드 표준코드 → 빈티지. 5개 운용사 × 빈티지(2025~2055) 순서.
_TDF_CODES = {
    "미래에셋": ["K55301BM7939", "K55301BM7681", "K55301BM7582", "K55301BM7400", "K55301BM7509", "K55301D51180", "K55301EB2732"],
    "삼성":     ["K55105BC8937", "K55105BC8648", "K55105BC8515", "K55105BC8390", "K55105BC7780", "K55105CK1519", "K55105CX9376"],
    "KB":       ["K55223BT0833", "K55223BT0999", "K55223BT1146", "K55223BT1351", "K55223BT1617", "K55223BT1807", "K55223D26691"],
    "한국투자": ["K55101BK8584", "K55101BK7347", "K55101BK7461", "K55101BK6919", "K55101BK7040", "K55101CU1578", "K55101DR6324"],
    "신한":     ["K55210BR6233", "K55210BR6365", "K55210BR6498", "K55210BR6621", "K55210BR6753", "K55210CO3752", "K55210DT9688"],
}
CODE2VINTAGE = {c: v for codes in _TDF_CODES.values()
                for c, v in zip(codes, range(2025, 2056, 5))}


@dataclass
class GlideConfig:
    # ▼ 기본값 = 리서치/데이터 기반(docs/가정_전수조사.md). 교수 확정 시 조정.
    eq_floor: float = 0.39          # 목표시점 주식비중 하한 (KB 2025=39%·스타일분석 39%)
    eq_cap: float = 0.80            # 초기 주식비중 상한 (KB 2060=79%)
    eq_slope: float = 0.0125        # 잔존연수 1년당 증가(공식 사용 시). empirical=True면 무시
    eq_kr: float = 0.35             # 주식 내 국내 (스타일분석 ~35/65)
    eq_us: float = 0.65             # 주식 내 해외
    bd_kr: float = 1.00             # 채권 내 국내 (스타일분석: 실제 TDF 채권 거의 100% 국내)
    bd_us: float = 0.00             # 채권 내 해외
    fee_annual: float = 0.0085      # 합성총보수/년 (자배형 평균 0.83%, 액티브~1.05%)
    hedge_foreign: bool = True      # 민감도분석: 헤지형이 실제 KOFIA TDF에 더 가까움(상관0.86>0.83, 7/7빈티지). 단 H/UH 혼재라 시사수준. docs/민감도_헤지_블록.md
    empirical: bool = True          # True=EMPIRICAL_EQUITY 사용(권장), False=공식 글라이드
    vintages: tuple = (2025, 2030, 2035, 2040, 2045, 2050, 2055)


def equity_weight(years_to_target: np.ndarray, cfg: GlideConfig) -> np.ndarray:
    return np.clip(cfg.eq_floor + cfg.eq_slope * years_to_target, cfg.eq_floor, cfg.eq_cap)


def _krw_convert(foreign_ret: pd.Series, fx_ret: pd.Series, hedge: bool) -> pd.Series:
    if hedge:
        return foreign_ret
    return (1 + foreign_ret) * (1 + fx_ret) - 1


def build(cfg: GlideConfig | None = None) -> pd.DataFrame:
    """빈티지별 합성 TDF 지수(base=100) DataFrame 반환."""
    cfg = cfg or GlideConfig()
    kr_eq = io.asset_series("kr_eq")
    us_eq = io.asset_series("us_eq")
    kr_bd = io.asset_series("kr_bd")
    us_bd = io.asset_series("us_bd_mid")
    fx = io.asset_series("usdkrw")
    px = pd.concat({"kr_eq": kr_eq, "us_eq": us_eq, "kr_bd": kr_bd, "us_bd": us_bd, "fx": fx},
                   axis=1).sort_index().ffill().dropna()
    r = px.pct_change()
    ret = pd.DataFrame({
        "kr_eq": r["kr_eq"],
        "us_eq": _krw_convert(r["us_eq"], r["fx"], cfg.hedge_foreign),
        "kr_bd": r["kr_bd"],
        "us_bd": _krw_convert(r["us_bd"], r["fx"], cfg.hedge_foreign),
    }).dropna()
    fee = cfg.fee_annual / TRADING_DAYS
    out = {}
    for V in cfg.vintages:
        if cfg.empirical and V in EMPIRICAL_EQUITY:
            ew = np.full(len(ret), EMPIRICAL_EQUITY[V])   # 실측 고정비중(스타일분석)
        else:
            yrs = V - (ret.index.year + (ret.index.dayofyear - 1) / 365.25)
            ew = equity_weight(yrs, cfg)
        port = (ew * cfg.eq_kr * ret["kr_eq"] + ew * cfg.eq_us * ret["us_eq"]
                + (1 - ew) * cfg.bd_kr * ret["kr_bd"] + (1 - ew) * cfg.bd_us * ret["us_bd"] - fee)
        out[V] = 100 * (1 + port).cumprod()
    return pd.DataFrame(out)


def validate_against_actual(syn: pd.DataFrame, code2vintage: dict = CODE2VINTAGE) -> pd.DataFrame:
    """합성 vs 실제 KOFIA(빈티지 평균) 월간상관·추적오차·누적 비교표."""
    nav = io.load_tdf_nav()
    act = {}
    for code, V in code2vintage.items():
        if code not in nav.columns:
            continue
        act.setdefault(V, []).append(code)
    rows = []
    for V, codes in sorted(act.items()):
        # 펀드별 출시일이 달라 '레벨 평균'은 신규펀드 편입시 불연속(가짜수익) 발생 →
        # 매일 '가용 펀드 수익률'을 평균(NaN=미출시 자동제외)한 뒤 누적.
        comp_ret = nav[codes].dropna(how="all").pct_change().mean(axis=1)
        a = (100 * (1 + comp_ret.fillna(0.0)).cumprod()).dropna()
        if V not in syn.columns:
            continue
        s = syn[V].dropna()
        c = a.index.intersection(s.index)
        if len(c) < 200:
            continue
        a2, s2 = a.reindex(c), s.reindex(c)
        am = a2.resample("ME").last().pct_change().dropna()
        sm = s2.resample("ME").last().pct_change().dropna()
        jm = am.index.intersection(sm.index)
        mcorr = float(np.corrcoef(am.reindex(jm), sm.reindex(jm))[0, 1])
        rows.append({
            "vintage": V, "overlap_start": str(c.min().date()), "n": len(c),
            "monthly_corr": round(mcorr, 2),
            "actual_cum_%": round((a2.iloc[-1] / a2.iloc[0] - 1) * 100),
            "synth_cum_%": round((s2.iloc[-1] / s2.iloc[0] - 1) * 100),
        })
    return pd.DataFrame(rows)
