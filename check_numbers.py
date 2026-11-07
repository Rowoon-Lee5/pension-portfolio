"""README 숫자 대조: 저장소 안 결과 CSV에서 README에 쓴 숫자를 다시 계산해 assert한다(새 시뮬레이션 없음).

실행: python check_numbers.py   (통과하면 'ok'와 표를 출력)
"""
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
    return dict(칸=len(p), P최소=round(pr.min(), 2), P최대=round(pr.max(), 2), P_05초과=int((pr > 0.5).sum()),
                예시_규칙=round(k["규칙_d_중앙"] * 100, 2), 예시_위약=round(k["위약_d_중앙"] * 100, 2), 예시_P=round(k["P_규칙gt위약"] * 100, 1)), cost


def i1():
    c = rd(T1 / "results/pilot10_I1_cost/I1_cost_pairs.csv")
    c = c[(c["분자"] == "더담기_D_+10")]
    return (c.groupby("편도비용")["d_중앙"].agg(["min", "max", "size"]) * [100, 100, 1]).round(2)


def t7():
    t = rd(T2 / "figures/fig3_T7_보수분해_data.csv")
    return t[["기간", "비교", "총차이", "겉보수", "하위보수", "나머지", "p_총차이", "p_나머지", "헤지_전부", "헤지_전부비"]].round(3)


def cand5():
    """상담표: 주식 100%(asset A)·월 30만 원·기준 셀, '앞쪽 < 뒤쪽'이었던 시작 연도 수 / 전체."""
    g = rd(T3 / "results/N/grid_stats.csv")
    g = g[(g["cell"] == "base") & (g["m"] == 300000) & (g["asset"] == "A")]
    f = lambda pair, when, who: "{}/{}".format(*g[(g["쌍"] == pair) & (g["비교"] == when) & (g["person"] == who)][["loss_n", "n"]].iloc[0].astype(int))
    W = ["wd36", "wd60", "p62", "p70"]
    rows = {"연금저축<예금 (가)": [f("ps<dep", w, "가") for w in W], "연금저축<예금 (다)": [f("ps<dep", w, "다") for w in W],
            "노란우산 해약<예금": [f("ny_cancel<dep", w, "가") for w in W[:2]] + ["", ""]}
    for who in "가나다":
        rows[f"노란우산 폐업·노령<예금 ({who})"] = [f("ny_close<dep", w, who) for w in W[:3]] + [f("ny_old<dep", "p70", who)]
    bp = rd(T3 / "results/N/bp_stats.csv")
    bp = bp[(bp.m == 300000) & (bp.asset == "A") & (bp.person == "가") & (bp.b == "B") & (bp.K1 == "전액") & (bp.K2 == "안넣음") & (bp["쌍"] == "ps<dep")]
    bp = {r.region: f"{int(r.loss_n)}/{int(r.n)}" for r in bp.itertuples()}
    return pd.DataFrame(rows, index=["3년", "5년", "62세", "70세"]).T, bp


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    out, loss = t4()
    assert out.loc["C 해지", "max"].max() < 0 and out.loc["D÷Y(타이밍 효과, 짝지음)"].abs().max().max() < 0.25
    d, cost = d_rule()
    assert d == dict(칸=234, P최소=0.16, P최대=0.59, P_05초과=51, 예시_규칙=6.46, 예시_위약=6.59, 예시_P=50.5), d
    pairs = i1()
    assert (pairs["min"] > 0).all()
    tab, bp = cand5()
    assert list(tab.loc["연금저축<예금 (가)"]) == ["14/32", "12/30", "10/29", "0/21"]
    assert list(tab.loc["연금저축<예금 (다)"]) == ["14/32", "11/30", "3/29", "0/21"]
    assert list(tab.loc["노란우산 해약<예금"])[:2] == ["32/32", "30/30"]
    assert list(tab.loc["노란우산 폐업·노령<예금 (가)"]) == ["14/32", "13/30", "13/29", "10/21"]
    assert list(tab.loc["노란우산 폐업·노령<예금 (나)"]) == ["8/32", "7/30", "7/29", "7/21"]
    assert list(tab.loc["노란우산 폐업·노령<예금 (다)"]) == ["0/32", "3/30", "2/29", "2/21"]
    assert bp["중소도시"] == "3/21" and bp["대도시"] == "10/21", bp
    print(out, loss, d, cost, pairs, t7().to_string(), tab, bp, "ok", sep="\n\n")
