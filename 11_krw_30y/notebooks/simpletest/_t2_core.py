"""간단 테스트 T2 공통 함수 — 명세 docs/ideas/본연구후보_20261027/간단테스트_명세_T2_20261027.md (커밋 d025dfb).
MDE 단계(_gen_T2.py mde)와 노트북이 같이 import. 공용 모듈(pilot7·bootstrap·runrecord)은 고치지 않고 공개 함수만 씀.
자가점검: python notebooks/simpletest/_t2_core.py
"""
from __future__ import annotations
import functools, warnings
import numpy as np
import pandas as pd
from pension_lab import pilot7 as P, io, paths
from pension_lab.bootstrap import paired_resample_paths

SEED, NP, T = 20261027, 10_000, 360
OUT = paths.RESULTS / "simpletest_20261027" / "T2"
RAWN = paths.RAW / "simpletest_20261027" / "T2"
GLIDE_F = paths.RESULTS / "pilot9_20261013" / "C_real_20261017" / "inputs" / "C2_glide_by_remaining_years.csv"
PHASE_F = paths.RESULTS / "pilot9_20261013" / "c1_korea" / "c1_ps_bear_phases_v2_20261014.csv"
FRDEV_F = paths.RAW / "global_equity_20261016" / "french_region_mkt_monthly_usd.csv"
FX64_F = paths.RAW / "kr_hist_20261016" / "kr_usdkrw_monthly_1964.csv"
MC_F = paths.PROCESSED / "multicountry_returns_20261017.csv"
US_ETF_TER = 0.000068   # T2-D17 B: TIGER미국S&P500 총보수 0.0068%(근거 대장 C 44행, 1차) — KODEX 0.0062%보다 큰 값(보수적)
W33 = (0.33, 0.67)      # ④ 회원 지정(ACO 2025)
W60 = 0.6               # ② 회원 지정
S35 = (0.35, 0.65)      # T2-D9 C: 가정_전수조사 #4 (P.EQ_KR_SHARE)
assert S35[0] == P.EQ_KR_SHARE
# pilot7.monthly_us_long 안 기간 차분 단언(첫 NaT)이 내는 pandas 경고 — 값과 무관, 노트북 경고 스팸 방지
warnings.filterwarnings("ignore", message="overflow encountered in scalar multiply", category=RuntimeWarning)
US_LONG = functools.cache(P.monthly_us_long)


# ── 자료 ─────────────────────────────────────────────────────────────
def _me(s):
    return s.set_axis(pd.DatetimeIndex(s.index) + pd.offsets.MonthEnd(0))


def mc_series(src: str, iso: str, var: str) -> pd.Series:
    m = pd.read_csv(MC_F, usecols=["source", "iso3", "freq", "period", "variable", "value"], dtype={"value": float}, low_memory=False)
    m = m[(m.source == src) & (m.iso3 == iso) & (m.freq == "M") & (m.variable == var)]
    return _me(pd.Series(m.value.values, index=pd.to_datetime(m.period)))


def us_usd_kr() -> pd.Series:
    """monthly_kr_long 안의 us_usd와 같은 공개 함수 조합(~1999 us_tr_monthend, 2000~ SPY TR). 재구성 일치는 kr_panel에서 assert."""
    return pd.concat([P.us_tr_monthend().loc[:"1999-12"], io.asset_series("us_eq").resample("ME").last().pct_change(fill_method=None).loc["2000-01":]])


def kr_panel() -> pd.DataFrame:
    """KR1991 패널 = monthly_kr_long() + us_usd·fx·헤지·French developed 원화 열. 공용 함수 무수정."""
    k = P.monthly_kr_long()
    fxl = io.asset_series("usdkrw").resample("ME").last(); fx = (fxl / fxl.shift(1) - 1)
    uu = us_usd_kr().reindex(k.index)
    assert np.allclose((1 + uu) * (1 + fx.reindex(k.index)) - 1, k["us"], rtol=0, atol=1e-12), "us 재구성 불일치"
    us_cash = US_LONG()["cash"].reindex(k.index)           # DTB3 전월말/1200
    kr3 = mc_series("OECD_FINMARK", "KOR", "IR3TIB").shift(1).reindex(k.index) / 1200
    fr = pd.read_csv(FRDEV_F); fr = fr[fr.region == "developed"]
    dev = pd.Series(fr.mkt_tr_pct.values / 100, index=pd.to_datetime(fr.yyyymm.astype(str), format="%Y%m") + pd.offsets.MonthEnd(0)).reindex(k.index)
    pre = (k.index <= "1999-12-31").astype(float)                    # 지수 구간(보수 없음) → D17-B 차감
    uuB = uu - pre * US_ETF_TER / 12
    car = {"A": k["cash"] - us_cash, "B": kr3 - us_cash}              # T2-D11 A: CD91−DTB3 / B: OECD IR3TIB KOR − DTB3 (모두 전월말)
    out = k.assign(us_usd=uu, fx=fx.reindex(k.index), us_cash=us_cash, carryA=car["A"], carryB=car["B"],
                   usB=(1 + uuB) * (1 + fx.reindex(k.index)) - 1, dev_usd=dev, dev=(1 + dev) * (1 + fx.reindex(k.index)) - 1,
                   us_infl=US_LONG()["infl"].reindex(k.index))
    for c in "AB":
        out[f"usH{c}"] = (1 + uu) * (1 + car[c]) - 1
        out[f"usH{c}_B17"] = (1 + uuB) * (1 + car[c]) - 1
        out[f"devH{c}"] = (1 + dev) * (1 + car[c]) - 1
    assert out.notna().all().all(), out.columns[out.isna().any()].tolist()
    return out


def fx64() -> pd.Series:
    f = pd.read_csv(FX64_F, parse_dates=["date"]).set_index("date")["usdkrw_end"]
    return (_me(f) / _me(f).shift(1) - 1).loc[:P.US_END]


def kr1980_panel() -> pd.DataFrame:
    """KR1980 주식판: eq = 코스피 종합 가격(배당 없음 ⚠, 보수 미차감 — 명세 2-1 그대로), us = 미국 USD 총수익(us_tr_monthend)×원/달러(1964~ 파일),
    infl = OECD_PRICES KOR. 현금 없음(→ D5-B 미산출)."""
    eq = P.kospi_px_1980().pct_change(fill_method=None)
    uu = P.us_tr_monthend(); fx = fx64()
    infl = mc_series("OECD_PRICES", "KOR", "cpi_index"); infl = infl / infl.shift(1) - 1
    pre = np.ones(len(uu))                                            # us_tr_monthend는 전 구간 지수 → D17-B 전 구간 차감
    d = pd.DataFrame({"eq": eq, "us": (1 + uu) * (1 + fx) - 1, "usB": (1 + uu - pre * US_ETF_TER / 12) * (1 + fx) - 1, "infl": infl})
    d = d.loc["1980-02":P.US_END].dropna()
    assert len(d) == len(pd.date_range(d.index[0], d.index[-1], freq="ME"))
    return d.assign(cash=np.nan)


def us_panel() -> pd.DataFrame:
    return US_LONG()


def us_krw_panel() -> pd.DataFrame:
    """US 원화판(③만): eq_krw = (1+US eq)(1+원/달러)−1, infl = OECD KOR CPI. 현금 없음."""
    u = US_LONG(); fx = fx64().reindex(u.index)
    infl = mc_series("OECD_PRICES", "KOR", "cpi_index"); infl = (infl / infl.shift(1) - 1).reindex(u.index)
    d = pd.DataFrame({"us": (1 + u["eq"]) * (1 + fx) - 1, "usB": (1 + u["eq"] - US_ETF_TER / 12) * (1 + fx) - 1, "infl": infl}).dropna()
    return d.assign(cash=np.nan)


def swinkels_oecd_panel(ol: dict) -> dict:
    """T2-D13 B: oecd_local_panel의 eq·cash·infl + bd = Swinkels 실측 10년 TR(~2022-12). Swinkels 9개국 중 OECD 패널에 있는 나라만(AUS는 월 CPI 없어 패널 밖)."""
    m = pd.read_csv(MC_F, usecols=["source", "iso3", "freq", "period", "variable", "value"], dtype={"value": float}, low_memory=False)
    m = m[(m.source == "Swinkels2023") & (m.variable == "bond_tr_10y_m") & (m.freq == "M")]
    bd = m.pivot(index="period", columns="iso3", values="value"); bd.index = pd.to_datetime(bd.index) + pd.offsets.MonthEnd(0)
    iso3 = {k: v for k, v in P._ISO3.items()}; stems = {iso: st for st, iso in P.OECD_ISO.items()}
    out = {}
    for name, df in ol.items():
        i3 = iso3[P.OECD_ISO[name.rsplit("_", 1)[0]]]
        if i3 not in bd:
            continue
        d = df.assign(bd=bd[i3].reindex(df.index))
        ok = d.notna().all(1).to_numpy().astype(int); e = np.flatnonzero(np.diff(np.r_[0, ok, 0]))
        for k, (a, b) in enumerate(zip(e[::2], e[1::2])):
            if b - a >= 12:
                out[f"{name}_s{k}"] = d.iloc[a:b]
    return out


def glide(kind: str) -> np.ndarray:
    """T2-D10 A: 매년 계단(잔여 −30+⌊t/12⌋) / B: 월 선형보간(잔여 −30+t/12). mean5 % → 소수, 길이 360."""
    g = pd.read_csv(GLIDE_F).set_index("years_rel_target")["mean5"] / 100
    t = np.arange(T)
    return g.loc[-30 + t // 12].to_numpy() if kind == "A" else np.interp(-30 + t / 12, g.index.to_numpy(float), g.to_numpy())


# ── 경로 인덱스 ───────────────────────────────────────────────────────
def boot_idx(n_rows: int, n: int, blk: float, seed: int, fast: bool = False, length: int = T) -> np.ndarray:
    """단일국 stationary bootstrap 인덱스(n,T). 기본 = bootstrap.paired_resample_paths(명세 3-4)에 0..n_rows−1 계열을 넣어 인덱스를 받음.
    fast=True = pilot7.pooled_paths(조각 1개 → 끝에서 처음으로 = 원형 연결, 같은 알고리즘의 벡터화판; MDE 단계 속도용)."""
    ix = pd.Series(np.arange(n_rows, dtype=float))
    if fast:
        return P.pooled_paths({"x": ix.to_frame("i")}, ["i"], n, length, blk, seed)[0].astype(np.int64)
    return paired_resample_paths([ix], n, length, blk, seed)[0].astype(np.int64)


def pooled_idx(panel: dict, n: int, blk: float, seed: int):
    """ACO 풀 bootstrap(pilot7.pooled_paths)으로 '전체 연결 행 번호'를 뽑음 → (idx, 연결 패널)."""
    flat = pd.concat(list(panel.values()), ignore_index=True)
    off = np.r_[0, np.cumsum([len(v) for v in panel.values()])[:-1]]
    pan = {k: v.assign(_gi=np.arange(len(v), dtype=float) + o) for (k, v), o in zip(panel.items(), off)}
    return P.pooled_paths(pan, ["_gi"], n, T, blk, seed)[0].astype(np.int64), flat


def windows(n_rows: int, step: int = 1) -> np.ndarray:
    s = np.arange(0, n_rows - T + 1, step)
    return s[:, None] + np.arange(T)


# ── 포트폴리오·금액 ─────────────────────────────────────────────────────
def port_R(X: np.ndarray, W: np.ndarray, annual: bool, reb=None, fee: float = P.FEE_PENSION) -> np.ndarray:
    """X (n,T,k) 구성 수익, W (T,k) 목표 비중. 매월(T2-D7 A, pilot7.mix_ret처럼 월초 목표비중) 또는 연 1회(B, reb 달만 목표로).
    매매비용 = 회전율(Σ|목표−표류 비중|) × FEE_PENSION, 리밸런싱한 달 수익에서 차감."""
    n, Tn, k = X.shape
    if k == 1:
        return X[..., 0]
    if not annual:
        R = (X * W).sum(-1)
        drift = W * (1 + X) / (1 + R)[..., None]
        to = np.abs(W[1:] - drift[:, :-1]).sum(-1)
        R[:, 1:] -= fee * to
        return R
    reb = np.broadcast_to(np.arange(Tn) % 12 == 0 if reb is None else reb, (n, Tn))
    cur = np.broadcast_to(W[0], (n, k)).copy(); R = np.empty((n, Tn))
    for t in range(Tn):
        if t > 0:
            m = reb[:, t]
            to = np.abs(W[t] - cur).sum(-1) * m
            cur[m] = W[t]
        else:
            to = 0.0
        R[:, t] = (cur * X[:, t]).sum(-1) - fee * to
        cur = cur * (1 + X[:, t]) / (1 + (cur * X[:, t]).sum(-1))[:, None]
    return R


CAP = P.CREDIT_CAP / P.CONTRIB_YEAR * 12; LIM = P.CONTRIB_LIMIT / P.CONTRIB_YEAR * 12; E = CAP - 12   # T4와 같은 정의(T4 노트북 50~52행)


def sim_after_tax(R, Cr, c):
    """T2-D5 B: T4 sim('A')(notebooks/pilot7/T4_첫하락장네선택.py 55~82행)과 같은 식 — 납입 c_t(경로×월)로 일반화.
    공제 16.5% 연말 환급·계좌 밖 현금 E·현금은 CD 세후(15.4%), 연 납입한도 초과분은 계좌 밖 현금, 연금소득세 5.5%."""
    n = R.shape[0]; V, N, yc, cy = (np.zeros(n) for _ in range(4)); cash = np.full(n, E)
    Ca = Cr * (1 - P.TAX_FINANCIAL)
    for t in range(R.shape[1]):
        if t % 12 == 0:
            yc[:] = 0; cy[:] = 0
        x = c[:, t]; xe = np.minimum(x, np.maximum(LIM - yc, 0)); cr = np.minimum(xe, np.maximum(CAP - yc, 0))
        V += xe; N += xe - cr; yc += xe; cy += cr; cash += x - xe
        V *= 1 + R[:, t]; cash *= 1 + Ca[:, t]
        if t % 12 == 11:
            cash += P.CREDIT_LOW * cy
    return V - P.PENSION_UNDER70 * np.maximum(V - N, 0) + cash


def ratio(R, I, Cr, d5: str, d6: str) -> np.ndarray:
    """실질 금액 ÷ 실질 납입 누계(명세 3-1·3-3). d5 A 계좌 세전 / B T4 세후(+E) / C 일시금 W_real; d6 A 명목 고정 / B 실질 고정."""
    D = np.cumprod(1 + I, axis=1); Dp = np.c_[np.ones(len(I)), D[:, :-1]]
    if d5 == "C":
        return np.prod(1 + R, axis=1) / D[:, -1]
    c = np.ones_like(R) if d6 == "A" else Dp
    if d5 == "A":
        G = np.cumprod((1 + R)[:, ::-1], axis=1)[:, ::-1]
        return (c * G).sum(1) / D[:, -1] / (c / Dp).sum(1)
    return sim_after_tax(R, Cr, c) / D[:, -1] / ((c / Dp).sum(1) + E)


def summ(x: np.ndarray) -> dict:
    p = float((x < 1).mean())
    return {"p": p, "mc_se": float(P.mc_se(p, len(x))), "P5": float(np.quantile(x, .05)), "P50": float(np.median(x)), "n": len(x)}


# ── 포트폴리오 변형(명세 8절 한국 33개 등) ────────────────────────────────
def variants_kr(dev: bool = True) -> list[dict]:
    """각 변형: name·port(①~⑤)·결정 태그·comps·W(T,k)·annual. 추천안 = 모든 태그 A."""
    gl = {g: glide(g) for g in "AB"}; one = np.ones(T)
    c = lambda *w: np.column_stack([np.broadcast_to(x, T) for x in w])
    out = [dict(port="①", tags={}, comps=["eq"], W=c(one), annual=False)]
    for d7 in "AB":
        out.append(dict(port="②", tags={"D7": d7}, comps=["eq", "bd"], W=c(W60, 1 - W60), annual=d7 == "B"))
    for d17 in "AB":
        out.append(dict(port="③", tags={"D17": d17}, comps=["us" if d17 == "A" else "usB"], W=c(one), annual=False))
        for d11 in "AB":
            out.append(dict(port="③H", tags={"D17": d17, "D11": d11}, comps=[f"usH{d11}" + ("" if d17 == "A" else "_B17")], W=c(one), annual=False))
    # 정정 r1 #1: ④ × D17, ⑤(S=33/67) × D8 × D17 추가. D8=B(French developed)엔 S&P500 ETF 보수(D17)가 해당 없음 → D17=A 한 칸만.
    F = {("A", "A"): "us", ("A", "B"): "usB", ("B", "A"): "dev"}
    FC = [k for k in F if dev or k[0] == "A"]
    for d8, d17 in FC:
        for d7 in "AB":
            out.append(dict(port="④", tags={"D8": d8, "D17": d17, "D7": d7}, comps=["eq", F[d8, d17]], W=c(*W33), annual=d7 == "B"))
    for d8 in ("AB" if dev else "A"):
        for d7 in "AB":
            for d11 in "AB":
                out.append(dict(port="④H", tags={"D8": d8, "D7": d7, "D11": d11}, comps=["eq", ("usH" if d8 == "A" else "devH") + d11], W=c(*W33), annual=d7 == "B",
                                label="④H(USD 금리차만, 미국 외 통화 비헤지)" if d8 == "B" else "④H"))
    for d10 in "AB":
        for d7 in "AB":
            g = gl[d10]
            for d8, d17 in FC:
                out.append(dict(port="⑤", tags={"D9": "A", "D8": d8, "D17": d17, "D10": d10, "D7": d7}, comps=["eq", F[d8, d17], "bd"], W=c(g * W33[0], g * W33[1], 1 - g), annual=d7 == "B"))
            out.append(dict(port="⑤", tags={"D9": "B", "D10": d10, "D7": d7}, comps=["eq", "bd"], W=c(g, 1 - g), annual=d7 == "B"))
            out.append(dict(port="⑤", tags={"D9": "C", "D10": d10, "D7": d7}, comps=["eq", "us", "bd"], W=c(g * S35[0], g * S35[1], 1 - g), annual=d7 == "B"))
    for v in out:
        v["name"] = v["port"] + "".join(f"|{k}={x}" for k, x in sorted(v["tags"].items()))
        v.setdefault("label", v["port"])
    return out


def variants_eqbd(with_eq: bool = True) -> list[dict]:
    """①·②(D7)·⑤(S = 자국 주식, D10×D7; D9 태그 없음) — 미국 달러판·OECD 현지판."""
    out = []
    for v in variants_kr(dev=False):
        if (v["port"] == "①" and with_eq) or v["port"] == "②":
            out.append(v)
        elif v["port"] == "⑤" and v["tags"]["D9"] == "B":
            t = {k: x for k, x in v["tags"].items() if k != "D9"}
            out.append(dict(v, tags=t, name="⑤" + "".join(f"|{k}={x}" for k, x in sorted(t.items()))))
    return out


def is_rec(v) -> bool:
    return all(x == "A" for x in v["tags"].values())


def run_variant(arr: np.ndarray, cols: dict, idx: np.ndarray, v: dict, d5s="ABC", d6s="AB", reb=None, shift: dict | None = None, chunk: int = 20_000) -> dict:
    """arr (행,열) 패널, idx (n,T) 행 번호 → {(d5,d6): 비율 배열}. shift = {열: 대체 열 배열} (위약 P2 원형 이동, P4 미국 CPI). 메모리 위해 경로를 chunk씩."""
    get = lambda nm: (shift or {}).get(nm, arr[:, cols[nm]] if nm in cols else np.full(len(arr), np.nan))
    out = {}
    for a in range(0, len(idx), chunk):
        ix = idx[a:a + chunk]
        X = np.stack([get(nm)[ix] for nm in v["comps"]], -1)
        R = port_R(X, v["W"], v["annual"], reb)
        I, Cr = get("infl")[ix], get("cash")[ix]
        for d5 in d5s:
            for d6 in (d6s if d5 != "C" else "A"):
                if d5 == "B" and np.isnan(Cr).any():
                    continue
                out.setdefault((d5, d6), []).append(ratio(R, I, Cr, d5, d6))
    out = {k: np.concatenate(x) for k, x in out.items()}
    if ("C", "A") in out and "B" in d6s:
        out[("C", "B")] = out[("C", "A")]                            # 일시금은 납입 방식과 무관(같은 값)
    return out


def arr_cols(df: pd.DataFrame):
    return df.to_numpy(float), {c: i for i, c in enumerate(df.columns)}


# ---- 판정 규칙(조정자 보완 3·4 + r2 지시 a~f): 문장·⚠·실효 단위를 여기 한 곳에서만 정한다 ----
DESCRIPTIVE = {("T2-D2", "120(한"): "명세 7절 D2-C '한 역사 재배열' 표시 병기", ("T2-D5", "C"): "명세 9절 D5-C 'ACO 정의 맞춘 참고'"}   # (d) ⚠ 판정 제외


def is_descriptive(dec: str, cand: str) -> str:
    """명세가 기술용·참고로 정한 후보면 그 근거 문구, 아니면 ''."""
    return next((w for (d, c), w in DESCRIPTIVE.items() if d == dec and str(cand).startswith(c)), "")


def n_eff(sample: str, wc: pd.DataFrame) -> int:
    """(보완 3) 실효 독립 단위: 단일국 = 안 겹친 30년 창 수(T2_window_counts), 다국가(French·OECD) = 1(같은 달력 구간, 정정 r1 #9)."""
    z = wc[(wc["묶음"] == "단일") & wc["표본"].str.startswith(sample)]
    return int(z["안겹친창"].iloc[0]) if len(z) == 1 else 1


def mde_cross(delta: float, mde: float):
    """(a) MDE 넘나듦만: MDE가 0·NaN(SD=0)이면 None(비교 불가) — 다른 기준은 그대로 적용."""
    return None if not (np.isfinite(mde) and mde > 0 and np.isfinite(delta)) else bool(abs(delta) > mde)


def sentence(main: bool, delta: float, mde: float, warn: str, neff: int) -> str:
    """(보완 4) 요약 문장 규칙 하나. 대안 행 → '대안 행(판정 아님)'(c). ⚠ → '선택에 따라 달라짐'. |Δ|<MDE → '식별 안 됨'. 실효 단위 1 → '검정력 없음, 기술만'(b)."""
    if not main:
        return "대안 행(판정 아님)"
    x = mde_cross(delta, mde)
    s = "비교 불가(MDE 0)" if x is None else (f"Δ {delta:+.4f}, MDE {mde:.4f}보다 큼(판정 아님)" if x else "식별 안 됨")
    if warn:
        s = f"선택에 따라 달라짐(⚠ {warn}) · 주 칸: {s}"
    return s + (" — 검정력 없음, 기술만(실효 독립 단위 1)" if neff <= 1 else "")


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    z = np.zeros((3, T))
    assert np.allclose(ratio(z, z, z, "A", "A"), 1) and np.allclose(ratio(z, z, z, "A", "B"), 1)          # 수익 0 → 실질 금액 = 실질 납입
    I = np.full((2, T), 0.002)
    assert np.allclose(ratio(I, I, I, "A", "B"), 1) and np.allclose(ratio(I, I, I, "C", "A"), 1)          # 수익 = 물가 → 1
    assert abs(sim_after_tax(np.zeros((1, 24)), np.zeros((1, 24)), np.ones((1, 24)))[0] - (24 + E + 0.165 * 24 - 0.055 * 24)) < 1e-9   # T4 85행 단언과 같음
    assert len(glide("A")) == T and glide("A")[0] == glide("A")[11] and abs(glide("A")[0] - 0.7844) < 1e-12
    X = rng.normal(0, .05, (4, T, 2)); W = np.tile([.6, .4], (T, 1))
    Rm = port_R(X, W, False, fee=0); assert np.allclose(Rm, (X * W).sum(-1))
    Ra = port_R(X, W, True, fee=0); assert np.allclose(Ra[:, 0], Rm[:, 0]) and np.allclose(Ra[:, 12], Rm[:, 12])
    ix = boot_idx(50, 200, 1e9, 1, fast=True)                                                           # 블록 무한대: 원형 연속
    assert ((np.diff(ix, axis=1) % 50) == 1).all()
    ix = boot_idx(50, 20, 1e9, 1); assert ((np.diff(ix, axis=1) % 50) == 1).all()
    assert mde_cross(0.1, 0.0) is None and mde_cross(0.1, np.nan) is None and mde_cross(0.1, 0.05) is True and mde_cross(-0.01, 0.05) is False
    assert sentence(False, 1, 0.1, "", 5) == "대안 행(판정 아님)" and sentence(True, 0.01, 0.1, "", 2) == "식별 안 됨"
    assert sentence(True, 0.01, 0.1, "T2-D9", 1).startswith("선택에 따라 달라짐") and sentence(True, 0.01, 0.1, "", 1).endswith("기술만(실효 독립 단위 1)")
    assert is_descriptive("T2-D2", "120(한 역사 재배열 표시)") and not is_descriptive("T2-D2", "120(ACO 기본)") and is_descriptive("T2-D5", "C") and not is_descriptive("T2-D5", "B")
    wc = pd.DataFrame(dict(묶음=["단일", "단일", "OECD"], 표본=["KR1991", "US1965(달러)", "UK_0"], 안겹친창=[1, 2, 1]))
    assert n_eff("KR1991", wc) == 1 and n_eff("US1965", wc) == 2 and n_eff("OECD 17개국", wc) == 1
    print("t2_core self-check ok")
