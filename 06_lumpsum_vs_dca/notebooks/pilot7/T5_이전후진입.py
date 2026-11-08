# %% [markdown]
# # 주제5 파일럿: 보험에서 옮긴 날이 고점이라면
# 연금저축보험을 펀드 계좌로 옮기면 목돈이 한 번에 현금으로 들어온다. **한 번에 넣기(LS)** vs **3~6개월 나눠 넣기(CA)**?
# 옮긴 날이 마침 사상 최고점(낙폭 0)이거나 약세장 한가운데라면 답이 바뀌나?
# **타깃: Finlay & Zorn(2023, Vanguard)** 설계 그대로: 분할 3·4·5·6개월, 평가 1년, 대기자금 0% 기본 + 단기금리(우리는 CD91) 민감도, 주식100·60/40·40/60. 시작 간격은 논문에 없음 → 월말마다(우리 데이터 주기).
# 계좌 안이라 세금 차이 없음. 매매비용: 연금계좌 ETF 0.0042%(삼성증권 1차) — 차이 무시 수준이라 0으로 둠(⚠명시).
# **보조 타깃**: 박영규·이상엽(2010) — 국내 1988–2008에서 1년 이하는 거치식(LS) 우위.

# %%
import numpy as np, pandas as pd
from pension_lab import pilot7 as P
from pension_lab.bootstrap import paired_resample_paths
OUT, SEED = P.OUT, P.SEED; OUT.mkdir(parents=True, exist_ok=True)
r = P.monthly().dropna(subset=["infl"]); H = 12      # CPI 없는 부분월(2026-09) 제외 — T4와 같은 표본

def ls_ca(pr, cash, k):
    """경로배열(n,H): LS와 k개월 CA의 H개월 뒤 자산(초기 1). CA: 매달 초 1/k 투자, 나머지는 cash."""
    ls = np.prod(1 + pr, axis=1)
    inv, wait = np.zeros(len(pr)), np.ones(len(pr))
    for t in range(pr.shape[1]):
        if t < k: inv += 1 / k; wait -= 1 / k
        inv *= 1 + pr[:, t]; wait *= 1 + cash[:, t]
    return ls, inv + wait

def windows(x):   # 롤링 H개월 창 (n,H), 시작 = 그 직전 월말
    a = x.to_numpy(); return np.lib.stride_tricks.sliding_window_view(a, H)

assert np.allclose(ls_ca(np.zeros((1, 12)), np.zeros((1, 12)), 3), (1, 1))

# %%
# 시작 상태 낙폭: SEC 정의(광범위 지수)대로 가격지수가 주 정의(KR: KOSPI200 1990~, US: S&P500 월말 종가 1965~), 총수익 낙폭은 민감도(KR 총수익은 1991~ 역사 기준)
SAMP = P.samples()                                        # KR 2004~ / KR 1991~ / US 1965~(월말) (한계 보완: 표본 연장·다국가)
KL = SAMP["KR 1991~"]
# 낙폭은 '가진 가장 긴 역사'로 잰 뒤 표본에 맞춤(4차 감사: 표본 시작점에서 다시 재면 과거 고점 무시)
DD_PX = {"KR 2004~": P.drawdown(P.kospi200_px()), "KR 1991~": P.drawdown(P.kospi200_px()), "US 1965~": P.drawdown(P.us_px_monthend())}
DD_TR = {"KR 2004~": P.drawdown(KL["eq"]), "KR 1991~": P.drawdown(KL["eq"]), "US 1965~": P.drawdown(SAMP["US 1965~"]["eq"])}

def indep(mask, off=0):   # 시작월이 12개월 이상 떨어진 창만(겹침 제거), 첫 창은 (첫 후보 + off개월) 이후
    out, last = [], -99; c = np.flatnonzero(mask)
    for i in (c[c >= c[0] + off] if len(c) else c):
        if i - last >= H: out.append(i); last = i
    return np.array(out, int)

rows = []
for smp, rr in SAMP.items():
    STATE = {"가격지수": DD_PX[smp].reindex(rr.index).to_numpy(), "총수익(민감도)": DD_TR[smp].reindex(rr.index).to_numpy()}
    for mix, w in P.MIX.items():
        pr = P.mix_ret(rr, w); W, C = windows(pr), windows(rr["cash"])
        for dname, dd in STATE.items():
            state = np.r_[np.nan, dd[:len(W) - 1]]             # 창 i 시작 상태 = 직전 월말
            for k in P.CA_MONTHS:
                for cname, cc in {"대기 0%": np.zeros_like(C), "대기 단기금리": C}.items():
                    ls, ca = ls_ca(W, cc, k)
                    for sname, m in {"전체": ~np.isnan(state), "최고점(낙폭 0)": state == 0, "약세장(낙폭≤−20%)": state <= P.BEAR}.items():
                        if not m.any(): continue
                        win = ls > ca; offs = [win[indep(m, o)].mean() for o in range(H) if len(indep(m, o))]
                        i0 = indep(m); lo, hi = P.wilson(int(win[i0].sum()), len(i0))
                        rows.append({"표본": smp, "상태정의": dname, "포트폴리오": mix, "분할": k, "대기자금": cname, "시작상태": sname, "n(겹친 창)": int(m.sum()),
                                     "LS 승률": win[m].mean(), "LS−CA 중앙값": np.median(ls[m] - ca[m]), "n(안 겹친 창)": len(i0),
                                     "LS 승률(안 겹친, 시작 0)": win[i0].mean(), "Wilson 95% 하": lo, "Wilson 95% 상": hi,
                                     "안 겹친 승률 범위(시작 0~11)": f"{min(offs):.2f}~{max(offs):.2f}"})
# 한국 1980~ 연장(6차 감사: '고점 창 8개'는 구조적 한계가 아님 — DataGuide 코스피 종합 일별 1980~): 주식100·대기 0%·가격수익(배당 없음 ⚠ → LS에 불리한 쪽)
KP = P.kospi_px_1980(); kpr = KP.pct_change().dropna().loc[:"2026-08"]; W80 = windows(kpr); dd80 = P.drawdown(kpr).to_numpy()   # drawdown은 수익률 입력
st80 = np.r_[np.nan, dd80[:len(W80) - 1]]; st80[:12] = np.nan                       # 자료 첫 12개월 제외(T5 다국가와 같은 규칙)
for k in P.CA_MONTHS:
    ls, ca = ls_ca(W80, np.zeros_like(W80), k); win = ls > ca
    for sname, m in {"전체": ~np.isnan(st80), "최고점(낙폭 0)": st80 == 0, "약세장(낙폭≤−20%)": st80 <= P.BEAR}.items():
        if not m.any(): continue
        offs = [win[indep(m, o)].mean() for o in range(H) if len(indep(m, o))]; i0 = indep(m); lo, hi = P.wilson(int(win[i0].sum()), len(i0))
        rows.append({"표본": "KR 1980~ 코스피 가격(배당 제외)", "상태정의": "가격지수", "포트폴리오": "주식100", "분할": k, "대기자금": "대기 0%", "시작상태": sname, "n(겹친 창)": int(m.sum()),
                     "LS 승률": win[m].mean(), "LS−CA 중앙값": np.median(ls[m] - ca[m]), "n(안 겹친 창)": len(i0), "LS 승률(안 겹친, 시작 0)": win[i0].mean(),
                     "Wilson 95% 하": lo, "Wilson 95% 상": hi, "안 겹친 승률 범위(시작 0~11)": f"{min(offs):.2f}~{max(offs):.2f}"})
hist = pd.DataFrame(rows); hist.to_csv(OUT / "T5_hist.csv", index=False, encoding="utf-8-sig")
display(hist[(hist["상태정의"] == "가격지수") & (hist["대기자금"] == "대기 0%")].pivot_table(index=["표본", "포트폴리오", "분할"], columns="시작상태", values="LS 승률").round(3))
hist[(hist["분할"] == 3) & (hist["대기자금"] == "대기 0%") & (hist["상태정의"] == "가격지수")][["표본", "포트폴리오", "시작상태", "n(겹친 창)", "LS 승률", "n(안 겹친 창)", "LS 승률(안 겹친, 시작 0)", "Wilson 95% 하", "Wilson 95% 상", "안 겹친 승률 범위(시작 0~11)"]].round(3)

# %% [markdown]
# Finlay & Zorn 보고값(참고): 3개월 분할 LS 승률 — 글로벌 USD 67.7%, 신흥국 61.6%, 미국 66.4% (100% 주식·대기 0%, PDF9).

# %% [markdown]
# ## 부트스트랩 (PW 평균블록, 10,000경로 = Finlay & Zorn PDF6) + Finlay & Zorn 확실성등가(CRRA γ=3/6/10): 승률이 아니라 위험회피 투자자의 후생으로도 비교
# (손실회피 λ=2.5 효용은 F&Z 부록 원식 미재현 → 생략, ⬜) — 무조건부

# %%
bt = []
BS = [("KR 2004~", SAMP["KR 2004~"]), ("KR 2004~ 2024년까지", SAMP["KR 2004~"].loc[:P.PRE]), ("KR 1991~", SAMP["KR 1991~"]), ("US 1965~", SAMP["US 1965~"])]
for (mix, w), (tag, rr) in [(m, t) for m in P.MIX.items() for t in BS]:
    pr = P.mix_ret(rr, w); b = P.pw_block(pr)
    R, C = paired_resample_paths([pr, rr["cash"]], P.NP, H, b, SEED)
    for k in P.CA_MONTHS:
        for cname, cc in {"대기 0%": np.zeros_like(C), "대기 단기금리": C}.items():
            ls, ca = ls_ca(R, cc, k); pw_ = (ls > ca).mean()
            bt.append({"포트폴리오": mix, "표본": tag, "평균블록": round(b, 2), "분할": k, "대기자금": cname, "LS 승률": pw_, "MC SE": float(P.mc_se(pw_, P.NP)), "LS−CA 중앙값": np.median(ls - ca),
                       **{f"CER차(LS−CA) γ={g}": P.cer(ls, g) - P.cer(ca, g) for g in P.GAMMAS}})
bt = pd.DataFrame(bt); bt.to_csv(OUT / "T5_boot.csv", index=False, encoding="utf-8-sig")
bt[(bt["분할"] == 3) & (bt["대기자금"] == "대기 0%")].round(4)

# %% [markdown]
# ## 다국가 월간 표본: French 국제 국가 포트폴리오 21개국 + 미국(1975~, 달러, 주식100) / OECD 17개국 현지통화(대기자금 = 각국 3개월 금리) — 한국 단일 표본의 '고점 시작 창이 몇 개 안 됨' 보완
# - 역사 창: 나라마다 12개월 롤링 창, 시작 상태 = 그 나라 총수익 낙폭(가격지수 없음 ⚠, 배당만큼 낙폭이 약간 작게 잡힘), 대기자금 = 미 1개월 T-bill.
#   각 나라 자료 첫 12개월은 시작 상태 판정에서 뺌(자료 시작점을 고점으로 오인). 독립성: 나라 안에서는 12개월 이상 떨어진 창만(위 indep 규칙), 나라끼리는 같은 달을 공유하므로 완전 독립 아님 → 나라 군집 부트스트랩 95% 구간 병기.
# - 부트스트랩: ACO 풀링(관측 비례 시작점), 평균블록 12·120개월.
# JST 16개국은 연→월 균등분할이라 '1년 안에서 나눠 넣기' 평가 불가 → 쓰지 않음.

# %%
PANELS = {"French 22개국(달러)": P.french_panel(need_infl=False),          # infl 안 씀 → CPI 공백(2025-10)으로 끊지 않음, 미국 포함
          "OECD 17개국(현지통화, 대기 = 현지 3개월 금리)": P.oecd_local_panel()}
fr_rows, by_c = [], []
for pname, FR in PANELS.items():
    for k, d in FR.items():
        W, C = windows(d["eq"]), windows(d["cash"]); dd = P.drawdown(d["eq"]).to_numpy(); st = np.r_[np.nan, dd[:len(W) - 1]]
        st[:12] = np.nan                                                         # 자료 첫 12개월은 '시작=고점' 착시 → 상태 판정에서 제외
        for kk in P.CA_MONTHS:
            for cname, cc in {"대기 0%": np.zeros_like(C), "대기 단기금리": C}.items():
                ls, ca = ls_ca(W, cc, kk); win = ls > ca
                for sname, m in {"전체": ~np.isnan(st), "최고점(낙폭 0)": st == 0, "약세장(낙폭≤−20%)": st <= P.BEAR}.items():
                    i0 = indep(m) if m.any() else np.array([], int)
                    by_c.append({"패널": pname, "나라": k.rsplit("_", 1)[0], "분할": kk, "대기자금": cname, "시작상태": sname, "n_겹침": int(m.sum()), "win_겹침": int(win[m].sum()),
                                 "n_독립": len(i0), "win_독립": int(win[i0].sum())})
bc = pd.DataFrame(by_c)
rng = np.random.default_rng(SEED)
for (pname, kk, cname, sname), g in bc.groupby(["패널", "분할", "대기자금", "시작상태"]):
    g = g[g["n_독립"] > 0]; lo, hi = P.wilson(int(g["win_독립"].sum()), int(g["n_독립"].sum()))
    bs = [g.iloc[i]["win_독립"].sum() / max(g.iloc[i]["n_독립"].sum(), 1) for i in (rng.integers(len(g), size=len(g)) for _ in range(2000))]
    fr_rows.append({"패널": pname, "분할": kk, "대기자금": cname, "시작상태": sname, "나라 수": g["나라"].nunique(), "조각 수": len(g), "n(겹친 창)": int(g["n_겹침"].sum()), "LS 승률(겹침)": g["win_겹침"].sum() / g["n_겹침"].sum(),
                    "n(안 겹친 창)": int(g["n_독립"].sum()), "LS 승률(안 겹친)": g["win_독립"].sum() / g["n_독립"].sum(), "Wilson 하": lo, "Wilson 상": hi,
                    "나라군집 부트 2.5%": np.quantile(bs, .025), "나라군집 부트 97.5%": np.quantile(bs, .975)})
fr = pd.DataFrame(fr_rows); fr.to_csv(OUT / "T5_french_hist.csv", index=False, encoding="utf-8-sig")
display(fr[fr["대기자금"] == "대기 0%"].round(3))

fb = []
for (pname, FR), blk in [(pp, b) for pp in PANELS.items() for b in (12.0, 120.0)]:
    EQ, CS = P.pooled_paths(FR, ["eq", "cash"], P.NP, H, blk, SEED)
    for kk in P.CA_MONTHS:
        for cname, cc in {"대기 0%": np.zeros_like(CS), "대기 단기금리": CS}.items():
            ls, ca = ls_ca(EQ, cc, kk); pw_ = (ls > ca).mean()
            fb.append({"패널": pname, "평균블록(ACO)": blk, "분할": kk, "대기자금": cname, "LS 승률": pw_, "MC SE": float(P.mc_se(pw_, P.NP)), "LS−CA 중앙값": np.median(ls - ca),
                       **{f"CER차(LS−CA) γ={g}": P.cer(ls, g) - P.cer(ca, g) for g in P.GAMMAS}})
fb = pd.DataFrame(fb); fb.to_csv(OUT / "T5_french_boot.csv", index=False, encoding="utf-8-sig"); fb.round(4)

# %% [markdown]
# ## 한계
# - '최고점' 시작 표본은 서로 겹치는 창(인접 월)이라 독립 표본 수가 n보다 훨씬 적다 → 안 겹친 창 Wilson 구간 병기, 표본 KR 1991~·US 1965~로 확장.
# - US는 월말 종가(1965~) + Shiller 배당. 대기자금 단기금리 = KR CD91, US 3개월 T-bill(DTB3). MC SE는 몬테카를로 오차만(표본이 한 번뿐인 불확실성 미포함).
# - 연금저축 계좌이전 규모·시점 통계는 공식 출처 없음(R3) → '얼마나 많은 사람이 고점에 옮겼나'는 이 파일럿으로 답 못 함.
