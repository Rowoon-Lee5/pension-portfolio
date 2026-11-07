# -*- coding: utf-8 -*-
"""I1_simple_20261017.ipynb 생성기 — pilot10 I1 '하락장에 줄일까·그대로 둘까·더 담을까' 간단 테스트.
명세 = $PENSION_DATA_ROOT/results/pilot10_20261017/I1_cut_hold_add/SPEC_I1_draft_20261017.md + DECISION_LOG 2026-10-17 'pilot10 I1 명세 확정(⬜ 추천대로)'.
탐색용 기술만 — 판정 없음. 실행: (cmd) set "PYTHONPATH=" 뒤 set PYTHONIOENCODING=utf-8 & python notebooks\\pilot10\\_gen_I1_simple.py
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pension_lab import runrecord as rr, paths  # noqa: E402

NB_PATH = ROOT / "notebooks" / "pilot10" / "I1_simple_20261017.ipynb"
OUTD = (paths.DATA_ROOT / "results/pilot10_20261017/I1_cut_hold_add")
INP = (paths.DATA_ROOT / "results/pilot9_20261013/C_real_20261017/inputs")
DSIM = (paths.DATA_ROOT / "results/pilot9_20261013/D_simple_20261017")
INPUTS = [INP / "C2_components_monthly.csv", INP / "C2_glide_by_remaining_years.csv",
          (paths.DATA_ROOT / "raw/kr_bond_pre2004_20261017/kis_monthly_2001_clean.csv"),
          (paths.DATA_ROOT / "processed/multicountry_returns_20261017.csv"),
          (paths.DATA_ROOT / "raw/fund_tdf/glidepath_disclosed_prospectus.csv"),
          (paths.DATA_ROOT / "results/pilot9_20261013/fee_pclass_20261016/pclass_fee_table.csv"),
          (paths.DATA_ROOT / "raw/equity_global/french/F-F_Research_Data_Factors.csv"),
          *sorted((paths.DATA_ROOT / "raw/equity_global/french_intl").glob("*.Dat")),
          (paths.DATA_ROOT / "raw/macro_fx_vol/ecos_cpi_long.csv"), (paths.DATA_ROOT / "raw/bond_kr/ecos_cd91_long.csv"),
          *[DSIM / f for f in ("D_kr_boot.csv", "D_t2_hist.csv", "D_placebo.csv", "D_mc_boot.csv", "pw_block.csv")]]
nb = nbf.v4.new_notebook(); cells = []
def md(s): cells.append(nbf.v4.new_markdown_cell(s))
def code(s): cells.append(nbf.v4.new_code_cell(s))

md("""# pilot10 I1 간단 테스트: 하락장에 줄일까, 그대로 둘까, 더 담을까 (2026-10-17)
**명세.** `I1_cut_hold_add\\SPEC_I1_draft_20261017.md` + `docs/DECISION_LOG.md` 2026-10-17 'pilot10 I1 명세 확정(⬜ 추천대로)'.

**성격.** 탐색용 기술 — 표와 숫자만 둔다. 판정 문장은 쓰지 않는다. d의 P5~P95는 '경로가 놓이는 범위'이고 신뢰구간이 아니다. ΔP5·ΔCVaR는 점값이다.

**팔(arm).** 같은 30세 저축자·같은 5대 평균 글라이드(G)·같은 경로·같은 보수.
- 그대로: 위험자산 비중 = G.
- 줄이기(주): 코스피 가격 월말 < 그 달 포함 10개월 단순평균이면 다음 달부터 G − Δ(Δ = 5·**10**·15%p), 줄인 몫은 국고채 TR. 평균 위로 돌아오면 다음 달부터 G. 같으면 직전 상태(Faber 2007 PDF 21~22쪽, Clare 2017 AAM 14쪽).
- 줄이기 민감도: 줄인 몫 → CD91 현금(Δ 10%p) / 신호 = 주식묶음 총수익(Δ 10%p) / 참고 = Faber 원형(평균 아래면 위험자산 전부 → CD91 현금).
- 더 담기: D 주 칸(코스피 가격 −20%·재무장 20%·전고점 회복 복귀, Δ = +5·**+10**·+15%p, `pilot9.dip_on`).
- 교차 참고: 10개월 평균 신호로 +10%p, −20% 하락 신호로 −10%p(신호와 방향을 나눠 보기 위함).

**결과변수.** 경로마다 d = ln(W_팔/W_그대로), 그리고 ln(W_더담기/W_줄이기). W = 360개월 뒤 실질 최종 금액.""")

code(r"""import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
%matplotlib inline
sys.path.insert(0, str(Path.cwd().parent / "pilot9"))                  # _build_C_real_inputs (D와 같은 입력 함수)
from _build_C_real_inputs import glide_w, fee_pct, fee_table
from pension_lab import pilot7 as P7, pilot9 as P9, pilot10 as P10, io, paths
from pension_lab.bootstrap import paired_resample_paths
from arch.bootstrap import optimal_block_length
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 400)
OUT = (paths.DATA_ROOT / "results/pilot10_20261017/I1_cut_hold_add"); OUT.mkdir(parents=True, exist_ok=True)
INP = P9.OUT / "C_real_20261017" / "inputs"; DSIM = P9.OUT / "D_simple_20261017"
SEED, NP, T = P7.SEED, P7.NP, 360
MGRS = ["KB", "미래에셋", "삼성", "신한", "한국투자"]
GROWTH = {"0%": 0.0, "3.4%": 0.034}
csv = lambda df, name: (df.to_csv(OUT / name, index=False, encoding="utf-8-sig"), df)[1]
t = np.arange(T); RY = -30 + t / 12; FEE_YEAR = 2025 + t // 12
contrib = lambda g: (1 + g) ** (t // 12)
TH, EX = -0.20, "peak"

# 팔 정의: (종류, 신호, 폭, 옮길 곳, 원형)
ARMS_KR = {f"줄이기_MA가격_-{k}": ("줄이기", "ma_px", -k / 100, "국채", False) for k in (5, 10, 15)}
ARMS_KR |= {"줄이기_MA가격_-10_현금": ("줄이기", "ma_px", -0.10, "현금", False), "줄이기_MA묶음TR_-10": ("줄이기", "ma_stk", -0.10, "국채", False),
            "Faber원형_MA가격_전부현금": ("참고", "ma_px", np.nan, "현금", True)}
ARMS_KR |= {f"더담기_D_+{k}": ("더담기", "dd", k / 100, "국채", False) for k in (5, 10, 15)}
ARMS_KR |= {"교차_MA가격_+10": ("교차", "ma_px", 0.10, "국채", False), "교차_D신호_-10": ("교차", "dd", -0.10, "국채", False)}
ARMS_MC = {f"줄이기_MA주식TR_-{k}": ("줄이기", "ma_px", -k / 100, "국채", False) for k in (5, 10, 15)} | \
          {f"더담기_D_+{k}": ("더담기", "dd", k / 100, "국채", False) for k in (5, 10, 15)} | \
          {"교차_MA주식TR_+10": ("교차", "ma_px", 0.10, "국채", False), "교차_D신호_-10": ("교차", "dd", -0.10, "국채", False)}
CUT_MAIN = lambda arms: [a for a, v in arms.items() if v[0] == "줄이기" and v[1] == "ma_px" and v[3] == "국채"]      # 주 줄이기(Δ 5·10·15)
def pairs_of(arms):
    cut = CUT_MAIN(arms)
    out = [(f"더담기_D_+{round(-arms[a][2] * 100)}", a) for a in cut]                                       # 같은 |Δ|끼리
    out += [("더담기_D_+10", a) for a, v in arms.items() if v[0] in ("줄이기", "참고") and a not in cut]       # 민감도·참고 팔
    out += [(a, b) for a in arms for b in arms if a.startswith("교차_MA") and b.startswith("교차_D")]
    return [(a, b) for a, b in out if a in arms and b in arms]
PL_ARMS = lambda arms: CUT_MAIN(arms) + [a for a, v in arms.items() if v[0] == "더담기"]

def signals(KO, SK=None, start=0):
    '''KO·SK (경로, 개월) 신호 수익 → {신호: 켜짐 (개월, 경로)}, dd 작동 기록(사건 수, 겹침 수).'''
    ON = {"ma_px": P10.lag1(P10.ma_below(KO)).T.copy()}
    if SK is not None: ON["ma_stk"] = P10.lag1(P10.ma_below(SK)).T.copy()
    on = np.zeros(KO.shape, bool); ne = np.zeros(len(KO), int); ov = np.zeros(len(KO), int)
    for p in range(len(KO)):
        on[p], ne[p], ov[p] = P9.dip_on(KO[p], TH, EX, P9.REARM, start)
    ON["dd"] = on.T.copy()
    return ON, (ne, ov)

def run(SKt, BDt, CAt, cc, ON, REC, G, FEE, meta, arms, place=True):
    '''팔별 행, 팔 쌍 행, 위약 행. SKt·BDt·CAt (개월, 경로). 경로 1개면 비 그대로.'''
    n, P_ = SKt.shape; rows, prs, pls = [], [], []
    for fk, f in FEE.items():
        for gk, g in GROWTH.items():
            c = contrib(g)[:n]; csum = c.sum(); fm = f[:n]
            Wb = P10.wealth(G[:n, None] * SKt + (1 - G[:n, None]) * BDt - fm[:, None], c); rb = Wb / cc / csum; W = {}
            for a, (kind, sig, dl, dest, full) in arms.items():
                on = ON[sig][:n]; R, raw = P10.arm_return(G[:n], on, dl, SKt, BDt, fm, CAt if dest == "현금" else None, full)
                Wr = P10.wealth(R, c); W[a] = Wr; rr_ = Wr / cc / csum; d = np.log(Wr / Wb)
                r = dict(**meta, 보수=fk, 납입증가=gk, 팔=a, 종류=kind, 신호=sig, 폭=dl, 옮길곳=dest,
                         켜진개월_평균=on.sum(0).mean(), 전환_평균=P10.switches(on.T).mean(), 평균비중변화_pctp=(np.clip(raw, 0, 1) - G[:n, None]).mean() * 100,
                         하한닿은_경로월=int((raw < 0).sum()), 상한닿은_경로월=int((raw > 1).sum()))
                if sig == "dd": r.update(사건수_평균=REC[0].mean(), 사건1개이상_비율=(REC[0] > 0).mean(), 겹침경로수=int((REC[1] > 0).sum()))
                if P_ == 1:
                    r.update(금액비_팔대그대로=float(np.exp(d[0])), d=float(d[0]), 기준_실질배수=float(rb[0]), 팔_실질배수=float(rr_[0]))
                else:
                    r.update(**P10.dist(d), 기준배수_중앙=np.median(rb), 기준배수_P5=np.quantile(rb, .05), 기준배수_CVaR5=P10.cvar5(rb),
                             규칙배수_중앙=np.median(rr_), 규칙배수_P5=np.quantile(rr_, .05), 규칙배수_CVaR5=P10.cvar5(rr_),
                             dP5=np.log(np.quantile(rr_, .05)) - np.log(np.quantile(rb, .05)), dCVaR=np.log(P10.cvar5(rr_)) - np.log(P10.cvar5(rb)))
                rows.append(r)
            for a, b in pairs_of(arms):
                dd_ = np.log(W[a] / W[b]); base = dict(**meta, 보수=fk, 납입증가=gk, 분자=a, 분모=b)
                prs.append(base | (dict(금액비=float(np.exp(dd_[0])), d=float(dd_[0])) if P_ == 1 else P10.dist(dd_)))
            if place and fk == "총보수" and gk == "0%" and P_ > 1:          # 위약: 켜짐의 월별 경로 평균 × Δ를 모든 경로에 매달(D 위약 정의, 부호만 반대 포함)
                for a in PL_ARMS(arms):
                    kind, sig, dl, dest, full = arms[a]; on = ON[sig][:n]
                    Rp, _ = P10.arm_return(G[:n], on.mean(1)[:, None], dl, SKt, BDt, fm)
                    d = np.log(W[a] / Wb); dp = np.log(P10.wealth(Rp, c) / Wb)
                    pls.append(dict(**meta, 보수=fk, 납입증가=gk, 팔=a, 종류=kind, 폭=dl, 켜진개월_평균=on.sum(0).mean(), 평균변화비중_pctp=dl * on.mean() * 100,
                                    규칙_d_중앙=np.median(d), 위약_d_중앙=np.median(dp), 위약_d_P5=np.quantile(dp, .05), 위약_d_P95=np.quantile(dp, .95),
                                    규칙빼기위약_중앙=np.median(d - dp), P_규칙gt위약=(d > dp).mean()))
    return rows, prs, pls""")

md("""## 0. 자기 점검 (합성 자료)
답을 아는 가짜 자료로 확인한다. 하나라도 틀리면 멈춘다(`assert`).""")
code(r"""rng = np.random.default_rng(0); Pn = 300
SK0, BD0, CA0 = rng.normal(0.006, 0.045, (Pn, T)), rng.normal(0.003, 0.01, (Pn, T)), rng.normal(0.002, 0.001, (Pn, T)); K0 = rng.normal(0.004, 0.07, (Pn, T))
G0 = glide_w(RY); F0 = {"총보수": np.full(T, 0.0078 / 12)}; one = np.ones(Pn); chk = []
ON0, R0 = signals(K0, SK0)
def rows0(SK, BD, CA, ON, arms):
    return run(SK.T.copy(), BD.T.copy(), CA.T.copy(), one, ON, R0, G0, F0, {}, arms, place=False)[0]
A0 = {k: v for k, v in ARMS_KR.items()}
# 1) 폭 0 → d = 0
r = rows0(SK0, BD0, CA0, ON0, {"z1": ("줄이기", "ma_px", 0.0, "국채", False), "z2": ("더담기", "dd", 0.0, "국채", False), "z3": ("줄이기", "ma_px", 0.0, "현금", False)})
chk.append(dict(점검="폭 0이면 모든 경로 d = 0(줄이기 국채·현금, 더 담기)", 기대=0.0, 결과=max(abs(x["d_P5"]) + abs(x["d_P95"]) for x in r), 통과=all(x["P_d영"] == 1.0 for x in r)))
# 2) 신호가 늘 오름(매달 +1%) → 10개월 평균 아래인 달 없음, 사건 없음 → d = 0
up = np.full((Pn, T), 0.01); ONu, Ru = signals(up, up)
r = rows0(SK0, BD0, CA0, ONu, A0)
chk.append(dict(점검="신호가 늘 오르면 모든 팔 d = 0", 기대=0.0, 결과=sum(int(v.sum()) for v in ONu.values()), 통과=all(x["P_d영"] == 1.0 for x in r)))
# 3) stk = bd → 국채로 옮기는 팔 |d| < 1e-12
r = rows0(SK0, SK0, CA0, ON0, {k: v for k, v in A0.items() if v[3] == "국채"})
mx = max(max(abs(x["d_P5"]), abs(x["d_P95"])) for x in r)
chk.append(dict(점검="위험자산 = 국채 수익이면 국채로 옮기는 팔 d = 0 (|d| < 1e-12)", 기대=0.0, 결과=mx, 통과=bool(mx < 1e-12)))
# 4) 룩어헤드 없음: t월 신호 수익만 바꿔도 0..t월 켜짐 같음
bad = 0
for p in range(60):
    for tt in (5, 9, 40, 100, 200, 300):
        for v in (-0.6, 0.6):
            K1 = K0[p].copy(); K1[tt] = v
            a, b = P10.lag1(P10.ma_below(K0[p])), P10.lag1(P10.ma_below(K1)); bad += int(not np.array_equal(a[:tt + 1], b[:tt + 1]))
chk.append(dict(점검="t월 수익을 바꿔도 0..t월 줄이기 켜짐이 같다(60경로×6시점×2값)", 기대=0, 결과=bad, 통과=bad == 0))
# 5) 손 계산: 10개월 0%, 10월 −5%, 11월 0%, 12월 +10% → 판정 10·11월 '아래', 켜짐 11·12월, 13월 복귀, 확인 당월(10)은 꺼짐
r5 = np.r_[np.zeros(10), -0.05, 0.0, 0.10, np.zeros(7)]
on5 = P10.lag1(P10.ma_below(r5))
ok5 = on5.tolist()[9:14] == [False, False, True, True, False]
chk.append(dict(점검="손 계산: 켜짐 11·12월, 확인월 10은 꺼짐, 13월 복귀(평균=가격인 달 0~9는 직전 상태=꺼짐)", 기대=True, 결과=ok5, 통과=bool(ok5)))
# 6) 첫 9개월(평균 없음) 꺼짐: 매달 −5%면 판정 9월부터 '아래' → 켜짐은 10월부터
on6 = P10.lag1(P10.ma_below(np.full(30, -0.05)))
chk.append(dict(점검="평균이 없는 0~8월 판정 없음 → 켜짐 첫 달 = 10월", 기대=10, 결과=int(np.argmax(on6)), 통과=bool(not on6[:10].any() and on6[10])))
# 7) 같음(가격 = 평균)이면 직전 상태 유지: 평평한 경로는 끝까지 꺼짐, 같음 횟수 기록
flat = np.zeros(40); ties = P10.ma_ties(flat)
chk.append(dict(점검="평평한 경로(가격 = 평균 31번)는 켜짐 0", 기대=0, 결과=int(P10.ma_below(flat).sum()), 통과=bool(P10.ma_below(flat).sum() == 0 and ties == 31)))
# 8) 더 담기 팔 = pilot9.dip_weights
gtest = np.full(T, 0.6); bad8 = 0
for p in range(50):
    w9, on9 = P9.dip_weights(K0[p], gtest, TH, 0.10, EX)
    _, raw = P10.arm_return(gtest, ON0["dd"][:, p:p + 1], 0.10, SK0[p][:, None], BD0[p][:, None], np.zeros(T)); bad8 += int(not np.array_equal(np.minimum(raw[:, 0], 1), w9))
chk.append(dict(점검="더 담기 비중 = pilot9.dip_weights(50경로)", 기대=0, 결과=bad8, 통과=bad8 == 0))
# 9) Faber 원형: 늘 켜지면 수익 = (1 − G)·국채 + G·현금 − 보수
onall = np.ones((T, 1), bool); g = G0
R9, _ = P10.arm_return(g, onall, np.nan, SK0[0][:, None], BD0[0][:, None], F0["총보수"], CA0[0][:, None], full=True)
ok9 = np.allclose(R9[:, 0], (1 - g) * BD0[0] + g * CA0[0] - F0["총보수"], atol=1e-15)
chk.append(dict(점검="Faber 원형 늘 켜짐 → (1−G)·국채 + G·현금 − 보수", 기대=True, 결과=ok9, 통과=bool(ok9)))
# 10) 현금 = 국채이면 현금 팔 = 국채 팔
a = rows0(SK0, BD0, BD0, ON0, {"c": ("줄이기", "ma_px", -0.10, "현금", False)})[0]; b = rows0(SK0, BD0, BD0, ON0, {"c": ("줄이기", "ma_px", -0.10, "국채", False)})[0]
chk.append(dict(점검="현금 수익 = 국채 수익이면 두 옮길 곳의 d가 같다", 기대=0.0, 결과=abs(a["d_중앙"] - b["d_중앙"]), 통과=bool(abs(a["d_중앙"] - b["d_중앙"]) < 1e-12)))
# 11) 수익 0 → 금액 = 납입 총액
ok11 = all(np.isclose(P10.wealth(np.zeros((T, 1)), contrib(g_))[0], contrib(g_).sum()) for g_ in GROWTH.values())
chk.append(dict(점검="수익 0 → 금액 = 납입 총액(0%·3.4%)", 기대=True, 결과=ok11, 통과=bool(ok11)))
# 12) 실제 글라이드에서 −15%p 하한 0, +15%p 상한 1에 닿지 않음
gm = glide_w(RY); chk.append(dict(점검="실제 G에서 G − 0.15 ≥ 0, G + 0.15 ≤ 1", 기대=True, 결과=f"{gm.min():.4f}~{gm.max():.4f}", 통과=bool(gm.min() >= 0.15 and gm.max() <= 0.85)))
CHK = csv(pd.DataFrame(chk), "selfcheck.csv"); print(CHK.to_string()); assert CHK.통과.all()""")

md("""## 1. 자료 (D와 같은 입력 + CD91)
- 한국: `C2_components_monthly.csv`의 `stk`(0.152·KOSPI200 TR + 0.848·French Developed × 원/달러, UH), `bd`(국고채 TR 2004-07~), `kospi`(가격 1980-02~), 물가 `io.asset_series('cpi')`, 현금 `io.asset_series('cd91')` 월말 연율 % → (1 + r/100)^(1/12) − 1(옛 아이디어 1과 같은 변환, 명목).
- KR-b 2001-02~2004-06 채권 = KIS 국고채권 총수익. 표본: KR-a 2004-07~2026-08(266), KR-b 2001-02~(307), KR-a~2024(246).
- 경로: `paired_resample_paths([stk, bd, cpi, kospi, cd91], …)` — 자료 점검에서 다섯 번째 계열을 넣어도 앞 네 계열 경로가 D와 같음을 확인했다(8절 회귀에서 다시 확인).""")
code(r"""C = pd.read_csv(INP / "C2_components_monthly.csv", index_col=0, parse_dates=True)
cpi = io.asset_series("cpi").resample("ME").last().pct_change(fill_method=None)
cd = io.asset_series("cd91").resample("ME").last(); cash = (1 + cd / 100) ** (1 / 12) - 1
kis = pd.read_csv((paths.DATA_ROOT / "raw/kr_bond_pre2004_20261017/kis_monthly_2001_clean.csv"), index_col=0, parse_dates=True).KISKTB_TR
kis_r = kis.pct_change(fill_method=None).loc["2001-02":"2004-06"]; assert len(kis_r) == 41 and kis_r.notna().all()
KOS = C.kospi.dropna(); STK = C.stk.dropna()
bd_b = pd.concat([kis_r, C.bd.loc["2004-07":]])
SAMP = {"KR-a": ("2004-07", "2026-08", C.bd), "KR-b": ("2001-02", "2026-08", bd_b), "KR-a~2024": ("2004-07", P7.PRE, C.bd)}
X = {}
for k, (a, b, bd) in SAMP.items():
    x = pd.DataFrame({"stk": C.stk, "bd": bd, "cpi": cpi, "kospi": C.kospi, "cash": cash}).loc[a:b]
    assert x.notna().all().all() and len(x) == len(pd.date_range(x.index[0], x.index[-1], freq="ME")), k
    X[k] = x
print({k: (v.index[0].strftime("%Y-%m"), v.index[-1].strftime("%Y-%m"), len(v)) for k, v in X.items()})
pw = []
for k, x in X.items():
    raw = float(optimal_block_length((x.stk - x.bd).to_numpy())["stationary"].iloc[0]); app = P7.pw_block(x.stk - x.bd)
    pw.append(dict(표본=k, 계열="stk − bd", n=len(x), PW_원값=raw, PW_적용=app, 하한적용=raw < 1))
PW = csv(pd.DataFrame(pw), "pw_block.csv"); print(PW.to_string(index=False))
FT = fee_table(); G = glide_w(RY, "mean5")
FEEM = {k: np.mean([fee_pct(m, FEE_YEAR, col=col, F=FT) for m in MGRS], axis=0) / 1200 for k, col in (("총보수", "total_fee_pct"), ("합성총보수", "synthetic_pct"))}
print("G 30세·45세·59세11월:", np.round(G[[0, 180, 359]], 4), "| 총보수 연%:", np.round(FEEM["총보수"][[0, 359]] * 1200, 4))""")

md("""## 2. 표 1 — 실제 신호 기록 (시뮬레이션 없음, KR-b 구간 2001-02~2026-08)
줄이기 켜짐 구간(코스피 가격 신호 = 1980-02~ 전체 코스피로 판정, 주식묶음 TR 신호 = 1990-07~ 전체로 판정)과 그 구간의 주식묶음·국채 누적 수익과 차(%p). 줄이기 기여 ≈ −Δ × 초과수익(1차 근사, 납입·복리 무시).
'구간 시작 전부터' = 2001-02 이전 판정으로 이미 켜져 있던 구간(표 2·부트스트랩에서는 쓰지 않음). 같은 구간에 D 더 담기(−20%·전고점)가 켜진 개월도 센다(D 표 1과 같은 판정: 확인월 전체 코스피).""")
code(r"""Xb = X["KR-b"]; ix = Xb.index
on_dd_full = pd.Series(P9.dip_on(KOS.to_numpy(), TH, EX, P9.REARM)[0], KOS.index).loc[ix[0]:ix[-1]]
rows = []
for nm, ser in (("코스피 가격", KOS), ("주식묶음 TR", STK)):
    on = pd.Series(P10.lag1(P10.ma_below(ser.to_numpy())), ser.index).loc[ix[0]:ix[-1]].astype(int)
    grp = (on.diff().fillna(on.iloc[0]) != 0).cumsum()
    for _, s in on[on == 1].groupby(grp[on == 1]):
        w = Xb.loc[s.index[0]:s.index[-1]]; cs, cb = np.prod(1 + w.stk) - 1, np.prod(1 + w.bd) - 1
        rows.append(dict(신호=nm, 켜짐_시작=s.index[0].strftime("%Y-%m"), 켜짐_끝=s.index[-1].strftime("%Y-%m"), 개월=len(s),
                         구간시작전부터=s.index[0] == ix[0], 자료끝까지=s.index[-1] == ix[-1], 위험자산누적_pct=cs * 100, 국채누적_pct=cb * 100, 초과_pctp=(cs - cb) * 100,
                         D더담기_같이켜진개월=int(on_dd_full.loc[s.index[0]:s.index[-1]].sum())))
T1 = csv(pd.DataFrame(rows), "I1_t1_signal_spells.csv")
print(T1.round(2).to_string(index=False)); print()
print(T1.groupby("신호").agg(구간수=("개월", "size"), 켜진개월=("개월", "sum"), D같이켜진=("D더담기_같이켜진개월", "sum")).to_string())
print("D 더담기(−20%·전고점) 켜진 개월(같은 창):", int(on_dd_full.sum()), "/", len(ix))""")

md("""## 3. 표 2 — 실제 역사 경로 1개
KR-a(2004-07에 30세, 266개월), KR-b(2001-02, 307개월), KR-a~2024(246개월). 신호는 1980-02~(묶음은 1990-07~) 전체로 판정하고, **판정월이 경로 첫 달 이후인 것만** 쓴다(D 표 2와 같은 규칙: 첫 달 켜짐 = 꺼짐). 값 = W_팔/W_그대로(명목·실질 같음).""")
code(r"""H, HP = [], []
for k, x in X.items():
    s0 = KOS.index.get_loc(x.index[0]); n = len(x); e = x.index[-1]
    mpx = P10.lag1(P10.ma_below(KOS.loc[:e].to_numpy()))[s0:s0 + n]; mpx[0] = False
    st = P10.lag1(P10.ma_below(STK.loc[:e].to_numpy())); mst = st[STK.index.get_loc(x.index[0]):][:n].copy(); mst[0] = False
    ond, ne, ov = P9.dip_on(KOS.to_numpy()[:s0 + n], TH, EX, P9.REARM, start=s0)
    ON = {"ma_px": mpx[:, None], "ma_stk": mst[:, None], "dd": ond[s0:s0 + n][:, None]}
    r, p_, _ = run(x.stk.to_numpy()[:, None], x.bd.to_numpy()[:, None], x.cash.to_numpy()[:, None], np.array([np.prod(1 + x.cpi.to_numpy())]), ON,
                   (np.array([ne]), np.array([ov])), G, FEEM, dict(표본=k, 시작=x.index[0].strftime("%Y-%m"), 끝=e.strftime("%Y-%m"), 개월=n), ARMS_KR)
    H += r; HP += p_
T2 = csv(pd.DataFrame(H), "I1_t2_hist.csv"); T2P = csv(pd.DataFrame(HP), "I1_t2_hist_pairs.csv")
v = T2[(T2.보수 == "총보수") & (T2.납입증가 == "0%")]
print("W_팔/W_그대로 (총보수·납입 0%)"); print(v.pivot_table(index="팔", columns="표본", values="금액비_팔대그대로", sort=False).round(4).to_string()); print()
print("켜진 개월 / 전환 횟수 (총보수·0%)"); print(v.pivot_table(index="팔", columns="표본", values=["켜진개월_평균", "전환_평균"], sort=False).to_string()); print()
print("W_분자/W_분모 (총보수·0%)"); w = T2P[(T2P.보수 == "총보수") & (T2P.납입증가 == "0%")]
print(w.pivot_table(index=["분자", "분모"], columns="표본", values="금액비", sort=False).round(4).to_string())""")

md("""## 4. 표 3 — 한국 부트스트랩 (seed 20261008, N = 10,000, 360개월, 블록 {1, PW, 12})
세 팔·위약이 같은 경로를 쓴다. PW 원값이 1보다 작으면 하한 1 → 블록 1과 같은 경로(그 결과를 'PW' 행에 그대로 적는다). 경로 첫 9개월은 10개월 평균이 없어 줄이기 꺼짐(⬜I1-g, 예열 없음).
d = ln(W_팔/W_그대로): 중앙·P5·P95(경로 범위)·P(d>0). ΔP5·ΔCVaR = 팔 대 그대로의 점값. 배수 = 실질 최종 금액 ÷ 명목 납입 총액. 위약 = 켜짐의 월별 경로 평균 × Δ를 모든 경로에 매달 똑같이(D 위약 정의, 줄이기는 부호 반대).""")
code(r"""B, BP, PL = [], [], []
for k, x in X.items():
    pwr = PW.set_index("표본").loc[k]; cache = {}
    for bn, b in (("1", 1.0), ("PW", float(pwr.PW_적용)), ("12", 12.0)):
        if b in cache:
            for L, c_ in zip((B, BP, PL), cache[b]): L += [dict(r, 블록=bn) for r in c_]
            continue
        SK, BD, CP, KO, CA = paired_resample_paths([x.stk, x.bd, x.cpi, x.kospi, x.cash], NP, T, b, SEED)
        ON, REC = signals(KO, SK); cc = np.prod(1 + CP, axis=1)
        out = run(SK.T.copy(), BD.T.copy(), CA.T.copy(), cc, ON, REC, G, FEEM, dict(표본=k, 블록=bn, 평균블록=b, PW_원값=pwr.PW_원값), ARMS_KR)
        for L, c_ in zip((B, BP, PL), out): L += c_
        cache[b] = out; print(k, bn, "done", flush=True)
KB_ = csv(pd.DataFrame(B), "I1_kr_boot.csv"); KBP = csv(pd.DataFrame(BP), "I1_kr_pairs.csv")
print(len(KB_), len(KBP), len(PL))""")
code(r"""cols = ["표본", "블록", "팔", "d_중앙", "d_P5", "d_P95", "P_d양수", "dP5", "dCVaR", "켜진개월_평균", "전환_평균", "평균비중변화_pctp"]
v = KB_[(KB_.보수 == "총보수") & (KB_.납입증가 == "0%")].copy()
for c in ["d_중앙", "d_P5", "d_P95", "dP5", "dCVaR"]: v[c] = v[c] * 100
print("총보수·납입 0% — d·ΔP5·ΔCVaR는 로그 %"); print(v[cols].round(3).to_string(index=False))""")
code(r"""w = KBP[(KBP.보수 == "총보수") & (KBP.납입증가 == "0%")].copy()
for c in ["d_중앙", "d_P5", "d_P95"]: w[c] = w[c] * 100
print("ln(W_분자/W_분모), 총보수·납입 0%, 로그 %"); print(w[["표본", "블록", "분자", "분모", "d_중앙", "d_P5", "d_P95", "P_d양수"]].round(3).to_string(index=False))""")
code(r"""print("합성총보수·납입 3.4% 판본 — d 중앙(로그 %), 주 팔"); z = KB_[KB_.팔.isin(["줄이기_MA가격_-10", "더담기_D_+10"])].copy(); z["d_중앙"] *= 100
print(z.pivot_table(index=["표본", "블록", "팔"], columns=["보수", "납입증가"], values="d_중앙", sort=False).round(3).to_string())""")

md("""## 5. 표 4 — 다국가 보충 (D와 같은 경로·같은 신호 정의)
9개국(AUS CAN DEU FRA GBR JPN NOR SWE USA), 자국 주식 = French 현지통화(미국 = F-F Mkt−RF + RF), 국채 = Swinkels 10년 총수익, 물가 = BIS. `P7.pooled_paths` 평균 블록 120(주)·1·12·240.
줄이기 신호 = 자국 주식 **총수익** 10개월 평균(한국 주 = 코스피 가격과 다름), 옮길 곳 = 자국 10년 국채. 현금 민감도·Faber 원형은 넣지 않는다(명세 ⬜I1-i).""")
code(r"""MC = pd.read_csv((paths.DATA_ROOT / "processed/multicountry_returns_20261017.csv"), dtype={"period": str})
def mcs(src, var, iso):
    x = MC[(MC.source == src) & (MC.variable == var) & (MC.iso3 == iso)]
    return pd.Series(x.value.to_numpy(float), index=pd.to_datetime(x.period) + pd.offsets.MonthEnd(0)).sort_index()
FR = {"AUS": "Austrlia", "CAN": "Canada", "DEU": "Germany", "FRA": "France", "GBR": "UK", "JPN": "Japan", "NOR": "Norway", "SWE": "Sweden"}
ff = pd.read_csv(paths.EQUITY_GLOBAL / "french" / "F-F_Research_Data_Factors.csv", skiprows=3, index_col=0)
fi = ff.index.astype(str).str.strip(); kp = fi.str.fullmatch(r"\d{6}")
us_eq = pd.Series((pd.to_numeric(ff["Mkt-RF"][kp]) + pd.to_numeric(ff["RF"][kp])).to_numpy() / 100, index=pd.to_datetime(fi[kp], format="%Y%m") + pd.offsets.MonthEnd(0))
PANEL = {}
for iso in ["AUS", "CAN", "DEU", "FRA", "GBR", "JPN", "NOR", "SWE", "USA"]:
    eq = us_eq if iso == "USA" else P7._french_table(paths.EQUITY_GLOBAL / "french_intl" / f"{FR[iso]}.Dat", "Value-Weight Local  Returns      All 4 Data Items Not Reqd")
    df = pd.DataFrame({"eq": eq, "bd": mcs("Swinkels2023", "bond_tr_10y_m", iso), "infl": mcs("BIS", "cpi_index", iso).pct_change(fill_method=None)}).dropna()
    assert len(df) == len(pd.date_range(df.index[0], df.index[-1], freq="ME")), iso
    PANEL[iso] = df
print({k: (v.index[0].strftime("%Y-%m"), v.index[-1].strftime("%Y-%m"), len(v)) for k, v in PANEL.items()})
MB, MP, MPL = [], [], []
for b in (120, 1, 12, 240):
    EQ, BD_, IN = P7.pooled_paths(PANEL, ["eq", "bd", "infl"], NP, T, b, SEED)
    ON, REC = signals(EQ); cc = np.prod(1 + IN, axis=1)
    r, p_, pl = run(EQ.T.copy(), BD_.T.copy(), None, cc, ON, REC, G, FEEM, dict(표본="다국가 9개국 풀", 블록=str(b), 평균블록=b), ARMS_MC)
    MB += r; MP += p_; MPL += pl; print("block", b, "done", flush=True)
MCB = csv(pd.DataFrame(MB), "I1_mc_boot.csv"); MCP = csv(pd.DataFrame(MP), "I1_mc_pairs.csv")
v = MCB[(MCB.보수 == "총보수") & (MCB.납입증가 == "0%")].copy()
for c in ["d_중앙", "d_P5", "d_P95", "dP5", "dCVaR"]: v[c] = v[c] * 100
print("다국가, 총보수·0%, 로그 %"); print(v[cols].round(3).to_string(index=False)); print()
w = MCP[(MCP.보수 == "총보수") & (MCP.납입증가 == "0%")].copy()
for c in ["d_중앙", "d_P5", "d_P95"]: w[c] = w[c] * 100
print(w[["블록", "분자", "분모", "d_중앙", "d_P5", "d_P95", "P_d양수"]].round(3).to_string(index=False))""")

md("""## 6. 위약 비교 → `I1_placebo.csv`
- 위약 = 규칙이 켜진 비율(달마다 1만 경로 평균) × Δ를 신호와 상관없이 모든 경로에 매달 똑같이 더하거나 뺀 정적 경로. 같은 경로·총보수·납입 0%.
- 위약은 경로 전체의 월별 평균 켜짐을 쓰므로 미리 실행할 수 있는 전략이 아니라 비교용 구성이다.""")
code(r"""PLD = csv(pd.DataFrame(PL + MPL), "I1_placebo.csv")
v = PLD[PLD.폭.abs() == 0.10].copy()
for c in ["규칙_d_중앙", "위약_d_중앙", "위약_d_P5", "위약_d_P95", "규칙빼기위약_중앙"]: v[c] = v[c] * 100
print("|Δ| = 10%p, 총보수·납입 0% — d는 로그 %")
print(v[["표본", "블록", "팔", "켜진개월_평균", "평균변화비중_pctp", "규칙_d_중앙", "위약_d_중앙", "규칙빼기위약_중앙", "P_규칙gt위약"]].round(4).to_string(index=False))""")

md("""## 6b. 순서 섞기 귀무 → `I1_shuffle_null.csv`(섞기별 행), `I1_shuffle_null_summary.csv`(요약) — 감사 HIGH-1 대응(2026-10-17)
**묻는 것.** 6절의 '규칙 − 위약'이 블록이 길 때 커지는 것이 자료의 **월 순서**(추세 지속성)에서 오는가, 아니면 같은 달들을 순서 없이 뽑아도 그만큼 나오는가.
- 방법(감사자 `audit\\recalc\\shuf.py`·`shufb.py`·`mcshuf.py`와 같은 방식): 표본 안에서 월 순서를 무작위로 섞는다. 한 달의 모든 열(한국 = stk·bd·cpi·kospi·cash, 다국가 = 나라마다 eq·bd·infl)은 같은 행으로 묶어 함께 옮긴다 → 같은 달 안의 관계는 남고 달 사이의 순서(시계열 상관)만 사라진다. 다국가는 나라마다 따로 섞는다.
- 섞은 자료에 6절과 **같은 절차**(같은 경로 seed 20261008, 같은 블록, 같은 신호·팔·위약, 총보수·납입 0%)를 돌려 줄이기 −10과 더 담기 +10의 '규칙 − 위약 중앙'·P(규칙 > 위약)을 구한다. 섞기마다 순열 seed = [20261017, 칸 번호, 섞기 번호](고정).
- 칸: 6절에서 규칙 − 위약이 커진 칸(KR-a·KR-b 블록 12, 다국가 블록 120)과 블록 1.
- 섞기 횟수·경로 수: 경로 **3,000**(감사자 2,000), 섞기 KR 블록 12 = **40회**, KR 블록 1 = **30회**, 다국가 = **100회**(감사자 20·20·12회).
  - 시간 제약: 사전 측정(2026-10-17, 이 PC, KR-a 블록 12) 한국 3,000경로 섞기 1회 ≈ 2.6초, 1만 경로 ≈ 9초 → 같은 시간이면 1만 경로는 섞기 횟수가 1/3로 준다. 목표는 3~10분이었으나 **실제 실행은 846초(약 14분)로 목표를 넘었다**(아래 출력의 칸별 초: 블록 1 칸이 1회 ≈ 5.5초로 사전 측정보다 느렸고, 다국가는 1회 ≈ 1.3초).
  - 몬테카를로 오차: 섞기마다 값이 흔들리는 폭(섞기 SD)은 주로 '어떤 순서로 섞였나'에서 나온다. 경로 수에서 오는 흔들림은 아래 '원값_같은N − 원값_N10000'(같은 원자료, 경로 3,000 대 1만)으로 보이며 섞기 SD보다 훨씬 작으면 경로 3,000으로 충분하다. 섞기 횟수 n에서 '원값 이상 비율' p의 표준오차 = √(p(1−p)/n)(예: p = 0.2, n = 40 → 0.063). 섞기 P5·P95는 30~100개 값의 분위라 거칠다(n = 40이면 P5 ≈ 작은 쪽 2~3번째 값).
- 원값 = 섞지 않은 자료의 같은 통계. 경로 3,000(섞기와 같은 경로 수, 비율 계산의 기준)과 1만(6절 `I1_placebo.csv`와 같아야 함 — `assert`, 허용 1e-12) 둘 다 적는다.
- 이 절은 기존 결과 파일을 바꾸지 않는다(새 파일 2개만 쓴다). 판정 없음 — 범위 안/밖과 비율만 적는다.""")
code(r"""import time
NUL_N, NUL_SEED = 3000, 20261017
NUL_CELLS = [("KR-a", "1", 1.0, 30), ("KR-a", "12", 12.0, 40), ("KR-b", "1", 1.0, 30), ("KR-b", "12", 12.0, 40),
             ("다국가 9개국 풀", "1", 1.0, 100), ("다국가 9개국 풀", "120", 120.0, 100)]
MCN = "다국가 9개국 풀"
def null_paths(src, b, n_, rng=None):
    '''섞은(rng 있으면) 자료로 6절과 같은 경로 → (위험자산, 신호수익, 국채) 각 (경로, 개월).'''
    sh = lambda df: df if rng is None else df.iloc[rng.permutation(len(df))].set_axis(df.index)
    if src == MCN:
        EQ, BD_, _ = P7.pooled_paths({k: sh(v) for k, v in PANEL.items()}, ["eq", "bd", "infl"], n_, T, b, SEED); return EQ, EQ, BD_
    x = sh(X[src]); SK, BD, _, KO, _ = paired_resample_paths([x.stk, x.bd, x.cpi, x.kospi, x.cash], n_, T, b, SEED); return SK, KO, BD
def null_stat(SK, KO, BD):
    '''run()의 위약 계산과 같은 식(총보수·납입 0%): 줄이기 −10(10개월 평균)·더 담기 +10(D 신호)의 (규칙−위약 중앙, P(규칙>위약)).'''
    ON, _ = signals(KO); fm = FEEM["총보수"]; c = contrib(0.0); SKt, BDt = SK.T.copy(), BD.T.copy()
    Wb = P10.wealth(G[:, None] * SKt + (1 - G[:, None]) * BDt - fm[:, None], c); out = []
    for sig, dl in (("ma_px", -0.10), ("dd", 0.10)):
        on = ON[sig]; d = np.log(P10.wealth(P10.arm_return(G, on, dl, SKt, BDt, fm)[0], c) / Wb)
        dp = np.log(P10.wealth(P10.arm_return(G, on.mean(1)[:, None], dl, SKt, BDt, fm)[0], c) / Wb)
        out.append((float(np.median(d - dp)), float((d > dp).mean())))
    return out
NROW, NSUM = [], []
for ci, (src, bn, b, ns) in enumerate(NUL_CELLS):
    t0 = time.time(); arms = ["줄이기_MA주식TR_-10" if src == MCN else "줄이기_MA가격_-10", "더담기_D_+10"]
    o10, oN = null_stat(*null_paths(src, b, NP)), null_stat(*null_paths(src, b, NUL_N))
    for a, (m10, p10) in zip(arms, o10):                    # 6절과 같은 절차인지: 1만 경로 원값 = I1_placebo.csv
        ref = PLD[(PLD.표본 == src) & (PLD.블록 == bn) & (PLD.팔 == a)]; assert len(ref) == 1, (src, bn, a)
        assert abs(ref.규칙빼기위약_중앙.iloc[0] - m10) <= 1e-12 and abs(ref.P_규칙gt위약.iloc[0] - p10) <= 1e-12, (src, bn, a)
    sres = [null_stat(*null_paths(src, b, NUL_N, np.random.default_rng([NUL_SEED, ci, s]))) for s in range(ns)]
    for s, rs in enumerate(sres):
        NROW += [dict(표본=src, 블록=bn, 평균블록=b, 경로수=NUL_N, 섞기번호=s, 순열시드=f"[{NUL_SEED},{ci},{s}]", 팔=a, 규칙빼기위약_중앙=m, P_규칙gt위약=p)
                 for a, (m, p) in zip(arms, rs)]
    for k, a in enumerate(arms):
        m = np.array([rs[k][0] for rs in sres]); p = np.array([rs[k][1] for rs in sres]); o = oN[k][0]; ge = float((m >= o).mean())
        NSUM.append(dict(표본=src, 블록=bn, 평균블록=b, 팔=a, 경로수=NUL_N, 섞기횟수=ns,
                         원값_N10000=o10[k][0], 원값P_N10000=o10[k][1], 원값_같은N=o, 원값P_같은N=oN[k][1], 원값_같은N빼기N10000=o - o10[k][0],
                         섞기_평균=m.mean(), 섞기_SD=m.std(ddof=1), 섞기_최소=m.min(), 섞기_P5=np.quantile(m, .05), 섞기_P95=np.quantile(m, .95), 섞기_최대=m.max(),
                         원값이상_비율=ge, 원값이상_표준오차=float(P7.mc_se(ge, ns)), 원값이하_비율=float((m <= o).mean()),
                         범위안_같은N=bool(m.min() <= o <= m.max()), 범위안_N10000=bool(m.min() <= o10[k][0] <= m.max()),
                         P섞기_최소=p.min(), P섞기_P5=np.quantile(p, .05), P섞기_P95=np.quantile(p, .95), P섞기_최대=p.max()))
    print(src, "블록", bn, f"섞기 {ns}회 {time.time() - t0:.0f}초", flush=True)
NULR = csv(pd.DataFrame(NROW), "I1_shuffle_null.csv"); NUL = csv(pd.DataFrame(NSUM), "I1_shuffle_null_summary.csv")
z = NUL.copy()
for c in ["원값_N10000", "원값_같은N", "원값_같은N빼기N10000", "섞기_평균", "섞기_SD", "섞기_최소", "섞기_P5", "섞기_P95", "섞기_최대"]: z[c] = z[c] * 100
print("규칙 − 위약 중앙(로그 %), 총보수·납입 0% — 원값 대 순서를 섞은 자료")
print(z[["표본", "블록", "팔", "섞기횟수", "원값_N10000", "원값_같은N", "원값_같은N빼기N10000", "섞기_평균", "섞기_SD", "섞기_최소", "섞기_P5", "섞기_P95", "섞기_최대",
         "원값이상_비율", "원값이상_표준오차", "범위안_같은N", "범위안_N10000"]].round(3).to_string(index=False)); print()
print("P(규칙 > 위약) — 원값 대 섞은 자료")
print(z[["표본", "블록", "팔", "원값P_N10000", "원값P_같은N", "P섞기_최소", "P섞기_P5", "P섞기_P95", "P섞기_최대"]].round(3).to_string(index=False))""")

md("""## 7. 그림 — KR-a·블록 1·총보수·납입 0%: 팔별 d 중앙과 경로 범위(P5~P95), 위약 d 중앙
점 = 경로 중앙값, 선 = 경로 P5~P95(신뢰구간 아님). 위약은 위약이 있는 팔만.""")
code(r"""plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
v = KB_[(KB_.표본 == "KR-a") & (KB_.블록 == "1") & (KB_.보수 == "총보수") & (KB_.납입증가 == "0%")].reset_index(drop=True)
pl = PLD[(PLD.표본 == "KR-a") & (PLD.블록 == "1")].set_index("팔")
fig, ax = plt.subplots(figsize=(8, 5.5)); y = np.arange(len(v))[::-1]
ax.hlines(y, v.d_P5 * 100, v.d_P95 * 100, color="#2a78d6", lw=2)
ax.plot(v.d_중앙 * 100, y, "o", ms=8, color="#2a78d6", mec="white", mew=2, label="규칙 d 중앙 (선 = P5~P95)")
yp = [yy for yy, a in zip(y, v.팔) if a in pl.index]
ax.plot([pl.loc[a, "위약_d_중앙"] * 100 for a in v.팔 if a in pl.index], yp, "D", ms=7, mfc="none", color="#eb6834", mew=2, label="위약 d 중앙")
ax.axvline(0, color="#888", lw=1); ax.set_yticks(y, v.팔); ax.set_xlabel("d = ln(W_팔 / W_그대로), 로그 %")
ax.grid(axis="x", color="#ddd", lw=0.8); ax.set_axisbelow(True); [ax.spines[s].set_visible(False) for s in ("top", "right")]
ax.legend(loc="upper left", frameon=False); ax.set_title("KR-a·블록 1·총보수·납입 0% (경로 1만 개)", loc="left")
fig.tight_layout(); fig.savefig(OUT / "I1_fig_d_by_arm_KRa_b1.png", dpi=150); plt.show()""")

md("""## 8. D 동결 결과와 회귀 대조 → `regress_vs_D.csv`
'더 담기'(D 주 칸 −20%·re20·전고점, Δ +5·+10·+15%p)와 '그대로'(기준배수 열) 값이 D 동결 CSV(`docs/동결목록.md` 188행)의 같은 칸과 같아야 한다. 허용 오차 1e-12(절대). 하나라도 다르면 멈춘다.""")
code(r"""def cmpD(Dfile, mine, keyD, keyM, cols, filt):
    Dd = pd.read_csv(DSIM / Dfile, encoding="utf-8-sig", dtype={"블록": str}); Dd = Dd[filt(Dd)]
    m = mine.copy(); m["증액"] = m.폭.round(2); Dd["증액"] = Dd.증액.round(2)
    j = Dd.merge(m, left_on=keyD, right_on=keyM, how="left", suffixes=("_D", "_I1"), validate="one_to_one")
    out = []
    for c in cols:
        cd_, ci_ = (c + "_D", c + "_I1") if c + "_D" in j else (c, c)
        diff = (j[cd_].astype(float) - j[ci_].astype(float)).abs()
        out += [dict(파일=Dfile, **{kk: r[kk] for kk in keyD}, 열=c, D값=r[cd_], I1값=r[ci_], 절대차=dv, 일치=bool(dv <= 1e-12)) for (_, r), dv in zip(j.iterrows(), diff)]
    return out
fD = lambda D_: (D_.문턱 == -0.20) & (D_.재무장 == "re20") & (D_.복귀 == "전고점 회복")
add = lambda D_: D_[D_.종류 == "더담기"]
cb = ["d_중앙", "d_P5", "d_P95", "P_d양수", "P_d영", "기준배수_중앙", "기준배수_P5", "기준배수_CVaR5", "규칙배수_중앙", "규칙배수_P5", "규칙배수_CVaR5", "dP5", "dCVaR",
      "사건수_평균", "사건1개이상_비율", "켜진개월_평균", "겹침경로수", "상한닿은_경로월"]
RG = cmpD("D_kr_boot.csv", add(KB_), ["표본", "블록", "보수", "납입증가", "증액"], ["표본", "블록", "보수", "납입증가", "증액"], cb, fD)
RG += cmpD("D_mc_boot.csv", add(MCB), ["표본", "블록", "보수", "납입증가", "증액"], ["표본", "블록", "보수", "납입증가", "증액"], cb, fD)
T2r = add(T2).rename(columns={"금액비_팔대그대로": "금액비_규칙대기준", "팔_실질배수": "규칙_실질배수"})
RG += cmpD("D_t2_hist.csv", T2r, ["표본", "보수", "납입증가", "증액"], ["표본", "보수", "납입증가", "증액"], ["금액비_규칙대기준", "d", "기준_실질배수", "규칙_실질배수", "사건수_평균", "켜진개월_평균", "겹침경로수"], fD)
PLr = add(PLD).rename(columns={"평균변화비중_pctp": "평균추가비중_pctp"})
RG += cmpD("D_placebo.csv", PLr, ["표본", "블록", "증액"], ["표본", "블록", "증액"], ["켜진개월_평균", "평균추가비중_pctp", "규칙_d_중앙", "위약_d_중앙", "위약_d_P5", "위약_d_P95", "규칙빼기위약_중앙", "P_규칙gt위약"], fD)
RGD = csv(pd.DataFrame(RG), "regress_vs_D.csv")
print(RGD.groupby("파일").agg(칸=("일치", "size"), 일치=("일치", "sum"), 최대절대차=("절대차", "max")).to_string())
assert RGD.D값.notna().all() and RGD.I1값.notna().all(), "짝 없는 칸"
assert RGD.일치.all(), "D 동결과 다른 칸 — 멈춤"
pwD = pd.read_csv(DSIM / "pw_block.csv", encoding="utf-8-sig"); assert np.allclose(pwD.PW_원값, PW.PW_원값, rtol=0, atol=1e-12)""")

md("""## 9. 작동 기록 요약과 한계
- 판정 도구(바깥 부트스트랩·Bonferroni·블록 관문·δ 꼬리 조건)는 쓰지 않았다. ΔP5·ΔCVaR는 점값이다.
- 주 비교의 줄이기와 더 담기는 신호(10개월 평균 vs −20% 하락)와 방향(− vs +)이 동시에 다르다. 교차 2팔(`교차_*`)과 쌍 비교(`I1_kr_pairs.csv`)를 함께 본다.
- d에는 '바뀐 비중 × 켜진 기간' 효과가 들어 있다. 같은 평균 변화의 위약 비교는 6절 표다.
- 한국 블록 {1, PW, 12}는 모두 12개월 이하다(KR-a PW 원값 0.44 → 블록 1). 블록 12·다국가 블록 120에서 커진 '규칙 − 위약'이 월 순서에서 오는지는 6b절의 순서 섞기 귀무와 숫자로만 대조한다(아래 출력): 섞은 자료의 범위(최소~최대) 안이면 '식별 안 됨', 밖이면 원값과 섞기 범위·원값 이상 비율만 적는다.
- 한국 부트스트랩 1만 경로는 같은 266(KR-b 307)개월을 되풀이해 뽑는다. P(규칙 > 위약)은 그 한 표본의 성질이고 1만 개의 독립 증거가 아니다. 실제 역사 경로(표 2)는 순서가 그대로인 경로 1개다.
- 위약 없는 행(Faber 원형, 줄이기 민감도 = 현금 행선지·묶음TR 신호·Δ 5·15, 교차 2팔): 위약 없음 → d는 노출과 시점이 섞임.
- 경로 첫 9개월은 줄이기 꺼짐(예열 없음). 실제 역사 경로는 판정월이 경로 첫 달 이후인 신호만 쓴다(첫 달 꺼짐).
- 거래비용 0(Faber PDF 22쪽처럼). 전환 횟수는 작동 기록(`전환_평균`)에 있다. 옮긴 몫에도 같은 보수. 현금은 CD91 금리 그대로(실제 MMF 보수 없음).
- D의 한계(국내 몫 0.152 고정, 선진국·UH만, 공시 글라이드 30년 유지, 한국·다국가 정의 차이, 다국가 사건 비독립·생존 시장)를 그대로 물려받는다.
- 다국가 줄이기 신호는 자국 주식 총수익, 한국 주 신호는 코스피 가격이다.""")
code(r"""ties = {k: P10.ma_ties(x.kospi.to_numpy()) for k, x in X.items()}
print("실제 표본 안 코스피 가격 = 10개월 평균인 달 수(⬜I1-k 영향):", ties)
print("하한 0%·상한 100%에 닿은 경로-월 합(한국·다국가 전 칸):", int(KB_.하한닿은_경로월.sum() + MCB.하한닿은_경로월.sum()), int(KB_.상한닿은_경로월.sum() + MCB.상한닿은_경로월.sum()))""")
code(r"""print("순서 섞기 귀무 대조(6b절, 규칙 − 위약 중앙, 로그 %, 총보수·납입 0%):")
for _, r in NUL.iterrows():
    tag = "섞은 자료 범위 안 → 식별 안 됨" if r.범위안_같은N else ("섞은 자료 범위 밖(원값 > 섞기 최대)" if r.원값_같은N > r.섞기_최대 else "섞은 자료 범위 밖(원값 < 섞기 최소)")
    print(f"- {r.표본}·블록 {r.블록}·{r.팔}: 원값 {r.원값_같은N * 100:+.3f}(경로 {r.경로수:,}) / {r.원값_N10000 * 100:+.3f}(경로 1만), "
          f"섞기 {r.섞기횟수}회 범위 {r.섞기_최소 * 100:+.3f}~{r.섞기_최대 * 100:+.3f}(P5 {r.섞기_P5 * 100:+.3f}, P95 {r.섞기_P95 * 100:+.3f}), "
          f"원값 이상 {r.원값이상_비율:.3f} → {tag}" + ("" if r.범위안_같은N == r.범위안_N10000 else " (1만 경로 원값 기준으로는 범위 판단이 다름)"))""")

nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
os.environ["PYTHONPATH"] = str(ROOT / "src")
NotebookClient(nb, timeout=7200, kernel_name="python3", resources={"metadata": {"path": str(NB_PATH.parent)}}).execute()
rr.save_executed(nb, NB_PATH)
NBM = OUTD / "nb_meta"; NBM.mkdir(parents=True, exist_ok=True)
extra = "seed=20261008\nN=10000\nT=360\nblocks_kr=1,PW,12\nblocks_mc=120,1,12,240\n" \
    + "shuffle_null(6b, audit HIGH-1 fix1 2026-10-17): N=3000 path_seed=20261008 perm_seed=[20261017,cell,s] shuffles KR-a/KR-b b1=30 b12=40, MC b1,b120=100\n" + "".join(
    f"input {p} sha256={rr.raw_sha256(p)}\n" for p in INPUTS + [ROOT / "notebooks/pilot9/_build_C_real_inputs.py"]) \
    + "".join(f"result {p.name} sha256={rr.raw_sha256(p)}\n" for p in sorted(OUTD.glob("*.csv")))
rr.write_run_meta(NBM, Path(__file__), ["src/pension_lab/pilot10.py", "src/pension_lab/pilot9.py", "src/pension_lab/pilot7.py", "src/pension_lab/bootstrap.py",
                                         "src/pension_lab/io.py", "notebooks/pilot9/_build_C_real_inputs.py"], extra)
print("실행완료 저장:", NB_PATH, NB_PATH.stat().st_size, "bytes")
