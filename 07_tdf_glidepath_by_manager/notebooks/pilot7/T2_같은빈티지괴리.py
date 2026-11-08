# %% [markdown]
# # 주제2 파일럿: 같은 2050인데 왜 나만 반토막?
# **질문**: 2026년 6/22(코스피 종가 고점)→7/30(저점) 급락에서 같은 목표연도 TDF끼리 손실이 얼마나 달랐나? 그 차이를 각 펀드가 투자설명서에 공시한 위험자산 비중이 설명하나?
# - 데이터: KOFIA TDF 기준가 35펀드(5개 운용사 × 2025~2055), 공시 글라이드패스 `glidepath_disclosed_prospectus.csv`(투자설명서 원문 추출, 기존 검증)
# - 비교 기준: Balduzzi & Reuter(2019)는 같은 빈티지 알파의 횡단면 표준편차 3.1%(2009, 미국) — 지표 정의가 달라 직접 비교 불가, 참고만.
# - ⚠ 이 주제는 국내 선행연구가 있음(홍원구 2026 KCMI 26-08 등). 파일럿은 '남은 각도'(급락 낙폭 vs 공시비중)만 확인.

# %%
import numpy as np, pandas as pd
from pension_lab import io, glidepath as gp, tdf_style as ts, pilot7 as P
OUT = P.OUT; OUT.mkdir(parents=True, exist_ok=True)
nav = ts.load_nav("clean_v3")      # 결산 분배 하락 제거본(감사 C #3)
MKT_PEAK, MKT_TROUGH = pd.Timestamp("2026-06-22"), pd.Timestamp("2026-07-30")   # 대장 B: 코스피 종가 고점·저점
k = io.asset_series("kr_eq_tr"); print("KOSPI200 TR 같은 구간:", round(k.asof(MKT_TROUGH) / k.asof(MKT_PEAK) - 1, 4))
# KOFIA 기준가 D일 = D−1일 시장가격 반영(감사 C: 시차 1일 상관 0.80) → 시장일 다음 기준가일 사용
PEAK, TROUGH = (nav.index[nav.index > d][0] for d in (MKT_PEAK, MKT_TROUGH))
print("사용 기준가일:", PEAK.date(), TROUGH.date())
assert nav.loc[[PEAK, TROUGH], [c for c in gp.CODE2VINTAGE if c in nav]].notna().all().all(), "기준가 결측"

# %%
gl = ts.glide_table()
rows = []
for c, v in gp.CODE2VINTAGE.items():
    if c not in nav: continue
    s = nav[c].dropna()
    rows.append({"code": c, "운용사": ts.MGR[c], "빈티지": v,
                 "급락수익": nav.at[TROUGH, c] / nav.at[PEAK, c] - 1,
                 "3년수익(→9/23)": s.iloc[-1] / s.asof(s.index[-1] - pd.DateOffset(years=3)) - 1 if s.index[0] <= s.index[-1] - pd.DateOffset(years=3) else np.nan,
                 "공시 위험자산비중@고점일": float(ts.glide_fn(c, gl)(ts.yrs_rel([PEAK], c))[0])})
f = pd.DataFrame(rows); f.to_csv(OUT / "T2_funds.csv", index=False, encoding="utf-8-sig")
g = f.groupby("빈티지")["급락수익"].agg(["count", "mean", "std", "min", "max"])
g["범위(최대−최소)"] = g["max"] - g["min"]; g.round(4)

# %% [markdown]
# ## 같은 빈티지 안 차이 vs 빈티지 사이 차이
# 빈티지 평균끼리의 표준편차(사이)와 빈티지 안 표준편차의 평균(안)을 비교. '안'이 '사이'만큼 크면 "같은 2050인데 다르다"가 사실.

# %%
within = g["std"].mean(); between = g["mean"].std()
print(f"빈티지 안 sd 평균 {within:.4f} / 빈티지 사이 sd {between:.4f} / 비율 {within/between:.2f}")
# 공시 위험자산비중이 낙폭을 설명하나 (단순 OLS, 35개)
X = np.c_[np.ones(len(f)), f["공시 위험자산비중@고점일"]]; y = f["급락수익"].values
b, *_ = np.linalg.lstsq(X, y, rcond=None); r2 = ts.r2(y, X, b); print("기울기", round(b[1], 4), "R²", round(r2, 3))
# 빈티지 고정효과를 뺀 뒤(같은 빈티지 안에서) 공시비중이 설명하나
fd = f.assign(y=y - f.groupby("빈티지")["급락수익"].transform("mean"),
              x=f["공시 위험자산비중@고점일"] - f.groupby("빈티지")["공시 위험자산비중@고점일"].transform("mean"))
bw = (fd.x * fd.y).sum() / (fd.x ** 2).sum(); r2w = 1 - ((fd.y - bw * fd.x) ** 2).sum() / (fd.y ** 2).sum()
print("빈티지 안 기울기", round(bw, 4), "빈티지 안 R²", round(r2w, 3))
# 원자료·같은 날짜 기준과 비교(감사 C 재계산값: within/between 0.87 → 0.68)
raw = io.load_tdf_nav(); rr = (raw.loc[MKT_TROUGH] / raw.loc[MKT_PEAK] - 1).reindex(f.code).to_numpy()
gr = pd.Series(rr).groupby(f["빈티지"].to_numpy())
print("원자료·같은날짜: within/between =", round(gr.std().mean() / gr.mean().std(), 2))
# 운용사 효과와 구분되나(통계 감사 🟠6): 빈티지 FE + 운용사 FE를 같이 넣은 OLS
D = pd.get_dummies(f[["빈티지", "운용사"]].astype(str), drop_first=True).astype(float)
Xf = np.c_[np.ones(len(f)), f["공시 위험자산비중@고점일"], D]; bf, *_ = np.linalg.lstsq(Xf, y, rcond=None); e = y - Xf @ bf
se = np.sqrt(e @ e / (len(y) - Xf.shape[1]) * np.linalg.inv(Xf.T @ Xf)[1, 1])
print(f"빈티지+운용사 FE: 기울기 {bf[1]:.4f} (SE {se:.4f}, t {bf[1]/se:.2f}), R² {ts.r2(y, Xf, bf):.3f}  ※운용사 5개·사건 1개 → 추론 약함")
pd.DataFrame([{"within_sd": within, "between_sd": between, "slope": b[1], "R2": r2, "slope_within": bw, "R2_within": r2w,
               "slope_vint_mgr_FE": bf[1], "se_vint_mgr_FE": se}]).to_csv(OUT / "T2_summary.csv", index=False)

# %%
f.sort_values(["빈티지", "급락수익"]).round(4)

# %% [markdown]
# ## 사건 패널로 확장 (한계 보완: '급락 1번·35개')
# - 사건 정의: KOSPI200 **가격지수 일별 종가**(`idx_kospi200.csv`)가 직전 고점 대비 −20% 이하, 고점부터 **2개월 이상** 지난 시점에 −20% 이하(SEC: "20% or more over at least a two-month period").
#   SEC 정의엔 사건 '끝' 규칙이 없어 두 규칙을 병기(회원 결정 2026-10-08): **규칙 A** 고점을 회복할 때까지 한 사건 / **규칙 B** 저점 대비 +20% 반등하면 그 사건을 끝내고 새로 셈(강세장 관례).
#   저점 = 사건 안 최저점. 기준가는 시장일 **다음** 기준가일(시차 1일, 위와 같은 규칙). 그 고점일에 기준가가 있는 펀드만.
# - 회귀(기본 = 사건×빈티지 FE: 같은 사건·같은 빈티지 안에서 공시비중이 다른 펀드끼리 비교): 급락수익 ~ 공시 위험자산비중 + FE. 표준오차: 펀드 군집 + 운용사 5개 군집의 wild cluster bootstrap(Webb 6점 가중, Roodman 등 2019).
# - 보조: 사건별 따로 회귀, x×시장낙폭(사건마다 낙폭 크기가 달라 기울기 크기가 다름).

# %%
D2 = pd.DateOffset(months=P.BEAR_MIN_MONTHS)
def episodes(lv, rule="A", thr=P.BEAR):
    """일별 수준 → [(고점일, 저점일, 낙폭)]. 판정: 고점+2개월 이후 낙폭 ≤ thr. 끝: A = 고점 회복, B = 저점 대비 +20% 반등 또는 고점 회복."""
    out, v, ix, n = [], lv.to_numpy(float), lv.index, len(lv)
    pk, pk_d, t = v[0], ix[0], 0
    while t < n:
        if v[t] >= pk: pk, pk_d = v[t], ix[t]; t += 1; continue
        if v[t] / pk - 1 <= thr and ix[t] >= pk_d + D2:
            p0 = ix.get_loc(pk_d); j = t; tr = p0 + int(np.argmin(v[p0:t + 1]))    # 반등 기준 저점은 고점부터 추적
            while j < n and v[j] < pk:
                if v[j] < v[tr]: tr = j
                if rule == "B" and v[j] >= v[tr] * (1 - thr): break
                j += 1
            lo = int(np.argmin(v[ix.get_loc(pk_d):j])) + ix.get_loc(pk_d)
            out.append((pk_d, ix[lo], float(v[lo] / pk - 1)))
            if j < n and rule == "B" and v[j] < pk: pk, pk_d = v[j], ix[j]    # 반등으로 끝난 경우 그 지점부터 새 고점 추적
            t = j; continue
        t += 1
    return out

_ix = pd.date_range("2020-01-01", periods=8, freq="45D")
_t = episodes(pd.Series([1, .9, .79, .97, 1.01, .85, .7, .95], index=_ix), "A")    # 손계산: 회복(1.01) 뒤 두 번째 사건
assert [(a, b) for a, b, _ in _t] == [(_ix[0], _ix[2]), (_ix[4], _ix[6])], _t
_s = pd.Series([1, .9, .79, .97, .99, .85, .7, .95], index=_ix)                         # 고점 1을 회복 못 함
assert [(a, b) for a, b, _ in episodes(_s, "A")] == [(_ix[0], _ix[6])]                    # A: 한 사건
assert [(a, b) for a, b, _ in episodes(_s, "B")] == [(_ix[0], _ix[2]), (_ix[4], _ix[6])]  # B: .79→.97(+23%) 반등으로 끝, 새 고점 .99에서 다시
assert episodes(pd.Series([1, .75, 1.01], index=pd.date_range("2020-01-01", periods=3, freq="20D"))) == []     # 2개월 안에 회복 → 사건 아님

KPXd = pd.read_csv(P.paths.EQUITY_KR / "idx_kospi200.csv", parse_dates=["날짜"]).set_index("날짜")["종가"].sort_index()
import statsmodels.formula.api as smf

def _crt(X, y, g, j):
    """OLS 계수 j의 군집강건(CR1, statsmodels와 같은 소표본 보정) t."""
    XtXi = np.linalg.pinv(X.T @ X); b = XtXi @ X.T @ y; u = y - X @ b; N, K = X.shape; G = g.max() + 1
    S = np.zeros((K, K))
    for k in range(G):
        s_ = X[g == k].T @ u[g == k]; S += np.outer(s_, s_)
    V = XtXi @ S @ XtXi * G / (G - 1) * (N - 1) / (N - K)
    return b[j] / np.sqrt(V[j, j])

def webb_wcb(df, fml, cl, B=9999, seed=P.SEED):
    """x 기울기 = 0 귀무 제약 wild cluster bootstrap-t (Webb 6점 가중), 군집 = cl. 양측 p값."""
    import patsy
    y, X = patsy.dmatrices(fml, df, return_type="dataframe"); j = list(X.columns).index("x")
    X, y = X.to_numpy(float), y.to_numpy(float).ravel(); g = pd.factorize(df.loc[:, cl])[0]
    t0 = _crt(X, y, g, j); Xr = np.delete(X, j, axis=1); br = np.linalg.lstsq(Xr, y, rcond=None)[0]; yh = Xr @ br; e = y - yh
    rng = np.random.default_rng(seed); w6 = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)]); G = g.max() + 1
    ts_ = np.array([_crt(X, yh + e * rng.choice(w6, G)[g], g, j) for _ in range(B)])
    return float((np.abs(ts_) >= abs(t0)).mean())

prow = []
for rule in ("A", "B"):
    EV = [e for e in episodes(KPXd, rule) if e[0] >= nav.index[0]]
    print(f"규칙 {rule} 사건(고점→저점, 낙폭):", [(a.date(), b.date(), round(d, 3)) for a, b, d in EV])
    for a, b_, dd in EV:
        pk, tr = (nav.index[nav.index > d][0] for d in (a, b_))
        for c, v in gp.CODE2VINTAGE.items():
            if c not in nav or pd.isna(nav.at[pk, c]) or pd.isna(nav.at[tr, c]): continue
            prow.append({"규칙": rule, "사건": f"{a.date()}→{b_.date()}" + (" (진행 중·저점 잠정)" if KPXd.loc[b_:].max() < KPXd.loc[a] and (rule == "A" or KPXd.loc[b_:].max() < KPXd.loc[b_] * (1 - P.BEAR)) else ""), "시장낙폭": dd, "code": c, "운용사": ts.MGR[c], "빈티지": v,
                         "급락수익": nav.at[tr, c] / nav.at[pk, c] - 1, "공시 위험자산비중@고점일": float(ts.glide_fn(c, gl)(ts.yrs_rel([pk], c))[0])})
pn = pd.DataFrame(prow); pn.to_csv(OUT / "T2_panel.csv", index=False, encoding="utf-8-sig")
display(pn.groupby(["규칙", "사건"]).agg(펀드수=("code", "size"), 시장낙폭=("시장낙폭", "first"), 평균=("급락수익", "mean"), 최소=("급락수익", "min"), 최대=("급락수익", "max")).round(4))
wb = pn.groupby(["규칙", "사건"]).apply(lambda e: e.groupby("빈티지")["급락수익"].std().mean() / e.groupby("빈티지")["급락수익"].mean().std(), include_groups=False)
print("사건별 빈티지 안/사이 sd 비율:", wb.round(2).to_dict())

pt = []
for rule, g in pn.groupby("규칙"):
    d_ = g.rename(columns={"급락수익": "y", "공시 위험자산비중@고점일": "x0", "사건": "ev", "빈티지": "vin", "운용사": "mgr", "시장낙폭": "mdd"})
    d_ = d_.assign(x=d_["x0"], evvin=d_["ev"] + "|" + d_["vin"].astype(str), xm=d_["x0"] * d_["mdd"])
    specs = [("사건FE", "y ~ x + C(ev)"), ("사건×빈티지FE (기본)", "y ~ x + C(evvin)"), ("사건×빈티지FE + 운용사FE", "y ~ x + C(evvin) + C(mgr)")]
    for spec, fml in specs:
        fit = smf.ols(fml, d_).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d_["code"])[0]})
        pt.append({"규칙": rule, "모형": spec, "기울기": fit.params["x"], "SE": fit.bse["x"], "SE 종류": "펀드군집", "t": fit.tvalues["x"], "p": fit.pvalues["x"],
                   "p(운용사 WCB, Webb)": webb_wcb(d_, fml, "mgr"), "N": int(fit.nobs), "R²": fit.rsquared})
    fit = smf.ols("y ~ xm + C(evvin)", d_).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d_["code"])[0]})
    pt.append({"규칙": rule, "모형": "기울기∝시장낙폭 제약(xm = x×낙폭만, 주효과 없음) + 사건×빈티지FE", "기울기": fit.params["xm"], "SE": fit.bse["xm"], "SE 종류": "펀드군집", "t": fit.tvalues["xm"], "p": fit.pvalues["xm"], "N": int(fit.nobs), "R²": fit.rsquared})
    for ev_, e in d_.groupby("ev"):
        fit = smf.ols("y ~ x + C(vin)", e).fit(cov_type="HC1")
        pt.append({"규칙": rule, "모형": f"사건별: {ev_} (빈티지FE, HC1)", "기울기": fit.params["x"], "SE": fit.bse["x"], "SE 종류": "HC1", "t": fit.tvalues["x"], "p": fit.pvalues["x"], "N": int(fit.nobs), "R²": fit.rsquared})
pt = pd.DataFrame(pt); pt.to_csv(OUT / "T2_panel_reg.csv", index=False, encoding="utf-8-sig"); pt.round(4)

# %% [markdown]
# 읽는 법: 기울기 음수 = 공시 위험자산비중이 높을수록 더 많이 빠짐(기대 방향). 사건FE만 넣으면 빈티지 차이(=비중 차이)가 대부분을 설명하고, 같은 사건·같은 빈티지 안에서 비교하면(기본) 공시비중이 남은 차이를 설명하는지가 핵심 질문.
# 운용사가 5개뿐이라 운용사 군집 추론은 wild cluster bootstrap p값으로 봄(군집 5개 Webb 가중은 서로 다른 부호 조합이 6^5개라 p값 해상도가 거칠고, 아주 작은 p는 나오기 어려움).

# %% [markdown]
# ## 확장 표본: 기존 5개 + 추가 운용사 (한계 보완 — '운용사 5개')
# 추가 운용사 TDF: 투자설명서 공시 글라이드(`glidepath_disclosed_web_kr_others.csv`)가 있는 펀드의 KOFIA 기준가를 설정일부터 다시 받아(`fetch.kofia_navfull ext`)
# 기존과 같은 정제 규칙 v3로 정제(`nav_tdfext_clean_v3`). 사건마다 그 고점일에 기준가가 있는 펀드만. 목표시점 = 목표연도 1월 1일.

# %%
UX = P.tdf_ext_universe(); NX = P.tdf_ext_nav()
def glide_ext(code):
    g = UX[UX.code == code].groupby("years_rel_target").risky_pct.mean().sort_index()
    return lambda yrs: np.interp(yrs, g.index.values.astype(float), g.values / 100, left=g.values[0] / 100, right=g.values[-1] / 100)
VX = UX.drop_duplicates("code").set_index("code")
xrow = []
for rule in ("A", "B"):
    for a, b_, dd in [e for e in episodes(KPXd, rule) if e[0] >= min(NX.index[0], nav.index[0])]:
        tag = f"{a.date()}→{b_.date()}"
        for src, navd in (("기존 5개사", nav), ("추가 운용사", NX)):
            pk, tr = (navd.index[navd.index > d][0] for d in (a, b_))
            if (pk - a).days > 7 or (tr - b_).days > 7: continue           # 그 자료의 기준가가 시장일 직후에 없으면(설정 전) 이 사건에서 제외
            for c in navd.columns:
                if pd.isna(navd.at[pk, c]) or pd.isna(navd.at[tr, c]): continue
                if src == "기존 5개사":
                    if c not in gp.CODE2VINTAGE: continue
                    mgr, vin, w = ts.MGR[c], gp.CODE2VINTAGE[c], float(ts.glide_fn(c, gl)(ts.yrs_rel([pk], c))[0])
                else:
                    mgr, vin = VX.at[c, "manager"], int(VX.at[c, "vintage"])
                    w = float(glide_ext(c)((pk - pd.Timestamp(f"{vin}-01-01")).days / 365.25))
                xrow.append({"규칙": rule, "사건": tag, "출처": src, "code": c, "운용사": mgr, "빈티지": vin, "급락수익": navd.at[tr, c] / navd.at[pk, c] - 1, "공시 위험자산비중@고점일": w})
px_ = pd.DataFrame(xrow); px_.to_csv(OUT / "T2_panel_ext.csv", index=False, encoding="utf-8-sig")
display(px_.groupby(["규칙", "사건"]).agg(펀드수=("code", "size"), 운용사수=("운용사", "nunique"), 평균=("급락수익", "mean"), 최소=("급락수익", "min"), 최대=("급락수익", "max")).round(4))
print("빈티지 안/사이 sd 비율:", px_.groupby(["규칙", "사건"]).apply(lambda e: e.groupby("빈티지")["급락수익"].std().mean() / e.groupby("빈티지")["급락수익"].mean().std(), include_groups=False).round(2).to_dict())
xt = []
for rule, g in px_.groupby("규칙"):
    d_ = g.rename(columns={"급락수익": "y", "공시 위험자산비중@고점일": "x", "사건": "ev", "빈티지": "vin", "운용사": "mgr"})
    d_ = d_.assign(evvin=d_["ev"] + "|" + d_["vin"].astype(str))
    for spec, fml in [("사건FE", "y ~ x + C(ev)"), ("사건×빈티지FE (기본)", "y ~ x + C(evvin)"), ("사건×빈티지FE + 운용사FE", "y ~ x + C(evvin) + C(mgr)")]:
        fit = smf.ols(fml, d_).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d_["mgr"])[0]})
        xt.append({"규칙": rule, "모형": spec, "기울기": fit.params["x"], "SE": fit.bse["x"], "SE 종류": "운용사군집", "t": fit.tvalues["x"], "p": fit.pvalues["x"],
                   "p(운용사 WCB, Webb)": webb_wcb(d_, fml, "mgr"), "N": int(fit.nobs), "운용사": d_["mgr"].nunique(), "R²": fit.rsquared})
xt = pd.DataFrame(xt); xt.to_csv(OUT / "T2_panel_ext_reg.csv", index=False, encoding="utf-8-sig"); xt.round(4)

# %% [markdown]
# ## 한계
# - 공시 위험자산비중은 투자설명서 '목표' 곡선(±1%p 평균) — 실제 보유비중 아님. 반도체 쏠림(종목 집중)은 이 자료로 못 봄.
# - 빈티지 사이 sd는 빈티지 평균 7개의 sd라 빈티지 안 잡음(sd/√5)이 섞여 약간 부풀려짐.
# - 단일 급락 35개 → 위 사건 패널(2016~ 가격지수 일별 −20%·2개월 사건 전부, 끝 규칙 2가지)로 확장. 2022~ 사건은 17개 운용사 확장 표본으로 다시 봄(위 절). 사건 수는 여전히 적음.
