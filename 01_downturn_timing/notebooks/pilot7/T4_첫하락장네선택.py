# %% [markdown]
# # 주제4 파일럿: 첫 하락장을 맞은 새내기의 네 가지 선택
# 매달 같은 돈을 연금저축에 넣던 사회초년생이 처음으로 약세장(고점 대비 −20%, ≥2개월; SEC investor.gov)을 맞는다. 그때
# **A 계속 넣기 · B k개월 납입 중단(그 돈은 CD로) 후 몰아넣고 재개 · C 해지(16.5%) 후 k개월 뒤 새 계좌 · D 올해 남은 공제한도를 지금 당겨넣기**.
# 30년 뒤(연금 개시 시점) 세후·실질 자산이 어떻게 갈리나? (약세장 = 시장지수(국내주식) 기준 — 60/40 보유자도 같은 시장 사건에서 판단)
# **방법(타깃: Anarkulova·Cederburg·O'Doherty)**: 월 수익률 stationary bootstrap으로 360개월 경로 10,000개(경로 길이 360 = ACO, 경로 수 = Finlay & Zorn PDF6).
# **표본(한계 보완 + 4차 감사 반영)**: KR 2004~ / 그중 2024년까지 / 평균만 이동(ACO 한국 실질 0.73%/월) / KR 1991~(90년대 배당 = DataGuide 시장 평균배당수익률, 1993-08~ 채권 = DataGuide 일별 월말 금리) / KR 1991~(1993-07 이전 월평균 금리 구간 채권 변동성 보정) / US 1965~(월말 종가) /
# French 22개국 풀링(1975~ 월, MSCI·Bloomberg, 달러 실질, 주식100만) / OECD 17개국 풀링(French 현지통화 주식 + OECD 10년 국채금리 합성 TR + OECD 3개월 금리 + 현지 CPI, ~2024-02; 60/40 가능 — ACO의 현지 실질 방식) / JST 16개국 풀링(1870~2020 연 자료를 월로 균등 분할 → **수준 지표만**, 행동 비교 제외: 약세장 해의 남은 달 수익이 미리 정해져 미래정보 효과).
# 약세장 판정: 단일국은 **가격지수**(KOSPI200, S&P500 월말; SEC 정의), 풀링은 가격지수가 없어 총수익 주식 ⚠. 평균블록: 단일국 {그 표본 PW, iid, 12}(PW가 1이면 iid 하나로), 풀링 ACO {12, 120(기본), 240}개월.
# **근거 상수**: 월 납입 = 연 342만원÷12(금감원 2024 계약당), 공제한도 600만·납입한도 1,800만(§59의3·시행령 §40의2), 공제 16.5%, 해지 16.5%, 연금수령 5.5%, CD91 현금.
# **위약 대조군**: 약세장 시점(tau)을 경로끼리 섞어 같은 '행동 시점 분포'에서 약세장과의 연관만 끊음 → 실제 tau 결과와 같으면 효과는 하락장 때문이 아니라 행동 자체(추가 납입·해지 과세) 때문.
# **해지 후 재납입**: 연 납입한도 1,800만 초과분은 다음 해 1월부터 한도 안에서 이월 재납입. 계좌 밖 현금 이자는 15.4% 과세.
# **대조군 Y**: D와 같은 돈을 같은 해 12월에 넣음 → D−Y = '하락장에 당겨넣은 타이밍' 효과만, D−A에는 '더 넣어 공제·이연 받은 효과'가 섞임.
# **⬜결정(근거 없음, 민감도만)**: 중단·재진입 기간 k ∈ {1,3,6,12}개월 — 타깃논문 8편에 재진입 지연값 없음(R2 보고).

# %%
import numpy as np, pandas as pd
from pension_lab import pilot7 as P
from pension_lab.bootstrap import paired_resample_paths
OUT, SEED, NP, T = P.OUT, P.SEED, P.NP, 360
OUT.mkdir(parents=True, exist_ok=True)
r = P.monthly().dropna(subset=["infl"])          # CPI 있는 달만(마지막 부분월 제외) — 블록 추정과 재표본이 같은 표본
CAP = P.CREDIT_CAP / P.CONTRIB_YEAR * 12        # 월납입=1 단위 연 공제한도 (≈21.05)
LIM = P.CONTRIB_LIMIT / P.CONTRIB_YEAR * 12     # 연 납입한도 (≈63.2)
E = CAP - 12                                    # D가 당겨넣는 연 추가분(≈9.05) — 모든 전략에 같은 외부현금
print(len(r), "개월", r.index[0].date(), "~", r.index[-1].date(), "| CAP", round(CAP, 2), "LIM", round(LIM, 2), "E", round(E, 2))

def sim(R, Cr, tau, kind, k=0):
    """전략별 30년 뒤 세후 총자산(계좌 세후 + 계좌 밖 현금). 경로 시작 = 1월."""
    n = R.shape[0]; V, N, yc, cy, pend = (np.zeros(n) for _ in range(5)); cash = np.full(n, E)
    Ca = Cr * (1 - P.TAX_FINANCIAL); BC = kind in "BC"
    def contrib(x):
        nonlocal V, N, yc, cy
        xe = np.minimum(x, np.maximum(LIM - yc, 0)); cr = np.minimum(xe, np.maximum(CAP - yc, 0))
        V += xe; N += xe - cr; yc += xe; cy += cr
        return x - xe                                                    # 연 납입한도 초과분
    for t in range(R.shape[1]):
        if t % 12 == 0:
            yc[:] = 0; cy[:] = 0
            if BC:                                                       # 대기금(한도 초과분 포함)은 매년 1월 한도 안에서 재납입
                x = np.where(t > tau + k, pend, 0); pend += contrib(x) - x
        if kind == "C":
            ev = t == tau
            pend += np.where(ev, V - P.ETC_TAX * np.maximum(V - N, 0), 0); V = np.where(ev, 0, V); N = np.where(ev, 0, N)
        if kind in "DY":                                                 # D: 약세장 직후 / Y: 같은 금액 그해 12월
            x = np.where(t == (tau if kind == "D" else tau // 12 * 12 + 11), np.minimum(E, cash), 0); cash -= x; cash += contrib(x)
        pause = BC & (t >= tau) & (t < tau + k)
        pend += pause; o = contrib(np.where(pause, 0.0, 1.0))
        if BC: pend += o                                                 # 한도에 막힌 월납입도 이월(감사 2차 🟠1)
        else: cash += o
        if BC:
            x = np.where(t == tau + k, pend, 0); pend += contrib(x) - x
        V *= 1 + R[:, t]; cash *= 1 + Ca[:, t]; pend *= 1 + Ca[:, t]
        if t % 12 == 11: cash += P.CREDIT_LOW * cy                        # 연말정산 환급(실제 다음 해 2월: ⚠약간 낙관)
    return V - P.PENSION_UNDER70 * np.maximum(V - N, 0) + cash + pend

z = np.zeros((1, 24))
assert abs(sim(z, z, np.array([24]), "A")[0] - (24 + E + 0.165 * 24 - 0.055 * 24)) < 1e-9
assert abs(sim(z, z, np.array([6]), "C", 3)[0] - (23.01 * 0.945 + E + 0.165 * 29.01)) < 1e-9
# 손계산(감사 2차 🟠1): 수익 0, t=100 해지, k=3 → 대기금 86.5 중 t=103에 58.16(한도), t=104~107 월납은 한도에 막혀 이월,
# t=108에 32.34 재납입 → 계좌 원금 127.5(유출 0), 비공제 N = 42.11+11.29+12 = 65.4, 공제 대상 = 8×12 + 21.05×2 + 24
z2 = np.zeros((1, 144))
v = sim(z2, z2, np.array([100]), "C", 3)[0]
N_exp = 127.5 - ((CAP - 4) + CAP + 24)            # 계좌 원금 − 해지 뒤 공제받은 납입(8년차 잔여 CAP−4, 9년차 CAP, 10~11년차 24) = 65.4
assert abs(v - (127.5 - P.PENSION_UNDER70 * (127.5 - N_exp) + E + P.CREDIT_LOW * (96 + 2 * CAP + 24))) < 1e-9, v

# %%
def mean_adj(rr, target=0.0073):
    """국내주식 '실질 월 산술평균'만 ACO Table 3 한국값(1996–2019 실질 산술평균 0.73%/월)으로 이동. 변동성·2025~26 급등 달의 순서는 그대로(평균만 이동 — 급등 효과 '분리'가 아님)."""
    real = (1 + rr["eq"]) / (1 + rr["infl"]) - 1
    return rr.assign(eq=(1 + real - real.mean() + target) * (1 + rr["infl"]) - 1)

KPX, UPX = P.kospi200_px(), P.us_px_monthend()       # 약세장 판정 = 가격지수(SEC 정의), 월말
KL0 = P.monthly_kr_long(); KL1 = P.monthly_kr_long(bond_vol_adj=True)
US = P.monthly_us_long(); JST = P.jst_panel(); FR = P.french_panel(); OL = P.oecd_local_panel()
FR = {k: v.assign(bd=np.nan) for k, v in FR.items()}                     # 미국(1975~)은 french_panel 안에서 같은 RF·CPI로 추가됨
RA = mean_adj(r); KPX_A = KPX.reindex(r.index) + (RA["eq"] - r["eq"])    # 평균 이동분을 가격지수에도 같이 더함(판정과 수익이 같은 세계)
SAMPLES = [("KR 2004~", r, KPX), ("KR 2004~ 2024년까지", r.loc[:P.PRE], KPX), ("KR 2004~ 평균만 이동(ACO 0.73%)", RA, KPX_A),
           ("KR 1991~", KL0, KPX), ("KR 1991~ (1993-07 이전 채권 변동성 보정)", KL1, KPX),
           ("US 1965~ (월말)", US, UPX), ("French 22개국 풀링(월, USD 실질)", "FR", None), ("OECD 17개국 풀링(월, 현지통화 실질, 국채 합성)", "OL", None), ("JST 16개국 풀링(연→월, 수준만)", "JST", None)]
print("French 조각:", len(FR), "| 나라-월:", sum(len(v) for v in FR.values()), "| JST 조각:", len(JST), "나라:", len({k.split('_')[0] for k in JST}), "| 나라-연:", sum(len(v) for v in JST.values()) // 12)

def paths_for(rr, px, w, blk):
    if isinstance(rr, str):                                  # ACO 풀링 bootstrap(관측 수 비례 시작점, 조각 끝 → 무작위 조각 처음)
        pan = {k: v.assign(mix=w * v["eq"] + (1 - w) * v["bd"] if w < 1 else v["eq"]) for k, v in {"FR": FR, "OL": OL, "JST": JST}[rr].items()}
        M, EQ, C, I = P.pooled_paths(pan, ["mix", "eq", "cash", "infl"], NP, T, blk, SEED)
        return M, EQ, C, I                                   # 풀링: 약세장 판정은 총수익 주식(가격지수 없음 ⚠)
    M, PX, C, I = paired_resample_paths([P.mix_ret(rr, w), px.reindex(rr.index), rr["cash"], rr["infl"]], NP, T, blk, SEED)
    return M, PX, C, I

rows, share = [], []
for mix, w in {k: P.MIX[k] for k in ("주식100", "60/40")}.items():
    for name, rr, px in SAMPLES:
        tag = rr if isinstance(rr, str) else None
        if tag == "FR" and w < 1: continue                    # French 국제 자료엔 국가별 채권 없음 → 주식100만
        if isinstance(rr, str): blocks = [(12.0, "ACO 12개월"), (120.0, "ACO 120개월(기본)"), (240.0, "ACO 240개월")]
        else:
            pw = round(P.pw_block(P.mix_ret(rr, w)), 2)
            blocks = sorted({(1.0, "iid" if pw > 1 else "iid (=PW 추정 1)"), (12.0, "12개월")} | ({(pw, "PW(그 표본)")} if pw > 1 else set()))
        for blk, src in blocks:
            R, EQ, Cr, I = paths_for(rr, px, w, blk)
            tau = P.first_bear(EQ)
            defl = np.cumprod(1 + I, axis=1); has = tau < T - 12   # 약세장 뒤 최소 12개월 관측(표시용 기준)
            creal = (1 / np.c_[np.ones(NP), defl[:, :-1]]).sum(1) + E
            base = sim(R, Cr, tau, "A") / defl[:, -1]; pl = (base < creal).mean()
            share.append({"포트폴리오": mix, "표본": name, "평균블록": blk, "블록출처": src, "약세장 만난 경로(348개월 안)": has.mean(),
                          "첫 약세장 중앙값(개월)": np.median(tau[has]) if has.any() else np.nan,
                          "A: P(실질자산<실질납입)": pl, "MC SE": float(P.mc_se(pl, NP)),
                          "A: 실질자산/납입 1%": np.quantile(base / creal, .01), "A: 5%": np.quantile(base / creal, .05), "A: 50%": np.median(base / creal)})
            if tag == "JST": continue                         # 연→월 균등분할: 약세장 해의 남은 달 수익이 미리 정해짐 → 행동 비교는 미래정보 효과(4차 감사 🔴) → 수준만
            tau_p = np.random.default_rng(SEED).permutation(tau); has_p = tau_p < T - 12
            vals = {}
            for kind, ks in [("B 중단", P.REENTRY_GRID), ("C 해지", P.REENTRY_GRID), ("D 당겨넣기", [0]), ("Y 대조군(연말)", [0])]:
                for k in ks:
                    v = sim(R, Cr, tau, kind[0], k) / defl[:, -1]; q = (v / base)[has]; vals[kind[0]] = v
                    rows.append({"포트폴리오": mix, "표본": name, "평균블록": blk, "블록출처": src, "전략": kind, "k": k,
                                 "A대비 중앙값": np.median(q), "P(A보다 큼)": (q > 1 + 1e-12).mean(), "A대비 5%": np.quantile(q, .05), "A대비 95%": np.quantile(q, .95),
                                 "위약(시점 섞음) A대비 중앙값": np.median((sim(R, Cr, tau_p, kind[0], k) / defl[:, -1] / base)[has_p]) if kind[0] in "CD" else np.nan})
            dy = (vals["D"] / vals["Y"])[has]
            rows.append({"포트폴리오": mix, "표본": name, "평균블록": blk, "블록출처": src, "전략": "D÷Y(타이밍 효과, 짝지음)", "k": 0,
                         "A대비 중앙값": np.median(dy), "P(A보다 큼)": (dy > 1 + 1e-12).mean(), "A대비 5%": np.quantile(dy, .05), "A대비 95%": np.quantile(dy, .95)})
res = pd.DataFrame(rows); res.to_csv(OUT / "T4_boot.csv", index=False, encoding="utf-8-sig")
sh = pd.DataFrame(share); sh.to_csv(OUT / "T4_level.csv", index=False, encoding="utf-8-sig")
display(sh.round(4))
res.groupby(["포트폴리오", "표본", "전략"])["A대비 중앙값"].agg(["min", "max"]).round(4)

# %% [markdown]
# ## 위약 대조군 비교 (실제 약세장 시점 vs 섞은 시점)

# %%
res[res["전략"].str[0].isin(["C", "D"])].groupby(["포트폴리오", "표본", "전략"])[["A대비 중앙값", "위약(시점 섞음) A대비 중앙값"]].median().round(4)

# %% [markdown]
# ## 실제 역사: 국내주식 약세장 진입(KOSPI200 가격지수, 1991~) 뒤 총수익

# %%
ep = []
for s in [x for x in P.bear_starts(P.kospi200_px()) if x >= KL0.index[0]]:   # 가격지수 전체 역사(1990~)로 판정, 1991-04 이후 사건만
    f = KL0["eq"].loc[s:].iloc[1:]
    ep.append({"진입월": s.date(), **{f"{m}개월 뒤": (1 + f.iloc[:m]).prod() - 1 if len(f) >= m else np.nan for m in (6, 12, 24, 36)}})
pd.DataFrame(ep).round(3)

# %% [markdown]
# ## 한계
# - 공제는 모두 16.5%·결정세액 충분 가정(13.2%·공제 0원 사회초년생은 주제3 결과로 보정 필요). 1,500만원 분리과세 한도 미반영.
# - MC SE는 몬테카를로 오차만 — '역사가 한 번뿐'인 표본 불확실성은 표본·풀링 간 차이로 봐야 함.
# - French 패널은 달러 기준 투자자의 실질(미 CPI) — 각국 현지통화 실질 아님(현지 월 CPI 무료 자료 없음).
# - 해지 후 재납입분도 공제 한도 안이면 다시 공제받는 것으로 계산(법상 새 납입) — 실무 확인 필요.
