"""후보 5 간단 테스트 — 50대(2026년 만 57세) 자영업자: 연금저축 vs 노란우산 vs 예금 (세금·적립·격자 엔진).

명세 = docs/ideas/본연구후보_20261027/후보5_간단테스트/후보5_명세_결정표_20261027.md (+ 정정 r1). 사전기준 = 같은 폴더 후보5_사전기준_20261027.md.
상수는 PARAMS 한 곳(값·결정 ID·출처), ⬜ 결정은 DEC 한 곳(후보·추천). 셀 목록·coverage·constants.csv는 여기서 자동 생성.
자가점검(손계산 예 + 룩어헤드): python -m pension_lab.cand5
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import paths, pilot7 as P7, pilot9 as P9, lifecycle as LC

# ── 상수: (값, 결정 ID, 출처). 제도규칙 = 후보5_제도규칙_1차출처_20261027.md, 노란우산 = 후보5_노란우산·KIRI_원문확인_20261027.md
PARAMS = {
    "local": (1.10, "", "지방소득세 = 소득세의 10% — 제도규칙 1절(13.2%/16.5% 환산)"),
    "credit_cap": (6_000_000, "", "§59의3① 연금저축 600만 초과분 없는 것으로 — law.go.kr 원문(시행 2026-01-01, 제21221호)"),
    "pen62": (0.055, "", "§129 연금소득세 70세 미만 5.5%(지방세 포함) — 제도규칙 5-1절 [보완확인]"),
    "pen70": (0.044, "", "§129 70세 이상 80세 미만 4.4% — 제도규칙 5-1절 [보완확인]"),
    "etc": (0.165, "", "§129①6나 '제21조제1항제18호 및 제21호 기타소득 100분의 15' + 지방세 10% — law.go.kr 원문"),
    "sep_limit": (3_000_000, "D17", "§14③8가 기타소득금액 300만 이하만 분리과세(9~20호, 18호 포함) — law.go.kr 원문"),
    "ny_old": (0.034, "", "노란우산 2026 3분기 노령 기준이율 — 노란우산 (마) [확인]"),
    "ny_close": (0.037, "", "폐업·사망 적용이율 — 노란우산 (마), 제도규칙 7-6절 [확인]"),
    "ny_close_add": (0.003, "", "폐업 가산 0.3%p — 노란우산 (라) 2017 약관"),
    "ny_floor_5y": (0.015, "", "최저보증 5년 이하 — 노란우산 (라) 2017 약관"),
    "ny_floor_after": (0.010, "", "최저보증 5년 초과 — 노란우산 (라) 2017 약관"),
    "ny_old_months": (120, "", "노령 지급 120회 이상 + 만 60세 — 제도규칙 7-5절, 노란우산 (다)"),
    "pension_open_months": (60, "", "가입 5년 경과 후 연금수령 — 제도규칙 4절 시행령 §40의2"),
    "refund_1_6": (0.775, "", "[가정] 2017 약관 별표3을 2026 신규에 적용(H4). 1~6회 77.5%(감사 제시 80% 미대조) — 2017 표 안에서는 36·60·72회에 영향 없음"),
    "refund_7_18": (0.90, "", "[가정] 7~18회 90% — 2017 약관 별표3(노란우산 (라)). 2026.1.1. 이후 가입자 표는 다름(제도규칙 113행 '1~3회 80% 등') — 미확인"),
    "refund_19_30": (0.95, "", "[가정] 19~30회 95% — 2017 약관 별표3(노란우산 (라)). 2026.1.1. 이후 가입자 표는 다름(제도규칙 113행 '1~3회 80% 등') — 미확인"),
    "refund_31_60": (1.00, "", "[가정] 31~60회 100% — 2017 약관 별표3(노란우산 (라)). 2026.1.1. 이후 가입자 표는 다름(제도규칙 113행 '1~3회 80% 등') — 미확인"),
    "bracket1": ((14_000_000, 0.06), "D12", "§55 1구간 — 법조문 표는 이미지라 국세청 세율 페이지로 대조(2026-10-27)"),
    "bracket2": ((50_000_000, 0.15), "D12", "§55 2구간 — 법조문 표는 이미지라 국세청 세율 페이지로 대조(2026-10-27)"),
    "bracket3": ((88_000_000, 0.24), "D12", "§55 3구간 — 법조문 표는 이미지라 국세청 세율 페이지로 대조(2026-10-27)"),
    "room_ga": (0, "", "(가) 그릇 0원 — 지시서 2절"),
    "room_na": (500_000, "", "(나) 그릇 약 50만 원 — 지시서 2절"),
    "monthly": ((100_000, 300_000, 500_000), "", "지시서 2절"),
    "w_eq": ({"A": 1.0, "B": 0.5}, "", "지시서 2절 (A) 100%, (B) 50:50 연 1회"),
    "H62": (72, "", "2026-01 시작 → 2031-12 말(62세)"),
    "H70": (168, "", "→ 2039-12 말(70세)"),
    "eq_fee": (0.0015, "", "KODEX200 보수 — pilot7 대장 C(monthly_kr_long 안에서 차감)"),
    "bd_fee": (P7.BD_TER, "", "국고채 ETF 보수 — pilot7 대장 C"),
    "seed": (20261027, "", "부트스트랩 시드"),
    "n_boot": (10_000, "", "부트스트랩 경로 수(pilot7 NP와 같음)"),
}
P = lambda k: PARAMS[k][0]

# ── ⬜ 결정표: 후보(이름 → 값), 첫 후보 = 추천(★). 명세 2절과 1:1.
DEC = {
    "D01": ("(다) 세금 그릇", {"200만": 2_000_000, "90만": 900_000}),
    "D02": ("소득 수준 묶음(연금저축 공제율, 노란우산 한도) — D03 흡수(정정r1)",
            {"15%·600만": (0.15, 6e6), "15%·500만": (0.15, 5e6), "12%·500만": (0.12, 5e6), "12%·400만": (0.12, 4e6)}),
    "D04": ("예금 이자세", {"15.4%": 0.154, "0%": 0.0}),
    "D05": ("예금 금리 모형", {"12개월사다리": "ladder", "전월금리": "last"}),
    "D06": ("환급·절세 쓰임", {"예금적립": True, "버림": False}),
    "D07": ("62·70세 연금저축 평가", {"연금소득세": "pen", "연금외16.5%": "etc"}),
    "D08": ("노란우산 61회+ 해약 이자비율 — ★ 없음, 두 값 나란히(정정r1)", {"40%": 0.40, "95%": 0.95}),
    "D09": ("노란우산 이율 경로", {"고정3.4·3.7": (0.034, 0.037), "고정3.0·3.3(2025)": (0.030, 0.033), "예금연동": "dep"}),
    "D10": ("노란우산 해약 과세 제외분(§86의3④ '실제 소득공제받은 금액 초과 납입')", {"실제공제((가)과표0)": "actual", "한도초과만": "cap"}),
    "D11": ("노란우산 해약 건보료", {"0": 0.0, "7.1%": 0.071}),
    "D12": ("노란우산 소득공제 절세", {"§55역산": True, "0": False}),
    "D13": ("인출한 해 납입 공제", {"없음": False, "있음": True}),
    "D14": ("시작 달", {"1월": "jan", "모든달": "all"}),
    "D15": ("표본", {"1991~배당포함": "main", "1980~가격": "s7"}),
    "D16": ("1996 이전 예금금리", {"통계청이어붙임": True, "안씀": False}),
    "D17": ("노란우산 해약 기타소득 과세 방식", {"§14③8(300만초과 합산)": "rule", "늘16.5%분리": "sep"}),
    "D18": ("연금저축 과세제외 확인 신청", {"신청함": True, "안함": False}),
}
BOOT_BLOCKS = ("PW_eq", "PW_dep", "12개월")   # 정정r1 BOOT, 첫째 = 추천
REC = {d: next(iter(c.values())) for d, (_, c) in DEC.items()}
NOT_COMPUTED = {"퇴직소득세(노란우산 폐업·노령 지급)": "산식이 제도규칙 파일에 없음 → 세전 = 노란우산 상한",
                "기초연금 소득인정액": "보건복지부 고시 미확인(⬜ 회원 확인, 연금저축에 불리한 방향)",
                "연금소득 1,500만 원 기준·연금수령한도": "D07 연금외 16.5%가 반대 경계"}
PAIRS = {"p62": [("ps", "dep"), ("ps", "ny_cancel"), ("ps", "ny_locked"), ("ny_cancel", "dep")],
         "p70": [("ps", "dep"), ("ps", "ny_old"), ("ny_old", "dep")],
         "wd36": [("ps", "dep"), ("ps", "ny_cancel"), ("ps", "ny_close"), ("ny_cancel", "dep"), ("ny_close", "dep")],
         "wd60": [("ps", "dep"), ("ps", "ny_cancel"), ("ps", "ny_close"), ("ny_cancel", "dep"), ("ny_close", "dep")]}
HS = {"p62": P("H62"), "p70": P("H70"), "wd36": 36, "wd60": 60}
OUT = paths.RESULTS / "candidate5_20261027"
FORBID = ("뚜렷", "크게", "유의", "검증", "복제", "입증", "없다", "장기라 안전")


def cells():
    """격자 셀 목록 = 기준(전부 추천) + 결정마다 추천 아닌 후보 하나씩 바꾼 셀. (cell_id, D, 후보명, 옵션 dict)."""
    out = [("base", "", "★", dict(REC))]
    for d, (_, c) in DEC.items():
        for name, v in list(c.items())[1:]:
            out.append((f"{d}:{name}", d, name, {**REC, d: v}))
    return out


def rooms(o) -> dict:
    return {"가": P("room_ga"), "나": P("room_na"), "다": o["D01"]}


# ── 세금 함수 ─────────────────────────────────────────────────────
def tax55(base: float) -> float:
    """과세표준 → 산출세액(소득세). §55 하위 3구간 [미검증, D12]."""
    t, lo = 0.0, 0.0
    for k in ("bracket1", "bracket2", "bracket3"):
        hi, r = P(k); t += max(min(base, hi) - lo, 0) * r; lo = hi
    assert base <= lo, "구간 밖"
    return t


def base_for(tax: float) -> float:
    lo, acc = 0.0, 0.0
    for k in ("bracket1", "bracket2", "bracket3"):
        hi, r = P(k); step = (hi - lo) * r
        if tax <= acc + step:
            return lo + (tax - acc) / r
        acc += step; lo = hi
    raise ValueError("구간 밖")


def pension_credit(contrib_year: float, room: float, rate: float) -> float:
    """연금저축 세액공제(소득세분) = min(공제율×min(납입,600만), 그릇) — 넘는 부분 소멸(§61③)."""
    return min(rate * min(contrib_year, P("credit_cap")), room)


def ny_saving(contrib_year: float, room: float, cap: float) -> float:
    """노란우산 소득공제로 줄어드는 소득세 = 그릇 − 공제 후 산출세액 (§55 역산, D12)."""
    if room <= 0:
        return 0.0
    return room - tax55(max(base_for(room) - min(contrib_year, cap), 0.0))


def ny_refund(n: int, principal: float, interest: float, share61: float) -> float:
    """노란우산 임의해약 환급금(2017 약관 별표3). 61회 이상 = 원금 + 이자×share61(D08)."""
    for hi, k in ((6, "refund_1_6"), (18, "refund_7_18"), (30, "refund_19_30"), (60, "refund_31_60")):
        if n <= hi:
            return P(k) * principal
    return principal + share61 * interest


# ── 입력 자료 ─────────────────────────────────────────────────────
def deposit_rate_monthly(splice_old: bool = True, start: str = "1979-01") -> pd.Series:
    """1년 정기예금 신규 금리(연 %), 월말 인덱스: 2012-01~ BEABAA2118 · 1996-07~ BEABAA2113 · 1996-01~06 BEABAA211 ·
    (D16) ~1995 통계청(2015) 연말값 — 전년 말 값을 그해 12개월에(범위 표기는 중간값)."""
    d = pd.read_csv(paths.DATA_ROOT / "processed" / "pilot9_ecos_deposit_rates_monthly.csv", parse_dates=["date"]).set_index("date")
    d.index = d.index + pd.offsets.MonthEnd(0)
    s = d["121Y002_BEABAA2118"].combine_first(d["121Y002_BEABAA2113"]).combine_first(d["121Y002_BEABAA211"]).dropna()
    if not splice_old:
        return s.loc["1996-07":]
    k = pd.read_csv(paths.DATA_ROOT / "raw" / "kr_hist_20261016" / "kr_deposit_annual_kostat2015_1945_2014.csv").set_index("year")["mid"]
    old = pd.Series({m: k[m.year - 1] for m in pd.date_range(start, "1995-12-31", freq="ME")})
    return pd.concat([old, s]).sort_index()


def deposit_return(rate_pct: pd.Series, model: str = "ladder") -> pd.Series:
    """그 달 예금 세전 월수익. ladder = 직전 12개월 신규금리 평균(전월말까지), last = 전월말 신규금리 (D05).
    ponytail: 사다리를 균등 평균으로 근사(잔액 가중 아님)."""
    x = rate_pct.rolling(12, min_periods=12).mean() if model == "ladder" else rate_pct
    return (x.shift(1) / 1200).dropna()


def inputs(o: dict) -> pd.DataFrame:
    """월 입력 (eq, bd, dep 세전). D15 main = pilot7.monthly_kr_long() 1991-04~; s7 = KOSPI 가격(배당 미포함) 1980-02~, bd 없음."""
    dep = deposit_return(deposit_rate_monthly(o["D16"]), o["D05"])
    if o["D15"] == "main":
        r = P7.monthly_kr_long()[["eq", "bd"]].copy()
    else:
        px = P7.kospi_px_1980()
        r = pd.DataFrame({"eq": px.pct_change(fill_method=None) - P("eq_fee") / 12}).dropna(); r["bd"] = np.nan
    r["dep"] = dep.reindex(r.index)
    return r.dropna(subset=["eq", "dep"])


def starts(r: pd.DataFrame, o: dict, first: int | None = None):
    first = first or (1992 if o["D15"] == "main" else 1981)
    return [d for d in r.index if d.year >= first and (o["D14"] == "all" or d.month == 1)]


def windows(r: pd.DataFrame, st, H: int):
    pos = [r.index.get_loc(s) for s in st if s in r.index]
    pos = [p for p in pos if p + H <= len(r)]
    take = lambda c: np.stack([r[c].to_numpy(float)[p:p + H] for p in pos]) if pos else np.empty((0, H))
    return take("eq"), take("bd"), take("dep"), [r.index[p].strftime("%Y-%m") for p in pos]


def nstat(r: pd.DataFrame, n_paths: int, H: int) -> dict:
    """n(겹치는 경로 수)과 n_eff(안 겹치는 구간 수 = lifecycle.independent_windows) — 항상 같이 낸다."""
    return {"n": n_paths, "n_eff": LC.independent_windows(len(r) / 12, H / 12)}


# ── 적립·평가 ──────────────────────────────────────────────────────
def accumulate(eq, bd, dep, m: float, w_eq: float, o: dict, mon0=None) -> dict:
    """월초 납입 m. 반환 (n,T) 그 달 말 값: ps(연금저축), dp(예금 세후), ny_old·ny_close(노란우산 적립), G(예금 세후 누적배수).
    (B) w_eq<1: 달력 1월 납입 때 목표 비중으로(mon0 = 경로별 시작 달 1~12, 없으면 1월 시작). D09 dep = 예금 금리 경로 + 최저보증, 폐업 +0.3%p."""
    eq, dep = np.atleast_2d(eq), np.atleast_2d(dep)
    bd = np.zeros_like(eq) if w_eq == 1 else np.atleast_2d(bd)
    n, T = eq.shape
    dnet = dep * (1 - o["D04"])
    if o["D09"] == "dep":
        fl = np.where(np.arange(T) < 60, P("ny_floor_5y"), P("ny_floor_after")) / 12
        r_old, r_close = np.maximum(dep, fl), np.maximum(dep + P("ny_close_add") / 12, fl)
    else:
        yo, yc = o["D09"]
        r_old = np.full((n, T), (1 + yo) ** (1 / 12) - 1); r_close = np.full((n, T), (1 + yc) ** (1 / 12) - 1)
    E = np.zeros(n); B = np.zeros(n); D = np.zeros(n); Y = np.zeros(n); C = np.zeros(n)
    out = {k: np.empty((n, T)) for k in ("ps", "dp", "ny_old", "ny_close")}
    mon0 = np.ones(n, int) if mon0 is None else np.asarray(mon0)
    for t in range(T):
        E = E + w_eq * m; B = B + (1 - w_eq) * m
        if w_eq < 1:
            jan = (mon0 - 1 + t) % 12 == 0; tot = E + B
            E, B = np.where(jan, w_eq * tot, E), np.where(jan, (1 - w_eq) * tot, B)
        E = E * (1 + eq[:, t]); B = B * (1 + bd[:, t])
        D = (D + m) * (1 + dnet[:, t]); Y = (Y + m) * (1 + r_old[:, t]); C = (C + m) * (1 + r_close[:, t])
        out["ps"][:, t], out["dp"][:, t], out["ny_old"][:, t], out["ny_close"][:, t] = E + B, D, Y, C
    out["G"] = np.cumprod(1 + dnet, axis=1)
    return out


def side_account(G: np.ndarray, H: int, per_year: float, years: int) -> np.ndarray:
    """해마다 per_year(지방세 포함 환급·절세)가 다음 해 5월 말(0기준 달 12k+16)에 들어와 예금에 쌓임. 평가 뒤 도착분은 액면."""
    v = np.zeros(G.shape[0])
    for k in range(years):
        a = 12 * k + 16
        v += per_year * (G[:, H - 1] / G[:, a] if a <= H - 1 else 1.0)
    return v


def ny_cancel_tax(x, room: float, how: str) -> np.ndarray:
    """노란우산 해지 기타소득금액 x(경로별)의 세금(지방세 포함). D17 rule: 300만 초과 → 종합합산 [§55(과표+x) − §55(과표)]×1.1,
    300만 이하 → 분리 16.5%와 합산 중 작은 쪽(§14③8가 단서). sep: 늘 16.5%. 과표 = 그릇에서 §55 역산."""
    x = np.atleast_1d(np.asarray(x, float)); sep = P("etc") * x
    if how == "sep":
        return sep
    b = base_for(room)
    comb = np.array([tax55(b + v) - tax55(b) for v in x]) * P("local")
    return np.where(x > P("sep_limit"), comb, np.minimum(sep, comb))


def evaluate(acc: dict, m: float, room: float, H: int, mode: str, o: dict) -> dict:
    """평가 달 H. mode p62·p70(끝까지) / wd(H달 말 전부 인출). 상품별 세후 금액 (n,)."""
    i, Y = H - 1, H // 12
    rate, cap = o["D02"]
    c, s = pension_credit(12 * m, room, rate), (ny_saving(12 * m, room, cap) if o["D12"] else 0.0)
    cy = Y if (mode != "wd" or o["D13"]) else Y - 1           # 연금저축 공제받는 해 수
    cyn = Y if (mode == "p70" or o["D13"]) else Y - 1         # 노란우산 해약(wd·62세): 해약한 해 납입 공제 없음(D13, 결과감사 r1 H1)
    nonded = (cy * (12 * m - c / rate) + (Y - cy) * 12 * m) if o["D18"] else 0.0   # 과세제외 원금(D18 확인 신청)
    k = P("local") if o["D06"] else 0.0
    side_p, side_n, side_nc = (side_account(acc["G"], H, k * x, y) for x, y in ((c, cy), (s, cy), (s, cyn)))
    prin = H * m
    ded = min(12 * m, cap, base_for(room)) if o["D10"] == "actual" else min(12 * m, cap)   # 해마다 실제 소득공제받은 금액
    over = cyn * (12 * m - ded) + (Y - cyn) * 12 * m                # 실제 공제 초과 납입 누계(§86의3④, 과세 제외)
    V = acc["ps"][:, i]; taxable = np.maximum(V - nonded, 0)
    ny_net = lambda ref: ref - ny_cancel_tax(np.maximum(ref - over, 0), room, o["D17"]) - o["D11"] * ref + side_nc
    res = {"contrib": prin, "dep": acc["dp"][:, i]}
    if mode == "wd":
        res["ps"] = V - P("etc") * taxable + side_p                                # 연금외수령: §14③8나 늘 분리
        res["ny_cancel"] = ny_net(np.full(V.shape, ny_refund(H, prin, 0.0, 0.0)))  # 36·60회: 원금 기준
        res["ny_close"] = acc["ny_close"][:, i] + side_n                          # 퇴직소득세 미계산(상한)
    else:
        tr = P("pen62") if mode == "p62" else P("pen70")
        res["ps"] = V - (tr if o["D07"] == "pen" else P("etc")) * taxable + side_p
        Yb = acc["ny_old"][:, i]
        if mode == "p62":
            res["ny_cancel"] = ny_net(np.array([ny_refund(H, prin, y - prin, o["D08"]) for y in Yb]))
            res["ny_locked"] = Yb + side_n
        else:
            res["ny_old"] = Yb + side_n                                           # 퇴직소득세 미계산(상한)
    return res


def run(r: pd.DataFrame, o: dict, H: int, mode: str, st=None) -> pd.DataFrame:
    """한 셀·한 시점: 사람×납입×자산별 세후 금액 긴 표. 자산 (B)는 채권 자료가 있을 때만."""
    eq, bd, dep, keys = windows(r, starts(r, o) if st is None else st, H)
    rows = []
    for an, w in P("w_eq").items():
        if w < 1 and (not len(keys) or np.isnan(bd).any()):
            continue
        for m in P("monthly"):
            acc = accumulate(eq, bd, dep, m, w, o, [int(k[5:]) for k in keys])
            for pn, room in rooms(o).items():
                e = evaluate(acc, m, room, H, mode, o)
                d = pd.DataFrame({k: v for k, v in e.items() if np.ndim(v)}); d["contrib"] = e["contrib"]
                d.insert(0, "path", keys); d.insert(1, "asset", an); d.insert(2, "m", m); d.insert(3, "person", pn)
                rows.append(d)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def loss_stats(df: pd.DataFrame, a: str, b: str, by=("asset", "m", "person")) -> pd.DataFrame:
    """a < b 경로 수·비율(신뢰구간 없음: 겹치는 경로)과 (a−b)/누적납입: 손해 경로 평균·최악·중앙값."""
    def f(g):
        x = (g[a] - g[b]) / g["contrib"]; k = int((x < 0).sum())
        return pd.Series({"n": len(x), "loss_n": k, "p_loss": k / len(x), "mean_loss": x[x < 0].mean() if k else np.nan,
                          "worst": x.min(), "median_gap": x.median()})
    return df.groupby(list(by), sort=False).apply(f, include_groups=False).reset_index()


# ── MDE·요약 문장 ───────────────────────────────────────────────────
def mde_table(r: pd.DataFrame) -> pd.DataFrame:
    """실질 차이 문턱(MDE, 정정r1 3절): 시점×쌍×자산마다 세금 넣기 전 두 상품 차이(÷누적납입)의 모든 달 시작 sd → pilot9.mde(sd, n_eff).
    sd=0 또는 n_eff=0 → '비교 불가'(식별 안 됨과 따로)."""
    o = {**REC, "D04": 0.0}
    rows = []
    for k, H in HS.items():
        eq, bd, dep, keys = windows(r, list(r.index), H)
        n = nstat(r, len(keys), H)
        for an, w in P("w_eq").items():
            if w < 1 and np.isnan(bd).any():
                continue
            a = accumulate(eq, bd, dep, 1.0, w, o, [int(x[5:]) for x in keys])
            v = {"ps": a["ps"][:, -1], "dep": a["dp"][:, -1], "ny_old": a["ny_old"][:, -1], "ny_locked": a["ny_old"][:, -1],
                 "ny_close": a["ny_close"][:, -1], "ny_cancel": np.array([ny_refund(H, H, y - H, REC["D08"]) for y in a["ny_old"][:, -1]])}
            for x, y in PAIRS[k]:
                sd = float(np.std((v[x] - v[y]) / H, ddof=1)); ok = sd > 1e-12 and n["n_eff"] > 0
                rows.append({"비교": k, "쌍": f"{x}<{y}", "asset": an, "sd": sd, **n,
                             "mde": P9.mde(sd, n["n_eff"]) if ok else np.nan, "비교불가": not ok})
    return pd.DataFrame(rows)


def sentence(text: str, diff: float | None = None, mde: float | None = None, bounds=None, warn: bool = False) -> str:
    """요약 문장 규칙: |차이|<MDE 또는 경계가 0 포함 → '식별 안 됨', ⚠ → '선택에 따라 달라짐'. 금지어 있으면 멈춤."""
    tags = []
    if (diff is not None and mde is not None and abs(diff) < mde) or (bounds is not None and min(bounds) <= 0 <= max(bounds)):
        tags.append("식별 안 됨")
    if warn:
        tags.append("선택에 따라 달라짐")
    s = text + (f" ({', '.join(tags)})" if tags else "")
    bad = [w for w in FORBID if w in s]
    assert not bad, f"금지어 {bad}: {s}"
    return s


def constants_table() -> pd.DataFrame:
    a = [{"키": k, "값": str(v), "결정": d, "출처": s} for k, (v, d, s) in PARAMS.items()]
    b = [{"키": f"{d} 후보:{n}", "값": str(v), "결정": d, "출처": (("기준셀(★ 없음) " if "★ 없음" in nm else "★추천 ") if i == 0 else "") + nm} for d, (nm, c) in DEC.items() for i, (n, v) in enumerate(c.items())]
    return pd.DataFrame(a + b)


def _check() -> None:
    """손계산 예(함수마다 2~3개 이상) + 룩어헤드."""
    o = dict(REC)
    assert tax55(10_000_000) == 600_000 and tax55(14_000_000) == 840_000 and abs(tax55(20_000_000) - 1_740_000) < 1e-6
    assert abs(base_for(500_000) - 8_333_333.33) < 1 and abs(base_for(2_000_000) - 21_733_333.33) < 1 and base_for(0) == 0
    assert pension_credit(6_000_000, 0, .15) == 0 and pension_credit(6_000_000, 2_000_000, .15) == 900_000
    assert pension_credit(6_000_000, 500_000, .15) == 500_000 and pension_credit(9_000_000, 5e6, .12) == 720_000
    assert ny_saving(6e6, 0, 6e6) == 0 and abs(ny_saving(6e6, 5e5, 6e6) - 360_000) < 1e-6 and abs(ny_saving(6e6, 2e6, 6e6) - 900_000) < 1e-6
    assert abs(ny_saving(6e6, 9e5, 6e6) - (0.15 * 4e5 + 0.06 * 5.6e6)) < 1e-6   # 그릇 90만: 과표 1,440만 → 공제 뒤 840만, 구간 걸침
    assert abs(ny_saving(6e6, 2e6, 5e6) - 750_000) < 1e-6                        # 한도 500만
    assert ny_refund(3, 300, 0, .4) == 232.5 and ny_refund(12, 100, 5, .4) == 90 and ny_refund(24, 100, 5, .4) == 95
    assert ny_refund(36, 100, 5, .4) == 100 and ny_refund(72, 100, 10, .4) == 104 and ny_refund(72, 100, 10, .95) == 109.5
    z = lambda T: np.zeros((1, T))
    ev = lambda m, room, oo, H=36: evaluate(accumulate(z(H), z(H), z(H), m, 1.0, oo), m, room, H, "wd", oo)
    # (가) 수익 0, 36개월 인출: 연금저축 = 원금(과세제외 확인), 노란우산 해약 = 원금(실제 공제 0 → 전부 과세 제외, §86의3④)
    e = ev(100_000, 0, o); assert abs(e["ps"][0] - 3.6e6) < 1e-6 and abs(e["ny_cancel"][0] - 3.6e6) < 1e-6
    # D10 한도초과만: (가)도 공제받았다고 봄 → 2년치 240만 과세 대상(300만 이하 → min(16.5%, 합산 6.6%) = 6.6%)
    e = ev(100_000, 0, {**o, "D10": "cap"}); assert abs(e["ny_cancel"][0] - (3.6e6 - .066 * 2.4e6)) < 1e-6
    # D17 늘 분리: 같은 경우 16.5%
    e = ev(100_000, 0, {**o, "D10": "cap", "D17": "sep"}); assert abs(e["ny_cancel"][0] - (3.6e6 - .165 * 2.4e6)) < 1e-6
    # D18 안 함: (가) 연금저축 원금 전부 16.5%
    e = ev(100_000, 0, {**o, "D18": False}); assert abs(e["ps"][0] - 3.6e6 * (1 - .165)) < 1e-6
    # (다) 월 50만 36개월: 2년 공제 → 과세 1,200만×16.5%, 환급 2×99만(예금 0%)
    e = ev(500_000, 2e6, o); assert abs(e["ps"][0] - (18e6 - .165 * 12e6 + 2 * 990_000)) < 1e-6
    # (다) 노란우산 해약: 3년째 납입 600만은 공제 안 받아 제외 → 기타소득 1,200만(>300만 합산, 과표 2,173만+ → 15%×1.1)
    assert abs(e["ny_cancel"][0] - (18e6 - .165 * 12e6 + 2 * 990_000)) < 1e-6
    # (나) 그릇 50만 → 과표 833만: 기타소득 1,200만 합산 = 6%×567만 + 15%×633만, ×1.1
    e = ev(500_000, 5e5, o); t = 1.1 * (.06 * (14e6 - 8_333_333.33) + .15 * (20_333_333.33 - 14e6))
    assert abs(e["ny_cancel"][0] - (18e6 - t + 2 * 1.1 * 360_000)) < 1
    # D13 있음: 3년째도 공제 → 연금저축 과세 1,800만, 환급 3번째는 액면
    e = ev(500_000, 2e6, {**o, "D13": True}); assert abs(e["ps"][0] - (18e6 - .165 * 18e6 + 3 * 990_000)) < 1e-6
    # D02 (15%, 500만): 연 100만 공제 밖 → 3년째 600만 + 2×100만 = 800만 제외, 기타소득 1,000만
    e = ev(500_000, 2e6, {**o, "D02": (0.15, 5e6)}); assert abs(e["ny_cancel"][0] - (18e6 - .165 * 10e6 + 2 * 1.1 * 750_000)) < 1e-6
    o0 = {**o, "D09": (0.0, 0.0)}; e = evaluate(accumulate(z(72), z(72), z(72), 500_000, 1.0, o0), 500_000, 2e6, 72, "p62", o0)
    b = base_for(2e6); t = 1.1 * (.15 * (50e6 - b) + .24 * (b + 30e6 - 50e6))   # 기타소득 3,000만 합산: 15%→24% 구간 걸침
    assert abs(e["ny_cancel"][0] - (36e6 - t + 5 * 990_000)) < 1e-6 and abs(e["ny_locked"][0] - (36e6 + 6 * 990_000)) < 1e-6
    # (위) 62세 해약 D13: 6년째 납입 600만 과세 제외·절세 5번, 묶임은 6번
    # 10% 한 번 오른 뒤 (가) 62세: 과세 = 수익분만 5.5%, D07 연금외면 16.5%
    r = z(72); r[0, -1] = .1
    e = evaluate(accumulate(r, None, z(72), 100_000, 1.0, o), 100_000, 0, 72, "p62", o)
    assert abs(e["ps"][0] - (7_920_000 - .055 * 720_000)) < 1e-6
    o7 = {**o, "D07": "etc"}; e = evaluate(accumulate(r, None, z(72), 100_000, 1.0, o7), 100_000, 0, 72, "p62", o7)
    assert abs(e["ps"][0] - (7_920_000 - .165 * 720_000)) < 1e-6
    # 70세 4.4%: 168개월 끝 10% → (가) 과세 = 수익분
    r = z(168); r[0, -1] = .1
    e = evaluate(accumulate(r, None, z(168), 100_000, 1.0, o), 100_000, 0, 168, "p70", o)
    assert abs(e["ps"][0] - (16_800_000 * 1.1 - .044 * 1_680_000)) < 1e-6
    # (B): 12번째 달 주식 +10% → 13번째 달(1월) 납입 때 50:50. 7월 시작이면 7번째 달(1월)에 맞춤
    a = accumulate(np.r_[np.zeros(11), .1, np.zeros(12)][None], z(24), z(24), 100_000, .5, o)
    assert abs(a["ps"][0, 12] - 1_360_000) < 1e-6
    a = accumulate(np.r_[.1, np.zeros(11)][None], z(12), z(12), 100_000, .5, o, [7])
    assert abs(a["ps"][0, 0] - 105_000) < 1e-6 and abs(a["ps"][0, 6] - 705_000) < 1e-6
    # 룩어헤드: t달 예금 수익은 t−1달까지 금리만 씀 — 미래 금리를 바꿔도 과거 수익 불변
    s = deposit_rate_monthly(); cut = s.index[300]
    s2 = s.copy(); s2.loc[cut:] += 5
    for mdl in ("ladder", "last"):
        a1, a2 = deposit_return(s, mdl), deposit_return(s2, mdl)
        assert (a1.loc[:cut] == a2.loc[:cut]).all() and (a1.loc[cut + pd.offsets.MonthEnd(1):] != a2.loc[cut + pd.offsets.MonthEnd(1):]).all()
    k = deposit_rate_monthly().loc["1990-01":"1990-12"]; assert k.nunique() == 1   # 통계청 연값: 1989 연말값을 1990 전체에
    # 격자: 결정마다 추천 아닌 후보 셀이 빠짐없이 있음
    ids = {c[1] for c in cells()}; assert ids == {""} | set(DEC), "격자 누락"
    assert ny_cancel_tax([4e6], 0, "rule")[0] == .066 * 4e6 and ny_cancel_tax([2e6], 3e6, "rule")[0] == .165 * 2e6
    assert "식별 안 됨" in sentence("x", .01, .02) and "선택에 따라" in sentence("x", warn=True)
    try:
        sentence("차이가 뚜렷하다"); stopped = False
    except AssertionError:
        stopped = True
    assert stopped, "금지어 검사 실패"
    print("cand5 자가점검 통과")


if __name__ == "__main__":
    _check()
