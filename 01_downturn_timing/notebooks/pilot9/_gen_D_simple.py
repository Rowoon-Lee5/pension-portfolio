# -*- coding: utf-8 -*-
"""D_simple_20261017.ipynb 생성기 — pilot9 D 간단 테스트(하락장에 위험자산 비중을 잠깐 올렸다 되돌리기).
명세 = $PENSION_DATA_ROOT/results/pilot9_20261013/D_simple_20261017/SPEC_D_simple_20261017.md + DECISION_LOG 2026-10-17 'pilot9 D 간단 테스트 명세(회원 결정 3건)'(다르면 DL 우선).
탐색용 기술만 — 판정 없음. 실행: (cmd) set "PYTHONPATH=" 뒤 set PYTHONIOENCODING=utf-8 & python notebooks\\pilot9\\_gen_D_simple.py
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pension_lab import runrecord as rr, paths  # noqa: E402

NB_PATH = ROOT / "notebooks" / "pilot9" / "D_simple_20261017.ipynb"
OUTD = (paths.DATA_ROOT / "results/pilot9_20261013/D_simple_20261017")
INP = (paths.DATA_ROOT / "results/pilot9_20261013/C_real_20261017/inputs")
FTD = (paths.DATA_ROOT / "raw/fund_tdf")
INPUTS = [INP / "C2_components_monthly.csv", INP / "C2_glide_by_remaining_years.csv", INP / "C3_dd_events.csv",
          (paths.DATA_ROOT / "raw/kr_bond_pre2004_20261017/kis_monthly_2001_clean.csv"),
          (paths.DATA_ROOT / "processed/multicountry_returns_20261017.csv"),
          FTD / "glidepath_disclosed_prospectus.csv", FTD / "glidepath_disclosed_web_kr_others.csv",
          (paths.DATA_ROOT / "results/pilot9_20261013/fee_pclass_20261016/pclass_fee_table.csv"),
          (paths.DATA_ROOT / "raw/equity_global/french/F-F_Research_Data_Factors.csv"),
          *sorted((paths.DATA_ROOT / "raw/equity_global/french_intl").glob("*.Dat")),
          (paths.DATA_ROOT / "raw/macro_fx_vol/ecos_cpi_long.csv")]
nb = nbf.v4.new_notebook(); cells = []
def md(s): cells.append(nbf.v4.new_markdown_cell(s))
def code(s): cells.append(nbf.v4.new_code_cell(s))

md("""# pilot9 D 간단 테스트: 하락장에 위험자산 비중을 잠깐 올렸다 되돌리면 60세 금액이 어떻게 달라지나 (2026-10-17)
**명세.** `D_simple_20261017\\SPEC_D_simple_20261017.md` + `docs/DECISION_LOG.md` 2026-10-17 'pilot9 D 간단 테스트 명세(회원 결정 3건)'. 둘이 다르면 DL 회원 결정이 우선이다.
- 회원 결정 ① 다국가 보충을 넣는다: C와 같은 방식(각국 저축자, 자기 나라 위험자산(주식) 총수익·자기 나라 국채 총수익, 현지통화), Swinkels 9개국, 위험자산 = French 국가별 **현지통화판**(없으면 ⬜, 달러판 대체 금지), 신호 = 자국 위험자산 −20%(18칸 모두 계산, 표는 −20%를 앞에 둔다).
- 회원 결정 ② 한국 표본 KR-a(2004-07~)와 KR-b(2001-02~, 채권 앞 41개월 = 한경 KIS 국고채권 총수익 실측) 둘 다 보고. 새 자료 감사에서 KIS HIGH 0건.
- 회원 결정 ③ 다른 논문 규칙 비교는 본 분석으로 미룬다.

**성격.** 탐색용 기술 — 표와 숫자만 둔다. 판정 문장은 쓰지 않는다. d의 P5~P95는 '경로가 놓이는 범위'이고 신뢰구간이 아니다. ΔP5·ΔCVaR는 점값이다.

**규칙.** 코스피 가격이 고점 대비 문턱(−10·−20·−30%) 이하로 떨어진 것이 확인된 달 t(월말, 고점 뒤 2개월 이상, 바닥 대비 +20% 반등 뒤 다시 셈)의 **다음 달(t+1)부터** 위험자산 비중 = 글라이드 + Δ(+5·+10·+15%p, 상한 100%). 복귀: ⓐ 그 사건의 판정 당시 고점을 다시 넘은 달의 다음 달 ⓑ 12개월 뒤. 사건이 겹치면 Δ를 더하지 않고 복귀 기준을 최근 사건으로 바꾼다.
**결과변수.** 경로마다 d = ln(W_규칙 / W_기준), W = 360개월 뒤 실질 최종 금액(같은 경로·같은 납입·같은 보수).
**d가 담는 것(감사 M-1).** d에는 '추가 비중 × 켜진 기간' 효과가 들어 있고, 이 노트북의 주 표는 하락장 시점 효과와 분리하지 않는다. 같은 평균 추가 비중을 하락장과 상관없이 매달 얹은 위약(placebo) 비교는 6절(`D_placebo.csv`)에 둔다.
**문서 단계 수정(2026-10-17).** 감사(`D_simple_20261017\\audit\\AUDIT_D_simple.md`) MEDIUM·LOW와 새 자료 감사의 코스피·KIS 항목 가운데 문구와 추가 계산을 반영했다. 기존 결과 CSV의 칸은 바꾸지 않았고, 새 파일(`D_placebo.csv`, `D_overlap_keep_sens.csv`, `D_mc_simul_events.csv`, `D_grid_range.csv`)만 더했다.""")

code(r"""import sys, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path.cwd()))                          # notebooks/pilot9 (입력 생성기 함수 import)
from _build_C_real_inputs import glide_w, fee_pct, fee_table
from pension_lab import pilot7 as P7, pilot9 as P9, io, paths
from pension_lab.bootstrap import paired_resample_paths
from arch.bootstrap import optimal_block_length
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 400)
OUT = P9.OUT / "D_simple_20261017"; OUT.mkdir(parents=True, exist_ok=True)
INP = P9.OUT / "C_real_20261017" / "inputs"
SEED, NP, T = P7.SEED, P7.NP, 360                            # seed 20261008, N 10,000, 30세→60세 360개월
MGRS = ["KB", "미래에셋", "삼성", "신한", "한국투자"]
DELTAS = (0.05, 0.10, 0.15); EXITS = ("peak", "1y"); EXN = {"peak": "전고점 회복", "1y": "1년"}
CELLS = [(th, P9.REARM, ex, dl) for th in P9.DD_GRID for ex in EXITS for dl in DELTAS] + \
        [(-0.20, ra, ex, dl) for ra in P9.REARM_SENS for ex in EXITS for dl in DELTAS]          # 18칸 + 재무장 민감도(−20%, 6칸 × 2)
COMBOS = sorted({(th, ra) for th, ra, _, _ in CELLS}, key=str)
GROWTH = {"0%": 0.0, "3.4%": 0.034}                            # DL 114: 연 명목임금 상승률 → 해마다 한 번 올림
csv = lambda df, name: (df.to_csv(OUT / name, index=False, encoding="utf-8-sig"), df)[1]
t = np.arange(T); RY = -30 + t / 12                            # 잔여기간(년)
FEE_YEAR = 2025 + t // 12                                      # 보수 달력 = ⌊2055 + 잔여기간⌋(글라이드와 같은 시계, A 감사 M2), 2026 이전은 첫 단계
contrib = lambda g: (1 + g) ** (t // 12)

def wealth(Rt, c):
    '''Rt (개월, 경로) 월 수익. 매달 초 c[t] 납입 → 그 달 수익. 마지막 달 말 잔액(명목).'''
    V = np.zeros(Rt.shape[1])
    for k in range(Rt.shape[0]):
        V = (V + c[k]) * (1 + Rt[k])
    return V

def masks(K, start=0, combos=COMBOS):
    '''K (경로, 개월) 신호 수익 → {(th, rearm, exit): 켜짐 (개월, 경로)}, 작동 기록 {(th, rearm, exit): (사건 수, 겹침 수) 경로별}.'''
    P_, n = K.shape; M, REC = {}, {}
    for th, ra in combos:
        for ex in EXITS:
            on = np.zeros((P_, n), bool); ne = np.zeros(P_, int); ov = np.zeros(P_, int)
            M[th, ra, ex] = (on, ne, ov)
        for p in range(P_):
            ev = P9.dd_events(K[p], th, rearm=ra)                 # 두 복귀 방식에 한 번만
            for ex in EXITS:
                on, ne, ov = M[th, ra, ex]; on[p], ne[p], ov[p] = P9.dip_on(K[p], th, ex, ra, start, ev)
        for ex in EXITS:
            on, ne, ov = M[th, ra, ex]; M[th, ra, ex] = on.T.copy(); REC[th, ra, ex] = (ne, ov)
    return M, REC

cvar5 = lambda x: np.sort(x)[:int(round(0.05 * len(x)))].mean()   # 자기 하위 5% 경로 평균(N=10,000 → 500개)

def evaluate(SKt, BDt, cpi_cum, M, REC, G, FEE, meta, cells=CELLS):
    '''SKt·BDt (개월, 경로). G 글라이드(개월). FEE {이름: 월 보수(개월)}. 경로 1개면 비 그대로.'''
    n, P_ = SKt.shape; rows = []
    for fk, f in FEE.items():
        for gk, g in GROWTH.items():
            c = contrib(g)[:n]; csum = c.sum()
            Wb = wealth(G[:n, None] * SKt + (1 - G[:n, None]) * BDt - f[:n, None], c); rb = Wb / cpi_cum / csum
            for th, ra, ex, dl in cells:
                on = M[th, ra, ex]; raw = G[:n, None] + dl * on; w = np.minimum(raw, 1.0)
                Wr = wealth(w * SKt + (1 - w) * BDt - f[:n, None], c); rr_ = Wr / cpi_cum / csum; d = np.log(Wr / Wb)
                ne, ov = REC[th, ra, ex]
                r = dict(**meta, 보수=fk, 납입증가=gk, 문턱=th, 재무장=P9.rearm_name(ra), 복귀=EXN[ex], 증액=dl,
                         사건수_평균=ne.mean(), 사건1개이상_비율=(ne > 0).mean(), 켜진개월_평균=on.sum(0).mean(), 겹침경로수=int((ov > 0).sum()),
                         상한닿은_경로월=int((raw > 1).sum()))
                if P_ == 1:
                    r.update(금액비_규칙대기준=float(np.exp(d[0])), d=float(d[0]), 기준_실질배수=float(rb[0]), 규칙_실질배수=float(rr_[0]))
                else:
                    r.update(d_중앙=np.median(d), d_P5=np.quantile(d, .05), d_P95=np.quantile(d, .95), P_d양수=(d > 0).mean(), P_d영=(d == 0).mean(),
                             기준배수_중앙=np.median(rb), 기준배수_P5=np.quantile(rb, .05), 기준배수_CVaR5=cvar5(rb),
                             규칙배수_중앙=np.median(rr_), 규칙배수_P5=np.quantile(rr_, .05), 규칙배수_CVaR5=cvar5(rr_),
                             dP5=np.log(np.quantile(rr_, .05)) - np.log(np.quantile(rb, .05)), dCVaR=np.log(cvar5(rr_)) - np.log(cvar5(rb)))
                rows.append(r)
    return rows

PL_CELLS = [(th, P9.REARM, ex, dl) for th in P9.DD_GRID for ex in EXITS for dl in DELTAS]   # 위약 비교: 주 18칸(재무장 20%), 총보수·납입 0%

def placebo(SKt, BDt, M, G, f, meta, cells=PL_CELLS):
    '''위약(감사 M-1, audit_recalc_2·3과 같은 정의): 규칙 켜짐의 '월별 경로 평균 × Δ'를 사건과 무관하게 모든 경로에 매달 똑같이 얹은 정적 기울기.
    같은 경로·같은 보수·납입 0%. d_위약 = ln(W_위약/W_기준). 규칙 d와 경로별로 짝지어 비교한다.'''
    n = SKt.shape[0]; c = contrib(0.0)[:n]; fm = f[:n, None]
    Wb = wealth(G[:n, None] * SKt + (1 - G[:n, None]) * BDt - fm, c); rows = []
    for th, ra, ex, dl in cells:
        on = M[th, ra, ex]; w = np.minimum(G[:n, None] + dl * on, 1.0); gp = np.minimum(G[:n] + dl * on.mean(1), 1.0)[:, None]
        d = np.log(wealth(w * SKt + (1 - w) * BDt - fm, c) / Wb); dp = np.log(wealth(gp * SKt + (1 - gp) * BDt - fm, c) / Wb)
        rows.append(dict(**meta, 보수="총보수", 납입증가="0%", 문턱=th, 재무장=P9.rearm_name(ra), 복귀=EXN[ex], 증액=dl, 켜진개월_평균=on.sum(0).mean(),
                         평균추가비중_pctp=dl * on.mean() * 100, 규칙_d_중앙=np.median(d), 위약_d_중앙=np.median(dp), 위약_d_P5=np.quantile(dp, .05),
                         위약_d_P95=np.quantile(dp, .95), 규칙빼기위약_중앙=np.median(d - dp), P_규칙gt위약=(d > dp).mean()))
    return rows

def dip_on_keep(K, th, exit, rearm=P9.REARM, start=0, ev=None):
    '''겹침 처리 민감도(감사 M-3, audit_recalc_2 'keep'과 같은 정의): 켜진 동안 새 사건이 확인되면 Δ는 더하지 않고, 복귀는 이전 사건과 새 사건 중 늦은 쪽.
    그 밖은 P9.dip_on과 같다(주 결과 = 최근 사건 기준).'''
    n = len(K); on = np.zeros(n, bool); end0 = -1
    for c, rc in [e for e in (P9.dd_events(K, th, rearm=rearm) if ev is None else ev) if e[0] >= start]:
        end = max(min(c + 12, n - 1) if exit == "1y" else (n - 1 if rc is None else rc), end0)
        on[c + 1:end + 1] = True; end0 = end
    return on""")

md("""## 0. 자기 점검 (합성 자료)
결과를 내기 전에 답을 아는 가짜 자료로 확인한다. 하나라도 틀리면 멈춘다(`assert`).""")
code(r"""rng = np.random.default_rng(0); Pn = 300
SK0, BD0 = rng.normal(0.006, 0.045, (Pn, T)), rng.normal(0.003, 0.01, (Pn, T)); K0 = rng.normal(0.004, 0.07, (Pn, T))
G0 = glide_w(RY); F0 = {"총보수": np.full(T, 0.0078 / 12)}; one = np.ones(Pn)
M0, R0 = masks(K0); chk = []
def d_of(SK, BD, M, R, cells):
    rows = evaluate(SK.T.copy(), BD.T.copy(), one, M, R, G0, F0, {}, cells)
    return rows
# 1) Δ = 0 → d = 0
r = d_of(SK0, BD0, M0, R0, [(-0.20, P9.REARM, ex, 0.0) for ex in EXITS])
chk.append(dict(점검="Δ = 0이면 모든 경로 d = 0", 기대=0.0, 결과=max(abs(x["d_P5"]) + abs(x["d_P95"]) for x in r), 통과=all(x["P_d영"] == 1.0 for x in r)))
# 2) 사건 없는 경로(신호 매달 +1%) → d = 0
Mn, Rn = masks(np.full((Pn, T), 0.01))
r = d_of(SK0, BD0, Mn, Rn, [c for c in CELLS])
chk.append(dict(점검="사건이 없으면 d = 0 (30칸 전부)", 기대=0.0, 결과=max(x["사건수_평균"] for x in r), 통과=all(x["P_d영"] == 1.0 and x["사건수_평균"] == 0 for x in r)))
# 3) stk = bd → d = 0(부동소수 오차 안)
r = d_of(SK0, SK0, M0, R0, CELLS)
mx = max(max(abs(x["d_P5"]), abs(x["d_P95"])) for x in r)
chk.append(dict(점검="위험자산 = 국채 수익이면 d = 0 (|d| < 1e-12)", 기대=0.0, 결과=mx, 통과=bool(mx < 1e-12)))
# 4) t월 수익은 t월까지의 비중에 쓰이지 않는다(룩어헤드 없음): t월 신호만 크게 바꿔도 0..t월 켜짐이 같다
bad = 0
for p in range(60):
    for tt in (5, 40, 100, 200, 300):
        for v in (-0.6, 0.6):
            K1 = K0[p].copy(); K1[tt] = v
            for th, ra in COMBOS:
                for ex in EXITS:
                    a, b = P9.dip_on(K0[p], th, ex, ra)[0], P9.dip_on(K1, th, ex, ra)[0]
                    bad += int(not np.array_equal(a[:tt + 1], b[:tt + 1]))
chk.append(dict(점검="t월 수익을 바꿔도 0..t월 비중이 같다(60경로×5시점×2값×10규칙)", 기대=0, 결과=bad, 통과=bad == 0))
# 5) 신호를 한 달 당겨 넣으면 결과가 달라진다(t+1 적용이 실제로 작동)
Ks = np.c_[K0[:, 1:], np.zeros(Pn)]; Ms, Rs = masks(Ks, combos=[(-0.20, P9.REARM)])
a = d_of(SK0, BD0, M0, R0, [(-0.20, P9.REARM, "peak", 0.10)])[0]; b = d_of(SK0, BD0, Ms, Rs, [(-0.20, P9.REARM, "peak", 0.10)])[0]
chk.append(dict(점검="신호 한 달 당김 → d 분포가 바뀐다", 기대="다름", 결과=f"{a['d_중앙']:.6f} vs {b['d_중앙']:.6f}", 통과=bool(a["d_중앙"] != b["d_중앙"])))
# 6) 손으로 푼 경로: 확인월 2 → 3월부터 켜짐, 회복월 5까지 켜짐, 6월 복귀 / 1년 = 정확히 12개월 / 확인월 당월은 글라이드
r6 = np.r_[0.0, -0.15, -0.10, 0.10, 0.10, 0.10, 0.05, np.zeros(13)]
on_pk, on_1y = P9.dip_on(r6, -0.20, "peak")[0], P9.dip_on(r6, -0.20, "1y")[0]
ok6 = on_pk.tolist()[:8] == [0, 0, 0, 1, 1, 1, 0, 0] and on_1y.sum() == 12 and on_1y[3:15].all() and not on_1y[2]
chk.append(dict(점검="손 계산 경로: 켜짐 3~5월(전고점), 3~14월(1년, 12개월), 확인월 2는 꺼짐", 기대=True, 결과=ok6, 통과=bool(ok6)))
# 7) 1년 복귀: 사건이 겹치지 않은 경로에서 켜진 개월 = 12 × 사건 수(끝이 잘리지 않은 경우)
on, ne, ov = M0[-0.20, P9.REARM, "1y"], *R0[-0.20, P9.REARM, "1y"]
last_c = np.array([max([c for c, _ in P9.dd_events(K0[p], -0.20, rearm=P9.REARM)] or [-99]) for p in range(Pn)])
sel = (ov == 0) & (ne > 0) & (last_c + 12 <= T - 1)
dev = int(np.abs(on.sum(0)[sel] - 12 * ne[sel]).max())
chk.append(dict(점검=f"1년 복귀 = 사건마다 정확히 12개월({int(sel.sum())}경로)", 기대=0, 결과=dev, 통과=dev == 0 and sel.sum() > 0))
# 8) 상한 100%: 글라이드 0.95 + 0.15 → 비중 최대 1, 상한 닿은 달 기록
w8, on8 = P9.dip_weights(r6, np.full(len(r6), 0.95), -0.20, 0.15, "peak")
chk.append(dict(점검="상한 100%: 0.95 + 0.15 → 1.00, 켜진 달 = 상한 닿은 달", 기대=1.0, 결과=float(w8.max()), 통과=bool(w8.max() == 1.0 and (w8[on8] == 1.0).all() and (w8[~on8] == 0.95).all())))
# 9) 실제 코스피 −20%·재무장 20% 확인월 = C3_dd_events.csv(KOSPI_px)
E = pd.read_csv(INP / "C3_dd_events.csv", encoding="utf-8-sig"); kos = pd.read_csv(INP / "C2_components_monthly.csv", index_col=0, parse_dates=True).kospi.dropna()
mine = [kos.index[c].strftime("%Y-%m") for c, _ in P9.dd_events(kos.to_numpy(), -0.20, rearm=P9.REARM)]
ref = E[E.series == "KOSPI_px"].confirm.tolist()
chk.append(dict(점검="실제 코스피 사건 날짜 = C3_dd_events.csv", 기대=";".join(ref), 결과=";".join(mine), 통과=mine == ref))
# 10) 수익 0이면 금액 = 납입 총액(증가 0%·3.4%)
ok10 = all(np.isclose(wealth(np.zeros((T, 1)), contrib(g))[0], contrib(g).sum()) for g in GROWTH.values())
chk.append(dict(점검="수익 0 → 금액 = 납입 총액(0%·3.4%)", 기대=True, 결과=ok10, 통과=bool(ok10)))
CHK = csv(pd.DataFrame(chk), "selfcheck.csv"); print(CHK.to_string()); assert CHK.통과.all()""")

md("""**자기 점검의 범위(감사 M-5).** #5(신호를 한 달 당기면 d가 다르다)는 어떤 변경이든 d를 바꾸므로 t+1 적용의 증거로는 약하다(룩어헤드 없음의 증거는 #4와 #6). #8(상한 100%)은 합성 자료에서만 유효하다. 실제 입력에서는 글라이드 최대 0.80 + Δ 최대 0.15 = 0.95라 상한에 닿을 수 없다. 겹침 처리를 검증하는 점검은 이 10개에 없고, 6절 겹침 민감도 셀에서 따로 확인한다.""")

md("""## 1. 자료
- 한국: `C2_components_monthly.csv`의 `stk`(위험자산 묶음 = 0.152·KOSPI200 TR + 0.848·French Developed USD × 원/달러, UH), `bd`(국고채 TR, 2004-07~), `kospi`(가격, 1980-02~). 물가 = `io.asset_series('cpi')`.
- KR-b: 2001-02~2004-06 채권 = 한경 KIS 국고채권 총수익(`KISKTB_TR`) 월말 수익(41개월), 2004-07~ = `bd`. KIS 국고채권의 구성 방식('전 만기를 시가총액 비중으로')은 출처를 찾지 못한 서술이다(새 자료 감사 M-4).
- 표본: KR-a 2004-07~2026-08(266), KR-b 2001-02~2026-08(307), KR-a~2024 2004-07~2024-12(246, `P7.PRE`).
- 글라이드: 5대 평균(`glide_w(r, 'mean5')`, 주), 범위 = 5대 각각·12사 평균·대신(최저)·키움(최고). 잔여기간 r = −30 + t/12. '12사 평균'의 T−30~T−29 구간은 공시가 T−29부터인 운용사가 빠져 실제로 11사 평균이다(아래 출력).
- 보수: 5대 평균 C-Pe 총보수(주)·합성총보수(병기), 달력 = ⌊2055 + r⌋ = 2025 + ⌊t/12⌋(2026 이전 = 첫 단계).""")
code(r"""C = pd.read_csv(INP / "C2_components_monthly.csv", index_col=0, parse_dates=True)
cpi = io.asset_series("cpi").resample("ME").last().pct_change(fill_method=None)
kis = pd.read_csv((paths.DATA_ROOT / "raw/kr_bond_pre2004_20261017/kis_monthly_2001_clean.csv"), index_col=0, parse_dates=True).KISKTB_TR
kis_r = kis.pct_change(fill_method=None).loc["2001-02":"2004-06"]
assert len(kis_r) == 41 and kis_r.notna().all() and (kis_r.index == pd.date_range("2001-02-28", "2004-06-30", freq="ME")).all()
KOS = C.kospi.dropna()                                          # 1980-02~ 코스피 가격 월 수익(실제 역사 경로의 사건 판정)
bd_b = pd.concat([kis_r, C.bd.loc["2004-07":]])
SAMP = {"KR-a": ("2004-07", "2026-08", C.bd), "KR-b": ("2001-02", "2026-08", bd_b), "KR-a~2024": ("2004-07", P7.PRE, C.bd)}
X = {}
for k, (a, b, bd) in SAMP.items():
    x = pd.DataFrame({"stk": C.stk, "bd": bd, "cpi": cpi, "kospi": C.kospi}).loc[a:b]
    assert x.notna().all().all() and len(x) == len(pd.date_range(x.index[0], x.index[-1], freq="ME")), (k, x.isna().sum())
    X[k] = x
print({k: (v.index[0].strftime("%Y-%m"), v.index[-1].strftime("%Y-%m"), len(v)) for k, v in X.items()})
print("KIS 국고채권 2001-02~2004-06: 월평균 %.3f%%, 월 표준편차 %.3f%%" % (kis_r.mean() * 100, kis_r.std() * 100))
# PW 원값(계산값) — 1보다 작으면 하한 1(블록 1과 같은 경로)
pw = []
for k, x in X.items():
    raw = float(optimal_block_length((x.stk - x.bd).to_numpy())["stationary"].iloc[0]); app = P7.pw_block(x.stk - x.bd)
    assert app == max(1.0, raw)
    pw.append(dict(표본=k, 계열="stk − bd", n=len(x), PW_원값=raw, PW_적용=app, 하한적용=raw < 1, 표기="블록 1과 같은 경로" if raw < 1 else ""))
PW = csv(pd.DataFrame(pw), "pw_block.csv"); print(PW.to_string(index=False))""")
code(r"""FT = fee_table()
G = {"5대평균": glide_w(RY, "mean5")} | {m: glide_w(RY, m) for m in MGRS}
gt = pd.read_csv(INP / "C2_glide_by_remaining_years.csv", index_col=0)
assert np.allclose(G["5대평균"][::12] * 100, gt.loc[-30:-1, "mean5"].to_numpy())             # C2 표와 같음(정수 잔여기간)
FEEM = {k: np.mean([fee_pct(m, FEE_YEAR, col=col, F=FT) for m in MGRS], axis=0) / 1200 for k, col in (("총보수", "total_fee_pct"), ("합성총보수", "synthetic_pct"))}
FEEO = {m: {k: fee_pct(m, FEE_YEAR, col=col, F=FT) / 1200 for k, col in (("총보수", "total_fee_pct"), ("합성총보수", "synthetic_pct"))} for m in MGRS}
# 12사 2055 공시 글라이드: 5대 투자설명서 + 기타 7사 웹 공시(decisions_survey a2_d1_inputs.py와 같은 읽기), 공시 범위 밖은 빈 값
import re
pr = pd.read_csv((paths.DATA_ROOT / "raw/fund_tdf/glidepath_disclosed_prospectus.csv")); pr = pr[pr.vintage == 2055]
wo = pd.read_csv((paths.DATA_ROOT / "raw/fund_tdf/glidepath_disclosed_web_kr_others.csv")); wo = wo[wo["product"].str.contains(r"TDF\s*2055", na=False)].copy()
def tp(s):
    m = re.search(r"T\s*([+-]\s*\d+|0)", str(s)) or re.search(r"T0", str(s))
    return 0 if m.group(0).replace(" ", "") == "T0" else int(m.group(1).replace(" ", ""))
pts = pd.concat([pr.assign(T=pr.years_rel_target, val=pr.risky_pct.astype(float))[["manager", "T", "val"]],
                 wo.assign(T=wo.target_year_or_years_to_target.apply(tp), val=wo.risky_pct.astype(str).str.replace("≤", "").astype(float))[["manager", "T", "val"]]])
def g12(r, mg=None):
    out = []
    for m, g in pts.groupby("manager"):
        if mg and m != mg: continue
        g = g.sort_values("T"); tt, vv = g["T"].to_numpy(float), g.val.to_numpy(float)
        out.append(np.where((r >= tt.min()) & (r <= tt.max()), np.interp(r, tt, vv), np.nan))
    return np.nanmean(out, axis=0) / 100, len(out)
v, n12 = g12(np.array([-30.0, 0.0]))
print("12사 평균 T−30·T0:", np.round(v * 100, 2), "| 운용사 수", n12, "| DL 124 감사값 78.9 → 33.9")
assert n12 == 12 and np.allclose(np.round(v * 100, 1), [78.9, 33.9])
n30 = {m: bool(g["T"].min() <= -30) for m, g in pts.groupby("manager")}
print("T−30 값이 있는 운용사 수(실제 평균 분모):", sum(n30.values()), "| T−30 공시 없는 운용사:", [m for m, x in n30.items() if not x])
G["12사평균"] = g12(RY)[0]; G["대신(최저)"] = g12(RY, "대신자산운용")[0]; G["키움(최고)"] = g12(RY, "키움투자자산운용")[0]
assert all(np.isfinite(g).all() for g in G.values())
GF = csv(pd.DataFrame({"t": t, "나이": 30 + t / 12, "잔여기간": RY, "보수연도": FEE_YEAR, **{f"w_{k}": v for k, v in G.items()},
                       "보수_총보수_5대평균_pctpa": FEEM["총보수"] * 1200, "보수_합성_5대평균_pctpa": FEEM["합성총보수"] * 1200}), "D_inputs_glide_fee_by_month.csv")
print(GF.iloc[[0, 12, 120, 240, 300, 359]].round(3).T.to_string())""")

md("""## 2. 표 1 — 실제 하락장 사례 (시뮬레이션 없음, KR-b 구간 2001-02~2026-08)
코스피 가격(1980-02~ 전체로 판정, 재무장 +20%)의 확인월이 2001-02~2026-08에 있는 사건. 켜진 기간마다 위험자산 묶음(`stk`)과 국채(`bd`, 2004-06 이전 KIS)의 누적 수익과 차(초과수익, %p).
규칙의 기여 ≈ Δ × 초과수익(그 시점 잔액 대비, 상한에 닿지 않고 그 기간 납입·복리를 무시한 1차 근사). 켜진 기간이 2026-08을 넘으면 '미완'. 겹침 = 이전 사건이 아직 켜져 있을 때 확인된 사건(규칙에서는 복귀 기준만 바뀜, 이 표는 사건별로 따로 잰다).
**경계 사례(새 자료 감사 MEDIUM-1):** 코스피 월말 종가 2026-05 8476.15, 2026-06 8476.48(차 0.33포인트, 0.004%)이라 고점이 6월로 잡히고, 2026-07(−22.2%)은 고점 뒤 1개월이라 사건이 아니다. 6월 종가가 0.34포인트만 낮았으면 2026-07이 −20% 사건이 된다. 코스피 종합지수 월말값은 DataGuide 한 출처만 확인했다. 그래서 2024-12에서 끊은 판본(KR-a~2024)을 함께 낸다.""")
code(r"""Xb = X["KR-b"]; ix = Xb.index; rows = []
for th in P9.DD_GRID:
    ev = P9.dd_events(KOS.to_numpy(), th, rearm=P9.REARM); end0 = {ex: pd.Timestamp("1900-01-31") for ex in EXITS}
    for c, rc in ev:
        cm = KOS.index[c]
        for ex in EXITS:
            e_full = KOS.index[c] + pd.offsets.MonthEnd(12) if ex == "1y" else (KOS.index[rc] if rc is not None else None)
            if not (ix[0] <= cm <= ix[-1]): continue                  # 저축 구간(2001-02~2026-08) 안 확인월만, 겹침도 그 안에서
            ov = cm < end0[ex]; end0[ex] = e_full if e_full is not None else pd.Timestamp("2100-12-31")
            s = cm + pd.offsets.MonthEnd(1); e = min(e_full, ix[-1]) if e_full is not None else ix[-1]
            w = Xb.loc[s:e]; cs, cb = np.prod(1 + w.stk) - 1, np.prod(1 + w.bd) - 1
            rows.append(dict(문턱=th, 확인월=cm.strftime("%Y-%m"), 복귀=EXN[ex], 켜짐_시작=s.strftime("%Y-%m"), 켜짐_끝=e.strftime("%Y-%m") if len(w) else "자료 끝 뒤", 개월=len(w),
                             미완=(e_full is None) or (e_full > ix[-1]), 겹침=bool(ov), 위험자산누적_pct=cs * 100, 국채누적_pct=cb * 100, 초과_pctp=(cs - cb) * 100,
                             **{f"기여_Δ{int(dl * 100)}_pctp": dl * (cs - cb) * 100 for dl in DELTAS}))
T1 = csv(pd.DataFrame(rows), "D_t1_events.csv")
print(T1.round(2).to_string(index=False))""")

md("""## 3. 표 2 — 실제 역사 경로 1개
KR-a(2004-07에 30세, 266개월 → 약 52세), KR-b(2001-02에 30세, 307개월 → 약 55세), KR-a~2024(246개월). 사건 판정은 1980-02~ 전체 코스피로 하고, **확인월이 경로 첫 달 이후인 사건만** 규칙을 켠다(저축 시작 전에 확인된 사건은 쓰지 않는다).
값 = 같은 경로·같은 납입의 최종 금액 비 W_규칙/W_기준(명목·실질 같음).""")
code(r"""H = []
for k, x in X.items():
    s0 = KOS.index.get_loc(x.index[0]); n = len(x)
    M, REC = masks(KOS.to_numpy()[None, :s0 + n], start=s0)            # 경로 끝까지의 코스피만(그 뒤 자료 안 씀), 확인월 >= 경로 첫 달
    M = {key: v[s0:s0 + n] for key, v in M.items()}
    H += evaluate(x.stk.to_numpy()[:, None], x.bd.to_numpy()[:, None], np.array([np.prod(1 + x.cpi.to_numpy())]), M, REC, G["5대평균"], FEEM,
                  dict(표본=k, 시작=x.index[0].strftime("%Y-%m"), 끝=x.index[-1].strftime("%Y-%m"), 개월=n))
T2 = csv(pd.DataFrame(H).drop(columns=["사건1개이상_비율"]), "D_t2_hist.csv")
v = T2[(T2.보수 == "총보수") & (T2.납입증가 == "0%")]
print(v.pivot_table(index=["재무장", "문턱", "복귀", "증액"], columns="표본", values="금액비_규칙대기준", sort=False).round(4).to_string())""")
code(r"""print("작동 기록(총보수·0%): 경로 안 사건 수, 켜진 개월, 겹친 사건 수, 상한 닿은 달")
print(v[v.증액 == 0.10][["표본", "재무장", "문턱", "복귀", "사건수_평균", "켜진개월_평균", "겹침경로수", "상한닿은_경로월", "기준_실질배수"]].to_string(index=False))
print(); print("합성총보수·납입증가 3.4% 판본(−20%·재무장 20%):")
w2 = T2[(T2.문턱 == -0.20) & (T2.재무장 == "re20")]
print(w2.pivot_table(index=["복귀", "증액"], columns=["표본", "보수", "납입증가"], values="금액비_규칙대기준", sort=False).round(4).to_string())""")

md("""## 4. 표 3 — 한국 부트스트랩 (seed 20261008, N = 10,000, 360개월, 블록 {1, PW, 12})
표본마다 `paired_resample_paths([stk, bd, cpi, kospi], 10,000, 360, b, 20261008)` — 기준과 모든 칸이 같은 경로를 쓴다. 고점 추적은 경로 첫 달부터(예열 없음, DL 145).
PW 원값이 1보다 작으면 하한 1이 적용되어 **블록 1과 같은 경로**다(같은 seed·같은 평균 블록) — 그때는 블록 1 결과를 'PW' 행에 그대로 적는다.
d = ln(W_규칙/W_기준): 중앙·P5·P95(경로 범위)·P(d>0). ΔP5 = ln P5(W_규칙) − ln P5(W_기준), ΔCVaR = ln CVaR5(W_규칙) − ln CVaR5(W_기준)(각자 하위 500개 경로 평균). 배수 = 실질 최종 금액(누적 물가로 나눔) ÷ **명목** 납입 총액(납입마다 실질화하지 않아 그렇게 한 배수보다 낮다. d·ΔP5·ΔCVaR에는 영향 없음).
'상한닿은_경로월' = 0은 결과가 아니라 설계상 정해진 값이다: 입력 글라이드 최대 80%(키움 T−30) + Δ 최대 15%p = 95%라 **상한 100%에 설계상 도달 불가(최대 95%)**.
위약 비교를 위해 같은 루프에서 6절 위약 행도 함께 계산한다(기존 열 계산은 그대로).""")
code(r"""B, BG, PL = [], [], []
for k, x in X.items():
    pwr = PW.set_index("표본").loc[k]; cache = {}
    for bn, b in (("1", 1.0), ("PW", float(pwr.PW_적용)), ("12", 12.0)):
        if b in cache:
            rows = [dict(r, 블록=bn) for r in cache[b]]; B += rows; BG += [dict(r, 블록=bn) for r in cache[b, "g"]]; PL += [dict(r, 블록=bn) for r in cache[b, "p"]]; continue
        SK, BD, CP, KO = paired_resample_paths([x.stk, x.bd, x.cpi, x.kospi], NP, T, b, SEED)
        assert SK.shape == (NP, T)
        M, REC = masks(KO); cc = np.prod(1 + CP, axis=1); SKt, BDt = SK.T.copy(), BD.T.copy()
        meta = dict(표본=k, 블록=bn, 평균블록=b, PW_원값=pwr.PW_원값)
        rows = evaluate(SKt, BDt, cc, M, REC, G["5대평균"], FEEM, meta); B += rows; cache[b] = rows
        cache[b, "p"] = placebo(SKt, BDt, M, G["5대평균"], FEEM["총보수"], meta); PL += cache[b, "p"]       # 6절 위약(문서 단계 추가)
        g_rows = []
        if k == "KR-a":                                       # 글라이드 범위: 같은 경로
            for gk in ["KB", "미래에셋", "삼성", "신한", "한국투자", "12사평균", "대신(최저)", "키움(최고)"]:
                fee = FEEO[gk] if gk in MGRS else FEEM
                g_rows += evaluate(SKt, BDt, cc, M, REC, G[gk], fee, dict(meta, 글라이드=gk, 보수출처="자기 운용사" if gk in MGRS else "5대 평균"))
        BG += g_rows; cache[b, "g"] = g_rows
        print(k, bn, "done", flush=True)
KB_ = csv(pd.DataFrame(B), "D_kr_boot.csv"); KG = csv(pd.DataFrame(BG), "D_kr_glide_range.csv")
print(len(KB_), len(KG))""")
code(r"""cols = ["표본", "블록", "문턱", "복귀", "증액", "d_중앙", "d_P5", "d_P95", "P_d양수", "dP5", "dCVaR", "기준배수_중앙", "규칙배수_중앙", "기준배수_P5", "규칙배수_P5"]
v = KB_[(KB_.보수 == "총보수") & (KB_.납입증가 == "0%") & (KB_.재무장 == "re20")].copy()
for c in ["d_중앙", "d_P5", "d_P95", "dP5", "dCVaR"]: v[c] = v[c] * 100     # 로그 %
print("총보수·납입증가 0%·재무장 20% — d·ΔP5·ΔCVaR는 로그 %"); print(v[cols].round(3).to_string(index=False))""")
code(r"""print("작동 기록(총보수·0%·Δ +10%p): 경로당 사건 수, 사건 1개 이상 비율, 켜진 개월, 겹친 경로 수, 상한 닿은 경로-월")
w = KB_[(KB_.보수 == "총보수") & (KB_.납입증가 == "0%") & (KB_.증액 == 0.10)]
print(w[["표본", "블록", "문턱", "재무장", "복귀", "사건수_평균", "사건1개이상_비율", "켜진개월_평균", "겹침경로수", "상한닿은_경로월"]].round(3).to_string(index=False))""")
code(r"""print("재무장 민감도(−20%, 총보수·0%) — d 중앙(로그 %)")
w = KB_[(KB_.문턱 == -0.20)].copy()
for c in ["d_중앙", "dP5", "dCVaR"]: w[c] = w[c] * 100
print(w[(w.보수 == "총보수") & (w.납입증가 == "0%")].pivot_table(index=["재무장", "복귀", "증액"], columns=["표본", "블록"], values="d_중앙", sort=False).round(3).to_string()); print()
print("합성총보수 vs 총보수, 납입 0% vs 3.4% (−20%·re20·Δ +10%p, d 중앙 로그 %)")
w2 = w[(w.재무장 == "re20") & (w.증액 == 0.10)]
print(w2.pivot_table(index=["표본", "블록", "복귀"], columns=["보수", "납입증가"], values="d_중앙", sort=False).round(3).to_string())""")
code(r"""print("글라이드 범위(KR-a, 총보수·0%·−20%·re20): d 중앙(로그 %)")
g = KG[(KG.보수 == "총보수") & (KG.납입증가 == "0%") & (KG.문턱 == -0.20) & (KG.재무장 == "re20")].copy()
for c in ["d_중앙", "dP5", "dCVaR"]: g[c] = g[c] * 100
print(g.pivot_table(index=["글라이드"], columns=["블록", "복귀", "증액"], values="d_중앙", sort=False).round(3).to_string())
print(); print("상한 100%%에 닿은 경로-월(Δ +15%%p, 전 블록 합) — 설계상 도달 불가: 입력 글라이드 최대 %.2f + Δ 최대 %.2f = %.2f"
              % (max(g_.max() for g_ in G.values()), max(DELTAS), max(g_.max() for g_ in G.values()) + max(DELTAS)))
print(KG[KG.증액 == 0.15].groupby("글라이드").상한닿은_경로월.sum().to_string())""")

md("""## 5. 표 4 — 다국가 보충 (회원 결정 ①: 각국 저축자, 현지통화)
- 9개국 = Swinkels 월 10년 국채 총수익이 있는 나라(AUS CAN DEU FRA GBR JPN NOR SWE USA).
- 위험자산 = French 국가별 **현지통화** 월 시장수익(`Value-Weight Local Returns, All 4 Data Items Not Reqd`의 Mkt). 미국은 국가 파일이 없어 French `F-F_Research_Data_Factors`의 Mkt−RF + RF(미국 시장, 달러 = 현지통화)를 쓴다.
- 안전자산 = 자국 Swinkels 10년 국채 총수익. 물가 = BIS 월 CPI(9개국 모두 2022년까지 있음. OECD 월 CPI는 호주 2024~·일본 ~2021-06뿐). **호주 BIS CPI는 분기 값을 달마다 반복한 계열**(월 변화 0인 달 67%)이다 — d에는 영향 없고 실질 배수에만 영향.
- 표본 = 나라마다 세 계열이 모두 있는 구간(~2022-12). 규칙 신호 = 그 경로의 위험자산 총수익(월말). 한국(코스피 **가격**)과 다르다.
- 경로 = `P7.pooled_paths`(나라-월 풀, 평균 블록 120(주)·1·12·240, seed 20261008, N 10,000). 같은 18칸 + 재무장 민감도.""")
code(r"""MC = pd.read_csv((paths.DATA_ROOT / "processed/multicountry_returns_20261017.csv"), dtype={"period": str})
def mcs(src, var, iso):
    x = MC[(MC.source == src) & (MC.variable == var) & (MC.iso3 == iso)]
    return pd.Series(x.value.to_numpy(float), index=pd.to_datetime(x.period) + pd.offsets.MonthEnd(0)).sort_index()
FR = {"AUS": "Austrlia", "CAN": "Canada", "DEU": "Germany", "FRA": "France", "GBR": "UK", "JPN": "Japan", "NOR": "Norway", "SWE": "Sweden"}
ff = pd.read_csv(paths.EQUITY_GLOBAL / "french" / "F-F_Research_Data_Factors.csv", skiprows=3, index_col=0)
fi = ff.index.astype(str).str.strip(); kp = fi.str.fullmatch(r"\d{6}")
us_eq = pd.Series((pd.to_numeric(ff["Mkt-RF"][kp]) + pd.to_numeric(ff["RF"][kp])).to_numpy() / 100, index=pd.to_datetime(fi[kp], format="%Y%m") + pd.offsets.MonthEnd(0))
PANEL, srows = {}, []
for iso in ["AUS", "CAN", "DEU", "FRA", "GBR", "JPN", "NOR", "SWE", "USA"]:
    eq = us_eq if iso == "USA" else P7._french_table(paths.EQUITY_GLOBAL / "french_intl" / f"{FR[iso]}.Dat", "Value-Weight Local  Returns      All 4 Data Items Not Reqd")
    df = pd.DataFrame({"eq": eq, "bd": mcs("Swinkels2023", "bond_tr_10y_m", iso), "infl": mcs("BIS", "cpi_index", iso).pct_change(fill_method=None)}).dropna()
    assert len(df) == len(pd.date_range(df.index[0], df.index[-1], freq="ME")), iso          # 끊김 없음
    PANEL[iso] = df
    ev = P9.dd_starts(df["eq"], -0.20, rearm=P9.REARM)
    srows.append(dict(나라=iso, 위험자산=("French F-F 미국 Mkt(달러=현지)" if iso == "USA" else f"French {FR[iso]}.Dat 현지통화"), 시작=df.index[0].strftime("%Y-%m"), 끝=df.index[-1].strftime("%Y-%m"),
                      개월=len(df), 풀비중=0.0, 위험자산_연복리_pct=(np.prod(1 + df["eq"]) ** (12 / len(df)) - 1) * 100, 국채_연복리_pct=(np.prod(1 + df.bd) ** (12 / len(df)) - 1) * 100,
                      물가_연율_pct=(np.prod(1 + df.infl) ** (12 / len(df)) - 1) * 100, 사건수_m20=len(ev), 사건확인월=";".join(x.strftime("%Y-%m") for x in ev)))
S = pd.DataFrame(srows); S["풀비중"] = S.개월 / S.개월.sum()
S = csv(S, "D_mc_sample.csv"); print(S.round(3).to_string(index=False))""")
code(r"""MCR, PLM = [], []
for b in (120, 1, 12, 240):
    EQ, BD_, IN = P7.pooled_paths(PANEL, ["eq", "bd", "infl"], NP, T, b, SEED)
    M, REC = masks(EQ); cc = np.prod(1 + IN, axis=1); SKt, BDt = EQ.T.copy(), BD_.T.copy(); meta = dict(표본="다국가 9개국 풀", 블록=str(b), 평균블록=b)
    MCR += evaluate(SKt, BDt, cc, M, REC, G["5대평균"], FEEM, meta)
    PLM += placebo(SKt, BDt, M, G["5대평균"], FEEM["총보수"], meta)                                  # 6절 위약(문서 단계 추가)
    print("block", b, "done", flush=True)
MCD = csv(pd.DataFrame(MCR), "D_mc_boot.csv")
v = MCD[(MCD.보수 == "총보수") & (MCD.납입증가 == "0%") & (MCD.재무장 == "re20")].copy()
for c in ["d_중앙", "d_P5", "d_P95", "dP5", "dCVaR"]: v[c] = v[c] * 100
v["_o"] = v.문턱.map({-0.20: 0, -0.10: 1, -0.30: 2}); v["_b"] = v.평균블록.map({120: 0, 1: 1, 12: 2, 240: 3})
print("총보수·0%·재무장 20% (−20% 먼저), 로그 %"); print(v.sort_values(["_b", "_o"], kind="stable")[cols[1:]].round(3).to_string(index=False))""")
code(r"""w = MCD[(MCD.보수 == "총보수") & (MCD.납입증가 == "0%") & (MCD.증액 == 0.10)]
print("작동 기록(다국가, 총보수·0%·Δ +10%p)"); print(w[["블록", "문턱", "재무장", "복귀", "사건수_평균", "사건1개이상_비율", "켜진개월_평균", "겹침경로수"]].round(3).to_string(index=False))
print(); print("한국(블록 1·PW·12)과 다국가(120·1·12·240) d 중앙 나란히 (−20%·re20·총보수·0%, 로그 %):")
a = KB_[(KB_.보수 == "총보수") & (KB_.납입증가 == "0%") & (KB_.문턱 == -0.20) & (KB_.재무장 == "re20")]
b_ = MCD[(MCD.보수 == "총보수") & (MCD.납입증가 == "0%") & (MCD.문턱 == -0.20) & (MCD.재무장 == "re20")]
z = pd.concat([a, b_]); z["열"] = z.표본 + " b" + z.블록.astype(str)
print((z.pivot_table(index=["복귀", "증액"], columns="열", values="d_중앙", sort=False) * 100).round(3).to_string())""")
md("""**위 나란히 표는 같은 조건의 비교가 아니다(감사 M-2).** 한국과 다국가는 다음이 다르다.
- 위험자산: 한국 = 국내 15.2% + 선진국(원화 환산, UH) 84.8% 묶음, 다국가 = 자국 주식 100%.
- 신호: 한국 = 코스피 **가격**(위험자산과 다른 계열), 다국가 = 위험자산 자신의 총수익.
- 국채: 한국 = FnGuide 국고채 TR(3년 중심, KR-b 앞 41개월은 KIS), 다국가 = Swinkels 10년물.
- 기간·블록: 한국 2004~2026(KR-b 2001~), 다국가 1975(미국 1947)~2022. 한국 블록은 모두 12개월 이하, 다국가 주 블록은 120.
- 두 쪽의 위험자산 − 국채 월평균 차와 켜진 개월은 아래 출력에 있다.""")
code(r"""prem = {"KR-a(stk − bd)": (X["KR-a"].stk - X["KR-a"].bd).mean() * 100, "다국가 풀(eq − bd)": (pd.concat(PANEL.values())["eq"] - pd.concat(PANEL.values()).bd).mean() * 100}
print("위험자산 − 국채 월평균 차(%/월):", {k: round(v, 3) for k, v in prem.items()})
q = lambda D_, bl: D_[(D_.보수 == "총보수") & (D_.납입증가 == "0%") & (D_.문턱 == -0.20) & (D_.재무장 == "re20") & (D_.복귀 == "전고점 회복") & (D_.증액 == 0.10) & (D_.블록 == bl)]
print("켜진 개월 평균(−20%%·re20·전고점·Δ+10%%p): KR-a 블록 1 = %.1f, 다국가 블록 1 = %.1f, 다국가 블록 120 = %.1f"
      % (q(KB_[KB_.표본 == "KR-a"], "1").켜진개월_평균.iloc[0], q(MCD, "1").켜진개월_평균.iloc[0], q(MCD, "120").켜진개월_평균.iloc[0]))""")

md("""## 6. 추가 계산 (문서 단계, 기존 결과는 바꾸지 않음)
### 6-1. 위약(placebo) 비교 (감사 M-1) → `D_placebo.csv`
- **위약 정의:** 경로마다 규칙이 켜졌는지(0/1)를 달마다 1만 경로 평균한 값 × Δ를, 하락장과 상관없이 **모든 경로에 매달 똑같이** 더 얹는다(정적 기울기). 평균 추가 비중은 규칙과 같고, 언제 얹는지만 하락장과 무관하다. 감사 재계산(`audit\\audit_recalc_2.py`, `audit_recalc_3.py`)과 같은 정의다.
- 같은 seed·같은 경로·같은 보수(5대 평균 총보수)·납입 0%. 규칙 d와 위약 d는 같은 기준(W_기준)에 대한 로그 비다.
- 열: 규칙_d_중앙(4·5절 d_중앙과 같은 값, assert로 확인), 위약_d_중앙·P5·P95, 규칙빼기위약_중앙(경로별 d − d_위약의 중앙), P_규칙gt위약(경로별 d > d_위약 비율), 켜진개월_평균, 평균추가비중_pctp.
- 범위: 재무장 20%의 주 18칸(문턱 3 × 복귀 2 × Δ 3), 한국 3표본 × 블록 {1, PW, 12}, 다국가 블록 {120, 1, 12, 240}.""")
code(r"""PLD = pd.DataFrame(PL + PLM)
key = ["표본", "블록", "보수", "납입증가", "문턱", "재무장", "복귀", "증액"]
ref = pd.concat([KB_, MCD])[key + ["d_중앙", "켜진개월_평균"]]
chkp = PLD.merge(ref, on=key, how="left", validate="one_to_one")
assert chkp.d_중앙.notna().all() and np.allclose(chkp.규칙_d_중앙, chkp.d_중앙, rtol=0, atol=1e-12) and np.allclose(chkp.켜진개월_평균_x, chkp.켜진개월_평균_y)
PLD = csv(PLD, "D_placebo.csv")
v = PLD[(PLD.문턱 == -0.20) & (PLD.증액 == 0.10)].copy()
for c in ["규칙_d_중앙", "위약_d_중앙", "위약_d_P5", "위약_d_P95", "규칙빼기위약_중앙"]: v[c] = v[c] * 100
print("−20%·재무장 20%·Δ +10%p·총보수·납입 0% — d는 로그 %")
print(v[["표본", "블록", "복귀", "켜진개월_평균", "평균추가비중_pctp", "규칙_d_중앙", "위약_d_중앙", "규칙빼기위약_중앙", "P_규칙gt위약"]].round(4).to_string(index=False))""")

md("""### 6-2. 겹침 처리 민감도 (감사 M-3) → `D_overlap_keep_sens.csv`
- 주 결과: 켜진 동안 새 사건이 확인되면 복귀 기준을 **최근 사건**으로 바꾼다(`P9.dip_on`). 재무장 뒤의 새 고점은 아직 회복하지 못한 옛 고점보다 낮으므로, 이 처리는 전고점 복귀에서 더 일찍 꺼지는 쪽으로만 움직인다.
- 민감도: **옛 사건 기준 유지**(이전 사건과 새 사건 중 늦은 복귀). 1년 복귀에서는 두 처리가 같다.
- 한국 대표 칸만: KR-a·블록 1·−20%·재무장 20%·Δ {5, 10, 15}%p·두 복귀·총보수·납입 0%. 같은 seed·같은 경로.
- 점검(겹침 처리 검증, 감사 M-5): ① 최근 사건 기준 켜짐을 사건 목록에서 다시 만들면 `P9.dip_on`과 같다 ② 옛 기준 유지 켜짐 ⊇ 최근 기준 켜짐 ③ 1년 복귀는 두 처리가 같다 ④ 최근 기준 판이 4절 `D_kr_boot.csv` 값과 같다.""")
code(r"""xa = X["KR-a"]; SK, BD, CP, KO = paired_resample_paths([xa.stk, xa.bd, xa.cpi, xa.kospi], NP, T, 1.0, SEED)
cc = np.prod(1 + CP, axis=1); SKt, BDt = SK.T.copy(), BD.T.copy(); th, ra = -0.20, P9.REARM
ML, MK, RC = {}, {}, {}
on_l = {ex: np.zeros((NP, T), bool) for ex in EXITS}; on_k = {ex: np.zeros((NP, T), bool) for ex in EXITS}; ne = np.zeros(NP, int); ov = {ex: np.zeros(NP, int) for ex in EXITS}
for p in range(NP):
    ev = P9.dd_events(KO[p], th, rearm=ra)
    for ex in EXITS:
        on_l[ex][p], ne[p], ov[ex][p] = P9.dip_on(KO[p], th, ex, ra, 0, ev); on_k[ex][p] = dip_on_keep(KO[p], th, ex, ra, 0, ev)
for ex in EXITS:
    assert (on_k[ex] >= on_l[ex]).all()                                             # ② 옛 기준 유지 ⊇ 최근 기준
    ML[th, ra, ex], MK[th, ra, ex], RC[th, ra, ex] = on_l[ex].T.copy(), on_k[ex].T.copy(), (ne, ov[ex])
assert (on_k["1y"] == on_l["1y"]).all()                                             # ③ 1년 복귀는 같음
cells = [(th, ra, ex, dl) for ex in EXITS for dl in DELTAS]; FE1 = {"총보수": FEEM["총보수"]}
OL = []
for name, MM in (("최근 사건 기준(주)", ML), ("옛 사건 기준 유지", MK)):
    rows = [r for r in evaluate(SKt, BDt, cc, MM, RC, G["5대평균"], FE1, dict(표본="KR-a", 블록="1", 평균블록=1.0, 겹침처리=name), cells) if r["납입증가"] == "0%"]
    OL += rows
OL = pd.DataFrame(OL).drop(columns=["상한닿은_경로월"])
base = KB_[(KB_.표본 == "KR-a") & (KB_.블록 == "1") & (KB_.보수 == "총보수") & (KB_.납입증가 == "0%") & (KB_.문턱 == th) & (KB_.재무장 == "re20")]
chk_ = OL[OL.겹침처리 == "최근 사건 기준(주)"].merge(base, on=["복귀", "증액"], suffixes=("", "_ref"))
assert len(chk_) == 6 and all(np.allclose(chk_[c], chk_[c + "_ref"], rtol=0, atol=1e-12) for c in ["d_중앙", "d_P5", "d_P95", "dP5", "dCVaR", "켜진개월_평균"])   # ①·④
OL = csv(OL, "D_overlap_keep_sens.csv")
w = OL.copy()
for c in ["d_중앙", "d_P5", "d_P95", "dP5", "dCVaR"]: w[c] = w[c] * 100
print("KR-a·블록 1·−20%·재무장 20%·총보수·납입 0% — d·ΔP5·ΔCVaR는 로그 %")
print(w[["겹침처리", "복귀", "증액", "d_중앙", "d_P5", "d_P95", "P_d양수", "dP5", "dCVaR", "켜진개월_평균", "겹침경로수"]].round(4).to_string(index=False))""")

md("""### 6-3. 다국가 동시 사건·물가 계열 (감사 M-4·L-8) → `D_mc_simul_events.csv`
- 나라별 −20%(재무장 20%) 사건 확인월(`D_mc_sample.csv`)을 달·해별로 세어, 같은 시기에 여러 나라에서 사건이 확인된 정도를 적는다. 풀링 부트스트랩은 나라-월을 서로 바꿔 쓸 수 있는 관측으로 다루므로, 독립적인 폭락 표본 수는 '나라 × 사건'보다 적다.
- 표본 구간 안에서 BIS 월 CPI 변화가 0인 달의 비율(나라별). d에는 영향이 없고 실질 배수 수준에만 영향이 있다.""")
code(r"""ev_ = S[["나라", "사건확인월"]].assign(달=S.사건확인월.str.split(";")).explode("달").dropna(subset=["달"]); ev_ = ev_[ev_.달 != ""]
ev_["해"] = ev_.달.str[:4]
by_m = ev_.groupby("달").나라.agg(나라수="nunique", 나라=lambda x: ",".join(sorted(set(x)))).reset_index().assign(단위="달")
by_y = ev_.groupby("해").나라.agg(나라수="nunique", 나라=lambda x: ",".join(sorted(set(x)))).reset_index().rename(columns={"해": "달"}).assign(단위="해")
SE = csv(pd.concat([by_m, by_y])[["단위", "달", "나라수", "나라"]], "D_mc_simul_events.csv")
print("같은 해에 사건이 확인된 나라 수(4개국 이상):"); print(SE[(SE.단위 == "해") & (SE.나라수 >= 4)].to_string(index=False)); print()
print("같은 달에 사건이 확인된 나라 수(3개국 이상):"); print(SE[(SE.단위 == "달") & (SE.나라수 >= 3)].to_string(index=False)); print()
print("표본 구간 BIS CPI 월 변화 0 비율:", {k: round(float((v_.infl == 0).mean()), 3) for k, v_ in PANEL.items()})""")

md("""### 6-4. 격자 전체 범위 (감사 5절 단서) → `D_grid_range.csv`
대표 칸 숫자를 인용할 때 함께 적을 격자 전체 범위: d 중앙의 최솟값·최댓값(로그 %), 겹친 경로 수 최댓값. 범위 = 각 CSV의 모든 칸(문턱·재무장·복귀·Δ·보수·납입·블록·표본).""")
code(r"""GR = csv(pd.DataFrame([dict(대상=k, 칸수=len(D_), d_중앙_최소_logpct=D_.d_중앙.min() * 100, d_중앙_최대_logpct=D_.d_중앙.max() * 100, 겹침경로수_최대=int(D_.겹침경로수.max()))
                        for k, D_ in (("한국 부트스트랩(D_kr_boot)", KB_), ("한국 글라이드 범위(D_kr_glide_range)", KG), ("다국가 풀(D_mc_boot)", MCD))]), "D_grid_range.csv")
print(GR.round(3).to_string(index=False))""")

md("""## 7. 한계 (명세 그대로 + 이번 실행에서 생긴 것 + 문서 단계 추가)
- 판정 도구(바깥 부트스트랩·Bonferroni·블록 관문·δ 꼬리 조건)는 쓰지 않았다. ΔP5·ΔCVaR는 경로 묶음 하나에서 나온 점값이다.
- 국내 몫 0.152를 모든 시점에 고정(2025~26 포함 추정값). 공시 '위험자산' 전부를 위험자산 묶음, 나머지를 국고채 TR로 본다. 해외는 선진국만, UH만.
- d에는 '추가 비중 × 켜진 기간' 효과가 들어 있고, 주 표는 하락장 시점 효과와 분리하지 않았다. 같은 평균 추가 비중의 위약 비교는 6-1 표다. 한국 블록 {1, PW, 12}는 모두 12개월 이하라, 전고점 회복 구간(실제 25~39개월)의 평균회귀를 담지 못한다(DL 141 결정).
- 사건 겹침 처리(최근 사건 기준)는 근거 문서가 없는 설계 선택(⬜4)이다. 옛 기준 유지 판은 6-2 표다.
- 한국과 다국가는 위험자산·신호·국채 만기·기간·블록이 다르다(5절 끝 단서).
- KR-b의 2001-02~2004-06 채권은 KIS 국고채권이라 2004-07부터의 FnGuide 국고채 TR(3년 중심)과 성격이 다르다. 새 자료 감사 MEDIUM: ② 월말이 아닌 달(2010-02·2019-03·2019-04, 2019-06·07 빈 값으로 2019-08 월수익도 빈 값, 미완성 2026-10 행) — 모두 이 노트북이 쓰는 2001-02~2004-06 밖이다 ③ 정제 유효 범위는 KTB·GBI·KBI만(순가격·신용 계열에 오류값 남음, 쓰는 열 = KTB 총수익) ④ 2001~2004 KIS 듀레이션 미상(공개 값은 최근 30일뿐), '전 만기·시가총액 비중' 구성 서술은 출처 없음.
- 신호(코스피 가격) 2026-07 사건 여부가 월말 0.33포인트(0.004%) 차이에 걸림(새 자료 감사 MEDIUM-1, 종합지수는 DataGuide 한 출처) → KR-a~2024 판본 병기. 코스피 사건 수를 인용할 때 이 경계 사례를 함께 적는다.
- 규칙의 추가 비중에도 같은 보수(문서에 없음). 현행 보수 단계표·현행 공시 글라이드가 30년 그대로 간다고 둔다. 펀드 전환 지연(t+2)은 넣지 않았다.
- 실제 역사 경로는 저축 시작 전에 확인된 사건을 쓰지 않는다(이번 실행에서 정함). 부트스트랩 경로의 고점 추적은 경로 첫 달부터. 감사 재계산(`audit_recalc_5.py`)에서 시작 때 아직 켜져 있을 사건을 포함하면 표 2 Δ+10%p 금액비 변화는 0.006 이하였다.
- 거래비용(펀드·ETF 전환 비용, 사건당 2회 × Δ × 잔액)은 모형에 없다. 세금은 사전등록대로 비교에 넣지 않았다(적립기 과세이연).
- ΔP5·ΔCVaR는 몬테카를로 잡음이 있다. 감사가 경로 복원추출 300회로 잰 표준오차(KR-a 블록 1)는 ΔP5 0.23~0.28 로그%p, ΔCVaR 0.10~0.13 로그%p였다. 음수 칸 가운데 |값| < 2 표준오차인 칸이 많아(ΔP5 한국 82/132·다국가 82/209), 작은 칸 하나하나의 부호는 잡음 범위 안이다.
- 다국가: 위험자산 신호가 총수익(한국은 가격). 미국 위험자산은 French 국가 파일이 아니라 F-F 미국 시장 계열. 호주 CPI는 분기 반복이고, 다른 나라도 월 변화 0인 달이 있다(6-3 출력). 표본 길이가 나라마다 달라(미국 1947~) 풀 비중이 다르다(`D_mc_sample.csv`). `pooled_paths`의 시작점은 나라-월 균등이지만, 조각 끝에서 다음 조각으로 넘어갈 때는 나라를 균등하게 고른다(관측 수에 비례하지 않음).
- 다국가 사건은 나라 사이에 독립이 아니다(1987·2008·2020-03 등 여러 나라 동시 사건, 6-3 표). 9개국은 Swinkels 자료가 있는 선진국이고 모두 1975~2022에 살아남은 시장이다(나라 선택 생존편향).
- 'wealth' 함수는 이 생성기 안에 있다(`pilot9.py`로 옮기는 일은 남음, 감사 L-4).""")

nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
os.environ["PYTHONPATH"] = str(ROOT / "src")
NotebookClient(nb, timeout=7200, kernel_name="python3", resources={"metadata": {"path": str(NB_PATH.parent)}}).execute()
rr.save_executed(nb, NB_PATH)
NBM = OUTD / "nb_meta"; NBM.mkdir(parents=True, exist_ok=True)
extra = "seed=20261008\nN=10000\nT=360\nblocks_kr=1,PW,12\nblocks_mc=120,1,12,240\n" + "".join(
    f"input {p} sha256={rr.raw_sha256(p)}\n" for p in INPUTS + [ROOT / "notebooks/pilot9/_build_C_real_inputs.py"]) \
    + "".join(f"result {p.name} sha256={rr.raw_sha256(p)}\n" for p in sorted(OUTD.glob("*.csv")))   # 결과 CSV 해시(문서 단계 추가, 감사 L-6)
rr.write_run_meta(NBM, Path(__file__), ["src/pension_lab/pilot9.py", "src/pension_lab/pilot7.py", "src/pension_lab/bootstrap.py",
                                         "src/pension_lab/io.py", "notebooks/pilot9/_build_C_real_inputs.py"], extra)
print("실행완료 저장:", NB_PATH, NB_PATH.stat().st_size, "bytes")
