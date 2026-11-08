"""README 숫자 대조: 저장소 안 결과 CSV에서 README 숫자를 다시 계산해, 문장 단위로 맞는지 assert한다(새 시뮬레이션 없음).

규칙 하나 = (폴더, README 문장 조각, 값들). 문장 조각의 {} 자리에 README가 쓴 글자가 결과 CSV에서 다시 계산해
반올림 규칙대로 만든 문자열과 똑같아야 한다. 같은 문장 조각이 README에 여러 번 나오면 모두 같아야 하고, 한 번도 없으면 실패.
그림·README 생성기(make_figures.py·make_topics_a.py·make_topics_b.py)는 쓰지 않고 CSV를 직접 읽어 다시 센다.

다루는 것(폴더별 README 본문 '결과'·'한 일' 숫자와 English summary, 루트 README 표·English summary):
  01 해지·멈춤·당겨넣기 범위, 손실 경로 비율, 더 담기 규칙 234칸·문턱별·예시 칸, 거래비용, 더 담기 대 줄이기
  02 기간별 표 전체 칸(차이·p), 점추정 범위, 보수 분해, 헤지 가정, 운용사별 나머지
  03 상담표 전체 칸, ※ 칸 수, 경계 1%p 칸, 이자 반영 시점·75·80·85·90세·3년 만기 단락 숫자
  04~07 결과 숫자(대출·담보부족, 두 통·리밸런싱, 목돈·나눠 넣기·CER, 2055 TDF 비·추적오차·MDE)
  08~11 결과 숫자(피신 R·구간·판정·사건 수·한국 사건·자금흐름, 글라이드 변경 펀드 수·운용사 줄·가장 큰 차이,
        재매수 판정 수·경계 폭·보류, 원화 30년 비율·MDE·하락 국면)
다루지 않는 것(이 저장소 CSV로 다시 셀 수 없음): 08 9개국 구간 끝값 P5·P95는 CSV 값을 그대로 씀(부트스트랩 재실행 안 함),
  09 '변경 9번 중 7번'·국면 수(사후 국면표가 저장소에 없음), 10 '경계 밖으로 16~25%p'(비중 원값을 뺌),
  03 '+0.558~+0.640'·'6,526,097원', 06 단일국 고점 창·Wilson 구간, 07 |t|·패널 기울기, 각 폴더 '한계' 절의 일부 숫자.

실행: python check_numbers.py              (통과하면 폴더별 규칙 수와 'ok')
      python check_numbers.py --selftest   (README 사본의 숫자 한 글자씩을 틀리게 바꿔 규칙이 실패하는지 시험 + 사본 파일 전체 실행)
      python check_numbers.py --csv 경로    (03 상담표 전체를 CSV로도 저장)
      python check_numbers.py --readme-dir 폴더   (README를 그 폴더의 같은 상대 경로 사본에서 읽음, 결과 CSV는 저장소 것)
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
D = dict(r=".", t1="01_downturn_timing", t2="02_tdf_vs_diy", t3="03_selfemployed_50s", t4="04_loan_vs_withdraw",
         t5="05_two_buckets_free_rebalancing", t6="06_lumpsum_vs_dca", t7="07_tdf_glidepath_by_manager",
         t8="08_shelter_in_account", t9="09_glidepath_changes", t10="10_tdf_rebuy_holdings", t11="11_krw_30y")
T1, T2, T3 = ROOT / D["t1"], ROOT / D["t2"], ROOT / D["t3"]
rd = lambda p: pd.read_csv(ROOT / p, encoding="utf-8-sig")
U = lambda s: s.replace("-", "−")                                             # U+2212 쓰는 폴더(01·02·03 표)


def sg(x, k=2):
    """부호 붙인 소수 k자리, 반올림해 0이면 부호 없이."""
    t = f"{x:+.{k}f}"
    return f"{0:.{k}f}" if float(t) == 0 else t


def pr(a, b, k=0):
    """a·b(비율)를 % 범위로: 같으면 한 값(make_topics_a.py와 같은 표기 규칙)."""
    x, y = f"{a * 100:.{k}f}", f"{b * 100:.{k}f}"
    return x if x == y else f"{x}~{y}"


class Rules(list):
    def add(self, where, tpl, *vals):
        assert not tpl.endswith("{}") and tpl.count("{}") == len(vals), tpl
        self.append((D[where], tpl, tuple(map(str, vals))))


rx = lambda tpl: re.compile(re.escape(tpl).replace(r"\{\}", r"([^|*\n]+?)"))      # 값 자리는 표 칸·굵은 글씨·줄을 넘지 않음


def check(rules, texts):
    """실패한 규칙 목록: (폴더, 문장 조각, 기대 값, README에서 찾은 값들)."""
    bad = []
    for w, tpl, vals in rules:
        ms = [m.groups() for m in rx(tpl).finditer(texts[w])]
        if not ms or any(g != vals for g in ms):
            bad.append((w, tpl, vals, ms))
    return bad


def load(base):
    return {w: (base / w / "README.md").read_text(encoding="utf-8") for w in D.values()}


# ── 01 ───────────────────────────────────────────────────────────────────────
def t4():
    """첫 하락장: 주식 100%, 다섯 표본의 전략별 'A(계속 넣기) 대비 30년 실질 자산 − 1' 칸별 중앙값 범위(%, 반올림 전)."""
    b = rd(f"{D['t1']}/results/pilot7/T4_boot.csv")
    S = {"KR 1991~": "한국 1991~", "KR 2004~": "한국 2004~", "US 1965~ (월말)": "미국 1965~",
         "French 22개국 풀링(월, USD 실질)": "22개국", "OECD 17개국 풀링(월, 현지통화 실질, 국채 합성)": "17개국"}
    c = b[(b["포트폴리오"] == "주식100") & b["표본"].isin(S)].assign(v=lambda d: (d["A대비 중앙값"] - 1) * 100, 표본=lambda d: d["표본"].map(S))
    out = c.groupby(["전략", "표본"]).v.agg(["min", "max"])
    lv = rd(f"{D['t1']}/results/pilot7/T4_level.csv")
    lv = lv[(lv["포트폴리오"] == "주식100") & lv["표본"].isin(S)].assign(표본=lambda d: d["표본"].map(S))
    loss = lv.groupby("표본")["A: P(실질자산<실질납입)"].agg(["min", "max"]) * 100
    return out, loss


def d_rule():
    p = rd(f"{D['t1']}/results/pilot9_D_simple/D_placebo.csv")
    pr_ = p["P_규칙gt위약"]
    key = p[(p["표본"] == "KR-a") & (p["블록"].astype(str) == "1") & (p["문턱"] == -0.2) & (p["복귀"] == "전고점 회복") & np.isclose(p["증액"], 0.10)]
    assert len(key) == 1
    k = key.iloc[0]
    c = rd(f"{D['t1']}/results/pilot9_D_cost/D_cost.csv")
    c = c[c["문턱"] == -0.2]
    cost = c.groupby("편도비용")["규칙빼기위약_중앙"].agg(["min", "max", "size"]) * [100, 100, 1]
    # 234칸 = 문턱 −10·−20·−30% 각 78칸. 문턱별 P 범위, 0.5 초과 칸, 칸 수, 규칙 − 위약 중앙값이 음수인 칸
    th = {t: (round(g.min(), 2), round(g.max(), 2), int((g > 0.5).sum()), len(g), int((p.loc[g.index, "규칙빼기위약_중앙"] < 0).sum()))
          for t, g in pr_.groupby(p["문턱"])}
    return th, dict(칸=len(p), P최소=round(pr_.min(), 2), P최대=round(pr_.max(), 2), P_05초과=int((pr_ > 0.5).sum()),
                    예시_규칙=round(k["규칙_d_중앙"] * 100, 2), 예시_위약=round(k["위약_d_중앙"] * 100, 2), 예시_P=round(k["P_규칙gt위약"] * 100, 1)), cost


def r01(R):
    out, loss = t4()
    S5 = ["한국 1991~", "한국 2004~", "미국 1965~", "22개국", "17개국"]
    C, f1 = out.loc["C 해지"], lambda x: U(f"{x:.1f}")
    assert C["max"].max() < 0 and out.loc["D÷Y(타이밍 효과, 짝지음)"].abs().max().max() < 0.25
    R.add("t1", "적었습니다. 한국 1991~ {}~{}%, 한국 2004~ {}~{}%, 미국 1965~ {}~{}%, 22개국 {}~{}%, 17개국 {}~{}%(주식 100%",
          *[f1(C.loc[s, m]) for s in S5 for m in ("max", "min")])
    rg2 = lambda st, k: (U(sg(out.loc[st, "min"].min(), k)), U(sg(out.loc[st, "max"].max(), k)))
    R.add("t1", "**멈췄다 몰아넣기(B)**: {}~{}%로", *rg2("B 중단", 2))
    R.add("t1", "**당겨넣기(D)**: {}~{}%였지만, 같은 돈을 연말에 넣은 대조군(Y)도 {}~{}%였습니다. 하락장 타이밍 몫(D÷Y)은 {}~{}%입니다",
          *rg2("D 당겨넣기", 1), *rg2("Y 대조군(연말)", 1), *rg2("D÷Y(타이밍 효과, 짝지음)", 2))
    f2 = lambda x: f"{x:.2f}"
    R.add("t1", "실질 납입액보다 적은 경로 비율은 표본·블록별로 {}~{}%입니다(한국 1991~ {}~{}%, 한국 2004~ {}~{}%, 미국 {}~{}%, 22개국 {}~{}%, 17개국 {}~{}%)",
          f2(loss["min"].min()), f2(loss["max"].max()), *[f2(loss.loc[s, m]) for s in S5 for m in ("min", "max")])
    lo6, hi6 = f"{-C['max'].max():.1f}", f"{-C['min'].min():.1f}"
    R.add("t1", "left median real wealth {}–{}% lower than continuing", lo6, hi6)
    R.add("t1", "ending below real contributions when continuing was {}–{}%.", f2(loss["min"].min()), f2(loss["max"].max()))
    R.add("r", "첫 하락장에서 해지하면 30년 뒤 실질 자산 중앙값이 다섯 표본 모두 {}~{}% 적었다", lo6, hi6)
    R.add("r", "canceling cost {}–{}% of median 30-year real wealth across five samples", lo6, hi6)

    th, d, cost = d_rule()
    assert d == dict(칸=234, P최소=0.16, P최대=0.59, P_05초과=51, 예시_규칙=6.46, 예시_위약=6.59, 예시_P=50.5), d
    t = {k: [f2(v[0]), f2(v[1]), *v[2:]] for k, v in th.items()}                 # 최소, 최대, 0.5 초과, 칸, 음수 칸
    assert d["P최소"] == th[-0.1][0]
    R.add("t1", "**더 담기 규칙 대 위약**: {}칸 전체에서 '규칙이 위약보다 큰 경로 비율'은 {}~{}였고, 0.5를 넘은 칸은 {}개입니다.",
          d["칸"], f2(d["P최소"]), f2(d["P최대"]), d["P_05초과"])
    R.add("t1", "문턱별로는 −10% {}~{}(0.5 초과 {}칸/{}), −20% {}~{}({}칸/{}), −30% {}~{}({}칸/{})입니다.", *t[-0.1][:4], *t[-0.2][:4], *t[-0.3][:4])
    R.add("t1", "최솟값 {}은 −10% 칸에서 나왔고, −10%에서는 {}칸 중 {}칸에서 규칙 − 위약 경로별 차의 중앙값이 0보다 작았습니다(−20% {}칸, −30% {}칸).",
          f2(th[-0.1][0]), t[-0.1][3], t[-0.1][4], t[-0.2][4], t[-0.3][4])
    R.add("t1", "전고점 복귀)은 규칙 {}, 위약 {} 로그%로, 규칙이 더 큰 경로가 {}%였습니다.", f2(d["예시_규칙"]), f2(d["예시_위약"]), d["예시_P"])
    R.add("t1", "(share of paths where the rule won: {}–{} overall; {}–{} at −10%, {}–{} at −20%, {}–{} at −30%)",
          f2(d["P최소"]), f2(d["P최대"]), *t[-0.1][:2], *t[-0.2][:2], *t[-0.3][:2])
    R.add("t1", "−30%; {} settings each, {} in all)", t[-0.2][3], d["칸"])
    R.add("r", "(규칙이 더 큰 경로 비율: {}칸 전체 {}~{}, 문턱 −20% {}~{}, −30% {}~{}, −10% {}~{})",
          d["칸"], f2(d["P최소"]), f2(d["P최대"]), *t[-0.2][:2], *t[-0.3][:2], *t[-0.1][:2])
    cs = lambda k: (U(sg(cost.loc[k, "min"])), U(sg(cost.loc[k, "max"])))
    R.add("t1", "**거래비용**(문턱 −20%, {}칸, 규칙 − 위약의 경로별 차 중앙): 비용 0에서 {}~{}, 0.015%에서 {}~{}, 0.3%(민감도)에서 {}~{} 로그%p.",
          int(cost.loc["0", "size"]), *cs("0"), *cs("0.015%"), *cs("0.3%(민감도)"))

    pp = rd(f"{D['t1']}/results/pilot10_I1_cost/I1_cost_pairs.csv")
    pp = pp[pp["분자"] == "더담기_D_+10"]
    assert (pp["d_중앙"] > 0).all()
    ip = lambda k: [sg(v * 100) for v in pp[pp["편도비용"].astype(str) == k]["d_중앙"].agg(["min", "max"])]
    ic = rd(f"{D['t1']}/results/pilot10_I1_cost/I1_cost.csv")
    ic = ic[ic["편도비용"].astype(str) == "0"].groupby("종류")["비중변경횟수_평균"].agg(["min", "max"]).map(lambda x: f"{x:.0f}")
    R.add("t1", "**더 담기 대 줄이기**: {}칸 모두 더 담기 쪽 60세 금액이 컸습니다(경로별 로그 비의 중앙 {}~{} 로그%, 비용 0).",
          pp.groupby(["표본", "블록"]).ngroups, *ip("0"))
    R.add("t1", "(0.3%에서 {}~{}). 30년 동안 비중을 바꾼 횟수가 줄이기는 경로 평균 {}~{}번, 더 담기는 {}~{}번",
          *ip("0.3%(민감도)"), *ic.loc["줄이기"], *ic.loc["더담기"])
    return out, loss, th, d, cost


# ── 02 ───────────────────────────────────────────────────────────────────────
def r02(R):
    t = rd(f"{D['t2']}/figures/fig3_T7_보수분해_data.csv")
    p3 = lambda p: "<0.001" if p < 0.001 else f"{p:.3f}".rstrip("0")
    for per, g in t.groupby("기간", sort=False):
        s, h = g[g["비교"] == "스타일 모형"].iloc[0], g[g["비교"] == "보유내역"].iloc[0]
        name, mon = re.fullmatch(r"(.+?)\s*\((\d+)개월\)", s["기간명"]).groups()
        R.add("t2", f"| {name} ({{}}개월) | {{}}%p (p {{}}) | {{}}%p (p{{}}) | {{}}%p (p {{}}) |",
              mon, U(f"{s['총차이']:.2f}"), f"{s['p_총차이']:.2f}", U(f"{h['총차이']:.2f}"),
              ("" if h["p_총차이"] < 0.001 else " ") + p3(h["p_총차이"]), U(f"{h['나머지']:.2f}"), p3(h["p_나머지"]))
    tot, fee = t["총차이"], t["겉보수"].iloc[0] + t["하위보수"].iloc[0]
    assert t["겉보수"].nunique() == 1 and t["하위보수"].nunique() == 1 and len(t) == 6
    R.add("t2", "비교 6개(기간 3 × 직접 운용 방식 2)의 점추정은 {}~{}%p이고", U(f"{tot.max():.2f}"), U(f"{tot.min():.2f}"))
    R.add("t2", "보수는 연 {}%p입니다(겉보수 {}% + 안에 담은 펀드 보수 {}%). 차이의 하한({}%p)이 보수보다 작아",
          f"{fee:.2f}", f"{t['겉보수'].iloc[0]:.2f}", f"{t['하위보수'].iloc[0]:.2f}", f"{-tot.max():.2f}")
    h = t[(t["기간"] == "전체") & (t["비교"] == "보유내역")].iloc[0]
    R.add("t2", "전부 헤지로 보면 {}%p, 전부 비헤지로 보면 {}%p입니다.", U(f"{h['헤지_전부']:.2f}"), U(f"{h['헤지_전부비']:.2f}"))
    m = rd(f"{D['t2']}/results/pilot7/T7_holdings_by_manager.csv").set_index(["기간", "운용사"])["TDF−⑥ + 합성보수(보수 외 차이)(연)"]
    R.add("t2", "보수 외 나머지(2022~26)는 KB {}%p, 삼성 {}%p, 한국투자 {}%p로", *[U(sg(m.loc[("전체", k)] * 100)) for k in ("KB", "삼성", "한국투자")])
    rem = t[t["비교"] == "보유내역"]["나머지"]
    n05 = int((t["p_총차이"] < 0.05).sum())
    R.add("t2", "point estimates {}–{} percentage points a year below", f"{-tot.max():.1f}", f"{-tot.min():.1f}")
    R.add("t2", "only {} of the six are distinguishable from zero (HAC p<0.05). Explicit fees are {} pp a year. The non-fee remainder (about {} to {} pp",
          {2: "two"}[n05], f"{fee:.2f}", U(f"{rem.max():.1f}"), U(f"{rem.min():.1f}"))
    R.add("r", "연 수익률 차이는 비교 {}개(기간 {} × 직접 운용 방식 {})에서 {}~{}%p였고, 0과 구분되는 것(HAC p<0.05)은 {}개다. 보수는 연 {}%p이고",
          len(t), t["기간"].nunique(), t["비교"].nunique(), U(f"{tot.max():.1f}"), U(f"{tot.min():.1f}"), n05, f"{fee:.2f}")
    R.add("r", "(point estimates of {} to {} pp a year across six comparisons, two of them distinguishable from zero; fees are {} pp a year)",
          U(f"{tot.max():.1f}"), U(f"{tot.min():.1f}"), f"{fee:.2f}")
    return t


# ── 03 ───────────────────────────────────────────────────────────────────────
def verdict(x):
    """작성자가 정한 판정 말(2026-11-07, 결과를 본 뒤 정함). x = 예금보다 적었던 비율."""
    return "유리" if x < 0.15 else "대체로 유리" if x <= 0.35 else "비슷" if x <= 0.65 else "불리"


def cand5():
    """상담표: 주식 100%(asset A)·월 30만 원·기준 셀. 칸마다 과거 시작 연도 수(앞쪽 < 예금 / 전체),
    부트스트랩 1만 경로 중 앞쪽 < 예금 비율(블록 3종 최소~최대), 판정(부트스트랩 범위 가운데값), 과거 연도 비율로 낸 판정."""
    g = rd(f"{D['t3']}/results/N/grid_stats.csv")
    g = g[(g["cell"] == "base") & (g["m"] == 300000) & (g["asset"] == "A")]
    b = rd(f"{D['t3']}/results/N/boot_stats.csv")
    b = b[(b["m"] == 300000) & (b["asset"] == "A")]
    W = dict(zip(["wd36", "wd60", "p62", "p70"], ["3년째", "5년째", "62세", "70세"]))
    spec = [("연금저축 < 예금, 세금 0원 (가)", "ps<dep", "가", W), ("연금저축 < 예금, 세금 내는 사람 (다)", "ps<dep", "다", W),
            ("노란우산 그냥 해약 < 예금 (가)", "ny_cancel<dep", "가", ["wd36", "wd60", "p62"])]
    spec += [(f"노란우산 폐업·노령 < 예금, {lab} ({who})", "ny_close<dep", who, W)
             for who, lab in zip("가나다", ["세금 0원", "세금 조금", "세금 많이"])]
    rows = []
    for label, pair, who, ws in spec:
        for w in ws:
            pr_ = "ny_old<dep" if (pair == "ny_close<dep" and w == "p70") else pair
            h = g[(g["쌍"] == pr_) & (g["비교"] == w) & (g["person"] == who)].iloc[0]
            bb = b[(b["쌍"] == pr_) & (b["비교"] == w) & (b["person"] == who)]["p_loss"]
            assert len(bb) == 3, (pr_, w, who)
            lo, hi = bb.min(), bb.max()
            rows.append(dict(비교=label, 시점=W[w], 쌍=pr_, person=who, 과거_적은해=int(h.loss_n), 과거_전체=int(h.n),
                             과거_비율=h.loss_n / h.n, 과거_판정=verdict(h.loss_n / h.n),
                             부트_최소=lo, 부트_최대=hi, 부트_가운데=(lo + hi) / 2, 판정=verdict((lo + hi) / 2)))
    t = pd.DataFrame(rows)
    t["판정_다름"] = t["판정"] != t["과거_판정"]
    t["경계_1pp"] = [min(abs(m - c) for c in (0.15, 0.35, 0.65)) < 0.01 for m in t["부트_가운데"]]
    pct = lambda x: f"{round(x * 100):.0f}"
    t["칸"] = [f"{r.과거_적은해}/{r.과거_전체} · " + (f"{pct(r.부트_최소)}%" if pct(r.부트_최소) == pct(r.부트_최대) else f"{pct(r.부트_최소)}~{pct(r.부트_최대)}%")
              + f" · {r.판정}" + (f" ※(과거: {r.과거_판정})" if r.판정_다름 else "") for r in t.itertuples()]
    t["판정_기준"] = "부트스트랩 가운데값"
    bp = rd(f"{D['t3']}/results/N/bp_stats.csv")
    bp = bp[(bp.m == 300000) & (bp.asset == "A") & (bp.person == "가") & (bp.b == "B") & (bp.K1 == "전액") & (bp.K2 == "안넣음") & (bp["쌍"] == "ps<dep")]
    # 사람 B(기초연금): 부트스트랩 없음 → 과거 연도 비율로 판정. 표에는 중소도시·대도시만.
    tb = pd.DataFrame([dict(비교=f"연금저축 < 예금, 세금 0원 + 기초연금 경계 (사람 B, {r.region})", 시점="70세", 쌍="ps<dep", person="가",
                            과거_적은해=int(r.loss_n), 과거_전체=int(r.n), 과거_비율=r.loss_n / r.n, 과거_판정=verdict(r.loss_n / r.n),
                            판정=verdict(r.loss_n / r.n), 판정_다름=False, 경계_1pp=False, 판정_기준="과거 연도(부트스트랩 없음)",
                            칸=f"{int(r.loss_n)}/{int(r.n)} · 부트스트랩 없음 · {verdict(r.loss_n / r.n)}(과거 기준)")
                       for r in bp.itertuples() if r.region != "농어촌"])
    return t, tb


def cand5_ext():
    """사람 B (가)·★ 칸(K1 전액, 기본판 K2 안넣음, 연기판 K2 넣음)·주식 100%·월 30만·중소도시, 연금저축 < 예금.
    값 = '손해/전체 · 차이 중앙값(÷ 누적 납입)'."""
    def cell(f, K2):
        s = rd(f"{D['t3']}/results/N/{f}")
        s = s[(s.m == 300000) & (s.asset == "A") & (s.person == "가") & (s.b == "B") & (s.K1 == "전액") & (s.K2 == K2)
              & (s.region == "중소도시") & (s["쌍"] == "ps<dep")]
        assert len(s) == 1, f
        r = s.iloc[0]
        return f"{int(r.loss_n)}/{int(r.n)} · {r.median_gap:+.3f}"
    out = {f"ext75{d}_{p}": cell(f"ext75{d}_{p}_bp_stats.csv", "넣음" if p == "defer" else "안넣음")
           for d in "ab" for p in ("base", "defer", "lump")}
    out["1년"] = cell("bp_stats.csv", "안넣음")
    for v in ("", "_만기+1년", "_만기+2년", "_상한"):
        out[f"3년{v}"] = cell(f"term_ii{v}_base_bp_stats.csv", "안넣음")
    out["3년_연기"] = cell("term_ii_defer_bp_stats.csv", "넣음")
    out["ext80a_base"] = cell("ext80a_base_bp_stats.csv", "안넣음")
    out["ext80a_defer"] = cell("ext80a_defer_bp_stats.csv", "넣음")
    out["그해이자_1년"] = cell("intalt/bp_stats.csv", "안넣음")      # 이자 반영 시점 민감도(표 5-7)
    r = rd(f"{D['t3']}/results/N/ext75a_rem_ratio.csv")["base"]
    out["잔액비율"] = f"{r.min() * 100:.0f}~{r.max() * 100:.0f}%, 중앙값 {r.median() * 100:.0f}%"
    tp = rd(f"{D['t3']}/results/N/term_people.csv").set_index(["사람", "세금 그릇", "판", "해"])
    for k, key in (("비율_1년", ("B", "(가)", "i", "해마다")), ("비율_만기", ("B", "(가)", "ii", "만기 해")),
                   ("비율_만기아님", ("B", "(가)", "ii", "만기 아닌 해"))):
        out[k] = f"{tp.loc[key, '선정기준액 대비'] * 100:.1f}%"
    return out


def cand5_late():
    """85·90세(표 5-8): 사람 B (가) ★ 칸, ★ 칸(사람 A·B·C × (가)(나)(다)) 전체 손해 최대, (c) 꼬리 1,000개 손해 최대, 꼬리 요약."""
    N, out, star = f"{D['t3']}/results/N", {}, 0
    for age in (85, 90):
        for d in "ab":
            for p, K2 in (("base", "안넣음"), ("defer", "넣음")):
                s = rd(f"{N}/ext{age}{d}_{p}_bp_stats.csv")
                s = s[(s.m == 300000) & (s.asset == "A") & (s.K1 == "전액") & (s.K2 == K2) & (s.region == "중소도시") & (s["쌍"] == "ps<dep")]
                assert len(s) == 9, (age, d, p)                         # 사람 A·B·C × (가)(나)(다)
                star = max(star, int(s.loss_n.max()))
                r = s[(s.person == "가") & (s.b == "B")].iloc[0]
                out[f"ext{age}{d}_{p}"] = f"{int(r.loss_n)}/{int(r.n)} · {r.median_gap:+.3f}"
    c, lp = rd(f"{N}/ext_late_c.csv"), rd(f"{N}/ext_late_paths.csv").set_index("나이")
    assert len(c) == 36000 and c.draw.nunique() == 1000 and (c.n == 21).all()
    assert lp["표본 부족(경로 5개 미만)"].tolist() == [False, True]
    return out, star, c, lp


def r03(R):
    t, tb = cand5()
    cols = ["3년째", "5년째", "62세", "70세"]
    for label, g in t.groupby("비교", sort=False):
        cell = g.set_index("시점")["칸"]
        R.add("t3", f"| {label} |" + "".join(" {} |" if c in cell else " |" for c in cols), *[cell[c] for c in cols if c in cell])
    reg = tb.set_index(tb["비교"].str.extract(r"(\S+)\)$")[0])["칸"]
    R.add("t3", "| 연금저축 < 예금, 세금 0원 + 기초연금 경계 (사람 B) | | | | 중소도시 {}, 대도시 {} |", reg["중소도시"], reg["대도시"])
    dif = t[t["판정_다름"]]
    R.add("t3", "적용한 판정과 다른 칸**({}칸 중 {}칸). 그중 {}칸은 부트스트랩에서", len(t), len(dif), int((dif["부트_가운데"] > dif["과거_비율"]).sum()))
    e = t[t["경계_1pp"]].set_index(["비교", "시점"])["부트_가운데"].map(lambda x: f"{x * 100:.1f}")
    assert len(e) == 3
    R.add("t3", "가운데값이 경계에서 1%p 안인 칸: 연금저축 (가) 5년째({}%), 노란우산 (가) 3년째({}%), 노란우산 (나) 3년째({}%).",
          e[("연금저축 < 예금, 세금 0원 (가)", "5년째")], e[("노란우산 폐업·노령 < 예금, 세금 0원 (가)", "3년째")], e[("노란우산 폐업·노령 < 예금, 세금 조금 (나)", "3년째")])
    q = t.set_index(["비교", "시점"])
    nc = q.loc["노란우산 그냥 해약 < 예금 (가)"]
    assert (nc.loc[["3년째", "5년째"], "과거_적은해"] == nc.loc[["3년째", "5년째"], "과거_전체"]).all()   # '모든 시작 연도'
    n62 = (nc.loc["62세", "과거_전체"], nc.loc["62세", "과거_적은해"])
    R.add("t3", "그냥 해약은 3·5년째는 모든 시작 연도에서, 62세는 {}개 중 {}개에서", *n62)
    R.add("t3", "(3·5년째 모든 시작 연도, 62세 {}개 중 {}개)", *n62)
    R.add("t3", "or 5 years, and in {} of {} at 62.", n62[1], n62[0])
    R.add("r", "3·5년째는 모든 시작 연도에서, 62세는 {}개 중 {}개에서 예금보다 적었다", *n62)
    ps = q.loc["연금저축 < 예금, 세금 0원 (가)"]
    r35 = ps.loc[["3년째", "5년째"], "과거_비율"] * 100
    p70 = ps.loc["70세"]
    b70 = f"{round(p70.부트_최소 * 100):.0f}~{round(p70.부트_최대 * 100):.0f}"
    R.add("r", "3·5년째 꺼내면 시작 연도의 {}~{}%에서 예금보다 적었고, 70세까지 두면 예금보다 적은 시작 연도가 없었다({}/{}, 부트스트랩 1만 경로 중에서는 {}%)",
          f"{r35.min():.0f}", f"{r35.max():.0f}", p70.과거_적은해, p70.과거_전체, b70)
    R.add("t3", "bank deposit in {}–{}% of historical start years if cashed out after 3–5 years, and in none of {} start years when held to 70 (but in {}% of 10,000",
          f"{r35.min():.0f}", f"{r35.max():.0f}", p70.과거_전체, b70.replace("~", "–"))
    n = lambda s: s.split(" · ")[0].split("/")
    R.add("t3", "the result at 70 depends on region ({} vs {} of {} start years", n(reg["중소도시"])[0], n(reg["대도시"])[0], n(reg["대도시"])[1])

    x = cand5_ext()
    R.add("t3", "같은 조건의 70세 비교는 **{}**입니다.", x["1년"])
    R.add("t3", "70세 비교가 **{}**, 사업안내 시점이면 **{}**입니다.", x["그해이자_1년"], x["1년"])
    R.add("t3", "앞선 판 결과({})를 본 뒤", n(x["그해이자_1년"])[0] + "/" + n(x["그해이자_1년"])[1])
    R.add("t3", "moves the 70-year comparison from {} to {} of {} start years", n(x["그해이자_1년"])[0], n(x["1년"])[0], n(x["1년"])[1])
    R.add("t3", "75세까지 실제 시장 자료가 있는 {}개 시작 연도(1992~2007년)에서 62세부터 받는 판은 **{}**, 70세부터 받는 판(연기판)은 **{}**이었습니다.",
          n(x["ext75a_base"])[1], x["ext75a_base"], x["ext75a_defer"])
    R.add("t3", "62세 판 **{}**(70세 비교에서는 {}), 연기판 **{}**였습니다.", x["ext75b_base"], "/".join(n(x["1년"])), x["ext75b_defer"])
    R.add("t3", "한꺼번에 꺼내면 62세 판이 **{}**, **{}**으로 나빠집니다.", x["ext75a_lump"], x["ext75b_lump"])
    R.add("t3", "2040년 초 잔액의 **{}**, `results", x["잔액비율"])
    R.add("t3", "fell short of the deposit in {} of {} start years for the draw-from-62 plan", *n(x["ext75a_base"]))
    R.add("t3", "시작 연도는 **{}개**(1992~2002년)입니다. 62세 판 **{}**, 연기판 **{}**였습니다.", n(x["ext80a_base"])[1], x["ext80a_base"], x["ext80a_defer"])
    R.add("t3", "Carried to age 80 on the {} start years", n(x["ext80a_base"])[1])
    R.add("t3", "62세 판의 결과가 **{}**에서 **{}**로 나빠집니다.", x["1년"], x["3년"])
    R.add("t3", "소득인정액이 선정기준액의 **{}**가 되어", x["비율_만기"])
    R.add("t3", "만기가 아닌 해에는 **{}**로 내려가 여유가 생깁니다(1년 예금이면 해마다 **{}**).", x["비율_만기아님"], x["비율_1년"])
    R.add("t3", "만기 해를 1년·2년 늦춰도 **{}**, **{}**, 추가 공제를 연 48만 원으로 자르는 해석으로 읽어도 **{}**입니다. 연기판은 **{}**으로",
          x["3년_만기+1년"], x["3년_만기+2년"], x["3년_상한"], x["3년_연기"])
    R.add("t3", "the pension account fell short in {} of {} start years instead of {},", *n(x["3년"]), n(x["1년"])[0])

    L, star, c, lp = cand5_late()
    assert star == 0 and int(c.loss_n.max()) == 0, star
    R.add("t3", "(a)·(b) 모두 {}이었고, (c)도 꼬리 {}개 모두 {}%였습니다.", star, f"{c.draw.nunique():,}", f"{c.loss_n.max() / 21 * 100:.0f}")
    R.add("t3", "85세 (a) 62세 판 **{}**, 연기판 **{}**, (b) **{}**, **{}**. 90세 (b) **{}**, **{}**.",
          L["ext85a_base"], L["ext85a_defer"], L["ext85b_base"], L["ext85b_defer"], L["ext90b_base"], L["ext90b_defer"])
    R.add("t3", "시작 연도가 **{}개**(1992년)뿐입니다(**{}**, 연기판 **{}**).", int(lp.loc[90, "(a) 경로"]), L["ext90a_base"], L["ext90a_defer"])
    R.add("t3", "(85세 {}개 1992~1997년, 90세 {}개 1992년)", int(lp.loc[85, "(a) 경로"]), int(lp.loc[90, "(a) 경로"]))
    tail = {f"{lp.loc[a, '(c) 꼬리 주식 월평균'] * 100:.2f}%|{lp.loc[a, '(c) 꼬리 평균 ÷ r̄']:.1f}배|{int(lp.loc[a, '(c) 꼬리로 바뀐 경로'])}개({lp.loc[a, '(c) 바뀐 경로 시작']}년 시작)" for a in (85, 90)}
    assert len(tail) == 1                                                     # 85·90세가 표기상 같은 값
    tm, tx, tc = tail.pop().split("|")
    R.add("t3", "꼬리 주식 월평균이 **{}**로 채움 금리의 **{}**여서", tm, tx)
    R.add("t3", "21개 중 **{}**뿐입니다", tc)
    R.add("t3", "on real data only ({} start years at 85, a single one at 90", int(lp.loc[85, "(a) 경로"]))
    R.add("t3", "across {} bootstrapped equity tails (which also raise the mean equity return to {} times the fill rate and move only {} of the {} paths)",
          f"{c.draw.nunique():,}", tx[:-1], tc.split("개")[0], int(lp.loc[85, "(b) 경로"]))
    return t, tb


# ── 04~07 ────────────────────────────────────────────────────────────────────
def r04_07(R):
    lab = {"KR 2004~": "한국 2004~", "KR 1991~": "한국 1991~", "US 1965~": "미국"}
    m = rd(f"{D['t4']}/results/portfolio/T1_margin_boot.csv")
    m = m[(m["포트폴리오"] == "주식100") & (m["기간"] == "전체") & (m["기간(개월)"] == 12)]
    f5 = m[m["꺼낼 금액(평가액 대비)"] == 0.5].groupby("표본")
    cheap, brk = f5["P(대출<② 공제분 인출)"].agg(["min", "max"]), f5["P(담보부족)"].agg(["min", "max"])
    be = rd(f"{D['t4']}/results/pilot7/T1_breakeven.csv").set_index("Unnamed: 0").loc["신한 연금저축담보 5.00%", "vs ② 공제분(16.5%)"]
    ic = rd(f"{D['t4']}/results/portfolio/T1_margin_interest.csv").iloc[0]
    nd = m["P(대출<① 비공제분 인출)"]
    low = f"{m[m['꺼낼 금액(평가액 대비)'] <= 0.3]['P(담보부족)'].max() * 100:.1f}"
    R.add("t4", "대출이 공제분 인출보다 쌀 확률: 한국 2004~ {}%, 한국 1991~ {}%, 미국 {}%. 계좌가 12개월 동안 {}%보다 덜 잃으면",
          *[pr(*cheap.loc[k]) for k in lab], f"{-be * 100:.1f}")
    R.add("t4", "같은 조건에서 대출이 쌀 확률 {}%.", pr(nd.min(), nd.max()))
    R.add("t4", "12개월 안 담보부족 확률**: 한국 2004~ {}%, 한국 1991~ {}%, 미국 {}%.", *[pr(*brk.loc[k], 1) for k in lab])
    R.add("t4", "12개월 담보부족 확률이 모든 표본·블록에서 {}% 이하였습니다", low)
    R.add("t4", "한도 전액 12개월 {}%→{}%", f"{ic['P(담보부족) 이자 따로'] * 100:.1f}", f"{round(ic['P(담보부족) 이자 원금 가산'] * 1000) / 10:.1f}")  # 0.0435 → 4.4
    R.add("t4", "probability of up to about {}% over 12 months", f"{brk['max'].max() * 100:.0f}")
    R.add("t4", "borrowing 30% or less kept it at {}% or below", low)
    R.add("r", "대출이 쌀 확률 세 표본 {}%). 한도(평가액 50%)를 다 빌리면 12개월 안 담보부족 확률이 {}%, 30% 이하면 {}% 이하였다.",
          pr(cheap["min"].min(), cheap["max"].max()), pr(brk["min"].min(), brk["max"].max(), 1), low)

    b = rd(f"{D['t5']}/results/pilot7/T3_buckets.csv")
    V = "일반계좌보다 나은 비율"
    k = lambda cred, ex, end="", asset="국내주식": b[(b["표본"] == "KR 2004~") & (b["자산"] == asset) & b["인출"].str.startswith(ex) & b["통"].str.startswith(cred) & b["통"].str.endswith(end)]
    rg = lambda x: f"{pr(x[V].min(), x[V].max())}%"
    nd = k("비공제통", "55세 전")
    same, cd = k("공제통 16.5%", "55세 전", "같은자산 일반계좌"), k("공제통 16.5%", "55세 전", "CD(세후)")
    same13, cd13 = k("공제통 13.2%", "55세 전", "같은자산 일반계좌"), k("공제통 13.2%", "55세 전", "CD(세후)")
    us = b[(b["자산"] == "미국주식") & b["인출"].str.startswith("55세 이후") & (b["h년"] >= 5)]
    assert (us[V] > 0.5).all(), "미국주식 55세 뒤 연금: 연금저축이 모든 칸에서 나아야 함"
    n5, s5 = nd[nd["h년"] >= 5], same[same["h년"] >= 5]
    R.add("t5", "5년 이상 보유에서 연금저축이 나은 시작 월은 {}(= 일반계좌가 나은 비율 {}). 1~4년 보유에서도 연금저축이 나은 비율 {}.",
          rg(n5), f"{pr(1 - n5[V].max(), 1 - n5[V].min())}%", rg(nd[nd["h년"] < 5]))
    R.add("t5", "환급금을 예금(CD)에 두면 공제율 16.5%에서 {}, 13.2%에서 {}로 일반계좌가 나았고, 같은 자산에 다시 넣으면 16.5%에서 {}, 13.2%에서 {}로 갈렸습니다.",
          rg(cd[cd["h년"] >= 5]), rg(cd13[cd13["h년"] >= 5]), rg(s5), rg(same13[same13["h년"] >= 5]))
    R.add("t5", "(2004~·보유 5년 이상: 환급 2개월 {} → 13개월 {})", rg(s5[s5["환급지연(개월)"] == 2]), rg(s5[s5["환급지연(개월)"] == 13]))
    p6 = rd(f"{D['t5']}/results/pilot7/T6_paired.csv")
    q = {s: (len(d), int(d["0 배제(95%)"].astype(str).eq("True").sum()), int((d["Holm형 조정(검정 아님)"] < 0.05).sum()),
             *[sg(v) for v in d[d["기간(년)"] == 10]["중앙값"].agg(["min", "max"])]) for s, d in p6.groupby("표본")}
    a, c = q["KR 2004~"], q["KR 1991~"]
    assert a[0] == c[0]
    R.add("t5", "**공짜 리밸런싱의 이득은 작다.** {}칸 중 95% 구간이 0을 뺀 칸은 2004~ {}칸(원 결과의 'Holm형 조정(검정 아님)' 열 기준 {}칸), 1991~ {}칸(조정 후 {}칸). 10년 누적 차이 중앙값 {}~{}%p(2004~), {}~{}%p(1991~).",
          a[0], a[1], a[2], c[1], c[2], *a[3:], *c[3:])
    R.add("r", "연금저축이 나은 시작 월이 {}(2004~ 표본, 5년 이상 보유)였고", rg(n5))
    R.add("r", "계좌 안 리밸런싱의 이득은 {}칸 중 95% 구간이 0을 뺀 칸이 {}·{}칸뿐이었다", a[0], a[1], c[1])

    fh = rd(f"{D['t6']}/results/pilot7/T5_french_hist.csv")
    w = fh[(fh["분할"] == 3) & (fh["대기자금"] == "대기 0%")].set_index(["패널", "시작상태"])["LS 승률(안 겹친)"] * 100
    P22, P17 = "French 22개국(달러)", "OECD 17개국(현지통화, 대기 = 현지 3개월 금리)"
    wa, wp = [w[(p, "전체")] for p in (P22, P17)], [w[(p, "최고점(낙폭 0)")] for p in (P22, P17)]
    f0 = lambda x: f"{x:.0f}"
    sb, fb = rd(f"{D['t6']}/results/pilot7/T5_boot.csv"), rd(f"{D['t6']}/results/pilot7/T5_french_boot.csv")
    g = pd.concat([sb[(sb["포트폴리오"] == "주식100") & sb["표본"].isin(lab) & (sb["분할"] == 3) & (sb["대기자금"] == "대기 0%")],
                   fb[(fb["분할"] == 3) & (fb["대기자금"] == "대기 0%")].assign(표본=lambda d: d["패널"])])
    g10 = g.groupby("표본")["CER차(LS−CA) γ=10"].agg(["min", "max"])
    assert (g10["max"] < 0).all(), "주식100 γ=10: 모든 표본에서 나눠 넣기가 나아야 함"
    R.add("t6", "안 겹친 1년 창 승률: 22개국 {}%, 17개국 {}%(주식 100%", *map(f0, wa))
    R.add("t6", "고점에서 시작해도 마찬가지였다.** 22개국 {}%, 17개국 {}%.", *map(f0, wp))
    R.add("t6", "CER 차이(한 번에 − 나눠): 한국 2004~ {}%p, 한국 1991~ {}%p, 미국 {}%p, 22개국 {}%p, 17개국 {}%p.",
          *[pr(*g10.loc[s], 1) for s in ("KR 2004~", "KR 1991~", "US 1965~", P22, P17)])
    R.add("t6", "(최댓값 {}%p)", f"{g['CER차(LS−CA) γ=3'].max() * 100:+.1f}")
    R.add("t6", "investing at once won {}–{}% of the time, and {}–{}% in windows that started at a market peak",
          f0(min(wa)), f0(max(wa)), f0(min(wp)), f0(max(wp)))
    R.add("r", "다국가 1년 창에서 한 번에 넣기가 {}·{}%, 고점 시작에서도 {}·{}% 이겼다", *map(f0, wa), *map(f0, wp))

    ck = rd(f"{D['t7']}/results/pilot9_C_real_inputs/C2_check_index_vs_real_overlap.csv")
    ck = ck[ck["nav_lag_bdays"].isin([0, 1, 2]) & ck["index_model"].str.endswith("total") & ck["real"].isin(["KB_UH", "미래에셋", "삼성_H", "신한", "한국투자_UH"])]
    assert len(ck) == 15
    bp = rd(f"{D['t7']}/results/pilot9_A_simple/L2b_boot_pairs.csv")
    bp = bp[(bp["블록"].astype(str) == "1") & (bp["보수"] == "총보수")]
    ratio = np.maximum(bp["비_중앙"], 1 / bp["비_중앙"])
    v55 = rd(f"{D['t7']}/results/pilot9_A_window_mde/vintage_summary.csv").set_index("vintage").loc[2055]
    te, rt, z0 = f"{ck['te_pctpa'].min():.1f}~{ck['te_pctpa'].max():.1f}", f"{ratio.min():.2f}~{ratio.max():.2f}", ck[ck["nav_lag_bdays"] == 0]["te_pctpa"]
    R.add("t7", "**설명서대로라면 운용사 사이 30년 금액이 {}배 차이**", rt)
    R.add("t7", "**그러나 실제 수익률은 설명서 계산과 연 {}%p씩 흔들렸다**", te)
    R.add("t7", "평균 차는 운용사별 {}~{}%p/년이었고", sg(ck["mean_diff_pctpa"].min()), sg(ck["mean_diff_pctpa"].max()))
    R.add("t7", "추적오차는 시차 0일일 때 가장 커서({}~{}%p)", f"{z0.min():.1f}", f"{z0.max():.1f}")
    R.add("t7", "2055 빈티지 5대 공통 {}개월로 구별할 수 있는 최소 연 차이(검정력 80%)는 중앙값 {}%p", int(v55["T"]), f"{v55['mde_med']:.1f}")
    R.add("t7", "해마다 연 {}%p씩 흔들리고, 2055 빈티지의 2년 남짓한 공통 기록으로는 연 약 {}%p보다", te, f"{v55['mde_med']:.1f}")
    R.add("r", "투자설명서대로면 30년 금액이 운용사 쌍별 {}배 달랐지만, 실제 수익률은 설명서 계산과 연 {}%p 흔들렸고, 2055 빈티지 공통 {}개월로 구별할 수 있는 최소 연 차이는 {}%p였다",
          rt, te, int(v55["T"]), f"{v55['mde_med']:.1f}")


# ── 08 ───────────────────────────────────────────────────────────────────────
def r08(R):
    ev = rd(f"{D['t8']}/results/T6_shelter_events.csv")
    S = rd(f"{D['t8']}/results/T6_shelter_summary.csv").set_index(["규칙", "안전자산"])
    nine = ev[ev["표본"] == "9개국"]
    hold = lambda lo, hi: "피신이 적었다" if hi < 1 else "피신이 많았다" if lo > 1 else "가려낼 수 없음"
    vs = lambda lo, hi, L: "피신 비용 > 해지 세금" if hi < L else "피신 비용 < 해지 세금" if lo > L else "가려낼 수 없음"
    med = {}
    for (rule, safe), g in nine.groupby(["규칙", "안전자산"]):
        s = S.loc[(rule, safe)]
        med[(rule, safe)] = g.R.median()
        R.add("t8", f"- {rule}·{safe}: 중앙 {{}}배(90% {{}}~{{}}; 신호 없음 {{}}건을 빼면 {{}}~{{}}) → 보유 대비 {{}}, 해지 대비(0.835 선, 설계서) {{}}, "
              f"수령세 넣은 선(0.863·0.884, 감사 뒤 민감도) {{}}·{{}}. 사건 {{}}개 중 보유보다 적었던 사건 {{}}개, 0.835 아래 {{}}개, 피신 기간 중앙 {{}}개월, 보유보다 적었던 사건의 놓친 상승분(1/R − 1) 중앙 {{}}%.",
              f"{g.R.median():.2f}", f"{s.P5:.3f}", f"{s.P95:.3f}", int(g["신호없음"].sum()), f"{s.P5_신호없음제외:.3f}", f"{s.P95_신호없음제외:.3f}",
              hold(s.P5, s.P95), vs(s.P5, s.P95, 0.835), vs(s.P5, s.P95, 0.835 / (1 - 0.033)), vs(s.P5, s.P95, 0.835 / (1 - 0.055)),
              len(g), int((g.R < 1).sum()), int((g.R < 0.835).sum()), f"{g['피신개월'].median():.0f}", f"{g[g.R < 1]['놓친상승'].median() * 100:.0f}")
        g5 = g.dropna(subset=["R_5년"])
        R.add("t8", f"{rule}·{safe} 중앙 {{}}배(90% {{}}~{{}}, {{}}개)", f"{g5['R_5년'].median():.2f}", f"{s.P5_5년:.2f}", f"{s.P95_5년:.2f}", len(g5))
    kr = ev[ev["나라"] == "KOR"]
    zero = kr["신호없음"] & (kr["피신개월"] == 0)
    kz = kr[~zero]
    kl = lambda rule: "; ".join(f"{r.confirm} 확인 {r.R:.2f}배({r.피신개월}개월{', 신호 없음' if r.신호없음 else ''})"
                                for r in kz[(kz["규칙"] == rule) & (kz["안전자산"] == "MMF")].itertuples())
    R.add("t8", "- 한국 하락장(사건별, 묶음 구간 없음): 전고점 회복·MMF — {}. 20% 반등·MMF — {}.\n- 확인 뒤 5년", kl("전고점 회복"), kl("저점 대비 20% 반등"))
    n9, nk, nk0 = nine.groupby(["규칙", "안전자산"]).size().unique(), kz.confirm.nunique(), kr[zero].confirm.nunique()
    assert len(n9) == 1
    R.add("t8", "현지통화) 하락장 {}번과 한국(1991~, KOSPI200+배당) 하락장 {}번(자료 끝 2026-08 확인 {}건은", n9[0], nk, nk0)
    fl = rd(f"{D['t8']}/results/T6_flow_vs_nonbear.csv")
    fz = lambda grp, t0: fl[(fl["묶음"] == grp) & (fl["h개월"] == 12) & (fl["확인월"] == t0)].iloc[0]
    a, f3 = fz("안정형4유형합", "2018-10"), lambda x: f"{x:.3f}"
    R.add("t8", "안정형 4유형 순설정 ÷ 순자산은 2018-10 확인 뒤 {}, 2022-06 확인 뒤 {}였고, 하락장이 아닌 같은 길이 창({}개)은 중앙 {}(10~90% {}~{}). "
          "MMF는 {}·{} 대 중앙 {}, TDF는 {}·{} 대 중앙 {}(비교창 {}개",
          f3(a.사건값), f3(fz("안정형4유형합", "2022-06").사건값), a.비교창, f3(a.비교_중앙), f3(a.비교_P10), f3(a.비교_P90),
          f3(fz("MMF", "2018-10").사건값), f3(fz("MMF", "2022-06").사건값), f3(fz("MMF", "2018-10").비교_중앙),
          f3(fz("TDF연금", "2018-10").사건값), f3(fz("TDF연금", "2022-06").사건값), f3(fz("TDF연금", "2018-10").비교_중앙), fz("TDF연금", "2018-10").비교창)
    pk = [med[("전고점 회복", s)] for s in ("MMF", "채권")]
    rb = [med[("저점 대비 20% 반등", s)] for s in ("MMF", "채권")]
    up = [S.loc[("전고점 회복", s), "P95"] for s in ("MMF", "채권")]
    assert max(up) < 1 and all(S.loc[("저점 대비 20% 반등", s), "P95"] > 1 > S.loc[("저점 대비 20% 반등", s), "P5"] for s in ("MMF", "채권"))
    f2 = lambda x: f"{x:.2f}"
    R.add("t8", "Across {} confirmed bear markets in nine developed countries", n9[0])
    R.add("t8", "left the median saver with {}–{} times what holding would have given (90% cluster-bootstrap intervals below 1); returning after a 20% rebound from the low gave {}–{} times",
          f2(min(pk)), f2(max(pk)), f2(min(rb)), f2(max(rb)))
    R.add("r", "9개국 하락장 {}번에서 MMF·채권으로 피했다가 전고점 회복 뒤 돌아오면 보유 대비 중앙 {}·{}배(90% 구간 상한 {}·{})였고, 저점 대비 20% 반등 뒤 돌아오면 {}·{}배로 보유와 가려낼 수 없었다",
          n9[0], *map(f2, pk), *[f"{x:.3f}" for x in up], *map(f2, rb))


# ── 09 ───────────────────────────────────────────────────────────────────────
def r09(R):
    T = rd(f"{D['t9']}/results/T9_cf_by_fund.csv")
    NOI, OUT = "판독 오차와 구분 안 됨", ["실제 계획이 더 많음", "처음 계획이 더 많음"]
    ok = T[T["판정"].isin([NOI] + OUT)].copy()
    # 판정·원인구분을 CSV 글자 대신 d·바닥선·방법변경 열에서 다시 냄
    assert (ok["판정"].eq(NOI) == (ok["d_적립"].abs() <= ok["바닥선"])).all()
    big_ = ok["d_적립"].abs() > ok["바닥선"]
    mc = ok["방법변경건넘"].astype(str).eq("True")
    cause = np.select([big_ & ~mc, big_ & (ok["d_같은방법구간"].abs() > ok["바닥선"]), big_], ["none", "same", "ins"], "")
    ok["c"] = cause
    names = lambda c: ", ".join(f"{r.운용사} {r.빈티지}" for r in ok[ok.c == c].sort_values(["운용사", "빈티지"]).itertuples())
    cnt = lambda c: int((ok.c == c).sum())
    long_, short_ = ok[ok["개월"] > 12], ok[ok["개월"] <= 12]
    R.add("t9", "**처음 계획을 지켰을 때와 비교할 수 있는 펀드는 {}개**였고(나머지 {}개는 비교 불가), 이 중 의미 있는 기간({}~{}개월)을 가진 것은 {} {}개이고, 신한·미래에셋 {}개는 첫 곡선 판이 2026-04라 {}개월 비교뿐입니다",
          len(ok), len(T) - len(ok), int(long_["개월"].min()), int(long_["개월"].max()), "·".join(sorted(set(long_["운용사"]))), len(long_), len(short_), int(short_["개월"].max()))
    R.add("t9", "금액 차이가 판독 잡음 바닥선보다 큰 펀드는 {}개입니다.", int(big_.sum()))
    R.add("t9", "(결과 뒤 추가한 구분): {}개({})는 같은 방법 구간만으로도 바닥선 밖이고, {}개({})는 차이가 방법 변경 뒤에만 생겨 계획 변경과 판독 방법 차이를 나눌 수 없으며, {}개({})는 방법 변경을 건너지 않았습니다.",
          cnt("same"), names("same"), cnt("ins"), names("ins"), cnt("none"), names("none"))
    for mg, g in ok.groupby("운용사"):
        R.add("t9", f"- {mg}: 비교 {{}}개, 비교 불가 {{}}개(첫 판 {{}}~{{}}, 계산 기간 {{}}~{{}}개월), 실제 ÷ 처음 계획 금액 로그 {{}}~{{}}%(중앙 {{}}%), 월 10만 원 적립 기준 금액 차이 {{}}~{{}}원, 바닥선 밖 {{}}개, 판독 방법 변경을 건넌 펀드 {{}}개.",
              len(g), int(((T["운용사"] == mg) & ~T.code.isin(ok.code)).sum()), g["첫판"].min(), g["첫판"].max(), int(g["개월"].min()), int(g["개월"].max()),
              *[f"{x * 100:+.2f}" for x in (g["d_적립"].min(), g["d_적립"].max(), g["d_적립"].median())],
              f"{g['월10만원_금액차'].min():+,.0f}", f"{g['월10만원_금액차'].max():+,.0f}", int((g.c != "").sum()), int(g["방법변경건넘"].astype(str).eq("True").sum()))
    b = ok.loc[ok["d_적립"].abs().idxmax()]
    R.add("t9", "- 가장 큰 차이: {} {} ({}), {}~{} {}개월, 로그 {}%(월 10만 원 적립, 원금 {}원 기준 {}원). 위험자산 비중 차이는 최대 {}%p.",
          b.운용사, b.빈티지, b.code, b.첫판, b.끝월, b.개월, f"{b.d_적립 * 100:+.2f}", f"{b.적립원금:,.0f}", f"{b.월10만원_금액차:+,.0f}", f"{b.위험비중차_최대 * 100:.1f}")
    R.add("t9", "같은 판을 두 번 읽을 때 생기는 차이의 95%, 약 {}%) 안이면", f"{ok['바닥선'].min() * 100:.2f}")
    fd = rd(f"{D['t9']}/figures/fig_T9_글라이드변경_data.csv")
    e = fd[fd["구분"] == "변경 9번"].groupby("운용사").size()
    R.add("t9", "(운용사별 KB {}, 삼성 {}, 신한 {}, 한국투자 {}, 미래에셋 {})", *[int(e.get(k, 0)) for k in ("KB", "삼성", "신한", "한국투자", "미래에셋")])
    R.add("t9", "the difference exceeded a chart-reading error floor for {} of {} comparable funds (the largest about {}% in log terms over {} months); {} of the {} had only four months",
          int(big_.sum()), len(ok), f"{b.d_적립 * 100:.0f}".replace("-", "−"), f"{b.개월:.0f}", len(short_), len(ok))
    R.add("t9", "For {} of the {} the difference appeared only after", cnt("ins"), int(big_.sum()))
    R.add("r", "| TDF {}개 중 처음 계획과 비교할 수 있는 {}개에서 판독 잡음 바닥선 밖 차이는 {}개(가장 큰 차이 로그 {}%, {}개월)였고, 그중 {}개는 판독 방법이 바뀐 뒤에만 차이가 생겨(결과 뒤 구분)",
          len(T), len(ok), int(big_.sum()), f"{b.d_적립 * 100:+.2f}", b.개월, cnt("ins"))


# ── 10 ───────────────────────────────────────────────────────────────────────
def r10(R):
    P = rd(f"{D['t10']}/results/T10_gap_by_report.csv")
    Dc = rd(f"{D['t10']}/results/T10_change_after_trough.csv")
    ob = P.set_index(["code", "period_end"])["점경계밖"]
    assert (ob == ~((P.lo_Shist <= P.g_Shist + 1e-12) & (P.g_Shist <= P.hi_Shist + 1e-12)).values).all()   # 점 − 목표가 경계 − 목표 안 ⇔ 점이 경계 안
    UP, DN, NO, HOLD = "목표 쪽으로 다시 올라옴", "더 벌어짐", "가려낼 수 없음", "판정 보류(경계 불성립)"
    # 판정을 CSV 글자 대신 경계 열·점경계밖에서 다시 냄
    Dc["bb"] = [ob[(c, p)] for c, p in zip(Dc.code, Dc.기준보고서)]
    Dc["ab"] = [ob[(c, p)] for c, p in zip(Dc.code, Dc.뒤보고서)]
    Dc["lvl"] = np.where(Dc.기준_상 < 0, "목표보다 낮음", np.where(Dc.기준_하 > 0, "목표보다 높음", NO))
    Dc["lvlh"] = np.where(Dc.bb & (Dc.lvl != NO), HOLD, Dc.lvl)
    Dc["pre"] = np.where(Dc.변화_하 > 0, UP, np.where(Dc.변화_상 < 0, DN, NO))
    Dc["fin"] = np.where((Dc.bb | Dc.ab) & (Dc.pre != NO), HOLD, Dc.pre)
    assert (Dc.fin == Dc.판정).all() and (Dc.lvlh == Dc.기준판정_보류규칙).all() and (Dc.lvl == Dc.기준판정).all()
    c4 = lambda tg, k: "·".join(str(int((Dc[(Dc.목표 == tg) & (Dc.k == k)].fin == p).sum())) for p in (UP, DN, NO, HOLD))
    k1 = lambda tg: Dc[(Dc.목표 == tg) & (Dc.k == 1)]
    lv = lambda tg, p, col="lvlh": int((k1(tg)[col] == p).sum())
    bw = (P.hi_Shist - P.lo_Shist) * 100
    R.add("t10", "(KB·한국투자·삼성 {}개 펀드, 보고서 {}개, {}~{})", P.code.nunique(), len(P), P.period_end.min(), P.period_end.max())
    R.add("t10", "경계 폭은 보고서별 {}~{}%p(중앙 {}%p)입니다.", f"{bw.min():.0f}", f"{bw.max():.0f}", f"{bw.median():.0f}")
    R.add("t10", "(그때 유효 목표): {}개 펀드 중 목표보다 낮음 {}개, 높음 {}개, 가려낼 수 없음 {}개, 판정 보류(경계 불성립) {}개. 설계서 규칙 그대로면 낮음 {}·높음 {}·가려낼 수 없음 {}개입니다",
          k1("Shist").code.nunique(), *[lv("Shist", p) for p in ("목표보다 낮음", "목표보다 높음", NO, HOLD)],
          *[lv("Shist", p, "lvl") for p in ("목표보다 낮음", "목표보다 높음", NO)])
    MN = {"kb": "KB", "kim": "한국투자", "samsung": "삼성"}
    bh = k1("Shist")[k1("Shist").lvlh == HOLD]
    R.add("t10", "보류 {}개({})는 기준 보고서에서 점 추정이 경계 밖이라 경계가 성립하지 않고, 점 추정 격차는 {}~{}%p입니다",
          len(bh), ", ".join(f"{MN[m]} {v}" for m, v in sorted(zip(bh.manager, bh.vintage))), f"{bh.기준격차.min() * 100:+.2f}", f"{bh.기준격차.max() * 100:+.2f}")
    R.add("t10", "목표를 2026년 공시로 바꾸면 저점 직전: 낮음 {}·높음 {}·가려낼 수 없음 {}·보류 {}개.", *[lv("S2026_own", p) for p in ("목표보다 낮음", "목표보다 높음", NO, HOLD)])
    sh = Dc[Dc.목표 == "Shist"]
    R.add("t10", "올라옴·벌어짐·가려낼 수 없음·판정 보류 순): 1분기 뒤 {}개, 2분기 뒤 {}개, 4분기 뒤 {}개. 방향(올라옴·벌어짐)이 나온 칸은 {}개입니다.",
          c4("Shist", 1), c4("Shist", 2), c4("Shist", 4), int(sh.fin.isin([UP, DN]).sum()))
    R.add("t10", "- 목표를 2026년 공시로 바꾸면: 1분기 뒤 {}개, 2분기 뒤 {}개, 4분기 뒤 {}개(같은 순서).", c4("S2026_own", 1), c4("S2026_own", 2), c4("S2026_own", 4))
    h = sh[sh.fin == HOLD]
    R.add("t10", "- 판정 보류 {}개는 {} 비교입니다(k = {}). 설계서 규칙으로는 '{}' 판정이었지만",
          len(h), ", ".join(sorted({f"{MN[m]} {b}~{a}" for m, b, a in zip(h.manager, h.기준보고서, h.뒤보고서)})), "·".join(map(str, sorted(set(h.k)))), "·".join(sorted(set(h.pre))))
    R.add("t10", "같은 비교의 점 추정 변화는 {}~{}%p였습니다.", f"{h.변화_점.min() * 100:+.1f}", f"{h.변화_점.max() * 100:+.1f}")
    dw = (k1("Shist").변화_상 - k1("Shist").변화_하) * 100
    R.add("t10", "변화 경계 폭(1분기 뒤)은 중앙 {}%p라", f"{dw.median():.0f}")
    Q = P.groupby(pd.PeriodIndex(P.period_end, freq="Q")).g_Shist.median()
    R.add("t10", "점 추정 중앙값(분기별)은 {}~{}%p 사이였습니다.", f"{Q.min() * 100:+.1f}", f"{Q.max() * 100:+.1f}")
    R.add("t10", "보고서 {}개 중 {}개에서 점이 경계 밖이었습니다.", len(P), int(P["점경계밖"].sum()))
    R.add("t10", "저점 직전 기준 보고서 중 점이 경계 밖인 것은 {}개입니다.", int(k1("Shist").bb.sum()))
    mm = rd(f"{D['t10']}/results/T10_pilot8_mismatch.csv")
    assert (mm.pe_prev > "2024-12-31").all()
    R.add("t10", "2025년 이후 보고서 {}행이 달랐습니다({}, `T10_pilot8_mismatch.csv`", len(mm), ", ".join(f"{MN[m]} {n}행" for m, n in mm.groupby("manager").size().items()))
    R.add("t10", "(three managers, {} funds, {} reports)", P.code.nunique(), len(P))
    R.add("t10", "The bound on the change is about {} percentage points wide (median), and none of the {} funds showed a distinguishable direction (the bounds included zero) one, two or four quarters after the low. Two quarters after, the rule written before the calculation would have called {} funds 'gap widened'; these were held back",
          f"{dw.median():.0f}", k1("Shist").code.nunique(), int(((sh.k == 2) & (sh.fin == HOLD) & (sh.pre == DN)).sum()))
    assert not sh.fin.isin([UP, DN]).any() and (sh[sh.fin == HOLD].k == 2).all()
    R.add("r", "분기 보고서 {}개({}개 펀드)로 2022년 하락장 뒤 '실제 − 목표' 변화를 쟀더니 1·2·4분기 뒤 방향(올라옴·벌어짐)이 나온 칸이 {}개였다({}분기 뒤 {}칸은 계산 전 규칙으로는 '{}'이었으나 결과 뒤 추가한 규칙으로 보류). 보고서에 안 실린 몫 때문에 변화 경계 폭이 중앙 {}%p라",
          len(P), P.code.nunique(), int(sh.fin.isin([UP, DN]).sum()), "·".join(map(str, sorted(set(h.k)))), len(h), "·".join(sorted(set(h.pre))), f"{dw.median():.0f}")


# ── 11 ───────────────────────────────────────────────────────────────────────
def r11(R):
    S = f"{D['t11']}/results/simpletest_T2"
    b, ph, iu, mde = (rd(f"{S}/{f}.csv") for f in ("T2_boot_cells", "T2_cushion_phases", "T2_independent_units", "T2_mde"))
    DC, PORT = ["D7", "D8", "D9", "D10", "D11", "D17"], ["①", "②", "③", "③H", "④", "④H", "⑤"]
    k = b[b.표본.isin(["KR1991", "KR1996", "KR~2024"]) & (b.경로수 == 10000) & (b.D5 == "A") & (b.D6 == "A") & b.포트.isin(PORT)
          & b[DC].apply(lambda c: c.isna() | (c == "A")).all(axis=1)].copy()
    k["블록종류"] = np.where(k.블록출처.str.startswith("PW"), "PW", np.where(k.블록출처.str.startswith("120"), "120", k.블록출처))
    assert k.groupby(["표본", "블록종류", "포트"]).size().eq(1).all() and len(k) == 3 * 4 * 7
    base = k[(k.표본 == "KR1991") & (k.블록종류 == "PW")].set_index("포트").p
    rng = k[k.블록종류 != "120"].groupby("포트").p.agg(["min", "max"])
    r120 = k[k.블록종류 == "120"].groupby("포트").p.agg(["min", "max"])
    p1 = lambda x: f"{x * 100:.1f}"
    R.add("t11", "**국내주식만 담으면 경로의 약 {}%({})가 30년 뒤 물가 뺀 원금보다 적었습니다**(1991~, 자동 블록). 표본·블록에 따라 {}~{}%, 블록 120개월 칸까지 넣으면 {}~{}%입니다",
          f"{base['①'] * 100:.0f}", f"{base['①']:.4f}", p1(rng.loc["①", "min"]), p1(rng.loc["①", "max"]),
          p1(min(rng.loc["①", "min"], r120.loc["①", "min"])), p1(max(rng.loc["①", "max"], r120.loc["①", "max"])))
    R.add("t11", "국내 60·채권 40 {}%, 미국주식 원화 {}%, 국내 33·해외 67 {}%, TDF 2055 평균 글라이드 {}%(0/10,000",
          *[f"{base[p] * 100:.2f}" for p in ("②", "③", "④", "⑤")])
    assert base["⑤"] == 0
    i1 = iu[(iu.묶음 == "단일") & (iu.표본 == "KR1991")].iloc[0]
    md = mde[(mde.표본 == "KR1991") & mde.블록출처.str.startswith("PW") & (mde.종류 == "차이") & (mde.지표 == "p")].set_index("대상")["MDE80"]
    R.add("t11", "겹치지 않는 30년 기간이 {}개뿐이라(실효 독립 단위 {}), ③−①·④−①을 가려내려면 손실 비율 차이가 약 {}·{}는 되어야 했습니다",
          int(i1.안겹친창), f"{i1.실효독립단위:.0f}", f"{md['③−①']:.2f}", f"{md['④−①']:.2f}")
    assert md[["③−①", "④−①"]].min() > base["①"]                              # '국내주식만의 비율 자체보다 큼'
    R.add("t11", "(1991-04~2026-08, {}개월)", int(i1.개월))
    c = ph[(ph.패널 == "1991~ 패널") & ph.계열.isin(["eq", "us"])].pivot(index=["고점", "저점", "하락20이상"], columns="계열", values="고점_저점").reset_index()
    assert (c["us"] > c["eq"]).all()                                          # '모두 덜 빠졌지만'
    m97 = c[c.고점 != "1994-10"].us.mean()
    R.add("t11", "**하락 국면 {}번(20% 이상 하락 {}번) 모두 원화 미국주식이 국내주식보다 덜 빠졌지만, {}번 중 {}번은 미국주식도 원화로 손실이었습니다.** 원화 미국주식 평균 {}%는 1994~98년 국면(외환위기, {}%) 하나가 끌어올린 것이고, 그 국면을 빼면 {}%입니다.",
          len(c), int(c.하락20이상.sum()), len(c), int((c.us <= 0).sum()), f"{c.us.mean() * 100:+.1f}", f"{c[c.고점 == '1994-10'].us.iloc[0] * 100:+.0f}", f"{m97 * 100:+.1f}")
    fx = max(rng.loc[p, "max"] for p in ("③", "④"))                          # 비헤지(환노출) 조합만, ⑤ TDF는 0
    R.add("t11", "about {}% of paths holding only Korean equities ended below inflation-adjusted contributions ({}–{}% across three samples and three block lengths, excluding a 120-month block); mixes with unhedged foreign equities were at 0–{}%.",
          f"{base['①'] * 100:.0f}", p1(rng.loc["①", "min"]), p1(rng.loc["①", "max"]), p1(fx))
    R.add("t11", "In all {} Korean downturns since 1991, US equities in won fell less than Korean equities, but in {} of them", len(c), int((c.us <= 0).sum()))
    R.add("r", "다시 뽑은 경로의 약 {}%가 물가 뺀 원금보다 적었다(표본 3개·블록 3종에 따라 {}~{}%, 블록 120개월 칸을 넣으면 {}~{}%). 겹치지 않는 30년 기간이 {}개뿐이라 조합 사이 차이는 가려낼 수 없었다. 하락 국면 {}번 모두 원화 미국주식이 덜 빠졌지만 {}번은",
          f"{base['①'] * 100:.0f}", p1(rng.loc["①", "min"]), p1(rng.loc["①", "max"]), p1(min(rng.loc["①", "min"], r120.loc["①", "min"])), p1(max(rng.loc["①", "max"], r120.loc["①", "max"])), int(i1.안겹친창), len(c), int((c.us <= 0).sum()))


def build():
    R = Rules()
    r01(R); r02(R); tab, tb = r03(R); r04_07(R); r08(R); r09(R); r10(R); r11(R)
    return R, pd.concat([tab, tb], ignore_index=True)


def mutate(s):
    """숫자 한 글자를 바꾸고(9 → 0, 그 밖 +1), 숫자가 없으면 글자를 덧붙인다."""
    m = re.search(r"\d", s)
    return s[:m.start()] + str((int(m.group()) + 1) % 10) + s[m.end():] if m else s + "X"


def selftest(R, texts):
    """① 규칙마다 첫 일치의 {} 자리 하나씩을 틀리게 바꾼 README 사본으로 그 규칙이 실패하는지(폴더별 잡은 수/전체).
    ② 폴더마다 숫자 하나를 틀리게 바꾼 README 사본 파일을 임시 폴더에 쓰고, 이 스크립트 전체를 그 사본으로 실행해 실패(종료 코드 ≠ 0)하는지."""
    res, missed, first = {}, [], {}
    for i, (w, tpl, vals) in enumerate(R):
        m = rx(tpl).search(texts[w])
        for j in range(len(vals)):
            a, b = m.span(j + 1)
            t = dict(texts); t[w] = texts[w][:a] + mutate(texts[w][a:b]) + texts[w][b:]
            hit = bool(check([R[i]], t))
            d = res.setdefault(w, [0, 0]); d[0] += hit; d[1] += 1
            if not hit:
                missed.append((w, tpl[:60], vals[j]))
            first.setdefault(w, (a, b))
    with tempfile.TemporaryDirectory() as tmp:
        for w, (a, b) in first.items():
            p = Path(tmp) / w / "README.md"; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(texts[w][:a] + mutate(texts[w][a:b]) + texts[w][b:], encoding="utf-8")
        r = subprocess.run([sys.executable, __file__, "--readme-dir", tmp], capture_output=True, text=True, encoding="utf-8")
        e2e = r.returncode != 0 and all(f"[{w}]" in r.stdout for w in first)
    return res, missed, e2e


if __name__ == "__main__":
    a = sys.argv
    R, tab = build()
    texts = load(Path(a[a.index("--readme-dir") + 1]) if "--readme-dir" in a else ROOT)
    bad = check(R, texts)
    for w, tpl, vals, ms in bad:
        print(f"FAIL [{w}] {tpl[:80]}…\n  기대 {vals}\n  README {ms if ms else '문장 없음'}")
    if bad:
        sys.exit(f"{len(bad)}개 규칙 실패")
    n = pd.Series([w for w, *_ in R]).value_counts().reindex(D.values())
    print("폴더별 규칙 수(값 자리 수):", {w: f"{n[w]}({sum(len(v) for x, _, v in R if x == w)})" for w in D.values()})
    if "--csv" in a:
        tab.to_csv(a[a.index("--csv") + 1], index=False, encoding="utf-8-sig")
    if "--selftest" in a:
        res, missed, e2e = selftest(R, texts)
        print("변조 시험(잡은 수/바꾼 자리 수):", {w: f"{x}/{y}" for w, (x, y) in res.items()})
        print("놓친 것:", missed or "없음", "| 사본 파일 전체 실행이 폴더 11+루트 모두에서 실패:", e2e)
        assert not missed and e2e
    print("ok")
