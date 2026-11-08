"""포트폴리오 주제 08~11(원 연구 저장소 notebooks/portfolio/make_topics_b.py, 커밋 66d40c1을 이 저장소 경로에 맞춰 옮김).
08 = 원 6번 계좌 안 피신(새 계산), 09 = 원 9번 글라이드 변경 반사실(새 계산), 10 = 원 10번 TDF 재매수(보고서 비중 재정리), 11 = 원 12번 원화 30년(기존 결과 그림).
판정 규칙 = 08_shelter_in_account/docs/설계서_포트폴리오_주제B_20261108.md(원 연구 커밋 6ef8992, 계산 전 기록).
계산·문장은 원 스크립트와 같고, 바꾼 것은 읽는 경로·쓰는 곳, 공개 결과 표에서 뺀 열(공시 글라이드 값과 그 값을 되살릴 수 있는 열),
README의 결과 파일 언급과 끝의 '그림·파일·실행' 절뿐이다.
실행: python 08_shelter_in_account/notebooks/portfolio/make_topics_b.py [t6 t9 t10 t12]
  - t12: 저장소 11_krw_30y/results/ 만 읽음(원자료 없이 됨).
  - t6·t9·t10: 원자료와 원 연구 결과 파일이 $PENSION_DATA_ROOT 아래(raw/·processed/·results/) 있어야 돈다(DATA_SOURCES.md).
  → <주제 폴더>/README.md, figures/, results/
"""
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "01_downturn_timing" / "notebooks" / "portfolio"), str(ROOT / "04_loan_vs_withdraw" / "notebooks" / "portfolio"),
                str(ROOT / "01_downturn_timing" / "notebooks" / "pilot9"), str(ROOT / "src")]
import make_figures as mf  # noqa: E402  (폰트·색 설정만 씀)
from make_topics_a import head  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from pension_lab import paths  # noqa: E402

BLUE, GREY, LGREY = mf.BLUE, mf.GREY, mf.LGREY
DATA = Path(os.environ["PENSION_DATA_ROOT"]) / "results" if os.environ.get("PENSION_DATA_ROOT") else None
D8, D9, D10, D11 = "08_shelter_in_account", "09_glidepath_changes", "10_tdf_rebuy_holdings", "11_krw_30y"
SCRIPT = f"{D8}/notebooks/portfolio/make_topics_b.py"
DESIGN = f"`../{D8}/docs/설계서_포트폴리오_주제B_20261108.md`(원 연구 커밋 6ef8992, 계산 전 기록)"
GIT = "원 연구 저장소 make_topics_b.py 커밋 66d40c1eca65875c0e68921ea98fd0a5b3b1c301을 옮김\n"
S2 = r"simpletest_20261027\T2"
PUB = {rf"{S2}\{f}": f"{D11}/results/simpletest_T2/{f}"     # 원 연구 결과 경로 → 이 저장소 경로(요약 결과만). 나머지는 $PENSION_DATA_ROOT 아래
       for f in ("T2_boot_cells.csv", "T2_cushion_phases.csv", "T2_independent_units.csv", "T2_mde.csv", "SAY_OK_T2.txt")}
ME = pd.offsets.MonthEnd(0)
LOG = []
OUT = None


def path(rel):
    """원 연구 결과 상대경로(문자열) 또는 원자료 절대경로(paths.RAW 등) → 읽을 파일. 없으면 PENSION_DATA_ROOT 안내 후 멈춤."""
    p = rel if isinstance(rel, Path) else ROOT / PUB[rel] if rel in PUB else DATA / rel.replace("\\", "/") if DATA else None
    if p is None or not p.exists():
        sys.exit(f"{rel}: 저장소에 없는 입력(원자료 또는 재배포 조건 미확인) — PENSION_DATA_ROOT를 설정해야 합니다(DATA_SOURCES.md).")
    return p


def log(p, rows=None):
    """재현 기록: 저장소 안이면 상대경로, 밖이면 $PENSION_DATA_ROOT/…, sha256, 행 수."""
    show = next((lab + p.relative_to(b).as_posix() for b, lab in ((ROOT, ""), (paths.DATA_ROOT, "$PENSION_DATA_ROOT/")) if p.is_relative_to(b)), p.name)
    LOG.append(f"{show}\tsha256={hashlib.sha256(p.read_bytes()).hexdigest()}" + (f"\trows={rows}" if rows is not None else ""))


def rd(rel, **kw):
    p = path(rel)
    df = pd.read_csv(p, **kw)
    log(p, len(df))
    return df


def save(fig, name, data):
    F = OUT / "figures"
    F.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(F / f"{name}.{ext}")
    plt.close(fig)
    data.to_csv(F / f"{name}_data.csv", index=False, encoding="utf-8-sig")
    (F / f"{name}_source.txt").write_text("\n".join(LOG) + f"\n생성: {SCRIPT}, {GIT}", encoding="utf-8")
    LOG.clear()


def csv(df, name, note, drop=()):
    """결과 표 → <주제>/results/. drop = 공개 표에서 뺄 열(공시 글라이드 값과 그 값을 되살릴 수 있는 열)."""
    R = OUT / "results"
    R.mkdir(parents=True, exist_ok=True)
    df.drop(columns=list(drop)).to_csv(R / f"{name}.csv", index=False, encoding="utf-8-sig")
    (R / f"{name}_source.txt").write_text("\n".join(LOG) + f"\n{note}\n생성: {SCRIPT}, {GIT}", encoding="utf-8")


def readme(o, title, **sec):
    body = "\n\n".join(f"## {k.replace('_', ' ')}\n\n{v.strip()}" for k, v in sec.items())
    title = f"{o.name[:2]}. " + title.split(". ", 1)[1]                                  # 원 주제 번호 → 이 저장소 폴더 번호
    (o / "README.md").write_text(f"# {title}\n\n{body}\n\n{TAIL[o.name].strip()}\n\n_생성: {SCRIPT} (숫자는 결과 CSV에서 읽어 자동으로 채움). "
                                 f"판정 규칙: {DESIGN}_\n", encoding="utf-8")


def out(sub):
    global OUT
    OUT = ROOT / {"06_계좌안피신": D8, "09_글라이드변경": D9, "10_TDF재매수": D10, "12_원화30년": D11}[sub]
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT


def cboot(v, cl, n=5000, seed=20261008):
    """묶음(cl) 복원추출 → 뽑힌 사건 전체 중앙값의 5·95% (C_multi cluster_bootstrap과 같은 방식)."""
    rng, g = np.random.default_rng(seed), pd.Series(v).groupby(np.asarray(cl)).apply(np.array)
    m = [np.median(np.concatenate(g.iloc[rng.integers(0, len(g), len(g))].tolist())) for _ in range(n)]
    return np.percentile(m, [5, 95])


# ── 6번: 하락장에 계좌 안 피신 ───────────────────────────────────────────────
def shelter(eq, safe, ev):
    """dd_detail 사건표 ev(같은 eq로 만든 것) → 사건·규칙별 R = 피신 ÷ 보유. eq·safe: 같은 월 인덱스의 월 수익.
    L 위치 k ↔ 수익 위치 k−1(dd_detail과 같은 수준 계열: 첫 달 앞에 1)."""
    L = pd.Series(np.r_[1.0, np.cumprod(1 + eq.to_numpy())], index=[eq.index[0] - pd.offsets.MonthEnd(1)] + list(eq.index))
    re, rs = np.r_[np.nan, eq.to_numpy()], np.r_[np.nan, safe.to_numpy()]
    rows = []
    for e in ev.itertuples():
        pos = lambda m: L.index.get_loc(pd.Timestamp(m) + ME)
        jc, jp, jf = pos(e.confirm), pos(e.peak), pos(e.first_cross)
        k = np.arange(jc + 1, len(L))
        sa = k[L.to_numpy()[k] >= L.iloc[jp]]                                                      # (a) 그 사건 고점 수준 회복
        sb = k[[L.iloc[j] / L.iloc[jf:j + 1].min() - 1 >= 0.20 for j in k]]                        # (b) 첫 돌파 뒤 최저 대비 +20%
        for rule, s in (("전고점 회복", sa), ("저점 대비 20% 반등", sb)):
            js, cen = (int(s[0]), False) if len(s) else (len(L) - 1, True)
            g = lambda a, b, out: np.prod(1 + np.where(np.arange(a, b + 1) <= js, out[a:b + 1], re[a:b + 1])) / np.prod(1 + re[a:b + 1])
            r5 = g(jc + 1, jc + 60, rs) if jc + 60 < len(L) else np.nan
            R = np.prod(1 + rs[jc + 1:js + 1]) / np.prod(1 + re[jc + 1:js + 1])
            rows.append(dict(peak=e.peak, confirm=e.confirm, 규칙=rule, 신호월=L.index[js].strftime("%Y-%m") if not cen else "", 신호없음=cen,
                             피신개월=js - jc, R=R, R_5년=r5, 놓친상승=(1 / R - 1) if R < 1 else 0.0,
                             주식_수익=np.prod(1 + re[jc + 1:js + 1]) - 1, 안전_수익=np.prod(1 + rs[jc + 1:js + 1]) - 1))
    return pd.DataFrame(rows)


def t6():
    from pension_lab import pilot7 as P7, pilot9 as P9, paths
    from _build_C_real_inputs import dd_detail
    o = out("06_계좌안피신")
    CM = r"pilot9_20261013\C_multi_20261017"
    evm = rd(rf"{CM}\events_monthly.csv")
    # 9개국 계열: _gen_C_multi.py 82–96행 그대로
    mc = rd(paths.PROCESSED / "multicountry_returns_20261017.csv", dtype={"period": str})

    def mpanel(src, var):
        x = mc[(mc.source == src) & (mc.freq == "M") & (mc.variable == var)]
        p = x.pivot(index="period", columns="iso3", values="value"); p.index = pd.to_datetime(p.index) + ME
        return p
    BD, R3 = mpanel("Swinkels2023", "bond_tr_10y_m"), mpanel("OECD_FINMARK", "IR3TIB") / 1200
    ff = rd(paths.EQUITY_GLOBAL / "french" / "F-F_Research_Data_Factors.csv", skiprows=3, index_col=0)
    ix = ff.index.astype(str).str.strip(); kp = ix.str.fullmatch(r"\d{6}")
    us = pd.Series((pd.to_numeric(ff["Mkt-RF"][kp]) + pd.to_numeric(ff["RF"][kp])).values / 100, index=pd.to_datetime(ix[kp], format="%Y%m") + ME)
    FRS = {"AUS": "Austrlia", "CAN": "Canada", "DEU": "Germany", "FRA": "France", "GBR": "UK", "JPN": "Japan", "NOR": "Norway", "SWE": "Sweden"}
    LOC = "Value-Weight Local  Returns      All 4 Data Items Not Reqd"
    EQ = {iso: P7._french_table(paths.EQUITY_GLOBAL / "french_intl" / f"{st}.Dat", LOC) for iso, st in FRS.items()} | {"USA": us}

    def longest(df):
        ok = df.notna().all(1).to_numpy().astype(int); e = np.flatnonzero(np.diff(np.r_[0, ok, 0]))
        a, b = max(zip(e[::2], e[1::2]), key=lambda z: z[1] - z[0]); return df.iloc[a:b]
    D = {iso: longest(pd.DataFrame({"stk": EQ[iso], "bd": BD[iso], "st": R3[iso]})) for iso in EQ}
    res = []
    for iso, d in D.items():
        ev = dd_detail(d.stk, iso, -0.20, P9.REARM)
        mine = evm[evm.series == iso]
        assert list(ev.confirm) == list(mine.confirm) and list(ev.recovery) == list(mine.recovery), iso   # 사건표 재현
        for safe, sname in ((d.st, "MMF"), (d.bd, "채권")):
            r = shelter(d.stk, safe, ev).assign(표본="9개국", 나라=iso, 안전자산=sname)
            a = r[r.규칙 == "전고점 회복"]; b = r[r.규칙 != "전고점 회복"].set_index("confirm")
            assert all((x.신호월 or "미회복(자료 끝)") == y for x, y in zip(a.itertuples(), mine.recovery)), iso     # (a) = 회복월 열
            rm = mine.set_index("confirm").rearm_month.str[:7]
            ok = [b.loc[c, "신호월"] == rm[c] for c in rm.index if rm[c] > c and b.loc[c, "신호월"]]   # (b) = 재무장월(확인월 뒤인 사건)
            assert all(ok) and len(ok) >= 0.8 * len(rm), (iso, sum(ok), len(rm))
            res.append(r)
    kr = P7.samples()["KR 1991~"]
    # 감사 L9: rd()를 거치지 않는 입력도 기록(French .Dat 파일, pilot7 한국 표본은 쓰는 열의 내용 해시)
    for st in FRS.values():
        log(paths.EQUITY_GLOBAL / "french_intl" / f"{st}.Dat")
    LOG.append(f"pension_lab.pilot7.samples()['KR 1991~'][eq·cash·bd] 내용\tsha256={hashlib.sha256(kr[['eq', 'cash', 'bd']].to_csv().encode()).hexdigest()}\trows={len(kr)}")
    evk = dd_detail(kr["eq"], "KR", -0.20, P9.REARM)
    for safe, sname in ((kr.cash, "MMF"), (kr.bd, "채권")):
        res.append(shelter(kr["eq"], safe, evk).assign(표본="한국 1991~", 나라="KOR", 안전자산=sname))
    R = pd.concat(res, ignore_index=True)
    R["안전자산_원자료"] = np.where(R.나라 == "KOR", np.where(R.안전자산 == "MMF", "CD91 전월말", "국고채 TR(pilot7 bd)"),
                              np.where(R.안전자산 == "MMF", "OECD IR3TIB", "Swinkels 10년 국채 TR"))
    R["확인연도"] = R.confirm.str[:4]
    csv(R, "T6_shelter_events", f"사건별·규칙별·안전자산별 R = 피신 금액 ÷ 보유 금액(복귀 신호 달 기준; 신호 없음 = 자료 끝). 판정 규칙: {DESIGN}.\n"
        "9개국 사건 = C_multi events_monthly.csv 63건(재현 assert, (a) 신호월 = recovery 열, (b) = rearm_month 열과 일치 assert). 한국 = pilot7 KR 1991~ eq에 같은 규칙.")
    summ = []
    vs = lambda lo, hi, L: "피신 비용 > 해지 세금" if hi < L else "피신 비용 < 해지 세금" if lo > L else "가려낼 수 없음"
    for (rule, safe), g in R[R.표본 == "9개국"].groupby(["규칙", "안전자산"]):
        lo, hi = cboot(g.R.to_numpy(), g.확인연도)
        g5 = g.dropna(subset=["R_5년"]); lo5, hi5 = cboot(g5.R_5년.to_numpy(), g5.확인연도)
        gs = g[~g.신호없음]; los, his = cboot(gs.R.to_numpy(), gs.확인연도)
        summ.append(dict(규칙=rule, 안전자산=safe, 사건=len(g), 확인연도=g.확인연도.nunique(), 신호없음=int(g.신호없음.sum()),
                         중앙R=g.R.median(), P5=lo, P95=hi,
                         보유대비="피신이 적었다" if hi < 1 else "피신이 많았다" if lo > 1 else "가려낼 수 없음",
                         해지대비=vs(lo, hi, 0.835),
                         # 감사 H1 뒤 추가(결과 뒤): 피신·보유 쪽에도 연금 수령 세금 τ를 매긴 손익분기 0.835 ÷ (1 − τ)
                         해지대비_수령세3_3=vs(lo, hi, 0.835 / (1 - 0.033)), 해지대비_수령세5_5=vs(lo, hi, 0.835 / (1 - 0.055)),
                         P5_신호없음제외=los, P95_신호없음제외=his,
                         R1미만=int((g.R < 1).sum()), R0835미만=int((g.R < 0.835).sum()), 피신개월_중앙=g.피신개월.median(),
                         놓친상승_중앙_R1미만=g[g.R < 1].놓친상승.median(),
                         사건_5년=len(g5), 중앙R_5년=g5.R_5년.median(), P5_5년=lo5, P95_5년=hi5))
    S = pd.DataFrame(summ)
    csv(S, "T6_shelter_summary", "9개국 사건 중앙값 R, 확인 연도 묶음 부트스트랩 5,000회(seed 20261008) 5~95%. 보유대비·해지대비 = 설계서 규칙 그대로.\n"
        "감사(H1) 뒤 추가, 결과 뒤 민감도: 해지대비_수령세3_3·5_5 = 같은 구간을 0.835 ÷ (1 − 3.3%·5.5%) = 0.8635·0.8836 선과 비교(피신·보유 쪽 연금 수령 세금 반영). "
        "P5·P95_신호없음제외 = 자료 끝까지 신호 없는 사건을 뺀 구간(참고).")

    # 자금흐름: T3a판 4묶음 + TDF, 하락장 아닌 같은 길이 창과 비교
    F3 = r"pilot10_20261017\T3_flow"
    fl = pd.concat([rd(rf"{F3}\T3_monthly_group_T3a.csv"), rd(rf"{F3}\T3_monthly_group.csv").query("묶음 == 'TDF|TDF연금'")])
    dde = rd(r"pilot9_20261013\C_real_20261017\inputs\C3_dd_events.csv")
    kre = rd(r"pilot9_20261013\C_kr_real_20261017\events.csv")
    months = pd.period_range("1980-02", "2026-09", freq="M")
    bear = pd.Series(False, index=months)
    for e in dde[dde.series == "KOSPI_px"].itertuples():
        bear[pd.Period(e.peak, "M"):(pd.Period(e.recovery, "M") if e.recovery[:2] in ("19", "20") else months[-1])] = True
    t0s = [c for c in kre[kre.series == "KOSPI가격(주)"].confirm if c >= "2014-07"]
    frows = []
    for grp in ("T3a판|안정형4유형합", "T3a판|MMF", "T3a판|국내채권형", "TDF|TDF연금"):
        f = fl[fl.묶음 == grp].assign(m=lambda x: pd.PeriodIndex(x.month, freq="M")).set_index("m").sort_index()
        assert f.index.is_unique and (f.index == pd.period_range(f.index[0], f.index[-1], freq="M")).all()
        for h in (3, 6, 12):
            F = lambda s: f.flow.loc[s:s + h - 1].sum() / f.na.loc[s - 1]
            ok = [s for s in f.index[1:len(f) - h + 1] if not bear[s:s + h - 1].any()]
            base = np.array([F(s) for s in ok])
            for t0 in t0s:
                v = F(pd.Period(t0, "M"))
                frows.append(dict(묶음=grp.split("|")[1], h개월=h, 확인월=t0, 사건값=v, 비교창=len(base),
                                  비교창_첫=str(ok[0]) if ok else "", 비교창_끝=str(ok[-1]) if ok else "",
                                  비교_중앙=np.median(base), 비교_P10=np.percentile(base, 10), 비교_P90=np.percentile(base, 90),
                                  사건이_큰_비율=(v > base).mean()))
    FL = pd.DataFrame(frows)
    csv(FL, "T6_flow_vs_nonbear", "F = 확인월부터 h개월 순설정 합 ÷ 확인월 전달 말 순자산(T3a판·TDF). 비교창 = 같은 길이, 모든 달이 하락장 상태(코스피 가격 [고점, 회복])가 아닌 창(겹침 허용).\n"
        "신규 납입·해지·이체·교체를 구분하지 못한다. 시기 추세가 커서(특히 TDF) 판정하지 않음.")

    # 그림
    fig = plt.figure(figsize=(9.5, 6.8))
    ax = fig.add_axes([0.08, 0.24, 0.56, 0.42]); bx = fig.add_axes([0.75, 0.24, 0.23, 0.42])
    combos = [("전고점 회복", "MMF"), ("전고점 회복", "채권"), ("저점 대비 20% 반등", "MMF"), ("저점 대비 20% 반등", "채권")]
    ax.axhline(1, color="black", lw=0.6); ax.axhline(0.835, color="#B03A2E", lw=0.8, ls="--")
    ax.axhspan(0.835 / (1 - 0.033), 0.835 / (1 - 0.055), color="#B03A2E", alpha=0.12, lw=0)
    kz = R[(R.나라 == "KOR") & ~(R.신호없음 & (R.피신개월 == 0))]                      # 감사 M2: 관찰 0개월(자료 끝 2026-08 확인) 사건 제외
    nk0 = R[(R.나라 == "KOR") & R.신호없음 & (R.피신개월 == 0)].confirm.nunique()
    rng = np.random.default_rng(1)
    for i, (rule, safe) in enumerate(combos):
        g = R[(R.표본 == "9개국") & (R.규칙 == rule) & (R.안전자산 == safe)]
        ax.scatter(i + rng.uniform(-0.18, 0.18, len(g)), g.R, s=9, color=LGREY, zorder=2)
        s = S[(S.규칙 == rule) & (S.안전자산 == safe)].iloc[0]
        ax.vlines(i + 0.3, s.P5, s.P95, color=BLUE, lw=2.5); ax.scatter(i + 0.3, s.중앙R, color=BLUE, s=30, zorder=4)
        ax.text(i + 0.36, s.중앙R, f"{s.중앙R:.2f}", fontsize=8, color=BLUE, va="center")
        k = kz[(kz.규칙 == rule) & (kz.안전자산 == safe)]
        ax.scatter(np.full(len(k), i - 0.3), k.R, marker="D", s=16, color="#333", zorder=3)
    sv = S.set_index(["규칙", "안전자산"])
    sh = {"피신이 적었다": "적음", "피신이 많았다": "많음", "가려낼 수 없음": "가려낼 수 없음", "피신 비용 > 해지 세금": "피신 쪽 손해 큼", "피신 비용 < 해지 세금": "피신 쪽 손해 작음"}
    ax.set_xticks(range(4), [f"{r.replace('저점 대비 ', '저점+')}·{s}\n보유 대비: {sh[sv.loc[(r, s), '보유대비']]}\n0.835: {sh[sv.loc[(r, s), '해지대비']]}\n0.863: {sh[sv.loc[(r, s), '해지대비_수령세3_3']]}\n0.884: {sh[sv.loc[(r, s), '해지대비_수령세5_5']]}"
                         for r, s in combos], fontsize=6.8)
    ax.set_yscale("log"); ax.set_ylim(0.3, 2.2); ax.set_yticks([0.4, 0.6, 0.835, 1, 1.5, 2], ["0.4", "0.6", "0.835", "1", "1.5", "2"]); ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_ylabel("피신 금액 ÷ 계속 보유 금액 (로그 눈금)")
    ax.text(3.55, 0.95, "띠 = 수령세\n넣은 선\n\n해지 세금\n16.5% 선", fontsize=6.5, color="#B03A2E", va="top")
    ax.set_title("회색 = 9개국 사건, 파랑 = 중앙값·연도 묶음 90%, ◆ = 한국", loc="left", fontsize=8.5, color="#222")
    fh = FL[FL.h개월 == 12]
    for j, grp in enumerate(["안정형4유형합", "MMF", "국내채권형", "TDF연금"]):
        z = fh[fh.묶음 == grp]
        bx.hlines(j, z.비교_P10.iloc[0], z.비교_P90.iloc[0], color=LGREY, lw=6); bx.scatter(z.비교_중앙.iloc[0], j, marker="|", s=80, color=GREY)
        for _, r in z.iterrows():
            bx.scatter(r.사건값, j, color=BLUE if r.확인월 == "2018-10" else "#B03A2E", s=18, zorder=3)
    bx.set_yticks(range(4), ["안정형 4유형", "MMF", "국내채권형", "TDF"], fontsize=8); bx.invert_yaxis(); bx.set_xscale("symlog", linthresh=0.5); bx.set_xticks([0, 0.5, 1, 5, 15], ["0", "0.5", "1", "5", "15"], fontsize=7.5); bx.xaxis.set_minor_formatter(plt.NullFormatter())
    bx.set_xlabel("12개월 순설정 ÷ 순자산", fontsize=8)
    bx.set_title("자금흐름: 확인월부터 12개월\n파랑 = 2018-10, 빨강 = 2022-06 확인\n회색 = 하락장 아닌 같은 길이 창 10~90%", loc="left", fontsize=8, color="#222")
    m = S[(S.규칙 == "전고점 회복") & (S.안전자산 == "MMF")].iloc[0]
    sa, sb = S[S.규칙 == "전고점 회복"], S[S.규칙 != "전고점 회복"]
    vt = lambda z: "·".join(sorted(set(z.보유대비))).replace("가려낼 수 없음", "보유와 가려낼 수 없음").replace("피신이 적었다", "보유보다 적음")
    head(fig, f"계좌 안 피신, 전고점 회복 뒤 복귀 = 보유의 {sa.중앙R.min():.2f}~{sa.중앙R.max():.2f}배({vt(sa)})\n"
              f"20% 반등 뒤 복귀 = {sb.중앙R.min():.2f}~{sb.중앙R.max():.2f}배({vt(sb)}), 9개국 중앙값",
         f"9개국(현지통화) 하락장 {m.사건}번(확인 연도 {m.확인연도}개)·한국 1991~ {len(evk) - nk0}번. 확인월 말 주식 1 → 다음 달 안전자산 → 복귀 신호 다음 달 주식\n"
         f"복귀 신호 2가지(계산 전 설계서에 고정): 전고점 회복 / 첫 돌파 뒤 최저 대비 20% 반등. 복귀 뒤엔 두 경로가 같이 움직여 비율이 고정됨\n"
         "판정(설계서): 묶음 90% 구간이 1 밖 → 보유보다 적음/많음, 0.835 밖 → 피신 쪽 손해가 해지 세금보다 큼/작음, 그 밖 → 가려낼 수 없음",
         "보수·전환 비용·일반계좌 세금은 넣지 않음. 0.835 선 = 확인월에 해지(16.5%를 잔액 전체에)하고 같은 주식에 다시 넣은 경우. 피신·보유 쪽 연금 수령 세금(3.3~5.5%)을\n"
         f"넣지 않아 해지에 불리한 쪽이며, 넣은 선 0.863~0.884(띠, 감사 뒤 추가한 민감도)로는 판정이 달라지는 칸이 있음(눈금 글자). 한국 자료 끝 관찰 0개월 {nk0}건은 뺌.\n"
         "9개국 = 각국 주식 총수익(French 현지통화, 미국 F-F), 안전자산 = OECD 3개월 금리·Swinkels 10년 국채. 한국 = KOSPI200+배당, CD91·국고채 TR. 자료 끝까지 신호 없는 사건은 자료 끝 값.\n"
         "자금흐름 = 금투협 연금 펀드 클래스 순설정(신규 납입·해지·이체 구분 불가), 하락장 상태 = 코스피 가격 [고점, 회복] 달. 시기 추세가 커서 기술만.\n"
         "출처: pilot9 C_multi events_monthly·multicountry_returns, pilot7 KR 1991~, pilot10 T3_flow. 결과: T6_shelter_events·T6_shelter_summary·T6_flow_vs_nonbear.csv.")
    save(fig, "fig_T6_계좌안피신", pd.concat([S.assign(구분="9개국 요약"), R[R.나라 == "KOR"].assign(구분="한국 사건"), fh.assign(구분="자금흐름 12개월")]))

    k = R[R.나라 == "KOR"]
    line = lambda s: f"{s.규칙}·{s.안전자산}: 중앙 {s.중앙R:.2f}배(90% {s.P5:.3f}~{s.P95:.3f}; 신호 없음 {s.신호없음}건을 빼면 {s.P5_신호없음제외:.3f}~{s.P95_신호없음제외:.3f}) → 보유 대비 {s.보유대비}, 해지 대비(0.835 선, 설계서) {s.해지대비}, 수령세 넣은 선(0.863·0.884, 감사 뒤 민감도) {s.해지대비_수령세3_3}·{s.해지대비_수령세5_5}. 사건 {s.사건}개 중 보유보다 적었던 사건 {s.R1미만}개, 0.835 아래 {s.R0835미만}개, 피신 기간 중앙 {s.피신개월_중앙:.0f}개월, 보유보다 적었던 사건의 놓친 상승분(1/R − 1) 중앙 {s.놓친상승_중앙_R1미만 * 100:.0f}%"
    kl = lambda rule, safe: "; ".join(f"{r.confirm} 확인 {r.R:.2f}배({r.피신개월}개월{', 신호 없음' if r.신호없음 else ''})" for r in kz[(kz.규칙 == rule) & (kz.안전자산 == safe)].itertuples())
    fz = lambda grp, t0: FL[(FL.묶음 == grp) & (FL.h개월 == 12) & (FL.확인월 == t0)].iloc[0]
    readme(o, "6. 하락장에 계좌 안에서 피신하기 — 해지 대신 MMF로 피했다 돌아오면 괜찮을까",
        문제의식="""
하락장에 "세금 16.5%를 내고 해지하느니, 연금계좌 안에서 MMF·채권형으로 옮겼다가 회복을 보고 돌아오면 된다"는 말이 있습니다. 세금은 없지만, 회복을 '확인'하고 돌아오는 사이에 주가가 이미 많이 올라 그 상승분을 놓칩니다. 놓친 상승분이 해지 세금보다 큰지 따져 봤습니다.
""",
        한_일=f"""
- 9개국(호주·캐나다·독일·프랑스·영국·일본·노르웨이·스웨덴·미국, 현지통화) 하락장 {m.사건}번과 한국(1991~, KOSPI200+배당) 하락장 {len(evk) - nk0}번(자료 끝 2026-08 확인 {nk0}건은 관찰 0개월이라 값 없음)에서, 하락장 확인월 말 주식 1을 ① 계속 보유 ② 다음 달 안전자산(MMF 대용 단기금리, 또는 10년 국채·국고채)으로 옮겼다가 복귀 신호 다음 달 주식으로 돌아오는 경우를 비교했습니다.
- 복귀 신호는 계산 전에 설계서에 두 가지로 고정했습니다: (a) 그 하락장 고점 수준 회복, (b) 처음 −20%를 넘은 뒤의 최저점 대비 20% 반등. 둘 다 그 달 말까지의 자료만 씁니다. 사건 날짜는 10월 17일 C_multi 사건표와 같고(재현 확인), (a)·(b) 신호 달이 사건표의 회복월·재무장월 열과 같은지 확인했습니다.
- 지표 R = 피신 금액 ÷ 보유 금액. 돌아온 뒤에는 두 경로가 같이 움직이므로 R은 복귀 신호 달에 정해집니다. 9개국은 확인 연도로 묶어 다시 뽑는 부트스트랩(5,000회)으로 중앙값의 90% 구간을 냈습니다.
- 해지 비교선 0.835 = 확인월에 잔액 전체에서 16.5%를 떼고 같은 주식에 바로 다시 넣은 경우.
- **결과 뒤 확인한 설계서 전제 오류(감사 H1)**: 설계서는 이 선을 "해지에 유리한 쪽"이라고 적었지만 틀렸습니다. 피신·보유 쪽에 연금 수령 세금(3.3~5.5%)을 매기지 않았고 16.5%를 세액공제 받지 않은 원금까지 잔액 전체에 매겼으므로 해지에 **불리한** 쪽입니다(일반계좌 세금을 뺀 것만 해지에 유리). 그래서 설계서 판정(0.835 선)은 그대로 두고, 수령세를 넣은 손익분기 0.835 ÷ (1 − τ) = 0.863(τ 3.3%)·0.884(5.5%) 판정을 결과 뒤 민감도로 덧붙였습니다.
- 자금흐름: 금투협 연금 펀드 순설정(T3a판, TDF)으로 하락장 확인월(2018-10, 2022-06)부터 3·6·12개월 순설정 ÷ 순자산을, 하락장이 아닌 달로만 된 같은 길이 창들과 비교했습니다.
- 결과: `T6_shelter_events.csv`(사건별), `T6_shelter_summary.csv`(판정), `T6_flow_vs_nonbear.csv`, 그림 `fig_T6_계좌안피신`.
""",
        결과="\n".join(f"- {line(s)}." for s in S.itertuples()) + f"""
- 한국 하락장(사건별, 묶음 구간 없음): 전고점 회복·MMF — {kl('전고점 회복', 'MMF')}. 20% 반등·MMF — {kl('저점 대비 20% 반등', 'MMF')}.
- 확인 뒤 5년 시점으로 보면(5년 자료 있는 사건): """ + "; ".join(f"{s.규칙}·{s.안전자산} 중앙 {s.중앙R_5년:.2f}배(90% {s.P5_5년:.2f}~{s.P95_5년:.2f}, {s.사건_5년}개)" for s in S.itertuples()) + f""".
- 자금흐름(12개월): 안정형 4유형 순설정 ÷ 순자산은 2018-10 확인 뒤 {fz('안정형4유형합', '2018-10').사건값:.3f}, 2022-06 확인 뒤 {fz('안정형4유형합', '2022-06').사건값:.3f}였고, 하락장이 아닌 같은 길이 창({fz('안정형4유형합', '2018-10').비교창}개)은 중앙 {fz('안정형4유형합', '2018-10').비교_중앙:.3f}(10~90% {fz('안정형4유형합', '2018-10').비교_P10:.3f}~{fz('안정형4유형합', '2018-10').비교_P90:.3f}). MMF는 {fz('MMF', '2018-10').사건값:.3f}·{fz('MMF', '2022-06').사건값:.3f} 대 중앙 {fz('MMF', '2018-10').비교_중앙:.3f}, TDF는 {fz('TDF연금', '2018-10').사건값:.3f}·{fz('TDF연금', '2022-06').사건값:.3f} 대 중앙 {fz('TDF연금', '2018-10').비교_중앙:.3f}(비교창 {fz('TDF연금', '2018-10').비교창}개, 대부분 TDF 초기 2014~2017년).
""",
        말하면_안_되는_것="""
- "계좌 안 피신은 안전하다" / "피신하면 손해다" — 판정 칸이 '가려낼 수 없음'인 조합은 어느 쪽도 말할 수 없습니다. 사건마다 크게 갈립니다(회색 점).
- 사건 비율을 "확률"로 말하기 — 63개 사건은 같은 해 여러 나라가 겹친 사건이라 독립이 아닙니다.
- "하락장 뒤 연금 가입자가 MMF로 옮겼다" — 순설정은 신규 납입·해지·이체를 구분하지 못하고, 안정형→TDF 이동은 직접 보이지 않습니다. 시기 추세가 커서 '평소보다 많다/적다'로 쓰지 않습니다.
""",
        한계=f"""
- 0.835 선은 연금 수령 세금(3.3~5.5%)을 피신 쪽에 매기지 않았고 16.5%를 잔액 전체에 매겨 해지에 **불리한** 쪽입니다. 일반계좌 세금을 뺀 것만 해지에 유리합니다. 수령세를 넣은 선(0.863~0.884)으로 보면 판정이 바뀌는 칸이 있어(결과 줄의 '수령세 넣은 선'), 해지 대비 판정은 세금 가정에 민감합니다.
- 보수(MMF·채권형과 주식형 보수 차이)와 전환 비용(단기 환매수수료·ETF 호가)을 넣지 않았습니다. 방향은 정해지지 않습니다.
- 자금흐름 h = 3·6·12개월과 보조 지표 '확인 뒤 5년'은 설계 선택이고 근거 자료가 없습니다(판정에 쓰지 않음).
- 9개국은 세 계열(주식·단기금리·10년 국채)이 모두 있는 선진 생존 시장입니다.
- 9개국 안전자산은 단기금리·10년 국채 지수라 실제 연금 MMF·채권형 펀드와 다릅니다. 한국 채권은 국고채 TR입니다.
- 자료 끝까지 복귀 신호가 없는 사건은 자료 끝 값으로 넣었습니다(9개국 '신호없음' 열). 미국 2020-03 사건은 표본 끝(OECD 금리 공백)이라 피신 기간이 0입니다(R = 1, 설계서 판정 표본 63건에는 그대로 둠).
- 한국은 1991년 이후 {len(evk) - nk0}번뿐이라(자료 끝 2026-08 확인 {nk0}건은 관찰 0개월이라 R = 1로 고정되어 결과·그림에서 뺌, CSV에는 있음) 사건별 값만 보였습니다. 한국 사건은 KOSPI200 총수익 기준이라 10월 19일 C(코스피 가격, 3번)와 날짜가 다를 수 있습니다.
- 자금흐름 비교창은 겹치고, 하락장이 아닌 달이 2014~2017년에 몰려 있어 TDF처럼 빨리 커진 묶음은 비교가 어렵습니다.
""")
    return dict(S=S, kr=k[["confirm", "규칙", "안전자산", "R", "피신개월", "신호없음"]], flow=FL[FL.h개월 == 12])


# ── 9번: 글라이드패스 변경 → 처음 계획대로였다면 ────────────────────────────
def t9():
    BAD = r"≠ 목록|전략배분|UH"     # 원 연구 pension_lab.h1d_r5.BAD(판독 불가 note), 이 저장소에 그 모듈이 없어 값만 옮김
    o = out("09_글라이드변경")
    g = rd(paths.RAW / "fund_tdf" / "glidepath_disclosed_hist_20261012fix.csv", dtype={"rcept_no": str, "rcept_dt": str, "code": str})
    C = rd(r"pilot9_20261013\C_real_20261017\inputs\C2_components_monthly.csv", parse_dates=["month_end"]).set_index("month_end")[["stk", "bd"]].dropna()
    S3 = r"simpletest_20261027\T3\full_r1_20261027_0433"
    ev = rd(rf"{S3}\T3_07_decision_events.csv"); ev = ev[(ev["τ이름"].astype(str) == "2.5") & (ev.D3 == "A") & (ev.D4 == "A")]
    assert len(ev) == 9 and ev.groupby("운용사").size().to_dict() == {"KB": 1, "삼성": 2, "신한": 4, "한국투자": 2}
    fl = rd(rf"{S3}\T3_13b_cf_floor_used.csv"); floor = fl[fl["종류"] == "누적"].groupby("운용사")["d바닥선_q95"].first()
    lt = rd(r"pilot10_20261017\I2x_hist\results_lt2020\lt2020_events.csv")
    note = g.note.fillna("")
    num = g[g.yrs_to_target.notna() & g.risky_target_pct.notna() & ~note.str.contains(BAD)]
    V = {}
    for (c, r), d in num.groupby(["code", "rcept_no"]):
        xy = d.groupby("yrs_to_target").risky_target_pct.mean()
        if len(xy) >= 2:
            V.setdefault(c, []).append(dict(rno=r, dt=pd.Timestamp(d.rcept_dt.iloc[0]), x=xy.index.to_numpy(float), y=xy.to_numpy(float) / 100,
                                           meth=str(d.method.iloc[0]).split("(")[0]))
    info = g.groupby("code").agg(manager=("manager", "first"), vintage=("vintage", "first"), 판수=("rcept_no", "nunique")).astype({"vintage": int})
    rows, paths_ = [], []
    for c, inf in info.iterrows():
        vs = sorted(V.get(c, []), key=lambda v: v["rno"]); base = dict(code=c, 운용사=inf.manager, 빈티지=inf.vintage, 판수=inf.판수, 곡선판=len(vs))
        if len(vs) < 2:
            rows.append(base | dict(판정="비교 불가(곡선으로 읽을 수 있는 판 2개 미만)")); continue
        v0 = vs[0]; end = min(pd.Timestamp("2026-08-31"), pd.Timestamp(f"{inf.vintage}-12-31"))
        m = C.loc[(C.index > v0["dt"] + ME) & (C.index <= end)]
        if not len(m):
            rows.append(base | dict(첫판=v0["dt"].date(), 판정="비교 불가(첫 판 뒤 계산 기간 없음)")); continue
        x = (m.index.year + (m.index.month - 1) / 12 - inf.vintage).to_numpy(float)
        known = [max((v for v in vs if v["dt"] <= t - pd.offsets.MonthEnd(1)), key=lambda v: v["rno"]) for t in m.index]   # 전달 말까지 접수된 최신 판
        wf = np.interp(x, v0["x"], v0["y"]); wa = np.array([np.interp(xi, v["x"], v["y"]) for xi, v in zip(x, known)])
        ext = np.mean([(xi < v["x"].min()) or (xi > v["x"].max()) for xi, v in zip(x, known)] + [(xi < v0["x"].min()) or (xi > v0["x"].max()) for xi in x])
        Rf, Ra = wf * m.stk + (1 - wf) * m.bd, wa * m.stk + (1 - wa) * m.bd
        acc = lambda Rr: np.cumprod((1 + Rr.to_numpy())[::-1]).sum()   # 매달 초 1 납입: Σ_t Π_{s≥t}(1+R_s)
        Wf, Wa = acc(Rf), acc(Ra)
        used = {v["rno"] for v in known}; nchg = len(used - {v0["rno"]})
        d = np.log(Wa / Wf); fz = floor.get(inf.manager, np.nan)
        # 감사 H2 뒤 추가(결과 뒤): 판독 방법이 처음 바뀌기 전 달까지만 누적한 d
        mc = [v["meth"] != v0["meth"] for v in known]; i1 = mc.index(True) if any(mc) else len(m)
        ds = np.log(acc(Ra.iloc[:i1]) / acc(Rf.iloc[:i1])) if i1 else np.nan
        rows.append(base | dict(첫판=v0["dt"].date(), 끝월=m.index[-1].strftime("%Y-%m"), 개월=len(m), 쓰인판=len(used), 바뀐판=nchg,
                                방법변경건넘=any(mc), 방법변경첫달=m.index[i1].strftime("%Y-%m") if any(mc) else "", 같은방법개월=i1, d_같은방법구간=ds, 범위밖비율=ext,
                                첫계획_평균위험비중=wf.mean(), 실제계획_평균위험비중=wa.mean(), 위험비중차_최대=np.abs(wa - wf).max(),
                                d_적립=d, d_일시금=np.log(np.prod(1 + Ra) / np.prod(1 + Rf)), 월10만원_금액차=(Wa - Wf) * 1e5, 적립원금=len(m) * 1e5, 바닥선=fz,
                                판정="비교 불가(쓰인 판이 첫 판뿐)" if nchg == 0 else "판독 오차와 구분 안 됨" if abs(d) <= fz else ("실제 계획이 더 많음" if d > 0 else "처음 계획이 더 많음")))
        paths_.append(pd.DataFrame(dict(code=c, 운용사=inf.manager, 빈티지=inf.vintage, month=m.index.strftime("%Y-%m"), x=x, w_첫=wf, w_실제=wa)))
    T = pd.DataFrame(rows)
    out_ = T.판정.isin(["실제 계획이 더 많음", "처음 계획이 더 많음"])
    T["원인구분"] = np.select([out_ & ~T.방법변경건넘.eq(True), out_ & (T.d_같은방법구간.abs() > T.바닥선), out_],
                            ["판독 방법 변경 없음", "같은 방법 구간에서도 바닥선 밖", "방법 변경 뒤에만 차이(나눌 수 없음)"], "")
    csv(T, "T9_cf_by_fund", f"펀드별 '처음 공시 계획' 대 '실제(바뀐) 계획', 같은 실제 시장 경로(C2_components stk·bd, 원화 UH), 보수 0(두 계획 같음). 판정 = {DESIGN}.\n"
        "판독 가능 행 = h1d_r5 규칙(BAD), 곡선 = 숫자 x 2개 이상인 판, 범위 밖 끝값 고정. 실제 계획 = 그 달 수익에 대해 전달 말까지 접수된 최신 판.\n"
        "감사(H2) 뒤 추가, 결과 뒤: d_같은방법구간 = 실제 계획에 쓰인 판의 판독 방법이 첫 판과 처음 달라지기 전 달까지만 누적한 d. 원인구분 = 바닥선 밖 펀드를 방법 변경 없음 / 같은 방법 구간에서도 밖 / 방법 변경 뒤에만 차이로 나눔.\n"
        "이 저장소 판은 첫계획_평균위험비중·실제계획_평균위험비중 열을 뺌(공시 글라이드 값).",
        drop=["첫계획_평균위험비중", "실제계획_평균위험비중"])
    # 원 연구는 여기서 T9_cf_weights_monthly.csv(펀드·월별 처음·실제 계획 위험자산 비중)를 쓴다 — 공시 글라이드 값이라 이 저장소에는 쓰지 않음
    ok = T[T.판정.isin(["판독 오차와 구분 안 됨", "실제 계획이 더 많음", "처음 계획이 더 많음"])]
    M = ok.groupby("운용사").agg(펀드=("code", "size"), d_중앙=("d_적립", "median"), d_최소=("d_적립", "min"), d_최대=("d_적립", "max"),
                               금액차_최소=("월10만원_금액차", "min"), 금액차_최대=("월10만원_금액차", "max"),
                               바닥선밖=("판정", lambda s: int((s != "판독 오차와 구분 안 됨").sum())), 방법변경건넘=("방법변경건넘", "sum"),
                               개월_최소=("개월", "min"), 개월_최대=("개월", "max"), 첫판_최소=("첫판", "min"), 첫판_최대=("첫판", "max")).reset_index()
    nc = T[~T.code.isin(ok.code)].groupby("운용사").size()
    M["비교불가"] = M.운용사.map(nc).fillna(0).astype(int)
    M = pd.concat([M, pd.DataFrame([dict(운용사=k, 펀드=0, 비교불가=int(v)) for k, v in nc.items() if k not in set(M.운용사)])], ignore_index=True)

    MG = ["KB", "삼성", "신한", "한국투자", "미래에셋"]
    fig = plt.figure(figsize=(9.5, 6.2))
    ax = fig.add_axes([0.10, 0.25, 0.52, 0.38]); bx = fig.add_axes([0.72, 0.25, 0.26, 0.38])
    for e in lt.itertuples():
        ax.axvspan(pd.Timestamp(e.peak), pd.Timestamp(e.trough) if isinstance(e.trough, str) else pd.Timestamp("2026-10-31"), color="#EEE", zorder=0)
    vd = g.drop_duplicates(["code", "rcept_no"]).assign(dt=lambda x: pd.to_datetime(x.rcept_dt), ok=lambda x: x.rcept_no.isin({v["rno"] for vv in V.values() for v in vv}))
    for i, mg in enumerate(MG):
        z = vd[vd.manager == mg].drop_duplicates("dt")
        ax.scatter(z.dt, np.full(len(z), i), s=6, color=np.where(z.ok, GREY, "white"), edgecolors=GREY, linewidths=0.4, zorder=2)
        e = ev[ev.운용사 == mg]
        ax.scatter(pd.to_datetime(e.묶음날짜), np.full(len(e), i), marker="D", s=40, color="#B03A2E", zorder=3)
    ax.set_yticks(range(5), MG); ax.invert_yaxis(); ax.set_ylim(4.6, -0.6)
    ax.set_title("판본 공시일(회색 = 곡선 판독 가능, 흰색 = 불가), ◆ = 2.5%p 넘는 변경\n음영 = 사후 구분한 하락 국면(LT 20/20)", loc="left", fontsize=8.5, color="#222")
    bx.axvspan(-floor.max() * 100, floor.max() * 100, color="#EEE")
    bx.axvline(0, color="black", lw=0.6)
    for i, mg in enumerate(MG):
        z = ok[ok.운용사 == mg]
        bx.scatter(z.d_적립 * 100, np.full(len(z), i) + np.linspace(-0.2, 0.2, len(z)) if len(z) else [], s=14,
                   color=np.where(z.판정 == "판독 오차와 구분 안 됨", GREY, np.where(z.원인구분 == "방법 변경 뒤에만 차이(나눌 수 없음)", "#E08E0B", BLUE)), zorder=3)
    bx.set_yticks(range(5), [f"{mg}\n비교 {int((ok.운용사 == mg).sum())}·불가 {int(nc.get(mg, 0))}" for mg in MG], fontsize=8); bx.invert_yaxis(); bx.set_ylim(4.7, -0.5)
    bx.set_xlabel("실제 ÷ 처음 계획 금액, 로그 % (월 적립)", fontsize=8)
    bx.set_title("펀드별 금액 차이, 회색 띠 = 판독 잡음 바닥선\n파랑 = 같은 판독 방법에서도 밖\n주황 = 판독 방법 변경 뒤에만 밖", loc="left", fontsize=7.5, color="#222")
    nbig = int((ok.판정 != '판독 오차와 구분 안 됨').sum()); nu = ok.원인구분.value_counts()
    n_same, n_ins, n_none = (int(nu.get(x, 0)) for x in ("같은 방법 구간에서도 바닥선 밖", "방법 변경 뒤에만 차이(나눌 수 없음)", "판독 방법 변경 없음"))
    fl_ = lambda x: ", ".join(f"{r.운용사} {r.빈티지}" for r in ok[ok.원인구분 == x].sort_values(["운용사", "빈티지"]).itertuples())
    long_ = ok[ok.개월 > 12]; short_ = ok[ok.개월 <= 12]
    assert set(short_.운용사) <= {"신한", "미래에셋"} and {str(x)[:7] for x in short_.첫판} == {"2026-04"} and short_.개월.max() <= 4
    inph = lambda d: [e.peak for e in lt.itertuples() if pd.Timestamp(e.peak) <= pd.Timestamp(d) <= (pd.Timestamp(e.trough) if isinstance(e.trough, str) else pd.Timestamp("2026-12-31"))]
    within = int(ev.묶음날짜.apply(lambda d: bool(inph(d))).sum()); nph = len({p for d in ev.묶음날짜 for p in inph(d)})
    head(fig, f"TDF 계획 변경 9번 중 {within}번이 사후 구분 하락 국면 안(국면 {nph}개에 몰림, 국면 비율 약 45%).\n"
              f"판독 오차 넘게 달라진 {nbig}개 중 {n_ins}개는 판독 방법이 바뀐 뒤에만 차이가 생겼고,\n"
              f"{nbig - n_ins}개는 같은 판독 방법에서도 바닥선 밖이었다(검정력 없음, 결과 뒤 구분)",
         "5대 운용사 TDF(2025~2055 빈티지 35개) 투자설명서 1,004판의 위험자산 비중 계획. 왼쪽 = 판본·변경 시점, 오른쪽 = 같은 실제 시장 경로에서\n"
         "'처음 공시한 계획을 끝까지 따랐다면' 대 '실제로 바뀐 계획을 따랐다면'(첫 판 다음 달 ~ 2026-08 또는 목표연도 말, 매달 같은 금액 적립)",
         f"시장 = 원화 주식 꾸러미(국내 15.2% + 선진국 84.8%, 환노출)·국고채 TR 월간. 보수는 두 계획에 같다고 보고 0. 판독 잡음 바닥선 = T3 정본 운용사별 약 {floor.min() * 100:.2f}%.\n"
         "변경 9번 = T3 정본(운용사·공시 묶음 단위, 펀드 기준 37쌍, 세는 기준에 따라 달라짐). 하락 국면은 사후 구분이고 기준 비율 0.446은 T3_10 값. 횟수가 적어 검정력이 없음(기술만).\n"
         f"비교 불가 = 곡선으로 읽을 수 있는 판이 2개 미만이거나, 첫 판 뒤 계산 기간이 없거나, 쓰인 판이 첫 판뿐. 신한·미래에셋 {len(short_)}개는 첫 곡선 판이 2026-04라 4개월 비교뿐.\n"
         "파랑·주황 구분(판독 방법이 처음 바뀌기 전 구간만 누적한 d)은 감사 뒤 결과를 보고 추가한 구분이고, 바닥선은 이 구간 길이에 맞춘 값이 아님.\n"
         "출처: raw glidepath_disclosed_hist_20261012fix, simpletest T3 full_r1(T3_07·T3_13b), pilot9 C2_components, pilot10 lt2020_events. 결과: T9_cf_by_fund.csv.")
    save(fig, "fig_T9_글라이드변경", pd.concat([M.assign(구분="운용사 요약"), ev.assign(구분="변경 9번")]))
    big = ok.loc[ok.d_적립.abs().idxmax()]
    readme(o, "9. TDF 글라이드패스 변경 이력 — 계획이 바뀐 게 가입자 금액을 얼마나 바꿨나",
        문제의식="""
TDF는 "나이에 따라 주식 비중을 이렇게 줄이겠다"는 계획(글라이드패스)을 투자설명서에 공시합니다. 그런데 이 계획이 중간에 바뀐 적이 있습니다. 가입할 때 본 계획과 실제로 따른 계획이 달랐다면, 가입자 금액은 얼마나 달라졌을까요? 그리고 계획 변경이 하락장에 몰렸을까요?
""",
        한_일=f"""
- 5대 운용사(KB·삼성·신한·한국투자·미래에셋) TDF 35개(2025~2055 빈티지)의 투자설명서 1,004판에서 뽑은 위험자산 비중표(10월 27일 T3)를 그대로 썼습니다.
- 펀드마다 "처음 공시한 계획(곡선으로 읽을 수 있는 첫 판)을 끝까지 따른 경우"와 "실제로 바뀐 계획을 공시 시점마다 갈아탄 경우"를, 같은 실제 시장 경로(원화 주식 꾸러미·국고채 월 수익, 2016~2026)에서 첫 판 다음 달부터 2026-08(또는 목표연도 말)까지 매달 같은 금액을 넣어 비교했습니다. 판정 규칙은 계산 전에 설계서에 적었습니다.
- 차이가 T3에서 잰 판독 잡음 바닥선(같은 판을 두 번 읽을 때 생기는 차이의 95%, 약 {floor.min() * 100:.2f}%) 안이면 "판독 오차와 구분 안 됨"으로 봤습니다.
- 변경 시점은 T3 정본의 9번(위험자산 비중 2.5%p 넘는 변경, 운용사·공시 묶음 단위)을 타임라인에 그렸습니다.
- 설계서 문구 정정(결과 보기 전): 설계서의 "그 달 말 이전에 접수된 판"을 "그 달 수익에는 전달 말까지 접수된 판"으로 구현했습니다(그 달 안에 공시된 계획을 그 달 초부터 쓰는 미래 정보 사용을 막기 위함).
- 결과: `results/T9_cf_by_fund.csv`(펀드별), 그림 `fig_T9_글라이드변경`.
""",
        결과=f"""
- **변경 9번 중 {within}번이 사후에 구분한 하락 국면 안이었습니다.** 이 국면은 전체 공시 기간의 약 45%(T3 기준 비율 0.446)입니다. {within}번은 국면 {nph}개에 몰려 있어 독립 사건 9개가 아니고, 국면 구분은 사후이며 후보 선택에 따라 달라집니다. 횟수가 적어 검정력이 없어 기술만 합니다(운용사별 KB 1, 삼성 2, 신한 4, 한국투자 2, 미래에셋 0).
- **처음 계획을 지켰을 때와 비교할 수 있는 펀드는 {len(ok)}개**였고(나머지 {len(T) - len(ok)}개는 비교 불가), 이 중 의미 있는 기간({int(long_.개월.min())}~{int(long_.개월.max())}개월)을 가진 것은 {'·'.join(sorted(set(long_.운용사)))} {len(long_)}개이고, 신한·미래에셋 {len(short_)}개는 첫 곡선 판이 2026-04라 {int(short_.개월.max())}개월 비교뿐입니다(그래서 d ≈ 0).
- 금액 차이가 판독 잡음 바닥선보다 큰 펀드는 {nbig}개입니다. 감사(H2) 뒤 판독 방법이 처음 바뀌기 전 구간만 따로 누적해 보니(결과 뒤 추가한 구분): {n_same}개({fl_('같은 방법 구간에서도 바닥선 밖')})는 같은 방법 구간만으로도 바닥선 밖이고, {n_ins}개({fl_('방법 변경 뒤에만 차이(나눌 수 없음)')})는 차이가 방법 변경 뒤에만 생겨 계획 변경과 판독 방법 차이를 나눌 수 없으며, {n_none}개({fl_('판독 방법 변경 없음')})는 방법 변경을 건너지 않았습니다. 처음 보고서(b64ec7a)의 "17개 중 15개는 방법 변경과 나눌 수 없다"는 틀린 문장이었습니다(경로 어디서든 방법이 바뀐 판을 한 번이라도 쓰면 '나눌 수 없음'으로 셌음).
""" + "\n".join(f"- {r.운용사}: 비교 {r.펀드}개, 비교 불가 {r.비교불가}개" + (f"(첫 판 {r.첫판_최소}~{r.첫판_최대}, 계산 기간 {int(r.개월_최소)}~{int(r.개월_최대)}개월), 실제 ÷ 처음 계획 금액 로그 {r.d_최소 * 100:+.2f}~{r.d_최대 * 100:+.2f}%(중앙 {r.d_중앙 * 100:+.2f}%), 월 10만 원 적립 기준 금액 차이 {r.금액차_최소:+,.0f}~{r.금액차_최대:+,.0f}원, 바닥선 밖 {r.바닥선밖}개, 판독 방법 변경을 건넌 펀드 {int(r.방법변경건넘)}개" if r.펀드 else "") + "." for r in M.itertuples()) + f"""
- 가장 큰 차이: {big.운용사} {big.빈티지} ({big.code}), {big.첫판}~{big.끝월} {big.개월}개월, 로그 {big.d_적립 * 100:+.2f}%(월 10만 원 적립, 원금 {big.적립원금:,.0f}원 기준 {big.월10만원_금액차:+,.0f}원). 위험자산 비중 차이는 최대 {big.위험비중차_최대 * 100:.1f}%p.
""",
        말하면_안_되는_것="""
- "운용사가 하락장을 예측해서 계획을 바꿨다" / "하락장에 몰렸다" — 9번뿐이고 국면은 사후 구분이라 검정력이 없습니다.
- "계획 변경으로 가입자가 손해(이득)를 봤다" — 판독 오차보다 큰 차이는 일부 펀드뿐이고, 일부는 방법 변경 뒤에만 차이가 생겨 방법 차이와 분리되지 않으며, 바닥선은 체계적 판독 차이를 담지 못합니다. 지수 × 비중 근사이지 실제 펀드 수익이 아닙니다.
- "하락 국면 안에 몰렸다" — 국면 안의 변경은 국면 몇 개 안에 묶여 있어 독립 사건이 아닙니다.
- 정확 이항 p 값을 근거로 쓰기(T3 SAY_OK 금지 목록).
""",
        한계="""
- 실제 펀드가 아니라 '공시 위험자산 비중 × 지수' 근사입니다. 위험자산 안의 구성(국내·해외, 환헤지) 변화는 반영하지 않았고, 보수는 두 계획에 같다고 보고 0으로 뒀습니다.
- 오래된 빈티지의 첫 판은 그 시점 이후 구간만 공시해 범위 밖은 끝값으로 고정했습니다(`범위밖비율` 열).
- 신한은 2026-04 이전 판 대부분이 0년 지점·그래프 왼쪽 끝만 읽혀 곡선을 만들 수 없고, 미래에셋은 2026-04 이전 판에 그래프가 없습니다. 그래서 두 운용사는 첫 곡선 판이 2026-04이고 비교가 4개월뿐입니다. 신한의 2018~2021년 변경 4번은 금액 계산에 들어가지 못했습니다.
- 바닥선은 T3의 2055·양식화 경로 조건에서 같은 판독 방법 안의 무작위 오차로 만든 값입니다. 지평이 다른 이 계산과, 같은 방법 안의 체계적 판독 차이·방법 변경의 체계적 차이에는 그대로 맞지 않습니다. 그래서 '같은 방법 구간에서도 바닥선 밖'도 "계획 변경 효과"라고 단정하지 않습니다.
- 설계서 문구("그 달 말 이전 접수") 그대로 구현했다면 바닥선 밖이 1개 늘어 18개였습니다(감사 L1; 구현은 미래 정보가 없는 '전달 말까지' 쪽). 이 정정은 결과와 같은 커밋(9761f8b)에 들어가 git으로 '결과 전'을 확인할 수는 없습니다.
- 변경 9번은 T3 정본의 운용사·공시 묶음 단위이고, 펀드 기준으로는 37쌍이라 세는 기준에 따라 달라집니다(DOC_AUDIT 9절).
- 5대 운용사의 현존 펀드만 봤고 청산·합병 TDF는 없습니다.
- 한 번뿐인 실제 시장 경로라 다른 시장에서는 크기·부호가 달라질 수 있습니다. 10월 27일 T3의 반사실(모든 빈티지를 2001년 30세로 놓은 양식화 계산, T3_14)과는 기간 정의가 다릅니다.
- 미국 선행연구(Brown·Davies·Sobotka)는 제목만 확인했고 원문 대조는 하지 않았습니다.
""")
    return dict(M=M, ev=ev[["운용사", "묶음날짜"]], within=within)


# ── 10번: 분기 보고서로 목표 − 실제 ───────────────────────────────────────────
def t10():
    o = out("10_TDF재매수")
    cp = rd(r"pilot10_20261017\T1_rebuy\T1c_calib_points.csv")
    VC = ["S_1", "S_6b_Fbd", "S_6a_Feq"]
    assert cp.groupby(["code", "period_end"])[VC].nunique().max().max() == 1
    P = cp.drop_duplicates(["code", "period_end"])[["code", "manager", "period_end"] + VC]
    t1d = rd(r"pilot8_20261010\T1d_desc\t1d_rows.csv")
    chk = t1d.merge(P, left_on=["code", "pe_prev"], right_on=["code", "period_end"], suffixes=("_t1d", ""))
    bad = chk[~np.isclose(chk[[c + "_t1d" for c in VC]].to_numpy(), chk[VC].to_numpy()).all(axis=1)]
    assert len(chk) == len(t1d) and (bad.pe_prev > "2024-12-31").all()                           # pilot8 t1d(pe_prev 기준)와 2024년까지 같은 값
    csv(bad[["code", "manager", "pe_prev"]].assign(**{f"{c}_차(t1d−T1c)": bad[c + "_t1d"] - bad[c] for c in VC}), "T10_pilot8_mismatch",
        "pilot8 t1d_rows(pe_prev 기준)와 pilot10 T1c 값이 다른 보고서(모두 2025년 이후 → 분석 창 밖). 원인 미확인.\n"
        "이 저장소 판은 두 값 대신 차이만 둠(비중 값과 10번 격차 표를 합치면 공시 글라이드 값이 되살아나므로).")
    gl = rd(r"pilot8_20261010\T1_reduced\t1r_glide_at_reports.csv")
    P = P.merge(gl[["code", "period_end", "vintage", "Shist", "S2026_own", "active_rcept_dt"]], on=["code", "period_end"], how="left", validate="1:1")
    assert P.Shist.notna().all() and P.S2026_own.notna().all()
    P["pe"] = pd.to_datetime(P.period_end)
    for tg in ("Shist", "S2026_own"):
        P[f"g_{tg}"], P[f"lo_{tg}"], P[f"hi_{tg}"] = P.S_1 - P[tg], P.S_6b_Fbd - P[tg], P.S_6a_Feq - P[tg]
    csv(P.assign(점경계밖=~P.S_1.between(P.S_6b_Fbd, P.S_6a_Feq)), "T10_gap_by_report",
        "보고서별 위험자산 비중(점 S_1, 경계 S_6b_Fbd~S_6a_Feq; pilot10 T1c_calib_points, pilot8 t1d_rows와 일치 assert) − 목표(그때 유효 공시 Shist, 민감도 2026 공시 S2026_own).\n"
        "이 저장소 판은 격차(g·lo·hi = 점·하한·상한 − 목표)와 점경계밖(점 S_1이 경계 밖)만 두고 비중 값·목표(공시 글라이드)·공시일 열은 뺌.",
        drop=["S_1", "S_6b_Fbd", "S_6a_Feq", "Shist", "S2026_own", "active_rcept_dt", "pe"])
    TR = pd.Timestamp("2022-09-30")
    rows = []
    for tg in ("Shist", "S2026_own"):
        for c, d in P.sort_values("pe").groupby("code"):
            b = d[d.pe <= TR]
            if not len(b):
                continue
            b, af = b.iloc[-1], d[d.pe > TR]
            lvl = "목표보다 낮음" if b[f"hi_{tg}"] < 0 else "목표보다 높음" if b[f"lo_{tg}"] > 0 else "가려낼 수 없음"
            for k in (1, 2, 4):
                if len(af) < k:
                    continue
                a = af.iloc[k - 1]
                lo, hi = a[f"lo_{tg}"] - b[f"hi_{tg}"], a[f"hi_{tg}"] - b[f"lo_{tg}"]
                pre = "목표 쪽으로 다시 올라옴" if lo > 0 else "더 벌어짐" if hi < 0 else "가려낼 수 없음"
                brk = any(not (x.S_6b_Fbd <= x.S_1 <= x.S_6a_Feq) for x in (a, b))   # 점이 경계 밖 = 경계 불성립
                rows.append(dict(목표=tg, code=c, manager=b.manager, vintage=b.vintage, 기준보고서=b.period_end, 기준격차=b[f"g_{tg}"], 기준_하=b[f"lo_{tg}"], 기준_상=b[f"hi_{tg}"],
                                 기준판정=lvl, k=k, 뒤보고서=a.period_end, 변화_점=a[f"g_{tg}"] - b[f"g_{tg}"], 변화_하=lo, 변화_상=hi,
                                 판정_설계서=pre, 경계불성립=brk, 기준경계불성립=(bb := not (b.S_6b_Fbd <= b.S_1 <= b.S_6a_Feq)),
                                 기준판정_보류규칙="판정 보류(경계 불성립)" if bb and lvl != "가려낼 수 없음" else lvl,   # 재감사 R1-H1: 같은 규칙을 기준판정에도
                                 # 감사 H3 뒤 규칙(결과 뒤): 두 보고서 중 하나라도 점이 경계 밖이면 방향 판정 보류
                                 판정="판정 보류(경계 불성립)" if brk and pre != "가려낼 수 없음" else pre))
    D = pd.DataFrame(rows)
    csv(D, "T10_change_after_trough", f"2022-09-30(E2021 저점) 이전 마지막 보고서 대비 1·2·4번째 뒤 보고서의 격차 변화. 경계 = [하(뒤) − 상(기준), 상(뒤) − 하(기준)]. 판정_설계서 = {DESIGN}.\n"
        "감사(H3) 뒤 규칙, 결과 뒤 변경: 경계불성립 = 기준·뒤 보고서 중 하나라도 점 S_1이 [S_6b_Fbd, S_6a_Feq] 밖. 이때 방향 판정은 '판정 보류(경계 불성립)'(판정 열). '가려낼 수 없음'은 그대로.\n"
        "재감사(R1-H1) 뒤 같은 규칙을 기준 수준에도: 기준판정_보류규칙 = 기준 보고서 점이 경계 밖이면 '낮음/높음'을 보류. 설계서 판정은 기준판정 열.")
    cnt = D.groupby(["목표", "k", "판정"]).size().unstack(fill_value=0).reset_index()
    lv = D[D.k == 1].groupby(["목표", "기준판정_보류규칙"]).size().unstack(fill_value=0).reset_index()
    lv0 = D[D.k == 1].groupby(["목표", "기준판정"]).size().unstack(fill_value=0)                       # 설계서 판정 그대로
    MN = {"kb": "KB", "kim": "한국투자", "samsung": "삼성"}

    Q = P.assign(q=P.pe.dt.to_period("Q")).groupby("q")[["g_Shist", "lo_Shist", "hi_Shist"]].median().reset_index()
    Q["n"] = P.assign(q=P.pe.dt.to_period("Q")).groupby("q").size().values
    fig = plt.figure(figsize=(9.5, 6.0))
    ax = fig.add_axes([0.08, 0.25, 0.54, 0.38]); bx = fig.add_axes([0.72, 0.25, 0.26, 0.38])
    xq = Q.q.dt.to_timestamp(how="end")
    ax.fill_between(xq, Q.lo_Shist * 100, Q.hi_Shist * 100, color=LGREY, step="mid", label="경계(안 실린 몫 전부 채권 ~ 전부 주식) 중앙값")
    ax.plot(xq, Q.g_Shist * 100, color=BLUE, marker="o", ms=3, lw=1.4, label="점 추정(실린 종목 비례 확대) 중앙값")
    ax.axhline(0, color="black", lw=0.6); ax.axvline(TR, color="#B03A2E", lw=0.8, ls="--")
    ax.text(TR, 12, " 2022-09\n 저점", color="#B03A2E", fontsize=8, va="top")
    ax.set_ylim(-30, 16); ax.set_ylabel("실제 − 목표 위험자산 비중 (%p)"); ax.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(2022, 2027)]), range(2022, 2027))
    ax.legend(fontsize=7.5, frameon=False, loc="lower left")
    ax.set_title(f"분기별 펀드 중앙값(KB·한국투자·삼성 {P.code.nunique()}개 펀드, 보고서 {len(P)}개)", loc="left", fontsize=8.5, color="#222")
    d1 = D[D.목표 == "Shist"]
    col = {"목표 쪽으로 다시 올라옴": BLUE, "더 벌어짐": "#B03A2E", "가려낼 수 없음": GREY, "판정 보류(경계 불성립)": "#E08E0B"}
    for j, k in enumerate((1, 2, 4)):
        z = d1[d1.k == k].sort_values("변화_점").reset_index(drop=True)
        xs = j + np.linspace(-0.35, 0.35, len(z))
        bx.vlines(xs, z.변화_하 * 100, z.변화_상 * 100, color=[col[p] for p in z.판정], lw=1)
        bx.scatter(xs, z.변화_점 * 100, s=6, color="black", zorder=3)
    bx.axhline(0, color="black", lw=0.6)
    bx.set_xticks(range(3), ["1분기 뒤", "2분기 뒤", "4분기 뒤"], fontsize=8)
    bx.set_ylabel("저점 직전 대비 격차 변화 (%p)", fontsize=8)
    bx.set_title("펀드별 변화와 경계\n(회색 = 0 포함, 주황 = 경계 불성립 보류)", loc="left", fontsize=8, color="#222")
    c1 = cnt[(cnt.목표 == "Shist")].set_index("k")
    getc = lambda k, p: int(c1.loc[k, p]) if p in c1.columns else 0
    bw = (P.S_6a_Feq - P.S_6b_Fbd) * 100; dw = (d1[d1.k == 1].변화_상 - d1[d1.k == 1].변화_하) * 100
    q4 = lambda k: "·".join(str(getc(k, p)) for p in ("목표 쪽으로 다시 올라옴", "더 벌어짐", "가려낼 수 없음", "판정 보류(경계 불성립)"))
    head(fig, f"2022년 하락장 저점 뒤 TDF가 주식을 목표만큼 다시 샀는지:\n보고서에 안 실린 몫 때문에 변화 경계 폭이 중앙 약 {dw.median():.0f}%p라\n"
              f"{d1[d1.k == 1].code.nunique()}개 펀드 중 {getc(1, '가려낼 수 없음')}개가 가려낼 수 없었다(1분기 뒤)",
         "분기 자산운용보고서 보유내역으로 잰 위험자산(주식 등) 비중 − 그때 유효했던 공시 글라이드 목표. 보고서에는 상위 10종목·5% 초과만 실려\n"
         f"안 실린 몫을 전부 채권 ~ 전부 주식으로 채운 경계(보고서별 폭 {bw.min():.0f}~{bw.max():.0f}%p, 중앙 {bw.median():.0f}%p)를 같이 봄.\n"
         "판정(설계서): 변화 경계가 0 밖이면 방향, 0 포함이면 가려낼 수 없음",
         f"변화 = 2022-09-30 이전 마지막 보고서 대비, 올라옴·벌어짐·가려낼 수 없음·보류 순: 1분기 뒤 {q4(1)}, 2분기 뒤 {q4(2)}, 4분기 뒤 {q4(4)}.\n"
         "보류 = 두 보고서 중 하나에서 점 추정이 경계 밖이라 경계가 성립하지 않음(감사 뒤 추가한 규칙, 설계서 판정은 CSV '판정_설계서' 열).\n"
         f"저점 직전 수준(낮음·높음·가려낼 수 없음·보류): {'·'.join(str(int(lv.set_index('목표').loc['Shist'].get(p, 0))) for p in ('목표보다 낮음', '목표보다 높음', '가려낼 수 없음', '판정 보류(경계 불성립)'))}"
         f"(설계서 판정 그대로면 {'·'.join(str(int(lv0.loc['Shist'].get(p, 0))) for p in ('목표보다 낮음', '목표보다 높음', '가려낼 수 없음'))}·0, 같은 보류 규칙을 결과 뒤 적용).\n"
         "신한(통화별 표 없음)·미래에셋(최신 1건)은 제외. 2018년 하락장(저점 2020-03)은 고점 전 보고서가 0건이라 계산 불가. 저점 전 보고서는 2022-01 이후뿐(고점 2021-06 전 없음).\n"
         "출처: pilot10 T1_rebuy T1c_calib_points(보고서별 비중), pilot8 t1d_rows(대조)·t1r_glide_at_reports(목표). 결과: T10_gap_by_report·T10_change_after_trough.csv.")
    save(fig, "fig_T10_TDF재매수", pd.concat([Q.assign(q=Q.q.astype(str), 구분="분기 중앙값"), cnt.assign(구분="변화 판정 수"), lv.assign(구분="기준 격차 판정 수")]))
    cn = lambda tg, k, p: int(cnt.set_index(["목표", "k"]).loc[(tg, k), p]) if p in cnt.columns else 0
    lvn = lambda tg, p: int(lv.set_index("목표").loc[tg, p]) if p in lv.columns else 0
    hold = D[(D.목표 == "Shist") & (D.판정 == "판정 보류(경계 불성립)")]
    c4 = lambda tg, k: "·".join(str(cn(tg, k, p)) for p in ("목표 쪽으로 다시 올라옴", "더 벌어짐", "가려낼 수 없음", "판정 보류(경계 불성립)"))
    out_by = lambda x: max(x.S_6b_Fbd - x.S_1, x.S_1 - x.S_6a_Feq, 0) * 100                      # 점이 경계 밖으로 나간 폭(%p)
    Pi = P.set_index(["code", "period_end"])
    hb = [max(out_by(Pi.loc[(r.code, r.기준보고서)]), out_by(Pi.loc[(r.code, r.뒤보고서)])) for r in hold.itertuples()]
    holdtxt = (f"- 판정 보류 {len(hold)}개는 {', '.join(sorted({f'{MN.get(m, m)} {b}~{a}' for m, b, a in zip(hold.manager, hold.기준보고서, hold.뒤보고서)}))} 비교입니다(k = {'·'.join(map(str, sorted(set(hold.k))))}). "
               f"설계서 규칙으로는 '{'·'.join(sorted(set(hold.판정_설계서)))}' 판정이었지만, 점 추정이 경계 밖으로 {min(hb):.0f}~{max(hb):.0f}%p 나가 경계가 성립하지 않았고, "
               f"같은 비교의 점 추정 변화는 {hold.변화_점.min() * 100:+.1f}~{hold.변화_점.max() * 100:+.1f}%p였습니다. 방향으로 읽지 않습니다.") if len(hold) else "- 판정 보류는 없었습니다."
    bh = D[(D.목표 == "Shist") & (D.k == 1) & (D.기준판정_보류규칙 == "판정 보류(경계 불성립)")]
    basetxt = (f"보류 {len(bh)}개({', '.join(f'{MN.get(m, m)} {v}' for m, v in sorted(zip(bh.manager, bh.vintage)))})는 기준 보고서에서 점 추정이 경계 밖이라 경계가 성립하지 않고, "
               f"점 추정 격차는 {bh.기준격차.min() * 100:+.2f}~{bh.기준격차.max() * 100:+.2f}%p입니다(재감사 R1-H1 뒤 같은 규칙을 기준 수준에도 적용, 결과 뒤 변경).") if len(bh) else ""
    readme(o, "10. TDF는 하락장 뒤 주식을 다시 사 주나 — 분기 보고서로 직접 재 보기",
        문제의식="""
TDF는 나이에 맞춰 정한 주식 비중(목표)을 유지해야 합니다. 하락장에 주가가 떨어지면 주식 비중이 저절로 낮아지므로, 계획대로라면 바닥 뒤 주식을 다시 사서 목표로 돌아와야 합니다. 10월 19일 F에서는 일별 기준가로 비중을 추정했는데 그 방법이 한쪽으로 치우쳐, 이번에는 분기 자산운용보고서의 실제 보유내역으로 직접 쟀습니다.
""",
        한_일=f"""
- 이미 모은 분기 자산운용보고서 보유내역에서 pilot10 T1c가 보고서마다 계산한 위험자산 비중을 썼습니다(KB·한국투자·삼성 {P.code.nunique()}개 펀드, 보고서 {len(P)}개, {P.period_end.min()}~{P.period_end.max()}). pilot8에서 같은 보고서로 잰 값과 같은지 확인했습니다.
- 보고서에는 상위 10종목과 5% 넘는 종목만 실립니다. 안 실린 몫을 전부 채권으로 본 값(하한)과 전부 주식으로 본 값(상한)을 경계로, 실린 종목을 비례로 늘린 값을 점으로 봤습니다. 경계 폭은 보고서별 {bw.min():.0f}~{bw.max():.0f}%p(중앙 {bw.median():.0f}%p)입니다.
- 목표 = 그 보고서 날짜에 유효했던 투자설명서 글라이드(민감도: 2026년 공시).
- 판정 규칙(계산 전 설계서): 2022-09 저점 이전 마지막 보고서 대비 1·2·4번째 뒤 보고서의 '실제 − 목표' 변화가 경계째 0 위면 "목표 쪽으로 다시 올라옴", 0 아래면 "더 벌어짐", 0을 포함하면 "가려낼 수 없음".
- **결과 뒤 추가한 규칙(감사 H3)**: 기준·뒤 보고서 중 하나라도 점 추정이 경계 밖이면 그 보고서의 경계가 성립하지 않으므로, 방향 판정을 "판정 보류(경계 불성립)"로 바꿨습니다. 재감사(R1-H1)에서 이 규칙을 저점 뒤 변화에만 쓰고 저점 직전 수준(낮음/높음)에는 쓰지 않은 비대칭을 지적받아, 같은 규칙을 저점 직전 수준에도 적용했습니다. 설계서 판정은 `T10_change_after_trough.csv`의 `판정_설계서`·`기준판정` 열에 그대로 남겼습니다.
- 결과: `T10_gap_by_report.csv`, `T10_change_after_trough.csv`, 그림 `fig_T10_TDF재매수`.
""",
        결과=f"""
- **할 수 있었던 사건은 2022년 하락장(고점 2021-06, 저점 2022-09) 하나**였습니다. 2018년 하락장(저점 2020-03)은 고점 전 보고서가 한 건도 없어 계산하지 못했습니다.
- **저점 직전 '실제 − 목표'**(그때 유효 목표): {d1[d1.k == 1].code.nunique()}개 펀드 중 목표보다 낮음 {lvn('Shist', '목표보다 낮음')}개, 높음 {lvn('Shist', '목표보다 높음')}개, 가려낼 수 없음 {lvn('Shist', '가려낼 수 없음')}개, 판정 보류(경계 불성립) {lvn('Shist', '판정 보류(경계 불성립)')}개. 설계서 규칙 그대로면 낮음 {int(lv0.loc['Shist'].get('목표보다 낮음', 0))}·높음 {int(lv0.loc['Shist'].get('목표보다 높음', 0))}·가려낼 수 없음 {int(lv0.loc['Shist'].get('가려낼 수 없음', 0))}개입니다(CSV `기준판정` 열). {basetxt}
- 목표를 2026년 공시로 바꾸면 저점 직전: 낮음 {lvn('S2026_own', '목표보다 낮음')}·높음 {lvn('S2026_own', '목표보다 높음')}·가려낼 수 없음 {lvn('S2026_own', '가려낼 수 없음')}·보류 {lvn('S2026_own', '판정 보류(경계 불성립)')}개.
- **저점 뒤 변화**(그때 유효 목표, 올라옴·벌어짐·가려낼 수 없음·판정 보류 순): 1분기 뒤 {c4('Shist', 1)}개, 2분기 뒤 {c4('Shist', 2)}개, 4분기 뒤 {c4('Shist', 4)}개. 방향(올라옴·벌어짐)이 나온 칸은 {int(D[D.목표 == 'Shist'].판정.isin(['목표 쪽으로 다시 올라옴', '더 벌어짐']).sum())}개입니다.
{holdtxt}
- 목표를 2026년 공시로 바꾸면: 1분기 뒤 {c4('S2026_own', 1)}개, 2분기 뒤 {c4('S2026_own', 2)}개, 4분기 뒤 {c4('S2026_own', 4)}개(같은 순서).
- 변화 경계 폭(1분기 뒤)은 중앙 {dw.median():.0f}%p라 '가려낼 수 없음'은 TDF 행동에 대한 정보라기보다 측정 방법(안 실린 몫)의 한계에서 거의 구조적으로 나옵니다.
- 점 추정 중앙값(분기별)은 {Q.g_Shist.min() * 100:+.1f}~{Q.g_Shist.max() * 100:+.1f}%p 사이였습니다.
""",
        말하면_안_되는_것="""
- "TDF는 하락장 뒤 주식을 다시 사지 않는다" / "제대로 되산다" — 경계가 0을 포함한 칸은 어느 쪽도 말할 수 없습니다.
- 점 추정(비례 확대)만 보고 판단하기 — 안 실린 몫이 크고, 점 추정은 그 몫이 실린 종목과 같은 비율이라는 가정입니다.
""",
        한계=f"""
- 보고서에 안 실린 몫이 커서 경계가 넓습니다. 이것이 결과를 '가려낼 수 없음' 쪽으로 미는 가장 큰 이유입니다.
- 점 추정(실린 종목 비례 확대)은 경계 안에 있다는 보장이 없습니다(경계는 원화 현금 몫을 늘 안전자산으로 두기 때문). 보고서 {len(P)}개 중 {int(((P.S_1 < P.S_6b_Fbd) | (P.S_1 > P.S_6a_Feq)).sum())}개에서 점이 경계 밖이었습니다. 그런 보고서가 들어간 방향 판정(저점 뒤 변화와 저점 직전 수준 모두)은 결과 뒤 규칙으로 보류했습니다(위). 저점 직전 기준 보고서 중 점이 경계 밖인 것은 {int(D[(D.목표 == 'Shist') & (D.k == 1)].기준경계불성립.sum())}개입니다.
- pilot8의 같은 보고서 값과 대조했을 때 2025년 이후 보고서 {len(bad)}행이 달랐습니다({', '.join(f'{MN.get(m, m)} {n}행' for m, n in bad.groupby('manager').size().items())}, `T10_pilot8_mismatch.csv`, 원인 미확인). 그래서 설계서의 "같은지 assert"를 "2024년까지 같은지"로 완화했습니다(결과 뒤 변경). 판정 창(2022~2023년)에는 영향이 없고, 그림의 2025~2026년 분기 값에는 들어 있습니다.
- KB·한국투자·삼성만 들어갔습니다. 신한은 통화별 표가 없어 같은 방식으로 나눌 수 없고, 미래에셋은 최신 보고서 1건뿐입니다. 한국투자 2022-03 보고서는 암호화로 받지 못했습니다.
- 사건이 하나뿐이고, 저점 전 보고서는 2022-01 이후만 있어 고점(2021-06) 무렵 비중은 보지 못했습니다. 2021년 보고서 일부(KB 6·한국투자 1·삼성 1 펀드, 다른 폴더)와 2026년 하락 뒤 새 보고서는 아직 파싱하지 않았습니다.
- 위험자산 = 투자설명서 정의(주식·금 등). 목표 글라이드는 그래프 판독 값입니다.
- 현존 펀드만 봤고 청산·합병 TDF는 없습니다.
""")
    return dict(cnt=cnt, lv=lv, Q=Q)


# ── 12번: 원화 30년(기존 결과 정리) ──────────────────────────────────────────
def t12():
    o = out("12_원화30년")
    b = rd(rf"{S2}\T2_boot_cells.csv"); ph = rd(rf"{S2}\T2_cushion_phases.csv"); iu = rd(rf"{S2}\T2_independent_units.csv")
    mde = rd(rf"{S2}\T2_mde.csv")
    log(path(rf"{S2}\SAY_OK_T2.txt"))                         # 문장 허용 범위(읽기만, 기록용)
    DC = ["D7", "D8", "D9", "D10", "D11", "D17"]
    PORT = ["①", "②", "③", "③H", "④", "④H", "⑤"]
    k = b[b.표본.isin(["KR1991", "KR1996", "KR~2024"]) & (b.경로수 == 10000) & (b.D5 == "A") & (b.D6 == "A") & b.포트.isin(PORT)
          & b[DC].apply(lambda c: c.isna() | (c == "A")).all(axis=1)].copy()
    k["블록종류"] = np.where(k.블록출처.str.startswith("PW"), "PW", np.where(k.블록출처.str.startswith("120"), "120", k.블록출처))
    assert k.groupby(["표본", "블록종류", "포트"]).size().eq(1).all() and len(k) == 3 * 4 * 7
    base = k[(k.표본 == "KR1991") & (k.블록종류 == "PW")].set_index("포트").p
    assert np.allclose(base[["①", "②", "③", "③H", "④", "④H", "⑤"]], [0.1296, 0.0407, 0.0011, 0.0005, 0.0021, 0.0010, 0])   # SAY_OK 1번
    rng = k[k.블록종류 != "120"].groupby("포트").p.agg(["min", "max"]); r120 = k[k.블록종류 == "120"].groupby("포트").p.agg(["min", "max"])
    c = ph[(ph.패널 == "1991~ 패널") & ph.계열.isin(["eq", "us"])].pivot(index=["고점", "저점", "하락20이상"], columns="계열", values="고점_저점").reset_index()
    assert len(c) == 11 and (c["us"] > c["eq"]).all() and (c["us"] > 0).sum() == 6 and c.하락20이상.sum() == 7
    m97 = c[c.고점 != "1994-10"].us.mean()
    LAB = {"①": "① 국내주식 100", "②": "② 국내 60·채권 40", "③": "③ 미국주식 원화(환노출)", "③H": "③H 미국주식 환헤지", "④": "④ 국내 33·해외 67(환노출)",
           "④H": "④H ④의 환헤지", "⑤": "⑤ TDF 2055 평균 글라이드"}
    fig = plt.figure(figsize=(9.5, 6.0))
    ax = fig.add_axes([0.25, 0.25, 0.33, 0.42]); bx = fig.add_axes([0.70, 0.25, 0.28, 0.42])
    for i, p in enumerate(PORT):
        ax.hlines(i, rng.loc[p, "min"] * 100, rng.loc[p, "max"] * 100, color=LGREY, lw=6)
        ax.scatter(r120.loc[p].values * 100, [i, i], marker="|", s=60, color=GREY)
        ax.scatter(base[p] * 100, i, color=BLUE, s=24, zorder=3)
        ax.text(max(rng.loc[p, "max"], base[p]) * 100 + 0.8, i, f"{base[p] * 100:.1f}%", va="center", fontsize=8, color=BLUE)
    ax.set_yticks(range(7), [LAB[p] for p in PORT], fontsize=8.5); ax.invert_yaxis()
    ax.set_xlabel("30년 뒤 실질 금액 < 실질 납입인 경로 비율 (%)", fontsize=8.5); ax.set_xlim(-0.5, 30)
    ax.set_title("● 기준(1991~, 자동 블록)  ▬ 표본·블록 9칸 범위\n| 블록 120개월(한 역사 재배열, 참고)", loc="left", fontsize=8, color="#222")
    cc = c.sort_values("고점").reset_index(drop=True)
    y = np.arange(len(cc))
    bx.barh(y - 0.2, cc["eq"] * 100, 0.38, color=GREY, label="국내주식(KOSPI200)")
    bx.barh(y + 0.2, cc["us"] * 100, 0.38, color=BLUE, label="미국주식(원화 환산)")
    bx.axvline(0, color="black", lw=0.6)
    bx.set_yticks(y, [f"{r.고점[:4]}~{r.저점[2:4]}" + (" *" if r.하락20이상 else "") for r in cc.itertuples()], fontsize=7.5); bx.invert_yaxis()
    bx.set_xscale("symlog", linthresh=100); bx.set_xlim(-80, 400)
    bx.set_xticks([-50, 0, 50, 100, 350], ["−50", "0", "50", "100", "350"], fontsize=7.5)
    bx.set_xlabel("고점→저점 누적 수익 (%)", fontsize=8.5); bx.legend(fontsize=7, frameon=False, loc="lower right")
    bx.set_title("한국 주가 하락 국면 11번\n(* = 코스피 20% 이상 하락, 7번)", loc="left", fontsize=8.5, color="#222")
    head(fig, f"원화로 30년 모은 경우, 국내주식만 담으면 경로의 약 {base['①'] * 100:.0f}%가 물가 뺀 원금보다 적었다\n(표본·블록에 따라 {rng.loc['①', 'min'] * 100:.0f}~{rng.loc['①', 'max'] * 100:.0f}%), 해외주식을 섞은 조합은 0~{max(rng.loc[p, 'max'] for p in PORT[2:]) * 100:.1f}%",
         "한국 월간 자료(1991-04~2026-08 등)를 블록으로 다시 뽑은 30년 경로 1만 개, 매달 같은 금액 적립. 손실 = 30년 뒤 실질 금액 < 실질 납입 누계\n"
         "겹치지 않는 30년이 1개뿐이라 조합 사이 차이는 가려낼 수 없음(통계 판정 없이 기술만)\n"
         "오른쪽: 1991년 이후 한국 주가 하락 국면 11번의 고점→저점 누적 수익. 11번 모두 원화 미국주식이 덜 빠졌지만 5번은 미국주식도 손실",
         f"9칸 = 표본 3(1991~, 1996~, ~2024) × 블록 3(자동 PW, 12개월, iid). 블록 120개월 칸(| 표시)은 425개월을 3.5블록으로 재배열한 것이라 참고만.\n"
         f"하락 국면 평균(원화 미국주식 {c["us"].mean() * 100:+.1f}%)은 1994~98년 국면(+{c[c.고점 == '1994-10'].us.iloc[0] * 100:.0f}%, 외환위기) 하나가 끌어올림 — 빼면 {m97 * 100:+.1f}%. 20% 이상 하락 표시는 코스피 종합 기준, 막대는 KOSPI200.\n"
         "③H·④H 환헤지는 CD91 − 미국 T-bill 금리차 근사. 보수 반영, 세금 0(계좌 안). 동결 결과를 다시 그린 것(새 계산 없음).\n"
         "출처: simpletest_20261027 T2_boot_cells·T2_cushion_phases·T2_independent_units·T2_mde.csv, SAY_OK_T2.txt.")
    save(fig, "fig_T12_원화30년", pd.concat([k.assign(구분="손실 경로 비율"), c.assign(구분="하락 국면")]))
    i1 = iu[(iu.묶음 == "단일") & (iu.표본 == "KR1991")].iloc[0]
    md = mde[(mde.표본 == "KR1991") & (mde.종류 == "차이")] if "종류" in mde.columns else mde
    readme(o, "12. 원화로 저축하는 30세에게 \"30년이면 주식은 안전하다\"가 맞나",
        문제의식="""
"30년 묻어 두면 주식은 손해 보지 않는다"는 말은 주로 미국 자료에서 나왔습니다. 원화로 벌고 원화로 은퇴하는 한국 저축자에게도 맞을까요? 또 1997년·2008년처럼 한국 주가가 떨어질 때 원화 가치도 함께 떨어진 적이 있어, 환율 위험을 막지 않은 해외주식이 원화로는 손실을 덜어 줬을 수 있습니다.
""",
        한_일=f"""
- 10월 27일 T2에서 이미 계산하고 감사(3회)를 거친 결과를 그림 1장과 이 요약으로 정리했습니다. 새 계산은 없습니다.
- 한국 월간 자료(1991-04~2026-08, {int(i1.개월)}개월)를 블록 부트스트랩으로 다시 뽑아 30년 적립 경로 1만 개를 만들고, 일곱 조합의 '30년 뒤 물가 뺀 금액이 물가 뺀 납입 누계보다 적은 경로 비율'을 셌습니다.
- 표본(1991~, 1996~, 2024년까지)과 블록 길이(자동 추정, 12개월, 1개월=iid, 120개월)를 바꿔 같은 계산을 했습니다.
- 1991년 이후 한국 주가 하락 국면 11번에서 국내주식과 원화로 환산한 미국주식의 고점→저점 누적 수익을 비교했습니다.
- 다국가(한국 1980~ 코스피, French 21개국+미국, OECD 17개국)로도 이미 계산했지만, 원화 조합 비교는 한국 자료로만 할 수 있어 이 그림에는 넣지 않았습니다.
""",
        결과=f"""
- **국내주식만 담으면 경로의 약 {base['①'] * 100:.0f}%({base['①']:.4f})가 30년 뒤 물가 뺀 원금보다 적었습니다**(1991~, 자동 블록). 표본·블록에 따라 {rng.loc['①', 'min'] * 100:.1f}~{rng.loc['①', 'max'] * 100:.1f}%, 블록 120개월 칸까지 넣으면 {min(rng.loc['①', 'min'], r120.loc['①', 'min']) * 100:.1f}~{rng.loc['①', 'max'] * 100:.1f}%입니다(2025~26년 급등을 뺀 2024년까지 표본에서 가장 높음).
- 다른 조합(기준 칸): 국내 60·채권 40 {base['②'] * 100:.2f}%, 미국주식 원화 {base['③'] * 100:.2f}%, 국내 33·해외 67 {base['④'] * 100:.2f}%, TDF 2055 평균 글라이드 {base['⑤'] * 100:.2f}%(0/10,000, 다시 뽑기 오차 상한 약 0.03%).
- **조합 사이 차이는 가려낼 수 없었습니다.** 겹치지 않는 30년 기간이 {int(i1.안겹친창)}개뿐이라(실효 독립 단위 {i1.실효독립단위:.0f}), ③−①·④−①을 가려내려면 손실 비율 차이가 약 0.52·0.49는 되어야 했습니다(국내주식만의 비율 자체보다 큼).
- **하락 국면 11번(20% 이상 하락 7번) 모두 원화 미국주식이 국내주식보다 덜 빠졌지만, 11번 중 {int((c["us"] <= 0).sum())}번은 미국주식도 원화로 손실이었습니다.** 원화 미국주식 평균 {c["us"].mean() * 100:+.1f}%는 1994~98년 국면(외환위기, +{c[c.고점 == '1994-10'].us.iloc[0] * 100:.0f}%) 하나가 끌어올린 것이고, 그 국면을 빼면 {m97 * 100:+.1f}%입니다.
""",
        말하면_안_되는_것="""
- "30년이면 주식은 안전하다/위험하다", "장기라 안전" — 실효 독립 단위가 1이라 이 자료로는 말할 수 없습니다.
- "약 13% 손해" — 손실 크기가 아니라 '원금보다 적은 경로의 비율'이고, 확률이 아니라 다시 뽑은 경로 중 비율입니다.
- "해외주식 쿠션이 하락장마다 작동했다", "하락장 평균 +30%" — 1997년 한 번이 평균을 좌우했고, 5번은 미국주식도 손실이었습니다.
- "환헤지가 유리하다" — 헤지는 금리차로 근사한 값입니다. "22개국 자료"라고 쓰지 않습니다(French 21개국+미국).
""",
        한계="""
- 겹치지 않는 30년 기간이 사실상 1개라 조합 사이 차이를 통계로 가려낼 수 없습니다(기술만).
- 국내주식은 KOSPI200+배당(2011년 이전 배당은 배당수익률로 근사), 미국주식은 S&P500을 원화로 환산했습니다. 환헤지는 CD91 − 미국 T-bill 금리차 근사입니다.
- 가장 가까운 해외 연구 Anarkulova·Cederburg·O'Doherty(2022, 저자 최종원고)는 선진국 39개국을 나라별 자국 통화 실질 기준으로 봤고 한국 1996~2019도 포함합니다. 같은 저자들의 2022년 11월 논문은 자국 통화 기준 해외주식도 다룹니다. 이 정리의 차별점은 '원화 저축자의 환노출 해외주식 조합'에 한정되며, 정의·표본이 달라 ACO 숫자와 직접 비교하지 않습니다.
- 하락 국면 20% 이상 표시는 코스피 종합 기준이고 막대는 KOSPI200이라 2011년 국면처럼 어긋나는 곳이 있습니다.
""")
    return dict(base=base, rng=rng, r120=r120, c=c, m97=m97)


NOTE = ("본문의 'T2'·'T3'·'pilot7~10'·'C_multi'·'10월 19일 C·F'·'DOC_AUDIT'·'감사 H1·H2·H3·R1-H1' 같은 이름은 원 연구 저장소의 분석·감사 이름입니다(이 저장소에 없음). "
        "'감사'는 원 연구에서 결과를 낸 뒤 독립 감사자가 한 점검이고, '결과 뒤'라고 적은 규칙·구분은 결과를 본 뒤 추가한 것입니다. 판정 규칙의 원문은 설계서(계산 전 기록)입니다.")
RUN = (f"실행: 저장소 루트에서 `python {SCRIPT} {{k}}`{{extra}}.")
NEED = " — 원자료와 원 연구 결과 파일(위 '입력')이 `$PENSION_DATA_ROOT` 아래 원 연구와 같은 경로에 있어야 돕니다(`../DATA_SOURCES.md`). 이 저장소만으로는 돌지 않습니다"
TAIL = {
    D8: f"""
## 그림

![계좌 안 피신](figures/fig_T6_계좌안피신.png)

## 파일

- `figures/`: 그림(`.png`·`.svg`), 그림 숫자(`_data.csv`: 9개국 판정 요약, 한국 사건별 값, 자금흐름 12개월), 읽은 파일 sha256(`_source.txt`).
- `results/`: `T6_shelter_events.csv`(사건·복귀 규칙·안전자산별 R = 피신 ÷ 보유, 신호월, 피신 개월, 그 기간 주식·안전자산 누적 수익), `T6_shelter_summary.csv`(4칸 판정, 묶음 부트스트랩 구간, 수령세 민감도), `T6_flow_vs_nonbear.csv`(순설정 ÷ 순자산 비율과 비교 창 분위수). 모두 이 주제가 계산한 요약 값이고 월 수익률·지수·기준가·순설정 원값은 없습니다.
- `docs/설계서_포트폴리오_주제B_20261108.md`: 08~11 판정 규칙(원 연구 커밋 6ef8992에 계산 전 커밋된 원문 그대로).
- 코드: `notebooks/portfolio/make_topics_b.py`(08~11 공용, 계산·그림·README). 하락장 날짜 규칙은 `../01_downturn_timing/notebooks/pilot9/_build_C_real_inputs.py`의 `dd_detail`, 한국 표본은 `../src/pension_lab/pilot7.py`의 `samples()`.
- 입력(이 저장소에 없음): French 국가별 주식(`fetch/pilot9_global_equity.py`), OECD 3개월 금리·Swinkels 10년 국채(`processed/multicountry_returns_20261017.csv`), 원 연구의 C_multi 사건표(`results/pilot9_20261013/C_multi_20261017/events_monthly.csv`, 재현 확인용), 국내 DataGuide 자료(KOSPI200 TR·국고채 TR·CD91), 금융투자협회 연금 펀드 순설정 묶음(`results/pilot10_20261017/T3_flow/`). 출처와 받는 법은 `../DATA_SOURCES.md`.
- RUN1

NOTE

---
**English summary.** In a bear market, instead of cashing out a Korean pension account (16.5% tax), a saver could switch to a money-market or bond fund inside the account and return after a recovery signal. Across 63 confirmed bear markets in nine developed countries (local currency), returning only after the index regained its previous peak left the median saver with 0.80–0.87 times what holding would have given (90% cluster-bootstrap intervals below 1); returning after a 20% rebound from the low gave 0.90–0.94 times, not distinguishable from holding. Whether switching costs more than the cash-out tax depends on how later pension-income tax is treated: a sensitivity added after seeing the results changes some verdicts. Korean events since 1991 are reported one by one. Fund-flow data cannot separate new contributions from switches. Not investment advice.
""".replace("RUN1", RUN.format(k="t6", extra=NEED)),
    D9: f"""
## 그림

![글라이드패스 변경](figures/fig_T9_글라이드변경.png)

## 파일

- `figures/`: 그림(`.png`·`.svg`), 그림 숫자(`_data.csv`: 운용사 요약과 변경 9번 날짜), 읽은 파일 sha256(`_source.txt`). 왼쪽 판본 점은 투자설명서 공시일이고, 공시 위험자산 비중 값은 그림·표 어디에도 넣지 않았습니다.
- `results/`: `T9_cf_by_fund.csv`(펀드별 첫 판·계산 기간·쓰인 판 수·판독 방법 변경·d·월 10만 원 금액 차이·판정·원인 구분). 원 연구의 평균 위험비중 2열과 펀드·월별 비중표(`T9_cf_weights_monthly.csv`)는 공시 글라이드 값이라 넣지 않았습니다.
- 판정 규칙: `../{D8}/docs/설계서_포트폴리오_주제B_20261108.md` 9번.
- 코드: `../{D8}/notebooks/portfolio/make_topics_b.py`(08~11 공용).
- 입력(이 저장소에 없음): 공시 글라이드 판본표(`raw/fund_tdf/glidepath_disclosed_hist_20261012fix.csv`, 금융투자협회 전자공시 투자설명서에서 읽음), 원 연구 T3 결과(`results/simpletest_20261027/T3/full_r1_20261027_0433/`의 변경 사건·판독 잡음 바닥선), 시장 경로(`results/pilot9_20261013/C_real_20261017/inputs/C2_components_monthly.csv`, DataGuide 가공), 하락 국면(`results/pilot10_20261017/I2x_hist/results_lt2020/lt2020_events.csv`). 출처는 `../DATA_SOURCES.md`.
- RUN1

NOTE

---
**English summary.** Korean target-date funds have revised the glide paths disclosed in their prospectuses. Comparing, on the same realized market path with equal monthly contributions, the plan first disclosed with the plan actually in force, the difference exceeded a chart-reading error floor for 17 of 33 comparable funds (the largest about −12% in log terms over 115 months); 12 of the 33 had only four months to compare. For 7 of the 17 the difference appeared only after the way the prospectus chart was read changed, so plan changes and reading method cannot be separated there. Seven of nine plan changes fell inside downturn phases identified after the fact, but they cluster in two phases and the count is too small to test. Not investment advice.
""".replace("RUN1", RUN.format(k="t9", extra=NEED)),
    D10: f"""
## 그림

![TDF 재매수](figures/fig_T10_TDF재매수.png)

## 파일

- `figures/`: 그림(`.png`·`.svg`), 그림 숫자(`_data.csv`: 분기 중앙값과 판정 개수), 읽은 파일 sha256(`_source.txt`).
- `results/`: `T10_gap_by_report.csv`(보고서별 '실제 − 목표' 격차의 점·하한·상한과 점이 경계 밖인지), `T10_change_after_trough.csv`(펀드별 저점 직전 수준과 1·2·4번째 뒤 보고서 변화, 설계서 판정과 결과 뒤 보류 규칙 판정), `T10_pilot8_mismatch.csv`(원 연구 두 계산의 값 차이). 보유내역 원행·비중 값·공시 목표 값은 넣지 않았고 격차만 넣었습니다(비중과 격차를 함께 두면 공시 글라이드 값이 되살아나므로).
- 판정 규칙: `../{D8}/docs/설계서_포트폴리오_주제B_20261108.md` 10번.
- 코드: `../{D8}/notebooks/portfolio/make_topics_b.py`(08~11 공용). 자산운용보고서 받는 코드는 `../src/pension_lab/fetch/mgmt_report_tdf.py`.
- 입력(이 저장소에 없음): 원 연구가 보유내역에서 만든 보고서별 위험자산 비중(`results/pilot10_20261017/T1_rebuy/T1c_calib_points.csv`, 대조용 `results/pilot8_20261010/T1d_desc/t1d_rows.csv`)과 보고서 날짜의 공시 목표(`results/pilot8_20261010/T1_reduced/t1r_glide_at_reports.csv`). 출처는 `../DATA_SOURCES.md`.
- RUN1

NOTE

---
**English summary.** Did Korean target-date funds buy equities back toward their glide-path targets after the 2022 bear-market low? Quarterly holdings reports (three managers, 19 funds, 349 reports) list only the largest holdings, so the risky-asset share can only be bounded. The bound on the change is about 30 percentage points wide (median), and none of the 19 funds showed a direction one or four quarters after the low; two quarters after, 3 directional calls were held back because the point estimate lay outside its own bounds. This reflects the limits of the measurement more than fund behaviour. Not investment advice.
""".replace("RUN1", RUN.format(k="t10", extra=NEED)),
    D11: f"""
## 그림

![원화 30년](figures/fig_T12_원화30년.png)

## 파일

- `figures/`: 그림(`.png`·`.svg`), 그림 숫자(`_data.csv`), 읽은 파일 sha256(`_source.txt`).
- `results/simpletest_T2/`: 원 연구 T2의 동결 결과 중 이 그림·요약이 읽는 것 — `T2_boot_cells.csv`(표본·블록·조합별 30년 손실 경로 비율 등 1만 경로 요약), `T2_cushion_phases.csv`(하락 국면별 국내주식·원화 미국주식 누적 수익), `T2_independent_units.csv`(겹치지 않는 30년 창·실효 독립 단위), `T2_mde.csv`(구별 가능 최소 차이), `SAY_OK_T2.txt`(원 연구 감사 뒤 쓸 수 있는 문장 범위).
- 코드: `../{D8}/notebooks/portfolio/make_topics_b.py`(그림·README), `notebooks/simpletest/`(원 계산: `_gen_T2.py`가 `T2_30년주식안전성.py`를 노트북으로 만들어 실행, 공통 함수 `_t2_core.py`). 원 계산은 원 연구 폴더 구조와 DataGuide 원자료가 필요해 그대로는 돌지 않습니다(`../DATA_SOURCES.md`).
- RUN1

NOTE

---
**English summary.** Is "stocks are safe over 30 years" true for a saver who earns and retires in Korean won? Resampling Korean monthly data (1991–2026) into 10,000 thirty-year contribution paths, about 13% of paths holding only Korean equities ended below inflation-adjusted contributions (10.2–26.5% across samples and block lengths); mixes with unhedged foreign equities were at 0–0.6%. With only one non-overlapping 30-year period, differences between mixes cannot be distinguished statistically. In all 11 Korean downturns since 1991, US equities in won fell less than Korean equities, but in 5 of them they also lost money in won. Not investment advice.
""".replace("RUN1", RUN.format(k="t12", extra=" — 저장소 `results/simpletest_T2/`만 읽어 원자료 없이 됩니다")),
}
TAIL = {k: v.replace("NOTE", NOTE) for k, v in TAIL.items()}


if __name__ == "__main__":
    pd.set_option("display.width", 240); pd.set_option("display.max_columns", 30)
    which = sys.argv[1:] or (["t6", "t9", "t10"] if DATA else []) + ["t12"]
    for k in which:
        print("=====", k); print(globals()[k]())
