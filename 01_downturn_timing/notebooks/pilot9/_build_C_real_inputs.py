# -*- coding: utf-8 -*-
"""pilot9 C 재시작(실제 자료) 입력 계열 + 점검표 — DECISION_LOG 2026-10-17 'C 재시작 표본 = 실제 펀드 + 실제 지수'.

만드는 것(결과변수 없음: 안정형 vs TDF·전환 이득·사건 뒤 수익 비교는 계산하지 않는다):
  1. 실제 TDF 2055 연금저축 클래스(C-Pe) 월 총수익(결산 분배 보정) — 운용사별·H/UH별·5대 단순평균
  2. 공시 글라이드 × 실제 지수 − 공시 C-Pe 보수 TDF 월 수익(2004-07~) + 글라이드·보수 잔여기간표 + 실제 TDF와 겹침 대조
  3. 실제 하락장 날짜표(pilot9.dd_starts, −20%, 재무장 +20%) + feasibility dd_events_kr_us.csv 대조
  4. 점검표
노트북에서: sys.path에 이 폴더를 넣고 `from _build_C_real_inputs import tdf_index, glide_w, fee_pct, load_comps` (실행 부분은 __main__ 안).
실행: (cmd) set "PYTHONPATH=" 뒤  set PYTHONIOENCODING=utf-8 & python notebooks\\pilot9\\_build_C_real_inputs.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pension_lab import pilot7 as P7, pilot9 as P9, paths, io  # noqa: E402
from pension_lab.t2_d import settle_return  # noqa: E402
from pension_lab.fetch.kofia_h_uh_nav import _segF  # noqa: E402

OUT = P9.OUT / "C_real_20261017" / "inputs"
ME = pd.offsets.MonthEnd(0)
ASOF = "2026-10-13"                     # KOFIA 수집 끝(pilot9add) → 2026-10 미완성 월 제외
W_KR = 0.152                            # DL A-2: TDF 주식 중 국내 몫
TARGET = 2055
# D-1 대표 계열(C_redesign v2 4-1·D-C5: 5대 2055 = KB온국민·삼성글로벌액티브·신한마음편한·미래에셋전략배분·한국투자TDF알아서)
FUNDS = {"KB_H": "KB|KB온국민TDF|2055|H", "KB_UH": "KB|KB온국민TDF|2055|UH", "삼성_H": "삼성|삼성글로벌액티브TDF|2055|H",
         "신한": "신한|신한마음편한TDF|2055|none", "미래에셋": "미래에셋|미래에셋전략배분TDF|2055|none",
         "한국투자_H": "한국투자|한국투자TDF알아서|2055|H", "한국투자_UH": "한국투자|한국투자TDF알아서|2055|UH"}
MGR = {"KB_H": "KB", "KB_UH": "KB", "삼성_H": "삼성", "신한": "신한", "미래에셋": "미래에셋", "한국투자_H": "한국투자", "한국투자_UH": "한국투자"}
AVG = {"H": ["KB_H", "삼성_H", "신한", "미래에셋", "한국투자_H"],          # 헤지 판본 없는 계열(신한·미래)은 양쪽에 같이
       "UH": ["KB_UH", "신한", "미래에셋", "한국투자_UH"]}                # 삼성은 H판만 있어 UH 평균에서 뺌(데이터 감사 H-1, 2026-10-17)
FT = paths.FUND_TDF
NAV_SRC = [  # 같은 (코드, 날짜)가 여러 파일에 있으면 앞 파일 우선(늦게 받은 것 먼저)
    (FT / "tdf_nav_kofia_pilot9add_20261013.csv", "navfull"), (FT / "h_uh_pairs" / "kofia_h_uh_navfull_20261010b.csv", "huh"),
    (FT / "h_uh_pairs" / "kofia_h_uh_navfull_20261010.csv", "huh"), (FT / "kofia_navfull_official_extra_v2_20260929.csv", "navfull"),
    (FT / "kofia_navfull_official_extra_20260929.csv", "navfull"), (FT / "kofia_navfull_tdf_20260928.csv", "navfull"),
    (FT / "kofia_navfull_defaultoption_20260928.csv", "navfull")]


def csv(df, name):
    df.to_csv(OUT / name, encoding="utf-8-sig", index=not isinstance(df.index, pd.RangeIndex)); return df


# ───────────── 1. 실제 TDF 기준가 ─────────────
def class_codes() -> pd.DataFrame:
    """TDF 마스터의 pension_class_codes에서 C-Pe(주)와 C-P(앞 잇기 후보) 코드."""
    m = pd.read_csv(paths.PROCESSED / "pilot9_tdf_master_20261013.csv", encoding="utf-8-sig").set_index("fund_key")
    rows = []
    for lab, k in FUNDS.items():
        cl = [x.split(":", 1)[::-1] for x in m.loc[k, "pension_class_codes"].split("|")]
        norm = {re.sub(r"[-\s]", "", c.upper()): v for c, v in cl}              # 'Cpe퇴직연금'·'C-P2e'는 CPE가 아님(정확히 일치만)
        assert "CPE" in norm and sum(re.sub(r"[-\s]", "", c.upper()) == "CPE" for c, _ in cl) == 1, (lab, cl)
        rows.append(dict(label=lab, fund_key=k, manager=MGR[lab], hedge=k.split("|")[-1], cpe=norm["CPE"], cp=norm.get("CP"), est=m.loc[k, "est_min"]))
    return pd.DataFrame(rows)


def load_nav(codes) -> tuple[pd.DataFrame, pd.DataFrame]:
    """여러 KOFIA 원자료를 합침(앞 파일 우선) + 파일 간 같은 날 기준가 불일치 점검."""
    parts = []
    for i, (f, kind) in enumerate(NAV_SRC):
        if not f.exists():
            continue
        for ch in pd.read_csv(f, dtype=str, encoding="utf-8-sig", chunksize=500_000):
            ch = ch[ch.fund_code.isin(codes)]
            if not len(ch):
                continue
            if kind == "huh":
                ch = ch.rename(columns={"v1": "date", "v2": "nav", "v3": "chg", "v5": "v5_setamt"})
            parts.append(pd.DataFrame(dict(code=ch.fund_code, date=pd.to_datetime(ch.date.str.replace("-", ""), format="%Y%m%d"),
                                           nav=pd.to_numeric(ch.nav), v3=pd.to_numeric(ch.chg, errors="coerce"),
                                           setamt=pd.to_numeric(ch.v5_setamt, errors="coerce"), pri=i, src=f.name)))
    A = pd.concat(parts, ignore_index=True)
    g = A.groupby(["code", "date"]).nav
    chk = A.assign(n_src=g.transform("size"), spread=g.transform("max") - g.transform("min"))
    chk = chk[chk.n_src > 1].groupby("code").agg(dup_days=("date", "nunique"), nav_mismatch_days=("spread", lambda s: int((s > 0).sum())),
                                                 max_spread=("spread", "max")).reset_index()
    D = A.sort_values(["code", "date", "pri"]).drop_duplicates(["code", "date"]).reset_index(drop=True)
    return D, chk


def settlements(codes) -> pd.DataFrame:
    """KOFIA 결산공시(rdmp_TDF_20261010b.csv: v4 회계기말, v7 결산 기준가, v9 결산후 기준가)."""
    R = pd.read_csv(FT / "h_uh_pairs" / "settle" / "rdmp_TDF_20261010b.csv", dtype=str, encoding="utf-8-sig")
    R = R[R.v11.isin(codes) & R.v10.isin(["결산", "분배"])]
    return pd.DataFrame(dict(code=R.v11, fiscal_end=pd.to_datetime(R.v4, format="%Y%m%d"), v7=pd.to_numeric(R.v7), v9=pd.to_numeric(R.v9),
                             kind=R.v10)).drop_duplicates(["code", "fiscal_end"]).sort_values(["code", "fiscal_end"])


def daily_tr(D: pd.DataFrame, S: pd.DataFrame, code: str) -> tuple[pd.Series, pd.DataFrame]:
    """설정원본 > 0 첫날부터 일별 총수익. 결산 반영일(회계기말 다음 자료일)은 T2-1 덧셈식 settle_return(전일, 당일, v7−v9).
    유효 수익 = act2(전일·당일 설정원본 > 0) ∩ cont(직전 행 = KOFIA 영업일 합집합의 직전일) — kofia_h_uh_nav._daily와 같은 규칙.
    그 밖의 날(휴면 뒤 재설정 1,000원 등)은 NaN. 반환: 일별 수익, 결산일 점검표(곱셈식·v3 정규화 조정액과의 차 포함)."""
    cal = pd.DatetimeIndex(sorted(D.date.unique())); pc = pd.Series(cal[:-1], index=cal[1:])
    x = D[D.code == code].sort_values("date").reset_index(drop=True)
    x = x[x.date >= x.loc[x.setamt > 0, "date"].min()].reset_index(drop=True)
    x["dnav"] = x.nav.diff(); x["cont"] = x.date.shift().eq(x.date.map(pc))
    x["act2"] = (x.setamt > 0) & (x.setamt.shift() > 0) & x.cont
    r = (x.nav / x.nav.shift() - 1).where(x.act2)
    s = S[(S.code == code) & (S.fiscal_end >= x.date.iloc[0])]          # 클래스 활성 전 회계기말은 해당 없음
    sd =[x.date[x.date > e].min() for e in s.fiscal_end]
    y = _segF(x, [d for d in sd if pd.notna(d)])                    # v3(분배 재투자 수정기준가 변화)로 본 조정액 — 점검용
    rows = []
    for (_, e), d in zip(s.iterrows(), sd):
        if pd.isna(d):
            rows.append(dict(code=code, fiscal_end=e.fiscal_end, settle_date=pd.NaT, note="반영일 미도래·자료 끝")); continue
        k = int(x.index[x.date == d][0]); prev, now = x.nav[k - 1], x.nav[k]
        adj = e.v7 - e.v9
        r[k] = settle_return(prev, now, adj) if x.act2[k] else np.nan
        rows.append(dict(code=code, fiscal_end=e.fiscal_end, settle_date=d, v7=e.v7, v9=e.v9, adj=adj, nav_prev=prev, nav_settle=now,
                         prev_minus_v7=prev - e.v7, r_add=r[k], r_mult=now * e.v7 / e.v9 / prev - 1,
                         r_v3=settle_return(prev, now, y.adj_norm[k]) if pd.notna(y.adj_norm[k]) else np.nan,
                         active=bool(x.act2[k]), note=""))
    # 결산일이 아닌데 v3로 분배성 점프가 검출된 날(공시 결산 누락 의심)
    extra = y[y.event & ~y.date.isin(sd)]
    for _, z in extra.iterrows():
        rows.append(dict(code=code, settle_date=z.date, nav_prev=z.nav - z.dnav, nav_settle=z.nav, note=f"공시 결산 아님·v3 검출(adj_norm={z.adj_norm:.3f})"))
    return pd.Series(r.values, index=x.date, name=code), pd.DataFrame(rows)   # 첫날(기준) 수익 = NaN


def to_monthly(r: pd.Series, cal: pd.DatetimeIndex, lag: int = 0) -> pd.Series:
    """일별 → 월 수익 = 그 달 일별 (1+r) 곱 − 1. 그 달 KOFIA 영업일(cal) 전부에 유효 수익이 있을 때만(아니면 NaN: 설정 달·휴면·자료 공백).
    lag=k: 기준가 반영 시차 점검용 — 월 경계를 k영업일 뒤로(월 t = t월 말 다음 k번째 영업일 기준가까지). 첫날(기준일)의 달 제외, 2026-10 미완성 월 제외."""
    key = pd.Series(cal[np.maximum(np.arange(len(cal)) - lag, 0)].to_period("M"), index=cal)
    r = r.iloc[1:]
    per, cper = pd.PeriodIndex(key.reindex(r.index)), pd.PeriodIndex(key)
    full = pd.Series(cal, index=cal).groupby(cper).size()
    m = r.groupby(per).agg(lambda s: np.prod(1 + s) - 1 if s.notna().all() else np.nan)
    m[r.groupby(per).size() != full.reindex(m.index)] = np.nan
    m.index = m.index.to_timestamp("M")
    return P9.complete_months(m, ASOF)


def fee_table() -> pd.DataFrame:
    f = pd.read_csv(P9.OUT / "fee_pclass_20261016" / "pclass_fee_table.csv", parse_dates=["start", "end"])
    return f.assign(total_fee_pct=pd.to_numeric(f.total_fee_pct), synthetic_pct=pd.to_numeric(f.synthetic_pct))


def fee_pct(manager: str, year, grp: str = "CPe", col: str = "total_fee_pct", F: pd.DataFrame | None = None) -> np.ndarray:
    """공시 단계 보수(연 %) — 달력 연도 year(배열). 2026 이전은 첫 단계(현행 공시, 과거 보수 아님 ⬜)."""
    F = fee_table() if F is None else F
    f = F[(F.manager == manager) & (F.grp == grp)].sort_values("start")
    y = np.clip(np.atleast_1d(year), f.start.dt.year.min(), None)
    return np.array([f.loc[(f.start.dt.year <= v) & (f.end.dt.year >= v), col].iloc[0] for v in y], float)


def splice_check(D, S, cc) -> pd.DataFrame:
    """C-Pe보다 C-P가 먼저 있으면: 겹침 구간 일별 수익 차(C-Pe − C-P)의 연율(달력일 기준)과 공시 보수 차(C-P − C-Pe 총보수) 대조."""
    F = fee_table(); rows = []
    for _, c in cc.iterrows():
        if not c.cp:
            rows.append(dict(label=c.label, note="C-P 코드 없음")); continue
        a, _ = daily_tr(D, S, c.cpe); b, _ = daily_tr(D, S, c.cp)
        j = pd.concat([a.rename("pe"), b.rename("p")], axis=1).dropna()
        days = (j.index[-1] - j.index[0]).days
        gap = (np.log1p(j.pe).sum() - np.log1p(j.p).sum()) / days * 365 * 100
        fd = fee_pct(c.manager, 2026, "CP", F=F)[0] - fee_pct(c.manager, 2026, F=F)[0]
        rows.append(dict(label=c.label, cpe=c.cpe, cp=c.cp, cpe_first=a.index[0].date(), cp_first=b.index[0].date(),
                         months_gained=max(0, (a.index[0].to_period("M") - b.index[0].to_period("M")).n), overlap_days=len(j),
                         gap_obs_pctpa=round(gap, 3), fee_diff_prospectus_pctpa=round(fd, 3), daily_corr=round(j.pe.corr(j.p), 5)))
    return pd.DataFrame(rows)


def fill_cp(pe: pd.Series, p: pd.Series, fee_diff_pct: float) -> pd.Series:
    """C-Pe 유효 수익이 없는 날(설정 전·휴면)을 같은 펀드 C-P 수익 + 공시 보수 차(연 %, 달력일 비례)로 채움. ⬜ 사용 여부 회원 결정."""
    days = pd.Series(p.index, index=p.index).diff().dt.days
    q = p + fee_diff_pct / 100 * days / 365
    out = pe.reindex(pe.index.union(p.index))
    return out.fillna(q.reindex(out.index))


def assemble(monthly: dict) -> pd.DataFrame:
    M = pd.DataFrame(monthly).sort_index().rename_axis("month_end")
    for sfx in ("", "_fillCP"):
        for h, labs in AVG.items():
            cols = [f"{l}{sfx}" if f"{l}{sfx}" in M else l for l in labs]
            M[f"avg_{h}{sfx}"] = M[cols].mean(axis=1); M[f"n_{h}{sfx}"] = M[cols].notna().sum(axis=1)
            M[f"avg_{h}{sfx}_all5"] = M[f"avg_{h}{sfx}"].where(M[f"n_{h}{sfx}"] == 5)
    return M


# ───────────── 2. 실제 지수 TDF ─────────────
def load_comps() -> pd.DataFrame:
    """월 수익: k200(2011-01까지 가격+KOSPI200 배당수익률(pilot7.kr_div_yield), 2011-02~ DataGuide KOSPI200 TR),
    dev_krw(French Developed USD 총수익 × ECOS 원/달러 월말), stk(0.152·k200 + 0.848·dev_krw), bd(kr_bd 국고채 TR 2004-07~), kospi(가격)."""
    dg = pd.read_csv(paths.DATAGUIDE / "dg_kospi_k200_tr_daily_19800104.csv", index_col=0, parse_dates=True)
    tr = P9.complete_months(dg.kospi200_tr.dropna().resample("ME").last().pct_change().dropna(), "2026-10-08")
    k200 = pd.concat([(P7.kospi200_px() + P7.kr_div_yield("dataguide")).loc[:"2011-01"], tr.loc["2011-02":]])
    reg = pd.read_csv(paths.RAW / "global_equity_20261016" / "french_region_mkt_monthly_usd.csv", encoding="utf-8-sig")
    reg["date"] = pd.to_datetime(reg.yyyymm.astype(str), format="%Y%m") + ME
    dev = reg[reg.region == "developed"].set_index("date").mkt_tr_pct / 100
    fx = pd.read_csv(paths.RAW / "kr_hist_20261016" / "kr_usdkrw_monthly_1964.csv", encoding="utf-8-sig", parse_dates=["date"]).set_index("date").usdkrw_end
    fx.index = fx.index + ME
    dev_krw = ((1 + dev) * (1 + fx.pct_change()) - 1).dropna()
    bd =io.asset_series("kr_bd").resample("ME").last().pct_change(fill_method=None).loc["2004-07":"2026-08"]   # 2026-09는 9/23까지 부분월
    kospi = P9.complete_months(P7.kospi_px_1980().pct_change(fill_method=None).dropna(), "2026-10-08")
    C = pd.DataFrame({"k200": k200, "dev_krw": dev_krw, "bd": bd, "kospi": kospi})
    C["stk"] = W_KR * C.k200 + (1 - W_KR) * C.dev_krw
    return C


def glide_table() -> pd.DataFrame:
    """5대 2055 공시 위험자산 비중(%) → 잔여기간 −30..0년 정수(공시 점 사이 선형 보간, 공시 점 여부 표시) + 5대 평균."""
    g = pd.read_csv(FT / "glidepath_disclosed_prospectus.csv")
    g = g[g.vintage == TARGET].pivot_table(index="years_rel_target", columns="manager", values="risky_pct")
    assert len(g.columns) == 5
    yrs = np.arange(-30, 1)
    T = pd.DataFrame({m: np.interp(yrs, c.dropna().index, c.dropna().values) for m, c in g.items()}, index=pd.Index(yrs, name="years_rel_target"))
    T["mean5"] = T.mean(axis=1)
    for m in g.columns:
        T[f"{m}_disclosed"] = T.index.isin(g[m].dropna().index)
    return T


def glide_w(rel_years, manager: str = "mean5", G: pd.DataFrame | None = None) -> np.ndarray:
    """잔여기간(년, 음수, 연속값) → 위험자산 비중(소수). 공시 범위(−30) 밖은 끝값 고정(⬜ 공시 없음)."""
    g = pd.read_csv(FT / "glidepath_disclosed_prospectus.csv") if G is None else G
    g = g[g.vintage == TARGET].pivot_table(index="years_rel_target", columns="manager", values="risky_pct")
    ms = list(g.columns) if manager == "mean5" else [manager]
    return np.mean([np.interp(rel_years, g[m].dropna().index, g[m].dropna().values) for m in ms], axis=0) / 100


def tdf_index(C: pd.DataFrame, rel_years, manager: str = "mean5", fee_col: str = "total_fee_pct") -> pd.Series:
    """월 수익 = w(잔여기간)·stk + (1−w)·bd − C-Pe 보수/12. rel_years: 스칼라(잔여기간 고정) 또는 'calendar'(빈티지 2055 달력 잔여기간).
    보수 연도 = 2055 + 잔여기간(달력판은 그 달 연도), 2026 이전은 첫 단계. mean5 = 5대 각각 계산 뒤 단순평균."""
    C = C[["stk", "bd"]].dropna()
    if manager == "mean5":
        return pd.concat([tdf_index(C, rel_years, m, fee_col) for m in ("KB", "미래에셋", "삼성", "신한", "한국투자")], axis=1).mean(axis=1).rename("mean5")
    rel = (C.index.year + (C.index.month - 1) / 12 - TARGET).to_numpy(float) if isinstance(rel_years, str) else np.full(len(C), float(rel_years))
    w = glide_w(rel, manager); fee = fee_pct(manager, np.floor(TARGET + rel).astype(int), col=fee_col)
    return pd.Series(w * C.stk.to_numpy() + (1 - w) * C.bd.to_numpy() - fee / 1200, index=C.index, name=manager)


# ───────────── 3. 하락장 날짜표 ─────────────
def dd_detail(ret: pd.Series, name: str, th: float = -0.20, rearm: float | None = P9.REARM) -> pd.DataFrame:
    """pilot9.dd_starts 확인월마다: 고점월, 시작월(고점 다음 달), 첫 돌파월, 확인월, 바닥월(첫 돌파~재무장), 재무장월(바닥 대비 +20%), 회복월(고점 회복)."""
    ret = ret.dropna(); conf = P9.dd_starts(ret, th, rearm=rearm)
    L = pd.Series(np.r_[1.0, np.cumprod(1 + ret.to_numpy())], index=[ret.index[0] - pd.offsets.MonthEnd(1)] + list(ret.index))
    rows, s0 = [], 0
    mo = lambda t: t.strftime("%Y-%m") if pd.notna(t) else ""
    for c in conf:
        jc = L.index.get_loc(c); seg = L.iloc[s0:jc + 1]
        pk = seg.index[len(seg) - 1 - int(np.argmax(seg.to_numpy()[::-1]))]
        jp = L.index.get_loc(pk); dd = L / L[pk] - 1
        assert dd[c] <= th and jc - jp >= P7.BEAR_MIN_MONTHS, (name, c)
        ft = dd.iloc[jp:jc + 1][dd.iloc[jp:jc + 1] <= th].index[0]; jf = L.index.get_loc(ft)
        after = L.iloc[jf:]; lo = after.cummin()
        ra = (after / lo - 1 >= rearm) & (after.index >= c) if rearm is not None else pd.Series(False, index=after.index)
        jr = L.index.get_loc(ra[ra].index[0]) if ra.any() else None
        win = L.iloc[jf:(jr if jr is not None else len(L) - 1) + 1]; tr = win.idxmin()
        rec = L.iloc[jc + 1:][L.iloc[jc + 1:] >= L[pk]]
        rows.append(dict(series=name, th=th, rearm=P9.rearm_name(rearm), peak=mo(pk), start=mo(L.index[jp + 1]), first_cross=mo(ft), confirm=mo(c),
                         trough=mo(tr), dd_at_confirm=round(dd[c], 4), dd_trough=round(L[tr] / L[pk] - 1, 4),
                         rearm_month=mo(L.index[jr]) if jr is not None else "미재무장(자료 끝)", recovery=mo(rec.index[0]) if len(rec) else "미회복(자료 끝)",
                         sample=f"{mo(ret.index[0])}~{mo(ret.index[-1])}"))
        s0 = jr if jr is not None else len(L)
    return pd.DataFrame(rows)


def check_row(name, s: pd.Series, note="") -> dict:
    s = s.dropna(); full = pd.date_range(s.index[0], s.index[-1], freq="ME")
    return dict(series=name, start=s.index[0].strftime("%Y-%m"), end=s.index[-1].strftime("%Y-%m"), n=len(s), missing_months=len(full.difference(s.index)),
                mean_pct=round(s.mean() * 100, 3), sd_pct=round(s.std() * 100, 3), min_pct=round(s.min() * 100, 2), min_month=s.idxmin().strftime("%Y-%m"),
                max_pct=round(s.max() * 100, 2), max_month=s.idxmax().strftime("%Y-%m"), p01_pct=round(s.quantile(.01) * 100, 2), p99_pct=round(s.quantile(.99) * 100, 2), note=note)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    # ── 1. 실제 TDF ──
    cc = csv(class_codes(), "C1_class_codes.csv")
    codes = list(cc.cpe) + [c for c in cc.cp if c]
    D, srcchk = load_nav(codes); csv(srcchk, "C1_check_nav_sources.csv")
    S = settlements(codes); CAL = pd.DatetimeIndex(sorted(D.date.unique()))
    daily, settle_rows = {}, []
    F = fee_table()
    for _, c in cc.iterrows():
        r, st = daily_tr(D, S, c.cpe); daily[c.label] = r; settle_rows.append(st.assign(label=c.label))
        if c.cp:
            rp, st2 = daily_tr(D, S, c.cp); settle_rows.append(st2.assign(label=f"{c.label}(C-P)"))
            fd = fee_pct(c.manager, 2026, "CP", F=F)[0] - fee_pct(c.manager, 2026, F=F)[0]
            daily[f"{c.label}_fillCP"] = fill_cp(r, rp, fd)
    csv(pd.concat(settle_rows, ignore_index=True), "C1_check_settlements.csv")
    pd.DataFrame(daily).rename_axis("date").to_csv(OUT / "C1_real_tdf2055_cpe_daily_ret.csv", encoding="utf-8-sig")
    ML = {k: assemble({l: to_monthly(r, CAL, k) for l, r in daily.items()}) for k in (0, 1, 2)}
    M = csv(ML[0], "C1_real_tdf2055_cpe_monthly.csv")
    for k in (1, 2):
        csv(ML[k], f"C1_real_tdf2055_cpe_monthly_navlag{k}.csv")
    csv(splice_check(D, S, cc), "C1_check_splice_cp.csv")

    # ── 2. 실제 지수 TDF ──
    C = load_comps(); csv(C.rename_axis("month_end"), "C2_components_monthly.csv")
    G = glide_table(); csv(G, "C2_glide_by_remaining_years.csv")
    fee_rows = [dict(years_rel_target=y, manager=m, calendar_year=max(TARGET + y, 2026), cpe_total_fee_pct=fee_pct(m, TARGET + y, F=F)[0],
                     cpe_synthetic_pct=fee_pct(m, TARGET + y, col="synthetic_pct", F=F)[0]) for y in range(-30, 1) for m in ("KB", "미래에셋", "삼성", "신한", "한국투자")]
    csv(pd.DataFrame(fee_rows), "C2_fee_cpe_by_remaining_years.csv")
    base = C.loc["2004-07":"2026-08"]
    X = pd.DataFrame({f"fixed_{y}y_{k}": tdf_index(base, y, fee_col=col) for y in (-30, -20, -10, 0) for k, col in (("total", "total_fee_pct"), ("synth", "synthetic_pct"))})
    for k, col in (("total", "total_fee_pct"), ("synth", "synthetic_pct")):
        X[f"calendar2055_{k}"] = tdf_index(base, "calendar", fee_col=col)
    csv(X.rename_axis("month_end"), "C2_index_tdf_monthly.csv")
    # 겹침 대조(입력 대조, 결과 아님): 운용사별 자기 글라이드·자기 보수 달력판 vs 실제 C-Pe 월 수익, 기준가 반영 시차 0·1·2영업일
    ov = []
    for lag, Mk in ML.items():
        for lab in list(cc.label) + ["avg_H", "avg_UH"]:
            m = "mean5" if lab.startswith("avg") else MGR[lab]
            for k, col in (("total", "total_fee_pct"), ("synth", "synthetic_pct")):
                j = pd.concat([Mk[lab].rename("real"), tdf_index(base, "calendar", m, col).rename("idx")], axis=1).dropna()
                d = j.real - j.idx
                ov.append(dict(real=lab, nav_lag_bdays=lag, index_model=f"{m}·달력2055·{k}", start=j.index[0].strftime("%Y-%m"), end=j.index[-1].strftime("%Y-%m"),
                               n=len(j), corr=round(j.real.corr(j.idx), 4), mean_diff_pctpa=round(d.mean() * 1200, 3), te_pctpa=round(d.std() * np.sqrt(12) * 100, 3),
                               sd_real_pctpa=round(j.real.std() * np.sqrt(12) * 100, 2), sd_idx_pctpa=round(j.idx.std() * np.sqrt(12) * 100, 2)))
    csv(pd.DataFrame(ov), "C2_check_index_vs_real_overlap.csv")
    # KOSPI200 가격+배당 vs 실제 TR(2011-02~): pilot7 KRX K200 배당수익률판과 ECOS 901Y014(코스피) 판
    dg = pd.read_csv(paths.DATAGUIDE / "dg_kospi_k200_tr_daily_19800104.csv", index_col=0, parse_dates=True)
    tr = P9.complete_months(dg.kospi200_tr.dropna().resample("ME").last().pct_change().dropna(), "2026-10-08").loc["2011-02":]
    px = dg.kospi200.dropna().resample("ME").last().pct_change().loc[tr.index]
    ec = pd.read_csv(paths.RAW / "kr_hist_20261016" / "ecos_901Y014_kospi_dy_M.csv", encoding="utf-8-sig", parse_dates=["date"]).set_index("date").value / 1200
    kc = []
    for nm, alt in (("가격+KRX K200 배당(pilot7)", px + P7.kr_div_yield("dataguide").reindex(tr.index)), ("가격+ECOS 901Y014 코스피", px + ec.reindex(tr.index))):
        j = pd.concat([tr.rename("tr"), alt.rename("alt")], axis=1).dropna(); d = j.alt - j.tr
        kc.append(dict(proxy=nm, start=j.index[0].strftime("%Y-%m"), end=j.index[-1].strftime("%Y-%m"), n=len(j), corr=round(j.tr.corr(j.alt), 5),
                       mean_diff_pctpa=round(d.mean() * 1200, 3), te_pctpa=round(d.std() * np.sqrt(12) * 100, 3)))
    csv(pd.DataFrame(kc), "C2_check_k200_pre2011_proxy.csv")

    # ── 3. 하락장 ──
    sig = {"KOSPI_px": C.kospi, "K200_TR": C.k200, "주식묶음_UH": C.stk, "실제TDF_avg_H": M.avg_H, "실제TDF_avg_UH": M.avg_UH,
           "실제TDF_avg_H_fillCP": M.avg_H_fillCP, "실제TDF_avg_UH_fillCP": M.avg_UH_fillCP}
    E = pd.concat([dd_detail(s, n) for n, s in sig.items()], ignore_index=True)
    csv(E, "C3_dd_events.csv")
    old = pd.read_csv(P9.OUT / "feasibility" / "dd_events_kr_us.csv", encoding="utf-8-sig")
    o = old[(old.market == "KR_kospi_px_1980") & (old.th == -0.2) & (old.rearm == "re20")].iloc[0]
    oe, ne = set(o.event_months.split(";")), set(E[E.series == "KOSPI_px"].confirm)
    csv(pd.DataFrame([dict(series="KOSPI_px", old_sample=f"{o.start}~{o.end}", old_n=o.n_events, new_n=len(ne), only_old=";".join(sorted(oe - ne)),
                           only_new=";".join(sorted(ne - oe)), same=oe == ne)]), "C3_check_vs_feasibility.csv")

    # ── 4. 점검표 ──
    rows = [check_row(f"real_{c}", M[c], "C-Pe 결산 보정 총수익" if "fill" not in c else "C-P로 빈 날 채움(⬜)") for c in daily]
    rows += [check_row(f"real_avg_{h}{x}", M[f"avg_{h}{x}"], "가용 운용사 단순평균") for h in AVG for x in ("", "_fillCP")]
    rows += [check_row(f"comp_{c}", C[c]) for c in C.columns] + [check_row(f"idx_{c}", X[c]) for c in X.columns]
    csv(pd.DataFrame(rows), "C4_check_series.csv")
    print(pd.DataFrame(rows).to_string())
    print("saved", OUT)
