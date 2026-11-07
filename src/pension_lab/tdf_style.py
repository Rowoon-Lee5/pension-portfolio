"""TDF 글라이드 예비테스트 공통 함수(노트북 idea_tdf_glidepath*·idea_tdf_supp가 함께 씀, 2026-09-28 분리).

- load_nav(src): 'raw'(KOFIA 원 기준가) | 'clean_v3'(결산 분배 하락을 KOFIA 전일대비 수익률로 바꾼 정제본)
- panel(nav, lag_mode): 펀드 기준가일에 맞춘 스타일 자산 가격(시차 맞춤·환헤지 carry 포함)
- style(): Sharpe(1992) 제약회귀(비중≥0, 합=1) / monthly·weekly / 공시 글라이드·목표시점
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from . import io, paths, glidepath as gp

MGR = {c: m for m, cs in gp._TDF_CODES.items() for c in cs}
V = pd.Series(gp.CODE2VINTAGE)
ASSETS = ['kr_eq', 'gl_eq_h', 'gl_eq_uh', 'kr_bd', 'gl_bd_h', 'cash']
A10 = ['kr_eq', 'gl_eq_h', 'gl_eq_uh', 'dm_eq_h', 'dm_eq_uh', 'em_eq_h', 'em_eq_uh', 'kr_bd', 'gl_bd_h', 'cash']
# 목표시점: 투자설명서 원문. 미래에셋 = V+1년 1월 1일, 나머지 = V년 1월 1일
TARGET = {c: pd.Timestamp(f'{V[c] + (1 if MGR[c] == "미래에셋" else 0)}-01-01') for c in V.index}


def load_nav(src: str = 'raw') -> pd.DataFrame:
    if src == 'raw':
        return io.load_tdf_nav()
    cl = pd.read_csv(paths.PROCESSED / 'nav_tdf_clean_v3_20260928.csv', usecols=['date', 'fund_code', 'nav_clean'], parse_dates=['date'])
    return cl.pivot_table(index='date', columns='fund_code', values='nav_clean').sort_index()


def on_dates(s, d, lag):
    """자산 자체 영업일 기준 lag일 늦춘 가격을 펀드 기준가일 d에 붙임(휴장일=직전값). lag = 상수 또는 d 인덱스 Series."""
    # 자산 자료가 기준가보다 먼저 끝나면 ffill이 끝 이후 자산 수익을 0으로 채운다 → 조용히 채우지 않고 멈춘다(2026-09-29 shift 점검)
    end = s.dropna().index.max()
    assert end >= d.max(), f'자산 자료 끝 {end.date()} < 기준가 끝 {d.max().date()}: 기준가를 자산 끝까지 잘라서 넣을 것'
    if np.isscalar(lag):
        return s.shift(int(lag)).reindex(s.index.union(d)).ffill().reindex(d)
    out = pd.Series(np.nan, index=d)
    for L in np.unique(lag.values):
        m = lag.values == L
        out[m] = on_dates(s, d, int(L))[m]
    return out


def best_lag(fr, s, absval=False):
    cs = {L: fr.corr(on_dates(s, fr.index, L).pct_change(fill_method=None)) for L in range(4)}
    return max(cs, key=lambda L: abs(cs[L]) if absval else cs[L])


def lag_path(fr, s, mode, absval=False):
    """full: 전기간 1개(사후 정보) / first2y: 첫 504영업일로 1개 고정 / trailing: 매월 직전 252영업일로 선택(과거만; 첫 252일은 첫 창 값)."""
    if mode == 'full':
        return best_lag(fr, s, absval)
    if mode == 'first2y':
        return best_lag(fr.iloc[:505], s, absval)
    d = fr.index
    out = pd.Series(np.nan, index=d)
    first = best_lag(fr.iloc[:253], s, absval)
    for per in pd.PeriodIndex(d, freq='M').unique():
        i0 = d.searchsorted(per.start_time)
        out[(d >= per.start_time) & (d <= per.end_time)] = best_lag(fr.iloc[i0 - 252:i0], s, absval) if i0 >= 253 else first
    return out.astype(int)


def panel(nav: pd.DataFrame, mode: str = 'full'):
    """(PX: 펀드별 가격 패널, LAGP: 시차 경로, lags: 요약표)."""
    raw = {k: io.asset_series(k) for k in ['kr_eq', 'us_eq', 'kr_bd', 'us_agg', 'usdkrw', 'cd91']}
    xtra = {'dm_eq': io.load_csv(paths.EQUITY_GLOBAL / 'global_dev_exus_efa.csv'),
            'em_eq': io.load_csv(paths.EQUITY_GLOBAL / 'global_emerging_eem.csv')}
    tb3 = pd.to_numeric(pd.read_csv(paths.MACRO / 'fred_dtb3.csv', index_col=0, parse_dates=True)['DTB3'], errors='coerce').dropna()
    LAGP, lags, PX = {}, {}, {}
    for c in nav:
        f = nav[c].dropna()
        fr = f.pct_change(fill_method=None)
        L = {'kr': lag_path(fr, raw['kr_eq'], mode), 'us': lag_path(fr, raw['us_eq'], mode), 'fx': lag_path(fr, raw['usdkrw'], mode, True)}
        LAGP[c] = L
        lags[c] = {k: (v if np.isscalar(v) else int(v.mode().iloc[0])) for k, v in L.items()}
        if mode == 'trailing':
            lags[c].update({f'{k}_변경횟수': int((v.diff().fillna(0) != 0).sum()) for k, v in L.items()})
        d = f.index
        us, fx = on_dates(raw['us_eq'], d, L['us']), on_dates(raw['usdkrw'], d, L['fx'])
        out = pd.DataFrame({'kr_eq': on_dates(raw['kr_eq'], d, L['kr']), 'gl_eq_h': us, 'gl_eq_uh': us * fx,
                            'kr_bd': on_dates(raw['kr_bd'], d, L['kr']), 'gl_bd_h': on_dates(raw['us_agg'], d, L['us'])})
        cd = on_dates(raw['cd91'], d, 0)
        dt = pd.Series(d, index=d).diff().dt.days.fillna(0)
        out['cash'] = (1 + cd.shift(1).fillna(cd.iloc[0]) / 100 * dt / 365).cumprod()
        # 환헤지 수익 ≈ 달러 수익 + (CD91 − 미 T-bill 3개월): 커버드 이자율 평형 근사
        carry = (1 + (cd - on_dates(tb3, d, L['us'])).shift(1).fillna(0) / 100 * dt / 365).cumprod()
        out['gl_eq_h0'], out['gl_bd_h0'] = out['gl_eq_h'], out['gl_bd_h']
        out['gl_eq_h'], out['gl_bd_h'] = out['gl_eq_h'] * carry, out['gl_bd_h'] * carry
        for k, s in xtra.items():
            x = on_dates(s, d, L['us'])
            out[f'{k}_h'], out[f'{k}_uh'] = x * carry, x * fx
        out.insert(0, 'fund', f)
        PX[c] = out.dropna()
    lags = pd.DataFrame(lags).T.astype(int)
    lags['manager'] = lags.index.map(MGR)
    lags['vintage'] = V
    return PX, LAGP, lags


def style(y, X):
    """min ||y − Xw||²  s.t. w ≥ 0, Σw = 1 (Sharpe 1992 이차계획)."""
    k = X.shape[1]
    XtX, Xty = X.T @ X, X.T @ y
    res = minimize(lambda w: w @ XtX @ w - 2 * w @ Xty, np.full(k, 1 / k), jac=lambda w: 2 * (XtX @ w - Xty),
                   bounds=[(0, 1)] * k, constraints=({'type': 'eq', 'fun': lambda w: w.sum() - 1, 'jac': lambda w: np.ones(k)},),
                   method='SLSQP', options={'ftol': 1e-12, 'maxiter': 500})
    return res.x


def r2(y, X, w):
    e = y - X @ w
    return 1 - e.var() / y.var()


def _last(p, f):
    x = p.groupby(p.index.to_period(f)).tail(1)
    x.index = x.index.to_period(f)
    return x


def monthly(p):
    return _last(p, 'M').pct_change(fill_method=None).dropna()


def weekly(p):
    return _last(p, 'W-FRI').pct_change(fill_method=None).dropna()


def glide_table() -> pd.DataFrame:
    return pd.read_csv(paths.FUND_TDF / 'glidepath_disclosed_prospectus.csv')


def glide_fn(code, gl=None):
    """운용사별 잔여연수 곡선(빈티지 공통, ±1%p). 공시 범위 밖은 양끝 값으로 평평하게."""
    gl = glide_table() if gl is None else gl
    g = gl[gl.manager == MGR[code]].groupby('years_rel_target').risky_pct.mean().sort_index()
    x, y = g.index.values.astype(float), g.values / 100
    return lambda yrs: np.interp(yrs, x, y, left=y[0], right=y[-1])


def yrs_rel(dates, code):
    return (pd.DatetimeIndex(dates) - TARGET[code]).days / 365.25
