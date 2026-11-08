"""간단 테스트 T2 생성기 — 명세 docs/ideas/본연구후보_20261027/간단테스트_명세_T2_20261027.md(d025dfb) + 정정 r1(17e7507·089553d).
단계(명세 5절: MDE가 결과보다 먼저):
  python notebooks/simpletest/_gen_T2.py pre   → 0단계: 입력 sha256·월 패널 CSV·창 수·PW 원값·글라이드 그림·자체 점검(결과변수 없음)
  python notebooks/simpletest/_gen_T2.py mde   → 1단계: T2_mde.csv (역사 재표본 SD만 — 평균·점추정은 저장·출력 안 함)
  python notebooks/simpletest/_gen_T2.py nb    → 2~4단계: T2_30년주식안전성.py(# %% 셀) → 실행된 .ipynb + run_meta.txt
실행: (cmd) set "PYTHONPATH=" 뒤 set PYTHONIOENCODING=utf-8 & python notebooks\\simpletest\\_gen_T2.py pre
"""
from __future__ import annotations
import datetime, hashlib, json, os, platform, re, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
os.environ["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(HERE)])
sys.path[:0] = [str(ROOT / "src"), str(HERE)]
import numpy as np, pandas as pd
from scipy.stats import norm
import _t2_core as C
from pension_lab import pilot7 as P, paths, runrecord as rr

OUT = C.OUT; META = OUT / "nb_meta"
B_OUT, N_IN = 1000, 2000                     # T2-D19 A(정정 r1: 항상 1,000) / 안쪽 2,000경로(명세 5절, 정정 r1 4(a))
Z80, Z90 = norm.ppf(.975) + norm.ppf(.80), norm.ppf(.975) + norm.ppf(.90)   # 2.80 / 3.24 (Bloom 1995 Table 1)
COMPS = [("③−①", "③", "①"), ("④−①", "④", "①"), ("⑤−②", "⑤", "②"), ("④−⑤", "④", "⑤")]


def log(msg):
    META.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')}\t{msg}"
    print(line, flush=True)
    with open(META / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def input_files() -> list[Path]:
    E, B, M, D = paths.EQUITY_KR, paths.BOND_KR, paths.MACRO, paths.DATAGUIDE
    G = paths.EQUITY_GLOBAL
    fs = [E / "idx_kospi200.csv", E / "idx_kospi200_fundamental.csv", D / "dg_econ_divyield_rates_19900101.csv", D / "dg_kospi_k200_tr_daily_19800104.csv",
          D / "bond_tr_index.xlsx", B / "ecos_nhb5y_monthly_1987.csv", B / "ecos_ktb3y_monthly_1995.csv", B / "ecos_ktb3y_long.csv",
          B / "ecos_shortrate_monthly_1989_1996.csv", B / "ecos_cd91_long.csv", M / "ecos_cpi_long.csv", M / "ecos_usdkrw_long.csv",
          G / "sp500_price_yf_1965.csv", G / "sp500_fdr.csv", G / "sp500tr_yf_1988.csv", G / "shiller_ie_data_20260928.xls", G / "global_us_spy_tr.csv",
          paths.BOND_GLOBAL / "global_ustreasury_mid_ief.csv", M / "fred_dtb3.csv", M / "fred_cpiaucsl.csv", G / "french" / "F-F_Research_Data_Factors.csv",
          C.FRDEV_F, C.FX64_F, C.MC_F, C.GLIDE_F, C.PHASE_F, M / "oecd_sdmx_cpi_raw_20261009.csv", M / "bis_long_cpi_monthly_20261009.csv"]
    fs += sorted((G / "french_intl").glob("*.Dat")) + sorted(M.glob("fred_oecd_*.csv")) + sorted(C.RAWN.glob("*"))
    return fs


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def kr_samples(k):
    return {"KR1991": k, "KR1996": k.loc["1996-01":], "KR~2024": k.loc[:P.PRE]}


def stage_pre():
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    lines = [f"{sha(f)}  {f}" for f in input_files()]
    k = C.kr_panel(); k8 = C.kr1980_panel(); us = C.us_panel(); uk = C.us_krw_panel()
    kr = k.join(k8.add_prefix("k80_"), how="outer"); kr.index.name = "date"
    usx = us.join(uk.add_prefix("krw_"), how="outer"); usx.index.name = "date"
    kr.to_csv(OUT / "T2_inputs_monthly_KR.csv", encoding="utf-8-sig"); usx.to_csv(OUT / "T2_inputs_monthly_US.csv", encoding="utf-8-sig")
    lines += [f"{sha(OUT / f)}  {OUT / f}  (생성 월 패널)" for f in ("T2_inputs_monthly_KR.csv", "T2_inputs_monthly_US.csv")]
    (OUT / "T2_inputs_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # 창 수(결과 무관)
    fr = P.french_panel(); ol = P.oecd_local_panel(); sw = C.swinkels_oecd_panel(ol)
    rows = []
    sam = kr_samples(k) | {"KR1980(주식판)": k8, "US1965(달러)": us, "US원화 D12-A(1965-02~)": uk, "US원화 D12-B(1980-03~)": uk.loc["1980-03":]}
    for nm, d in sam.items():
        Tn = len(d); rows.append(dict(묶음="단일", 표본=nm, 시작=d.index[0].strftime("%Y-%m"), 끝=d.index[-1].strftime("%Y-%m"), 개월=Tn,
                                     겹치는창=max(Tn - C.T + 1, 0), 안겹친창=Tn // C.T, h_over_T=round(C.T / Tn, 3)))
    for grp, pan in (("French 달러(21개국+미국)", fr), ("OECD 현지 17개국", ol), ("OECD 현지 + Swinkels 국채(D13-B)", sw)):
        for nm, d in sorted(pan.items()):
            Tn = len(d); rows.append(dict(묶음=grp, 표본=nm, 시작=d.index[0].strftime("%Y-%m"), 끝=d.index[-1].strftime("%Y-%m"), 개월=Tn,
                                         겹치는창=max(Tn - C.T + 1, 0), 안겹친창=Tn // C.T, h_over_T=round(C.T / Tn, 3)))
    wc = pd.DataFrame(rows); wc.to_csv(OUT / "T2_window_counts.csv", index=False, encoding="utf-8-sig")
    # PW 원값(전체 표본, 결과변수 아님 — 블록 설계 입력. 명세 3-6: 자료를 보고 정한 설계라 원값 기록)
    pw = []
    for nm, d in (kr_samples(k) | {"KR1980(주식판)": k8}).items():
        for c in [c for c in ("eq", "bd", "us", "dev", "usHA") if c in d]:
            pw.append(dict(표본=nm, 계열=c, PW=P.pw_block(d[c])))
    for c in ("eq", "bd"):
        pw.append(dict(표본="US1965(달러)", 계열=c, PW=P.pw_block(us[c])))
    for nm, d in {"US원화 D12-A": uk, "US원화 D12-B": uk.loc["1980-03":]}.items():
        pw.append(dict(표본=nm, 계열="us", PW=P.pw_block(d["us"])))
    pd.DataFrame(pw).to_csv(OUT / "T2_pw_blocks.csv", index=False, encoding="utf-8-sig")
    # 글라이드 그림(입력)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
    g = pd.read_csv(C.GLIDE_F).set_index("years_rel_target")
    fig, ax = plt.subplots(figsize=(7, 4))
    for m in ("KB", "미래에셋", "삼성", "신한", "한국투자"):
        ax.plot(g.index, g[m], lw=1, alpha=.6, label=m)
    ax.plot(g.index, g["mean5"], "k", lw=2.2, label="mean5(입력)"); ax.step(-30 + np.arange(30), g["mean5"].loc[-30:-1], "r--", where="post", lw=1, label="D10-A 연 계단")
    ax.set(xlabel="목표연도까지 남은 해(음수)", ylabel="위험자산 비중 %", title="입력: 5대 운용사 2055 공시 글라이드 mean5"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "T2_fig_glide.png", dpi=130); plt.close(fig)
    g.to_csv(OUT / "T2_fig_glide_data.csv", encoding="utf-8-sig")
    selfcheck(k)
    log(f"pre 끝 {time.time() - t0:.0f}s, 입력 {len(lines)}개")


def selfcheck(k):
    """10절 자체 점검(합성 자료) + T4 세후(D5-B) 한 칸 재현 + us 재구성(kr_panel 안 assert)."""
    rows = []
    z = np.zeros((5, C.T))
    rows.append(("수익 0 → 실질 금액 = 실질 납입(D5-A, D6 A·B)", bool(np.allclose(C.ratio(z, z, z, "A", "A"), 1) and np.allclose(C.ratio(z, z, z, "A", "B"), 1))))
    r = subprocess.run([sys.executable, "-m", "pension_lab.pilot7"], capture_output=True, text=True, env=os.environ | {"PYTHONIOENCODING": "utf-8"})
    rows.append(("pilot7 self-check(블록 무한대 풀 경로가 조각을 따라감 포함)", "self-check ok" in r.stdout))
    ix = C.boot_idx(50, 100, 1e9, 1, fast=True)
    rows.append(("단일 조각 pooled_paths 블록 무한대 = 원형 연속(MDE 단계 벡터화판)", bool(((np.diff(ix, axis=1) % 50) == 1).all())))
    hA = (1 + k["us_usd"]) * (1 + (k["cash"] * 1200 - k["us_cash"] * 1200) / 1200) - 1        # 명세 2-1: (1+us_usd)(1+(i_KR−i_US)/1200)−1, 금리 % 단위
    rows.append(("헤지식 단위(% 금리 → /1200)·kr_panel usHA 일치", bool(np.allclose(hA, k["usHA"], atol=1e-14)) and 0 < k["cash"].mean() * 1200 < 20))
    a = np.arange(10.0); rows.append(("원형 이동 0 오프셋 = 원값", bool(np.array_equal(np.roll(a, 0), a))))
    rows.append(("글라이드 연 계단 길이 360·평균 63.54%", len(C.glide("A")) == 360 and abs(C.glide("A").mean() - 0.6354) < 5e-5))
    rows.append(("us = (1+us_usd)(1+fx)−1 재구성이 monthly_kr_long us와 1e-12 일치", True))      # kr_panel()이 assert로 확인(실패 시 여기 못 옴)
    # T4 D5-B 재현: KR 1991~ 주식100 블록 12 → T4_level.csv 'A: P(실질자산<실질납입)'
    t4 = pd.read_csv(P.OUT / "T4_level.csv")
    want = float(t4[(t4["포트폴리오"] == "주식100") & (t4["표본"] == "KR 1991~") & (t4["평균블록"] == 12.0)]["A: P(실질자산<실질납입)"].iloc[0])
    KL0 = P.monthly_kr_long(); KPX = P.kospi200_px()
    from pension_lab.bootstrap import paired_resample_paths
    M, PX, Cr, I = paired_resample_paths([P.mix_ret(KL0, 1.0), KPX.reindex(KL0.index), KL0["cash"], KL0["infl"]], P.NP, 360, 12.0, P.SEED)
    defl = np.cumprod(1 + I, axis=1); creal = (1 / np.c_[np.ones(P.NP), defl[:, :-1]]).sum(1) + C.E
    got = float((C.sim_after_tax(M, Cr, np.ones_like(M)) / defl[:, -1] < creal).mean())
    rows.append((f"T4 세후 재현(KR 1991~ 주식100 블록12): T4_level {want:.6f} vs 재계산 {got:.6f}", abs(got - want) < 1e-12))
    sc = pd.DataFrame(rows, columns=["점검", "통과"]); META.mkdir(parents=True, exist_ok=True)
    sc.to_csv(META / "selfcheck.csv", index=False, encoding="utf-8-sig")
    print(sc.to_string()); assert sc["통과"].all(), "자체 점검 실패"


def stage_mde():
    """5절 (a) 역사 재표본 SE: 주 표본 KR1991, 블록 4, B_out 1,000 × 안쪽 2,000경로, 추천안 변형, D5-A·D6-A.
    저장 = SD와 그 MC 오차만(평균·점추정 저장·출력 금지). 바깥 시드 SEED+10_000+b, 안쪽 시드 SEED+10_000+B_OUT+b(명세에 없음 → 이탈 목록)."""
    t0 = time.time(); k = C.kr_panel(); arr, cols = C.arr_cols(k)
    pw = float(pd.read_csv(OUT / "T2_pw_blocks.csv").query("표본=='KR1991' and 계열=='eq'")["PW"].iloc[0])
    V = {v["port"]: v for v in C.variants_kr() if C.is_rec(v) and v["port"] in ("①", "②", "③", "③H", "④", "④H", "⑤")}
    rows = []
    for blk, src in ((pw, "PW(KR1991 eq)"), (12.0, "12"), (1.0, "iid"), (120.0, "120")):
        st = {}
        for b in range(B_OUT):
            h = C.boot_idx(len(k), 1, blk, C.SEED + 10_000 + b, fast=True, length=len(k))[0]   # 가짜 역사(같은 블록 규칙)
            fake = arr[h]; idx = C.boot_idx(len(k), N_IN, blk, C.SEED + 10_000 + B_OUT + b, fast=True)
            res = {p: C.summ(C.run_variant(fake, cols, idx, v, "A", "A")[("A", "A")]) for p, v in V.items()}
            for p, s in res.items():
                for m in ("p", "P5", "P50"):
                    st.setdefault(("수준", p, m), []).append(s[m])
                st.setdefault(("수준MCvar", p, "p"), []).append(s["p"] * (1 - s["p"]) / N_IN)
            for nm, a, c in COMPS:
                for m in ("p", "P5"):
                    st.setdefault(("차이", nm, m), []).append(res[a][m] - res[c][m])
                st.setdefault(("차이MCvar", nm, "p"), []).append(res[a]["p"] * (1 - res[a]["p"]) / N_IN + res[c]["p"] * (1 - res[c]["p"]) / N_IN)
            if b % 100 == 99:
                log(f"mde 블록 {src} {b + 1}/{B_OUT} ({time.time() - t0:.0f}s)")
        for (kind, nm, m), x in st.items():
            if "MCvar" in kind:
                continue
            sd = float(np.std(x, ddof=1))
            mcv = st.get((kind + "MCvar", nm, m))
            mc = float(np.sqrt(np.mean(mcv))) if mcv else np.nan                       # 정정 r1 4(a): SE_hist의 MC 오차
            sdc = float(np.sqrt(max(sd ** 2 - mc ** 2, 0))) if mcv else np.nan
            rows.append(dict(표본="KR1991", 블록=blk, 블록출처=src, 종류=kind, 대상=nm, 지표=m, B_out=B_OUT, 안쪽경로=N_IN, SD_hist=sd,
                             MC오차_안쪽=mc, SD_MC보정=sdc, MDE80=Z80 * sd, MDE90=Z90 * sd, MDE80_MC보정=Z80 * sdc if mcv else np.nan))
        st.clear()
    d = pd.DataFrame(rows); d.to_csv(OUT / "T2_mde.csv", index=False, encoding="utf-8-sig")
    log(f"mde 끝 {time.time() - t0:.0f}s sha256={sha(OUT / 'T2_mde.csv')} (평균·점추정 미저장)")


def stage_nb():
    nbp = HERE / "T2_30년주식안전성.ipynb"
    t0 = datetime.datetime.now(); log("nb 시작")
    build_nb(HERE / "T2_30년주식안전성.py", nbp, 6 * 3600); t1 = datetime.datetime.now()
    log(f"nb 끝 {nbp.stat().st_size / 1e6:.2f}MB")
    import scipy, statsmodels, arch, matplotlib
    extra = (f"python={platform.python_version()}\nnumpy={np.__version__}\npandas={pd.__version__}\nscipy={scipy.__version__}\nstatsmodels={statsmodels.__version__}\n"
             f"arch={arch.__version__}\nmatplotlib={matplotlib.__version__}\nos={platform.platform()}\nseed={C.SEED} (D4-B {C.SEED + 1}, MDE 바깥 SEED+10000+b, 안쪽 SEED+10000+{B_OUT}+b)\n"
             f"paths={C.NP} (D4-B 100000)\nB_out={B_OUT}\ninner={N_IN}\nnb_start={t0.isoformat(timespec='seconds')}\nnb_end={t1.isoformat(timespec='seconds')}\n"
             f"spec=d025dfb + 정정 r1 17e7507·089553d\nspec_commit_check={rr.git('log', '-1', '--format=%H', '--', 'docs/ideas/본연구후보_20261027/간단테스트_명세_T2_20261027.md')}\n"
             f"mde_sha256={sha(OUT / 'T2_mde.csv')}\nnotebook_sha256_lf={rr.lf_sha256(nbp)}\n"
             f"decisions=T2-D1~D21 전 후보(D14·D15 A만=명세 추천, D19 1000만=정정 r1)\n")
    rr.write_run_meta(META, Path(__file__), deps=["src/pension_lab/pilot7.py", "src/pension_lab/bootstrap.py", "src/pension_lab/io.py", "src/pension_lab/paths.py",
                                                  "notebooks/simpletest/_t2_core.py", "notebooks/simpletest/T2_30년주식안전성.py"], extra=extra)


DECISIONS = {"T2-D1": ["12", "240", "iid"], "T2-D2": ["12", "iid", "120"], "T2-D3": ["KR1996", "KR~2024", "D"], "T2-D4": ["B"], "T2-D5": ["B", "C"], "T2-D6": ["B"],
             "T2-D7": ["B"], "T2-D8": ["B"], "T2-D9": ["B", "C"], "T2-D10": ["B"], "T2-D11": ["B"], "T2-D12": ["B"], "T2-D13": ["B"], "T2-D14": ["—"], "T2-D15": ["—"],
             "T2-D16": ["—"], "T2-D17": ["B"], "T2-D18": ["—"], "T2-D19": ["—"], "T2-D20": ["B"], "T2-D21": ["B"]}   # 명세 7절 + 정정 r1(추천 A 대비 다른 후보)


CONSTS = [  # (상수, 값, 쓰는 곳, 출처 또는 ⬜)
    ("SEED", C.SEED, "주 부트스트랩", "명세 10절"), ("SEED+1", C.SEED + 1, "D4-B", "명세 10절"), ("SEED+10000+b", "—", "MDE 바깥", "명세 10절"),
    ("SEED+10000+1000+b", "—", "MDE 안쪽", "⬜ 명세에 없음(이탈 목록)"), ("SEED+2", C.SEED + 2, "재현 점검(다른 시드)", "조정자 사전점검 7(재현용, 결과 아님)"),
    ("NP", C.NP, "경로 수", "T2-D4 A"), ("100000", 100_000, "경로 수", "T2-D4 B"), ("T", C.T, "30년×12", "회원 지정(30세·30년)"),
    ("B_OUT", B_OUT, "MDE 바깥", "T2-D19 A·정정 r1 4(d)"), ("N_IN", N_IN, "MDE 안쪽", "명세 5절(a)·정정 r1 4(a) 유지"),
    ("Z80", round(Z80, 4), "MDE", "Bloom 1995 Table 1 p.550(2.80)"), ("Z90", round(Z90, 4), "MDE", "T2-D21 B(3.24)"), ("1.96", 1.96, "0 근처", "정정 r1 4(c)"),
    ("블록 1·12·120", "1·12·120", "단일국", "T2-D2 A·B·C"), ("PW", "자동", "단일국 주 블록", "T2-D2 D·정정 r1 4(e)"),
    ("블록 120·12·240·1", "—", "다국가", "T2-D1"), ("W60", C.W60, "②", "회원 지정"), ("W33", str(C.W33), "④·⑤ S(D9-A)", "회원 지정(ACO 2025)"),
    ("S35", str(C.S35), "⑤ S(D9-C)", "T2-D9 C·가정_전수조사 #4(P.EQ_KR_SHARE)"), ("glide mean5", "파일", "⑤", "명세 2-4(C2_glide, sha 9f968ca5…)"),
    ("63.54%", round(C.glide("A").mean(), 6), "P3 사전 상수", "명세 6절(mean5 −30~−1 평균)"),
    ("US_ETF_TER", C.US_ETF_TER, "D17-B", "근거 대장 C 44행(TIGER미국S&P500 0.0068%, 1차) — KODEX 0.0062%보다 큰 값 선택 ⬜(이탈 목록)"),
    ("FEE_PENSION", P.FEE_PENSION, "매매비용", "근거 대장 C(pilot7)"), ("eq 보수 0.15%", 0.0015, "KR eq", "근거 대장 C(monthly_kr_long)"), ("BD_TER", P.BD_TER, "KR bd", "근거 대장 C"),
    ("CAP·LIM·E", f"{C.CAP:.4f}·{C.LIM:.4f}·{C.E:.4f}", "D5-B", "T4 정의(근거 대장 A·B: 공제한도 600만·납입한도 1,800만·연 342만)"),
    ("CREDIT_LOW·PENSION_UNDER70·TAX_FINANCIAL", f"{P.CREDIT_LOW}·{P.PENSION_UNDER70}·{P.TAX_FINANCIAL}", "D5-B", "근거 대장 A(소득세법 §59의3·§129)"),
    ("PRE", P.PRE, "KR~2024", "T2-D3 C(근거 대장 D2)"), ("1996-01", "1996-01", "KR1996", "T2-D3 B(ACO 2022 Table 1, M2 원문)"), ("1980-03", "1980-03", "D12-B 시작",
     "N2 한국은행(2016) PDF 137~138: 단일변동환율제도 1964.5~1980.2 사실상 고정, 1980.2 복수통화바스켓 → 다음 달 시작"),
    ("하락 20%", -0.20, "D16-B", "SEC '약세장'(근거 대장 D2)"), ("12·36개월", "12·36", "국면 뒤 창", "⬜ 기술용, 추천 아님(정정 r1 4(b))"),
    ("D20-B 199", 199, "원형 이동 무작위", "T2-D20 B(근거 문헌 없음)"), ("chunk 20000", 20000, "메모리 분할", "계산 편의(결과 무관)"),
    ("12개월 미만 조각 제외", 12, "다국가 조각", "pilot7 french_panel·oecd_local_panel 기존 규칙·정정 r1 #8")]


def coverage(SF: pd.DataFrame, out: Path, tag: str = ""):
    """(사전점검 1·보완 1) 결정표 dict → (결정, 후보, 주비교) 칸 자동 생성, 민감도 표 행 수를 셈. 0칸은 사유 없으면 assert."""
    # 1 격자 coverage
    comps = [c for c, _, _ in COMPS]; rows = []
    for d in [f"T2-D{i}" for i in range(1, 22)]:
        z = SF[SF["결정"] == d]; txt = z["맥락"].fillna("") + " " + z["기준1_상세"].fillna("")
        for c in comps:
            if d == "T2-D20":                                                  # 원형 이동 Δp_vs_① = ③−①(③·③H 변형)·④−①(④·④H 변형)
                n = int(z["맥락"].str.contains(rf"\s{c[0]}H?\|", regex=True).sum()) if c in ("③−①", "④−①") else 0
            else:
                n = int(txt.str.contains(c, regex=False).sum())
            rows.append(dict(결정=d, 주비교=c, 행수=n))
    cov = pd.DataFrame(rows)
    why = {"T2-D1": "다국가: ③·④ 없음(D14 A 미보고) → ⑤−②만", "T2-D12": "US 원화판은 ③만(명세 8절)", "T2-D13": "다국가: ⑤−②만", "T2-D14": "A(미보고)만",
           "T2-D15": "A만", "T2-D16": "국면표(손실확률 칸 아님)", "T2-D18": "요약 순서", "T2-D19": "정정 r1로 1,000만", "T2-D20": "원형 이동 위약은 ③·④ 계열(⑤ 없음)",
           ("T2-D3", "D"): "KR1980은 ①·③만(명세 2-2: 1980년대 채권 미검증) → ③−①만"}
    cov["0칸_사유"] = [why.get(r.결정, "") if r.행수 == 0 else "" for r in cov.itertuples()]
    cov.to_csv(out / f"T2_grid_coverage{tag}.csv", index=False, encoding="utf-8-sig")
    assert not ((cov["행수"] == 0) & (cov["0칸_사유"] == "")).any(), cov[(cov["행수"] == 0) & (cov["0칸_사유"] == "")]
    # (조정자 보완 1) 결정표 dict에서 (결정, 후보, 주비교) 셀을 자동 생성 → 민감도 표에 그 후보 행이 있는지 셈
    cc = []
    for d, cands in DECISIONS.items():
        z = SF[SF["결정"] == d]
        for cand in cands:
            zc = z[z["후보"].astype(str).str.startswith(cand)] if cand != "—" else z
            txt = zc["맥락"].fillna("") + " " + zc["기준1_상세"].fillna("")
            for c in comps:
                n = (int(zc["맥락"].str.contains(rf"\s{c[0]}H?\|", regex=True).sum()) if c in ("③−①", "④−①") else 0) if d == "T2-D20" else int(txt.str.contains(c, regex=False).sum())
                cc.append({"결정": d, "후보": cand, "주비교": c, "행수": n, "⚠칸수": int(zc["⚠"].astype(str).eq("True").sum()), "0칸_사유": why.get((d, cand), why.get(d, "")) if n == 0 else ""})
    cc = pd.DataFrame(cc); cc.to_csv(out / f"T2_grid_coverage_by_candidate{tag}.csv", index=False, encoding="utf-8-sig")
    assert not ((cc["행수"] == 0) & (cc["0칸_사유"] == "")).any(), cc[(cc["행수"] == 0) & (cc["0칸_사유"] == "")]
    return cov, cc


def stage_post():
    """조정자 사전점검 8항목 중 코드로 할 것: 격자 coverage·독립 단위·룩어헤드 assert·상수표·이전 숫자 재계산·다른 시드 재현. run_meta에 덧붙임."""
    k = C.kr_panel(); out = []
    # 3 룩어헤드 assert
    cdm = pd.concat([pd.read_csv(paths.BOND_KR / "ecos_shortrate_monthly_1989_1996.csv", parse_dates=["date"]).set_index("date")["cd91_monthly"].pipe(lambda s: s.set_axis(s.index + pd.offsets.MonthEnd(0))).loc[:"1994-05"],
                     P.dg_econ()["cd91_pct"].dropna().resample("ME").last().loc["1994-06":"1994-12"], C.io.asset_series("cd91").resample("ME").last().loc["1995-01":]])
    la = {"cash_t = CD91(t−1 월말)/1200": bool(np.allclose(k["cash"].iloc[1:], cdm.shift(1).reindex(k.index).iloc[1:] / 1200, atol=1e-15)),
          "us_cash_t = DTB3(t−1 월말)/1200": bool(np.allclose(k["us_cash"], pd.to_numeric(pd.read_csv(paths.MACRO / "fred_dtb3.csv", index_col=0, parse_dates=True)["DTB3"], errors="coerce").resample("ME").last().shift(1).reindex(k.index) / 1200))}
    rng = np.random.default_rng(1); X = rng.normal(0, .05, (3, C.T, 3)); v5 = [v for v in C.variants_kr() if v["port"] == "⑤" and C.is_rec(v)][0]
    for ann in (False, True):
        X2 = X.copy(); X2[:, 200:] += 0.3
        R1, R2 = C.port_R(X, v5["W"], ann), C.port_R(X2, v5["W"], ann)
        la[f"port_R 인과성(t≥200 바꿔도 t<200 수익 불변, annual={ann})"] = bool(np.allclose(R1[:, :200], R2[:, :200]))
    I = rng.normal(.002, .003, (2, C.T)); I2 = I.copy(); I2[:, 100] += .5
    Dp = lambda I: np.c_[np.ones(len(I)), np.cumprod(1 + I, axis=1)[:, :-1]]
    la["D6-B 납입 c_t는 전월까지 물가만(t=100 물가 바꿔도 c_≤100 불변)"] = bool(np.allclose(Dp(I)[:, :101], Dp(I2)[:, :101]))
    la["글라이드 w_t는 자료 무관(나이만)"] = bool(np.array_equal(v5["W"], [v for v in C.variants_kr() if v["port"] == "⑤" and C.is_rec(v)][0]["W"]))
    la["국면 저점·회복월은 사후 확정 → 국면표(기술용)에만 사용, 포트폴리오 비중엔 미사용"] = True
    assert all(la.values()), la
    # 1 격자 coverage
    cov, _ = coverage(pd.read_csv(OUT / "T2_sensitivity_flip.csv"), OUT)
    # 4 상수표
    pd.DataFrame(CONSTS, columns=["상수", "값", "쓰는 곳", "출처"]).to_csv(OUT / "T2_constants.csv", index=False, encoding="utf-8-sig")
    # 2 독립 단위
    wc = pd.read_csv(OUT / "T2_window_counts.csv"); ph = pd.read_csv(C.PHASE_F).query("market == 'KR'")
    iu = wc.assign(실효독립단위=np.where(wc["묶음"] == "단일", wc["안겹친창"], np.nan))
    iu = pd.concat([iu, pd.DataFrame([
        dict(묶음="다국가 French", 표본="안 겹친 창 합계", 안겹친창=int(wc[wc["묶음"].str.startswith("French")]["안겹친창"].sum()), 실효독립단위=1, 비고="같은 달력 구간 공유 → 1(정정 r1 #9)"),
        dict(묶음="다국가 OECD", 표본="안 겹친 창 합계", 안겹친창=int(wc[wc["묶음"] == "OECD 현지 17개국"]["안겹친창"].sum()), 실효독립단위=1, 비고="같은 달력 구간 공유 → 1"),
        dict(묶음="한국 하락 국면(1991~)", 표본="c1 PS", 안겹친창=np.nan, 실효독립단위=int((pd.to_datetime(ph["peak"]) >= "1991-04").sum()), 비고=f"20% 이상 {int(((pd.to_datetime(ph['peak']) >= '1991-04') & (ph['fall'] <= -.2)).sum())}"),
        dict(묶음="한국 하락 국면(1980~)", 표본="c1 PS", 안겹친창=np.nan, 실효독립단위=len(ph), 비고=f"20% 이상 {int((ph['fall'] <= -.2).sum())}")])])
    iu.to_csv(OUT / "T2_independent_units.csv", index=False, encoding="utf-8-sig")
    # 5 이전 숫자(T4_level) 원 CSV 재계산
    t4 = pd.read_csv(P.OUT / "T4_level.csv"); col = "A: P(실질자산<실질납입)"
    prev = []
    for pf in ("주식100", "60/40"):
        for s in ("KR 1991~", "US 1965~ (월말)"):
            x = t4[(t4["포트폴리오"] == pf) & (t4["표본"] == s)][col]
            prev.append(dict(출처="pilot7 T4_level.csv", 포트폴리오=pf, 표본=s, 최소=x.min(), 최대=x.max()))
    pd.DataFrame(prev).to_csv(OUT / "T2_prev_numbers_recheck.csv", index=False, encoding="utf-8-sig")
    # 7 다른 시드 재현: 주 표본·주 블록 추천안 Δp의 MDE 판정
    arr, cols = C.arr_cols(k); pwv = float(pd.read_csv(OUT / "T2_pw_blocks.csv").query("표본=='KR1991' and 계열=='eq'")["PW"].iloc[0])
    V = {v["port"]: v for v in C.variants_kr() if C.is_rec(v) and v["port"] in ("①", "②", "③", "④", "⑤")}
    mv = pd.read_csv(OUT / "T2_mde_vs_delta.csv"); rs = []
    for blk, src in ((pwv, "PW"), (12.0, "12"), (1.0, "iid")):
        idx = C.boot_idx(len(k), C.NP, blk, C.SEED + 2)
        p = {q: C.summ(C.run_variant(arr, cols, idx, v, "A", "A")[("A", "A")])["p"] for q, v in V.items()}
        for nm, a, b in COMPS:
            m = mv[(mv["비교"] == nm) & (mv["지표"] == "p") & mv["블록출처"].str.startswith(src if src != "PW" else "PW")].iloc[0]
            d2 = p[a] - p[b]
            rs.append(dict(블록=src, 비교=nm, 주시드_Δp=m["차이"], 시드2_Δp=d2, MDE80=m["MDE80"], 주시드_기술=m["기술80"], 시드2_기술="식별 안 됨" if abs(d2) < m["MDE80"] else "MDE80보다 큼"))
    # 요약 문장은 r2 단계(T2_판정r2 노트북, 규칙 함수 C.sentence)가 만든다 — 옛 T2_summary_sentences.csv는 ⚠ 미반영판(대체됨)
    rs = pd.DataFrame(rs); rs["같음"] = rs["주시드_기술"] == rs["시드2_기술"]; rs.to_csv(OUT / "T2_reseed_check.csv", index=False, encoding="utf-8-sig")
    with open(META / "run_meta.txt", "a", encoding="utf-8") as f:
        f.write("lookahead_asserts=" + json.dumps(la, ensure_ascii=False) + "\n")
        f.write(f"inputs_sha256_file={OUT / 'T2_inputs_sha256.txt'} sha256={sha(OUT / 'T2_inputs_sha256.txt')}\n")
        f.write(f"spec_commits=d025dfb(원 명세), 17e7507(정정 r1), 089553d(정정 r1 9번)\nreseed_check_same_all={bool(rs['같음'].all())}\npost_end={datetime.datetime.now().isoformat(timespec='seconds')}\n")
    print(json.dumps(la, ensure_ascii=False, indent=1)); print(cov.pivot_table(index="결정", columns="주비교", values="행수", sort=False)); print(rs.to_string())
    log("post 끝")


def build_nb(src: Path, nbp: Path, timeout: int):
    import nbformat as nbf
    from nbclient import NotebookClient
    parts = re.compile(r"^# %%( \[markdown\])?$", re.M).split(src.read_text(encoding="utf-8"))
    nb = nbf.v4.new_notebook()
    for md, body in zip(parts[1::2], parts[2::2]):
        nb.cells.append(nbf.v4.new_markdown_cell(re.sub(r"^# ?", "", body.strip(), flags=re.M)) if md else nbf.v4.new_code_cell(body.strip()))
    NotebookClient(nb, timeout=timeout, kernel_name="python3", resources={"metadata": {"path": str(HERE)}}).execute()
    nbf.write(nb, str(nbp))


def stage_r2():
    """조정자 r2 지시(a~h): 계산된 CSV만 읽어 판정 규칙 재적용, 출력은 OUT/r2_판정(기존 파일 안 지움). 시뮬레이션 재실행 없음."""
    R2 = OUT / "r2_판정"; t0 = datetime.datetime.now(); log("r2 시작")
    build_nb(HERE / "T2_판정r2.py", HERE / "T2_판정r2.ipynb", 1800)
    cov, cc = coverage(pd.read_csv(R2 / "T2_sensitivity_flip_r2.csv"), R2, "_r2"); (R2 / "nb_meta").mkdir(exist_ok=True)
    extra = "\n".join([f"stage=r2(판정 규칙만 재적용, 시뮬레이션 없음)", f"mde_sha256={sha(OUT / 'T2_mde.csv')}", f"nb_start={t0.isoformat(timespec='seconds')}",
                       f"notebook_sha256_lf={rr.lf_sha256(HERE / 'T2_판정r2.ipynb')}", "rules=_t2_core.mde_cross·sentence·n_eff·is_descriptive", ""])
    rr.write_run_meta(R2 / "nb_meta", Path(__file__), deps=["notebooks/simpletest/_t2_core.py", "notebooks/simpletest/T2_판정r2.py"], extra=extra)
    print(cov.pivot_table(index="결정", columns="주비교", values="행수", sort=False)); log("r2 끝")


INTENDED_NEW = {"기준2_MC안", "기준3_MDEΔp잣대", "기준3_MDEΔp잣대_상세", "기준3_단서", "판정", "순위기준만", "비고"}   # r3에서 새로 생긴 열(감사 H1·M2·M6·M7)


def regress_r2_r3(r2: Path, r3: Path) -> pd.DataFrame:
    """r2 대비 r3 칸별 회귀: 같은 이름 파일의 공통 칸을 비교. 의도한 변화 = M6('해당 없음'으로 바뀐 ⚠ 칸)·P4 열 이름(LOW)·새 열. 그 밖은 '의도 밖'."""
    rows = []
    pairs = [("T2_sensitivity_flip_r2.csv", "T2_sensitivity_flip_r3.csv")] + [(f.name, f.name) for f in sorted(r2.glob("T2_gen_*.csv"))] + \
            [("T2_definitional_zero_excluded.csv",) * 2, ("T2_grid_coverage_r2.csv", "T2_grid_coverage_r3.csv"), ("T2_grid_coverage_by_candidate_r2.csv", "T2_grid_coverage_by_candidate_r3.csv")]
    for a, b in pairs:
        A, B = pd.read_csv(r2 / a).astype(str), pd.read_csv(r3 / b).astype(str)
        if a == "T2_gen_placebo_P4.csv":
            B = B.rename(columns={"블록별 부호 엇갈림(120 제외, 분해·검정 아님)": "생성기⚠(120 제외)"})
            rows.append(dict(파일=b, 행="—", 열="생성기⚠(120 제외)", r2="열 이름", r3="블록별 부호 엇갈림(120 제외, 분해·검정 아님)", 구분="의도(LOW P4 분해 표기)"))
        assert len(A) == len(B), (a, len(A), len(B))
        for c in sorted(set(B.columns) - set(A.columns)):
            rows.append(dict(파일=b, 행="—", 열=c, r2="(없음)", r3="새 열", 구분="의도(새 열)" if c in INTENDED_NEW else "의도 밖(새 열)"))
        for c in A.columns:
            if c not in B.columns:
                rows.append(dict(파일=b, 행="—", 열=c, r2="열", r3="(없음)", 구분="의도 밖(열 사라짐)")); continue
            for i in np.flatnonzero((A[c] != B[c]).to_numpy()):
                intended = c in ("⚠", "⚠_원규칙") and B.get("판정", pd.Series([""] * len(B))).iloc[i].startswith("해당 없음")
                rows.append(dict(파일=b, 행=i, 열=c, r2=A[c].iloc[i], r3=B[c].iloc[i], 구분="의도(M6 해당 없음)" if intended else "의도 밖"))
    return pd.DataFrame(rows, columns=["파일", "행", "열", "r2", "r3", "구분"])


def stage_r3():
    """감사 r1 수정(H1~H3·M2~M7·M10·LOW): 판정 규칙만 다시, 출력은 새 폴더 OUT/r3_판정_HHMM. 시뮬레이션 없음. r2 대비 칸별 회귀 자동."""
    R3 = OUT / f"r3_판정_{datetime.datetime.now():%H%M}"; os.environ["T2_R3_DIR"] = str(R3); t0 = datetime.datetime.now(); log(f"r3 시작 {R3.name}")
    build_nb(HERE / "T2_판정r3.py", HERE / "T2_판정r3.ipynb", 1800)
    cov, cc = coverage(pd.read_csv(R3 / "T2_sensitivity_flip_r3.csv"), R3, "_r3"); (R3 / "nb_meta").mkdir(exist_ok=True)
    rg = regress_r2_r3(OUT / "r2_판정", R3); rg.to_csv(R3 / "T2_regress_r2_vs_r3.csv", index=False, encoding="utf-8-sig")
    note = (f"대체됨 안내 ({datetime.date.today()}): 이 폴더의 T2_summary_sentences.csv(⚠ 미반영 — warn=False 결함, OECD D13을 한국 행에 섞음)와 "
            f"T2_sensitivity_flip.csv(원 노트북 판)는 지우지 않고 남겨 둡니다. 현행 판정·문장은 {R3.name}\\T2_summary_sentences_r3.csv(문장_원규칙 1순위)와 "
            f"{R3.name}\\T2_sensitivity_flip_r3.csv입니다. r2_판정\\도 r3로 대체됨(감사 r1 H1·H2).\n")
    (OUT / "T2_대체됨_안내.txt").write_text(note, encoding="utf-8")
    extra = "\n".join([f"stage=r3(감사 r1 수정, 판정 규칙만, 시뮬레이션 없음)", f"mde_sha256={sha(OUT / 'T2_mde.csv')}", f"nb_start={t0.isoformat(timespec='seconds')}",
                       f"notebook_sha256_lf={rr.lf_sha256(HERE / 'T2_판정r3.ipynb')}", f"regress_unintended={int(rg['구분'].str.startswith('의도 밖').sum())}", ""])
    rr.write_run_meta(R3 / "nb_meta", Path(__file__), deps=["notebooks/simpletest/_t2_core.py", "notebooks/simpletest/T2_판정r3.py"], extra=extra)
    print(rg["구분"].value_counts()); print(rg[rg["구분"].str.startswith("의도 밖")].to_string()); log(f"r3 끝 {R3.name}")


R3B_TEXT = {"판정", "기준3_단서", "문장_원규칙", "문장_결과후규칙"}   # 재감사 N2·N3·문장 꼬리: 문장·설명 열


def regress_r3_r3b(a: Path, b: Path) -> pd.DataFrame:
    """r3 대비 r3b 칸별 회귀(같은 이름 CSV 전부). 의도 = 기준2_MC안(D2·D8)·새 열 기준2_MC안_비고·문장/설명 열. 그 밖은 '의도 밖'."""
    rows = []
    for f in sorted(a.glob("*.csv")):
        if f.name.startswith("T2_regress"): continue
        A, B = pd.read_csv(f).astype(str), pd.read_csv(b / f.name).astype(str)
        assert len(A) == len(B), (f.name, len(A), len(B))
        for c in sorted(set(B.columns) ^ set(A.columns)):
            rows.append(dict(파일=f.name, 행="—", 열=c, r3="(없음)" if c in B else "열", r3b="새 열" if c in B else "(없음)", 구분="의도(새 열)" if c == "기준2_MC안_비고" else "의도 밖(열 증감)"))
        for c in set(A.columns) & set(B.columns):
            for i in np.flatnonzero((A[c] != B[c]).to_numpy()):
                dec = A["결정"].iloc[i] if "결정" in A else ""
                ok = c in R3B_TEXT or (c == "기준2_MC안" and dec in ("T2-D2", "T2-D8"))
                rows.append(dict(파일=f.name, 행=i, 열=c, r3=A[c].iloc[i], r3b=B[c].iloc[i], 구분=f"의도({c})" if ok else "의도 밖"))
    for f in sorted(b.glob("*.csv")):
        if not (a / f.name).exists(): rows.append(dict(파일=f.name, 행="—", 열="—", r3="(없음)", r3b="새 파일", 구분="의도(새 파일)" if f.name == "T2_column_notes_r3b.csv" else "의도 밖(새 파일)"))
    return pd.DataFrame(rows, columns=["파일", "행", "열", "r3", "r3b", "구분"])


def stage_r3b():
    """재감사 R-H1·N1~N3: 판정 규칙만 다시, 출력은 새 폴더 OUT/r3b_판정_HHMM(r3_판정_0438 그대로). 시뮬레이션 없음. r3 대비 칸별 회귀 자동."""
    R = OUT / f"r3b_판정_{datetime.datetime.now():%H%M}"; os.environ["T2_R3_DIR"] = str(R); t0 = datetime.datetime.now(); log(f"r3b 시작 {R.name}")
    build_nb(HERE / "T2_판정r3b.py", HERE / "T2_판정r3b.ipynb", 1800)
    coverage(pd.read_csv(R / "T2_sensitivity_flip_r3.csv"), R, "_r3"); (R / "nb_meta").mkdir(exist_ok=True)
    rg = regress_r3_r3b(OUT / "r3_판정_0438", R); rg.to_csv(R / "T2_regress_r3_vs_r3b.csv", index=False, encoding="utf-8-sig")
    note = (f"대체됨 안내 ({datetime.date.today()}): 루트의 T2_summary_sentences.csv·T2_sensitivity_flip.csv, r2_판정\\, r3_판정_0438\\은 지우지 않고 남겨 둡니다. "
            f"현행 판정·문장은 {R.name}\\T2_summary_sentences_r3.csv(문장_원규칙 1순위)와 {R.name}\\T2_sensitivity_flip_r3.csv입니다(재감사 R-H1·N1~N3 반영).\n")
    (OUT / "T2_대체됨_안내.txt").write_text(note, encoding="utf-8")
    extra = "\n".join([f"stage=r3b(재감사 R-H1·N1~N3, 판정 규칙만, 시뮬레이션 없음)", f"mde_sha256={sha(OUT / 'T2_mde.csv')}", f"nb_start={t0.isoformat(timespec='seconds')}",
                       f"notebook_sha256_lf={rr.lf_sha256(HERE / 'T2_판정r3b.ipynb')}", f"regress_unintended={int(rg['구분'].str.startswith('의도 밖').sum())}", ""])
    rr.write_run_meta(R / "nb_meta", Path(__file__), deps=["notebooks/simpletest/_t2_core.py", "notebooks/simpletest/T2_판정r3b.py"], extra=extra)
    print(rg["구분"].value_counts()); print(rg[rg["구분"].str.startswith("의도 밖")].to_string()); log(f"r3b 끝 {R.name}")


if __name__ == "__main__":
    {"pre": stage_pre, "mde": stage_mde, "nb": stage_nb, "post": stage_post, "r2": stage_r2, "r3": stage_r3, "r3b": stage_r3b}[sys.argv[1]]()
