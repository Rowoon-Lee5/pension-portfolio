"""포트폴리오 그림 3장. 저장된 결과 CSV만 읽어 그린다(새 계산 없음, 표시용 빼기·최소/최대만).
실행: python notebooks/portfolio/make_figures.py  →  D:\\pension-lab_data\\results\\portfolio_figures_20261107\\
"""
import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from matplotlib.transforms import blended_transform_factory

RES = Path(r"D:\pension-lab_data\results")
OUT = RES / "portfolio_figures_20261107"
BLUE, GREY, LGREY = "#1F4E8C", "#9AA3AD", "#D3D8DD"
names = {f.name for f in fm.fontManager.ttflist}
plt.rcParams.update({"font.family": ["Malgun Gothic" if "Malgun Gothic" in names else "NanumGothic", "DejaVu Sans"],  # DejaVu = '−' 대체
                     "axes.unicode_minus": False, "figure.dpi": 100, "savefig.dpi": 200,
                     "axes.spines.top": False, "axes.spines.right": False})


def read(rel):
    p = RES / rel
    df = pd.read_csv(p)
    read.log.append(f"{p}\tsha256={hashlib.sha256(p.read_bytes()).hexdigest()}\trows={len(df)}")
    return df


read.log = []


def save(fig, name, data):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.png")
    fig.savefig(OUT / f"{name}.svg")
    plt.close(fig)
    data.to_csv(OUT / f"{name}_data.csv", index=False, encoding="utf-8-sig")
    (OUT / f"{name}_source.txt").write_text("\n".join(read.log) + "\n", encoding="utf-8")
    read.log = []


def head(fig, title, sub, note):
    fig.suptitle(title, x=0.02, ha="left", fontsize=15, fontweight="bold", y=0.975)
    fig.text(0.02, 0.915, sub, fontsize=9.5, color="#444", va="top", linespacing=1.4)
    fig.text(0.02, 0.012, note, fontsize=7.2, color="#666", linespacing=1.4)


# ── 그림 1. T4 첫 하락장: C 해지 vs A 계속 넣기 (주식100) ─────────────────────
def fig1():
    b, lv = read(r"pilot7_20261008\T4_boot.csv"), read(r"pilot7_20261008\T4_level.csv")
    S = {"KR 1991~": "한국 1991~", "KR 2004~": "한국 2004~", "US 1965~ (월말)": "미국 1965~",
         "French 22개국 풀링(월, USD 실질)": "22개국\n(달러 실질)"}
    S |= {s: "17개국\n(현지통화 실질)" for s in b["표본"].unique() if s.startswith("OECD 17개국")}
    c = b[(b["포트폴리오"] == "주식100") & (b["전략"] == "C 해지") & b["표본"].isin(S)].copy()
    assert c.groupby("표본").size().min() >= 8 and len(S) == 5, "표본 누락"
    for col in ["A대비 중앙값", "A대비 5%", "A대비 95%"]:
        c[col.replace("A대비", "%")] = (c[col] - 1) * 100
    order = list(S)
    c["g"] = c["표본"].map(order.index)
    c = c.sort_values(["g", "평균블록", "k"]).reset_index(drop=True)
    c["x"] = c["g"] + (c.groupby("g").cumcount() - c.groupby("g")["k"].transform("size").sub(1) / 2) * 0.055

    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_axes([0.08, 0.30, 0.90, 0.53])
    ax.axhline(0, color="black", lw=0.6)
    ax.vlines(c["x"], c["% 5%"], c["% 95%"], color=LGREY, lw=1.2)
    ax.scatter(c["x"], c["% 중앙값"], s=14, color=BLUE, zorder=3)
    for g, d in c.groupby("g"):
        ax.text(g, 11.5, f"중앙값 {d['% 중앙값'].max():.1f} ~ {d['% 중앙값'].min():.1f}%", color=BLUE, fontsize=8.5, ha="center")
    ax.text(-0.45, -33, "파란 점: 칸별 중앙값\n회색 선: 경로 5~95%", color="#666", fontsize=8)
    ax.set_ylim(-37, 14)
    ax.set_xticks(range(5), [S[s] for s in order], fontsize=9)
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylabel("30년 뒤 실질 자산, 계속 넣기 대비 (%)")

    a = lv[(lv["포트폴리오"] == "주식100") & lv["표본"].isin(S)].copy()
    a["p"] = a["A: P(실질자산<실질납입)"] * 100
    loss = a.groupby("표본")["p"].agg(["min", "max"]).reindex(order)
    tr = blended_transform_factory(ax.transData, fig.transFigure)
    for i, r in enumerate(loss.itertuples()):
        ax.text(i, 0.115, f"{r.min:.2f} ~ {r.max:.2f}%", ha="center", fontsize=10, color="#222", transform=tr)
    fig.text(0.02, 0.165, "표: '계속 넣기'의 30년 실질 손실 확률(실질 자산 < 실질 납입), 블록 길이별 범위", fontsize=9, color="#444")
    lo, hi = c["% 중앙값"].max(), c["% 중앙값"].min()
    assert lo < 0, "해지가 이득인 칸이 있음 — 제목 수정 필요"
    head(fig, f"첫 하락장에서 해지하면, 다섯 표본 모두 30년 뒤 실질 자산이 {-lo:.1f}~{-hi:.1f}% 적다",
         "해지(C) ÷ 계속 넣기(A), 30년 실질 자산의 부트스트랩 중앙값\n"
         "한국 1991-04~·2004-07~, 미국 1965-02~, French 22개국 1975~2025(달러 실질), OECD 17개국 ~2025(현지통화 실질)",
         "점 = 칸별 부트스트랩 중앙값(해지 시점 k=1·3·6·12개월 × 평균 블록 길이). 주식 100% 포트폴리오만(22개국 자료는 주식만 있음).\n"
         "단위는 금액 차이가 아니라 비율(해지 ÷ 계속 넣기 − 1). 출처: pilot7_20261008 T4_boot.csv·T4_level.csv.")
    out = c[["표본", "평균블록", "블록출처", "k", "% 중앙값", "% 5%", "% 95%", "P(A보다 큼)"]]
    out = pd.concat([out, loss.reset_index().rename(columns={"min": "A손실확률_최소_pct", "max": "A손실확률_최대_pct"})])
    save(fig, "fig1_T4_해지비용", out)
    return c, loss


# ── 그림 2. D 하락장 더 담기: 규칙 vs 매달 고르게(위약) ──────────────────────
def fig2():
    p = read(r"pilot9_20261013\D_simple_20261017\D_placebo.csv")
    k = read(r"pilot9_20261013\D_cost_20261106\D_cost.csv")
    for col in ["규칙_d_중앙", "위약_d_중앙", "규칙빼기위약_중앙"]:
        p[col] *= 100
    k["규칙빼기위약_중앙"] *= 100
    p = p.sort_values("규칙_d_중앙").reset_index(drop=True)
    p["x"] = np.arange(len(p))
    m = (p["표본"] == "KR-a") & (p["블록"] == "1") & (p["문턱"] == -0.2) & (p["복귀"] == "전고점 회복") & (p["증액"] == 0.10)
    assert m.sum() == 1
    key = p[m].iloc[0]

    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_axes([0.08, 0.17, 0.62, 0.65])
    ax.vlines(p["x"], p["규칙_d_중앙"], p["위약_d_중앙"], color=GREY, lw=0.8)
    ax.scatter(p["x"], p["위약_d_중앙"], s=7, color=GREY, zorder=2)
    ax.scatter(p["x"], p["규칙_d_중앙"], s=7, color=BLUE, zorder=3)
    ax.axhline(0, color="black", lw=0.6)
    ax.annotate(f"예시 칸(한국 KR-a, −20%·+10%p·전고점 복귀)\n규칙 {key['규칙_d_중앙']:.2f}  대  매달 고르게 {key['위약_d_중앙']:.2f} 로그%\n"
                f"규칙이 더 큰 경로 {key['P_규칙gt위약'] * 100:.1f}%",
                (key["x"], key["규칙_d_중앙"]), (5, 10.3), fontsize=8, arrowprops=dict(arrowstyle="-", color="#666", lw=0.6))
    last = p.iloc[-1]
    ax.text(len(p) + 10, last["규칙_d_중앙"] + 0.5, "하락장 규칙", color=BLUE, fontsize=9)
    ax.text(len(p) + 10, last["위약_d_중앙"] - 1.6, "매달 고르게\n같은 양", color="#666", fontsize=9)
    ax.set_xlim(-3, len(p) + 60)
    ax.set_xlabel(f"설정 칸 {len(p)}개 (규칙 이득 크기순)")
    ax.set_ylabel("60세 금액, 그대로 대비 이득 (로그 %)")
    ax.set_xticks([])
    pr = p["P_규칙gt위약"]
    ax.text(0, -1.6, f"칸별 '규칙이 더 큰 경로 비율' {pr.min():.2f}~{pr.max():.2f} (0.5 초과 {int((pr > 0.5).sum())}칸 / {len(p)})",
            fontsize=8, color="#444")
    ax.set_ylim(-2.3, 13.5)

    costs = ["0", "0.0036%", "0.015%", "0.3%(민감도)"]
    k = k[k["편도비용"].isin(costs)]
    bx = fig.add_axes([0.80, 0.17, 0.18, 0.60])
    bx.axvline(0, color="black", lw=0.6)
    rows = []
    for i, cst in enumerate(costs):
        v = k.loc[k["편도비용"] == cst, "규칙빼기위약_중앙"]
        bx.hlines(i, v.min(), v.max(), color=GREY, lw=6)
        bx.scatter(v, np.full(len(v), i), s=6, color=BLUE, zorder=3)
        rows.append(dict(편도비용=cst, 칸=len(v), 규칙빼기위약_최소=v.min(), 규칙빼기위약_최대=v.max()))
    bx.set_yticks(range(4), ["0", "0.0036%", "0.015%", "0.3%"], fontsize=8.5)
    bx.invert_yaxis()
    bx.set_xlabel("경로별 차의 중앙 (로그 %p)", fontsize=8.5)
    bx.set_title(f"편도 거래비용별\n규칙 − 매달 고르게\n({rows[0]['칸']}칸, 문턱 −20%)", fontsize=8.5, loc="left")
    head(fig, "하락장에 더 담는 규칙의 이득은, 같은 양을 매달 고르게 더 담은 것과 거의 같다",
         "한국 부트스트랩(KR-a·KR-b·KR-a~2024)·다국가 9개국 풀, 1만 경로, 30년 적립 후 60세 금액 · 단위 로그%",
         "'매달 고르게'(위약) = 규칙이 켜진 평균 추가 비중을 하락장과 상관없이 모든 달에 똑같이 더함(무작위 시점이 아님). 재무장 20%·총보수·납입 0%.\n"
         "로그% = ln(규칙 금액 ÷ 그대로 금액)×100. 출처: pilot9_20261013 D_simple_20261017\\D_placebo.csv(234칸), D_cost_20261106\\D_cost.csv.")
    cost = pd.DataFrame(rows)
    save(fig, "fig2_D_규칙대위약",
         pd.concat([p[["표본", "블록", "문턱", "복귀", "증액", "규칙_d_중앙", "위약_d_중앙", "규칙빼기위약_중앙", "P_규칙gt위약"]], cost]))
    return key, pr, cost


# ── 그림 3. T7 TDF − 직접 운용: 보수 몫 + 나머지 ─────────────────────────────
def fig3():
    s = read(r"pilot7_20261008\T7_holdings_summary.csv")
    h = read(r"pilot7_20261008\T7_holdings_hac.csv")
    col = "운용사 동일가중"
    g = lambda per, cmp: s.loc[(s["기간"] == per) & (s["비교"] == cmp)].iloc[0]
    hp = lambda ver, per: h.loc[(h["판본"] == ver) & (h["기간"] == per), "p"].iloc[0]
    rows = []
    for per, lab in [("전체", "2022~26\n(56개월)"), ("~2024", "~2024\n(35개월)"), ("2025~", "2025~\n(21개월)")]:
        for cmp, short, ver in [("TDF−스타일직접형(연)", "스타일 모형", "스타일"),
                                ("TDF−보유내역 ⑥원화몫=보고서(주식비중=글라이드)(연)", "보유내역", "⑥원화몫=보고서(주식비중=글라이드)")]:
            r = g(per, cmp)
            d = dict(기간=per, 기간명=lab, 비교=short, 총차이=r[col] * 100, 겉보수=r["래퍼 총보수 운용사 동일가중"] * 100,
                     하위보수=r["하위펀드 보수 운용사 동일가중"] * 100, p_총차이=hp(ver, per))
            d["나머지"] = d["총차이"] + d["겉보수"] + d["하위보수"]  # 표시용 분해: 총차이 = −보수 + 나머지
            if short == "보유내역":
                d["헤지_전부"] = g(per, "TDF−보유내역 ⑥+전부헤지(연)")[col] * 100
                d["헤지_전부비"] = g(per, "TDF−보유내역 ⑥+전부비헤지(연)")[col] * 100
                d["나머지_저장값"] = g(per, "TDF−⑥ + 합성보수(보수 외 차이)(연)")[col] * 100
                d["p_나머지"] = hp("⑥ + 합성보수(보수 외)", per)
                assert abs(d["나머지"] - d["나머지_저장값"]) < 0.01
            rows.append(d)
    t = pd.DataFrame(rows)

    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_axes([0.09, 0.21, 0.89, 0.60])
    ax.axhline(0, color="black", lw=0.6)
    for x, r in zip([0, 0.9, 2.3, 3.2, 4.6, 5.5], t.itertuples()):
        fee = -(r.겉보수 + r.하위보수)
        ax.bar(x, -r.겉보수, 0.7, color=GREY)
        ax.bar(x, -r.하위보수, 0.7, bottom=-r.겉보수, color=LGREY)
        ax.bar(x, r.나머지, 0.7, bottom=fee if r.나머지 < 0 else 0, color=BLUE)
        ax.scatter(x, r.총차이, marker="D", s=22, color="black", zorder=4)
        hedge = [r.헤지_전부, r.헤지_전부비] if r.비교 == "보유내역" else []
        if hedge:
            ax.vlines(x + 0.2, *hedge, color="black", lw=1)
            ax.hlines(hedge, x + 0.14, x + 0.26, color="black", lw=1)
        txt = f"{r.총차이:+.1f}%\n" + ("0과 구분 안 됨" if r.p_총차이 >= 0.05 else "p<0.001" if r.p_총차이 < 0.001 else f"p={r.p_총차이:.3f}")
        ax.text(x, min(r.총차이, fee, *hedge) - 0.25, txt, ha="center", va="top", fontsize=7.5)
        ax.text(x, 0.15 + max(r.나머지, 0), r.비교, ha="center", va="bottom", fontsize=8, color="#333")
    ax.set_xticks([0.45, 2.75, 5.05], t["기간명"].iloc[::2])
    ax.set_ylim(-9.6, 1.6)
    ax.set_xlim(-0.6, 7.3)
    ax.set_ylabel("TDF − 직접 운용, 연 수익률 차이 (%p)")
    r0 = t.iloc[1]
    ax.text(6.05, -r0.겉보수 / 2, f"겉보수 {r0.겉보수:.2f}%", fontsize=8, color="#555", va="center")
    ax.text(6.05, -r0.겉보수 - r0.하위보수 / 2 - 0.3, f"안에 담은 펀드\n보수 {r0.하위보수:.2f}%", fontsize=8, color="#777", va="center")
    ax.text(6.05, -2.4, "보수 외 나머지", fontsize=8, color=BLUE, va="center")
    ax.text(6.05, -3.4, "◆ 전체 차이\n┃ 환헤지 가정 범위\n  (전부 헤지 ~\n   전부 비헤지)", fontsize=7.5, color="#222", va="top")
    head(fig, f"TDF는 직접 운용보다 연 {-t.총차이.max():.1f}~{-t.총차이.min():.1f}%p 뒤졌고, 보수만 연 {r0.겉보수 + r0.하위보수:.1f}%p다",
         "TDF 수익률 − 같은 비중을 직접 운용한 수익률, 연율 · 2022~2026 월간, 3개 운용사 19펀드\n"
         "직접 운용 = 스타일 모형 추정 비중, 또는 분기 자산운용보고서 보유내역 재구성(⑥, 보고서 헤지비율)",
         "운용사 동일가중(KB·삼성·한국투자 19펀드). 보수 = 간이투자설명서 C 클래스 현행 값을 전 기간에 적용. 0과 구분 = 달별 HAC p<0.05(전체 차이 기준).\n"
         "보유내역 '보수 외' HAC p: " + ", ".join(f"{r.기간} {r.p_나머지:.2f}" for r in t[t.비교 == "보유내역"].itertuples()) +
         ". 신한은 환헤지 비율이 숫자로 공시되지 않아 빠짐. 현재 남아 있는 펀드만 봄(생존편향).\n"
         "출처: pilot7_20261008 T7_holdings_summary.csv·T7_holdings_hac.csv.")
    save(fig, "fig3_T7_보수분해", t)
    return t


if __name__ == "__main__":
    c, loss = fig1()
    key, pr, cost = fig2()
    t = fig3()
    pd.set_option("display.width", 200)
    print(loss.round(2), "\n", key[["규칙_d_중앙", "위약_d_중앙", "P_규칙gt위약"]], "\n", pr.min(), pr.max(), (pr > 0.5).sum())
    print(cost.round(4), "\n", t.round(3).to_string())
