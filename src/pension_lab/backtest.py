"""백테스트 엔진 — 거래비용·리밸런싱·지표를 한 곳에.

⚠룩어헤드 금지: 가중치는 항상 전일까지 정보로 결정(weights.shift(1) 강제).
수익률 index/시계열은 pct_change 기반. 세금·거래비용은 명시 인자.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .bootstrap import mdd_from_returns

TRADING_DAYS = 252


def to_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    return prices.pct_change()


def portfolio_returns(asset_rets: pd.DataFrame, weights: pd.DataFrame,
                      cost_bps: float = 0.0) -> pd.Series:
    """가중 포트폴리오 일수익률.

    asset_rets : (date x asset) 일수익률
    weights    : (date x asset) 목표비중 — **당일 수익 실현 전에 정해진 값**
                 룩어헤드 방지 위해 내부에서 shift(1) 적용(전일 비중으로 당일수익).
    cost_bps   : 비중변경분(turnover)에 부과하는 편도 거래비용(bps).
    """
    w = weights.reindex(asset_rets.index).ffill()
    w_eff = w.shift(1)                      # 전일 비중으로 당일 수익 (룩어헤드 차단)
    gross = (w_eff * asset_rets).sum(axis=1, min_count=1)   # 첫행(비중 전부 NaN)=NaN 유지, 가짜 0 방지
    if cost_bps:
        # 비용은 '실제 보유비중'(w_eff)이 바뀌는 날에 부과. **편도 회전율=0.5·Σ|Δw|**
        # (완전투자 Σw=1 가정: 판 만큼 사므로 실거래 notional=매도측=0.5·Σ|Δw|). cost_bps=편도.
        turnover = 0.5 * (w_eff - w_eff.shift(1)).abs().sum(axis=1).fillna(0.0)
        gross = gross - turnover * (cost_bps / 1e4)
    return gross.rename("port_ret")


def to_index(returns: pd.Series, base: float = 100.0) -> pd.Series:
    return base * (1.0 + returns.fillna(0.0)).cumprod()


def max_drawdown(index: pd.Series) -> float:
    roll_max = index.cummax()
    return float((index / roll_max - 1.0).min())


def cagr(index: pd.Series) -> float:
    yrs = (index.index[-1] - index.index[0]).days / 365.25
    if yrs <= 0:
        return float("nan")
    return float((index.iloc[-1] / index.iloc[0]) ** (1 / yrs) - 1)


def ann_vol(returns: pd.Series) -> float:
    return float(returns.std() * np.sqrt(TRADING_DAYS))


def sharpe(returns: pd.Series, rf_annual: float = 0.0) -> float:
    excess = returns - rf_annual / TRADING_DAYS
    sd = returns.std()
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float(excess.mean() / sd * np.sqrt(TRADING_DAYS))


def metrics(returns: pd.Series, rf_annual: float = 0.0) -> dict:
    idx = to_index(returns)
    return {
        "cagr": cagr(idx),
        "ann_vol": ann_vol(returns),
        "sharpe": sharpe(returns, rf_annual),
        "mdd": mdd_from_returns(returns.dropna().to_numpy(float)),   # 수익률기반(첫날락폭 포함·index 앵커 함정 회피)
        "start": str(idx.index.min().date()),
        "end": str(idx.index.max().date()),
        "n": int(returns.notna().sum()),
    }
