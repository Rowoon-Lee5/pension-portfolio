# -*- coding: utf-8 -*-
"""후보 5 결과 문서 생성: run 폴더 CSV → 결과 md(+PDF). 표·숫자는 전부 CSV에서, 요약 문장은 cand5.sentence() 하나로.
호출: _gen_cand5.py --stage doc (build(run, md_to_pdf))."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from pension_lab import cand5 as C

DOC = Path(__file__).resolve().parents[2] / "docs" / "ideas" / "본연구후보_20261027" / "후보5_간단테스트"
OUT_MD = DOC / "후보5_간단테스트_결과_20261027.md"
M = 300_000                                   # 본문 표 = 월 30만 원(10·50만은 grid_stats.csv)
NAME = {"ps": "연금저축", "dep": "예금", "ny_cancel": "노란우산 해약", "ny_locked": "노란우산 묶임", "ny_old": "노란우산 노령",
        "ny_close": "노란우산 폐업"}
WHEN = {"p62": "62세(72개월)", "p70": "70세(168개월)", "wd36": "36개월째 인출", "wd60": "60개월째 인출"}
pair = lambda s: "{} < {}".format(*(NAME[x] for x in s.split("<")))
f3 = lambda x: "" if pd.isna(x) else f"{x:+.3f}"


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    return "\n".join(["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)] +
                     ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)])


def build(run: Path, md_to_pdf) -> Path:
    rd = lambda f: pd.read_csv(run / f)
    st, ch, mde = rd("grid_stats.csv"), rd("change_table.csv"), pd.read_csv(DOC / "data" / "cand5_mde_prerun.csv")
    base = st[(st.cell == "base") & (st.m == M)].merge(mde[["비교", "쌍", "asset", "mde"]], on=["비교", "쌍", "asset"], how="left")
    warn = ch[ch.m == M].groupby(["비교", "쌍"]).warn.any()
    te_all = rd("tax_effect.csv")
    tag = lambda r: C.sentence("", r.median_gap, r.mde).strip(" ()") or "MDE 이상"

    def loss_table(keys):
        b = base[base.비교.isin(keys)].copy()
        b["손해 경로"] = b.loss_n.astype(int).astype(str) + "/" + b.n.astype(int).astype(str)
        b["차이 중앙값"] = b.median_gap.map(f3); b["최악"] = b.worst.map(f3); b["MDE"] = b.mde.map(lambda x: f"{x:.3f}")
        b["판독"] = b.apply(tag, axis=1); b["⚠"] = [("⚠" if warn.get((k, s), False) else "") for k, s in zip(b.비교, b.쌍)]
        b["시점"] = b.비교.map(WHEN); b["비교 쌍"] = b.쌍.map(pair); b["사람"] = "(" + b.person + ")"
        return md_table(b[["시점", "비교 쌍", "asset", "사람", "손해 경로", "n_eff", "차이 중앙값", "최악", "MDE", "판독", "⚠"]]
                        .rename(columns={"asset": "자산"}))

    # 요약 5줄: 사람 셋 중 |중앙값| 최대 셀로 '식별 안 됨' 판단, ⚠은 그 시점·쌍에 경고 셀이 하나라도 있으면
    def line(k, s, a, text):
        g = base[(base.비교 == k) & (base.쌍 == s) & (base.asset == a)]
        r = g.loc[g.median_gap.abs().idxmax()]
        cnt = " · ".join(f"({p}) {int(x)}/{int(n)}" for p, x, n in zip(g.person, g.loss_n, g.n))
        meds = "/".join(f3(x) for x in g.median_gap)
        return C.sentence(f"{text}: {cnt} (연금저축−비교상품 차이 중앙값 (가)/(나)/(다) {meds}, MDE {r.mde:.3f}, 독립 구간 {int(r.n_eff)}개)",
                          r.median_gap, r.mde, warn=bool(warn.get((k, s), False)))

    g = lambda k, s_, a: base[(base.비교 == k) & (base.쌍 == s_) & (base.asset == a)].set_index("person")
    p70, d15 = g("p70", "ps<dep", "A"), ch[(ch.m == M) & (ch.cell == "D15:1980~가격") & (ch.비교 == "p70") & (ch.쌍 == "ps<dep") & (ch.asset == "A")].set_index("person")
    te36 = te_all[(te_all.m == M) & (te_all.비교 == "wd36") & (te_all.asset == "A") & (te_all.차이 == "(다)−(가)")].iloc[0]
    nyd = {k: g(k, "ny_cancel<dep", a) for k in ("wd36", "wd60") for a in ("A",)}
    nyc = ch[(ch.m == M) & ch.비교.isin(["wd36", "wd60"]) & (ch.쌍 == "ny_cancel<dep")]
    cr = rd("crash_cases.csv"); cr = cr[(cr.m == M) & (cr.asset == "A") & (cr.폭락달 == "2008-11") & (cr.H == 36)].set_index("person")
    summ = [line("p62", "ps<dep", "A", "62세(72개월) 평가에서 월 30만 원·주식 100% 연금저축이 예금보다 적었던 1월 시작 연도 수"),
            C.sentence("70세(168개월) 평가에서 같은 조건의 연금저축은 1991~ 표본 1월 시작 경로 " + " · ".join(f"({p}) {int(r.n - r.loss_n)}/{int(r.n)}" for p, r in p70.iterrows())
                       + "에서 예금보다 많았다(가장 작은 차이 " + "/".join(f3(r.worst) for _, r in p70.iterrows()) + f", 독립 구간 {int(p70.n_eff.iloc[0])}개, MDE {p70.mde.iloc[0]:.3f}). "
                       + "1980~ 가격지수 표본(D15)에서는 예금보다 적었던 경로가 " + " · ".join(f"({p}) {int(r.loss_n)}/{int(r.n)}" for p, r in d15.iterrows()) + "였다",
                       p70.median_gap.abs().max(), p70.mde.iloc[0], warn=bool(warn.get(("p70", "ps<dep"), False))),
            line("wd36", "ps<dep", "A", f"36개월째 전부 꺼낼 때 연금저축(주식 100%)이 예금보다 적었던 시작 연도 수[세금 수준 차이: 같은 경로에서 (다)−(가) 연금저축 세후 차이 중앙값 {f3(te36['median'])}]"),
            C.sentence("36·60개월째 노란우산을 해약하면 월 30만 원·주식 100% 셀에서 예금보다 적었던 경로가 " + " / ".join(
                f"{WHEN[k]} " + " · ".join(f"({p}) {int(r.loss_n)}/{int(r.n)}" for p, r in v.iterrows()) for k, v in nyd.items())
                       + f"였다. 격자의 단일 결정 변경 {len(nyc)}칸에서 이 경로 수는 바뀐 칸이 {int((nyc.d_p.abs() > 1e-12).sum())}칸이고, 차이 크기는 "
                       + "·".join(sorted(nyc[nyc.warn].D.unique())) + "에서 MDE 이상 바뀌었다. 31~60회 환급 = 원금(2017 약관 별표3, 2026 신규 가입자 표 미확인) 가정 아래의 결과다",
                       warn=bool(nyc.warn.any())),
            C.sentence("기술용 사례(사후에 고른 날짜): 2008-11에 36개월째 전부 꺼내면(2005-12 시작) 원금 " + f"{int(cr.contrib.iloc[0]):,}원에 대해 연금저축 (가) {cr.ps['가']:,.0f}원 · (다) {cr.ps['다']:,.0f}원, "
                       + f"예금 {cr.dep['가']:,.0f}원, 노란우산 해약 (가) {cr.ny_cancel['가']:,.0f}원이었다(1월이 아닌 시작이라 세금 연도는 근사)")]

    # ⚠ 결정 표
    cs = ch[ch.m == M].groupby(["D", "후보"]).agg(경고셀=("warn", "sum"), 셀=("warn", "size"),
                                                최대Δ손해비율=("d_p", lambda x: x.abs().max()), 최대Δ중앙값=("d_med", lambda x: x.abs().max())).reset_index()
    cs["결정"] = cs.D.map(lambda d: C.DEC[d][0]); cs = cs.sort_values(["경고셀", "최대Δ손해비율"], ascending=False)
    for c in ("최대Δ손해비율", "최대Δ중앙값"):
        cs[c] = cs[c].map(lambda x: f"{x:.3f}")
    cs["경고/셀"] = cs.경고셀.astype(int).astype(str) + "/" + cs.셀.astype(str)

    # 표 3: 자산 A vs B (같은 경로·같은 사람)
    rows = []
    for k in C.HS:
        h = rd(f"base_hist_{k}.csv"); h = h[h.m == M].pivot_table(index=["path", "person"], columns="asset", values="ps").join(
            h[h.m == M].groupby(["path", "person"]).contrib.first())
        h = h.dropna(subset=["A", "B"]); x = (h.A - h.B) / h.contrib
        for p, g in x.groupby(level="person"):
            rows.append({"시점": WHEN[k], "사람": f"({p})", "A<B 경로": f"{int((g < 0).sum())}/{len(g)}",
                         "(A−B) 중앙값": f3(g.median()), "최소": f3(g.min()), "최대": f3(g.max())})
    t3 = pd.DataFrame(rows)

    cc = rd("crash_cases.csv"); cc = cc[(cc.m == M) & (cc.asset == "A")].copy()
    for c in ("contrib", "ps", "dep", "ny_cancel", "ny_close"):
        cc[c] = (cc[c] / 1e4).round(0).astype(int)
    cc = cc[["폭락달", "H", "path", "person", "contrib", "ps", "dep", "ny_cancel", "ny_close"]].rename(columns={
        "H": "개월", "path": "시작", "person": "사람", "contrib": "원금", "ps": "연금저축", "dep": "예금", "ny_cancel": "노란우산 해약", "ny_close": "노란우산 폐업"})

    te = te_all[te_all.m == M].copy(); te["시점"] = te.비교.map(WHEN)
    for c in ("min", "median", "max"):
        te[c] = te[c].map(f3)
    bs = rd("boot_stats.csv"); bs = bs[(bs.m == M) & (bs.asset == "A") & (bs.쌍 == "ps<dep")].copy()
    bs = bs.pivot_table(index=["비교", "person"], columns="블록", values="p_loss").reindex(columns=list(C.BOOT_BLOCKS)).round(3).reset_index()
    bs["비교"] = bs.비교.map(WHEN)

    dec = pd.DataFrame([{"ID": d, "결정": nm, "★(기준 셀)": next(iter(c)), "다른 후보": " / ".join(list(c)[1:])} for d, (nm, c) in C.DEC.items()])
    sha = hashlib.sha256((DOC / "data" / "cand5_mde_prerun.csv").read_bytes()).hexdigest()
    import subprocess
    gsha = hashlib.sha256(Path(__file__).read_bytes().replace(bytes([13, 10]), bytes([10]))).hexdigest()[:16]
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=DOC).stdout.strip()
    L = [
        "# 후보 5 간단 테스트 결과 — 50대(2026년 만 57세) 자영업자: 연금저축 vs 노란우산공제 vs 예금 (2026-10-27)",
        "",
        f"- 실행: `{run}` · 명세: `후보5_명세_결정표_20261027.md` + **정정 r1** · 사전기준 `후보5_사전기준_20261027.md` · MDE 사전 고정 sha256 `{sha}`.",
        f"- 문서 생성기 `_doc_cand5.py` sha256(LF) {gsha}…, 생성 시 HEAD {head}. TASIS·MDE 원본 사본: `D:\\pension-lab_data\\raw\\candidate5_20261027\\`, `D:\\pension-lab_data\\results\\candidate5_20261027\\cand5_mde_prerun.csv`(레포 data\\ 폴더는 gitignore).",
        "- 성격: **탐색용 기술**이다. 판정하지 않는다. 비율은 모두 누적 납입 대비다(예: −0.10 = 넣은 돈의 10%만큼 적음).",
        "- 이 문서의 표와 숫자는 `notebooks/candidate5/_doc_cand5.py`가 run 폴더 CSV에서 만들었다. 요약 문장은 `cand5.sentence()` 규칙을 따른다.",
        "- 주의: 규칙이 도착하기 전에 1차 실행(run_0)을 돌려 결과를 먼저 봤다. 일부 결정 후보와 ★ 변경(D10·D17)은 그 뒤에 정해졌다. 정정 r1 1절에 공개했다.",
        "",
        "## 시나리오 근거 (계산에는 쓰지 않음)",
        "",
        "- 국세청 국세통계(TASIS) 3-3-1 「종합소득세 확정신고 인원 현황」, 2024년 귀속(표 ID 20250103C01202541096, 2026-10-27 화면 조회): 확정신고 11,932,469명 = 기장 4,709,067 + 추계 4,655,034 + 비사업자 2,568,368. 원본 옮김 `data/tasis_3-3-1_2024귀속_전국_20261027.csv`.",
        "- 결정세액 0원인 사업소득자 수·비율, 50대·60대별 값, 결정세액 50만 원 이하 비율은 **원표를 찾지 못했다**(TASIS 목록 화면이 '연도정보가 존재하지 않습니다'로 비어 있음). 언론이 인용한 '2023년 귀속 1,148만 명 중 284만 명(24.7%) 결정세액 0원'은 원표 대조 전이다 → **미확인**.",
        "",
        "## ⚠ 후보를 바꾸면 결과가 바뀌는 결정 (월 30만 원 셀 기준)",
        "",
        "⚠ 기준(구현 그대로): 기준 셀(모든 결정 ★) 대비 손해 경로 **비율** 변화가 1/기준 경로 수 이상(경로 수가 같으면 = 손해 경로가 하나라도 다름)이거나, 차이 중앙값 변화가 MDE 이상. 경로 수가 달라지는 D14·D15·D16은 비율로 비교한다. 경고/셀 = ⚠가 붙은 칸 수 / 그 후보의 전체 칸 수(시점 × 쌍 × 자산 × 사람).",
        "",
        md_table(cs[["D", "결정", "후보", "경고/셀", "최대Δ손해비율", "최대Δ중앙값"]]),
        "",
        "## 5줄 요약",
        "",
        *[f"{i}. {s}" for i, s in enumerate(summ, 1)],
        "",
        "(괄호 안 '식별 안 됨' = 사람 셋 가운데 차이가 가장 큰 칸도 MDE보다 작음. '선택에 따라 달라짐' = 위 ⚠ 표에서 그 시점·쌍에 경고 칸이 있음 — 월 30만 원 셀에서는 " + f"{int(warn.sum())}/{len(warn)}개 시점·쌍 모두 해당하므로 이 꼬리표만으로는 결과끼리 구별되지 않는다. 요약에 월 30만 원·주식 100% 셀을 쓴 것은 결과를 본 뒤의 표시 선택이다. 다른 셀은 grid_stats.csv에 있다.)",
        "",
        "## 표 1. 끝까지 쌓아 둘 때 (62·70세, 월 30만 원)",
        "",
        "손해 경로 = 앞 상품이 뒤 상품보다 적었던 1월 시작 연도 수 / 전체 경로 수. 경로끼리 기간이 겹치므로 신뢰구간은 붙이지 않는다. n_eff = 안 겹치는 구간 수. "
        "62세 노란우산은 노령 지급 조건(120회 이상)이 안 돼 '해약하면'(이자 40%)과 '묶여 있음'(꺼낼 수 없음)을 둘 다 보인다. 이자 95% 값은 ⚠ 표의 D08 줄과 grid_stats.csv에 있다. "
        "노란우산 노령·폐업 지급은 퇴직소득세를 계산하지 않았다(세전 = 노란우산에 유리한 상한).",
        "",
        loss_table(["p62", "p70"]),
        "",
        "## 표 2. 중간에 전부 꺼낼 때 (36·60개월째, 월 30만 원)",
        "",
        "연금저축 = 연금외수령 16.5%(공제받은 원금 + 수익분). 노란우산 해약 = 별표3 환급(31~60회 원금 100%) − 기타소득세(D17). 노란우산 폐업 = 폐업 적용이율 적립액(퇴직소득세 전).",
        "",
        loss_table(["wd36", "wd60"]),
        "",
        "### 표 2-1. 폭락 달에 꺼낸 사례 (기술용, 만 원, 주식 100%)",
        "",
        "폭락 달 = KOSPI200 가격의 2008년·2020년 연중 최저 월말. 이 날짜는 나중에 알게 된 사실이므로 비교 기준으로 쓰지 않는다.",
        "",
        md_table(cc),
        "",
        "## 표 3. 자산 (A) 주식 100% vs (B) 주식·채권 50:50 (연금저축, 같은 경로, 월 30만 원)",
        "",
        "(A−B) = 두 자산 연금저축 세후 금액 차이 ÷ 누적 납입. (B)는 달력 1월마다 50:50으로 맞춘다.",
        "",
        md_table(t3),
        "",
        "## 세금 수준에 따른 차이 (연금저축 세후, 같은 경로, 월 30만 원)",
        "",
        md_table(te[["시점", "asset", "차이", "min", "median", "max"]].rename(columns={"asset": "자산", "min": "최소", "median": "중앙값", "max": "최대"})),
        "",
        "## 블록 부트스트랩 손해 비율 (연금저축 < 예금, 주식 100%, 월 30만 원, 10,000경로)",
        "",
        "과거 달을 묶음째 다시 뽑아 만든 가상 경로다. 평균 블록 길이는 세 후보를 나란히 둔다(정정 r1 BOOT). 과거 한 번의 경로를 다시 뽑은 것이라 새로운 독립 정보가 아니다.",
        "",
        md_table(bs.rename(columns={"비교": "시점", "person": "사람"})),
        "",
        "## 그림",
        "",
        "![그림 1](fig/fig1_p70_by_start.png)",
        "",
        "![그림 2](fig/fig2_withdraw.png)",
        "",
        "![그림 3](fig/fig3_boot_p70.png)",
        "",
        "## 이 결과로 말할 수 없는 것",
        "",
        "- 앞으로 손해 볼 확률. 과거 1991~2026년의 한 경로를 시작 연도만 바꿔 본 것이다. 안 겹치는 구간은 62세 5개, 70세 2개, 36개월 11개, 60개월 7개뿐이다.",
        "- 노란우산 노령·폐업 지급의 실제 세후 금액. 퇴직소득세를 계산하지 않았다.",
        "- 기초연금·건강보험료를 포함한 실제 가계 효과. 기초연금은 계산하지 않았고, 건보료는 D11 민감도로만 봤다.",
        "- 다른 나이, 다른 소득, 연금저축보험·IRP. 2026년 만 57세 자영업자와 연금저축펀드만 다뤘다.",
        "- (가) 결정세액 0인 사람이 노란우산에서 실제로 소득공제를 받았는지. D10의 두 후보로만 봤다(⬜ 회원 확인).",
        "- 이 기간 안에서도 '오래 둘수록 손해가 적다'는 일반화. 70세 비교는 독립 구간이 2개뿐이다.",
        "- 실제 노란우산의 과거 성과. 노란우산은 2007년에 생겼다. 1992년 시작 경로는 2026년 규칙을 과거 시장에 얹은 가상 설계다.",
        "",
        "### 알려진 근사·한계 (결과 감사 r1 MEDIUM)",
        "",
        "- 1월이 아닌 달에 시작한 경로(D14 모든 달, 폭락 사례 2005-12·2003-12·2017-04·2015-04 시작)는 공제 연도·환급 시점·인출한 해 처리를 '시작부터 12개월 묶음'으로 셌다. 실제 달력과 최대 11개월 어긋난다. 리밸런싱만 달력 1월이다.",
        "- D10 '한도초과만' 후보는 정의상 (가)에게 과세표준이 있다고 보지만, 해약세는 과세표준 0(6% 구간)으로 계산했다. 이 민감도 셀의 크기는 확정되지 않았다.",
        "- 해약환급률은 2017 약관 별표3이다. 제도규칙 113행에 '2026. 1. 1. 이후 가입자, 1~3회 납입 시 80% 등'이라는 단서가 있어 2026 신규 가입자 표는 다를 수 있다(미확인). 36·60개월 노란우산 해약 결과는 이 가정에 기대고 있다.",
        "- 1996-01~06 예금 금리(BEABAA211, 정기예금 전체)는 겹치는 1996-07~1999 구간에서 1년 정기예금(2113)보다 중앙값 0.695%p(평균 0.40%p) 낮다(결과 감사 r1 계산). 그래서 1997년 중반까지 예금 수익이 조금 낮게 잡힌다. 연금저축에 유리한 방향이다.",
        "- 노란우산 이율의 월 환산은 연복리 (1+y)^(1/12)로 했다. 원문으로 확인하지 않았다. 2026년 이율 3.2%·3.5% 후보는 격자에 없다.",
        "",
        "## [가정]·민감도 목록",
        "",
        md_table(dec),
        "",
        "계산하지 않은 것(coverage.csv에 '전체' 행으로 이유를 남김): " + " · ".join(f"{k} — {v}" for k, v in C.NOT_COMPUTED.items()),
        "",
        "박힌 선택: 월초 납입, 월말 평가, 지방세 = 소득세 × 1.1, 환급은 이듬해 5월 말 도착, 예금 사다리 = 직전 12개월 금리 균등 평균, 예금 중도해지 이율 = 만기 이율(예금에 유리), 이자 매월 과세 근사.",
        "",
        "## 재현",
        "",
        "`PYTHONPATH= PYTHONIOENCODING=utf-8 python notebooks/candidate5/_gen_cand5.py --stage check | mde | results | nb | doc`. 세부 표는 run 폴더 `grid_stats.csv`(모든 셀), `change_table.csv`(⚠ 판단), `coverage.csv`(빈칸 이유)에 있다.",
    ]
    text = "\n".join(L) + "\n"
    bad = [w for w in C.FORBID if w in "\n".join(summ)]
    assert not bad, bad
    OUT_MD.write_text(text, encoding="utf-8")
    return md_to_pdf(OUT_MD)
