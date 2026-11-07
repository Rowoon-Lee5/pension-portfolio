"""공개판 발췌: 원본 `fetch/kofia_h_uh_nav.py`(공개 범위 밖 주제의 수집 코드)에서 `_segF`와 `TICK`만 남겼다.

`01_downturn_timing/notebooks/pilot9/_build_C_real_inputs.py`가 `_segF`만 import한다(분배 조정액 점검용). 식은 원본과 같다.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

TICK = 0.01                      # KOFIA 기준가·전일대비 공시 단위(원, 소수 둘째 자리) — 응답 값에서 확인


def _segF(x, sd):
    """한 코드의 일별 표 x, 결산 반영일 집합 sd → 구간별 F(=v3/Δ기준가, 최소제곱)·표준오차, 잔차, 반올림 한계."""
    sd = list(sd); x = x.copy(); x["seg"] = (x.date.isin(sd) | ~x.cont).cumsum()      # 결산 반영일·공백 뒤 재개일에서 구간을 끊음
    use = x.act2 & ~x.date.isin(sd) & x.v3.notna() & (x.dnav != 0)
    st = x[use].groupby("seg").apply(lambda g: pd.Series(dict(F=(g.v3 * g.dnav).sum() / (g.dnav ** 2).sum(), n=len(g))), include_groups=False)
    if len(st):
        res = x[use].v3 - x[use].seg.map(st.F) * x[use].dnav
        st["seF"] = (res ** 2).groupby(x[use].seg).sum().div((st.n - 1).clip(lower=1)).pow(0.5) / x[use].dnav.pow(2).groupby(x[use].seg).sum().pow(0.5)
    else:
        st = pd.DataFrame(columns=["F", "n", "seF"])
    x["F"] = x.seg.map(st.F); x["seF"] = x.seg.map(st.seF)
    x["F_before"] = np.where(x.date.isin(sd), (x.seg - 1).map(st.F), x.F)
    x["seF_before"] = np.where(x.date.isin(sd), (x.seg - 1).map(st.seF), x.seF)
    x["resid"] = x.v3 - x.F_before * x.dnav
    x["bound"] = 0.5 * TICK + TICK * x.F_before + x.seF_before * x.dnav.abs()   # v3 반올림 ±0.005 + 두 기준가 반올림 ±0.01·F + F 추정 표준오차 1배
    x["event"] = x.act2 & x.v3.notna() & (x.resid.abs() > x.bound)
    x["adj_norm"] = x.resid / x.F_before
    return x
