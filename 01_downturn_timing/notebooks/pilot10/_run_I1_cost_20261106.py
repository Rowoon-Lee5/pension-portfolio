"""pilot10 I1 거래비용 판본 (2026-11-06, 포트폴리오 정리용 추가 계산). pilot9 D 판본(_run_D_cost_20261106.py)과 같은 비용 모형.

I1_simple_20261017.ipynb의 설정·자기 점검·자료 셀과 다국가 패널 부분을 그대로 실행한 뒤(결과 CSV는 새 폴더로만 씀),
주 줄이기(10개월 평균 아래, 국채로, Δ 5·10·15%p)와 더 담기(D 칸, Δ +5·+10·+15%p)에 비용을 넣는다(총보수·납입 증가 0%).
규칙이 비중을 바꿀 때마다 한쪽을 팔고 다른 쪽을 사므로 '2 × 바꾼 비중 × 편도 비용'을 그 달 납입 뒤 잔액에서 뺀다.
바꾼 비중 sw = |글라이드에서 벗어난 몫(w − G)의 달 사이 변화|, 첫 달 = 0. 위약(정적 경로)은 비중을 바꾸지 않으므로 비용 0.
비용 격자(편도 = 한 번 거래(팔기 또는 사기)한 금액 대비):
  0.0036396% 키움 연금저축 ETF 온라인 이벤트(유관기관 수수료만)  https://www.kiwoom.com/e/wm/event/evtUserEC230018View
  0.015%     같은 페이지의 일반 ETF 온라인 수수료
  0.1%, 0.3% 민감도(호가 차이·펀드 환매 대기일 포함 가정). 출처 없는 값.
빠른 점검: I1C_QUICK=1 → 경로 200개, 결과는 NEW\\_quick에만, 기존 CSV 대조(1e-12, 경로 1만 기준)는 건너뜀.
"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd, nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
NB = ROOT / "notebooks" / "pilot10" / "I1_simple_20261017.ipynb"
REF = Path(r"D:\pension-lab_data\results\pilot10_20261017\I1_cut_hold_add")
QUICK = os.environ.get("I1C_QUICK") == "1"
NEW = Path(r"D:\pension-lab_data\results\pilot10_20261017\I1_cost_20261106") / ("_quick" if QUICK else ""); NEW.mkdir(parents=True, exist_ok=True)
os.chdir(NB.parent); sys.path.insert(0, str(ROOT / "src"))

nomagic = lambda s: "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("%"))   # %matplotlib inline
src = [nomagic(c.source) for c in nbf.read(NB, as_version=4).cells if c.cell_type == "code"]
ns: dict = {"__name__": "i1_cost"}
exec(src[0], ns); ns["OUT"] = NEW                                   # 이후 csv()는 새 폴더에만 쓴다
for s in src[1:3]: exec(s, ns)                                       # 자기 점검, 자료·글라이드·보수
mc = next(s for s in src if s.startswith("MC = pd.read_csv")); exec(mc[:mc.index("MB, MP, MPL")], ns)   # 다국가 패널만
g = ns; P7, P10, T, SEED = g["P7"], g["P10"], g["T"], g["SEED"]; NP = 200 if QUICK else g["NP"]
G, FEE, c = g["G"], g["FEEM"]["총보수"], g["contrib"](0.0)
sub = lambda arms: {a: arms[a] for a in g["PL_ARMS"](arms)}          # 주 줄이기 3 + 더 담기 3
AK, AM = sub(g["ARMS_KR"]), sub(g["ARMS_MC"])
KS = {"0": 0.0, "0.0036%": 0.000036396, "0.015%": 0.00015, "0.1%(민감도)": 0.001, "0.3%(민감도)": 0.003}


def wealth_tc(Rt, c, sw, k):
    '''sw (개월, 경로) = 그 달 초에 바꾼 비중 크기. 납입 뒤 잔액의 2 × k × sw를 비용으로 뺀다(D 판본과 같은 식).'''
    V = np.zeros(Rt.shape[1])
    for i in range(Rt.shape[0]):
        V = (V + c[i]) * (1 - 2 * k * sw[i]) * (1 + Rt[i])
    return V


def run(SKt, BDt, ON, arms, meta):
    n = SKt.shape[0]; f = FEE[:n]; Gn = G[:n, None]; cn = c[:n]
    Wb = P10.wealth(Gn * SKt + (1 - Gn) * BDt - f[:, None], cn)
    W, rows = {}, []
    for a, (kind, sig, dl, _, _) in arms.items():
        on = ON[sig][:n]; R, raw = P10.arm_return(G[:n], on, dl, SKt, BDt, f)
        x = np.clip(raw, 0, 1) - Gn; sw = np.abs(np.diff(x, axis=0, prepend=x[:1]))        # 첫 달 = 0
        dp = np.log(P10.wealth(P10.arm_return(G[:n], on.mean(1)[:, None], dl, SKt, BDt, f)[0], cn) / Wb)
        for kn, k in KS.items():
            W[a, kn] = wealth_tc(R, cn, sw, k); d = np.log(W[a, kn] / Wb)
            rows.append(dict(**meta, 팔=a, 종류=kind, 폭=dl, 편도비용=kn, 편도비용_값=k, 전환_평균=P10.switches(on.T).mean(),
                             비중변경횟수_평균=(sw > 1e-12).sum(0).mean(), 클립달_비율=((raw < 0) | (raw > 1)).mean(),
                             d_중앙=np.median(d), d_P5=np.quantile(d, .05), d_P95=np.quantile(d, .95),
                             위약_d_중앙=np.median(dp), 규칙빼기위약_중앙=np.median(d - dp), P_규칙gt위약=(d > dp).mean()))
    prs = [dict(**meta, 분자=a, 분모=b, 편도비용=kn, 편도비용_값=k, **P10.dist(np.log(W[a, kn] / W[b, kn])))
           for a, b in g["pairs_of"](arms) for kn, k in KS.items()]
    return rows, prs


# 자기 점검: 잔액 100에서 Δ=0.1로 한 번 켜졌다 꺼지면 비용 ≈ 4 × k × Δ × 잔액, 줄이기 팔의 바꾼 비중 = [0, Δ, 0, Δ]
R1 = np.zeros((4, 1)); sw1 = np.array([[0.0], [0.1], [0.0], [0.1]])
cost1 = 100 - wealth_tc(R1, np.array([100.0, 0, 0, 0]), sw1, 0.01)[0]
assert np.isclose(cost1, 100 * (1 - (1 - 0.002) ** 2)) and abs(cost1 - 4 * 0.01 * 0.1 * 100) <= 0.002 ** 2 * 100 + 1e-12
assert np.isclose(wealth_tc(R1, np.ones(4), np.zeros((4, 1)), 0.5)[0], 4.0)
_, raw1 = P10.arm_return(np.full(4, 0.6), np.array([[0], [1], [1], [0]]), -0.1, R1, R1, np.zeros(4))
x1 = raw1 - 0.6; assert np.allclose(np.abs(np.diff(x1, axis=0, prepend=x1[:1]))[:, 0], [0, 0.1, 0, 0.1])

rows, prs = [], []
for k, x in g["X"].items():
    pwv = float(g["PW"].set_index("표본").loc[k, "PW_적용"]); done = {}
    for bn, b in (("1", 1.0), ("PW", pwv), ("12", 12.0)):
        if b not in done:
            SK, BD, CP, KO, CA = g["paired_resample_paths"]([x.stk, x.bd, x.cpi, x.kospi, x.cash], NP, T, b, SEED)
            done[b] = run(SK.T.copy(), BD.T.copy(), g["signals"](KO)[0], AK, dict(표본=k, 블록=None))
        rows += [dict(r, 블록=bn) for r in done[b][0]]; prs += [dict(r, 블록=bn) for r in done[b][1]]; print(k, bn, flush=True)
for b in (120, 1):
    EQ, BD_, IN = P7.pooled_paths(g["PANEL"], ["eq", "bd", "infl"], NP, T, b, SEED)
    r, p = run(EQ.T.copy(), BD_.T.copy(), g["signals"](EQ)[0], AM, dict(표본="다국가 9개국 풀", 블록=str(b))); rows += r; prs += p; print("mc", b, flush=True)
D, PR = pd.DataFrame(rows), pd.DataFrame(prs)

# 점검: 비용 0 = 기존 d·쌍, 위약 = 기존 I1_placebo.csv(총보수·납입 0%), 비용이 클수록 d가 작다, 클립 없음 → 바꾼 횟수 = 전환 횟수
key, pk = ["표본", "블록", "팔"], ["표본", "블록", "분자", "분모"]
close = lambda a, b: np.allclose(a, b, rtol=0, atol=1e-12)
if not QUICK:
    rd = lambda f: (r := pd.read_csv(REF / f, encoding="utf-8-sig", dtype={"블록": str}))[(r.보수 == "총보수") & (r.납입증가 == "0%")]
    z = D[D.편도비용 == "0"].merge(pd.concat([rd("I1_kr_boot.csv"), rd("I1_mc_boot.csv")])[key + ["d_중앙", "d_P5", "d_P95"]],
                                  on=key, suffixes=("", "_기존"), validate="one_to_one")
    assert len(z) == len(D) // len(KS) and all(close(z[q], z[q + "_기존"]) for q in ("d_중앙", "d_P5", "d_P95"))
    zp = D.merge(rd("I1_placebo.csv")[key + ["위약_d_중앙", "규칙빼기위약_중앙", "P_규칙gt위약"]], on=key, suffixes=("", "_기존"), validate="many_to_one")
    z0 = zp[zp.편도비용 == "0"]
    assert len(zp) == len(D) and close(zp.위약_d_중앙, zp.위약_d_중앙_기존) and close(z0.규칙빼기위약_중앙, z0.규칙빼기위약_중앙_기존) \
        and close(z0.P_규칙gt위약, z0.P_규칙gt위약_기존)
    zq = PR[PR.편도비용 == "0"].merge(pd.concat([rd("I1_kr_pairs.csv"), rd("I1_mc_pairs.csv")])[pk + ["d_중앙", "d_P5", "d_P95", "P_d양수"]],
                                     on=pk, suffixes=("", "_기존"), validate="one_to_one")
    assert len(zq) == len(PR) // len(KS) and all(close(zq[q], zq[q + "_기존"]) for q in ("d_중앙", "d_P5", "d_P95", "P_d양수"))
    print("기존 대조 통과:", len(z), "팔 칸,", len(zq), "쌍 칸,", len(zp), "위약 행")
assert (D.sort_values("편도비용_값").groupby(key).d_중앙.apply(lambda s: (np.diff(s.to_numpy()) <= 1e-15).all())).all()
assert (D.클립달_비율 == 0).all() and close(D.비중변경횟수_평균, D.전환_평균)
D.to_csv(NEW / "I1_cost.csv", index=False, encoding="utf-8-sig"); PR.to_csv(NEW / "I1_cost_pairs.csv", index=False, encoding="utf-8-sig")

# 결과 문서: 아래 숫자는 모두 방금 쓴 CSV에서 읽어 만든다
C = pd.read_csv(NEW / "I1_cost.csv", encoding="utf-8-sig", dtype={"블록": str, "편도비용": str})
CP_ = pd.read_csv(NEW / "I1_cost_pairs.csv", encoding="utf-8-sig", dtype={"블록": str, "편도비용": str})
fmt = lambda v, s=3: "0" if v == 0 else f"{v:.{max(s - 1 - int(np.floor(np.log10(abs(v)))), 0)}f}"   # 유효숫자 3자리
order = list(KS); idx = ["표본", "블록"]


def section(v, col, title, neg):
    tab = v.pivot_table(index=idx, columns="편도비용", values=col, sort=False)[order] * 100; base = tab["0"]
    lines = [f"| {k} | {fmt(tab[k].min())} ~ {fmt(tab[k].max())} | {fmt((tab[k] - base).min())} ~ {fmt((tab[k] - base).max())} | "
             f"{(tab[k] < 0).sum()} / {len(tab)} | {((base >= 0) & (tab[k] < 0)).sum()} |" for k in order]
    body = "\n".join(f"| {' | '.join(map(str, i))} | " + " | ".join(fmt(tab.loc[i, k]) for k in order) + " |" for i in tab.index)
    return f"""### {title}

| 편도 비용 | 범위(최소 ~ 최대) | 비용 0 대비 변화(최소 ~ 최대) | 0 미만 칸 | 비용 0에서 0 이상이었다가 0 미만이 된 칸 |
| --- | --- | --- | --- | --- |
{chr(10).join(lines)}

| 표본 | 블록 | {" | ".join(order)} |
| --- | --- | {" | ".join("---" for _ in order)} |
{body}
{neg}"""


v10 = C[np.isclose(C.폭.abs(), 0.10)]
chg = v10[v10.편도비용 == "0"].groupby("종류").비중변경횟수_평균.agg(["min", "max"])
md = f"""# pilot10 I1 거래비용 판본 결과 (2026-11-06){" — 빠른 점검(경로 200, 기존 대조 생략)" if QUICK else ""}

이 문서의 숫자는 모두 `I1_cost.csv`({len(C)}행)·`I1_cost_pairs.csv`({len(CP_)}행)에서 스크립트가 자동으로 뽑았다. 기존 I1 결과 문서의 판정 문장은 옮겨 오지 않았다.

- 코드: `notebooks/pilot10/_run_I1_cost_20261106.py` (I1_simple_20261017.ipynb 설정·자기 점검·자료 셀을 그대로 실행, 결과는 이 폴더에만 씀). 비용 모형은 pilot9 D 판본(`_run_D_cost_20261106.py`)과 같다.
- 대상 팔: 줄이기(코스피 가격 < 10개월 평균이면 다음 달 G − Δ, 줄인 몫은 국고채 TR. 다국가는 자국 주식 총수익 신호)와 더 담기(D 칸: 코스피 −20%·재무장 20%·전고점 회복, G + Δ), Δ 5·10·15%p, 5대 평균 글라이드·총보수·납입 증가 0%
- 표본: 한국 KR-a·KR-b·KR-a~2024 × 블록 1·PW·12, 다국가 9개국 풀 × 블록 120·1 (seed {SEED}, {NP:,} 경로, {T}개월)

## 비용 모형
- 비용 단위: **편도 = 한 번 거래(팔기 또는 사기)한 금액 대비 비율. 비중을 한 번 바꿀 때 한쪽을 팔고 다른 쪽을 사므로 두 번, 켜졌다 꺼지면 네 번.**
- 바꾼 비중 = 글라이드에서 벗어난 몫(w − 글라이드)이 달 사이에 바뀐 크기. 첫 달은 0. 비중 0%·100% 한계에 닿은 경로-월은 모든 칸에서 0(클립달_비율 최대 {fmt(C.클립달_비율.max())}).
- 그 달 초 납입 뒤 잔액 × 2 × 바꾼 비중 × 편도 비용을 잔액에서 뺀다. 위약(켜짐의 월별 경로 평균 × Δ를 모든 경로에 매달 고정)은 비중을 바꾸지 않으므로 비용 0.
- 쌍 비교 ln(W_더담기/W_줄이기)는 두 팔 모두 같은 편도 비용을 뺀 뒤의 값이다.

| 편도 비용 | 근거 |
| --- | --- |
| 0.0036396% | 키움 연금저축 ETF 온라인 이벤트 수수료(유관기관 수수료만) |
| 0.015% | 같은 페이지의 일반 ETF 온라인 수수료 |
| 0.1%, 0.3% | 민감도. 호가 차이·펀드 환매 대기일을 넉넉히 잡은 값이며 출처 없음 |

출처: https://www.kiwoom.com/e/wm/event/evtUserEC230018View — 2026-11-06 claude.ai 대화에서 확인한 값이다(이 실행에서 페이지를 다시 열지 않음).

## 열 설명
- `I1_cost.csv` `d_중앙·d_P5·d_P95`: 팔(비용 뺀 뒤) 잔액 ÷ 그대로(글라이드) 잔액의 로그, 경로 분포의 중앙·5%·95%.
- `위약_d_중앙`: 비용 0인 위약의 d 중앙(비용 칸마다 같은 값 반복). `규칙빼기위약_중앙`: 경로별 (팔 d, 비용 뺀 뒤) − (위약 d, 비용 0)의 중앙. `P_규칙gt위약`: 그 차이가 0보다 큰 경로 비율.
- `비중변경횟수_평균`: 360개월 동안 바꾼 비중이 1e-12보다 큰 달 수의 경로 평균(부동소수 잔차 제외, 비용 계산에는 원래 값). `전환_평균`: 켜짐↔꺼짐 전환 횟수(기존 I1과 같은 정의).
- `I1_cost_pairs.csv` `d_중앙·d_P5·d_P95·P_d양수·P_d영`: ln(W_분자/W_분모)의 경로 분포.

## 점검 (스크립트 assert, 모두 통과해야 이 문서가 만들어진다)
{"- (빠른 점검: 기존 CSV 대조 3개는 경로 수가 달라 건너뜀)" if QUICK else ""}
- 비용 0의 d 중앙·P5·P95 = 기존 I1_kr_boot.csv·I1_mc_boot.csv(총보수·납입 0%) 값(차이 1e-12 이하)
- 위약 d 중앙 = 기존 I1_placebo.csv 값(모든 비용 행), 비용 0의 규칙빼기위약_중앙·P_규칙gt위약 = 기존 값, key(표본·블록·팔)로 대조(차이 1e-12 이하)
- 비용 0의 쌍 d 중앙·P5·P95·P_d양수 = 기존 I1_kr_pairs.csv·I1_mc_pairs.csv 값(차이 1e-12 이하)
- 비용이 클수록 팔 d 중앙이 작거나 같다. 비중 한계에 닿은 달 없음, 바꾼 횟수 = 전환 횟수.
- 손 계산: 한 번 켜졌다 꺼지면 비용 ≈ 4 × k × Δ × 잔액(곱셈식이라 차이는 (2kΔ)² × 잔액 이하), 첫 달 바꾼 비중 = 0, 줄이기 팔(켜짐 0·1·1·0)의 바꾼 비중 = 0·Δ·0·Δ

## 결과 (|Δ| = 10%p, 로그 %)
비중변경횟수_평균(비용 0 행): {"; ".join(f"{i} {fmt(r['min'])}~{fmt(r['max'])}번" for i, r in chg.iterrows())}.

{section(v10[v10.종류 == "줄이기"], "규칙빼기위약_중앙", "줄이기 −10 대 위약 (규칙빼기위약_중앙)", "")}
{section(v10[v10.종류 == "더담기"], "규칙빼기위약_중앙", "더 담기 +10 대 위약 (규칙빼기위약_중앙)", "")}
{section(CP_[CP_.분자 == "더담기_D_+10"], "d_중앙", "더 담기 +10 대 줄이기 −10 (쌍 d_중앙 = ln(W_더담기/W_줄이기))", "")}
## 주의
- 펀드 환매 대기(현금으로 있는 며칠)는 비용률로만 근사했다. 실제 날짜 공백을 넣은 계산은 하지 않았다.
- 0.1%·0.3%는 출처 없는 민감도 값이다.
- 두 팔은 바꾼 횟수가 다르다(위 비중변경횟수_평균). 두 팔은 신호와 방향이 동시에 다르다(기존 I1 한계 그대로).
"""
(NEW / "RESULT_I1_cost_20261106.md").write_text(md, encoding="utf-8")
print(md)
from pension_lab import runrecord as rr
rr.write_run_meta(NEW, Path(__file__), ["notebooks/pilot10/I1_simple_20261017.ipynb", "src/pension_lab/pilot10.py", "src/pension_lab/pilot9.py",
                                        "src/pension_lab/pilot7.py", "src/pension_lab/bootstrap.py"],
                  f"seed={SEED}\nN={NP}\nT={T}\nquick={QUICK}\ncosts={KS}\n" + "".join(f"result {f} sha256={rr.raw_sha256(NEW / f)}\n" for f in ("I1_cost.csv", "I1_cost_pairs.csv")))
print("done", NEW)
