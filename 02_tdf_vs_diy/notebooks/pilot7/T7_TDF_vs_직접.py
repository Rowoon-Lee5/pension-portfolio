# %% [markdown]
# # 주제7 파일럿: TDF 하나 vs 직접 리밸런싱 vs 방치 vs 겁먹고 빼기
# 같은 연금저축 계좌 안에서 ① TDF 하나(실제 기준가, 보수 차감 후) ② 그 TDF의 **공시 글라이드패스**를 ETF로 직접 따라가기(월/연 리밸런싱) ③ 처음 비중으로 사서 방치 ④ 직접형인데 약세장(−20%)에 현금 피신 후 k개월 뒤 복귀.
# **직접형 구성 두 가지(감사 C 반영)**
# - (가) **구성 맞춤형(실행 가능, 주 비교)**: 위험·안전자산 안 구성비를 펀드별 스타일분석(Sharpe 1992, `tdf_style`)으로 **매년 1월 직전까지의 자료로만** 재추정(확장창). TDF − (가) = 보수 + 운용사 재량 + 모형오차.
# - (가′) 구성 맞춤형(사후, 상한 참고): 전기간 스타일 비중 — 사후정보라 차이를 더 크게 보이게 함(감사 2차 결함 1).
# - (나) 단순 2-ETF형: 국내 {15.2% = 이 노트북의 전기간(사후) 스타일 재추정 중앙값, 35% = 가정_전수조사 #4} × 해외(헤지) + 국고채.
# - 피신 트리거: **시장지수 약세장**(KOSPI200 가격지수 `bear_starts`, SEC 정의) 다음 달부터 k개월 현금 — 혼합 포트폴리오 자체 낙폭(−20%에 거의 안 닿음)이 아님.
# - 확장창 첫 추정에 필요한 최소 개월 수 = 36, 비교 구간도 36개월 이상인 펀드만 (⬜결정, 근거 없음 — 첫 추정 24로 민감도).
# - 기준가: 결산 분배 하락을 제거한 정제본 `clean_v3`, 자산 가격은 펀드 기준가일에 시차 맞춤·헤지 carry(CD91 − 미 T-bill) 포함 = `tdf_style.panel` 재사용.
# - 비용: ETF 가격은 보수 차감 후(KODEX200 수정주가, SPY/EFA/EEM), 국고채 지수는 TER 0.17% 차감, 매매 0.0042087%(연금계좌).
# - 재진입 k = ⬜결정 그리드(근거 없음).

# %%
import numpy as np, pandas as pd
from pension_lab import pilot7 as P, paths, glidepath as gp, tdf_style as ts, perfstats as ps
from pension_lab.bootstrap import paired_bootstrap_diff, cagr_from_returns, mdd_from_returns
OUT, SEED = P.OUT, P.SEED; OUT.mkdir(parents=True, exist_ok=True)
nav = ts.load_nav("clean_v3"); nav = nav.loc[:, [c for c in gp.CODE2VINTAGE if c in nav]]
PX, _, _ = ts.panel(nav, "full"); gl = ts.glide_table()
RISKY = ["kr_eq", "gl_eq_h", "gl_eq_uh", "dm_eq_h", "dm_eq_uh", "em_eq_h", "em_eq_uh"]; SAFE = ["kr_bd", "gl_bd_h", "cash"]
BEAR_M = set(P.bear_starts(P.kospi200_px()))            # 시장 약세장 판정월
fee = pd.read_csv(paths.FUND_TDF / "tdf_fee_c_class.csv", parse_dates=["start", "end"])   # KOFIA 간이공시 보수(기간별)

def monthly_rets(c):
    m = ts.monthly(PX[c]).loc[:, ["fund"] + ts.A10]; m.index = m.index.to_timestamp(how="end").normalize()
    m["kr_bd"] -= P.BD_TER / 12
    return m.dropna()

def split(w):
    wr, ws = w[RISKY], w[SAFE]
    return wr / wr.sum(), (ws / ws.sum() if ws.sum() > 1e-9 else pd.Series([1.0, 0, 0], index=SAFE))

def style_w(m):
    return pd.Series(ts.style(m["fund"].to_numpy(), m[ts.A10].to_numpy()), index=ts.A10)

def weights_path(m, mode, min_m=36):
    """월별 (위험 안 구성, 안전 안 구성). full=전기간 사후 / expand=매년 1월 직전까지로 재추정(그 전 달은 NaN)."""
    if mode == "full":
        return {t: split(style_w(m)) for t in m.index}
    out, cur = {}, None
    for t in m.index:
        if t.month == 1 or cur is None:
            past = m.loc[: t - pd.offsets.MonthEnd(1)]
            cur = split(style_w(past)) if len(past) >= min_m else None
        if cur is not None: out[t] = cur
    return out

def diy(c, m, wp, every=1, panic_k=None, efn=None):
    """공시 글라이드 e(t) × 구성비(wp: 월→(위험,안전)). every=None 방치. 피신: 시장 약세장 판정 다음 달부터 k개월 현금."""
    idx = [t for t in m.index if t in wp]; m = m.loc[idx]
    e = (efn or (lambda ix: ts.glide_fn(c, gl)(ts.yrs_rel(ix, c))))(m.index); cols = RISKY + SAFE
    tgt = np.array([np.r_[ei * wp[t][0].reindex(RISKY, fill_value=0.0).to_numpy(), (1 - ei) * wp[t][1].reindex(SAFE, fill_value=0.0).to_numpy()] for ei, t in zip(e, idx)])
    R = m[cols].to_numpy(); icash = cols.index("cash"); h = tgt[0].copy(); out = []; out_until = -1
    for i, t in enumerate(idx):
        v0 = h.sum(); back = panic_k and i == out_until + 1 and out_until >= 0
        if panic_k and i <= out_until: w = np.zeros(len(cols)); w[icash] = v0
        elif (every and i % every == 0) or back: w = tgt[i] * v0
        else: w = h
        h = w * (1 - P.FEE_PENSION * np.abs(w - h).sum() / v0) * (1 + R[i]); out.append(h.sum() / v0 - 1)
        if panic_k and i > out_until and t in BEAR_M: out_until = i + panic_k
    return pd.Series(out, index=idx)

def stats(x):
    a = x.to_numpy(float); return {"연수익": cagr_from_returns(a, 12), "연변동성": a.std(ddof=1) * 12 ** .5, "MDD": mdd_from_returns(a)}

def avg_fee(c, idx):
    f = fee[fee.standardCd == c]; return np.mean([f[(f.start <= t) & (f.end >= t)].fee_pct.iloc[0] for t in idx]) / 100

assert abs(stats(pd.Series([-0.3, 0.1]))["MDD"] + 0.3) < 1e-12

# %%
rows, dl, wt, DS = [], [], [], {}
for c in nav.columns:
    m = monthly_rets(c)
    if len(m) < 36: continue
    wf = weights_path(m, "full"); we = weights_path(m, "expand"); we24 = weights_path(m, "expand", 24)
    w = style_w(m); wt.append({"code": c, **w.round(4).to_dict(), "주식안국내": w["kr_eq"] / w[RISKY].sum()})
    t = m["fund"]
    if len(we) < 36: continue
    var = {"TDF(실제)": t, "직접·구성(확장창)·월": diy(c, m, we), "직접·구성(확장창 24)·월": diy(c, m, we24),
           "직접·구성(사후)·월": diy(c, m, wf), "직접·구성(확장창)·연": diy(c, m, we, 12), "방치·구성(확장창)": diy(c, m, we, None)}
    for k in P.REENTRY_GRID: var[f"직접·구성(확장창)·월+시장약세장 피신{k}"] = diy(c, m, we, 1, k)
    common = var["직접·구성(확장창)·월"].index
    if len(common) < 36: continue                         # 비교 구간 36개월 미만 제외(⬜ 같은 기준)
    for name, x in var.items():
        x = x.loc[x.index.intersection(common)]
        rows.append({"code": c, "운용사": ts.MGR[c], "빈티지": gp.CODE2VINTAGE[c], "개월": len(x), "전략": name, **stats(x)})
    tt = t.loc[common]; d = var["직접·구성(확장창)·월"]; DS[c] = (tt, d, m["cash"].loc[common])
    bd = paired_bootstrap_diff(tt, d, lambda x: x.mean() * 12, P.NP, P.pw_block(tt - d), None, SEED)
    dl.append({"code": c, "운용사": ts.MGR[c], "빈티지": gp.CODE2VINTAGE[c], "개월": len(common), "평균 보수(KOFIA)": avg_fee(c, common),
               "TDF−확장창(보수+재량+모형오차)": (tt - d).mean() * 12, "95%CI 하": np.quantile(bd, .025), "95%CI 상": np.quantile(bd, .975),
               "TDF−사후(상한 참고)": (tt - var["직접·구성(사후)·월"].loc[common]).mean() * 12,
               "확장창 ~2024": (tt - d).loc[:P.PRE].mean() * 12, "확장창 2025~": (tt - d).loc["2025-01":].mean() * 12})
res, dl, wt = pd.DataFrame(rows), pd.DataFrame(dl), pd.DataFrame(wt)
KR_DATA = round(float(wt["주식안국내"].median()), 3)
print("펀드 수", len(dl), "| 주식 안 국내 비중(전기간 스타일) 중앙값:", KR_DATA)

# 단순 2-ETF형: 국내 {재추정 중앙값, 35%}
for c in dl.code:
    m = monthly_rets(c); common = diy(c, m, weights_path(m, "expand")).index
    for kr in (KR_DATA, P.EQ_KR_SHARE):
        wp = {t: (pd.Series({"kr_eq": kr, "gl_eq_h": 1 - kr}), pd.Series({"kr_bd": 1.0})) for t in common}
        x = diy(c, m, wp)
        rows.append({"code": c, "운용사": ts.MGR[c], "빈티지": gp.CODE2VINTAGE[c], "개월": len(x), "전략": f"직접·단순2ETF(국내 {kr:.1%})·월", **stats(x)})
res = pd.DataFrame(rows)
assert not res[["연수익", "연변동성", "MDD"]].isna().any().any(), "결과에 NaN"   # 3차 감사 🔴1
for n, x in [("T7_funds", res), ("T7_diff", dl), ("T7_style_weights", wt)]: x.to_csv(OUT / f"{n}.csv", index=False, encoding="utf-8-sig")
display(res.pivot_table(index="전략", values=["연수익", "연변동성", "MDD"], aggfunc="median").round(4))
two = res[res["전략"].str.contains("단순2ETF")].merge(res[res["전략"] == "TDF(실제)"][["code", "연수익"]], on="code", suffixes=("", "_TDF"))
(two.assign(**{"TDF−2ETF 연수익": two["연수익_TDF"] - two["연수익"]}).groupby("전략")["TDF−2ETF 연수익"].median().round(4))

# %% [markdown]
# ## TDF − 직접형 (연환산, 펀드 중앙값). 보수는 각 펀드 KOFIA 간이공시(기간별) 평균

# %%
display(dl.drop(columns=["code", "운용사", "빈티지"]).median().round(4))
print("확장창 기준 95%CI가 0 아래인 펀드:", int((dl["95%CI 상"] < 0).sum()), "/", len(dl), "(펀드들은 같은 시장 구간을 공유 → 독립 증거 아님)")
print("차이 − 보수(=재량+모형오차) 중앙값:", round(float((dl["TDF−확장창(보수+재량+모형오차)"] + dl["평균 보수(KOFIA)"]).median()), 4))
dl.groupby("운용사")[["평균 보수(KOFIA)", "TDF−확장창(보수+재량+모형오차)", "TDF−사후(상한 참고)"]].median().round(4)

# %% [markdown]
# ## 정식 검정 (한계 보완: '부트스트랩 구간 = p값 아님' → 검정 통계량 병기)
# - 펀드별 평균차: Newey–West HAC t (`P.hac_t`, 대역폭 floor(4(T/100)^(2/9))). 다중비교: 펀드 수만큼 Holm 보정.
# - 펀드별 Sharpe차: Ledoit & Wolf(2008) HAC 검정(`perfstats.sharpe_diff_test`, 월 초과수익 = 수익 − CD91 월금리, 반복 999 = 모듈 기본값).
#   circular block: 그 펀드 차이의 Politis–White 추정이 1~25로 흩어져(T=38~88) → 고정 블록 2·4·6 민감도를 같이 보고(4차 감사).
# - 펀드 묶음(추정 대상을 셋으로 명시): (a) 달별 횡단면 평균(펀드 수가 달마다 5~31개로 다름) HAC t (b) 모든 펀드가 있는 균형 구간만 HAC t
#   (c) 펀드 동일가중(가중치 1/T_i) 평균 — 같은 달 공유를 반영해 달 군집 표준오차. (b)·(a)의 마지막 달 2026-09는 9/23까지의 부분월.

# %%
import statsmodels.api as sm
ft = []
for c, (tt, d, cs) in DS.items():
    h = P.hac_t(tt - d); pw = max(1, int(round(P.pw_block(tt - d))))
    row = {"code": c, "운용사": ts.MGR[c], "빈티지": gp.CODE2VINTAGE[c], "개월": h["T"], "평균차(연)": h["mean"] * 12, "HAC t": h["t"], "HAC p": h["p"], "PW 블록": pw}
    for lab, bl in (("PW", pw), ("2", 2), ("4", 4), ("6", 6)):
        lw = ps.sharpe_diff_test(tt - cs, d - cs, block_size=bl, n_boot=999, seed=SEED, annualize=False)
        row["Sharpe(TDF,월)"], row["Sharpe(직접,월)"] = lw["sharpe1"], lw["sharpe2"]; row[f"LW p(블록 {lab})"] = lw["pvalue"]
    ft.append(row)
ft = pd.DataFrame(ft); ft["HAC p Holm"] = P.holm(ft["HAC p"].to_numpy())
for col in [c for c in ft if c.startswith("LW p(")]: ft[col + " Holm"] = P.holm(ft[col].to_numpy())
ft.to_csv(OUT / "T7_tests.csv", index=False, encoding="utf-8-sig")
panel = pd.concat({c: tt - d for c, (tt, d, _) in DS.items()}, axis=1)
pa = P.hac_t(panel.mean(axis=1)); bal = panel.dropna(); pb = P.hac_t(bal.mean(axis=1))
long = panel.stack().rename("x").reset_index(); long.columns = ["월", "code", "x"]
wts = 1 / long.groupby("code")["x"].transform("size")
fc = sm.WLS(long["x"].to_numpy(), np.ones(len(long)), weights=wts.to_numpy()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(long["월"])[0]})
pool = pd.DataFrame([{"추정대상": "(a) 달별 횡단면 평균(불균형)", "평균차(연)": pa["mean"] * 12, "t": pa["t"], "p": pa["p"], "개월": pa["T"], "비고": f"HAC lags {pa['lags']}"},
                     {"추정대상": "(b) 균형 구간(모든 펀드 존재)", "평균차(연)": pb["mean"] * 12, "t": pb["t"], "p": pb["p"], "개월": pb["T"], "비고": f"{bal.index[0].date()}~{bal.index[-1].date()}, HAC lags {pb['lags']}"},
                     {"추정대상": "(c) 펀드 동일가중(1/T_i), 달 군집 SE", "평균차(연)": fc.params[0] * 12, "t": fc.tvalues[0], "p": fc.pvalues[0], "개월": panel.shape[0], "비고": f"펀드 {panel.shape[1]}개"}])
pool.to_csv(OUT / "T7_pooled_test.csv", index=False, encoding="utf-8-sig"); display(pool.round(4))
print("Holm 후 HAC p<0.05 펀드:", int((ft["HAC p Holm"] < .05).sum()), "/", len(ft), "|", {c: int((ft[c] < .05).sum()) for c in ft if c.startswith("LW p(") and c.endswith("Holm")})
ft.round(4)

# %% [markdown]
# ## 외부 대조: 미국 TDF (Shoven & Walton 복제, 이 저장소 `notebooks/idea_tdf_sw_replication.ipynb`)
# - 같은 질문(TDF − 직접 따라하기)을 미국 자료로 한 기존 복제(펀드 158개): 저비용 TDF −1.78bp/월, 고비용 −3.63bp/월, 보수(ER)에 대한 기울기 −0.036(95% CI가 원논문 값을 배제 → **부분 재현**).
#   원논문(Shoven & Walton, 표본 395): 저비용 −0.7bp/월, 고비용 −3.9bp/월, 기울기 −0.079.
# - 미국 수치는 **전기간 스타일 회귀 상수(사후)** → 같은 성격의 한국 비교값은 위 표의 'TDF−사후(상한 참고)' 열이지 확장창 열이 아님.

# %%
print("한국 'TDF−사후' 펀드 중앙값(연):", round(float(dl["TDF−사후(상한 참고)"].median()), 4), "→ 월", round(float(dl["TDF−사후(상한 참고)"].median()) / 12 * 1e4, 1), "bp | 미국 복제 고비용 −3.63bp/월")

# %% [markdown]
# ## 실제 보유내역으로 만든 직접형 (2025~26 차이가 스타일 모형 오차인지 점검)
# 운용사 분기 자산운용보고서(삼성·신한·한국투자·KB 25펀드, 2022~2026; 미래에셋은 최신 1건뿐이라 제외)의 보유종목 → 자산군 비중(`P.tdf_holdings_weights`).
# 보고서 기준일 다음 달부터 다음 보고서 전까지 그 비중을 매달 유지(월 리밸런싱)하고, 자산 수익률은 스타일 직접형과 같은 ETF·지수(펀드 기준가일 시차 맞춤) 사용.
# 환헤지: 보고서의 '기준일 현재 환헤지 비율'(총 외화자산 대비, KB 61~99%·한국투자 71~99%·삼성 77~104%) h로 외화자산을 h·헤지 + (1−h)·비헤지; 이름에 (H)면 항상 헤지,
# 원화 상장 해외 ETF(KODEX·TIGER 미국… (H) 없음)는 외화자산이 아니라 항상 비헤지(10차 감사 🟠). 신한은 비율을 숫자로 싣지 않아 이 비교에서 빠짐.
# 금(한국투자 2025-12~ 10~17%, 10차 감사 🟠)은 금 USD 가격 × 환율(헤지분은 USD 수익 + 헤지 carry)로 대용. 리츠·글로벌 부동산·혼합형 모펀드는 대응 수익률이 없어 제외 후 재정규화(제외 비중 표시).
# **실리지 않은 비중(평균 약 27%) 처리 — 결과가 가장 민감한 가정(10·11차 감사 🔴)**: ① 비례 확대(실린 종목 구성 = 전체) ⑤ 나머지로 국내주식을 그 펀드의 스타일(사후) 국내주식 비중까지 채우고 남는 건 비례 확대(사후정보 ⚠, 국내주식 누락 보정용)
# ② 나머지 = 스타일 직접형 수익률(비교 대상을 섞어 스타일 결과 쪽으로 당겨짐 ⚠) ③ 나머지 = 국내주식 ④ 나머지 = 국고채(③④는 현실성 없는 경계값).
# **⑥(주 판본, 사후정보 없음)**: 보고서 '통화별 구분' 표의 원화 비중(`fetch.mgmt_report_tdf.extract_krw`, KB·삼성·한국투자 349건)에서 실린 원화 자산(국내주식·국내채권·원화 현금·원화 상장 ETF)을 빼 '안 실린 원화 몫'을 구하고,
# 이를 국내주식:국고채 = 그 펀드 공시 글라이드 주식비중으로 나눔(⑥a 전부 국내주식·⑥b 전부 국고채는 경계). 안 실린 외화 몫은 실린 외화 자산 구성 비례.
# 12차 감사 반영: 원화 중 '증권'(주식·채권·어음·집합투자증권 열)만 국내 위험자산 몫으로, 원화 예금·기타는 현금으로; 원화 상장 (H) ETF는 실린 원화 증권에 포함. ⑥에도 공시시차·전부 비헤지/헤지 판본.
# ⚠ 직접형은 지수·ETF 대용이라 TDF가 담은 하위 액티브 펀드의 보수·초과/부진이 'TDF − 직접형'에 들어감 → 차이를 전부 TDF(래퍼) 운용 손실로 볼 수 없음.
# 보수 분해: KOFIA 간이투자설명서 C 클래스 표의 총보수(래퍼: 운용+판매+수탁+사무)와 합성 총보수·비용 − 총보수(피투자펀드 보수·기타비용; `fetch.tdf_fee_extract.run(both=True)`).
# 'TDF − ⑥ + 합성보수' = 두 보수를 다 돌려놓고도 남는 차이(하위 펀드의 지수 대비 성과, 헤지 비용·시점, 모형 오차).
# 보고서 상위종목은 대형 해외 펀드 위주라 ①은 국내주식을 빠뜨리는 쪽으로 치우칠 수 있음(아래 '국내주식 비중' 비교). 공시 시차 판본(기준일 3개월째부터 적용)·실린 비중 80% 이상 보고서만 쓴 판본 병기.
# 개별 액티브 펀드의 초과·부진은 '같은 자산군 지수와의 차이'로 남음. 모든 판본을 같은 달로 맞춰 비교.

# %%
HW = P.tdf_holdings_weights()
HR = pd.read_csv(paths.FUND_TDF / "mgmt_reports" / "hedge_ratio_20261011fix.csv", dtype={"code": str, "period_end": str})
HR["period_end"] = pd.to_datetime(HR["period_end"]); HR = HR.sort_values(["code", "period_end"])
HR["h"] = (HR.groupby("code")["hedge_pct"].ffill() / 100).clip(0, 1)          # 삼성 2023-04-20 5건은 파서 결측이었고 원문 값(90.4~90.6)을 정정본에 넣음(근거 stage4_fixlist\t7_fix) → 직전 값 채움 대상 없음(신한은 비율 미공시라 빈칸 그대로), 100% 초과(삼성 2025-04 101~104%)는 1로
GOLD = P.gold_monthly_usd()
KRW = pd.read_csv(paths.FUND_TDF / "mgmt_reports" / "krw_share_20261011fix.csv", dtype={"code": str, "period_end": str})
KRW = KRW.assign(period_end=pd.to_datetime(KRW["period_end"])).set_index(["code", "period_end"])
KRWS, KRW = KRW["krw_sec_pct"].div(100).to_dict(), KRW["krw_pct"].div(100).to_dict()   # 보고서 통화별 표: 원화 증권(주식·채권·어음·집합투자증권) 비중, 원화 전체 비중(전체 자산 대비)
BASE = {"KR_EQ": "kr_eq", "KR_BD": "kr_bd", "US_EQ": "gl_eq", "DM_EXUS_EQ": "dm_eq", "EM_EQ": "em_eq", "GLOBAL_BD": "gl_bd", "GOLD": "gold"}
def hold_diy(c, hedge="report", rem="prorata", lag=1, min_cov=0.0):
    """hedge: 'report'(보고서 h)·'none'·'full'. rem: 실리지 않은 비중 = 'prorata'(비례 확대)·'style'(스타일 직접형)·'kr_eq'·'kr_bd'·'kr_style'(국내주식을 스타일 비중까지)
    ·'krw'/'krw_eq'/'krw_bd'(보고서 통화별 표 원화 비중 − 실린 원화 자산 = 안 실린 원화 몫 → 국내주식:국고채를 공시 글라이드 주식비중으로/전부 국내주식/전부 국고채, 안 실린 외화 몫은 실린 외화 자산 비례).
    lag: 기준일 몇 달 뒤 달부터 적용(1 = 다음 달). min_cov: 실린 비중(%)이 이보다 작은 보고서는 쓰지 않음. -> (월 수익률, 국내주식 비중)."""
    px = PX[c].copy(); fxr = px["gl_eq_uh"] / px["gl_eq_h0"]
    px["gl_bd_uh"] = px["gl_bd_h0"] * fxr; px["fx"] = fxr
    r = ts.monthly(px); r.index = r.index.to_timestamp(how="end").normalize(); r["kr_bd"] -= P.BD_TER / 12
    g = GOLD.reindex(r.index); r["gold_uh"] = (1 + g) * (1 + r["fx"]) - 1; r["gold_h"] = g + (r["gl_eq_h"] - r["gl_eq_h0"])
    w = HW[(HW.code == c) & (HW.covered >= min_cov)]; hr = HR[HR.code == c].set_index("period_end")["h"]
    if w.empty: return None, None
    sty = DS[c][1]
    out, kr = {}, {}
    pes = sorted(w.period_end.unique())
    for t in r.index:
        start = (t.to_period("M") - (lag - 1)).to_timestamp()                                  # lag=1: 그 달 1일 전에 기준일이 지난 보고서만(lag=3: 두 달 전 1일)
        prev = [pe for pe in pes if pe < start]
        if not prev or (t - prev[-1]).days > 170 + 30 * lag: continue                          # 보고서 공백이 길면 쓰지 않음
        cur = w[w.period_end == prev[-1]]
        h = {"none": 0.0, "full": 1.0}.get(hedge, hr.get(prev[-1], np.nan))
        if pd.isna(h): continue
        rr = r.loc[t]; tot = 0.0; tot_f = 0.0; w_f = 0.0; w_k = 0.0; w_kc = 0.0
        if rr[["kr_eq", "kr_bd", "cash", "fx", "gl_eq_h", "gl_eq_uh"]].isna().any(): continue
        for row in cur.itertuples():
            if row.cls == "CASH":
                ret = rr["cash"] if row.hedge in ("NA", "KRW") else h * rr["cash"] + (1 - h) * rr["fx"]
            elif row.cls in ("KR_EQ", "KR_BD"):
                ret = rr[BASE[row.cls]]
            elif row.hedge == "H":
                ret = rr[BASE[row.cls] + "_h"]
            elif row.hedge == "KRW":
                ret = rr[BASE[row.cls] + "_uh"]
            else:
                ret = h * rr[BASE[row.cls] + "_h"] + (1 - h) * rr[BASE[row.cls] + "_uh"]
            tot += row.w * ret
            if row.cls == "CASH" and row.hedge == "NA": w_kc += row.w                             # 원화 현금
            elif row.cls in ("KR_EQ", "KR_BD") or row.krw_listed: w_k += row.w                     # 원화 증권(원화 상장 (H) ETF 포함, 12차 감사 🟠)
            if not (row.cls in ("KR_EQ", "KR_BD") or row.hedge in ("NA", "KRW")): tot_f += row.w * ret; w_f += row.w
        if pd.isna(tot): continue
        u = max(0.0, 1 - cur["covered"].iloc[0] / 100); krw = cur.loc[cur.cls == "KR_EQ", "w"].sum()
        if rem != "prorata":
            if rem in ("krw", "krw_eq", "krw_bd"):
                ks, kp = KRWS.get((c, prev[-1]), np.nan), KRW.get((c, prev[-1]), np.nan)
                if pd.isna(ks) or pd.isna(kp) or w_f <= 0: continue
                ce = (cur["covered"].iloc[0] - cur["excluded"].iloc[0]) / 100
                ku = min(u, max(0.0, ks - w_k * ce))                                              # 안 실린 원화 증권 몫 → 국내주식·국고채
                kc = min(u - ku, max(0.0, (kp - ks) - w_kc * ce))                                 # 안 실린 원화 예금·기타 몫 → 현금(12차 감사 🔴)
                phi = {"krw_eq": 1.0, "krw_bd": 0.0}.get(rem, float(ts.glide_fn(c, gl)(ts.yrs_rel(pd.DatetimeIndex([t]), c))[0]))
                tot = (1 - u) * tot + ku * (phi * rr["kr_eq"] + (1 - phi) * rr["kr_bd"]) + kc * rr["cash"] + (u - ku - kc) * tot_f / w_f
                krw = (1 - u) * krw + ku * phi
            elif rem == "kr_style":                                                               # 나머지로 국내주식을 스타일(사후) 비중까지 채우고, 남는 나머지는 비례 확대
                gk = min(u, max(0.0, KR_STY[c] - (1 - u) * krw))
                tot = (1 - gk) * tot + gk * rr["kr_eq"]; krw = (1 - gk) * krw + gk
            else:
                if rem == "style":
                    if t not in sty.index: continue
                    rv = sty.at[t]
                else:
                    rv = rr[rem]
                tot = (1 - u) * tot + u * rv; krw = (1 - u) * krw + (u if rem == "kr_eq" else 0.0)
        out[t] = tot; kr[t] = krw
    return pd.Series(out, dtype=float), pd.Series(kr, dtype=float)

FU = pd.read_csv(paths.FUND_TDF / "tdf_fee_underlying_c_class_20261009.csv", parse_dates=["start", "end"])
FU = FU[FU.source.str.startswith("KOFIA")]                                                      # 현행 간이투자설명서 C 클래스: 총보수(래퍼)·합성 − 총보수(피투자펀드 보수·기타비용)
def fee_parts(c, idx):
    f = FU[FU.standardCd == c]
    pick = lambda col: np.mean([f[(f.start <= t) & (f.end >= t)][col].iloc[0] for t in idx]) / 100
    return pick("total_fee_pct"), pick("underlying_pct")
VARS = {"①비례확대": dict(), "⑥원화몫=보고서(주식비중=글라이드)": dict(rem="krw"), "⑥a 원화몫=국내주식": dict(rem="krw_eq"), "⑥b 원화몫=국고채": dict(rem="krw_bd"),
        "⑥+공시시차(3개월째)": dict(rem="krw", lag=3), "⑥+전부비헤지": dict(rem="krw", hedge="none"), "⑥+전부헤지": dict(rem="krw", hedge="full"),
        "⑤국내주식=스타일비중": dict(rem="kr_style"), "②나머지=스타일": dict(rem="style"), "③나머지=국내주식": dict(rem="kr_eq"), "④나머지=국고채": dict(rem="kr_bd"),
        "①+공시시차(3개월째)": dict(lag=3), "①+실린80%↑만": dict(min_cov=80.0), "①+전부비헤지": dict(hedge="none"), "①+전부헤지": dict(hedge="full")}
WT = wt.set_index("code"); KR_STY = WT["kr_eq"].to_dict()   # ⑤: 전기간(사후) 스타일 국내주식 비중 — 사후정보 ⚠(보고서 상위종목에 국내주식이 0~5%만 실려, 11차 감사 🔴)
hc, MD = [], {}                                                                                   # MD[(판본, code)] = 같은 달 월별 차이(검정용)
for c, (tt, d, _) in DS.items():
    v = {k: hold_diy(c, **kw) for k, kw in VARS.items()}
    if v["①비례확대"][0] is None or len(v["①비례확대"][0]) == 0: continue
    for per, msk in [("전체", slice(None)), ("~2024", slice(None, P.PRE)), ("2025~", slice("2025-01", None))]:
        j = tt.index.intersection(d.index)
        for k in ("①비례확대", "⑥원화몫=보고서(주식비중=글라이드)", "⑥a 원화몫=국내주식", "⑥b 원화몫=국고채", "⑤국내주식=스타일비중", "②나머지=스타일", "③나머지=국내주식", "④나머지=국고채", "①+전부비헤지", "①+전부헤지", "⑥+전부비헤지", "⑥+전부헤지"):
            j = j.intersection(v[k][0].index)                                                   # 주 판본들은 같은 달로
        jj = pd.Series(j, index=j).loc[msk].index
        if len(jj) < 6: continue
        if per == "전체":
            MD[("스타일", c)] = (tt - d).loc[jj]
            for k in ("①비례확대", "⑥원화몫=보고서(주식비중=글라이드)", "⑥a 원화몫=국내주식", "⑥b 원화몫=국고채", "⑥+전부비헤지", "⑥+전부헤지"): MD[(k, c)] = (tt - v[k][0]).loc[jj]
            MD[("⑥ + 합성보수(보수 외)", c)] = MD[("⑥원화몫=보고서(주식비중=글라이드)", c)] + avg_fee(c, jj) / 12
        rec = {"code": c, "운용사": ts.MGR[c], "빈티지": gp.CODE2VINTAGE[c], "기간": per, "개월": len(jj),
               "TDF−스타일직접형(연)": (tt - d).loc[jj].mean() * 12, "평균 보수(KOFIA)": avg_fee(c, jj),
               "래퍼 총보수": fee_parts(c, jj)[0], "하위펀드 보수(합성−총보수)": fee_parts(c, jj)[1],
               "국내주식 비중: 스타일(사후)": WT.at[c, "kr_eq"], "국내주식 비중: ①": v["①비례확대"][1].loc[jj].mean(), "국내주식 비중: ③": v["③나머지=국내주식"][1].loc[jj].mean(), "국내주식 비중: ⑤": v["⑤국내주식=스타일비중"][1].loc[jj].mean(), "국내주식 비중: ⑥": v["⑥원화몫=보고서(주식비중=글라이드)"][1].loc[jj].mean(), "국내주식 비중: ⑥a": v["⑥a 원화몫=국내주식"][1].loc[jj].mean(),
               "실린 비중 평균(%)": np.nan}
        for k in VARS:
            x, _ = v[k]
            if x is None: x = pd.Series(dtype=float)
            jk = jj.intersection(x.index) if "+공시" in k or k.startswith("①+실린") else jj
            rec[f"TDF−보유내역 {k}(연)"] = (tt - x).loc[jk].mean() * 12 if len(jk) >= 6 else np.nan
            if "+공시" in k or k.startswith("①+실린"): rec[f"{k} 개월"] = len(jk)
        hc.append(rec)
hc = pd.DataFrame(hc)
cv = HW.drop_duplicates(["code", "period_end"]).groupby("code")["covered"].mean()
hc["실린 비중 평균(%)"] = hc["code"].map(cv)
hc["TDF−⑥ + 합성보수(보수 외 차이)(연)"] = hc["TDF−보유내역 ⑥원화몫=보고서(주식비중=글라이드)(연)"] + hc["평균 보수(KOFIA)"]   # 직접형 ETF 보수(약 0.1~0.2%)는 직접형 쪽에서 이미 빠져 있어 보수 외 차이를 약간 크게 잡음
hc.to_csv(OUT / "T7_holdings_check.csv", index=False, encoding="utf-8-sig")
COLS = ["TDF−스타일직접형(연)"] + [f"TDF−보유내역 {k}(연)" for k in VARS] + ["TDF−⑥ + 합성보수(보수 외 차이)(연)"]
hs = []
for per in ("전체", "~2024", "2025~"):
    g = hc[hc["기간"] == per]
    for col_ in COLS:
        gg = g.dropna(subset=[col_])
        hs.append({"기간": per, "비교": col_, "펀드": len(gg), "운용사": gg["운용사"].nunique(), "펀드 중앙값": gg[col_].median(), "펀드 평균": gg[col_].mean(),
                   "운용사 동일가중": gg.groupby("운용사")[col_].mean().mean(), "보수 중앙값": gg["평균 보수(KOFIA)"].median(),
                   "래퍼 총보수 운용사 동일가중": gg.groupby("운용사")["래퍼 총보수"].mean().mean(), "하위펀드 보수 운용사 동일가중": gg.groupby("운용사")["하위펀드 보수(합성−총보수)"].mean().mean()})
hs = pd.DataFrame(hs); hs.to_csv(OUT / "T7_holdings_summary.csv", index=False, encoding="utf-8-sig"); display(hs.round(4))
hm = hc.groupby(["기간", "운용사"])[COLS + ["평균 보수(KOFIA)", "래퍼 총보수", "하위펀드 보수(합성−총보수)", "국내주식 비중: 스타일(사후)", "국내주식 비중: ①", "국내주식 비중: ③", "국내주식 비중: ⑤", "국내주식 비중: ⑥", "국내주식 비중: ⑥a", "실린 비중 평균(%)"]].mean()
hm.to_csv(OUT / "T7_holdings_by_manager.csv", encoding="utf-8-sig"); display(hm.round(4))
# 운용사 동일가중 달별 차이의 HAC t(달마다 운용사 평균 → 평균; 3개사라 운용사 군집 불가)
ht = []
for k in ("스타일", "①비례확대", "⑥원화몫=보고서(주식비중=글라이드)", "⑥a 원화몫=국내주식", "⑥b 원화몫=국고채", "⑥+전부비헤지", "⑥+전부헤지", "⑥ + 합성보수(보수 외)"):
    pk = pd.concat({c: x for (kk, c), x in MD.items() if kk == k}, axis=1)
    mg = pk.T.groupby(pk.columns.map(ts.MGR).to_numpy()).mean().T.mean(axis=1)
    for per, msk in [("전체", slice(None)), ("~2024", slice(None, P.PRE)), ("2025~", slice("2025-01", None))]:
        q = P.hac_t(mg.loc[msk]); ht.append({"판본": k, "기간": per, "평균차(연)": q["mean"] * 12, "t": q["t"], "p": q["p"], "개월": q["T"]})
ht = pd.DataFrame(ht); ht.to_csv(OUT / "T7_holdings_hac.csv", index=False, encoding="utf-8-sig"); display(ht.round(4))
excl = HW.drop_duplicates(["code", "period_end"]).assign(운용사=lambda q: q.code.map(ts.MGR)).groupby("운용사")[["covered", "excluded"]].mean()
display(excl.round(1))   # 실린 비중·제외(리츠·혼합 등) 비중 평균(%)

# %% [markdown]
# ## 확장 표본: 추가 운용사 TDF (한계 보완 — '운용사 5개')
# 공시 글라이드가 있는 추가 운용사 펀드의 KOFIA 기준가를 설정일부터 다시 받아 같은 정제 규칙 v3로 정제(`nav_tdfext_clean_v3`).
# 주 규칙은 위와 같음(첫 추정 36·비교 36개월), 민감도로 첫 추정 24·비교 24개월. 기준가는 정제 조각 경계·14일 넘는 공백에서 끊고 가장 긴 연속 구간만(6차 감사 🔴).
# 운용사 동일가중 (d)와, 기존 5개사를 같은 달로 맞춘 (a)를 병기해 운용사 효과와 기간 효과를 가름. 사후(전기간) 구성 비교 병기. 보수: KOFIA 투자설명서·간이투자설명서에서 펀드 코드의 종류별 합성 총보수·비용(종류형 운용펀드 코드는 합성 − 총보수 = 운용 기준가에 빠지는 몫, 클래스 총보수는 안 빠짐)을 받아 '차이 − 보수' 분해(`fetch.tdfext_fee_extract`, 2026-10-09). 운용펀드 코드(61개)는 투자자가 실제로 클래스 총보수(연 0.3~1.0%)를 더 냄 → 이 펀드들의 차이는 투자자 기준보다 작게 잡힘 ⚠. 코드 종류별로 따로 봄.

# %%
UX = P.tdf_ext_universe(); NX = P.tdf_ext_nav().loc[:nav.index.max()]; VX = UX.drop_duplicates("code").set_index("code")   # 자산 자료 끝(기존 표본 끝)까지
NAMES = pd.read_csv(paths.FUND_TDF / "tdfext_fund_names_kofia_20261008.csv").set_index("fund_code")["fund_name"].to_dict()
_fee = pd.read_csv(paths.FUND_TDF / "tdfext_fee_kofia_20261009.csv"); UXF = _fee.groupby("standardCd")["fee_pct"].apply(lambda v: v.isna().all()).to_dict()   # True = 종류형 운용펀드 코드
PXX, _, _ = ts.panel(NX, "full")
def glide_ext(c):
    g = UX[UX.code == c].groupby("years_rel_target").risky_pct.mean().sort_index(); tgt = pd.Timestamp(f"{int(VX.at[c, 'vintage'])}-01-01")
    return lambda ix: np.interp((pd.DatetimeIndex(ix) - tgt).days / 365.25, g.index.values.astype(float), g.values / 100, left=g.values[0] / 100, right=g.values[-1] / 100)
xr, XS = [], {}
def risky_style(m, min_m):
    """스타일 회귀가 본 위험자산 합계(매년 1월 직전 자료로만) — 공시 글라이드 대신 쓰는 민감도(8차 점검: 공시 글라이드 지정 오류)."""
    out, cur = {}, None
    for t in m.index:
        if t.month == 1 or cur is None:
            past = m.loc[: t - pd.offsets.MonthEnd(1)]
            cur = float(style_w(past)[RISKY].sum()) if len(past) >= min_m else None
        if cur is not None: out[t] = cur
    return lambda ix: np.array([out[t] for t in pd.DatetimeIndex(ix)])
XS_style = {}
for (minm, c) in [(mm, cc) for mm in (36, 24) for cc in NX.columns]:
    m = ts.monthly(PXX[c]).loc[:, ["fund"] + ts.A10]; m.index = m.index.to_timestamp(how="end").normalize(); m["kr_bd"] -= P.BD_TER / 12; m = m.dropna()
    we = weights_path(m, "expand", minm); wf = weights_path(m, "full")
    if len(we) < minm: continue
    d_e = diy(c, m, we, efn=glide_ext(c)); d_f = diy(c, m, wf, efn=glide_ext(c)); t_ = m["fund"].loc[d_e.index]
    XS[(minm, c)] = t_ - d_e; h = P.hac_t(t_ - d_e)
    d_s = diy(c, m, we, efn=risky_style(m, minm)); XS_style[(minm, c)] = (m["fund"] - d_s).loc[d_s.index]
    xr.append({"규칙": f"첫추정·비교 {minm}개월", "code": c, "운용사": VX.at[c, "manager"], "빈티지": int(VX.at[c, "vintage"]), "개월": len(d_e), "TDF−확장창(연)": (t_ - d_e).mean() * 12,
               "TDF−사후(연)": (m["fund"] - d_f).loc[d_e.index].mean() * 12, "HAC t": h["t"], "HAC p": h["p"],
               "기준가 내 보수(연, KOFIA)": P.tdf_ext_fee(c, d_e.index), "연금클래스 추가보수(연)": P.tdf_ext_fee(c, d_e.index, "investor_extra"),
               "코드 종류": "운용펀드(클래스 보수 미차감)" if UXF.get(c) else "클래스·단일",
               "~2024 차이(연)": (t_ - d_e).loc[:P.PRE].mean() * 12, "2025~ 차이(연)": (t_ - d_e).loc["2025-01":].mean() * 12,
               "스타일 위험비중 직접형 대비(연)": XS_style[(minm, c)].mean() * 12})
xr = pd.DataFrame(xr); xr["차이 − 보수(연)"] = xr["TDF−확장창(연)"] + xr["기준가 내 보수(연, KOFIA)"]; xr["투자자(연금 클래스) 기준 차이(연)"] = xr["TDF−확장창(연)"] - xr["연금클래스 추가보수(연)"]; xr["HAC p Holm"] = xr.groupby("규칙")["HAC p"].transform(lambda q: pd.Series(P.holm(q.to_numpy()), index=q.index))
xr.to_csv(OUT / "T7_ext_tests.csv", index=False, encoding="utf-8-sig")
pool_x = []
for minm in (36, 24):
    pnx = pd.concat({c: v for (mm, c), v in XS.items() if mm == minm}, axis=1); pa_x = P.hac_t(pnx.mean(axis=1))
    lx = pnx.stack().rename("x").reset_index(); lx.columns = ["월", "code", "x"]
    fcx = sm.WLS(lx["x"].to_numpy(), np.ones(len(lx)), weights=(1 / lx.groupby("code")["x"].transform("size")).to_numpy()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(lx["월"])[0]})
    g_ = xr[xr["규칙"] == f"첫추정·비교 {minm}개월"]
    pool_x += [{"규칙": f"첫추정·비교 {minm}개월", "펀드": len(g_), "운용사": g_["운용사"].nunique(), "Holm 후 p<0.05 펀드": int((g_["HAC p Holm"] < .05).sum()),
                "추정대상": "(a) 달별 평균", "평균차(연)": pa_x["mean"] * 12, "t": pa_x["t"], "p": pa_x["p"], "개월": pa_x["T"]},
               {"규칙": f"첫추정·비교 {minm}개월", "펀드": len(g_), "운용사": g_["운용사"].nunique(), "Holm 후 p<0.05 펀드": int((g_["HAC p Holm"] < .05).sum()),
                "추정대상": "(c) 펀드 동일가중, 달 군집", "평균차(연)": fcx.params[0] * 12, "t": fcx.tvalues[0], "p": fcx.pvalues[0], "개월": pnx.shape[0]}]
    # (d) 운용사 동일가중(6차 감사 🟠: 운용사 수가 적어 운용사 군집 불가 → 달마다 운용사 평균의 평균, HAC)
    mg = pnx.T.groupby(VX.loc[pnx.columns, "manager"].to_numpy()).mean().T.mean(axis=1); pm = P.hac_t(mg)
    pool_x.append({"규칙": f"첫추정·비교 {minm}개월", "펀드": len(g_), "운용사": g_["운용사"].nunique(), "Holm 후 p<0.05 펀드": int((g_["HAC p Holm"] < .05).sum()),
                   "추정대상": "(d) 운용사 동일가중, 달별", "평균차(연)": pm["mean"] * 12, "t": pm["t"], "p": pm["p"], "개월": pm["T"]})
    # 기존 5개사를 같은 달로 맞춘 (a): 운용사 차이와 기간 차이를 가르기(6차 감사: 기존 88개월 vs 추가 다른 기간)
    po = pd.concat({c: (v[0] - v[1]) for c, v in DS.items()}, axis=1).reindex(pnx.index).mean(axis=1).dropna(); po_ = P.hac_t(po)
    pool_x.append({"규칙": f"첫추정·비교 {minm}개월", "펀드": len(DS), "운용사": 5, "Holm 후 p<0.05 펀드": np.nan,
                   "추정대상": "(a) 기존 5개사, 추가 표본과 같은 달", "평균차(연)": po_["mean"] * 12, "t": po_["t"], "p": po_["p"], "개월": po_["T"]})
pool_x = pd.DataFrame(pool_x); pool_x.to_csv(OUT / "T7_ext_pooled.csv", index=False, encoding="utf-8-sig"); display(pool_x.round(4))
display(xr.groupby(["규칙", "운용사"])[["TDF−확장창(연)", "TDF−사후(연)", "기준가 내 보수(연, KOFIA)", "차이 − 보수(연)"]].median().round(4))
display(xr.groupby(["규칙", "코드 종류"])[["TDF−확장창(연)", "기준가 내 보수(연, KOFIA)", "차이 − 보수(연)"]].agg(["median", "size"]).round(4))
print("차이 − 보수, 펀드 중앙값:", xr.groupby("규칙")["차이 − 보수(연)"].median().round(4).to_dict(), "| 코드 종류:", xr.groupby(["규칙", "코드 종류"]).size().to_dict())
for minm in (36, 24):   # 묶음 (a)에 보수를 더한 잔차(재량+모형오차): 달마다 펀드 평균 보수/12를 더함
    pnx = pd.concat({c: v + P.tdf_ext_fee(c, v.index) / 12 for (mm, c), v in XS.items() if mm == minm}, axis=1); r_ = P.hac_t(pnx.mean(axis=1))
    print(f"[{minm}개월] (a) 차이 − 보수: 연 {r_['mean'] * 12:.4f}, p {r_['p']:.3f}")

# 민감도(8차 점검 권고): 묶음 (a) 달별 평균을 조건별로 — 투자자(연금 클래스) 기준, 스타일 위험비중, 기간 분할, 키움·대신 제외, 같은 모펀드 형제 코드 하나만
SIB = {c for c in NX.columns if "신종개인연금" in str(NAMES.get(c, ""))}            # 한화 신종개인연금(클래스) = LIFEPLUS 운용 코드와 같은 모투자신탁 → 하나만 남김
def pooled(sel, d=XS, add=None):
    cols = {c: (v if add is None else v - add(c, v.index) / 12) for (mm, c), v in d.items() if mm == sel[0] and sel[1](c)}
    q = P.hac_t(pd.concat(cols, axis=1).mean(axis=1)); return {"펀드": len(cols), "평균차(연)": q["mean"] * 12, "p": q["p"], "개월": q["T"]}
sens = []
for minm in (36, 24):
    allc = lambda c: True
    for name, args in [("기본(기준가 그대로)", dict(sel=(minm, allc))),
                       ("투자자 기준(운용펀드 코드에 연금 클래스 총보수 차감)", dict(sel=(minm, allc), add=lambda c, ix: P.tdf_ext_fee(c, ix, "investor_extra"))),
                       ("차이 − 기준가 내 보수", dict(sel=(minm, allc), add=lambda c, ix: -P.tdf_ext_fee(c, ix))),
                       ("공시 글라이드 대신 스타일 위험비중", dict(sel=(minm, allc), d=XS_style)),
                       ("키움·대신 제외", dict(sel=(minm, lambda c: VX.at[c, "manager"] not in ("키움투자자산운용", "대신자산운용")))),
                       ("한화 신종개인연금 형제 코드 제외", dict(sel=(minm, lambda c: c not in SIB)))]:
        sens.append({"규칙": f"첫추정·비교 {minm}개월", "조건": name, **pooled(**args)})
    for per, sl in [("~2024", slice(None, P.PRE)), ("2025~", slice("2025-01", None))]:
        q = P.hac_t(pd.concat({c: v.loc[sl] for (mm, c), v in XS.items() if mm == minm}, axis=1).mean(axis=1))
        sens.append({"규칙": f"첫추정·비교 {minm}개월", "조건": f"기간 {per}", "펀드": None, "평균차(연)": q["mean"] * 12, "p": q["p"], "개월": q["T"]})
sens = pd.DataFrame(sens); sens.to_csv(OUT / "T7_ext_sensitivity.csv", index=False, encoding="utf-8-sig"); display(sens.round(4))
xr.round(4)

# %% [markdown]
# ## 시장 약세장 피신 (KOSPI200 가격지수 약세장 판정월 기준)

# %%
print("표본 안 시장 약세장 판정월:", sorted(d.date() for d in BEAR_M if d >= pd.Timestamp("2016-01-01")))
res[res["전략"].str.contains("확장창\\)·월")].pivot_table(index="전략", values=["연수익", "MDD"], aggfunc="median").round(4)

# %% [markdown]
# ## 한계
# - 확장창 구성도 스타일 회귀(모형)라 실제 보유와 다름 → 차이에 모형오차 포함(2026-07 급락 달 잔차 큼, 감사 2차).
# - 해외 ETF는 미국 상장 EFA·EEM·SPY(미국 보수 포함) → 직접형에 약간 불리. 헤지 carry는 CD91−미 T-bill 근사.
# - 표본 2016~2026(최장 약 10년), 2025~26 국내 급등. 펀드·빈티지끼리 같은 구간을 공유. 36개월 미만 펀드 제외(약한 생존편향).
