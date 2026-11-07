"""pilot9 D 거래비용 판본 (2026-11-06, 포트폴리오 정리용 추가 계산).

D_simple_20261017.ipynb의 설정·함수 셀을 그대로 실행한 뒤(결과 CSV는 새 폴더로만 씀),
규칙이 비중을 바꿀 때마다(켜짐·꺼짐) 한쪽을 팔고 다른 쪽을 사므로 '2 × 바꾼 금액 × 편도 비용'을 잔액에서 뺀다.
바꾼 비중 sw = |글라이드에서 벗어난 몫(w − 글라이드)의 달 사이 변화|, 첫 달 = 0(상한 100%가 걸린 달은 실제로 바뀐 만큼만).
비용 격자(편도 = 한 번 거래(팔기 또는 사기)한 금액 대비. 한 번 바꿀 때 팔기·사기 두 번, 켜졌다 꺼지면 네 번):
  0.0036396% 키움 연금저축 ETF 온라인 이벤트(유관기관 수수료만)  https://www.kiwoom.com/e/wm/event/evtUserEC230018View
  0.015%     같은 페이지의 일반 ETF 온라인 수수료
  0.1%, 0.3% 민감도(호가 차이·펀드 환매 대기일 포함 가정). 출처 없는 값이라 판정에 쓰지 않는다.
위약(정적 기울기)은 비중을 바꾸지 않으므로 비용 0. 위약 값은 기존 D_placebo.csv와 key로 맞춰 대조한다.
"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd, nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
NB = ROOT / "notebooks" / "pilot9" / "D_simple_20261017.ipynb"
REF = Path(r"D:\pension-lab_data\results\pilot9_20261013\D_simple_20261017")
NEW = Path(r"D:\pension-lab_data\results\pilot9_20261013\D_cost_20261106"); NEW.mkdir(parents=True, exist_ok=True)
os.chdir(NB.parent); sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(NB.parent))

src = [c.source for c in nbf.read(NB, as_version=4).cells if c.cell_type == "code"]
ns: dict = {"__name__": "d_cost"}
exec(src[0], ns); ns["OUT"] = NEW                                   # 이후 csv()는 새 폴더에만 쓴다
for s in src[1:4]: exec(s, ns)                                       # 자기 점검, 자료, 글라이드·보수
exec(next(s for s in src if s.startswith("MC = pd.read_csv")), ns)   # 다국가 패널
g = ns; P7, P9, NP, T, SEED = g["P7"], g["P9"], g["NP"], g["T"], g["SEED"]
G5, FEE, EXN, DELTAS, EXITS = g["G"]["5대평균"], g["FEEM"]["총보수"], g["EXN"], g["DELTAS"], g["EXITS"]
KS = {"0": 0.0, "0.0036%": 0.000036396, "0.015%": 0.00015, "0.1%(민감도)": 0.001, "0.3%(민감도)": 0.003}
TH, RA = -0.20, P9.REARM
CELLS = [(TH, RA, ex, dl) for ex in EXITS for dl in DELTAS]


def wealth_tc(Rt, c, sw, k):
    '''sw (개월, 경로) = 그 달 초에 바꾼 비중 크기. 파는 쪽·사는 쪽 각각 k이므로 납입 뒤 잔액의 2 × k × sw를 비용으로 뺀다(곱셈이라 다음 달 비용은 앞 비용을 뺀 잔액 기준).'''
    V = np.zeros(Rt.shape[1])
    for i in range(Rt.shape[0]):
        V = (V + c[i]) * (1 - 2 * k * sw[i]) * (1 + Rt[i])
    return V


def run(SKt, BDt, M, meta):
    n = SKt.shape[0]; c = g["contrib"](0.0)[:n]; f = FEE[:n, None]; G = G5[:n, None]
    Wb = g["wealth"](G * SKt + (1 - G) * BDt - f, c)
    rows = []
    for th, ra, ex, dl in CELLS:
        on = M[th, ra, ex].astype(float); w = np.minimum(G + dl * on, 1.0)
        x = w - G; sw = np.abs(np.diff(x, axis=0, prepend=x[:1]))       # 첫 달 = 0
        gp = np.minimum(G5[:n] + dl * on.mean(1), 1.0)[:, None]
        dp = np.log(g["wealth"](gp * SKt + (1 - gp) * BDt - f, c) / Wb)
        for kn, k in KS.items():
            d = np.log(wealth_tc(w * SKt + (1 - w) * BDt - f, c, sw, k) / Wb)
            rows.append(dict(**meta, 문턱=th, 재무장=P9.rearm_name(ra), 복귀=EXN[ex], 증액=dl, 편도비용=kn, 편도비용_값=k,
                             비중변경횟수_평균=(sw > 1e-12).sum(0).mean(),   # (G+Δ)−G 부동소수 잔차(~1e-17)는 세지 않는다
                             상한걸린달_비율=(G + dl * on > 1).mean(),
                             d_중앙=np.median(d), d_P5=np.quantile(d, .05), d_P95=np.quantile(d, .95),
                             위약_d_중앙=np.median(dp), 규칙빼기위약_중앙=np.median(d - dp), P_규칙gt위약=(d > dp).mean()))
    return rows


# 자기 점검: 잔액 100에서 Δ=0.1로 한 번 켜졌다 꺼지면(팔기·사기 × 2번) 비용 ≈ 4 × k × Δ × 잔액(오차는 (2kΔ)² × 잔액 이하)
R1 = np.zeros((4, 1)); sw1 = np.array([[0.0], [0.1], [0.0], [0.1]])
cost1 = 100 - wealth_tc(R1, np.array([100.0, 0, 0, 0]), sw1, 0.01)[0]
assert np.isclose(cost1, 100 * (1 - (1 - 0.002) ** 2)) and abs(cost1 - 4 * 0.01 * 0.1 * 100) <= 0.002 ** 2 * 100 + 1e-12
assert np.isclose(wealth_tc(R1, np.ones(4), np.zeros((4, 1)), 0.5)[0], 4.0)
x1 = np.array([[0.1], [0.1], [0.0], [0.1]]); assert np.allclose(np.abs(np.diff(x1, axis=0, prepend=x1[:1]))[:, 0], [0, 0, 0.1, 0.1])

rows = []
for k, x in g["X"].items():
    pwv = float(g["PW"].set_index("표본").loc[k, "PW_적용"]); done = {}
    for bn, b in (("1", 1.0), ("PW", pwv), ("12", 12.0)):
        if b in done: rows += [dict(r, 블록=bn) for r in done[b]]; continue
        SK, BD, CP, KO = g["paired_resample_paths"]([x.stk, x.bd, x.cpi, x.kospi], NP, T, b, SEED)
        M, _ = g["masks"](KO, combos=[(TH, RA)])
        done[b] = run(SK.T.copy(), BD.T.copy(), M, dict(표본=k, 블록=bn)); rows += done[b]; print(k, bn, flush=True)
for b in (120, 1):
    EQ, BD_, IN = P7.pooled_paths(g["PANEL"], ["eq", "bd", "infl"], NP, T, b, SEED)
    M, _ = g["masks"](EQ, combos=[(TH, RA)])
    rows += run(EQ.T.copy(), BD_.T.copy(), M, dict(표본="다국가 9개국 풀", 블록=str(b))); print("mc", b, flush=True)
D = pd.DataFrame(rows)

# 비용 0 = 기존 d, 위약 = 기존 D_placebo.csv(총보수·납입 0%), 비용이 클수록 d가 작다
key = ["표본", "블록", "문턱", "재무장", "복귀", "증액"]
rd = lambda f: (r := pd.read_csv(REF / f, encoding="utf-8-sig", dtype={"블록": str}))[(r.보수 == "총보수") & (r.납입증가 == "0%")]
ref = pd.concat([rd("D_kr_boot.csv"), rd("D_mc_boot.csv")])[key + ["d_중앙"]]
z = D[D.편도비용 == "0"].merge(ref, on=key, suffixes=("", "_기존"), validate="one_to_one")
assert len(z) == len(D) // len(KS) and np.allclose(z.d_중앙, z.d_중앙_기존, rtol=0, atol=1e-12)
zp = D.merge(rd("D_placebo.csv")[key + ["위약_d_중앙"]], on=key, suffixes=("", "_기존"), validate="many_to_one")
assert len(zp) == len(D) and np.allclose(zp.위약_d_중앙, zp.위약_d_중앙_기존, rtol=0, atol=1e-12)
assert (D.sort_values("편도비용_값").groupby(key).d_중앙.apply(lambda s: (np.diff(s.to_numpy()) <= 1e-15).all())).all()
if (OLD := NEW / "D_cost_before_countfix.csv").exists():    # 횟수 수정(2026-11-06) 전후: 횟수 외 칸은 같고 횟수만 줄어든다
    o = pd.read_csv(OLD, encoding="utf-8-sig", dtype={"블록": str, "편도비용": str}); num = D.select_dtypes("number").columns
    cn = num.drop("비중변경횟수_평균"); txt = D.columns.difference(num)
    assert list(o.columns) == list(D.columns) and o[txt].astype(str).equals(D[txt].astype(str))
    assert np.allclose(o[cn], D[cn], rtol=0, atol=1e-12) and (D.비중변경횟수_평균 <= o.비중변경횟수_평균 + 1e-12).all()
    print("수정 전후 최대 차이(횟수 외 숫자 칸):", float(np.abs(o[cn].to_numpy() - D[cn].to_numpy()).max()))
D.to_csv(NEW / "D_cost.csv", index=False, encoding="utf-8-sig")

# 결과 문서: 아래 숫자는 모두 방금 쓴 D_cost.csv에서 읽어 만든다
C = pd.read_csv(NEW / "D_cost.csv", encoding="utf-8-sig", dtype={"블록": str, "편도비용": str})
fmt = lambda v, s=3: "0" if v == 0 else f"{v:.{max(s - 1 - int(np.floor(np.log10(abs(v)))), 0)}f}"   # 유효숫자 3자리
v = C[np.isclose(C.증액, 0.10)].copy(); v["rp"] = v.규칙빼기위약_중앙 * 100
grp = ["표본", "블록", "복귀"]; order = list(KS)
tab = v.pivot_table(index=grp, columns="편도비용", values="rp", sort=False)[order]
base = tab["0"]
lines = [f"| {k} | {fmt(tab[k].min())} ~ {fmt(tab[k].max())} | {fmt((tab[k] - base).min())} ~ {fmt((tab[k] - base).max())} | "
         f"{(tab[k] < 0).sum()} / {len(tab)} | {((base >= 0) & (tab[k] < 0)).sum()} |" for k in order]
chg = v[v.편도비용 == "0"].groupby("복귀").비중변경횟수_평균.agg(["min", "max"])
cap = C.groupby("증액").상한걸린달_비율.max()
body = "\n".join(f"| {' | '.join(map(str, i))} | " + " | ".join(fmt(tab.loc[i, k]) for k in order) + " |" for i in tab.index)
md = f"""# pilot9 D 거래비용 판본 결과 (2026-11-06)

이 문서의 숫자는 모두 `D_cost.csv`({len(C)}행)에서 스크립트가 자동으로 뽑았다. 기존 D_simple 결과 문서의 판정 문장은 옮겨 오지 않았다.

- 코드: `notebooks/pilot9/_run_D_cost_20261106.py` (D_simple_20261017.ipynb 설정·함수 셀을 그대로 실행, 결과는 이 폴더에만 씀)
- 대상 칸: 코스피 −20%·재무장 20%·두 복귀·Δ 5·10·15%p·5대 평균 글라이드·총보수·납입 증가 0%
- 표본: 한국 KR-a·KR-b·KR-a~2024 × 블록 1·PW·12, 다국가 9개국 풀 × 블록 1·120 (seed {SEED}, {NP:,} 경로, {T}개월)

## 비용 모형
- 비용 단위: **편도 = 한 번 거래(팔기 또는 사기)한 금액 대비 비율. 비중을 한 번 바꿀 때 한쪽을 팔고 다른 쪽을 사므로 두 번, 켜졌다 꺼지면 네 번.**
- 바꾼 비중 = 글라이드에서 벗어난 몫(w − 글라이드)이 달 사이에 바뀐 크기. 첫 달은 0. 위험자산 상한 100%가 걸린 달은 실제로 바뀐 만큼만 센다(상한 걸린 달 비율 최대: {", ".join(f"Δ {fmt(d * 100)}%p {fmt(r * 100)}%" for d, r in cap.items())}).
- 그 달 초 납입 뒤 잔액 × 2 × 바꾼 비중 × 편도 비용(파는 쪽·사는 쪽)을 잔액에서 뺀다. 위약(같은 평균 추가 비중을 매달 고정으로 얹음)은 비중을 바꾸지 않으므로 비용 0.

| 편도 비용 | 근거 |
| --- | --- |
| 0.0036396% | 키움 연금저축 ETF 온라인 이벤트 수수료(유관기관 수수료만) |
| 0.015% | 같은 페이지의 일반 ETF 온라인 수수료 |
| 0.1%, 0.3% | 민감도. 호가 차이·펀드 환매 대기일을 넉넉히 잡은 값이며 출처 없음 |

출처: https://www.kiwoom.com/e/wm/event/evtUserEC230018View — 2026-11-06 claude.ai 대화에서 확인한 값이다(이 실행에서 페이지를 다시 열지 않음).

## 열 설명 (`D_cost.csv`)
- `d_중앙·d_P5·d_P95`: 규칙(비용 뺀 뒤) 잔액 ÷ 기준 글라이드 잔액의 로그, 경로 분포의 중앙·5%·95%.
- `위약_d_중앙`: 비용 0인 위약의 d 중앙. 비용 칸마다 같은 값이 반복된다.
- `규칙빼기위약_중앙`: 경로별 (규칙 d, 비용 뺀 뒤) − (위약 d, 비용 0)의 중앙. `P_규칙gt위약`: 그 차이가 0보다 큰 경로 비율.
- `비중변경횟수_평균`: 360개월 동안 바꾼 비중이 1e-12보다 큰 달 수의 경로 평균((글라이드+Δ)−글라이드 계산에서 생기는 1e-17 크기 부동소수 잔차는 거래가 아니므로 뺐다. 비용 계산에는 원래 값을 그대로 써서 d는 바뀌지 않는다).

## 점검 (스크립트 assert, 모두 통과해야 이 문서가 만들어진다)
- 비용 0의 d 중앙 = 기존 D_kr_boot.csv·D_mc_boot.csv 값(차이 1e-12 이하)
- 위약 d 중앙 = 기존 D_placebo.csv(총보수·납입 0%) 값, key(표본·블록·문턱·재무장·복귀·증액)로 맞춰 대조(차이 1e-12 이하)
- 비용이 클수록 d 중앙이 작거나 같다
- 손 계산: 한 번 켜졌다 꺼지면(팔기·사기 × 2번) 비용 ≈ 4 × k × Δ × 잔액(곱셈식이라 차이는 (2kΔ)² × 잔액 이하), 첫 달 바꾼 비중 = 0

## 결과 (Δ +10%p, 규칙빼기위약_중앙, 로그 %)
비중변경횟수_평균(비용 0 행): {"; ".join(f"{i} {fmt(r['min'])}~{fmt(r['max'])}번" for i, r in chg.iterrows())}.

| 편도 비용 | 범위(최소 ~ 최대) | 비용 0 대비 변화(최소 ~ 최대) | 0 미만 칸 | 비용 0에서 0 이상이었다가 0 미만이 된 칸 |
| --- | --- | --- | --- | --- |
{chr(10).join(lines)}

칸별 값:

| 표본 | 블록 | 복귀 | {" | ".join(order)} |
| --- | --- | --- | {" | ".join("---" for _ in order)} |
{body}

## 주의
- 펀드 환매 대기(현금으로 있는 며칠)는 비용률로만 근사했다. 실제 날짜 공백을 넣은 계산은 하지 않았다.
- 0.1%·0.3%는 출처 없는 민감도 값이다.
"""
(NEW / "RESULT_D_cost_20261106.md").write_text(md, encoding="utf-8")
print(md)
from pension_lab import runrecord as rr
rr.write_run_meta(NEW, Path(__file__), ["notebooks/pilot9/D_simple_20261017.ipynb", "src/pension_lab/pilot9.py", "src/pension_lab/pilot7.py",
                                        "src/pension_lab/bootstrap.py"], f"seed={SEED}\nN={NP}\nT={T}\ncosts={KS}\nresult D_cost.csv sha256={rr.raw_sha256(NEW / 'D_cost.csv')}\n")
print("done", NEW)
