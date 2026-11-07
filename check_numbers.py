"""README 숫자 대조: 저장소 안 결과 CSV에서 README 숫자 일부를 다시 계산한다(새 시뮬레이션 없음).

assert 하는 것: 01 해지(C) 부호·D÷Y 범위, 더 담기 규칙 234칸과 문턱별 P 범위·예시 칸, 더 담기 대 줄이기 부호,
03 상담표 전체 칸(과거 시작 연도 수·부트스트랩 범위·판정 문자열이 03 README에 그대로 있는지)과 기초연금 칸,
03 '75세까지 넓히면'·'3년 만기 예금이면' 단락 숫자(표 5-4·5-5).
assert 하지 않고 표만 출력하는 것: 01 표본별 범위·거래비용 범위, 02 전체(그림 3 숫자). README와는 눈으로 대조.
실행: python check_numbers.py   (통과하면 'ok'와 표를 출력)
      python check_numbers.py --csv 경로   (03 상담표 전체를 CSV로도 저장)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
T1, T2, T3 = ROOT / "01_downturn_timing", ROOT / "02_tdf_vs_diy", ROOT / "03_selfemployed_50s"
rd = lambda p: pd.read_csv(p, encoding="utf-8-sig")


def t4():
    """첫 하락장: 주식 100%, 다섯 표본의 전략별 'A(계속 넣기) 대비 30년 실질 자산 − 1' 칸별 중앙값 범위(%)."""
    b = rd(T1 / "results/pilot7/T4_boot.csv")
    S = {"KR 1991~": "한국 1991~", "KR 2004~": "한국 2004~", "US 1965~ (월말)": "미국 1965~",
         "French 22개국 풀링(월, USD 실질)": "22개국", "OECD 17개국 풀링(월, 현지통화 실질, 국채 합성)": "17개국"}
    c = b[(b["포트폴리오"] == "주식100") & b["표본"].isin(S)].assign(v=lambda d: (d["A대비 중앙값"] - 1) * 100)
    out = c.groupby(["전략", "표본"]).v.agg(["min", "max"]).round(2)
    lv = rd(T1 / "results/pilot7/T4_level.csv")
    lv = lv[(lv["포트폴리오"] == "주식100") & lv["표본"].isin(S)]
    loss = (lv.groupby("표본")["A: P(실질자산<실질납입)"].agg(["min", "max"]) * 100).round(2)
    return out, loss


def d_rule():
    p = rd(T1 / "results/pilot9_D_simple/D_placebo.csv")
    pr = p["P_규칙gt위약"]
    key = p[(p["표본"] == "KR-a") & (p["블록"].astype(str) == "1") & (p["문턱"] == -0.2) & (p["복귀"] == "전고점 회복") & np.isclose(p["증액"], 0.10)]
    assert len(key) == 1
    k = key.iloc[0]
    c = rd(T1 / "results/pilot9_D_cost/D_cost.csv")
    cost = (c.groupby("편도비용")["규칙빼기위약_중앙"].agg(["min", "max", "size"]) * [100, 100, 1]).round(2)
    # 234칸 = 문턱 −10·−20·−30% 각 78칸. 문턱별 P 범위, 0.5 초과 칸, 규칙 − 위약 중앙값이 음수인 칸
    th = {t: (round(g.min(), 2), round(g.max(), 2), int((g > 0.5).sum()), len(g), int((p.loc[g.index, "규칙빼기위약_중앙"] < 0).sum()))
          for t, g in pr.groupby(p["문턱"])}
    return th, dict(칸=len(p), P최소=round(pr.min(), 2), P최대=round(pr.max(), 2), P_05초과=int((pr > 0.5).sum()),
                예시_규칙=round(k["규칙_d_중앙"] * 100, 2), 예시_위약=round(k["위약_d_중앙"] * 100, 2), 예시_P=round(k["P_규칙gt위약"] * 100, 1)), cost


def i1():
    c = rd(T1 / "results/pilot10_I1_cost/I1_cost_pairs.csv")
    c = c[(c["분자"] == "더담기_D_+10")]
    return (c.groupby("편도비용")["d_중앙"].agg(["min", "max", "size"]) * [100, 100, 1]).round(2)


def t7():
    t = rd(T2 / "figures/fig3_T7_보수분해_data.csv")
    return t[["기간", "비교", "총차이", "겉보수", "하위보수", "나머지", "p_총차이", "p_나머지", "헤지_전부", "헤지_전부비"]].round(3)


def verdict(x):
    """작성자가 정한 판정 말(2026-11-07, 결과를 본 뒤 정함). x = 예금보다 적었던 비율."""
    return "유리" if x < 0.15 else "대체로 유리" if x <= 0.35 else "비슷" if x <= 0.65 else "불리"


def cand5():
    """상담표: 주식 100%(asset A)·월 30만 원·기준 셀. 칸마다 과거 시작 연도 수(앞쪽 < 예금 / 전체),
    부트스트랩 1만 경로 중 앞쪽 < 예금 비율(블록 3종 최소~최대), 판정(부트스트랩 범위 가운데값), 과거 연도 비율로 낸 판정."""
    g = rd(T3 / "results/N/grid_stats.csv")
    g = g[(g["cell"] == "base") & (g["m"] == 300000) & (g["asset"] == "A")]
    b = rd(T3 / "results/N/boot_stats.csv")
    b = b[(b["m"] == 300000) & (b["asset"] == "A")]
    W = dict(zip(["wd36", "wd60", "p62", "p70"], ["3년째", "5년째", "62세", "70세"]))
    spec = [("연금저축 < 예금, 세금 0원 (가)", "ps<dep", "가", W), ("연금저축 < 예금, 세금 내는 사람 (다)", "ps<dep", "다", W),
            ("노란우산 그냥 해약 < 예금 (가)", "ny_cancel<dep", "가", ["wd36", "wd60", "p62"])]
    spec += [(f"노란우산 폐업·노령 < 예금, {lab} ({who})", "ny_close<dep", who, W)
             for who, lab in zip("가나다", ["세금 0원", "세금 조금", "세금 많이"])]
    rows = []
    for label, pair, who, ws in spec:
        for w in ws:
            pr = "ny_old<dep" if (pair == "ny_close<dep" and w == "p70") else pair
            h = g[(g["쌍"] == pr) & (g["비교"] == w) & (g["person"] == who)].iloc[0]
            bb = b[(b["쌍"] == pr) & (b["비교"] == w) & (b["person"] == who)]["p_loss"]
            assert len(bb) == 3, (pr, w, who)
            lo, hi = bb.min(), bb.max()
            rows.append(dict(비교=label, 시점=W[w], 쌍=pr, person=who, 과거_적은해=int(h.loss_n), 과거_전체=int(h.n),
                             과거_비율=h.loss_n / h.n, 과거_판정=verdict(h.loss_n / h.n),
                             부트_최소=lo, 부트_최대=hi, 부트_가운데=(lo + hi) / 2, 판정=verdict((lo + hi) / 2)))
    t = pd.DataFrame(rows)
    t["판정_다름"] = t["판정"] != t["과거_판정"]
    t["경계_1pp"] = [min(abs(m - c) for c in (0.15, 0.35, 0.65)) < 0.01 for m in t["부트_가운데"]]
    pct = lambda x: f"{round(x * 100):.0f}"
    t["칸"] = [f"{r.과거_적은해}/{r.과거_전체} · " + (f"{pct(r.부트_최소)}%" if pct(r.부트_최소) == pct(r.부트_최대) else f"{pct(r.부트_최소)}~{pct(r.부트_최대)}%")
              + f" · {r.판정}" + (f" ※(과거: {r.과거_판정})" if r.판정_다름 else "") for r in t.itertuples()]
    t["판정_기준"] = "부트스트랩 가운데값"
    bp = rd(T3 / "results/N/bp_stats.csv")
    bp = bp[(bp.m == 300000) & (bp.asset == "A") & (bp.person == "가") & (bp.b == "B") & (bp.K1 == "전액") & (bp.K2 == "안넣음") & (bp["쌍"] == "ps<dep")]
    # 사람 B(기초연금): 부트스트랩 없음 → 과거 연도 비율로 판정. 표에는 중소도시·대도시만.
    tb = pd.DataFrame([dict(비교=f"연금저축 < 예금, 세금 0원 + 기초연금 경계 (사람 B, {r.region})", 시점="70세", 쌍="ps<dep", person="가",
                            과거_적은해=int(r.loss_n), 과거_전체=int(r.n), 과거_비율=r.loss_n / r.n, 과거_판정=verdict(r.loss_n / r.n),
                            판정=verdict(r.loss_n / r.n), 판정_다름=False, 경계_1pp=False, 판정_기준="과거 연도(부트스트랩 없음)",
                            칸=f"{int(r.loss_n)}/{int(r.n)} · 부트스트랩 없음 · {verdict(r.loss_n / r.n)}(과거 기준)")
                       for r in bp.itertuples() if r.region != "농어촌"])
    bp = {r.region: f"{int(r.loss_n)}/{int(r.n)}" for r in bp.itertuples()}
    return pd.concat([t, tb], ignore_index=True), bp


def cand5_ext():
    """03 README '75세까지 넓히면'·'처음 가진 돈이 3년 만기 예금이면': 사람 B (가)·★ 칸(K1 전액, 기본판 K2 안넣음,
    연기판 K2 넣음)·주식 100%·월 30만·중소도시, 연금저축 < 예금. 값 = '손해/전체 · 차이 중앙값(÷ 누적 납입)'."""
    def cell(f, K2):
        s = rd(T3 / "results/N" / f)
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
    tp = rd(T3 / "results/N/term_people.csv").set_index(["사람", "세금 그릇", "판", "해"])
    for k, key in (("비율_1년", ("B", "(가)", "i", "해마다")), ("비율_만기", ("B", "(가)", "ii", "만기 해")),
                   ("비율_만기아님", ("B", "(가)", "ii", "만기 아닌 해"))):
        out[k] = f"{tp.loc[key, '선정기준액 대비'] * 100:.1f}%"
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    out, loss = t4()
    assert out.loc["C 해지", "max"].max() < 0 and out.loc["D÷Y(타이밍 효과, 짝지음)"].abs().max().max() < 0.25
    th, d, cost = d_rule()
    assert d == dict(칸=234, P최소=0.16, P최대=0.59, P_05초과=51, 예시_규칙=6.46, 예시_위약=6.59, 예시_P=50.5), d
    assert th == {-0.3: (0.37, 0.59, 24, 78, 54), -0.2: (0.42, 0.55, 18, 78, 60), -0.1: (0.16, 0.51, 9, 78, 69)}, th
    pairs = i1()
    assert (pairs["min"] > 0).all()
    tab, bp = cand5()
    readme3 = (T3 / "README.md").read_text(encoding="utf-8")
    miss = [c for c in tab["칸"] if c not in readme3]
    assert not miss, f"03 README에 없는 칸: {miss}"
    assert bp["중소도시"] == "3/21" and bp["대도시"] == "10/21", bp
    ext = cand5_ext()
    miss = [f"{k}={v}" for k, v in ext.items() if v not in readme3]
    assert not miss, f"03 README에 없는 75세·3년 예금 숫자: {miss}"
    if "--csv" in sys.argv:
        tab.to_csv(sys.argv[sys.argv.index("--csv") + 1], index=False, encoding="utf-8-sig")
    print(out, loss, th, d, cost, pairs, t7().to_string(), tab.drop(columns="칸").round(3).to_string(), bp, ext, "ok", sep="\n\n")
