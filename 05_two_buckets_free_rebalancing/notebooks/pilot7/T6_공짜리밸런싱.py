# %% [markdown]
# # 주제6 파일럿: 연금계좌에서는 공짜인 리밸런싱
# 같은 60/40을 **연금저축 계좌**와 **일반 계좌**에서 리밸런싱하면 비용이 얼마나 다른가? 리밸런싱의 이득(안 하는 것 대비)이 일반계좌에선 세금·수수료로 얼마나 깎이나?
# **한국 세제의 반전(R1, 1차 조문)**: 일반계좌에서 국내주식형 ETF 매매차익은 **비과세**(분배금만 15.4%), 국고채·해외주식형 ETF 매매차익은 15.4%(법은 min(실제차익, 과표증분) — 코드는 실제차익 사용(두 값 거의 같다고 가정 ⚠), 매수단가 이동평균법 — 시행규칙 §13③⑥).
# → 국내주식/국고채 60/40은 '팔 때 세금'이 주로 채권 쪽에서만, 미국주식/국고채는 양쪽 다.
# **전략(타깃: Dichtl·Drobetz·Wambach)**: 방치(B&H) · 주기형 월/분기/연 · 임계형(±3% 벗어나면 목표로) 월/분기/연. 기간 5·7·10년(Dichtl PDF8). 부트스트랩 10,000경로, 평균블록 Politis–White.
# **비용**: 연금계좌 ETF 0.0042087%(삼성증권 1차) / 일반계좌 0.015%·0.147216%(금투협·삼성증권 1차; 정액 1,500원은 금액 의존이라 제외 ⚠).
# **끝 처리**: 기간 끝에 전부 판다고 보고 일반계좌는 미실현 과세이익에 15.4%, 연금계좌는 수익에 5.5%(연금수령). 손실은 다른 ETF 이익과 통산 안 함(조문 불명 → 보수적, ⚠).
# ⚠ 채권형 ETF 이자는 분배 안 하고 가격에 쌓인다고 가정(매도 시 과세). 해외 ETF 분배금 과세 시점 무시.

# %%
import numpy as np, pandas as pd
from pension_lab import pilot7 as P
from pension_lab.bootstrap import paired_resample_paths
OUT, SEED = P.OUT, P.SEED; OUT.mkdir(parents=True, exist_ok=True)
r = P.monthly(); W0, B = 0.6, P.NP   # B: Dichtl 1,000 → 분위수 안정 위해 F&Z 10,000(통계 감사 🟡12)
div_m = P.div_monthly(r.index)   # 과세표준 기준 월 분배율
STRATS = {"B&H": (None, None), "월 주기": (1, None), "분기 주기": (3, None), "연 주기": (12, None),
          "월 ±3%": (1, P.BAND), "분기 ±3%": (3, P.BAND), "연 ±3%": (12, P.BAND)}

def run(Re, Rb, D, every, band, fee, taxable, eq_taxed):
    """(n,T) 경로. 자산 0=주식, 1=채권. taxable이면 과세자산 매도차익 15.4%(이동평균 단가), 주식 분배금 15.4%. eq_taxed(해외주식)면 Re는 가격수익, D 분배를 따로 더함."""
    n, T = Re.shape; h = np.c_[np.full(n, W0), np.full(n, 1 - W0)].astype(float); b = h.copy()
    tx = np.array([eq_taxed, True]) & taxable
    for t in range(T):
        h[:, 0] *= 1 + Re[:, t]; h[:, 1] *= 1 + Rb[:, t]
        dv = D[:, t] * h[:, 0]
        if eq_taxed:                                                         # 해외주식형: Re = 가격수익 → 분배를 더함(일반계좌는 15.4% 원천징수 후), 재투자분은 취득가에 더함
            net = dv * (1 - P.TAX_FINANCIAL * taxable); h[:, 0] += net
            if taxable: b[:, 0] += net
        elif taxable: h[:, 0] -= P.TAX_FINANCIAL * dv                        # 국내주식형: Re = 총수익 → 분배금 과세만 차감
        if every and (t + 1) % every == 0:
            v = h.sum(1); w = h[:, 0] / v
            go = np.abs(w - W0) > band if band else np.ones(n, bool)
            tgt = np.c_[W0 * v, (1 - W0) * v]; d = np.where(go[:, None], tgt - h, 0.0)   # +매수 −매도
            sell = np.clip(-d, 0, None); gain = sell * (1 - b / np.where(h > 0, h, 1))
            tax = (P.TAX_FINANCIAL * np.clip(gain, 0, None) * tx).sum(1)
            b -= np.where(h > 0, sell / np.where(h > 0, h, 1), 0) * b              # 매도분 단가 비례 차감
            cost = fee * np.abs(d).sum(1) + tax
            buy = np.clip(d, 0, None); buy *= np.where(buy.sum(1) > 0, (buy.sum(1) - cost) / np.where(buy.sum(1) > 0, buy.sum(1), 1), 0)[:, None]
            h += buy - sell; b += buy
    if taxable:
        return h.sum(1) - (P.TAX_FINANCIAL * np.clip(h - b, 0, None) * tx).sum(1)
    return h.sum(1) - P.PENSION_UNDER70 * np.clip(h.sum(1) - 1, 0, None)

z = np.zeros((1, 12)); assert abs(run(z, z, z, 1, None, 0, True, True)[0] - 1) < 1e-12
# 손계산 점검: 채권만 첫 달 +10% → 연말 리밸런싱(채권 0.024 매도, 단가 0.4/0.44) → 끝에 청산.
# 실현+미실현 과세이익 합 = 채권 이익 0.04 전부 → 세금 0.154×0.04, 최종 1.04 − 0.00616 = 1.03384 (리밸런싱은 세금 '시점'만 바꿈)
e = np.zeros((1, 12)); bb = np.zeros((1, 12)); bb[0, 0] = 0.10
v = run(e, bb, z, 12, None, 0, True, True)[0]; assert abs(v - 1.03384) < 1e-4, v
dd0 = np.zeros((1, 12)); dd0[0, 0] = 0.01                                     # 해외주식 분배 1%: 0.6×1%×(1−15.4%) 재투자, 취득가에도 더함 → 매도차익 0
assert abs(run(z, z, dd0, None, None, 0, True, True)[0] - (1 + 0.006 * (1 - P.TAX_FINANCIAL))) < 1e-12
print("self-check ok", round(v, 6))

# %%
# 표본(한계 보완): KR 2004~(기본) + KR 1991~(확장; 국내주식 분배 = KOSPI200 배당수익률/12 × KODEX 과표비율 실측 평균, 1990년대는 DataGuide 시장 평균배당수익률).
# 미국주식 분배(일반계좌 해외주식형 ETF 분배금 15.4%): Shiller 배당 ÷ 전월말 S&P 종가. 수익은 '가격 + 분배'로 쪼개 분배는 매달 과세·재투자.
KL = P.monthly_kr_long(); RATIO = P.div_tax_ratio()
SMP = {"KR 2004~": (r, div_m), "KR 1991~": (KL, P.kr_div_yield().reindex(KL.index) * RATIO)}
DIVUS = {k: P.us_div_yield(v[0].index) for k, v in SMP.items()}
print("과표비율", round(RATIO, 4))
rows, keep = [], {}
for smp, (rr, dd) in SMP.items():
    for pname, eqcol, eq_taxed in [("국내주식/국고채", "eq", False), ("미국주식/국고채", "us", True)]:
        blk = P.pw_block(P.mix_ret(rr, W0, eqcol))
        for yrs in (5, 7, 10):
            dU = DIVUS[smp]; eqr = rr["eq"] if eqcol == "eq" else (1 + rr["us"]) / (1 + dU) - 1      # 미국: 가격수익(분배는 D로 따로)
            Re, Rb, D = paired_resample_paths([eqr, rr["bd"], dd if eqcol == "eq" else dU], B, 12 * yrs, blk, SEED)
            for acct, fee, taxable in [("연금계좌", P.FEE_PENSION, False)] + [(f"일반계좌 {k}", f, True) for k, f in P.FEE_TAXABLE.items()]:
                base = run(Re, Rb, D, None, None, fee, taxable, eq_taxed)
                for s_, (ev, band) in STRATS.items():
                    v = run(Re, Rb, D, ev, band, fee, taxable, eq_taxed); d = v / base - 1; keep[(smp, pname, yrs, acct, s_)] = d
                    rows.append({"표본": smp, "포트폴리오": pname, "기간(년)": yrs, "계좌": acct, "전략": s_, "평균블록": round(blk, 2),
                                 "세후 연수익 중앙값": np.median(v) ** (1 / yrs) - 1, "B&H 대비 중앙값": np.median(d),
                                 "P(B&H보다 나음)": (d > 0).mean(), "2.5%": np.quantile(d, .025), "97.5%": np.quantile(d, .975)})
res = pd.DataFrame(rows); res.to_csv(OUT / "T6_boot.csv", index=False, encoding="utf-8-sig")
res[res["기간(년)"] == 10].pivot_table(index=["표본", "포트폴리오", "전략"], columns="계좌", values="B&H 대비 중앙값").round(4)

# %% [markdown]
# ## 리밸런싱 이득이 계좌 때문에 깎이는 정도 — 같은 경로끼리 짝지은 차이 (일반 − 연금, 10년 누적 최종부 비율, %p)
# (경로별 짝지은 차이의 분포, 95% 구간. 표본마다 72칸이라 몇 칸은 우연히 0을 배제할 수 있음 → Holm형 조정 열과 기간·전략에 걸친 일관성으로 판단)

# %%
pr = []
for (smp, pname, yrs, acct, st), d in keep.items():
    if acct == "연금계좌" or st == "B&H": continue
    x = (d - keep[(smp, pname, yrs, "연금계좌", st)]) * 100
    lo, hi = np.quantile(x, [.025, .975])
    pr.append({"표본": smp, "포트폴리오": pname, "기간(년)": yrs, "계좌": acct, "전략": st, "중앙값": np.median(x), "2.5%": lo, "97.5%": hi,
               "0 배제(95%)": bool(hi < 0 or lo > 0), "경로 반대편 비율(양측)": max(2 * min((x <= 0).mean(), (x >= 0).mean()), 2 / B)})
pr = pd.DataFrame(pr)
# 다중비교: 표본별 72칸에 Holm 방식 조정. ⚠ '경로 반대편 비율'은 경로 분포(예측분포)에서 0 반대편에 있는 경로 비율이지 평균에 대한 검정 p값이 아님 — '몇 칸이 우연히 튀었나' 감 잡기용.
# 10,000경로에서 0이 나오면 최소 분해능 2/10,000으로 표기(×72 = 0.0144 < 0.05라 5% 판정 가능).
pr["Holm형 조정(검정 아님)"] = pr.groupby("표본")["경로 반대편 비율(양측)"].transform(lambda q: pd.Series(P.holm(q.to_numpy()), index=q.index))
pr.to_csv(OUT / "T6_paired.csv", index=False, encoding="utf-8-sig")
display(pr.groupby("표본").agg(칸수=("0 배제(95%)", "size"), 영배제=("0 배제(95%)", "sum"), 조정후_5pct미만=("Holm형 조정(검정 아님)", lambda q: int((q < .05).sum()))))
pr[pr["기간(년)"] == 10].round(3)

# %% [markdown]
# ## 역사 1경로(KR 2004~ 전체) 확인

# %%
hrow = []
for pname, eqcol, eq_taxed in [("국내주식/국고채", "eq", False), ("미국주식/국고채", "us", True)]:
    dU = DIVUS["KR 2004~"]; eqr = r["eq"] if eqcol == "eq" else (1 + r["us"]) / (1 + dU) - 1
    Re, Rb, D = (x.to_numpy()[None, :] for x in (eqr, r["bd"], div_m if eqcol == "eq" else dU))
    for acct, fee, taxable in [("연금계좌", P.FEE_PENSION, False)] + [(f"일반계좌 {k}", f, True) for k, f in P.FEE_TAXABLE.items()]:
        for s, (ev, band) in STRATS.items():
            hrow.append({"포트폴리오": pname, "계좌": acct, "전략": s, "세후 최종배수": run(Re, Rb, D, ev, band, fee, taxable, eq_taxed)[0]})
pd.DataFrame(hrow).pivot_table(index=["포트폴리오", "전략"], columns="계좌", values="세후 최종배수").round(4)

# %% [markdown]
# ## 읽는 법·한계
# - 'B&H 대비'가 모두 음수인 것은 표본기간 주식이 채권보다 훨씬 많이 올라 방치한 포트폴리오가 주식 쪽으로 쏠렸기 때문 — 리밸런싱의 본래 목적(위험 유지)은 이 표에 안 나온다(Dichtl은 Sharpe·Sortino·Omega로 평가). 이 파일럿의 관심은 **같은 전략의 계좌 간 차이**(두 번째 표).
# - 리밸런싱 자체의 가치(위험 유지)는 Dichtl의 Sharpe·Sortino·Omega로 봐야 하나 이 파일럿 범위(계좌 비용) 밖 → 미평가.
# - 연금계좌 끝 처리는 '내 돈을 옮겨 넣은' 틀(수익에만 5.5%) — 세액공제·공제원금 과세는 빠짐 → 계좌별 '수준' 비교에 쓰지 말 것, 같은 계좌 안 전략 비교용.
# - 미국주식 분배율은 S&P500 지수 배당(Shiller)으로 근사 — 실제 ETF 분기 분배 시점과 다름. 2023-07~2026-08은 S&P500 총수익지수−가격지수 월수익으로 배당 산출(6차 감사 연장).
# - 정액 수수료(1,500원/건)·호가스프레드(1차 근거 없음, R1 ⚠8)·손익통산 불가 가정은 일반계좌를 다소 불리하게 만들 수 있음.
