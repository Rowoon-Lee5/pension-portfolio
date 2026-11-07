"""pilot9 공통 — TDF·글라이드패스 실험 공통 함수(이 저장소는 D 하락장 더 담기에서 씀).

1단계-c 실현가능성(결과 맹검)용: 하락 사건 판정(pilot7 SEC 규칙을 하락폭 매개변수로 일반화).
하락 기준은 C-1 결정(2026-10-14, docs/ideas/pilot9_C1_하락기준_종합_20261014.md): 월말·−20% 주·바닥 대비 +20% 반등 재무장. 자가점검: python -m pension_lab.pilot9
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd
from . import paths
from . import pilot7 as P7

OUT = paths.RESULTS / "pilot9_20261013"
DD_GRID = (-0.10, -0.20, -0.30)   # C-1 결정(2026-10-14): −0.20 주(SEC 'Bear market', pilot7 대장 D2), −0.10·−0.30 민감도


REARM = 0.20             # C-1 결정(2026-10-14): 바닥 대비 +20% 반등 뒤 다음 사건(Lunde-Timmermann λ1=20). 민감도 None(고점 완전 회복 = pilot7)·0.15
REARM_SENS = (None, 0.15)


def dd_starts(ret: pd.Series, th: float, min_months: int = P7.BEAR_MIN_MONTHS, rearm: float | None = None) -> list[pd.Timestamp]:
    """고점 대비 th 이하 하락이 고점 뒤 min_months개월 이상 지나 처음 확인된 월말(같은 달 두 조건 동시 성립).
    다음 사건: rearm=None이면 판정 당시 고점 회복 뒤(pilot7; th=P7.BEAR이면 pilot7.bear_starts와 같다, 자가점검),
    rearm=x면 th 첫 돌파 달 이후 최저점(LT 식 (3) Pmin) 대비 +x 반등한 달부터 새 고점 추적.
    c1_interp_compare 'same' 모드와 실제 자료 396조합 일치(2026-10-14 감사). 단 고점 동률(같은 값 재등장)은 여기선 고점 갱신(>=, pilot7과 같음),
    기준 구현은 갱신 안 함(>) — 동률이 있으면 날짜가 다를 수 있다(현재 자료 영향 0).
    ⚠ 기본값 rearm=None은 pilot7 비교용이다. C·D 주 규칙은 rearm=REARM을 반드시 명시해 부른다."""
    R = ret.to_numpy(float); out, i = [], 0
    while i < len(R):
        lvl = np.r_[1.0, np.cumprod(1 + R[i:])]; peak = np.maximum.accumulate(lvl)
        t = np.arange(len(lvl)); ppos = np.maximum.accumulate(np.where(lvl >= peak, t, 0))
        hit = np.flatnonzero((lvl / peak - 1 <= th) & (t - ppos >= min_months))
        if not len(hit):
            break
        j = int(hit[0]); out.append(ret.index[i + j - 1])
        if rearm is None:
            rec = np.flatnonzero(lvl[j + 1:] >= peak[j])      # 판정 다음 달부터 판정 당시 고점 회복
            if not len(rec):
                break
            i = i + j + int(rec[0]) + 1
        else:
            ft = ppos[j] + int(np.flatnonzero(lvl[ppos[j]:j + 1] / peak[j] - 1 <= th)[0])   # 문턱 첫 돌파 달
            lo = np.minimum.accumulate(lvl[ft:])[j - ft:]                                     # 첫 돌파 달부터 각 달까지 최저점
            rec = np.flatnonzero(lvl[j:] / lo - 1 >= rearm)
            if not len(rec):
                break
            i = i + j + int(rec[0])
    return out


def dd_events(ret, th: float, min_months: int = P7.BEAR_MIN_MONTHS, rearm: float | None = None) -> list[tuple[int, int | None]]:
    """dd_starts와 같은 판정의 위치판(1차원 배열) + 사건마다 회복월. 반환 [(확인월 위치 c, 회복월 위치 또는 None)].
    회복월 = c 다음 달부터 '판정 당시 고점' 수준 이상(>=)이 처음 된 달(dd_starts rearm=None의 다음 사건 기준과 같은 정의).
    확인월 목록은 dd_starts와 같아야 한다(자가점검, pilot9 D 2026-10-17)."""
    R = np.asarray(ret, float); out, i = [], 0
    while i < len(R):
        lvl = np.r_[1.0, np.cumprod(1 + R[i:])]; peak = np.maximum.accumulate(lvl)
        t = np.arange(len(lvl)); ppos = np.maximum.accumulate(np.where(lvl >= peak, t, 0))
        hit = np.flatnonzero((lvl / peak - 1 <= th) & (t - ppos >= min_months))
        if not len(hit):
            break
        j = int(hit[0]); c = i + j - 1
        rc = np.flatnonzero(lvl[j + 1:] >= peak[j]); out.append((c, c + 1 + int(rc[0]) if len(rc) else None))
        if rearm is None:
            if not len(rc):
                break
            i = i + j + int(rc[0]) + 1
        else:
            ft = ppos[j] + int(np.flatnonzero(lvl[ppos[j]:j + 1] / peak[j] - 1 <= th)[0])
            lo = np.minimum.accumulate(lvl[ft:])[j - ft:]
            rec = np.flatnonzero(lvl[j:] / lo - 1 >= rearm)
            if not len(rec):
                break
            i = i + j + int(rec[0])
    return out


def dip_on(price_ret, th: float, exit: str, rearm: float | None = REARM, start: int = 0, ev: list | None = None) -> tuple[np.ndarray, int, int]:
    """pilot9 D 규칙 켜짐(bool, 길이 = 입력). 확인월 c(위치 >= start)의 다음 달(t+1)부터 켜짐.
    exit='peak': 그 사건의 판정 당시 고점을 다시 넘은 달까지 켜짐(그다음 달 복귀, 자료 끝까지 미회복이면 끝까지). exit='1y': c+1..c+12(12개월).
    사건이 겹치면(켜진 동안 새 확인) 더하지 않고 복귀 기준을 가장 최근 사건으로 바꾼다. 반환 (켜짐, 사건 수, 겹친 사건 수).
    ev: 같은 입력의 dd_events 결과(두 복귀 방식에 한 번만 계산할 때)."""
    n = len(price_ret); on = np.zeros(n, bool); end0, ov = -1, 0
    ev = [e for e in (dd_events(price_ret, th, rearm=rearm) if ev is None else ev) if e[0] >= start]
    for c, rc in ev:
        end = min(c + 12, n - 1) if exit == "1y" else (n - 1 if rc is None else rc)
        ov += c < end0
        on[c + 1:] = False; on[c + 1:end + 1] = True; end0 = end
    return on, len(ev), int(ov)


def dip_weights(price_ret, glide, th: float, delta: float, exit: str, rearm: float | None = REARM, start: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """위험자산 비중 = min(글라이드 + delta·켜짐, 1)(상한 100%). 반환 (비중, 켜짐)."""
    on = dip_on(price_ret, th, exit, rearm, start)[0]
    return np.minimum(np.asarray(glide, float) + delta * on, 1.0), on


def rearm_name(x: float | None) -> str:
    return "full" if x is None else f"re{round(x * 100)}"


def event_table(markets: dict[str, pd.Series], grid=DD_GRID, rearms=(REARM, *REARM_SENS)) -> pd.DataFrame:
    """시장×하락폭×재무장별 사건 수·시작월 목록·표본 기간(가격 수익률 입력, 결과변수 아님). rearm 열: re20(주)·full·re15."""
    rows = []
    for m, r in markets.items():
        r = r.dropna()
        for th in grid:
            for ra in rearms:
                s = dd_starts(r, th, rearm=ra)
                rows.append(dict(market=m, th=th, rearm=rearm_name(ra), n_events=len(s), start=r.index[0].strftime("%Y-%m"),
                                 end=r.index[-1].strftime("%Y-%m"), months=len(r),
                                 event_months=";".join(x.strftime("%Y-%m") for x in s)))
    return pd.DataFrame(rows)


def complete_months(ret: pd.Series, asof: str) -> pd.Series:
    """asof(자료 기준일)가 속한 달이 끝나지 않았으면 그 달을 뺀다(미완성 월 수익 금지)."""
    a = pd.Timestamp(asof)
    return ret[ret.index < a.to_period("M").to_timestamp()] if a != a + pd.offsets.MonthEnd(0) else ret[ret.index <= a]


def clusters(starts: list[pd.Timestamp], gap_months: int = 12) -> int:
    """여러 시장 사건 시작월을 날짜순으로 놓고, 묶음 첫 사건에서 gap_months 이내면 같은 묶음 → 묶음 수(동시 하락을 1건으로)."""
    n, first = 0, None
    for t in sorted(starts):
        if first is None or (t.year - first.year) * 12 + t.month - first.month > gap_months:
            n, first = n + 1, t
    return n


def mde(sd: float, n1: int, n2: int | None = None, alpha: float = 0.05, power: float = 0.8, m: int = 1) -> float:
    """두 표본 평균차 최소검출효과(정규 근사). n2=None이면 비교군을 무한대로 봄. m = Holm 최악(첫 단계) 보정 수."""
    from scipy.stats import norm
    return (norm.ppf(1 - alpha / (2 * m)) + norm.ppf(power)) * sd * np.sqrt(1 / n1 + (1 / n2 if n2 else 0))


TDF_ABBR = {"한국TDF알아서": "한국투자TDF알아서", "미래전략배분": "미래에셋전략배분",   # 안내서의 줄임 표기 → KOFIA 계열명(원문 대조)
            "미래에셋자산배분TDF": "미래에셋ETF로자산배분TDF"}   # 옛 이름 → 새 이름(official_rename_check_v2 개명 사슬, TDF 마스터 line 묶음과 같음)


def tdf_series(name: str) -> tuple[str | None, str | None]:
    """구성 상품명 → (계열, 빈티지). 공백 제거·대문자·'적격' 제거 뒤 'TDF…20xx'. 예: '한국적격TDF알아서2035증권O' → ('한국투자TDF알아서','2035')."""
    s = re.sub(r"\s", "", str(name)).upper().replace("적격", "")
    m = re.search(r"^(.*?TDF[가-힣A-Z]*?)\(?(20\d\d)", s)
    if not m:
        return None, None
    line = m.group(1)
    for a, b in TDF_ABBR.items():
        line = line.replace(a.upper(), b.upper())
    return line, m.group(2)


if __name__ == "__main__":
    assert tdf_series("한국적격TDF알아서2035증권O(주혼-재)") == ("한국투자TDF알아서", "2035")
    assert tdf_series("한화 LifePlus 적격 TDF2035(채혼재간) 펀드") == ("한화LIFEPLUSTDF", "2035")
    assert tdf_series("디폴트옵션중립투자형TDF(2030)1") == ("디폴트옵션중립투자형TDF", "2030")
    assert clusters([pd.Timestamp(x) for x in ("2008-01-31", "2008-06-30", "2011-08-31", "2009-03-31")]) == 3   # 2008-01·06 | 2009-03(14개월 뒤) | 2011-08
    assert len(complete_months(pd.Series(1.0, index=pd.date_range("2026-08-31", periods=3, freq="ME")), "2026-10-14")) == 2
    ix = lambda n: pd.date_range("2000-01-31", periods=n, freq="ME")
    for s in (pd.Series([0.0, -0.15, -0.1, 0.0, 0.5, 0.0, -0.25, -0.01], index=ix(8)),
              pd.Series([-0.25, -0.01, 0.0], index=ix(3)), pd.Series([0.0, -0.15, -0.1], index=ix(3))):
        assert dd_starts(s, P7.BEAR) == P7.bear_starts(s), (dd_starts(s, P7.BEAR), P7.bear_starts(s))
    rng = np.random.default_rng(1)
    for _ in range(300):
        s = pd.Series(rng.normal(0.005, 0.07, 240), index=ix(240))
        assert dd_starts(s, P7.BEAR) == P7.bear_starts(s)
    for m, r in {"KR_kospi": P7.kospi_px_1980().pct_change(fill_method=None).dropna(), "US_sp500": P7.us_px_monthend()}.items():
        assert dd_starts(r, P7.BEAR) == P7.bear_starts(r), m
    s = pd.Series([0.0, -0.25, 0.0, 0.25, -0.25, 0.0, 0.0], index=ix(7))   # 바닥 0.75 → +25% 반등(고점 미회복) 뒤 재하락 → re20만 두 번째 사건
    assert (len(dd_starts(s, P7.BEAR)), len(dd_starts(s, P7.BEAR, rearm=0.20))) == (1, 2)
    assert rearm_name(None) == "full" and rearm_name(REARM) == "re20" and rearm_name(0.15) == "re15"
    kp = P7.kospi_px_1980().pct_change(fill_method=None).dropna()      # dd_events 확인월 = dd_starts (D 규칙용 위치판)
    for s in [kp] + [pd.Series(rng.normal(0.005, 0.07, 240), index=ix(240)) for _ in range(100)]:
        for th in DD_GRID:
            for ra in (REARM, *REARM_SENS):
                assert [s.index[c] for c, _ in dd_events(s.to_numpy(), th, rearm=ra)] == dd_starts(s, th, rearm=ra), (th, ra)
    r = np.array([0.0, -0.15, -0.10, 0.10, 0.10, 0.10, 0.05, 0.0, 0.0])   # 고점 1 → 확인월 2(−23.5%) → 회복월 5(1.018)
    assert dd_events(r, -0.20) == [(2, 5)] and dip_on(r, -0.20, "peak")[0].tolist() == [0, 0, 0, 1, 1, 1, 0, 0, 0]
    assert dip_on(np.r_[r, np.zeros(10)], -0.20, "1y")[0].sum() == 12 and dip_weights(r, np.full(9, 0.95), -0.20, 0.15, "peak")[0].max() == 1.0
    print("pilot9 self-check ok")
