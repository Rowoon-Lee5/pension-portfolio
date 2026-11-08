# -*- coding: utf-8 -*-
"""A_simple_20261017.ipynb 생성기 — pilot9 A 간단 테스트. 명세 = docs/DECISION_LOG.md 2026-10-17 'pilot9 A 간단 테스트 명세'(결과 전 기록).

층1 실제 기준가(5대 2055 C-Pe, C_real inputs C1) / 층2 공시 글라이드 × 실제 지수 − C-Pe 보수 시뮬레이션((a) 역사 경로 1개, (b) 블록 {1, PW, 12} 공통 경로).
탐색용 기술만 — 판정 없음(X=1.10%는 참고선). 실행: (cmd) set "PYTHONPATH=" 뒤 set PYTHONIOENCODING=utf-8 & python notebooks\\pilot9\\_gen_A_simple.py
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pension_lab import runrecord as rr, paths  # noqa: E402

NB_PATH = ROOT / "notebooks" / "pilot9" / "A_simple_20261017.ipynb"
OUTD = (paths.DATA_ROOT / "results/pilot9_20261013/A_simple_20261017")
INP = (paths.DATA_ROOT / "results/pilot9_20261013/C_real_20261017/inputs")
INPUTS = [INP / "C1_real_tdf2055_cpe_monthly.csv", INP / "C2_components_monthly.csv",
          (paths.DATA_ROOT / "raw/fund_tdf/glidepath_disclosed_prospectus.csv"),
          (paths.DATA_ROOT / "results/pilot9_20261013/fee_pclass_20261016/pclass_fee_table.csv"),
          (paths.DATA_ROOT / "raw/macro_fx_vol/ecos_cpi_long.csv"),
          INP / "C2_check_index_vs_real_overlap.csv"]          # io.asset_series('cpi') 원천(감사 LOW-3, 문서 단계 추가)
nb = nbf.v4.new_notebook(); cells = []
def md(s): cells.append(nbf.v4.new_markdown_cell(s))
def code(s): cells.append(nbf.v4.new_code_cell(s))

md("""# pilot9 A 간단 테스트: 같은 2055 TDF, 운용사에 따라 최종 금액이 얼마나 다른가 (2026-10-17)
**명세.** `docs/DECISION_LOG.md` 2026-10-17 'pilot9 A 간단 테스트 명세'(결과 보기 전 기록) 그대로.
**성격.** 탐색용 기술 — 표와 숫자만 둔다. 판정 문장은 쓰지 않는다. X = 1.10%(비 1.011)는 참고선으로만 표시한다(DL 132에서 효력이 정지된 X 후보의 정정값, ⬜ 재결정 전 후보값).
**문서 단계 수정(2026-10-17).** 감사(`A_simple_20261017\\audit\\AUDIT_A_simple.md`) MEDIUM·LOW 가운데 문구와 추가 계산을 반영했다. 기존 결과 CSV의 칸은 바꾸지 않았고, 새 파일(`L1_common_trough.csv`, `L1_common_pair_t.csv`, `L2b_sens_glide_align.csv`)과 `pw_block.csv`의 새 열만 더했다.
- **층1(실제):** 5대 2055 연금저축 클래스(C-Pe) 실제 월 총수익. 실제 보수·실제 운용이 이미 들어 있다.
- **층2(시뮬레이션):** 운용사별 공시 2055 글라이드 × 같은 실제 지수 − 운용사별 C-Pe 총보수 단계표(합성총보수 병기). 30세→60세 매달 같은 금액, 2026년 시작. '공시대로 운용하면'의 차이다.""")

code(r"""import sys, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path.cwd()))                          # notebooks/pilot9 (입력 생성기 함수 import)
from _build_C_real_inputs import glide_w, fee_pct, fee_table
from pension_lab import pilot7 as P7, pilot9 as P9, io, paths
from pension_lab.bootstrap import paired_resample_paths
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
OUT = P9.OUT / "A_simple_20261017"; OUT.mkdir(parents=True, exist_ok=True)
INP = P9.OUT / "C_real_20261017" / "inputs"
SEED, NP, T = P7.SEED, P7.NP, 360                            # seed 20261008, N 10,000, 30세→60세 360개월
MGRS = ["KB", "미래에셋", "삼성", "신한", "한국투자"]
PAIRS = list(itertools.combinations(MGRS, 2))                  # 10쌍, 비 = 앞 ÷ 뒤
X_REF = 1.011                                                  # X = 1.10% 참고선(판정에 쓰지 않음). DL 132 효력 정지 X 후보의 정정값 = ⬜ 재결정 전 후보값
FEECOL = {"총보수": "total_fee_pct", "합성총보수": "synthetic_pct"}
csv = lambda df, name: (df.to_csv(OUT / name, index=False, encoding="utf-8-sig"), df)[1]

def final_amt(R):
    '''R (경로, 개월) 월 수익. 매달 초 1 납입 → 그 달 수익. 마지막 달 말 잔액.'''
    R = np.atleast_2d(R); V = np.zeros(R.shape[0])
    for t in range(R.shape[1]):
        V = (V + 1) * (1 + R[:, t])
    return V""")

md("""## 0. 자기 점검 (합성 자료)
같은 함수로 결과를 내기 전에, 답을 아는 가짜 자료로 확인한다.
1. 글라이드·보수가 같으면 비 = 정확히 1.
2. 보수만 연 0.1%p 다르면(월 수익 0.5% 고정, 360개월): 보수 낮은 쪽이 더 많고, 비가 닫힌 식(적립 등비급수)과 같다.
3. 분해: 보수 몫 + 글라이드 몫 = 전체(두 순서 모두), 글라이드가 같으면 글라이드 몫 = 0.
4. 층1 지표: 매달 1% → 연수익 = 1.01¹²−1, 변동성 0, 최대낙폭 0 / −50% 뒤 +100% → 최대낙폭 −50%.""")
code(r"""def decomp(L, a, b):
    '''L[(g, f)] = ln 최종 금액(글라이드 g, 보수 f). 전체 T = ln(W_a/W_b).
    순서1 = 글라이드 먼저: (b,b)→(a,b) 글라이드 몫 G1, 그다음 (a,b)→(a,a) 보수 몫 F1. 순서2 = 보수 먼저: (b,b)→(b,a) F2, 그다음 G2. Shapley = 두 순서 평균.'''
    Tt = L[a, a] - L[b, b]
    F1, G1 = L[a, a] - L[a, b], L[a, b] - L[b, b]
    G2, F2 = L[a, a] - L[b, a], L[b, a] - L[b, b]
    return dict(T=Tt, F1=F1, G1=G1, F2=F2, G2=G2, S_F=(F1 + F2) / 2, S_G=(G1 + G2) / 2)

def l1_stats(r):
    r = np.asarray(r, float); lvl = np.r_[1.0, np.cumprod(1 + r)]
    return dict(ann_ret=lvl[-1] ** (12 / len(r)) - 1, ann_vol=r.std(ddof=1) * np.sqrt(12) if len(r) > 1 else np.nan,
                mdd=(lvl / np.maximum.accumulate(lvl) - 1).min())

rng = np.random.default_rng(0); Z = rng.normal(0.005, 0.04, (200, T))
w0, f0 = np.linspace(0.8, 0.4, T), np.full(T, 0.008 / 12)
chk = []
same = final_amt(w0 * Z + (1 - w0) * 0.002 - f0) / final_amt(w0 * Z + (1 - w0) * 0.002 - f0)
chk.append(dict(점검="같은 글라이드·같은 보수 → 비 = 1", 기대=1.0, 결과=float(np.abs(same - 1).max() + 1), 통과=bool(np.all(same == 1.0))))
r, dlt = 0.005, 0.001 / 12
closed = lambda q: ((1 + q) ** (T + 1) - (1 + q)) / q          # Σ_{k=1..T}(1+q)^k
sim = final_amt(np.full(T, r - dlt))[0] / final_amt(np.full(T, r))[0]
chk.append(dict(점검="보수만 0.1%p 높음: 비(높음/낮음) = 닫힌 식", 기대=closed(r - dlt) / closed(r), 결과=sim,
                통과=bool(np.isclose(sim, closed(r - dlt) / closed(r), rtol=0, atol=1e-12) and sim < 1)))
sim0 = final_amt(np.full(T, -dlt))[0] / T                       # 수익 0이면 ≈ 1 − 0.1%×평균 보유기간(약 15년)
chk.append(dict(점검="수익 0·보수 0.1%p: 비 ≈ 1 − 0.001×15.04(평균 보유년)", 기대=1 - 0.001 * (T + 1) / 2 / 12, 결과=sim0,
                통과=bool(abs(sim0 - (1 - 0.001 * (T + 1) / 2 / 12)) < 5e-4)))
gA, gB = np.linspace(0.8, 0.4, T), np.linspace(0.7, 0.2, T); fA, fB = np.full(T, 0.0085 / 12), np.full(T, 0.0065 / 12)
G, F = {"A": gA, "B": gB}, {"A": fA, "B": fB}
L = {(g, f): np.log(final_amt(G[g] * Z + (1 - G[g]) * 0.002 - F[f])) for g in "AB" for f in "AB"}
D = decomp(L, "A", "B")
chk.append(dict(점검="분해: F1+G1 = F2+G2 = S_F+S_G = T", 기대=0.0, 결과=float(max(np.abs(D["F1"] + D["G1"] - D["T"]).max(), np.abs(D["F2"] + D["G2"] - D["T"]).max(), np.abs(D["S_F"] + D["S_G"] - D["T"]).max())),
                통과=bool(np.allclose(D["F1"] + D["G1"], D["T"], atol=1e-12) and np.allclose(D["S_F"] + D["S_G"], D["T"], atol=1e-12))))
G["B"] = gA; L = {(g, f): np.log(final_amt(G[g] * Z + (1 - G[g]) * 0.002 - F[f])) for g in "AB" for f in "AB"}; D = decomp(L, "A", "B")
chk.append(dict(점검="글라이드 같음 → S_G = 0, S_F = T", 기대=0.0, 결과=float(np.abs(D["S_G"]).max()), 통과=bool(np.all(D["S_G"] == 0) and np.allclose(D["S_F"], D["T"]))))
s1 = l1_stats(np.full(24, 0.01)); s2 = l1_stats([0.0, -0.5, 1.0])
chk.append(dict(점검="층1 지표(1%/월: 연수익·변동성·낙폭)", 기대=1.01 ** 12 - 1, 결과=s1["ann_ret"], 통과=bool(np.isclose(s1["ann_ret"], 1.01 ** 12 - 1) and s1["ann_vol"] < 1e-15 and s1["mdd"] == 0)))
chk.append(dict(점검="층1 최대낙폭(−50% 뒤 +100%)", 기대=-0.5, 결과=s2["mdd"], 통과=bool(np.isclose(s2["mdd"], -0.5))))
CHK = csv(pd.DataFrame(chk), "selfcheck.csv"); print(CHK.to_string()); assert CHK.통과.all()""")

md("""## 1. 층1 — 실제 기준가 (5대 2055 C-Pe 실제 월 총수익, 결산 보정)
- 입력: `C_real_20261017\\inputs\\C1_real_tdf2055_cpe_monthly.csv`(시차 0). **UH 판본이 주, H 판본 병기.** 신한·미래에셋은 헤지 표기 없음, 삼성은 H판만 있어 두 판본 모두에 같은 계열이 들어간다.
- C-P 앞 잇기: 없음(주 열) / 있음(`*_fillCP` 열, C-P 수익 + 공시 보수 차). 한국투자_H는 C-P 코드가 없어 '있음'도 같은 열.
- 구간: 공통(그 판본 5개 모두 자료가 있는 달) / 운용사별 전 구간. 전 구간 안에 빈 달이 있으면 **가장 최근의 끊김 없는 구간**을 쓴다(빈 달 수는 표에 적음).
- 지표: 연수익(기하), 변동성(월 표준편차×√12), 최대낙폭(월말), 매달 초 10만원 적립 시 마지막 달 말 금액(명목)과 납입 총액.
- **'전구간' 행은 운용사마다 시작 달이 다르다(2020-03~2024-08).** 기간이 달라 운용사끼리 비교하지 않는다. 운용사끼리 나란히 놓을 수 있는 것은 '공통' 행뿐이다.
- 층1 수익 차에는 환헤지(삼성은 H판만, 신한·미래에셋은 헤지 표기 없음), 글라이드, 보수 차이가 함께 들어 있다. 공통 구간 최대낙폭이 어느 달에서 나왔는지와 쌍별 월 수익 차의 t값은 아래 1-b에 적는다.""")
code(r"""M = pd.read_csv(INP / "C1_real_tdf2055_cpe_monthly.csv", index_col=0, parse_dates=True)
SETS = {"UH": {"KB": "KB_UH", "미래에셋": "미래에셋", "삼성": "삼성_H", "신한": "신한", "한국투자": "한국투자_UH"},
        "H": {"KB": "KB_H", "미래에셋": "미래에셋", "삼성": "삼성_H", "신한": "신한", "한국투자": "한국투자_H"}}
def last_run(s):
    s = s.dropna(); per = s.index.to_period("M"); brk = np.r_[True, (per[1:] - per[:-1]).map(lambda x: x.n) != 1]
    return s[np.cumsum(brk) == np.cumsum(brk)[-1]]
rows = []
for hset, mp in SETS.items():
    for fill in ("없음", "있음"):
        cols = {m: (f"{c}_fillCP" if fill == "있음" and f"{c}_fillCP" in M else c) for m, c in mp.items()}
        common = M[list(cols.values())].dropna().index
        assert len(common) and (common.to_period("M")[-1] - common.to_period("M")[0]).n + 1 == len(common)   # 공통 구간 끊김 없음
        for win in ("공통", "전구간"):
            for m, c in cols.items():
                s = M.loc[common, c] if win == "공통" else last_run(M[c])
                full = M[c].dropna()
                gaps = len(pd.period_range(full.index[0], full.index[-1], freq="M")) - len(full)
                amt = 100_000 * final_amt(s.to_numpy())[0]
                rows.append(dict(판본=hset, C_P앞잇기=fill, 구간=win, 운용사=m, 열=c, 시작=s.index[0].strftime("%Y-%m"), 끝=s.index[-1].strftime("%Y-%m"),
                                 개월=len(s), 전체빈달=gaps, **l1_stats(s), 적립금액_원=amt, 납입총액_원=100_000 * len(s), 금액_납입배수=amt / (100_000 * len(s))))
L1 = csv(pd.DataFrame(rows), "L1_real_nav_stats.csv")
show = L1.assign(연수익pct=L1.ann_ret * 100, 변동성pct=L1.ann_vol * 100, 최대낙폭pct=L1.mdd * 100).drop(columns=["ann_ret", "ann_vol", "mdd"])
print(show[(show.판본 == "UH") & (show.C_P앞잇기 == "없음")].round(2).to_string(index=False))""")
code(r"""print(show[~((show.판본 == "UH") & (show.C_P앞잇기 == "없음"))].round(2).to_string(index=False))""")
md("""### 1-b. 공통 구간 보충 (문서 단계 추가, 감사 MEDIUM-1)
- 공통 구간에서 각 계열의 최대낙폭 고점 달과 바닥 달(`L1_common_trough.csv`).
- 쌍별 월 수익 차(앞 − 뒤)의 평균, 표준편차, t = 평균 ÷ (표준편차/√개월)(`L1_common_pair_t.csv`). 기존 표의 숫자는 그대로다.""")
code(r"""tr, pt = [], []
for hset, mp in SETS.items():
    for fill in ("없음", "있음"):
        cols = {m: (f"{c}_fillCP" if fill == "있음" and f"{c}_fillCP" in M else c) for m, c in mp.items()}
        Mc = M[list(cols.values())].dropna()
        for m, c in cols.items():
            lvl = (1 + Mc[c]).cumprod(); dd = lvl / lvl.cummax() - 1; b_ = dd.idxmin()
            tr.append(dict(판본=hset, C_P앞잇기=fill, 운용사=m, 열=c, 시작=Mc.index[0].strftime("%Y-%m"), 끝=Mc.index[-1].strftime("%Y-%m"),
                           최대낙폭_pct=dd.min() * 100, 고점_달=lvl.loc[:b_].idxmax().strftime("%Y-%m"), 바닥_달=b_.strftime("%Y-%m"), 바닥달_월수익_pct=Mc.loc[b_, c] * 100))
        for a, b in PAIRS:
            x = Mc[cols[a]] - Mc[cols[b]]
            pt.append(dict(판본=hset, C_P앞잇기=fill, 쌍=f"{a}/{b}", 개월=len(x), 월차_평균_pct=x.mean() * 100, 월차_표준편차_pct=x.std(ddof=1) * 100,
                           t=x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))))
TR = csv(pd.DataFrame(tr), "L1_common_trough.csv"); PT = csv(pd.DataFrame(pt), "L1_common_pair_t.csv")
print(TR.round(2).to_string(index=False)); print()
print(PT.round(3).to_string(index=False)); print()
print("판본·C-P 잇기별 쌍 |t| 최대:", PT.groupby(["판본", "C_P앞잇기"]).t.apply(lambda s: round(s.abs().max(), 3)).to_dict())""")

md("""## 2. 층2 입력 — 지수·글라이드·보수
- 지수: `C2_components_monthly.csv`의 `stk`(= 0.152·KOSPI200 TR + 0.848·French Developed USD × 원/달러, UH)와 `bd`(국고채 TR), 2004-07~2026-08(266개월). 물가 = `io.asset_series('cpi')`(실질 금액 표시용, 같은 경로의 비에는 영향 없음).
- 글라이드: 운용사별 공시 2055 위험자산 비중, 납입 t달(0~359)의 잔여기간 = −30 + t/12년, 공시 점 사이 직선 보간(`glide_w`).
- 보수: 운용사별 C-Pe 단계표, 달력 연도 = 2026 + ⌊t/12⌋(`fee_pct`), 월 = 연÷12. 총보수 주, 합성총보수 병기.
- **달력 1년 어긋남(감사 MEDIUM-2):** 2055 펀드에서 2026년은 잔여 −29년이다. 위 처리에서는 같은 달의 글라이드 위치(t = 0 → 잔여 −30 = 2025년)가 보수 단계(2026년)보다 1년 이르다. 이 방식의 근거는 적혀 있지 않다. 글라이드를 −29 + t/12로 맞춘 판은 4절 끝 민감도 열(`L2b_sens_glide_align.csv`)에 둔다. 주 결과는 그대로 −30 + t/12다.
- **보간 근사(감사 MEDIUM-6):** 신한·삼성 공시 곡선은 5년 점 사이가 직선이 아니다(신한은 목표 직전에 가파르게 떨어지는 오목 곡선). 직선 보간은 신한 2052~2054년 비중을 실제 차트보다 1.6~2.0%p 낮게 둔다. 감사자가 차트를 디지타이즈한 연 단위 곡선을 쓰면 KB/신한 중앙값(블록 1, 총보수)은 1.2034 → 1.1924였다(감사 `audit\\sens.py`; 디지타이즈 값은 원자료 파일에 없어 이 노트북에서 다시 계산하지 않는다). 방향은 달력 맞춤(+0.012)과 반대다.
- PW 블록 = `pilot7.pw_block(stk − bd)`, 같은 표본. `pilot7.pw_block`은 원값이 1보다 작으면 하한 1을 적용한다. 원값(stationary·circular)은 `pw_block.csv`의 새 열에 남긴다. 원값이 1보다 작으면 PW 판은 블록 1(독립 추출)과 같은 seed·같은 함수라 **경로가 완전히 같고**, 실제로 다른 블록은 1과 12의 두 가지다.
- `pw_block.csv`의 `auditor_value_2004_07` = 1.00은 생성기에 적은 문자 상수다(계산값이 아님, 감사 MEDIUM-3).""")
code(r"""C = pd.read_csv(INP / "C2_components_monthly.csv", index_col=0, parse_dates=True)
cpi = io.asset_series("cpi").resample("ME").last().pct_change(fill_method=None)
X = pd.DataFrame({"stk": C.stk, "bd": C.bd, "cpi": cpi}).loc["2004-07":"2026-08"]
assert X.notna().all().all() and len(X) == 266, (len(X), X.isna().sum())
FT = fee_table(); t = np.arange(T)
W = {m: glide_w(-30 + t / 12, m) for m in MGRS}
FEE = {k: {m: fee_pct(m, 2026 + t // 12, col=col, F=FT) / 1200 for m in MGRS} for k, col in FEECOL.items()}
GF = pd.DataFrame({"t": t, "age": 30 + t / 12, "fee_year": 2026 + t // 12, **{f"w_{m}": W[m] for m in MGRS},
                   **{f"fee_{k}_{m}_pctpa": FEE[k][m] * 1200 for k in FEECOL for m in MGRS}})
csv(GF, "L2_inputs_glide_fee_by_month.csv")
print(GF.iloc[[0, 120, 168, 228, 265, 359]].round(4).T.to_string())
PW = P7.pw_block(X.stk - X.bd)
from arch.bootstrap import optimal_block_length
OBL = optimal_block_length((X.stk - X.bd).to_numpy()); PW_RAW, PW_CIRC = float(OBL["stationary"].iloc[0]), float(OBL["circular"].iloc[0])
assert PW == max(1.0, PW_RAW)
csv(pd.DataFrame([dict(series="stk − bd", sample="2004-07~2026-08", n=len(X), pw_block=PW, auditor_value_2004_07=1.00,
                       pw_raw_stationary=PW_RAW, pw_raw_circular=PW_CIRC, 하한1_적용=PW_RAW < 1,
                       auditor_value_표기="생성기 문자 상수(계산값 아님)")]), "pw_block.csv")
print("PW 블록(stk − bd, 2004-07~):", round(PW, 4), "| 원값 stationary", round(PW_RAW, 4), "circular", round(PW_CIRC, 4), "| auditor_value_2004_07 = 1.00은 문자 상수")
BLOCKS = {"1": 1.0, "PW": PW, "12": 12.0}""")
code(r"""ex = (X.stk - X.bd) * 100
print("표본 조건(감사 HIGH-1): 2004-07~2026-08 주식묶음 − 국고채 TR 월 수익 차 산술평균 × 12 = 연 %.2f%%p, 표준오차 = 월 표준편차 × 12 / √개월 = %.2f%%p (%d개월)"
      % (ex.mean() * 12, ex.std(ddof=1) * 12 / np.sqrt(len(ex)), len(ex)))""")

md("""## 3. 층2 (a) — 실제 역사 경로 1개 (2004-07~2026-08 = 266개월, 잔여 30년 → 약 7.8년)
2004-07에 30세로 시작해 2026-08까지 매달 같은 금액. 운용사별 금액(납입 총액 배수)과 쌍별 금액 비·분해.""")
code(r"""def run_combos(SK, BD, n):
    '''25개 (글라이드 g, 보수 f) 조합의 ln 최종 금액. 앞 n개월만.'''
    return {k: {(g, f): np.log(final_amt(W[g][:n] * SK[:, :n] + (1 - W[g][:n]) * BD[:, :n] - FEE[k][f][:n])) for g in MGRS for f in MGRS} for k in FEECOL}

def pair_rows(Lk, extra, stats):
    rows = []
    for a, b in PAIRS:
        D = decomp(Lk, a, b); r = np.exp(D["T"])
        rows.append(dict(**extra, 쌍=f"{a}/{b}", **stats(r), **{f"{k}_중앙_logpct": np.median(v) * 100 for k, v in D.items()},
                         **{f"{k}_평균_logpct": np.mean(v) * 100 for k, v in D.items() if k in ("T", "S_F", "S_G")}))
    return rows

n = len(X); SKh, BDh = X.stk.to_numpy()[None, :], X.bd.to_numpy()[None, :]
LH = run_combos(SKh, BDh, n); cpi_h = np.prod(1 + X.cpi.to_numpy())
A_m = csv(pd.DataFrame([dict(보수=k, 운용사=m, 개월=n, 끝_나이=30 + n / 12, 금액_납입배수=np.exp(LH[k][m, m][0]) / n, 실질금액_납입배수=np.exp(LH[k][m, m][0]) / cpi_h / n)
                        for k in FEECOL for m in MGRS]), "L2a_hist_by_manager.csv")
A_p = csv(pd.DataFrame(sum([pair_rows(LH[k], dict(보수=k), lambda r: dict(금액비=r[0])) for k in FEECOL], [])).filter(regex="^(?!.*평균)"), "L2a_hist_pairs.csv")   # 경로 1개: 평균 = 중앙
print(A_m.round(4).to_string(index=False)); print()
print(A_p.round(4).to_string(index=False))""")

md("""## 4. 층2 (b) — 블록 부트스트랩 공통 경로 (seed 20261008, N = 10,000, 360개월, 블록 {1, PW, 12})
같은 경로(같은 블록 인덱스로 stk·bd·cpi를 함께 뽑음)를 모든 운용사·모든 (글라이드, 보수) 조합에 쓴다. 쌍별 최종 금액 비(앞 ÷ 뒤)의 중앙값·P5·P95.
분해(로그 %): T = ln 비, 순서1 = 글라이드 먼저(G1, 그다음 보수 F1), 순서2 = 보수 먼저(F2, 그다음 글라이드 G2), Shapley S_F = (F1+F2)/2, S_G = (G1+G2)/2. 중앙값은 더해지지 않으므로 평균도 적는다(평균은 S_F + S_G = T). (문서 단계 정정, 감사 LOW-1: 이전 판의 순서 이름표가 반대였다. 열 값과 Shapley 값은 같다.)""")
code(r"""pq = lambda r: dict(비_중앙=np.median(r), 비_P5=np.quantile(r, .05), 비_P95=np.quantile(r, .95))
B_m, B_p = [], []
for bn, b in BLOCKS.items():
    SK, BD, CP = paired_resample_paths([X.stk, X.bd, X.cpi], NP, T, b, SEED)
    assert SK.shape == (NP, T)
    Lb = run_combos(SK, BD, T); cp = np.prod(1 + CP, axis=1)
    for k in FEECOL:
        for m in MGRS:
            v = np.exp(Lb[k][m, m]) / T; vr = v / cp
            B_m.append(dict(블록=bn, 평균블록=b, 보수=k, 운용사=m, 금액배수_중앙=np.median(v), 금액배수_P5=np.quantile(v, .05), 금액배수_P95=np.quantile(v, .95),
                            실질배수_중앙=np.median(vr), 실질배수_P5=np.quantile(vr, .05), 실질배수_P95=np.quantile(vr, .95)))
        B_p += pair_rows(Lb[k], dict(블록=bn, 평균블록=b, 보수=k), pq)
B_m = csv(pd.DataFrame(B_m), "L2b_boot_by_manager.csv"); B_p = csv(pd.DataFrame(B_p), "L2b_boot_pairs.csv")
print(B_m.round(3).to_string(index=False))""")
code(r"""print("참고선(판정 아님): 비 1.011 / 0.989(= 1/1.011)")
print(B_p[B_p.보수 == "총보수"][["블록", "평균블록", "쌍", "비_중앙", "비_P5", "비_P95"]].round(4).to_string(index=False))""")
code(r"""print(B_p[B_p.보수 == "합성총보수"][["블록", "평균블록", "쌍", "비_중앙", "비_P5", "비_P95"]].round(4).to_string(index=False))""")
md("### 보수 몫과 글라이드 몫 (로그 %, 중앙값과 평균)")
code(r"""cols = ["블록", "보수", "쌍", "T_중앙_logpct", "F1_중앙_logpct", "G1_중앙_logpct", "F2_중앙_logpct", "G2_중앙_logpct", "S_F_중앙_logpct", "S_G_중앙_logpct", "T_평균_logpct", "S_F_평균_logpct", "S_G_평균_logpct"]
print(B_p[cols].round(3).to_string(index=False))""")
code(r"""import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
fig, ax = plt.subplots(figsize=(9, 3.6), dpi=80)
for i, (bn, g) in enumerate(B_p[B_p.보수 == "총보수"].groupby("블록", sort=False)):
    x = np.arange(len(g)) + (i - 1) * 0.25
    ax.errorbar(x, g.비_중앙, yerr=[g.비_중앙 - g.비_P5, g.비_P95 - g.비_중앙], fmt="o", ms=3, capsize=2, label=f"블록 {bn}")
for y in (X_REF, 1 / X_REF):
    ax.axhline(y, ls="--", lw=0.8, c="gray")
ax.axhline(1, lw=0.6, c="k"); ax.set_xticks(range(len(PAIRS))); ax.set_xticklabels([f"{a}/{b}" for a, b in PAIRS], rotation=30, fontsize=8)
ax.set_ylabel("최종 금액 비"); ax.set_title("층2 (b) 총보수: 중앙값과 P5–P95 (점선 = 참고선 1.011·1/1.011, X 1.10% = 재결정 전 후보값(DL 132))", fontsize=9)
ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(OUT / "L2b_pairs_total_fee.png"); plt.show()""")
md("""### 민감도 열 — 글라이드를 보수 달력에 맞춘 판 (문서 단계 추가, 감사 MEDIUM-2)
주 결과(글라이드 잔여 −30 + t/12)는 그대로 두고, 글라이드만 −29 + t/12(2026년 = 잔여 −29)로 바꾼 판을 같은 seed·같은 경로(블록 1·12)로 다시 계산한다. 보수 달력(2026 + ⌊t/12⌋)과 지수 경로는 같다. 쌍별 금액 비(자기 글라이드 × 자기 보수끼리)만 낸다(`L2b_sens_glide_align.csv`). PW 판은 블록 1과 같은 경로라 따로 계산하지 않는다.""")
code(r"""WA = {m: glide_w(-29 + t / 12, m) for m in MGRS}
SA = []
for bn, b in (("1", 1.0), ("12", 12.0)):
    SK, BD, CP = paired_resample_paths([X.stk, X.bd, X.cpi], NP, T, b, SEED)
    for k in FEECOL:
        L0 = {m: np.log(final_amt(W[m] * SK + (1 - W[m]) * BD - FEE[k][m])) for m in MGRS}
        LA = {m: np.log(final_amt(WA[m] * SK + (1 - WA[m]) * BD - FEE[k][m])) for m in MGRS}
        for a, b_ in PAIRS:
            r0, r1 = np.exp(L0[a] - L0[b_]), np.exp(LA[a] - LA[b_])
            ref = B_p[(B_p.블록 == bn) & (B_p.보수 == k) & (B_p.쌍 == f"{a}/{b_}")].비_중앙.iloc[0]
            assert np.isclose(np.median(r0), ref, rtol=0, atol=1e-12)          # 주 결과 재현
            SA.append(dict(블록=bn, 보수=k, 쌍=f"{a}/{b_}", 주_글라이드="−30 + t/12", 비_중앙_주=np.median(r0),
                           맞춤_글라이드="−29 + t/12", 비_중앙_맞춤=np.median(r1), 비_P5_맞춤=np.quantile(r1, .05), 비_P95_맞춤=np.quantile(r1, .95),
                           중앙_차=np.median(r1) - np.median(r0)))
SA = csv(pd.DataFrame(SA), "L2b_sens_glide_align.csv")
print(SA.round(4).to_string(index=False))""")

md("""## 5. 한계 (명세 그대로 + 문서 단계 추가)
- 층1: 실제 구간이 짧다(5개 공통 2024-08~). 실제 수익에는 실제 보수·실제 운용·환 효과가 함께 들어 있어 나누지 않는다. 공통 구간 최대낙폭의 바닥 달과 쌍별 t값은 1-b 표에 있다.
- 층2와 실제의 대조(감사 HIGH-2 제안 문장의 틀, 숫자는 아래 출력 = 현재 `C2_check_index_vs_real_overlap.csv` 시차 0·총보수): 실제 C-Pe 기준가와 '공시 글라이드 × 지수 − 총보수' 시뮬레이션을 겹치는 달(운용사별 25~78개월)로 대조한 월 상관·추적오차·평균 차(실제 − 시뮬레이션)는 아래 표와 같다. 평균 차는 운용사별로 흩어져 있고, 가용 평균 UH판의 평균 차는 |t| < 2로 0과 구별되지 않는다(아래 출력, assert). 그래서 층2 숫자는 '공시대로 운용하고 비용이 공시대로라면'의 차이이고, 실제 운용사 간 차이의 크기나 순서를 말해 주지 않는다.
- 정정 메모: 감사 시점(이전 판 한계 문장)의 avg_UH 평균 차 −2.6%p는 헤지판 삼성_H가 섞인 값이었다. 데이터 감사 H-1 정정(`C_real_20261017\\inputs\\README.md` '정정 2026-10-17') 뒤 avg_UH는 KB_UH·신한·미래에셋·한국투자_UH 4계열 평균이다. 이 노트북의 층1 결과는 avg 열을 쓰지 않아 정정 전후가 같다.
- 층2 표본은 2004-07~2026-08(266개월) 하나다. 360개월 경로는 블록을 이어 붙여 만들고(순환), (a) 역사 경로는 잔여 약 7.8년에서 끝난다. 이 표본의 주식묶음 − 국고채 TR 차(연율)와 표준오차는 2절 끝 출력에 있고, 부트스트랩은 이 표본을 다시 뽑는다.
- 공시 '위험자산'은 모두 주식묶음, 나머지(안전자산)는 전부 국고채 TR로 처리했다. 공시 정의의 안전자산(현금성자산·채무증권, 회사채 포함)과 다르다. 해외는 UH만. 국내 몫 w = 0.152는 2025~26 급등을 포함한 추정값이고, 이를 2004~ 경로에 그대로 쓴다(DL A-2, 숫자 영향 미측정).
- 보수 단계표는 2026 현행 투자설명서이며 2004~2026 역사 경로(L2a)와 30년 미래에 그대로 쓴다. 삼성의 2040 이후 '기타비용 실비'는 0으로 들어간다. 합성총보수 첫 단계는 기타비용을 포함하고 이후 단계는 포함하지 않는다(fee_pclass 표 그대로).
- 글라이드-보수 달력 1년 어긋남(2절, 4절 끝 민감도 열), 신한·삼성 직선 보간 근사(2절, 감사 수치)가 있다. **미래에셋 글라이드는 투자설명서 원문 쪽과 대조하지 못했다(감사 MEDIUM-7, 미확인).** 나머지 4사는 감사가 원문 쪽과 대조했다.
- 표본 선정: 5대는 현재 규모로 고른 운용사이고, 운용사마다 2055 계열 하나다. 층1은 현존 클래스만 있다. 결과는 '이 5개 펀드'의 기술이며, 같은 운용사의 다른 TDF 계열은 들어 있지 않다. 운용사 일반으로 넓혀 읽지 않는다.
- 판정 도구(바깥 부트스트랩·Bonferroni·블록 관문)는 쓰지 않았다.""")
code(r"""ov = pd.read_csv(INP / "C2_check_index_vs_real_overlap.csv", encoding="utf-8-sig")
ov = ov[(ov.nav_lag_bdays == 0) & ov.index_model.str.endswith("total")].copy()
ov["평균차_표준오차"] = ov.te_pctpa / np.sqrt(ov.n / 12); ov["t"] = ov.mean_diff_pctpa / ov.평균차_표준오차
print("실제 − 시뮬레이션(시차 0, 총보수, %p/년):"); print(ov[["real", "start", "end", "n", "corr", "mean_diff_pctpa", "te_pctpa", "평균차_표준오차", "t"]].round(3).to_string(index=False))
one = ov[ov.real.isin(["KB_UH", "신한", "미래에셋", "한국투자_UH", "삼성_H"])]
print("UH판 운용사별(삼성은 H판만): 상관 %.2f~%.2f, 추적오차 %.1f~%.1f%%/년, 평균 차 %.2f~%+.2f%%p/년, 개월 %d~%d"
      % (one["corr"].min(), one["corr"].max(), one.te_pctpa.min(), one.te_pctpa.max(), one.mean_diff_pctpa.min(), one.mean_diff_pctpa.max(), one.n.min(), one.n.max()))
au = ov[ov.real == "avg_UH"].iloc[0]; assert abs(au.t) < 2
print("avg_UH: 평균 차 %+.2f%%p/년, 표준오차 %.2f%%p, t = %.2f (%d개월)" % (au.mean_diff_pctpa, au.평균차_표준오차, au.t, au.n))""")

nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
os.environ["PYTHONPATH"] = str(ROOT / "src")
NotebookClient(nb, timeout=7200, kernel_name="python3", resources={"metadata": {"path": str(NB_PATH.parent)}}).execute()
rr.save_executed(nb, NB_PATH)
NBM = OUTD / "nb_meta"; NBM.mkdir(parents=True, exist_ok=True)
extra = "seed=20261008\nN=10000\nT=360\nblocks=1,PW,12\n" + "".join(f"input {p} sha256={rr.raw_sha256(p)}\n" for p in INPUTS + [ROOT / "notebooks/pilot9/_build_C_real_inputs.py"]) \
        + "".join(f"result {p.name} sha256={rr.raw_sha256(p)}\n" for p in sorted(OUTD.glob("*.csv")))   # 결과 CSV 해시(문서 단계 추가)
rr.write_run_meta(NBM, Path(__file__), ["src/pension_lab/pilot9.py", "src/pension_lab/pilot7.py", "src/pension_lab/bootstrap.py",
                                         "notebooks/pilot9/_build_C_real_inputs.py"], extra)
print("실행완료 저장:", NB_PATH, NB_PATH.stat().st_size, "bytes")
