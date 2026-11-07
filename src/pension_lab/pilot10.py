"""pilot10 공통 함수 — I1 '하락장에 줄일까·그대로 둘까·더 담을까' (2026-10-17).

명세 = D:\\pension-lab_data\\results\\pilot10_20261017\\I1_cut_hold_add\\SPEC_I1_draft_20261017.md (DL 2026-10-17 'pilot10 I1 명세 확정').
pilot9.py는 고치지 않는다(D 규칙 = pilot9.dd_events·dip_on 그대로 사용).
- 10개월 평균 신호: Faber(2007) PDF 21~22쪽 — 월말 가격 > 10개월 단순평균이면 보유, < 이면 줄임. 같으면 직전 상태 유지(⬜I1-k).
  평균이 없는 처음 n−1개월은 '줄이기 꺼짐'(⬜I1-g). t월 판정 → t+1월 비중(Clare 2017 AAM 14쪽 'subsequent month').
- 금액: 매달 초 납입 → 그 달 수익(D 생성기 wealth와 같은 식).
"""
from __future__ import annotations
import numpy as np

MA_N = 10


def ma_below(price_ret, n: int = MA_N) -> np.ndarray:
    """월 수익(… , 개월) → '평균 아래' 상태(bool, 같은 모양). 지수 = 누적곱, 평균 = 그 달 포함 n개월 단순평균."""
    r = np.atleast_2d(np.asarray(price_ret, float)); P = np.cumprod(1 + r, axis=1)
    c = np.cumsum(P, axis=1); S = np.full_like(P, np.nan)
    S[:, n - 1] = c[:, n - 1] / n; S[:, n:] = (c[:, n:] - c[:, :-n]) / n
    st = np.zeros(P.shape, bool); prev = np.zeros(P.shape[0], bool)
    for t in range(n - 1, P.shape[1]):
        prev = np.where(P[:, t] < S[:, t], True, np.where(P[:, t] > S[:, t], False, prev)); st[:, t] = prev
    return st.reshape(np.shape(price_ret))


def ma_ties(price_ret, n: int = MA_N) -> int:
    """가격 = 평균인 달 수(⬜I1-k 영향 점검)."""
    r = np.atleast_2d(np.asarray(price_ret, float)); P = np.cumprod(1 + r, axis=1); c = np.cumsum(P, axis=1)
    S = (c[:, n - 1:] - np.c_[np.zeros(len(P)), c[:, :-n]]) / n
    return int((P[:, n - 1:] == S).sum())


def lag1(state) -> np.ndarray:
    """t월 상태 → t+1월 켜짐(첫 달 False)."""
    s = np.asarray(state, bool); on = np.zeros_like(s); on[..., 1:] = s[..., :-1]
    return on


def switches(on) -> np.ndarray:
    """경로별 켜짐↔꺼짐 전환 횟수(마지막 축 = 개월)."""
    o = np.asarray(on, np.int8)
    return np.abs(np.diff(o, axis=-1)).sum(-1)


def arm_return(G, on, delta, SK, BD, f, CASH=None, full=False):
    """(개월, 경로) 월 수익과 위험자산 비중(클립 전 raw 포함).
    w = clip(G + delta·on, 0, 1). CASH 없으면 나머지 전부 국채(D와 같은 식), 있으면 옮긴 몫(G − w)만 현금.
    full=True: Faber 원형(켜지면 위험자산 전부 → 현금, w = G·(1 − on))."""
    G = np.asarray(G, float)[:, None]
    raw = G * (1 - on) if full else G + delta * on
    w = np.minimum(np.maximum(raw, 0.0), 1.0)
    R = w * SK + (1 - w) * BD - f[:, None] if CASH is None else w * SK + (1 - G) * BD + (G - w) * CASH - f[:, None]
    return R, raw


def wealth(Rt, c) -> np.ndarray:
    """Rt (개월, 경로), c 월 납입 → 마지막 달 말 잔액(명목)."""
    V = np.zeros(Rt.shape[1])
    for k in range(Rt.shape[0]):
        V = (V + c[k]) * (1 + Rt[k])
    return V


def cvar5(x) -> float:
    """자기 하위 5% 경로 평균(N = 10,000 → 500개)."""
    return float(np.sort(x)[:int(round(0.05 * len(x)))].mean())


def dist(d) -> dict:
    """로그비 d의 기술 지표(경로 범위, 신뢰구간 아님)."""
    d = np.asarray(d)
    return dict(d_중앙=float(np.median(d)), d_P5=float(np.quantile(d, .05)), d_P95=float(np.quantile(d, .95)),
                P_d양수=float((d > 0).mean()), P_d영=float((d == 0).mean()))
