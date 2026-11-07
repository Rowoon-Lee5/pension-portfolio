"""성과 통계검정 — Ledoit-Wolf(2008) Sharpe차 검정 (SOURCES J5).

왜? 두 전략의 Sharpe가 "우연히" 다를 수도 있다. 표본이 짧고 수익률이
자기상관·두꺼운꼬리라 단순 t검정은 과신한다. Ledoit & Wolf(2008,
"Robust performance hypothesis testing with the Sharpe ratio", J.Empirical
Finance 15:850)는 **HAC(자기상관·이분산 보정) 표준오차 + studentized
circular block bootstrap**으로 Sharpe차의 견고한 양측 p값을 준다.

방법(원논문 그대로):
  - Δ = SR1 − SR2 (Sharpe는 μ/σ, σ=하방아닌 표준편차).
  - 모멘트 벡터 y_t=[r1−μ1, r2−μ2, r1²−γ1, r2²−γ2] (γ=E[r²]).
  - Δ의 표준오차 = √(∇f' Ψ ∇f / T), Ψ=Bartlett 커널 HAC 장기공분산,
    ∇f=Δ의 (μ1,μ2,γ1,γ2)에 대한 델타법 기울기
    (∂SR/∂μ=γ/(γ−μ²)^{3/2}, ∂SR/∂γ=−μ/(2(γ−μ²)^{3/2})).
  - p값: 블록부트스트랩 표본마다 studentized t*=(Δ*−Δ̂)/SE*,
    p=(#{|t*|≥|t̂|}+1)/(B+1). (studentize가 부트스트랩 정합성의 핵심.)

⛔주의: 연율화(×√252)는 Δ·SE에 같은 상수라 **t통계량·p값 불변**. 초과Sharpe가
필요하면 **초과수익률(r−rf)** 을 넣어라(함수는 넣은 시계열로 그대로 계산).
재현성: seed 고정(circular block bootstrap). 짝지은 비교(같은 리샘플 아님)가 아니라
두 시계열을 **함께 같은 블록인덱스로** 리샘플(동시성 보존).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _sharpe(x: np.ndarray) -> float:
    """일별 Sharpe(연율 아님): mean/std(ddof=1)."""
    sd = x.std(ddof=1)
    return float(x.mean() / sd) if sd > 0 else float("nan")


def _hac_bandwidth(T: int) -> int:
    """Newey-West(1994) 플러그인 대역폭 근사 S=⌊4(T/100)^{2/9}⌋ (≥1)."""
    return max(1, int(np.floor(4.0 * (T / 100.0) ** (2.0 / 9.0))))


def _diff_se(r1: np.ndarray, r2: np.ndarray, bandwidth: int | None) -> tuple[float, float, float, float]:
    """(Δ=SR1−SR2, HAC SE(Δ), SR1, SR2) — 일별 스케일. Ledoit-Wolf 델타법+Bartlett HAC."""
    T = len(r1)
    m1, m2 = r1.mean(), r2.mean()
    g1, g2 = np.mean(r1 ** 2), np.mean(r2 ** 2)
    D1, D2 = g1 - m1 ** 2, g2 - m2 ** 2               # 분산(=σ²)
    if D1 <= 0 or D2 <= 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    sr1, sr2 = m1 / np.sqrt(D1), m2 / np.sqrt(D2)
    diff = sr1 - sr2
    # ∇f: [∂/∂μ1, ∂/∂μ2, ∂/∂γ1, ∂/∂γ2]
    grad = np.array([
        g1 / D1 ** 1.5,
        -g2 / D2 ** 1.5,
        -m1 / (2.0 * D1 ** 1.5),
        m2 / (2.0 * D2 ** 1.5),
    ])
    # 모멘트 편차 (T x 4)
    y = np.column_stack([r1 - m1, r2 - m2, r1 ** 2 - g1, r2 ** 2 - g2])
    S = _hac_bandwidth(T) if bandwidth is None else max(0, int(bandwidth))
    psi = (y.T @ y) / T                               # Γ0
    for j in range(1, min(S, T - 1) + 1):
        gj = (y[j:].T @ y[:-j]) / T                   # Γj
        w = 1.0 - j / (S + 1.0)                       # Bartlett
        psi += w * (gj + gj.T)
    var = float(grad @ psi @ grad) / T
    se = float(np.sqrt(var)) if var > 0 else float("nan")
    return float(diff), se, float(sr1), float(sr2)


def _circular_block_idx(T: int, L: int, rng: np.random.Generator) -> np.ndarray:
    """길이 T circular block bootstrap 인덱스 (블록길이 L, 순환 wrap)."""
    nb = int(np.ceil(T / L))
    starts = rng.integers(0, T, size=nb)
    idx = (starts[:, None] + np.arange(L)[None, :]).ravel() % T
    return idx[:T]


def sharpe_diff_test(ret1, ret2, block_size: int = 20, n_boot: int = 999,
                     seed: int = 0, bandwidth: int | None = None,
                     annualize: bool = True) -> dict:
    """Ledoit-Wolf(2008) Sharpe차 검정. H0: SR(ret1)=SR(ret2).

    ret1, ret2 : 일수익률(초과Sharpe면 각자 rf 뺀 초과수익률을 넣을 것). 날짜교집합 자동정렬.
    block_size : circular block 길이(일). 일별 자기상관 보존(기본 20≈1개월).
    n_boot     : 부트스트랩 반복수. p=(#{|t*|≥|t̂|}+1)/(B+1).
    bandwidth  : HAC Bartlett 대역폭(None=Newey-West 자동).
    annualize  : 보고용 sharpe/diff/se를 ×√252 (t통계량·p값은 불변).

    반환 dict: sharpe1, sharpe2, diff, se, tstat, pvalue, n, n_boot, block_size.
    """
    s1, s2 = pd.Series(ret1).dropna(), pd.Series(ret2).dropna()
    common = s1.index.intersection(s2.index)
    a = s1.reindex(common).to_numpy(float)
    b = s2.reindex(common).to_numpy(float)
    T = len(a)
    if T < 30:
        raise ValueError(f"표본부족: 공통 {T} < 30")
    diff, se, sr1, sr2 = _diff_se(a, b, bandwidth)
    sc = np.sqrt(TRADING_DAYS) if annualize else 1.0
    if not np.isfinite(se) or se == 0:
        # 엣지케이스(F6): 동일(또는 사실상 동일) 시계열 → Δ=0, HAC SE=0(선형결합이 항등적 0).
        #   검정이 불가한 게 아니라 "차이 없음"이 정답이므로 ValueError 대신 p=1.0·t=0 반환.
        #   Δ≠0인데 SE=0 = 진짜 비정상(퇴화)일 때만 오류.
        if np.isfinite(diff) and abs(diff) < 1e-12:
            return {
                "sharpe1": (sr1 * sc if np.isfinite(sr1) else float("nan")),
                "sharpe2": (sr2 * sc if np.isfinite(sr2) else float("nan")),
                "diff": 0.0, "se": 0.0, "tstat": 0.0, "pvalue": 1.0,
                "n": int(T), "n_boot": int(n_boot), "block_size": int(block_size),
            }
        raise ValueError("SE 산출 불가(분산 0 또는 비정상)")
    t_hat = diff / se
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_boot):
        idx = _circular_block_idx(T, block_size, rng)
        d_b, se_b, _, _ = _diff_se(a[idx], b[idx], bandwidth)
        if np.isfinite(se_b) and se_b > 0:
            t_b = (d_b - diff) / se_b
            if abs(t_b) >= abs(t_hat):
                count += 1
    pval = (count + 1) / (n_boot + 1)
    return {
        "sharpe1": sr1 * sc, "sharpe2": sr2 * sc,
        "diff": diff * sc, "se": se * sc, "tstat": float(t_hat),
        "pvalue": float(pval), "n": int(T), "n_boot": int(n_boot),
        "block_size": int(block_size),
    }


if __name__ == "__main__":  # 자기검증
    idx = pd.bdate_range("2005-01-03", periods=1500)
    # 1) 보정(calibration): H0참(동일분포·독립) 반복 → 5% 기각률 ≈ 5%여야(과신 없음).
    #    단일 draw는 우연히 극단일 수 있으니 반복 기각률로 검증(개별 p는 우연 outlier 정상).
    reps, rej = 40, 0
    for k in range(reps):
        rr = np.random.default_rng(2000 + k)
        x = pd.Series(rr.normal(0.0004, 0.01, 1500), index=idx)
        y = pd.Series(rr.normal(0.0004, 0.01, 1500), index=idx)
        if sharpe_diff_test(x, y, n_boot=199, seed=k)["pvalue"] < 0.05:
            rej += 1
    rate = rej / reps
    assert rate <= 0.20, f"H0 기각률 과다(과신): {rate:.2f} (이상적 0.05)"
    # 2) 검정력: 뚜렷이 다른 Sharpe(강한 양드리프트 vs 음드리프트·고변동) → p 작아야
    rng = np.random.default_rng(0)
    hi = pd.Series(rng.normal(0.0010, 0.008, 1500), index=idx)
    lo = pd.Series(rng.normal(-0.0002, 0.020, 1500), index=idx)
    r_diff = sharpe_diff_test(hi, lo, n_boot=499, seed=1)
    assert r_diff["pvalue"] < 0.05, f"명백히 다른데 p큼 {r_diff['pvalue']}"
    assert r_diff["diff"] > 0, "고Sharpe−저Sharpe>0 아님"
    # 3) 결정성
    a = sharpe_diff_test(hi, lo, n_boot=299, seed=7)
    b = sharpe_diff_test(hi, lo, n_boot=299, seed=7)
    assert a == b, "비결정적"
    print("OK perfstats | H0 기각률 %.2f (≈0.05 목표) | 검정력 p=%.4f (Δ=%.2f, t=%.2f)"
          % (rate, r_diff["pvalue"], r_diff["diff"], r_diff["tstat"]))
