# %% [markdown]
# # 주제1 파일럿: 급전이 필요할 때, 해지 대신 꺼내기
# **질문**: 연금저축에서 돈 X가 급히 필요할 때 **꺼내기(부분 인출)** vs **계좌 담보대출** vs **은행 신용대출** 중 무엇이 싼가? 하락장 한가운데라면?
# **법이 정한 인출 순서(시행령 §40의3①)** 때문에 '어떤 돈을 꺼낼지'는 고를 수 없다 — 계좌 상태로 정해진다(감사 A #3 반영):
# - 상태 ① 비공제분(공제 안 받은 납입) 잔액 ≥ X → 꺼내는 돈은 비과세 원금
# - 상태 ② 비공제분 0 → 공제분+수익을 꺼냄 → 기타소득세 16.5%
# - 상태 ③ 부득이한 사유(시행령 §20의2: 3개월 이상 요양, 파산·회생 등) → 연금소득세 5.5%로 분리과세
# **잣대**: 12개월 뒤(신한 담보대출 기간 365일) 순자산 감소. 계좌 안 돈은 나중에 연금으로 받을 때 5.5%를 떼므로 그만큼 깎아서 센다. 대출 원금은 12개월 뒤 계좌 밖 소득으로 갚는다고 봄(양쪽 같은 현금흐름).
# - 근거: `docs/ideas/7주제_파일럿_파라미터근거_20261008.md` (대출 5.00/6.33/6.55%, 담보 한도 50%·유지 140%, 세율, 약세장 −20% = SEC investor.gov)
# - **표본 3개(한계 보완)**: KR 2004~(기본), KR 1991~(1990년대 배당 = DataGuide 시장 평균배당수익률), US 1965~(월말 종가 + Shiller 배당; 한국 세제·금리를 미국 수익률에 얹은 반사실). 부트스트랩 확률에는 몬테카를로 표준오차(MC SE).
# - **대출금리 두 방식(회원 결정 2026-10-08, 병기)**: ① 2026년 값 고정 ② 그때 단기금리(KR CD91, US 3개월 T-bill) + 2026 가산폭(대출금리 − 그 기준시점 CD91: 신한 2025-12-31, ECOS 2026-08 평균). 1990년대 CD 10%+ 시기엔 ②가 대출을 훨씬 비싸게 만든다.

# %%
import numpy as np, pandas as pd
from pension_lab import pilot7 as P
from pension_lab.bootstrap import paired_resample_paths
OUT, SEED, NP, H = P.OUT, P.SEED, P.NP, P.LOAN_TERM_M
OUT.mkdir(parents=True, exist_ok=True)
MIXES = {k: P.MIX[k] for k in ("주식100", "60/40")}
SAMP = P.samples()
PXS = {"KR 2004~": P.kospi200_px(), "KR 1991~": P.kospi200_px(), "US 1965~": P.us_px_monthend()}   # 약세장 판정 = 가격지수(SEC), 월말
SPREAD = P.loan_spread()          # 가산폭 = 2026 대출금리 − 그 기준시점 CD91 (회원 결정: 두 방식 병기)
print({k: round(v, 4) for k, v in SPREAD.items()})
for k, v in SAMP.items(): print(f"{k}: {v.index[0].date()} ~ {v.index[-1].date()} ({len(v)}개월)")
RATE = ["2026 고정", "그때 단기금리+가산폭"]

def cost_table(R, short=None):
    """1원 마련 비용(12개월 뒤 세후 순자산 감소). R = 계좌 12개월 수익, short = 결정 시점 연 단기금리(그때 금리 방식)."""
    t = P.PENSION_UNDER70
    c = pd.DataFrame({"① 비공제분 인출": 1 + R * (1 - t),
                      "② 공제분 인출(16.5%)": (1 + R) * (1 - t) / (1 - P.ETC_TAX),
                      "③ 부득이 인출(5.5%)": 1 + R})
    for k, L in P.LOAN.items():
        c[(k, "2026 고정")] = 1 + L * H / 12
        if short is not None: c[(k, "그때 단기금리+가산폭")] = 1 + (np.asarray(short) + SPREAD[k]) * H / 12
    return c

ALTS = ["① 비공제분 인출", "② 공제분 인출(16.5%)", "③ 부득이 인출(5.5%)"]
rows, ev, boot = [], [], []
for sname, r in SAMP.items():
    short_now = (r["cash"].shift(-1) * 12)          # s월말 결정 시점의 연 단기금리(cash는 전월말 금리/12)
    for name, w in MIXES.items():
        pr = P.mix_ret(r, w); R = P.fwd(pr, H) - 1; c = cost_table(R, short_now.reindex(R.index))
        for loan in P.LOAN:
            for rate in RATE:
                for alt in ALTS:
                    d = (c[alt] - c[(loan, rate)]).dropna()
                    rows.append({"표본": sname, "포트폴리오": name, "대출": loan, "대출금리": rate, "비교(같은 계좌상태)": alt, "n(겹친 12개월 창)": len(d),
                                 "대출이 더 싼 비율": (d > 0).mean(), "비용차 중앙값": d.median()})
        px = PXS[sname]                                       # 전체 역사로 판정 후 표본 안 사건만
        for s in [x for x in P.bear_starts(px) if r.index[0] <= x <= r.index[-1]]:   # 약세장 진입 사건(가격지수 기준)
            f = pr.loc[s:].iloc[1:H + 1]
            if len(f) < H: ev.append({"표본": sname, "진입월": s.date(), "포트폴리오": name, "상태": "미완(12개월 미도래)"}); continue
            Rv = (1 + f).prod() - 1; low = (1 + f).cumprod().min() - 1; cv = cost_table(pd.Series([Rv]), [short_now.get(s, np.nan)]).iloc[0]
            k5 = "신한 연금저축담보 5.00%"
            ev.append({"표본": sname, "진입월": s.date(), "포트폴리오": name, "상태": "완료", "그때 단기금리": short_now.get(s, np.nan), "12개월 수익": Rv, "12개월 안 최저": low,
                       "반대매매 위험": low <= P.LOAN_MAINT * P.LOAN_LTV - 1,
                       **{f"담보대출({rt})가 {a[0]}보다 쌈": cv[a] > cv[(k5, rt)] for rt in RATE for a in ALTS[:2]}})
        tags = [("전체", r)] + ([("2024년까지", r.loc[:P.PRE])] if sname == "KR 2004~" else [])
        for tag, rr in tags:
            prr = P.mix_ret(rr, w); b = round(P.pw_block(prr), 2)
            blocks = sorted({(1.0, "iid" if b > 1 else "iid (=PW 추정 1)"), (12.0, "12개월")} | ({(b, "PW(그 표본)")} if b > 1 else set()))
            for blk, src in blocks:
                Rp, Cp = paired_resample_paths([prr, rr["cash"]], NP, H, blk, SEED)
                Rb = pd.Series(np.prod(1 + Rp, axis=1) - 1); cb = cost_table(Rb, Cp[:, 0] * 12)
                for loan in P.LOAN:
                    for rate in RATE:
                        qs = {a: (cb[a] > cb[(loan, rate)]).mean() for a in ALTS}
                        boot.append({"표본": sname, "기간": tag, "포트폴리오": name, "평균블록": blk, "블록출처": src, "대출": loan, "대출금리": rate,
                                     "P(대출<①)": qs[ALTS[0]], "P(대출<②)": qs[ALTS[1]], "P(대출<③)": qs[ALTS[2]],
                                     "MC SE(최대)": float(max(P.mc_se(q, NP) for q in qs.values()))})
hist, ev, boot = pd.DataFrame(rows), pd.DataFrame(ev), pd.DataFrame(boot)
for n, x in [("T1_hist", hist), ("T1_events", ev), ("T1_boot", boot)]: x.to_csv(OUT / f"{n}.csv", index=False, encoding="utf-8-sig")
hist[hist["대출"].str.startswith("신한")].pivot_table(index=["포트폴리오", "비교(같은 계좌상태)"], columns=["표본", "대출금리"], values="대출이 더 싼 비율").round(3)

# %% [markdown]
# ## 약세장 진입 사건(사건 단위, 가격지수 기준) — 표본 3개 합치면 독립 사건이 늘어남. 같은 시장의 사건은 KR 두 표본에서 겹침.

# %%
e = ev[ev["상태"] == "완료"]; B = [c for c in ev.columns if c.startswith("담보대출(")] + ["반대매매 위험"]
display(e.assign(**{c: e[c].astype(bool).astype(int) for c in B}).groupby(["표본", "포트폴리오"])[B].agg(["sum", "count"]))
ev.round(3)

# %% [markdown]
# ## 부트스트랩 (표본·블록·대출금리 방식별, MC SE ≤ 0.005)

# %%
boot.pivot_table(index=["표본", "기간", "포트폴리오", "대출금리"], columns="대출", values=["P(대출<①)", "P(대출<②)"], aggfunc=["min", "max"]).round(3)

# %% [markdown]
# ## 손익분기·결정론적 부분

# %%
be = pd.DataFrame({k: {"vs ① 비공제분": L / (1 - P.PENSION_UNDER70), "vs ② 공제분(16.5%)": (1 + L) * (1 - P.ETC_TAX) / (1 - P.PENSION_UNDER70) - 1,
                       "vs ③ 부득이(5.5%)": L} for k, L in P.LOAN.items()}).T
be.to_csv(OUT / "T1_breakeven.csv", encoding="utf-8-sig")
det = pd.DataFrame({"공제율": [P.CREDIT_LOW, P.CREDIT_HIGH]}); det["공제분 1원 인출 순손익"] = det["공제율"] - P.ETC_TAX
det.to_csv(OUT / "T1_det.csv", index=False, encoding="utf-8-sig"); display(be.round(4)); det.round(3)

# %% [markdown]
# ## 한계
# - 비공제분을 꺼내면 이후 §118의3 전환특례를 실무상 못 쓸 수 있음(KB, 조문 원문 미확인). 손실 시 ① 식은 과세분이 손실을 흡수한다는 전제(§40의3⑤).
# - 세율은 한국 2026년 법 → 과거 수익률에 현재 세법을 얹은 반사실. 미국 표본의 '그때 금리'는 T-bill + 한국 가산폭(반사실).
