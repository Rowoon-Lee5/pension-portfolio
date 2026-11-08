# %% [markdown]
# # 간단 테스트 T2: 원화로 매달 저축하는 30세에게 "30년이면 주식은 안전하다"가 맞나
# **성격: 탐색용 기술. 판정하지 않는다.** 숫자만 보여 준다. "유의", "효과 있다", "안전/위험하다" 같은 단정은 쓰지 않는다.
#
# - 정본 명세: `docs/ideas/본연구후보_20261027/간단테스트_명세_T2_20261027.md`(커밋 d025dfb, 결과 전 사전등록) + 정정 r1 `간단테스트_명세_T2_정정r1_20261027.md`(17e7507·089553d, 원 명세보다 우선).
# - 순서(명세 5절): 0단계 입력·창 수 → **1단계 MDE(`T2_mde.csv`, SD만, 이 노트북보다 먼저 `_gen_T2.py mde`로 계산)** → 2단계 본 격자 → 3단계 위약 → 4단계 국면표·민감도·그림.
# - 지표(3-3): 손실확률 p = P(실질 금액 < 실질 납입 누계), 하위 5%(P5)·중앙값(P50) = 실질 금액 ÷ 실질 납입 누계의 분위수. MC SE는 **몬테카를로 오차일 뿐 표본 불확실성이 아니다.**
# - 포트폴리오: ① 국내주식 100 · ② 국내주식 60/국내채권 40 · ③ 미국주식 원화 비헤지 · ③H 헤지(한·미 단기금리 차) · ④ 국내 33/해외 67(ACO 2025, 회원 지정) · ④H · ⑤ 5대 운용사 2055 글라이드 mean5.
# - 리밸런싱(D7-B)·글라이드 계단(D10-A)은 **가입 시점부터 12개월마다(t mod 12 = 0)**, 달력 1월이 아님(정정 r1 #6).
# - 판정 규칙은 하나(정정 r1 #3): 주 비교 Δp가 MDE보다 작으면 "식별 안 됨". ACO 숫자는 손실확률 수준의 참고값일 뿐.
#
# **이미 본 결과(명세 1절·정정 r1 #2, 사전 지식 공개)**: 7주제 파일럿 T4(세후·계좌 밖 현금 포함 정의, KR1991 주식100 7.42~7.77%, US 1.25~1.74% 등), 배당 민감도(sens_k200dy), pilot9 C·D 글라이드, T3, M2 예시 계산,
# 공통확인 환율사건(`results/pilot8_20261010/common_crash_fx_20261010.csv`: 코스피 급락 8행 중 E3·E6(2026)은 원화 강세 = 쿠션 미작동 사례), 주제2 d 결과(θ3 Δb 식별 안 됨), 심층 2 T6 리밸런싱 주기 결과.

# %%
import time, numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy.stats import beta
import _t2_core as C
from pension_lab import pilot7 as P
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
OUT, T, NP, SEED = C.OUT, C.T, C.NP, C.SEED
TAGS = ["D7", "D8", "D9", "D10", "D11", "D17"]
TIMER = {}
def tic(nm): TIMER[nm] = time.time()
def toc(nm):
    s = time.time() - TIMER[nm]; print(f"[{nm}] {s:.0f}s")
    with open(OUT / "nb_meta" / "run_log.txt", "a", encoding="utf-8") as f: f.write(f"{pd.Timestamp.now().isoformat(timespec='seconds')}\tcell {nm}\t{s:.0f}s\n")
tic("자료")
k = C.kr_panel(); k8 = C.kr1980_panel(); us = C.us_panel(); uk = C.us_krw_panel()
fr = P.french_panel(); ol = P.oecd_local_panel(); sw = C.swinkels_oecd_panel(ol)
PWT = pd.read_csv(OUT / "T2_pw_blocks.csv")
pw = lambda s, c="eq": float(PWT.query("표본 == @s and 계열 == @c")["PW"].iloc[0])
WC = pd.read_csv(OUT / "T2_window_counts.csv")
display(WC[WC["묶음"] == "단일"])
print("French 조각(12개월 이상):", len(fr), "| 360개월 이상:", int((WC[WC["묶음"].str.startswith("French")]["개월"] >= T).sum()),
      "| 끝:", max(v.index[-1] for v in fr.values()).date(), "(정정 r1 #8: 실제 끝 2025-09)")
print("PW 원값(전체 표본, 명세 3-6 '자료를 보고 정한 설계' — 원값 기록):"); display(PWT)
toc("자료")

# %% [markdown]
# ## 1. MDE (결과 전 계산·동결분 읽기만)
# `T2_mde.csv`는 이 노트북보다 먼저 `_gen_T2.py mde`로 만들었다(run_log 시각 참고). 역사 재표본 SD만 있고 평균·점추정은 없다.
# - MDE = (z0.975 + z0.80)·SE_hist = 2.80·SD (90%: 3.24·SD, T2-D21 병기). 주 표본 KR1991, 블록 4개, B_out 1,000 × 안쪽 2,000경로.
# - 정정 r1 4(a): `MC오차_안쪽` = √(평균 p(1−p)/2000) (차이는 두 칸 MC 분산 합의 제곱근 — 짝지은 경로라 실제보다 큰 쪽). **MC 오차가 SE_hist를 부풀릴 수 있다** → `SD_MC보정` = √(SD² − MC오차²) 병기.
# - 한계: 안쪽 계산이 결과와 같은 양을 만들므로 '결과를 모른다'는 맹검은 약하다(SD만 저장하는 절차 통제뿐).

# %%
MDE = pd.read_csv(OUT / "T2_mde.csv")
display(MDE.pivot_table(index=["종류", "대상", "지표"], columns="블록출처", values="MDE80").round(4))
mde = lambda blk, kind, nm, m, col="MDE80": float(MDE[(np.isclose(MDE["블록"], blk)) & (MDE["종류"] == kind) & (MDE["대상"] == nm) & (MDE["지표"] == m)][col].iloc[0])
print("(b) 독립 단위 기준 — 다국가 두 군 비율차 MDE(각 22창, 'M2_calc_mde_prop.csv') = **독립 가정 시(낙관)**:")
display(pd.read_csv(C.paths.RESULTS / "simpletest_20261027" / "method" / "M2_calc_mde_prop.csv").assign(표기="독립 가정 시(낙관)"))

# %% [markdown]
# ## 2. 블록 부트스트랩 격자 (명세 8절 + 정정 r1 #1)
# - 단일국: `bootstrap.paired_resample_paths`로 한 표본의 모든 열에 같은 인덱스(포트폴리오 간 짝). 블록 = PW 원값(T2-D18 주, 정정 r1) · 12 · 1(iid) · 120(425개월 ≈ 3.5블록 = **한 역사 재배열 ⚠**).
# - 다국가: `pilot7.pooled_paths`(ACO 방식). 블록 120(기본)·12·240·1.
# - 경로 10,000개(T2-D4 A), 주 표본은 100,000개(D4-B, 시드 SEED+1)도. 한국 변형 43개(원 33 + 정정 r1 ④×D17, ⑤×D8×D17).
# - D5: A 계좌 세전 / B T4 세후(공제 16.5% 환급·연금소득세 5.5%·계좌 밖 현금 E — T4 sim('A') 같은 식, 0단계에서 T4_level 한 칸 재현 확인) / C 일시금 P(W_real<1). D6: A 명목 고정 / B 실질 고정(전월까지 물가).
# - 현금 계열이 없는 표본(KR1980·US 원화)은 D5-B 미산출.

# %%
tic("부트스트랩")
VK = C.variants_kr()
V80 = [v for v in VK if v["port"] in ("①", "③")]
VUK = [v for v in VK if v["port"] == "③"]
VEB = C.variants_eqbd(); VEB_B = C.variants_eqbd(with_eq=False)
def bl_single(pwv, src):
    return [(pwv, f"PW({src})" + ("=1(iid와 같음)" if pwv == 1 else "")), (12.0, "12"), (1.0, "iid"), (120.0, "120(한 역사 재배열 ⚠)")]
BL_POOL = [(120.0, "120(ACO 기본)"), (12.0, "12"), (240.0, "240"), (1.0, "iid")]
SINGLE = [("KR", "KR1991", k, VK, bl_single(pw("KR1991"), "KR1991 eq")),
          ("KR", "KR1996", k.loc["1996-01":], VK, bl_single(pw("KR1996"), "KR1996 eq")),
          ("KR", "KR~2024", k.loc[:P.PRE], VK, bl_single(pw("KR~2024"), "KR~2024 eq")),
          ("KR1980", "KR1980", k8, V80, bl_single(pw("KR1980(주식판)"), "KR1980 eq")),
          ("US달러", "US1965", us, VEB, bl_single(pw("US1965(달러)"), "US eq")),
          ("US원화", "US원화 D12-A", uk, VUK, bl_single(pw("US원화 D12-A", "us"), "US원화 us")),
          ("US원화", "US원화 D12-B", uk.loc["1980-03":], VUK, bl_single(pw("US원화 D12-B", "us"), "US원화 us"))]
POOLED = [("French달러", "French 21개국+미국", fr, [VK[0]]), ("OECD현지", "OECD 17개국(D13-A 합성 국채)", ol, VEB), ("OECD현지", "OECD+Swinkels(D13-B)", sw, VEB_B)]
rows = []
def add(grp, sname, blk, src, n, v, res, extra={}):
    for (d5, d6), x in res.items():
        rows.append(dict(묶음=grp, 표본=sname, 블록=blk, 블록출처=src, 경로수=n, 변형=v["name"], 이름표=v["label"], 포트=v["port"],
                         **{d: v["tags"].get(d, "") for d in TAGS}, D5=d5, D6=d6, **extra, **C.summ(x)))
V4 = dict(port="③USD(P4)", tags={}, comps=["us_usd"], W=np.ones((T, 1)), annual=False, name="③USD(P4, 미국 CPI 실질)", label="③USD(P4)")
for grp, sname, df, V, bl in SINGLE:
    arr, cols = C.arr_cols(df)
    for blk, src in bl:
        idx = C.boot_idx(len(df), NP, blk, SEED)
        for v in V:
            add(grp, sname, blk, src, NP, v, C.run_variant(arr, cols, idx, v))
        if grp == "KR":                                        # 위약 P4: 같은 경로, 미국 USD 수익 + 미국 CPI
            add(grp, sname, blk, src, NP, V4, C.run_variant(arr, cols, idx, V4, "AC", "AB", shift={"infl": arr[:, cols["us_infl"]]}))
    print(sname, "끝", f"{time.time() - TIMER['부트스트랩']:.0f}s", flush=True)
arr, cols = C.arr_cols(k); idx = C.boot_idx(len(k), 100_000, pw("KR1991"), SEED + 1)   # T2-D4 B: 주 표본·주 블록
for v in VK:
    add("KR", "KR1991", pw("KR1991"), "PW(KR1991 eq)", 100_000, v, C.run_variant(arr, cols, idx, v))
del idx
for grp, sname, pan, V in POOLED:
    for blk, src in BL_POOL:
        idx, flat = C.pooled_idx(pan, NP, blk, SEED); arr, cols = C.arr_cols(flat)
        for v in V:
            add(grp, sname, blk, src, NP, v, C.run_variant(arr, cols, idx, v))
    print(sname, "끝", flush=True)
BOOT = pd.DataFrame(rows); BOOT.to_csv(OUT / "T2_boot_cells.csv", index=False, encoding="utf-8-sig")
print("칸 수:", len(BOOT))
toc("부트스트랩")

# %%
MAINB = pw("KR1991")
REC = lambda d: d[d["변형"].isin([v["name"] for v in VK + VEB + VEB_B if C.is_rec(v)]) | (d["포트"] == "③USD(P4)")]
show = REC(BOOT[(BOOT["D5"] == "A") & (BOOT["D6"] == "A") & (BOOT["경로수"] == NP)])
print("추천안(D5-A·D6-A) 손실확률 p — 표본 × 블록 × 포트폴리오")
display(show.pivot_table(index=["묶음", "표본", "블록출처"], columns="이름표", values="p", sort=False).round(4))
print("같은 칸의 P5 / P50")
display(show.pivot_table(index=["묶음", "표본", "블록출처"], columns="이름표", values=["P5", "P50"], sort=False).round(3))

# %% [markdown]
# ### 2-1. 주 비교 Δp와 MDE (KR1991) — Δp가 MDE보다 작으면 "식별 안 됨"(정정 r1 #3)
# MC SE_Δ = √(SE_a² + SE_b²). |Δp| < 1.96·MC SE_Δ면 "0 근처"(정정 r1 3(c)).

# %%
def rec_cell(d, sname, blk, port, d5="A", d6="A", n=NP):
    x = REC(d[(d["표본"] == sname) & np.isclose(d["블록"], blk) & (d["포트"] == port) & (d["D5"] == d5) & (d["D6"] == d6) & (d["경로수"] == n)])
    assert len(x) == 1, (sname, blk, port, len(x)); return x.iloc[0]
COMPS = [("③−①", "③", "①"), ("④−①", "④", "①"), ("⑤−②", "⑤", "②"), ("④−⑤", "④", "⑤")]
mrows = []
for blk, src in bl_single(MAINB, "KR1991 eq"):
    for nm, a, b in COMPS:
        A, B = rec_cell(BOOT, "KR1991", blk, a), rec_cell(BOOT, "KR1991", blk, b)
        for m in ("p", "P5"):
            dlt = A[m] - B[m]; m80, m90 = mde(blk, "차이", nm, m), mde(blk, "차이", nm, m, "MDE90")
            se = np.hypot(A["mc_se"], B["mc_se"]) if m == "p" else np.nan
            mrows.append(dict(블록출처=src, 비교=nm, 지표=m, 차이=dlt, MC_SE=se, 영근처=bool(abs(dlt) < 1.96 * se) if m == "p" else None,
                              MDE80=m80, MDE90=m90, 기술80="식별 안 됨" if abs(dlt) < m80 else "MDE80보다 큼", 기술90="식별 안 됨" if abs(dlt) < m90 else "MDE90보다 큼"))
MV = pd.DataFrame(mrows); MV.to_csv(OUT / "T2_mde_vs_delta.csv", index=False, encoding="utf-8-sig"); display(MV.round(4))

# %% [markdown]
# ## 3. 실제 역사 창 (명세 3-4 ①·②)
# - **안 겹친 창**: 표본 첫 달부터 360개월씩. 한국은 표본마다 1개 → **사례 기술만**(0건이어도 95% 상한 0.975).
# - **겹치는 창**: 매달 시작하는 모든 창. 분포만 기술하고 "손실 창 비율"에 표준오차·신뢰구간을 붙이지 않는다(독립 아님, h/T = 0.85 — Valkanov 2003).

# %%
tic("역사 창")
hrows, crow = [], []
def hist(grp, sname, df, V, step=1, shift=None):
    arr, cols = C.arr_cols(df); W = C.windows(len(df), step)
    if not len(W): return
    for v in V:
        for (d5, d6), x in C.run_variant(arr, cols, W, v, shift=shift).items():
            for j, xx in zip(W[:, 0], x):
                hrows.append(dict(묶음=grp, 표본=sname, 변형=v["name"], 이름표=v["label"], 포트=v["port"], **{d: v["tags"].get(d, "") for d in TAGS},
                                  D5=d5, D6=d6, 시작=df.index[j].strftime("%Y-%m"), 끝=df.index[j + T - 1].strftime("%Y-%m"), 안겹침=bool(j % T == 0), 배수=xx, 손실=bool(xx < 1)))
for grp, sname, df, V, _ in SINGLE:
    hist(grp, sname, df, V)
for nm, df in sorted(fr.items()):
    hist("French달러", nm, df, [VK[0]], step=T)
for nm, df in sorted(ol.items()):
    hist("OECD현지(D13-A)", nm, df, VEB, step=T)
for nm, df in sorted(sw.items()):
    hist("OECD현지(D13-B)", nm, df, VEB_B, step=T)
H = pd.DataFrame(hrows)
HS = H[H["묶음"].isin(["KR", "KR1980", "US달러", "US원화"])]
HS.to_csv(OUT / "T2_hist_windows_overlap.csv", index=False, encoding="utf-8-sig")
g = HS.groupby(["묶음", "표본", "변형", "이름표", "포트", "D5", "D6"], sort=False)
SUMO = g["배수"].agg(창수="size", 최소="min", 하위5=lambda x: x.quantile(.05), 중앙=lambda x: x.median(), 최대="max").join(g["손실"].mean().rename("손실창비율(기술용, SE 없음)"))
NON = HS[HS["안겹침"]]
SUMO.reset_index().merge(NON.groupby(["묶음", "표본", "변형", "D5", "D6"])["배수"].apply(lambda x: "; ".join(f"{v:.3f}" for v in x)).rename("안겹친창_배수").reset_index(),
                          on=["묶음", "표본", "변형", "D5", "D6"]).to_csv(OUT / "T2_hist_windows_nonoverlap.csv", index=False, encoding="utf-8-sig")
MC = H[~H["묶음"].isin(["KR", "KR1980", "US달러", "US원화"])].sort_values(["묶음", "표본", "변형", "D5", "D6", "시작"])
MC.to_csv(OUT / "T2_multicountry_by_country.csv", index=False, encoding="utf-8-sig")
print("한국·미국 안 겹친 창(추천안, D5-A·D6-A) — 사례:")
display(REC(NON[(NON["D5"] == "A") & (NON["D6"] == "A")]).pivot_table(index=["표본", "시작", "끝"], columns="이름표", values="배수", sort=False).round(3))
print("겹치는 창 분포(추천안, D5-A·D6-A) — 기술용:")
display(REC(SUMO.reset_index()[lambda d: (d["D5"] == "A") & (d["D6"] == "A")]).set_index(["표본", "이름표"])[["창수", "최소", "하위5", "중앙", "최대", "손실창비율(기술용, SE 없음)"]].round(3))
toc("역사 창")

# %% [markdown]
# ### 3-1. 다국가 안 겹친 창 — 나라별(알파벳순)·Clopper–Pearson 상한 (정정 r1 #9)
# - n = 창 수: **독립 가정 시(낙관)**. n = 1: 나라들이 대체로 같은 달력 구간(1975-01~2025 전후)을 쓰므로 **실효 독립 단위 1** → 0건이면 상한 0.975. **요약은 n = 1 값 기준.**
# - French 21개국은 살아남은 선진시장(ACO는 사라진 시장 포함) → 손실 꼬리는 과소 추정 방향일 수 있다.

# %%
cp = lambda kk, n: 1.0 if kk >= n else float(beta.ppf(0.975, kk + 1, n - kk))
mrow = []
for (grp, var, d5, d6), d in MC.groupby(["묶음", "변형", "D5", "D6"]):
    kk, n = int(d["손실"].sum()), len(d)
    mrow.append(dict(묶음=grp, 변형=var, D5=d5, D6=d6, 창수=n, 손실창=kk, 상한_독립가정시_낙관=cp(kk, n), 상한_실효n1=cp(min(kk, 1), 1),
                     창시작범위=f"{d['시작'].min()}~{d['시작'].max()}"))
MCS = pd.DataFrame(mrow); MCS.to_csv(OUT / "T2_multicountry_cp.csv", index=False, encoding="utf-8-sig")
display(MCS[(MCS["D5"] == "A") & (MCS["D6"] == "A")].round(4))

# %% [markdown]
# ## 4. 위약(가짜약) 비교 (명세 6절)
# ### P1 iid vs 블록 — 같은 자료, 블록만 다름

# %%
b0 = show.copy()
base = b0[np.isclose(b0["블록"], 1.0)].set_index(["묶음", "표본", "변형"])[["p", "P5", "P50"]]; base = base[~base.index.duplicated()]
P1 = b0.join(base, on=["묶음", "표본", "변형"], rsuffix="_iid")
for m in ("p", "P5", "P50"):
    P1[f"{m}−iid"] = P1[m] - P1[f"{m}_iid"]
P1 = P1[~np.isclose(P1["블록"], 1.0)][["묶음", "표본", "블록출처", "이름표", "p", "p_iid", "p−iid", "P5−iid", "P50−iid", "mc_se"]]
P1.to_csv(OUT / "T2_placebo_iid_vs_block.csv", index=False, encoding="utf-8-sig")
display(P1[P1["표본"].isin(["KR1991", "US1965", "French 21개국+미국", "OECD 17개국(D13-A 합성 국채)"])].round(4))

# %% [markdown]
# ### P2 원형 이동 — 해외 계열만 1..T−1 전수 이동(T2-D20 A, 결정적), 국내 eq·bd·infl·cash와의 시점 정렬만 깸
# 각 오프셋에서 본 격자와 같은 부트스트랩 인덱스(같은 시드)를 재사용. 금융 1차 근거는 [미확인](M2 2-7, 생태학 반론 존재). D20-B = 오프셋 무작위 199개(시드 SEED, 명세에 시드 없음 → 이탈 목록).

# %%
tic("P2")
arr, cols = C.arr_cols(k); TT = len(k)
FOR = ["us", "usB", "usHA", "usHB", "usHA_B17", "usHB_B17", "dev", "devHA", "devHB"]
pick = lambda port, **t: next(v for v in VK if v["port"] == port and all(v["tags"].get(a, "A") == b for a, b in t.items()) and all(x == "A" for a, x in v["tags"].items() if a not in t))
PV = [pick("③"), pick("③H"), pick("④"), pick("④H"), pick("④", D8="B"), pick("④H", D8="B")]
prow = []
for blk, src in bl_single(MAINB, "KR1991 eq"):
    idx = C.boot_idx(TT, NP, blk, SEED)
    p1 = C.summ(C.run_variant(arr, cols, idx, VK[0], "A", "A")[("A", "A")])["p"]
    for o in range(TT):
        sh = {c: np.roll(arr[:, cols[c]], o) for c in FOR}
        for v in PV:
            s = C.summ(C.run_variant(arr, cols, idx, v, "A", "A", shift=sh)[("A", "A")])
            prow.append(dict(블록=blk, 블록출처=src, 변형=v["name"], 이름표=v["label"], 오프셋=o, p=s["p"], P5=s["P5"], P50=s["P50"], **{"Δp_vs_①": s["p"] - p1}))
    print(src, f"{time.time() - TIMER['P2']:.0f}s", flush=True)
P2 = pd.DataFrame(prow); P2.to_csv(OUT / "T2_placebo_circshift.csv", index=False, encoding="utf-8-sig")
R20 = np.random.default_rng(SEED).choice(np.arange(1, TT), 199, replace=False)
def p2sum(d, offs, tag):
    a = d[d["오프셋"] == 0].iloc[0]; z = d[d["오프셋"].isin(offs)]
    q = z["Δp_vs_①"].quantile([.05, .5, .95]).to_numpy()
    return dict(오프셋집합=tag, 실제_p=a["p"], 실제_Δp=a["Δp_vs_①"], 이동_Δp_5=q[0], 이동_Δp_50=q[1], 이동_Δp_95=q[2],
                실제_Δp_백분위=float((z["Δp_vs_①"] <= a["Δp_vs_①"]).mean()), 실제가_5_95_밖=bool(a["Δp_vs_①"] < q[0] or a["Δp_vs_①"] > q[2]))
P2S = pd.DataFrame([dict(블록출처=s, 이름표=l, 변형=v, **p2sum(d, offs, tag)) for (s, l, v), d in P2.groupby(["블록출처", "이름표", "변형"], sort=False)
                    for offs, tag in ((range(1, TT), "A 전수 424"), (R20, "B 무작위 199"))])
P2S.to_csv(OUT / "T2_placebo_circshift_summary.csv", index=False, encoding="utf-8-sig"); display(P2S.round(4))
toc("P2")

# %% [markdown]
# ### P3 글라이드 vs 같은 평균 노출 상수 비중
# - 사전판: 상수 63.54%(mean5 잔여 −30~−1년 단순평균, 자료 무관). 사후판: 경로별 Σw_t·W_t/ΣW_t의 평균(W_t = 그 달 납입 뒤 금액) — **사후 정보**(Cederburg 외 2020 비판대로).
# - 같은 경로 위 짝 비교. D5-A·D6-A, 추천안(D7-A·D10-A, 한국 S = 33/67, 미국·OECD S = 자국 주식).

# %%
tic("P3")
def p3(grp, sname, arr, cols, idx, v5, blk, src):
    X = np.stack([arr[:, cols[nm]][idx] for nm in v5["comps"]], -1); R = C.port_R(X, v5["W"], v5["annual"])
    Wt = np.empty_like(R); w = np.zeros(len(R))
    for t in range(T):
        w = w + 1; Wt[:, t] = w; w = w * (1 + R[:, t])
    g = v5["W"][:, :-1].sum(1)                                               # 위험 꾸러미 비중 w_t
    post = float(((Wt * g).sum(1) / Wt.sum(1)).mean()); pre = float(C.glide("A").mean())
    S = v5["W"][:, :-1] / g[:, None]                                         # 꾸러미 안 구성(상수)
    out = [("⑤ 글라이드", v5)]
    for tag, c in (("상수(사전 63.54%)", pre), (f"상수(사후 {post:.4f})", post)):
        out.append((tag, dict(v5, W=np.column_stack([S * c, np.full(T, 1 - c)]), name=tag)))
    for tag, v in out:
        s = C.summ(C.run_variant(arr, cols, idx, v, "A", "A")[("A", "A")])
        p3r.append(dict(묶음=grp, 표본=sname, 블록출처=src, 비교=tag, 사후상수=post, **s))
p3r = []
v5k, v5e = pick("⑤"), next(v for v in VEB if v["port"] == "⑤" and C.is_rec(v))
for grp, sname, df, V, bl in SINGLE[:3] + [SINGLE[4]]:
    arr, cols = C.arr_cols(df)
    for blk, src in bl:
        p3(grp, sname, arr, cols, C.boot_idx(len(df), NP, blk, SEED), v5k if grp == "KR" else v5e, blk, src)
for blk, src in BL_POOL:
    idx, flat = C.pooled_idx(ol, NP, blk, SEED); arr, cols = C.arr_cols(flat)
    p3("OECD현지", "OECD 17개국(D13-A 합성 국채)", arr, cols, idx, v5e, blk, src)
P3 = pd.DataFrame(p3r); P3.to_csv(OUT / "T2_placebo_glide_const.csv", index=False, encoding="utf-8-sig")
display(P3.pivot_table(index=["표본", "블록출처"], columns="비교", values="p", sort=False).round(4))
toc("P3")

# %% [markdown]
# ### P4 원화 환산의 몫 — ③ 원화 실질(한국 CPI) vs 미국 USD 실질(미국 CPI)
# 분해이지 귀무가 아니다. 같은 부트스트랩 경로. (D5-B는 USD 판에 원화 현금이 맞지 않아 미산출.)

# %%
P4 = show[show["포트"].isin(["③", "③USD(P4)"]) & (show["묶음"] == "KR")].pivot_table(index=["표본", "블록출처"], columns="이름표", values=["p", "P5", "P50"], sort=False)
P4.to_csv(OUT / "T2_placebo_usd_vs_krw.csv", encoding="utf-8-sig"); display(P4.round(4))

# %% [markdown]
# ## 5. 하락장 쿠션 국면표 (명세 3-5, T2-D16 A 전부·B 20% 이상 부분합·C 1997·2008 강조)
# - 국면 경계 = 코스피 **종합** 월말(c1 PS 국면표), eq = **KOSPI200**(1991~) / 코스피 종합 가격(1980~ 판) — 불일치 각주.
# - 고점월 다음 달 → 저점월 누적. 저점 뒤 12·36개월 = **⬜ 기술용, 추천 아님**(정정 r1 4(b)). 저점 → 직전 고점 회복(코스피 종합 월말 ≥ 고점 수준인 첫 달)까지 누적도 함께.

# %%
ph = pd.read_csv(C.PHASE_F); ph = ph[ph["market"] == "KR"].copy()
kx = P.kospi_px_1980().loc[:P.US_END]
def cum(s, i0, i1):
    return np.nan if (i0 is None or i1 is None or i0 > i1 or i1 >= len(s)) else float((1 + s.iloc[i0:i1 + 1]).prod() - 1)
crow = []
for _, r in ph.iterrows():
    pk, tr = pd.Period(r["peak"], "M").to_timestamp("M"), pd.Period(r["trough"], "M").to_timestamp("M")
    rec = kx.loc[tr:][kx.loc[tr:] >= kx.loc[pk]]; rm = rec.index[0] if len(rec) else None
    for panel, nm, cols_ in ((k, "1991~ 패널", ["eq", "us_usd", "fx", "us", "usHA", "dev", "bd"]), (k8, "1980~ 주식판", ["eq", "us"])):
        if pk not in panel.index:
            continue
        ip, it = panel.index.get_loc(pk), panel.index.get_loc(tr); ir = panel.index.get_loc(rm) if rm is not None and rm in panel.index else None
        for c in cols_:
            s = panel[c]
            crow.append(dict(패널=nm, 고점=r["peak"], 저점=r["trough"], 하락폭=r["fall"], 하락20이상=r["fall"] <= -0.20, 강조_1997_2008=r["peak"] in ("1994-10", "2007-10"),
                             회복월=rm.strftime("%Y-%m") if rm is not None else "미회복", 계열=c, 고점_저점=cum(s, ip + 1, it),
                             저점후12_기술용=cum(s, it + 1, it + 12), 저점후36_기술용=cum(s, it + 1, it + 36), 저점_회복=cum(s, it + 1, ir)))
CU = pd.DataFrame(crow); CU.to_csv(OUT / "T2_cushion_phases.csv", index=False, encoding="utf-8-sig")
display(CU[CU["패널"] == "1991~ 패널"].pivot_table(index=["고점", "저점", "하락폭"], columns="계열", values="고점_저점", sort=False).round(3))
avg = []
for nm, d in CU.groupby("패널", sort=False):
    for tag, m in (("A 전부", d["하락20이상"] | True), ("B 20% 이상", d["하락20이상"]), ("C 1997·2008", d["강조_1997_2008"])):
        z = d[m]
        for c, dd in z.groupby("계열", sort=False):
            avg.append(dict(패널=nm, 집합=tag, 계열=c, 국면수n=len(dd), 고점_저점_평균=dd["고점_저점"].mean(), 저점_회복_평균=dd["저점_회복"].mean()))
CUA = pd.DataFrame(avg); CUA.to_csv(OUT / "T2_cushion_phase_means.csv", index=False, encoding="utf-8-sig")
display(CUA.pivot_table(index=["패널", "집합", "국면수n"], columns="계열", values="고점_저점_평균", sort=False).round(3))

# %% [markdown]
# ## 6. "후보를 바꾸면 결과가 바뀌나" (명세 8절 기준, 결과 전 고정 + 정정 r1)
# 한 결정의 후보만 바꾸고 나머지는 추천안. ⚠ 조건: ① 주 비교 Δp 부호 바뀜(|Δp| < 1.96·MC SE면 "0 근처" — 부호 변화로 안 침) ② 다섯 포트폴리오 손실확률 1위·꼴찌 바뀜
# ③ 주 표본(KR1991·PW 블록·D5-A·D6-A) p·P5·P50 변화 > MDE80(그 포트폴리오 수준 SD × 2.80) ④ 안 겹친 창 손실 여부 바뀜.
# 기준 ③은 주 표본 칸에만 적용(명세 "주 표본의 p·P5·P50").

# %%
FIVE = ["①", "②", "③", "④", "⑤"]
def sel(d, port, ov):
    """port의 칸: ov = {결정: 후보}. D5·D6는 열, 나머지는 변형 태그(태그 없는 포트 = 빈칸 → 그대로)."""
    d = d[(d["포트"] == port) & (d["D5"] == ov.get("D5", "A")) & (d["D6"] == ov.get("D6", "A"))]
    for t in TAGS:
        d = d[d[t].isin([ov.get(t, "A"), ""])]
    return d
def ctx_cells(d, ov):
    return {p: (x.iloc[0] if len(x := sel(d, p, ov)) == 1 else None) for p in FIVE + ["③H", "④H"]}
def rank_ends(c):
    ps = {p: c[p]["p"] for p in FIVE if c.get(p) is not None}
    lo, hi = min(ps.values()), max(ps.values())
    return frozenset(p for p, v in ps.items() if v == lo), frozenset(p for p, v in ps.items() if v == hi)
def compare(dec, cand, base, alt, main, hbase=None, halt=None, comps=COMPS):
    r = dict(결정=dec, 후보=cand)
    f1 = []
    for nm, a, b in comps:
        if any(x is None for x in (base.get(a), base.get(b), alt.get(a), alt.get(b))): continue
        d0, d1 = base[a]["p"] - base[b]["p"], alt[a]["p"] - alt[b]["p"]
        s0, s1 = np.hypot(base[a]["mc_se"], base[b]["mc_se"]), np.hypot(alt[a]["mc_se"], alt[b]["mc_se"])
        near = abs(d0) <= 1.96 * s0 or abs(d1) <= 1.96 * s1                 # Δ=0·SE=0(둘 다 p=0)도 0 근처
        f1.append((nm, d0, d1, near, (np.sign(d0) != np.sign(d1)) and not near))
    r["기준1_부호"] = any(x[4] for x in f1) if f1 else None
    r["기준1_상세"] = "; ".join(f"{n} {a:+.4f}→{b:+.4f}{'(0근처)' if nr else ''}" for n, a, b, nr, _ in f1) or         "주 비교 없음; p 변화 " + ", ".join(f"{p} {base[p]['p']:.4f}→{alt[p]['p']:.4f}" for p in base if base.get(p) is not None and alt.get(p) is not None)
    if sum(base.get(p) is not None for p in FIVE) >= 2 and sum(alt.get(p) is not None for p in FIVE) >= 2:
        e0, e1 = rank_ends(base), rank_ends(alt); r["기준2_순위"] = e0 != e1; r["기준2_상세"] = f"1위(p 최저) {''.join(sorted(e0[0]))}→{''.join(sorted(e1[0]))}, 꼴찌(p 최고) {''.join(sorted(e0[1]))}→{''.join(sorted(e1[1]))}"
    else:
        r["기준2_순위"] = None; r["기준2_상세"] = "포트폴리오 2개 미만"
    if main:
        f3 = []
        for p in FIVE + ["③H", "④H"]:
            if base.get(p) is None or alt.get(p) is None: continue
            for m in ("p", "P5", "P50"):
                dv, th = alt[p][m] - base[p][m], mde(MAINB, "수준", p, m)
                if abs(dv) > th: f3.append(f"{p} {m} {dv:+.4f}>MDE {th:.4f}")
        r["기준3_MDE"] = bool(f3); r["기준3_상세"] = "; ".join(f3)
    else:
        r["기준3_MDE"] = None; r["기준3_상세"] = "주 표본 아님(적용 안 함)"
    if hbase is not None and halt is not None:
        f4 = [f"{p} {'손실' if hbase[p] else '비손실'}→{'손실' if halt[p] else '비손실'}" for p in hbase if p in halt and hbase[p] != halt[p]]
        r["기준4_창"] = bool(f4); r["기준4_상세"] = "; ".join(f4) or f"바뀜 없음({len(hbase)}개 포트)"
    else:
        r["기준4_창"] = None; r["기준4_상세"] = "해당 없음"
    r["⚠"] = any(bool(r[c]) for c in ("기준1_부호", "기준2_순위", "기준3_MDE", "기준4_창"))
    return r
BM = BOOT[BOOT["경로수"] == NP]
def boot_ctx(sname, blk, grp="KR"):
    return BM[(BM["묶음"] == grp) & (BM["표본"] == sname) & np.isclose(BM["블록"], blk)]
def hist_flags(sname, ov, grp="KR"):
    d = NON[(NON["묶음"] == grp) & (NON["표본"] == sname)]
    d = d[d["시작"] == d["시작"].min()]                                    # 첫 안 겹친 창(한국은 1개뿐)
    return {p: bool(x["손실"].iloc[0]) for p in FIVE + ["③H", "④H"] if len(x := sel(d, p, ov)) == 1}
SROWS = []
KRS = [(s, bl) for _, s, _, _, bl in SINGLE[:3]]
for s, bl in KRS:
    main_blk = bl[0][0]
    for dec, cands in (("D5", "BC"), ("D6", "B"), ("D7", "B"), ("D8", "B"), ("D9", "BC"), ("D10", "B"), ("D11", "B"), ("D17", "B")):
        for cand in cands:
            for blk, src in bl:
                d = boot_ctx(s, blk); main = s == "KR1991" and np.isclose(blk, MAINB)
                hb, ha = (hist_flags(s, {}), hist_flags(s, {dec: cand})) if np.isclose(blk, main_blk) else (None, None)
                SROWS.append(dict(맥락=f"{s} {src}", **compare(f"T2-{dec}", cand, ctx_cells(d, {}), ctx_cells(d, {dec: cand}), main, hb, ha)))
    for blk, src in bl[1:]:
        SROWS.append(dict(맥락=f"{s} {src} vs {bl[0][1]}", **compare("T2-D2", src, ctx_cells(boot_ctx(s, bl[0][0]), {}), ctx_cells(boot_ctx(s, blk), {}), s == "KR1991")))
for s, bl in KRS[1:]:
    SROWS.append(dict(맥락=f"{s} vs KR1991 (각 PW)", **compare("T2-D3", s, ctx_cells(boot_ctx("KR1991", MAINB), {}), ctx_cells(boot_ctx(s, bl[0][0]), {}), True,
                                                                  hist_flags("KR1991", {}), hist_flags(s, {}))))
b80 = SINGLE[3][4][0][0]
SROWS.append(dict(맥락="KR1980(①③) vs KR1991 (각 PW)", **compare("T2-D3", "D(1980~)", {p: v for p, v in ctx_cells(boot_ctx("KR1991", MAINB), {}).items() if p in ("①", "③")},
                                                                ctx_cells(boot_ctx("KR1980", b80, "KR1980"), {}), True, {p: v for p, v in hist_flags("KR1991", {}).items() if p in ("①", "③")}, hist_flags("KR1980", {}, "KR1980"))))
d100 = BOOT[(BOOT["표본"] == "KR1991") & (BOOT["경로수"] == 100_000)]
SROWS.append(dict(맥락="KR1991 PW", **compare("T2-D4", "B(100,000)", ctx_cells(boot_ctx("KR1991", MAINB), {}), ctx_cells(d100, {}), True)))
uA, uB = SINGLE[5][4][0][0], SINGLE[6][4][0][0]
SROWS.append(dict(맥락="US원화 ③ (각 PW)", **compare("T2-D12", "B(1980-03~, N2 한국은행 1차)", ctx_cells(boot_ctx("US원화 D12-A", uA, "US원화"), {}), ctx_cells(boot_ctx("US원화 D12-B", uB, "US원화"), {}), False,
                                                 hist_flags("US원화 D12-A", {}, "US원화"), hist_flags("US원화 D12-B", {}, "US원화"))))
for s, bl, grp in (("US원화 D12-A", SINGLE[5][4], "US원화"), ("US원화 D12-B", SINGLE[6][4], "US원화"), ("KR1980", SINGLE[3][4], "KR1980")):
    SROWS.append(dict(맥락=f"{s} ③ {bl[0][1]}", **compare("T2-D17", "B", ctx_cells(boot_ctx(s, bl[0][0], grp), {}), ctx_cells(boot_ctx(s, bl[0][0], grp), {"D17": "B"}), False,
                                                           hist_flags(s, {}, grp), hist_flags(s, {"D17": "B"}, grp))))
OEA, OEB = "OECD 17개국(D13-A 합성 국채)", "OECD+Swinkels(D13-B)"
O5 = [("⑤−②", "⑤", "②")]
for blk, src in BL_POOL[1:]:
    SROWS.append(dict(맥락=f"OECD현지 D13-A {src} vs 120", **compare("T2-D1", src, ctx_cells(boot_ctx(OEA, 120.0, "OECD현지"), {}), ctx_cells(boot_ctx(OEA, blk, "OECD현지"), {}), False, comps=O5)))
    fa, fb = ctx_cells(boot_ctx("French 21개국+미국", 120.0, "French달러"), {}), ctx_cells(boot_ctx("French 21개국+미국", blk, "French달러"), {})
    SROWS.append(dict(맥락=f"French ① {src} vs 120", 결정="T2-D1", 후보=src, 기준1_부호=None, 기준1_상세=f"① p {fa['①']['p']:.4f}→{fb['①']['p']:.4f} (포트 1개라 기준 1·2 해당 없음)", **{"⚠": False}))
for blk, src in BL_POOL:
    a = ctx_cells(boot_ctx(OEA, blk, "OECD현지"), {}); b = ctx_cells(boot_ctx(OEB, blk, "OECD현지"), {}); b["①"] = a["①"]
    SROWS.append(dict(맥락=f"OECD현지 {src}", **compare("T2-D13", "B(Swinkels 실측, 8개국 ~2022-12)", a, b, False, comps=O5)))
for tag, sub in P2S.groupby(["블록출처", "이름표", "변형"], sort=False):
    a_, b_ = sub.iloc[0], sub.iloc[1]
    SROWS.append(dict(맥락=f"P2 {tag[0]} {tag[2]}", 결정="T2-D20", 후보="B 무작위 199", 기준1_부호=None,
                      기준1_상세=f"실제 Δp 백분위 {a_['실제_Δp_백분위']:.3f}→{b_['실제_Δp_백분위']:.3f}, 5~95% 밖 {a_['실제가_5_95_밖']}→{b_['실제가_5_95_밖']}", **{"⚠": bool(a_["실제가_5_95_밖"] != b_["실제가_5_95_밖"])}))
for _, r in MV[MV["지표"] == "p"].iterrows():
    SROWS.append(dict(맥락=f"KR1991 {r['블록출처']} {r['비교']}", 결정="T2-D21", 후보="B 90%(3.24)", 기준1_부호=None,
                      기준1_상세=f"|Δp| {abs(r['차이']):.4f} vs MDE80 {r['MDE80']:.4f}·MDE90 {r['MDE90']:.4f}: {r['기술80']}→{r['기술90']}", **{"⚠": r["기술80"] != r["기술90"].replace("MDE90", "MDE80")}))
for dec, why in (("T2-D14", "A(미보고)만 — 다국가 ④ 근거·자료 미비(명세 추천)"), ("T2-D15", "A(17개국)만 — 분기 CPI 월 분할 근거 없음(명세 추천)"), ("T2-D16", "국면표는 손실확률 칸이 아니라 기준 1~4 미적용 — A·B·C 평균 나란히(5절)"),
                 ("T2-D18", "요약 순서만(판정 아님). 주 블록 = PW(정정 r1)"), ("T2-D19", "정정 r1로 B(200) 삭제 — 1,000만")):
    SROWS.append(dict(맥락="—", 결정=dec, 후보="—", 기준1_상세=why, **{"⚠": False}))
SF = pd.DataFrame(SROWS); SF.to_csv(OUT / "T2_sensitivity_flip.csv", index=False, encoding="utf-8-sig")
print("⚠ 결정 목록(후보·맥락별):")
display(SF[SF["⚠"]].groupby(["결정", "후보"]).agg(맥락수=("맥락", "size"), 맥락=("맥락", lambda x: " | ".join(x[:4]) + (" …" if len(x) > 4 else ""))))
print("결정별 ⚠ 칸 수 / 전체 칸 수:")
display(SF.groupby("결정")["⚠"].agg(["sum", "size"]))

# %% [markdown]
# ## 7. 그림 (그림마다 원자료 CSV 하나)

# %%
fig_d = show[show["포트"].isin(FIVE + ["③H", "④H"]) & ((np.isclose(show["블록"], 120.0) & show["묶음"].isin(["French달러", "OECD현지"])) | show["블록출처"].str.startswith("PW"))]
fig_d.to_csv(OUT / "T2_fig_loss_by_sample_data.csv", index=False, encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(11, 4.5)); xs = list(dict.fromkeys(fig_d["표본"])); cmap = dict(zip(FIVE + ["③H", "④H"], plt.cm.tab10.colors))
for j, p in enumerate(FIVE + ["③H", "④H"]):
    z = fig_d[fig_d["포트"] == p]
    ax.errorbar([xs.index(s) + (j - 3) * 0.09 for s in z["표본"]], z["p"], yerr=1.96 * z["mc_se"], fmt="o", ms=4, color=cmap[p], label=p, capsize=2)
ax.set_xticks(range(len(xs))); ax.set_xticklabels(xs, rotation=20, fontsize=8); ax.set_ylabel("손실확률 p (D5-A·D6-A)")
ax.set_title("표본 × 포트폴리오 손실확률(단일국 PW 블록, 다국가 120). 막대 = MC 오차 ±1.96·SE(표본 불확실성 아님)"); ax.legend(ncol=7, fontsize=8); fig.tight_layout()
fig.savefig(OUT / "T2_fig_loss_by_sample.png", dpi=130); plt.show()
cd_ = MC[(MC["D5"] == "A") & (MC["D6"] == "A") & MC["변형"].isin([v["name"] for v in VEB + VEB_B if C.is_rec(v)] + ["①"])]
cd_.to_csv(OUT / "T2_fig_country_dots_data.csv", index=False, encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(11, 4.5))
for j, ((grp, lab), z) in enumerate(cd_.groupby(["묶음", "이름표"], sort=False)):
    ax.scatter(z["표본"].str.replace(r"_\d+(_s\d+)?$", "", regex=True), z["배수"], s=18, label=f"{grp} {lab}", alpha=.8)
ax.axhline(1, color="k", lw=.8); ax.set_ylabel("실질 금액 ÷ 실질 납입(안 겹친 30년 창)"); ax.tick_params(axis="x", rotation=60, labelsize=7); ax.legend(fontsize=7)
ax.set_title("다국가 나라별 안 겹친 창(전부, 알파벳순) — 실효 독립 단위는 1에 가까움"); fig.tight_layout(); fig.savefig(OUT / "T2_fig_country_dots.png", dpi=130); plt.show()
cu = CU[(CU["계열"].isin(["eq", "us"]))].pivot_table(index=["패널", "고점"], columns="계열", values="고점_저점", sort=False).reset_index()
cu.to_csv(OUT / "T2_fig_cushion_data.csv", index=False, encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(11, 4)); xx = np.arange(len(cu))
ax.bar(xx - .2, cu["eq"], .4, label="국내주식 eq"); ax.bar(xx + .2, cu["us"], .4, label="미국주식 원화(us)")
ax.set_xticks(xx); ax.set_xticklabels(cu["패널"].str[:5] + " " + cu["고점"], rotation=45, fontsize=7); ax.axhline(0, color="k", lw=.8); ax.legend()
ax.set_title("하락 국면(고점 다음 달→저점) 누적 — 국면 경계는 코스피 종합, eq는 KOSPI200(1991~)/코스피 가격(1980~)"); fig.tight_layout()
fig.savefig(OUT / "T2_fig_cushion.png", dpi=130); plt.show()

# %% [markdown]
# ## 8. 말할 수 있는 것 / 없는 것 (명세 9절 그대로)
# - 말할 수 있는 것: 표본·방법·후보별 p·P5·P50 숫자(CSV 칸과 함께), 한국 안 겹친 창 1개(사례), Δp vs MDE 기술("식별 안 됨"), 국면별 원화 환산 해외주식 수익(사례 n개), 위약 대비 차이.
# - 말할 수 없는 것: "30년 주식은 안전/위험" 판정, 겹치는 창 비율의 신뢰구간, 1만 경로 = 1만 증거, ACO 일시금 12%·미국 1.2%와 직접 비교(D5-C 칸만 '정의 맞춘 참고'), 미래 원화 약세 예측, 1965~1980 환율 쿠션 해석, 나라 하나를 대표로.
# - 쓰면 안 되는 문장: "30년이면 안전", "해외주식이 방패임이 검증됐다", "뚜렷한/크게/복제했다/검증 완료", "ACO는 한국 저축자를 다루지 않았다", "22개국 자료"(→ French 21개국 + 미국 합성), 1997 쿠션 1건의 일반화.
