# %% [markdown]
# # 주제3 파일럿: 사회초년생 두 통 설계
# **질문**: 1원을 어디에 넣을까? ① 연금저축 + 세액공제(공제통) ② 연금저축이지만 공제 못 받음(비공제통 — 결정세액 0원) ③ 일반계좌 ETF. 꺼내는 시점(55세 전 / 55세 이후 연금)에 따라 순위가 바뀌나?
# **규칙(1차 조문)**: 공제 16.5/13.2%(§59의3) · 연금수령 5.5%(§129①5의2; 요건 55세 이상·가입 5년·수령한도) · 55세 전 인출 16.5%(공제분+수익; 비공제 원금 비과세, 시행령 §40의3) · 일반계좌 국내주식형 ETF 매매차익 비과세+분배금 15.4%(과세표준 기준), 해외주식형 매매차익 15.4%(시행령 §26의2, 시행규칙 §13).
# **같은 자산을 각 통에** 넣어 계좌 차이만 본다: 국내주식, 미국주식(원화). 보유기간 h = 1~30년 전부(롤링 월 시작). 표본: KR 2004~(기본), KR 1991~(확장; 1990년대 배당 = DataGuide 시장 평균배당수익률, 분배 과세는 그 표본의 배당과 같은 값에). **h ≥ 21년은 KR 1991~ 한 표본뿐이고 서로 겹친 창이라 독립 창은 1~2개 → 비율이 아니라 사례로 읽을 것**('독립 창 수' 열).
# 일반계좌 미국주식: 매달 분배금 15.4% 원천징수 후 재투자 + 매도 시 차익 15.4%(분배율 = Shiller 배당 ÷ 전월말 종가, 2023-07~2026-08은 S&P500 총수익−가격 월수익).
# **환급금 처리(감사 A #1)** — 근거로 하나를 정할 수 없어 둘 다: (a) CD 예금(이자 15.4% 과세) (b) 같은 자산을 일반계좌에서 매수. 환급 시점 = 연말정산 2월 → 납입월에 따라 2~13개월 뒤, 두 끝값 모두.
# **연금수령 행**: 가입 5년 요건 때문에 h<5는 불가(빈칸). 'h년 뒤 55세가 된다'는 뜻으로 읽을 것. 수령한도로 한 번에 다 못 받는 점은 단순화(⚠).

# %%
import numpy as np, pandas as pd
from pension_lab import pilot7 as P
OUT = P.OUT; OUT.mkdir(parents=True, exist_ok=True)
grow = P.fwd   # s월말 → s+lag+1..s+n 누적배수
TX = P.TAX_FINANCIAL

def gen_us(p, dy, n, lag=0):
    """일반계좌 해외주식형 ETF 세후배수(s월말 매수 → s+lag+1..s+n 보유 → 매도). 매달 분배금 15.4% 원천징수 후 재투자(재투자분은 취득가에 더함),
    매도 시 (평가액 − 취득가)의 15.4%(시행령 §26의2④, 이동평균 단가). p = 가격수익, dy = 월 분배율."""
    a, d = p.to_numpy(float), dy.to_numpy(float); m = n - lag; S = len(a) - n
    if S <= 0: return pd.Series(dtype=float)
    V, B = np.ones(S), np.ones(S)
    for j in range(m):
        col = np.arange(S) + lag + 1 + j
        V *= 1 + a[col]; net = V * d[col] * (1 - TX); V += net; B += net
    return pd.Series(V - TX * np.clip(V - B, 0, None), index=p.index[:S])

_p = pd.Series([0.0, 0.10, 0.0], index=pd.date_range("2000", periods=3, freq="ME")); _d = pd.Series([0, 0.0, 0.01], index=_p.index)
assert abs(gen_us(_p, _d, 2).iloc[0] - (1.1 + 1.1 * 0.01 * (1 - TX) - TX * 0.1)) < 1e-12      # 손계산: 가격 +10%, 분배 1%(세후 재투자)

rows = []
for sname, r in P.samples(us_col=True).items():
    # 국내주식 일반계좌: 매매차익 비과세, 분배금 15.4%(과세표준 기준). KR 2004~ = KODEX200 실제 분배(배당락 월),
    # KR 1991~ = 이 표본 eq에 넣은 배당수익률 × 과표비율(KODEX 실측 평균) 전 기간 — 수익과 세금이 같은 배당(4차 감사 🟠2, T6과 같은 규칙)
    D_kr = P.div_monthly(r.index) if sname == "KR 2004~" else P.kr_div_yield().reindex(r.index) * P.div_tax_ratio()
    eq_gen = r["eq"] - TX * D_kr
    dy_us = P.us_div_yield(r.index); p_us = (1 + r["us"]) / (1 + dy_us) - 1          # 미국주식 = 가격 + 분배(Shiller 배당 ÷ 전월말 종가)
    cash_at = r["cash"] * (1 - TX)                                                   # CD 이자 15.4% 과세
    for h in range(1, 31):
        n = 12 * h
        for asset in ("국내주식", "미국주식"):
            ret = r["eq"] if asset == "국내주식" else r["us"]
            G = grow(ret, n)
            gen_full = grow(eq_gen, n) if asset == "국내주식" else gen_us(p_us, dy_us, n)
            for lag in (2, 13):
                if lag >= n: continue
                Cd = grow(cash_at, n, lag)
                gen_lag = grow(eq_gen, n, lag) if asset == "국내주식" else gen_us(p_us, dy_us, n, lag)
                idx = G.index.intersection(gen_full.index).intersection(Cd.index).intersection(gen_lag.index)
                if len(idx) < 12: continue
                g, gen = G[idx] - 1, gen_full[idx]
                refund = {"CD(세후)": Cd[idx], "같은자산 일반계좌": gen_lag[idx]}
                for exitk, t in [("55세 이후 연금(5.5%)", P.PENSION_UNDER70), ("55세 전 인출(16.5%)", P.ETC_TAX)]:
                    if exitk.startswith("55세 이후") and h < 5: continue
                    v = {"비공제통": 1 + g - t * g.clip(lower=0)} if lag == 2 else {}
                    for cr in (P.CREDIT_LOW, P.CREDIT_HIGH):
                        for rk, rv in refund.items():
                            v[f"공제통 {cr:.1%} / 환급금 {rk}"] = (1 + g) * (1 - t) + cr * rv
                    for bname, val in v.items():
                        rows.append({"표본": sname, "h년": h, "자산": asset, "인출": exitk, "통": bname, "환급지연(개월)": lag, "n": len(idx),
                                     "안 겹친 창 수": (len(idx) - 1) // n + 1,
                                     "세후배수 중앙값": val.median(), "일반계좌 중앙값": gen.median(),
                                     "일반계좌보다 나은 비율": float((val > gen + 1e-12).mean()), "같은 비율": float((abs(val - gen) <= 1e-12).mean()),
                                     "나은 비율(창이 2024-12 안에서 끝남)": float((val > gen + 1e-12)[val.index + pd.offsets.MonthEnd(n) <= pd.Timestamp(P.PRE) + pd.offsets.MonthEnd(0)].mean())})
res = pd.DataFrame(rows); res.to_csv(OUT / "T3_buckets.csv", index=False, encoding="utf-8-sig")
print(res.groupby(["표본", "h년"]).n.max().unstack(0).loc[[1, 10, 20, 25, 30]])

# %% [markdown]
# ## (읽는 법: '창이 2024-12 안에서 끝남' 열이 빈칸이면 그 h에는 그런 창이 없다는 뜻)
# ## 핵심 1: 결정세액 0원 사회초년생(공제 불가) — 비공제통 vs 일반계좌 ('나은 비율', 환급 없음이라 지연 무관)

# %%
k = res[res["통"] == "비공제통"]
k.pivot_table(index="h년", columns=["표본", "자산", "인출"], values=["일반계좌보다 나은 비율", "나은 비율(창이 2024-12 안에서 끝남)"]).reindex([1, 3, 5, 10, 15, 20, 25, 30]).round(2)

# %% [markdown]
# ## 핵심 2: 공제통(16.5%)은 환급금을 어디 두느냐에 따라 55세 전 인출 결론이 바뀌나

# %%
k2 = res[res["통"].str.startswith("공제통 16.5%") & (res["인출"] == "55세 전 인출(16.5%)")]
k2.pivot_table(index="h년", columns=["표본", "자산", "통", "환급지연(개월)"], values="일반계좌보다 나은 비율").reindex([3, 5, 10, 15, 20, 25, 30]).round(2)

# %% [markdown]
# ## 한계
# - 공제율 16.5%와 55세 전 인출세 16.5%가 같아서, 환급금을 같은 자산에 다시 넣으면 공제통은 '세금 시점만 바뀐' 일반계좌와 거의 같아진다 — 결론이 환급금 사용 방식에 민감(⬜ 회원/교수 결정: 기준 시나리오).
# - 미국주식 분배율은 S&P500 지수 배당(Shiller)으로 근사 — 실제 ETF 분배 시점(분기)·환율 시점과 다름. 2023-07~2026-08은 S&P500 총수익지수−가격지수 월수익으로 배당 산출(6차 감사 연장).
# - 겹치는 창: 비율은 독립 관측이 아니며 h가 길수록 2025~26에 끝나는 창 비중이 커짐(h=20은 78%) → "2024-12 안에서 끝나는 창" 열을 같이 봄.
# - 1,500만원 분리과세 한도·종합과세 선택·연도별 세율 개정 미반영. 전환특례(§118의3)로 비공제분 일부를 다음 해 공제분으로 바꿀 수 있음(실무 제약 미확인).
