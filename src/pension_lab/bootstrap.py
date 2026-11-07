"""② 블록 부트스트랩 — 표본 1개(역사 1경로) 문제를 푼다.

왜 필요? 역사수익은 딱 한 번 실현된 경로다. "MDD가 -30%였다"는 우연일 수도.
수익률을 **블록(연속 구간) 단위로 무작위 재조합**해 그럴듯한 대체역사 수천 개를 만들면
MDD·손실(CVaR)·전략우열의 **분포와 신뢰구간**을 얻는다.
블록으로 뽑는 이유: 하루씩 섞으면 변동성 군집·자기상관이 깨진다. 블록은 그걸 보존.

방법: Politis & Romano(1994) stationary bootstrap — 블록길이가 기하분포(평균 mean_block).
재현성: seed 고정(넘파이 Generator). AGENTS.md 시드고정 규칙 준수.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

TRADING_DAYS = 252


# ---------- 통계 함수(수익률 배열 기준) ----------
def mdd_from_returns(r: np.ndarray) -> float:
    """일수익률 배열 → 최대낙폭(MDD, 음수). 시작점 1 포함(첫날 급락도 반영)."""
    idx = np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(r, float))])
    peak = np.maximum.accumulate(idx)
    return float((idx / peak - 1.0).min())


def cagr_from_returns(r: np.ndarray, trading_days: int = TRADING_DAYS) -> float:
    yrs = len(r) / trading_days
    return float(np.prod(1.0 + r) ** (1 / yrs) - 1) if yrs > 0 else float("nan")


def cvar_from_returns(r: np.ndarray, alpha: float = 0.05) -> float:
    """하위 alpha 평균손실(Expected Shortfall). 음수일수록 나쁨."""
    q = np.quantile(r, alpha)
    tail = r[r <= q]
    return float(tail.mean()) if len(tail) else float(q)


# ---------- stationary bootstrap ----------
def _stationary_indices(n: int, mean_block: float, length: int, rng: np.random.Generator) -> np.ndarray:
    """길이 length 의 인덱스 경로 생성. 매 스텝 확률 p=1/mean_block 로 새 시작점,
    아니면 직전+1(순환). 기하분포 블록 = stationary bootstrap."""
    p = 1.0 / mean_block
    idx = np.empty(length, dtype=np.int64)
    cur = rng.integers(0, n)
    for t in range(length):
        if t == 0 or rng.random() < p:
            cur = rng.integers(0, n)
        else:
            cur = (cur + 1) % n
        idx[t] = cur
    return idx


def resample_paths(returns, n_paths: int, mean_block: float = 20.0,
                   horizon: int | None = None, seed: int = 42) -> np.ndarray:
    """(n_paths, horizon) 부트스트랩 수익률 경로. horizon 미지정=원자료 길이."""
    r = np.asarray(pd.Series(returns).dropna(), dtype=float)
    n = len(r)
    H = horizon or n
    rng = np.random.default_rng(seed)
    out = np.empty((n_paths, H), dtype=float)
    for i in range(n_paths):
        out[i] = r[_stationary_indices(n, mean_block, H, rng)]
    return out


def bootstrap_distribution(returns, stat_fn, n_paths: int = 2000, mean_block: float = 20.0,
                           horizon: int | None = None, seed: int = 42) -> np.ndarray:
    """각 부트스트랩 경로에 stat_fn(경로수익률)→통계량 표본 배열."""
    paths = resample_paths(returns, n_paths, mean_block, horizon, seed)
    return np.array([stat_fn(p) for p in paths])


def paired_bootstrap_diff(ret_a, ret_b, stat_fn, n_paths: int = 2000, mean_block: float = 20.0,
                          horizon: int | None = None, seed: int = 42) -> np.ndarray:
    """두 전략 A,B에 **같은 리샘플 인덱스**를 적용해 stat(A)-stat(B) 분포.
    (같은 대체역사에서 비교해야 우열이 공정 — 전략비교의 핵심)."""
    # 날짜 교집합으로 정렬(위치정렬 금지 — 결측일 패턴 다르면 비동시 날짜가 짝지어짐)
    sa, sb = pd.Series(ret_a).dropna(), pd.Series(ret_b).dropna()
    common = sa.index.intersection(sb.index)
    a = sa.reindex(common).to_numpy(float)
    b = sb.reindex(common).to_numpy(float)
    m = len(a)
    H = horizon or m
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_paths)
    for i in range(n_paths):
        idx = _stationary_indices(m, mean_block, H, rng)
        diffs[i] = stat_fn(a[idx]) - stat_fn(b[idx])
    return diffs


def paired_resample_paths(returns_list, n_paths: int, horizon: int,
                          mean_block: float = 20.0, seed: int = 42) -> list[np.ndarray]:
    """여러 시계열에 **같은 블록 인덱스**를 적용해 각 시계열의 (n_paths, horizon) 경로배열 리스트.

    왜? 방어 vs 비방어를 **같은 대체역사(같은 리샘플 인덱스)** 위에서 비교해야 우열·차이가 공정.
    paired_bootstrap_diff는 stat 차이만 주지만, 생애주기 flip은 경로별 최종부·MDD의 **분포 자체**가
    필요하므로 raw 경로를 돌려준다. 모든 입력 시계열은 **공통 날짜 교집합**으로 정렬(위치정렬 금지).
    반환: returns_list와 같은 순서의 np.ndarray 리스트(각 shape=(n_paths, horizon)).
    """
    series = [pd.Series(r).dropna() for r in returns_list]
    common = series[0].index
    for s in series[1:]:
        common = common.intersection(s.index)
    arrs = [s.reindex(common).to_numpy(float) for s in series]
    m = len(common)
    if m < 2:
        raise ValueError(f"공통 표본부족: {m}")
    rng = np.random.default_rng(seed)
    outs = [np.empty((n_paths, horizon), dtype=float) for _ in arrs]
    for i in range(n_paths):
        idx = _stationary_indices(m, mean_block, horizon, rng)
        for k, a in enumerate(arrs):
            outs[k][i] = a[idx]
    return outs


def ci(samples: np.ndarray, level: float = 0.95) -> tuple[float, float]:
    lo = (1 - level) / 2
    return float(np.quantile(samples, lo)), float(np.quantile(samples, 1 - lo))


def prob_positive(samples: np.ndarray) -> float:
    """차이표본이 0보다 클 확률(예: A의 MDD개선이 B보다 나을 확률)."""
    return float((samples > 0).mean())
