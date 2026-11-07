"""생애주기(잔여기간) flip 분석 코어 — C주제 Phase2b (SOURCES J9·J11·J12·J16).

C의 노벨티 = **국면방어의 값어치가 잔여 투자기간 h에 따라 부호전환(flip)** 하나
(Guidolin-Timmermann 2007, J9: 최적 주식비중이 국면×horizon에 **비단조**). 이 모듈은
노트북(c_lifecycle_flip)이 쓰는 **순수·검정가능 함수**만 담는다 — 백테스트 배관·부트스트랩
경로생성은 backtest.portfolio_returns·bootstrap.paired_resample_paths 재사용(중복 금지).

담는 것:
  1. CRRA 확실성등가(CEC) — 축적기 말기부 효용(설계 §13 T1, 표준 CRRA 공식·임의상수 없음).
  2. 경로배열(2D) → 최종부·MDD 벡터화(bootstrap.mdd_from_returns 로직과 동일, 행단위).
  3. flip 검출: 값어치(방어−비방어)의 h격자 부호전환점 h* (선형보간) — 단조=flip없음.
  4. h* 부트스트랩 분포 + 표본내/외삽 분류(설계 §14).
  5. 유효 독립창(비겹침) 수 — 22년 표본 정직성(설계 §16·B lifecycle 교훈).

⛔임의값 금지: γ·h격자·블록길이는 호출측(노트북)이 근거와 함께 주입. 여기 함수는 무단위·범용.
"""
from __future__ import annotations
import warnings
import numpy as np


# ----------------------------- CRRA 확실성등가(CEC) -----------------------------
def crra_utility(wealth, gamma: float):
    """CRRA(상대위험회피) 효용 U(W). γ=1이면 log(W), 아니면 W^(1-γ)/(1-γ). W>0 가정.

    표준 정의(교과서·SOURCES J13/J16). 임의 스케일상수 없음. 배열/스칼라 모두 지원.
    """
    w = np.asarray(wealth, dtype=float)
    if np.any(w <= 0):
        raise ValueError("CRRA 효용은 W>0에서만 정의(최종부에 0/음수 존재)")
    if abs(gamma - 1.0) < 1e-12:
        return np.log(w)
    return w ** (1.0 - gamma) / (1.0 - gamma)


def certainty_equivalent(wealth, gamma: float) -> float:
    """최종부 분포 → CRRA **확실성등가 부(CEC)**: 이 분포와 무차별한 '확실한 부'.

    γ≠1: CEC = ( E[W^(1-γ)] )^(1/(1-γ))   (효용역함수)
    γ=1: CEC = exp( E[log W] )              (기하평균)
    성질(검증됨): 상수분포→그 값, 위험회피(γ>0)면 CEC≤E[W](Jensen), γ↑이면 CEC↓.
    """
    w = np.asarray(wealth, dtype=float)
    if w.size == 0:
        return float("nan")
    if np.any(w <= 0):
        raise ValueError("CEC는 W>0에서만 정의(최종부에 0/음수 존재)")
    if abs(gamma - 1.0) < 1e-12:
        return float(np.exp(np.mean(np.log(w))))
    p = 1.0 - gamma
    return float(np.mean(w ** p) ** (1.0 / p))


# --------------------------- 경로배열(2D) 벡터화 지표 ---------------------------
def terminal_wealth_rows(paths) -> np.ndarray:
    """(n_paths, horizon) 일수익 경로배열 → 경로별 최종부(∏(1+r)) 벡터."""
    return np.prod(1.0 + np.asarray(paths, dtype=float), axis=1)


def mdd_rows(paths) -> np.ndarray:
    """(n_paths, horizon) 경로배열 → 경로별 최대낙폭(MDD, 음수) 벡터.

    bootstrap.mdd_from_returns와 동일 로직(시작점 1 포함=첫날 급락 반영)을 행단위 벡터화.
    """
    P = np.asarray(paths, dtype=float)
    idx = np.cumprod(1.0 + P, axis=1)
    idx = np.concatenate([np.ones((P.shape[0], 1)), idx], axis=1)
    peak = np.maximum.accumulate(idx, axis=1)
    return (idx / peak - 1.0).min(axis=1)


# ------------------- 중첩(공유 대체역사) horizon 지표 (수정#2) -------------------
def metrics_by_horizon(paths_by_name: dict, h_grid, trading_days: int = 252) -> dict:
    """**하나의 최대-horizon 경로배열**에서 각 h의 앞 h·td일만 슬라이스해 h별 지표를 낸다(중첩 horizon).

    왜(설계 §14 핵심·수정#2): flip 검출율이 유효하려면 부트스트랩 표본 **행 i의 h-곡선이 '하나의 진짜
    대체역사'** 여야 한다. 예전엔 h마다 **별도** paired_resample_paths(horizon=h·td)를 호출해 행 i가 h별로
    **다른 대체역사**였고, 이후 공통 재표집 인덱스는 **인위적 종속**만 줘 검출율을 왜곡했다. 여기선 호출측이
    max(h)·td 로 **공유 블록인덱스 경로를 1회 생성**(paired_resample_paths, 모든 계열 같은 인덱스) → 각 h는
    그 경로의 **앞 h·td 열만** 취한다. 룩어헤드 없음(각 대체역사의 '초반' h년만 사용=과거 재조합, 미래정보 X).

    paths_by_name: {이름: (n_paths, H_max) 수익률 경로배열}. 모든 이름이 **같은 리샘플 인덱스**로 만들어져야
                   방어 vs 비방어가 같은 대체역사 위에서 비교됨(paired_resample_paths가 보장).
    반환: {h: {'TW_<이름>': 최종부벡터, 'MDD_<이름>': MDD벡터}} — bootstrap_flip_distribution이 요구하는
          **행 정렬(행 i = 모든 h에서 같은 대체역사)** 형태. TW/MDD는 terminal_wealth_rows·mdd_rows와 동일.
    """
    out: dict = {}
    for h in h_grid:
        L = int(round(h * trading_days))
        d: dict = {}
        for name, P in paths_by_name.items():
            P = np.asarray(P, dtype=float)
            if P.ndim != 2 or P.shape[1] < L:
                raise ValueError(
                    "경로 horizon %s < 요구 %s (h=%s) — max(h)·td 로 생성했는지 확인"
                    % (None if P.ndim != 2 else P.shape[1], L, h))
            sub = P[:, :L]
            d["TW_" + name] = terminal_wealth_rows(sub)
            d["MDD_" + name] = mdd_rows(sub)
        out[h] = d
    return out


# ------------------------------- flip 검출 -------------------------------
def find_flip(h_grid, value, *, return_undecidable: bool = False, warn: bool = True):
    """값어치 곡선 value(h)의 **부호전환점 h***들(선형보간). 단조·동부호면 빈 리스트=flip없음.

    value = (방어−비방어)[지표]. **인접** 유효격자에서 부호가 바뀌면 그 사이 선형보간 영점 h*를 반환.
    노드값이 정확히 0이면 그 h를 전환점으로 본다. 다중전환이면 모두 반환.

    ⚠**NaN 안전(silent skip 금지, C Phase2b 수정#3)**: NaN 노드가 두 **유효 노드 사이**에 끼어 그
    양옆 유효값의 **부호가 다르면**(=NaN 구간에 숨은 부호전환이 있을 수 있음), 그 구간을 조용히 버리지
    않고 **판정불가 구간**(h_lo, h_hi)으로 표기한다. 2c 지표(CVaR·coverage·파산확률)는 소표본서 NaN이
    날 수 있어, NaN 사이 실제 flip을 침묵 누락하면 위험하기 때문. NaN 양옆 동부호면 숨은 순flip 신호가
    없으므로 판정불가 아님(보수적으로 '전환 없음'과 동일 취급).

    반환:
      - return_undecidable=False(기본): 부호전환점 리스트(유효데이터만 있으면 종전과 동일 동작).
      - return_undecidable=True: (부호전환점 리스트, 판정불가구간 리스트[(h_lo,h_hi),...]).
      판정불가 구간이 있으면 warn=True일 때 RuntimeWarning으로 알림(조용한 누락 방지).
    """
    h = np.asarray(h_grid, dtype=float)
    v = np.asarray(value, dtype=float)
    order = np.argsort(h)
    h, v = h[order], v[order]
    fin_idx = np.where(np.isfinite(v))[0]              # 유효(비NaN) 노드 인덱스(오름차 h)
    crossings: list[float] = []
    undecidable: list[tuple[float, float]] = []
    # (1) 유효 노드값이 정확히 0 → 그 h가 전환점
    for j in fin_idx:
        if v[j] == 0.0:
            crossings.append(float(h[j]))
    # (2) 연속한 두 유효노드 쌍만 검사(그 사이 NaN 유무로 인접/갭 구분)
    for p in range(len(fin_idx) - 1):
        i0, i1 = int(fin_idx[p]), int(fin_idx[p + 1])
        a, b = v[i0], v[i1]
        if a == 0.0 or b == 0.0:                       # 0 끝점은 (1)에서 처리
            continue
        if (a < 0) == (b < 0):                         # 동부호 → 전환 없음
            continue
        if i1 == i0 + 1:                               # 인접(사이 NaN 없음) → 선형보간 영점
            hstar = h[i0] + (0.0 - a) * (h[i1] - h[i0]) / (b - a)
            crossings.append(float(hstar))
        else:                                          # 사이에 NaN 존재 + 부호 다름 → 숨은 flip, 판정불가
            undecidable.append((float(h[i0]), float(h[i1])))
    # 부동소수 중복 제거(같은 h를 두 분기서 잡는 경우), h 오름차 정렬
    uniq: list[float] = []
    for c in sorted(crossings):
        if not any(abs(c - u) < 1e-9 for u in uniq):
            uniq.append(c)
    if undecidable and warn:
        warnings.warn(
            "find_flip: NaN이 부호전환 가능구간에 끼어 판정불가 구간 %s (silent skip 아님 — "
            "NaN 사이 실제 flip일 수 있음)" % undecidable, RuntimeWarning, stacklevel=2)
    if return_undecidable:
        return uniq, undecidable
    return uniq


def first_flip(h_grid, value) -> float:
    """find_flip의 첫 전환점(없으면 NaN) — h* 스칼라가 필요할 때.

    부트스트랩 재표집 루프서 대량 호출되므로 warn=False(구간경고는 §5·§7 직접 find_flip 호출이 담당).
    판정불가(NaN 갭)는 여기선 '전환 없음(NaN)'으로 처리 = 해당 재표집을 미검출로 보수 집계.
    """
    cr = find_flip(h_grid, value, warn=False)
    return cr[0] if cr else float("nan")


def classify_flip(hstar: float, h_decidable_max: float) -> str:
    """flip h*를 표본내 판정가능('in_sample') vs 외삽/탐색적('extrapolation') vs 없음('none').

    h_decidable_max = 비겹침 독립창이 최소 2개 이상 존재하는 최대 h(호출측이 유효표본으로 산정).
    그 이하=크루드하게라도 독립검증 여지→표본내. 초과=곡선이 겹침창에만 의존→외삽/탐색적 강등.
    """
    if hstar is None or not np.isfinite(hstar):
        return "none"
    return "in_sample" if hstar <= h_decidable_max + 1e-9 else "extrapolation"


def bootstrap_flip_distribution(per_h_arrays: dict, h_grid, value_fn,
                                n_resample: int = 500, seed: int = 0) -> np.ndarray:
    """부트스트랩 표본마다 값어치 곡선을 다시 그려 **h* 분포**를 낸다(설계 §14 핵심).

    per_h_arrays: {h: {이름: 1d배열(길이 B, 모든 h·이름 동일 B)}} — 각 h의 부트스트랩 경로에서
                  이미 뽑아둔 지표배열(예: 최종부·MDD).
    ⚠**행 정렬 필수(수정#2)**: 서로 다른 h에서 **같은 인덱스 i는 같은 대체역사**여야 한다(중첩 horizon).
      즉 max(h)·td 경로 1회 생성 후 `metrics_by_horizon`으로 만든 per_h를 넣어야 공통 재표집 인덱스가
      의미를 가진다. h별로 **따로** 생성한(=행 i가 h마다 다른 대체역사인) 배열을 넣으면 공통 인덱스가
      인위적 종속만 줘 검출율이 왜곡된다.
    여기선 그 B개 경로(행)를 **재표집**해 곡선의 표집불확실성을 전파한다(1단계 블록부트로 만든 경로는
    서로 독립이라 iid 재표집 정당).
    value_fn(sample_dict)->float: 한 h의 재표집 지표들 dict로 그 h의 값어치 스칼라 산출.
    반환: 길이 n_resample 의 h* 배열(전환 없거나 NaN갭 판정불가면 그 원소=NaN=미검출로 보수 집계).
    """
    hs = list(h_grid)
    first_key = next(iter(per_h_arrays[hs[0]]))
    B = len(per_h_arrays[hs[0]][first_key])
    rng = np.random.default_rng(seed)
    out = np.empty(n_resample, dtype=float)
    for t in range(n_resample):
        idx = rng.integers(0, B, B)                 # 모든 h에 공통 재표집 인덱스
        curve = [value_fn({k: v[idx] for k, v in per_h_arrays[h].items()}) for h in hs]
        out[t] = first_flip(hs, curve)
    return out


# --------------------------- 유효 독립창(정직성) ---------------------------
def independent_windows(span_years: float, horizon_years: float) -> int:
    """표본기간 span_years에서 길이 horizon_years 창의 **비겹침 독립창 수** ⌊span/h⌋.

    22년·독립위기 3~4개라 장기 h는 1~2개뿐(설계 §16). 겹침창 통계는 '분포보기'용이지 단정불가.
    """
    if horizon_years <= 0:
        return 0
    return int(np.floor(span_years / horizon_years))


# ----------------------------- 자기검증 -----------------------------
if __name__ == "__main__":
    # 1) CEC 성질
    assert abs(certainty_equivalent(np.full(1000, 1.5), 5) - 1.5) < 1e-9, "상수→그 값 실패"
    w = np.array([0.5, 1.5])
    assert certainty_equivalent(w, 2) < w.mean(), "위험회피면 CEC<E[W]"
    ce2, ce10 = certainty_equivalent(w, 2), certainty_equivalent(w, 10)
    assert ce10 < ce2, "γ↑이면 CEC↓ 실패"
    assert abs(certainty_equivalent(w, 1) - np.exp(np.mean(np.log(w)))) < 1e-12, "γ=1 기하평균"
    assert abs(certainty_equivalent(w, 2) - 2.0 / (1 / 0.5 + 1 / 1.5)) < 1e-9, "γ=2 조화평균"
    # 2) flip
    assert find_flip([3, 5, 7, 10], [1, 1, -1, -1]), "부호전환 미검출"
    assert not find_flip([3, 5, 7], [1, 2, 3]), "단조인데 flip 잡음"
    assert abs(first_flip([0, 10], [1, -1]) - 5.0) < 1e-9, "선형 영점 위치 오류"
    assert len(find_flip([0, 1, 2], [1, -1, 1])) == 2, "다중전환 미검출"
    assert classify_flip(6.0, 10) == "in_sample" and classify_flip(15.0, 10) == "extrapolation"
    assert classify_flip(float("nan"), 10) == "none"
    # 2b) NaN 안전(수정#3): NaN 사이 부호전환은 판정불가로 표기(silent 아님)
    cr, und = find_flip([3, 5, 7, 10], [1.0, float("nan"), -1.0, -2.0],
                        return_undecidable=True, warn=False)
    assert cr == [] and und == [(3.0, 7.0)], "NaN 갭 판정불가 미표기"
    _, und2 = find_flip([3, 5, 7], [1.0, float("nan"), 0.5],
                        return_undecidable=True, warn=False)
    assert und2 == [], "NaN 동부호는 판정불가 아님"
    # 3) 경로지표
    P = np.array([[0.1, -0.05], [0.0, 0.0]])
    assert np.allclose(terminal_wealth_rows(P), [1.1 * 0.95, 1.0])
    from pension_lab.bootstrap import mdd_from_returns
    assert abs(mdd_rows(P)[0] - mdd_from_returns(P[0])) < 1e-12, "MDD 행벡터≠기준"
    assert independent_windows(21, 15) == 1 and independent_windows(21, 3) == 7
    # 3b) 중첩 horizon 지표(수정#2): 앞 h·td 슬라이스 = 접두 최종부
    Q = np.array([[0.01] * 10, [-0.01] * 10])
    mh = metrics_by_horizon({"x": Q}, [1, 2], trading_days=5)
    assert np.allclose(mh[1]["TW_x"], np.prod(1 + Q[:, :5], axis=1)), "중첩 h=1 최종부 오류"
    assert np.allclose(mh[2]["TW_x"], np.prod(1 + Q, axis=1)), "중첩 h=2(=전체) 최종부 오류"
    print("lifecycle 자기검증 통과 (CEC·flip·NaN안전·중첩horizon·경로지표·독립창)")
