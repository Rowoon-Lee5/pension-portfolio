"""포트폴리오 주제 04~07(원 연구 저장소 notebooks/portfolio/make_topics_a.py, 커밋 78f2b99를 이 저장소 경로에 맞춰 옮김).
04 T1 대출(새 계산: 담보부족 확률), 05 T3·T6 결정 나무, 06 T5, 07 T2+A. 계산·문장은 원 스크립트와 같고, 바꾼 것은 읽는 경로·쓰는 곳과
README 끝의 '그림·파일·실행' 절뿐이다.
실행: python 04_loan_vs_withdraw/notebooks/portfolio/make_topics_a.py [t1 t3t6 t5 t2a]
  - t3t6·t5: 저장소 results/ 만 읽음(원자료 없이 됨).
  - t1: PENSION_DATA_ROOT(원자료, DATA_SOURCES.md)가 있으면 부트스트랩을 다시 돌리고(12개월 값이 results/pilot7/T1_boot.csv와 같은지 assert),
        없으면 저장소 results/portfolio/T1_margin_boot.csv·T1_margin_interest.csv를 읽어 그림·README만 만든다.
  - t2a: 공시 글라이드·보수 입력(재배포 조건 미확인이라 저장소에 없음)을 $PENSION_DATA_ROOT/results/ 아래에서 읽어야 돈다.
  → <주제 폴더>/README.md, figures/, (t1) results/portfolio/
"""
import hashlib
import os
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "01_downturn_timing" / "notebooks" / "portfolio"), str(ROOT / "src")]
import make_figures as mf  # noqa: E402  (폰트·색 설정만 씀)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

BLUE, GREY, LGREY = mf.BLUE, mf.GREY, mf.LGREY
DATA = Path(os.environ["PENSION_DATA_ROOT"]) / "results" if os.environ.get("PENSION_DATA_ROOT") else None
P7 = r"pilot7_20261008"
GIT = "원 연구 저장소 make_topics_a.py 커밋 78f2b992ab8e11717f4a1eb29062525b1b7fd685을 옮김\n"
LOAN_CAP = 4000           # 만 원, 신한 한도 상한(신한투자증권 연금저축계좌 담보대출 안내, 1차 — DATA_SOURCES.md 6절)
D4, D5, D6, D7 = "04_loan_vs_withdraw", "05_two_buckets_free_rebalancing", "06_lumpsum_vs_dca", "07_tdf_glidepath_by_manager"
PUB = {  # 원 연구 결과 경로 → 이 저장소 경로(요약 결과만). 여기 없는 파일은 $PENSION_DATA_ROOT/results/ 에서 읽음
    **{rf"{P7}\{f}": f"{D4}/results/pilot7/{f}" for f in ("T1_boot.csv", "T1_events.csv", "T1_breakeven.csv")},
    **{rf"{P7}\{f}": f"{D5}/results/pilot7/{f}" for f in ("T3_buckets.csv", "T6_paired.csv")},
    **{rf"{P7}\{f}": f"{D6}/results/pilot7/{f}" for f in ("T5_french_hist.csv", "T5_hist.csv", "T5_french_boot.csv", "T5_boot.csv")},
    rf"{P7}\T2_panel_ext_reg.csv": f"{D7}/results/pilot7/T2_panel_ext_reg.csv",
    **{rf"pilot9_20261013\A_simple_20261017\{f}": f"{D7}/results/pilot9_A_simple/{f}" for f in ("L2b_boot_pairs.csv", "L1_common_pair_t.csv", "L1_real_nav_stats.csv")},
    **{rf"pilot9_20261013\A_window_mde_20261026\{f}": f"{D7}/results/pilot9_A_window_mde/{f}" for f in ("vintage_summary.csv", "common_window.csv")},
    r"pilot9_20261013\C_real_20261017\inputs\C2_check_index_vs_real_overlap.csv": f"{D7}/results/pilot9_C_real_inputs/C2_check_index_vs_real_overlap.csv",
}
LOG = []


def path(rel):
    if rel in PUB:
        return ROOT / PUB[rel]
    if DATA is None:
        sys.exit(f"{rel}: 저장소에 없는 입력(재배포 조건 미확인) — PENSION_DATA_ROOT를 설정해야 합니다(DATA_SOURCES.md).")
    return DATA / rel.replace("\\", "/")


def read(rel, **kw):
    p = rel if isinstance(rel, Path) else path(rel)
    df = pd.read_csv(p, **kw)
    LOG.append(f"{p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else '$PENSION_DATA_ROOT/results/' + rel.replace(chr(92), '/')}"
               f"\tsha256={hashlib.sha256(p.read_bytes()).hexdigest()}\trows={len(df)}")
    return df


def save(fig, name, data):
    for ext in ("png",) if FIG.parent.name == D7 else ("png", "svg"):   # 07 svg는 선 좌표에 공시 글라이드 값이 그대로 남아 뺌(공개 감사 F2)
        fig.savefig(FIG / f"{name}.{ext}")
    plt.close(fig)
    data.to_csv(FIG / f"{name}_data.csv", index=False, encoding="utf-8-sig")
    (FIG / f"{name}_source.txt").write_text("\n".join(LOG) + f"\n생성: {D4}/notebooks/portfolio/make_topics_a.py, {GIT}", encoding="utf-8")
    LOG.clear()


def head(fig, title, sub, note):
    """mf.head와 같은 모양, 제목이 두 줄이면 부제를 그만큼 내림."""
    fig.suptitle(title, x=0.02, ha="left", fontsize=15, fontweight="bold", y=0.975, va="top", linespacing=1.3)
    fig.text(0.02, 0.905 - 0.05 * title.count("\n"), sub, fontsize=9.5, color="#444", va="top", linespacing=1.4)
    fig.text(0.02, 0.012, note, fontsize=7.2, color="#666", linespacing=1.4)


NOTE = ("본문의 '파일럿 T1·T3·T5·T6·T2', '10월 19일 A' 같은 이름은 원 연구 저장소의 분석 이름이고, 그 결과 파일은 이 폴더 `results/`에 있습니다. "
        "'문서'·'포트폴리오 문서'는 원 연구 저장소의 요약 문서(이 저장소에 없음), '9번 주제'는 원 연구 저장소의 다른 주제입니다.")
RUN = (f"실행: 저장소 루트에서 `python {D4}/notebooks/portfolio/make_topics_a.py {{k}}`{{extra}}. "
       "파일럿 원 계산(`notebooks/` 아래)은 DataGuide 원자료가 필요합니다(루트 README '재현 방법' 3, `../DATA_SOURCES.md`).")
TAIL = {
    D4: """
## 그림

![대출 금액·기간표](figures/fig_T1_대출_금액기간표.png)

## 파일

- `figures/`: 그림(`.png`·`.svg`), 그림 숫자(`_data.csv`), 읽은 결과 파일 sha256(`_source.txt`).
- `results/portfolio/`: `T1_margin_boot.csv`(표본·기간·포트폴리오·블록·빌리는 기간·금액별 담보부족 확률과 대출이 쌀 확률, 1만 경로 비율), `T1_margin_interest.csv`(이자를 원금에 더한 예시 1칸).
- `results/pilot7/`: 파일럿 T1 결과 — `T1_boot.csv`(대출 3종·금리 2방식의 '대출이 쌀 확률'), `T1_events.csv`(실제 약세장 진입 사건별 12개월 수익·최저), `T1_breakeven.csv`(손익분기 수익률). 모두 요약 표입니다.
- 코드: `notebooks/portfolio/make_topics_a.py`(04~07 공용, 그림·README), `notebooks/pilot7/T1_해지대신꺼내기.py`(파일럿 T1, 공통 모듈 `pilot7`·`bootstrap`).
- RUN1

NOTE

---
**English summary.** Should a Korean pension-savings holder who needs cash borrow against the account instead of withdrawing? Using a block bootstrap of past monthly returns (Korea 2004–, 1991–; US 1965–) with 2026 tax rules and one broker's loan terms, borrowing for 12 months was usually cheaper than withdrawing tax-deducted money, but close to a coin flip against withdrawing non-deducted principal. Borrowing the full 50% limit carried a margin-shortfall (top-up or forced sale) probability of up to about 9% over 12 months depending on the sample; borrowing 30% or less kept it at 0.2% or below. Figures are resampled history, not forecasts. Not investment advice.
""".replace("RUN1", RUN.format(k="t1", extra=" — 원자료가 없으면 저장된 `results/portfolio/` CSV로 그림·README만, `PENSION_DATA_ROOT`가 있으면 부트스트랩부터 다시 돌리고 12개월 값이 `results/pilot7/T1_boot.csv`와 같은지 확인")),
    D5: """
## 그림

![결정 나무](figures/fig_T3T6_결정나무.png)

## 파일

- `figures/`: 그림(`.png`·`.svg`), 그림 숫자(`_data.csv`: 잎·환급금 사용법별 2004~·1991~ 범위, 1~4년 보유 값), 읽은 결과 파일 sha256(`_source.txt`).
- `results/pilot7/`: `T3_buckets.csv`(표본·보유기간·자산·인출 시점·계좌·환급 지연별 '연금저축이 일반계좌보다 나은 시작 월 비율'과 세후배수 중앙값), `T6_paired.csv`(리밸런싱 비용 차이의 부트스트랩 중앙값·95% 구간). 모두 요약 표입니다.
- 코드: `../04_loan_vs_withdraw/notebooks/portfolio/make_topics_a.py`(그림·README), `notebooks/pilot7/T3_두통설계.py`·`T6_공짜리밸런싱.py`(파일럿 원 계산, 공통 모듈 `pilot7`·`bootstrap`).
- RUN1

NOTE

---
**English summary.** Is a Korean pension savings account always better than a taxable brokerage account? Comparing after-tax outcomes of the same contribution for every historical start month (Korea, 2004– and 1991–), the answer depends on whether the saver gets the tax credit, the asset (Korean equity ETFs are tax-free on gains outside the account), when the money comes out (before 55 vs. as a pension), and what is done with the tax refund. Savers without a credit who withdraw Korean equity before 55 did better in the taxable account; US equity taken as a pension favoured the pension account for every group. The benefit of tax-free rebalancing inside the account was small. The display rule of the decision tree was set after seeing pilot results. Not investment advice.
""".replace("RUN1", RUN.format(k="t3t6", extra=" — 저장소 `results/`만 읽어 원자료 없이 됩니다")),
    D6: """
## 그림

![목돈 한 번에 대 나눠 넣기](figures/fig_T5_목돈_나눠넣기.png)

## 파일

- `figures/`: 그림(`.png`·`.svg`), 그림 숫자(`_data.csv`), 읽은 결과 파일 sha256(`_source.txt`).
- `results/pilot7/`: `T5_french_hist.csv`·`T5_hist.csv`(과거 창 승률·Wilson·나라 묶음 부트스트랩 구간), `T5_french_boot.csv`·`T5_boot.csv`(부트스트랩 승률·확실성등가 차이). 모두 요약 표입니다.
- 코드: `../04_loan_vs_withdraw/notebooks/portfolio/make_topics_a.py`(그림·README), `notebooks/pilot7/T5_이전후진입.py`(파일럿 원 계산, 공통 모듈 `pilot7`·`bootstrap`).
- RUN1

NOTE

---
**English summary.** When a lump sum moves into a pension fund, should it go in at once or over three months? In non-overlapping one-year windows across 22 (USD) and 17 (local-currency) countries, investing at once won 59–66% of the time, and 64–66% in windows that started at a market peak; single-country peak windows were few and mixed. For a highly risk-averse investor (relative risk aversion 10), spreading the money had a higher certainty-equivalent return in every sample for an all-equity portfolio, but not for every balanced-portfolio cell. Not investment advice.
""".replace("RUN1", RUN.format(k="t5", extra=" — 저장소 `results/`만 읽어 원자료 없이 됩니다")),
    D7: """
## 그림

![운용사별 글라이드패스와 실제 − 계산](figures/fig_T2A_운용사별_글라이드.png)

## 파일

- `figures/`: 그림(`.png`만), 그림 숫자(`_data.csv`: 오른쪽 '실제 − 계산' 점·선과 30년 금액 비만), 읽은 결과 파일 sha256(`_source.txt`). 왼쪽 선의 공시 글라이드패스 값은 넣지 않았습니다(금융투자협회·운용사 공시, 재배포 조건 미확인 — `../DATA_SOURCES.md`). `.svg`는 선 좌표에 그 값이 그대로 남아 넣지 않았습니다.
- `results/pilot9_A_simple/`: `L2b_boot_pairs.csv`(운용사 쌍별 30년 금액 비 부트스트랩 요약), `L1_common_pair_t.csv`(공통 기간 쌍별 월 수익 차 t), `L1_real_nav_stats.csv`(운용사별 실제 연수익·변동성·낙폭 요약).
- `results/pilot9_A_window_mde/`: `vintage_summary.csv`(빈티지별 구별 가능 최소 차이), `common_window.csv`(빈티지별 공통 기간).
- `results/pilot9_C_real_inputs/`: `C2_check_index_vs_real_overlap.csv`(실제 기준가 대 '공시 비중 × 지수' 계산의 상관·평균차·추적오차, 시차 0~2일).
- `results/pilot7/`: `T2_panel_ext_reg.csv`(19개 운용사 패널 회귀). 모두 요약 표이고 기준가·보수·글라이드 원값은 없습니다.
- 코드: `../04_loan_vs_withdraw/notebooks/portfolio/make_topics_a.py`(그림·README), `notebooks/pilot9/_gen_A_simple.py`·`_gen_A_window_mde.py`(원 계산 노트북 생성기), `notebooks/pilot7/T2_같은빈티지괴리.py`(패널), 입력 생성은 `../01_downturn_timing/notebooks/pilot9/_build_C_real_inputs.py`. 두 생성기는 이 저장소 구조에 맞춰 경로만 고쳤습니다(`_build_C_real_inputs.py`를 `../01_downturn_timing/notebooks/pilot9/`에서 import). 고친 뒤 import 경로가 풀리는 것까지만 확인했고 전체 실행은 하지 않았습니다(실행하면 `$PENSION_DATA_ROOT/results/` 아래 결과를 다시 씀). 기준가·보수 받는 코드는 `../src/pension_lab/fetch/`(`kofia_tdf.py`·`kofia_h_uh_nav.py`·`tdf_fee_extract.py`·`tdfext_fee_extract.py`).
- RUN1

NOTE

---
**English summary.** Target-date 2055 funds from Korea's five largest managers follow different disclosed glide paths; held exactly as disclosed, they would end 30 years apart by a factor of about 1.0–1.2 in simulation. But actual returns deviated from a 'disclosed weights × indices − fee' replica by several percentage points a year, and two years of common history can only distinguish annual differences of roughly 9–10 pp. Within the same vintage, a 19-manager panel did not find differences in crash losses explained by the disclosed risky-asset share (across vintages the share does line up with losses). Short return rankings therefore say little about manager differences. Not investment advice.
""".replace("RUN1", RUN.format(k="t2a", extra=" — 공시 글라이드·보수 입력(`pilot9_20261013/A_simple_20261017/L2_inputs_glide_fee_by_month.csv`, `pilot9_20261013/decisions_survey/D1_glide_2055_annual.csv`)이 저장소에 없어 `PENSION_DATA_ROOT`의 `results/` 아래에 있어야 돕니다")),
}
TAIL = {k: v.replace("NOTE", NOTE) for k, v in TAIL.items()}


def readme(o, title, **sec):
    """한 쪽 요약. 숫자는 모두 호출한 함수가 결과 파일에서 읽어 넣은 값. 끝에 이 저장소용 '그림·파일·실행' 절(TAIL)."""
    body = "\n\n".join(f"## {k.replace('_', ' ')}\n\n{v.strip()}" for k, v in sec.items())
    title = f"{o.name[:2]}. " + title.split(". ", 1)[1].replace(" + 5. ", " + ")   # 원 주제 번호 → 이 저장소 폴더 번호
    (o / "README.md").write_text(f"# {title}\n\n{body}\n\n{TAIL[o.name].strip()}\n\n_생성: {D4}/notebooks/portfolio/make_topics_a.py "
                                 f"(숫자는 결과 CSV에서 읽어 자동으로 채움)_\n", encoding="utf-8")


def out(sub):
    global FIG
    o = ROOT / {"01_해지대신대출": D4, "02_두통설계_공짜리밸런싱": D5, "04_목돈_vs_나눠넣기": D6, "07_운용사별_2055TDF": D7}[sub]
    FIG = o / "figures"
    FIG.mkdir(parents=True, exist_ok=True)
    return o


# ── 1번 T1: 담보대출 담보부족(반대매매) 확률 + 금액·기간별 비교표 ─────────────────
def t1():
    from pension_lab import pilot7 as P
    from pension_lab.bootstrap import paired_resample_paths
    o = out("01_해지대신대출")
    LOAN = "신한 연금저축담보 5.00%"
    L, LTV, MAINT, t = P.LOAN[LOAN], P.LOAN_LTV, P.LOAN_MAINT, P.PENSION_UNDER70
    assert (L, LTV, MAINT, P.LOAN_TERM_M) == (0.05, 0.5, 1.4, 12)
    FR = [0.1, 0.2, 0.3, 0.4, 0.5]            # 꺼낼 금액 = 계좌 평가액 대비(0.5 = 한도)
    HS = [3, 6, 12]                           # 12 = 대출 기간(1차). 3·6 = 만기 전 상환(중도상환수수료 미확인 → 0)
    old = read(rf"{P7}\T1_boot.csv")
    old = old[(old["대출"] == LOAN) & (old["대출금리"] == "2026 고정")]
    RP = o / "results" / "portfolio"
    if DATA is None:                          # 원자료 없음 → 저장소에 넣은 이 계산의 결과를 읽어 그림·README만
        d = read(RP / "T1_margin_boot.csv", float_precision="round_trip")
        ic = read(RP / "T1_margin_interest.csv", float_precision="round_trip").iloc[0]
        ic = dict(따로=ic["P(담보부족) 이자 따로"], 가산=ic["P(담보부족) 이자 원금 가산"])
    else:
        rows = []
        for sname, r in P.samples().items():      # T1 노트북과 같은 순서·같은 호출(시드 P.SEED, 경로 P.NP)
            tags = [("전체", r)] + ([("2024년까지", r.loc[:P.PRE])] if sname == "KR 2004~" else [])
            for tag, rr in tags:
                for name, w in {k: P.MIX[k] for k in ("주식100", "60/40")}.items():
                    prr = P.mix_ret(rr, w); b = round(P.pw_block(prr), 2)
                    blocks = sorted({(1.0, "iid" if b > 1 else "iid (=PW 추정 1)"), (12.0, "12개월")} | ({(b, "PW(그 표본)")} if b > 1 else set()))
                    for blk, src in blocks:
                        Rp, _ = paired_resample_paths([prr, rr["cash"]], P.NP, P.LOAN_TERM_M, blk, P.SEED)
                        V = np.cumprod(1 + Rp, axis=1)                 # 월말 계좌 평가액(시작 = 1)
                        low = np.minimum.accumulate(V, axis=1)
                        if (sname, tag, name, blk) == ("KR 2004~", "전체", "주식100", 12.0):   # 이자를 원금에 더한 예시(감사 M1·LOW-R1)
                            thr = MAINT * 0.5 * (1 + L * np.arange(1, P.LOAN_TERM_M + 1) / 12)
                            ic = dict(따로=(low[:, -1] <= MAINT * 0.5).mean(), 가산=(V <= thr).any(axis=1).mean())
                        for h in HS:
                            R = V[:, h - 1] - 1
                            c1, c2 = 1 + R * (1 - t), (1 + R) * (1 - t) / (1 - P.ETC_TAX)   # T1 cost_table ①·② 그대로
                            loan = 1 + L * h / 12
                            if h == 12:                                 # 회귀: T1_boot와 같은 값이어야 함
                                m = old[(old["표본"] == sname) & (old["기간"] == tag) & (old["포트폴리오"] == name) & (old["평균블록"] == blk)]
                                assert len(m) == 1 and abs(m["P(대출<①)"].iloc[0] - (c1 > loan).mean()) < 1e-12 \
                                    and abs(m["P(대출<②)"].iloc[0] - (c2 > loan).mean()) < 1e-12, (sname, tag, name, blk)
                            for f in FR:
                                brk = low[:, h - 1] <= MAINT * f                # 평가액 ≤ 140% × 대출 (T1 사건 판정과 같은 ≤)
                                rows.append({"표본": sname, "기간": tag, "포트폴리오": name, "평균블록": blk, "블록출처": src,
                                             "기간(개월)": h, "꺼낼 금액(평가액 대비)": f, "담보부족 기준 낙폭": MAINT * f - 1,
                                             "P(담보부족)": brk.mean(), "P(대출<② 공제분 인출)": (c2 > loan).mean(),
                                             "P(대출<② 이고 담보부족 없음)": ((c2 > loan) & ~brk).mean(),
                                             "P(대출<① 비공제분 인출)": (c1 > loan).mean()})
        d = pd.DataFrame(rows)
        d["MC SE(담보부족)"] = np.sqrt(d["P(담보부족)"] * (1 - d["P(담보부족)"]) / P.NP)
        d.to_csv(RP / "T1_margin_boot.csv", index=False, encoding="utf-8-sig")
        assert abs(ic["따로"] - d[(d["표본"] == "KR 2004~") & (d["기간"] == "전체") & (d["포트폴리오"] == "주식100") & (d["평균블록"] == 12.0)
                                  & (d["기간(개월)"] == 12) & (d["꺼낼 금액(평가액 대비)"] == 0.5)]["P(담보부족)"].iloc[0]) < 1e-12
        pd.DataFrame([dict(표본="KR 2004~", 포트폴리오="주식100", 평균블록=12.0, **{"기간(개월)": 12, "꺼낼 금액(평가액 대비)": 0.5,
                      "P(담보부족) 이자 따로": ic["따로"], "P(담보부족) 이자 원금 가산": ic["가산"]})]).to_csv(RP / "T1_margin_interest.csv", index=False, encoding="utf-8-sig")
        (RP / "T1_margin_boot_source.txt").write_text(
            f"생성: {D4}/notebooks/portfolio/make_topics_a.py t1(). seed={P.SEED}, 경로={P.NP}, paired_resample_paths(T1과 같은 호출).\n"
            f"회귀: 기간 12개월의 P(대출<①)·P(대출<②)가 {D4}/results/pilot7/T1_boot.csv({LOAN}, 2026 고정) 22행과 1e-12 안에서 같음(assert 통과).\n"
            f"담보부족 = 대출 기간 중 어느 월말 평가액 ≤ 1.4 × 대출원금(이자는 따로 낸다고 봄; 이자를 원금에 더하면 확률이 높아짐 — 한국 2004~ 블록12 {ic['따로']:.4f}→{ic['가산']:.4f}, T1_margin_interest.csv).\n"
            f"월말 값만 봄 → 달 안 장중 하락은 못 잡음(확률 과소 쪽).\n{GIT}", encoding="utf-8")
    p1 = lambda x: f"{(Decimal(str(x)) * 100).quantize(Decimal('0.1'), ROUND_HALF_UP)}%"   # 0.0435 → 4.4%(float 서식은 4.3)
    IC = f"{p1(ic['따로'])}→{p1(ic['가산'])}"

    # 한 장 표: 주식100, 전체 기간, 표본별 블록 범위(최소~최대)
    s = d[(d["포트폴리오"] == "주식100") & (d["기간"] == "전체")]
    g = s.groupby(["표본", "기간(개월)", "꺼낼 금액(평가액 대비)"]).agg(
        담보부족_최소=("P(담보부족)", "min"), 담보부족_최대=("P(담보부족)", "max"),
        대출싸다_최소=("P(대출<② 공제분 인출)", "min"), 대출싸다_최대=("P(대출<② 공제분 인출)", "max"),
        싸고안전_최소=("P(대출<② 이고 담보부족 없음)", "min"), 싸고안전_최대=("P(대출<② 이고 담보부족 없음)", "max"),
        비공제_최소=("P(대출<① 비공제분 인출)", "min"), 비공제_최대=("P(대출<① 비공제분 인출)", "max")).reset_index()
    ev = read(rf"{P7}\T1_events.csv")
    ev = ev[(ev["상태"] == "완료") & (ev["포트폴리오"] == "주식100")]
    evs = ev.groupby("표본").agg(사건=("진입월", "size"), 반대매매위험=("반대매매 위험", lambda x: int(x.astype(str).eq("True").sum())),
                               해당월=("진입월", lambda x: ", ".join(ev.loc[x.index][ev.loc[x.index, "반대매매 위험"].astype(str).eq("True")]["진입월"].str[:7])))
    be = read(rf"{P7}\T1_breakeven.csv").set_index("Unnamed: 0").loc[LOAN]

    order = ["KR 2004~", "KR 1991~", "US 1965~"]
    lab = {"KR 2004~": "한국 2004~", "KR 1991~": "한국 1991~", "US 1965~": "미국 1965~"}
    rng = lambda a, b, k=0: f"{a * 100:.{k}f}" if f"{a * 100:.{k}f}" == f"{b * 100:.{k}f}" else f"{a * 100:.{k}f}~{b * 100:.{k}f}"

    def table(ax, cell, cols, colors):
        tb = ax.table(cell, colLabels=cols, cellColours=colors, loc="upper center", cellLoc="center", colLoc="center")
        tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.25)
        for (i, j), c in tb.get_celld().items():
            c.set_edgecolor(LGREY)
            if i == 0: c.set_height(c.get_height() * 1.8); c.set_text_props(fontweight="bold", color="#222")

    q = lambda k, h, f=0.5: g[(g["표본"] == k) & (g["기간(개월)"] == h) & (g["꺼낼 금액(평가액 대비)"] == f)].iloc[0]
    fig = plt.figure(figsize=(9, 7.6))
    ax1 = fig.add_axes([0.02, 0.53, 0.96, 0.17]); ax1.axis("off")
    ax1.set_title("① 무엇이 싼가: 대출이 인출보다 쌀 확률(%)", loc="left", fontsize=10, color=BLUE, fontweight="bold")
    c1, k1 = [], []
    for h in HS:
        c1.append([f"{h}개월" + (" *" if h < 12 else "")] + [rng(q(k, h).대출싸다_최소, q(k, h).대출싸다_최대) for k in order]
                  + [rng(q(k, h).비공제_최소, q(k, h).비공제_최대) for k in order])
        k1.append(["white"] + ["#DCE6F2" if q(k, h).대출싸다_최소 > 0.5 else "white" for k in order] + ["#DCE6F2" if q(k, h).비공제_최소 > 0.5 else "white" for k in order])
    table(ax1, c1, ["빌리는 기간"] + [f"공제분 인출 대비\n{lab[k]}" for k in order] + [f"비공제분 인출 대비\n{lab[k]}" for k in order], k1)
    ax2 = fig.add_axes([0.02, 0.15, 0.96, 0.28]); ax2.axis("off")
    ax2.set_title("② 얼마까지 빌려도 되나: 기간 안 담보부족(추가담보·반대매매) 확률(%)", loc="left", fontsize=10, color=BLUE, fontweight="bold")
    c2, k2 = [], []
    for f in FR:
        c2.append([f"{f:.0%}", f"{(MAINT * f - 1) * 100:.0f}%"] + [rng(q(k, h, f).담보부족_최소, q(k, h, f).담보부족_최대, 1) for h in (6, 12) for k in order])
        k2.append(["white"] * 2 + ["#DCE6F2" if q(k, h, f).담보부족_최대 < 0.01 else "white" for h in (6, 12) for k in order])
    table(ax2, c2, ["빌린 금액\n(평가액 대비)", "담보부족이 되는\n계좌 하락"] + [f"{h}개월 *\n{lab[k]}" if h < 12 else f"{h}개월\n{lab[k]}" for h in (6, 12) for k in order], k2)
    hi = g[(g["기간(개월)"] == 12) & (g["꺼낼 금액(평가액 대비)"] == 0.5)]
    lo = g[(g["기간(개월)"] == 12) & (g["꺼낼 금액(평가액 대비)"] <= 0.3)]
    head(fig, f"공제받은 돈을 꺼낼 바엔 대출이 대체로 싸다. 다만 한도(50%)를 다 빌리면\n12개월 안 담보부족 확률이 "
                 f"{hi.담보부족_최소.min() * 100:.1f}~{hi.담보부족_최대.max() * 100:.1f}%",
            f"연금저축 담보대출(신한, 연 {L:.2%}, 한도 평가액 {LTV:.0%}, 담보유지 {MAINT:.0%}) 대 인출, 주식 100%, 부트스트랩 1만 경로. 칸 = 블록 길이별 범위\n"
            f"파란 칸: ①은 모든 블록에서 대출이 쌀 확률 50% 초과, ②는 모든 블록에서 담보부족 1% 미만\n"
            f"평가액의 30% 이하를 12개월 빌리면 담보부족 확률 최대 {lo.담보부족_최대.max() * 100:.1f}%",
            "담보부족 = 대출 기간 중 월말 평가액 ≤ 140% × 대출(월말만 봄 → 달 안 장중 하락은 못 잡아 확률이 낮게 나올 수 있음).\n"
            f"이자는 따로 낸다고 봄(이자를 원금에 더하면 확률이 높아짐, 예: 한국 2004~ 블록12 한도 전액 12개월 {IC}).\n"
            "* 3·6개월 = 만기(365일) 전에 갚는 경우. 중도상환수수료는 확인하지 못해 0으로 둠(대출에 유리한 쪽). ①은 반대매매가 없다고 본 값.\n"
            f"손익분기(12개월): 계좌가 {-be['vs ② 공제분(16.5%)'] * 100:.1f}%보다 덜 잃으면 대출이 공제분 인출보다 쌈. 비공제분 = 공제받지 않은 원금(꺼내도 세금 없음).\n"
            "실제 약세장 진입(주식100, 한도 전액): " + "; ".join(f"{lab[k]} {evs.loc[k, '사건']}번 중 {evs.loc[k, '반대매매위험']}번 담보부족({evs.loc[k, '해당월']})" for k in order) +
            ".\n출처: pilot7_20261008 T1_boot·T1_events·T1_breakeven.csv + 이번 계산 T1_margin_boot.csv(같은 시드, 12개월 값 회귀 일치).")
    save(fig, "fig_T1_대출_금액기간표", g)
    allb = pd.read_csv(path(rf"{P7}\T1_boot.csv"))                  # 문서 범위 대조용(대출 3종·금리 2방식 전부)
    r2 = lambda k: rng(q(k, 12).대출싸다_최소, q(k, 12).대출싸다_최대) + "%"
    m12 = lambda k, f: rng(q(k, 12, f).담보부족_최소, q(k, 12, f).담보부족_최대, 1) + "%"
    readme(o, "1. 해지 대신 대출 — 급전이 필요할 때 연금저축을 깨지 말고 빌릴까",
        문제의식=f"""
연금저축에서 세액공제를 받은 돈을 꺼내면 16.5% 세금이 붙습니다. 그런데 계좌를 담보로 연 {L:.2%}에 빌리는 상품도 있습니다(신한투자증권, 한도 평가액의 {LTV:.0%}·최대 {LOAN_CAP:,}만 원, 담보유지비율 {MAINT:.0%}, 기간 365일).
대출은 세금이 없는 대신 이자가 나가고, 계좌가 많이 떨어지면 담보가 모자라 추가 담보를 넣거나 강제로 팔리는(반대매매) 위험이 있습니다.
""",
        한_일=f"""
- 파일럿 T1(10월 8일)의 부트스트랩을 그대로 다시 돌렸습니다(같은 시드 {P.SEED}, 경로 {P.NP:,}개, 한국 2004~·1991~, 미국 1965~). 12개월 결과가 기존 파일과 소수 12자리까지 같은지 확인했습니다.
- 새로 센 것은 두 가지입니다. ① 빌린 금액(평가액의 10~50%)마다, 기간 안 어느 월말에 평가액이 대출의 140% 아래로 내려간 경로의 비율(담보부족 확률). ② 3·6개월에 갚는 경우의 비용 비교.
- 결과: `T1_margin_boot.csv`(표본·포트폴리오·블록·기간·금액 전부), 그림 `fig_T1_대출_금액기간표`.
""",
        결과=f"""
- **공제받은 돈을 꺼내야 한다면 대출이 대체로 싸다.** 12개월, 주식 100% 기준 대출이 공제분 인출보다 쌀 확률: 한국 2004~ {r2('KR 2004~')}, 한국 1991~ {r2('KR 1991~')}, 미국 {r2('US 1965~')}. 계좌가 12개월 동안 {-be['vs ② 공제분(16.5%)'] * 100:.1f}%보다 덜 잃으면 대출이 쌉니다.
- **공제받지 않은 원금을 꺼낼 수 있다면 반반에 가깝다.** 같은 조건에서 대출이 쌀 확률 {s[s['기간(개월)'] == 12]['P(대출<① 비공제분 인출)'].min() * 100:.0f}~{s[s['기간(개월)'] == 12]['P(대출<① 비공제분 인출)'].max() * 100:.0f}%.
- **한도를 다 빌리면(평가액 50%) 12개월 안 담보부족 확률**: 한국 2004~ {m12('KR 2004~', 0.5)}, 한국 1991~ {m12('KR 1991~', 0.5)}, 미국 {m12('US 1965~', 0.5)}. 계좌가 30% 떨어지면 걸립니다.
- **평가액의 30% 이하만 빌리면** 12개월 담보부족 확률이 모든 표본·블록에서 {lo.담보부족_최대.max() * 100:.1f}% 이하였습니다(계좌가 58% 넘게 떨어져야 걸림).
- 실제 약세장 진입 때 한도를 다 빌렸다면(주식 100%): """ + "; ".join(f"{lab[k]} {evs.loc[k, '사건']}번 중 {evs.loc[k, '반대매매위험']}번 담보부족({evs.loc[k, '해당월']})" for k in order) + ".",
        말하면_안_되는_것="""
- "연금저축 담보대출은 안전하다" — 한도를 다 빌리면 2008년 같은 하락에서 담보부족이 실제로 났을 것입니다.
- "대출이 항상 싸다" — 공제받지 않은 원금을 꺼낼 수 있으면 반반이고, 계좌가 크게 떨어진 해에는 인출이 더 쌌습니다.
- 확률을 "앞으로 일어날 확률"로 말하기 — 과거 수익률을 다시 뽑은 값입니다.
""",
        한계="""
- 월말 값만 봐서 달 중간 장중 하락은 못 잡습니다(담보부족 확률이 낮게 나올 수 있음). 이자는 따로 낸다고 봤습니다. 이자를 원금에 더하면 담보부족 확률이 높아집니다(예: 한국 2004~ 주식100 블록12 한도 전액 12개월 IC_, `T1_margin_interest.csv`).
- 3·6개월 칸은 만기 전에 갚는 경우입니다. 중도상환수수료를 확인하지 못해 0으로 뒀습니다(대출에 유리한 쪽, ⬜ 확인 필요). 신한 상품 페이지 원문 스냅샷은 이번에 다시 받지 못했고, 조건은 파일럿 근거 대장(10월 8일, 1차 출처 https://www.shinhansec.com/siw/pension/saving-info/saving_account_service1/view.do, 2026.01.01 기준)의 값입니다. 한도 상한 CAP_은 평가액이 CAP2_을 넘을 때만 걸리고, 표는 평가액 대비 비율이라 영향이 없습니다.
- 대출이 쌀 확률은 반대매매가 없다고 본 값입니다. 반대매매가 나면 그때 판 금액에 세금이 붙어 대출 쪽 비용이 더 커집니다(`P(대출<② 이고 담보부족 없음)` 열 참고).
- 파일럿 T1의 다른 대출 2종과 '그때 금리' 방식은 이번 표에서 뺐습니다(연 5.00% 신한 조건만). 문서의 "0.67~0.96" 범위는 이들을 모두 합친 값입니다.
- 실제 약세장 진입 사건은 파일럿 T1 정의(직전 고점을 회복한 뒤에만 새 사건으로 셈)를 따라, 한국 1997년 외환위기 하락은 따로 세지 않았습니다.
- 2026년 세법·금리를 과거 수익률에 얹은 반사실이고, 미국 표본은 한국 세제를 미국 수익률에 얹은 것입니다.
""".replace("IC_", IC).replace("CAP2_", f"{LOAN_CAP / LTV:,.0f}만 원").replace("CAP_", f"{LOAN_CAP:,}만 원"))
    return dict(g=g, evs=evs, be=be, 문서대조_공제분=allb[["P(대출<②)"]].agg(["min", "max"]),
                문서대조_비공제분=allb.groupby("표본")["P(대출<①)"].agg(["min", "max"]))


# ── 2번 T3 + 5번 T6: 결정 나무 ────────────────────────────────────────────────
def t3t6():
    o = out("02_두통설계_공짜리밸런싱")
    b = read(rf"{P7}\T3_buckets.csv")
    V, SAME = "일반계좌보다 나은 비율", "같은 비율"
    assert (b[SAME] == 0).all()                     # 같은 칸 없음 → 일반계좌가 나은 비율 = 1 − 나은 비율
    CRED = {"16.5%": "공제통 16.5%", "13.2%": "공제통 13.2%", "못 받음": "비공제통"}   # 공제율 두 단계 모두(감사 HIGH-3)
    pick = lambda k, cred: k[k["통"] == "비공제통"] if cred == "못 받음" else k[k["통"].str.startswith(CRED[cred])]   # 환급 2·13개월 둘 다(T3 '두 끝값 모두', 감사 HIGH-2)
    leaves = []
    for cred in CRED:
        for asset in ("국내주식", "미국주식"):
            for ex in ("55세 전 인출(16.5%)", "55세 이후 연금(5.5%)"):
                k = pick(b[(b["자산"] == asset) & (b["인출"] == ex) & (b["h년"] >= 5)], cred)
                opts = {"": k} if cred == "못 받음" else {"환급금 같은 자산": k[k["통"].str.endswith("같은자산 일반계좌")],
                                                         "환급금 예금(CD)": k[k["통"].str.endswith("CD(세후)")]}
                rec, parts = set(), []
                for on, kk in opts.items():
                    rs = {s: (kk[kk["표본"] == s][V].min(), kk[kk["표본"] == s][V].max(), kk[kk["표본"] == s]["h년"].max()) for s in ("KR 2004~", "KR 1991~")}
                    lo, hi, _ = rs["KR 2004~"]
                    rk = "연금저축" if lo > 0.5 else "일반계좌" if hi < 0.5 else "갈림"   # 규칙: 2004~ 모든 보유기간에서 다수가 한쪽이면 그쪽
                    rec.add(rk)
                    parts.append(dict(옵션=on, 옵션추천=rk, **{f"{s} {n}": v for s, r in rs.items() for n, v in zip(("최소", "최대", "최대h"), r)}))
                short = pick(b[(b["자산"] == asset) & (b["인출"] == ex) & (b["h년"] < 5) & (b["표본"] == "KR 2004~")], cred)
                leaves.append(dict(공제=cred, 자산=asset, 시점=ex, 추천=rec.pop() if len(rec) == 1 else "갈림", 근거=parts,
                                   단기_최소=short[V].min() if len(short) else np.nan, 단기_최대=short[V].max() if len(short) else np.nan))
    p6 = read(rf"{P7}\T6_paired.csv")
    assert [p6[c].nunique() for c in ("포트폴리오", "기간(년)", "계좌", "전략")] == [2, 3, 2, 6] and len(p6) == 144
    t6 = {s: dict(n=len(d), 배제=int(d["0 배제(95%)"].astype(str).eq("True").sum()), holm=int((d["Holm형 조정(검정 아님)"] < 0.05).sum()),
                  lo10=d[d["기간(년)"] == 10]["중앙값"].min(), hi10=d[d["기간(년)"] == 10]["중앙값"].max())  # 이미 %p 단위
          for s, d in p6.groupby("표본")}

    N = len(leaves) - 1                         # 12잎: 공제 3 × 자산 2 × 시점 2
    fig = plt.figure(figsize=(10, 10.2))
    ax = fig.add_axes([0.01, 0.10, 0.98, 0.65]); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(-1.8, N + 0.4)
    box = lambda x, y, s, **kw: ax.text(x, y, s, ha="center", va="center", fontsize=kw.pop("fs", 8.5),
                                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=GREY, lw=0.8), **kw)
    line = lambda x0, y0, x1, y1: ax.plot([x0, x0 + 0.2, x0 + 0.2, x1], [y0, y0, y1, y1], color=GREY, lw=0.8, zorder=0)
    pr = lambda a, b: f"{a * 100:.0f}%" if f"{a * 100:.0f}" == f"{b * 100:.0f}" else f"{a * 100:.0f}~{b * 100:.0f}%"
    box(0.5, N / 2, "세액공제를\n받나?", fs=9.5, fontweight="bold")
    col = {"연금저축": BLUE, "일반계좌": "#333", "갈림": "#777"}
    word = {"연금저축": "연금저축", "일반계좌": "일반계좌", "갈림": "갈림(보유기간·환급 시점에 따라)", "갈림0": "갈림(보유기간에 따라)"}   # 갈림0 = 환급 없는 '못 받음' 잎(LOW-R4)
    CL = {"16.5%": "받음 16.5%\n(총급여 5,500만 이하)", "13.2%": "받음 13.2%\n(그 초과)", "못 받음": "못 받음\n(낼 세금 0원)"}
    data = []
    for i, lf in enumerate(leaves):
        y = N - i
        if i % 4 == 0: line(0.95, N / 2, 1.3, y - 1.5); box(1.95, y - 1.5, CL[lf["공제"]], fs=8)
        if i % 2 == 0: line(2.6, N - (i // 4) * 4 - 1.5, 2.95, y - 0.5); box(3.35, y - 0.5, lf["자산"])
        line(3.8, N - (i // 2) * 2 - 0.5, 4.25, y); box(4.85, y, "55세 전 꺼냄" if lf["시점"].startswith("55세 전") else "55세 뒤 연금")
        ax.plot([5.45, 5.6], [y, y], color=GREY, lw=0.8)
        g0 = lf["근거"]
        if len(g0) == 1 or len({p["옵션추천"] for p in g0}) == 1:
            ax.text(5.68, y + 0.14, word["갈림0" if lf["공제"] == "못 받음" and lf["추천"] == "갈림" else lf["추천"]], fontsize=9.5, fontweight="bold", color=col[lf["추천"]], va="center")
            ax.text(5.68, y - 0.2, "연금저축이 나은 비율 " + " · ".join(f"{p['옵션'].replace('환급금 ', '') + ' ' if p['옵션'] else ''}{pr(p['KR 2004~ 최소'], p['KR 2004~ 최대'])}" for p in g0),
                    fontsize=7.6, color="#444", va="center")
        else:                                   # 환급금 사용법에 따라 추천이 다른 칸: 옵션별로 한 줄씩
            for j, p in enumerate(g0):
                ax.text(5.68, y + 0.17 - 0.34 * j, f"{p['옵션']} → ", fontsize=8, color="#444", va="center")
                ax.text(7.25, y + 0.17 - 0.34 * j, f"{word[p['옵션추천']]} ({pr(p['KR 2004~ 최소'], p['KR 2004~ 최대'])})",
                        fontsize=8.5, fontweight="bold", color=col[p["옵션추천"]], va="center")
        for p in g0:
            data.append({k: lf[k] for k in ("공제", "자산", "시점", "추천", "단기_최소", "단기_최대")} | p)
    ax.text(0.0, -1.3, f"⑤ 공짜 리밸런싱(T6): 일반계좌에서 비중을 되돌리면 세금·수수료로 더 깎이는 몫. 72칸 중 95% 구간이 0을 뺀 칸은 "
                       f"한국 2004~ {t6['KR 2004~']['배제']}칸(Holm형 조정(검정 아님) 후 {t6['KR 2004~']['holm']}칸),\n"
                       f"    1991~ {t6['KR 1991~']['배제']}칸(조정 후 {t6['KR 1991~']['holm']}칸). 10년 누적 차이(일반 − 연금) 중앙값 "
                       f"{t6['KR 2004~']['lo10']:+.2f}~{t6['KR 2004~']['hi10']:+.2f}%p(2004~), {t6['KR 1991~']['lo10']:+.2f}~{t6['KR 1991~']['hi10']:+.2f}%p(1991~).",
            fontsize=8, color="#222", va="center", bbox=dict(fc="#F3F5F7", ec="none", pad=4))
    head(fig, "연금저축이 늘 이득은 아니다:\n공제를 못 받는 사람이 국내주식을 55세 전에 꺼낼 거면 일반계좌가 낫다",
            "같은 1원을 연금저축(공제 16.5%·13.2%·못 받음)과 일반계좌 ETF에 넣고 h년 뒤 세후 금액 비교. 한국 월간 2004-07~, 보유 5년 이상(h=5~21년)\n"
            "비율 = 연금저축이 일반계좌보다 많았던 시작 월의 비율(2004~ 표본, 겹치는 창). 공제 받음 칸은 환급 2개월·13개월 뒤 두 끝값을 합친 범위\n"
            "표시 규칙(결과를 본 뒤 이 그림을 만들며 정함): 모든 보유기간·환급 시점에서 50% 초과 → 연금저축, 모두 50% 미만 → 일반계좌, 그 밖 → 갈림",
            "일반계좌: 국내주식형 ETF 매매차익 비과세·분배금 15.4%, 해외주식형 매매차익·분배금 15.4%. 연금저축: 55세 전 인출 16.5%(비공제 원금은 비과세), 55세 뒤 연금 5.5%.\n"
            "환급금은 연말정산 뒤(납입월에 따라 2~13개월 뒤) 같은 자산(일반계좌)에 넣거나 CD 예금에 둠. 겹치는 창이라 비율은 독립 관측이 아님(21년 보유는 안 겹친 창 1개).\n"
            "출처: pilot7_20261008 T3_buckets.csv·T6_paired.csv. 1991~ 표본 범위와 1~4년 보유 값은 _data.csv에.")
    save(fig, "fig_T3T6_결정나무", pd.DataFrame(data))
    L = {(x["공제"], x["자산"], x["시점"][:5]): x for x in leaves}
    rr = lambda key, j=0, s="KR 2004~": f"{L[key]['근거'][j][s + ' 최소'] * 100:.0f}~{L[key]['근거'][j][s + ' 최대'] * 100:.0f}%"
    nd = ("못 받음", "국내주식", "55세 전")
    allh = b[(b["인출"] == "55세 전 인출(16.5%)") & b["통"].str.startswith(CRED["16.5%"]) & (b["환급지연(개월)"] == 2) & (b["자산"] == "국내주식")]
    ah = lambda end: f"{allh[allh['통'].str.endswith(end)][V].min() * 100:.0f}~{allh[allh['통'].str.endswith(end)][V].max() * 100:.0f}%"
    k13 = b[(b["인출"] == "55세 전 인출(16.5%)") & b["통"].str.startswith(CRED["16.5%"]) & b["통"].str.endswith("같은자산 일반계좌")
            & (b["자산"] == "국내주식") & (b["h년"] >= 5) & (b["표본"] == "KR 2004~")]
    d13 = lambda lag: pr(k13[k13["환급지연(개월)"] == lag][V].min(), k13[k13["환급지연(개월)"] == lag][V].max())   # 감사 LOW-R3
    readme(o, "2. 두 통 설계 + 5. 공짜 리밸런싱 — 연금저축이 누구에게나 이득일까",
        문제의식="""
"연금저축은 무조건 이득"이라는 말은 세액공제를 받는 사람 기준입니다. 낼 세금이 0원이라 공제를 못 받는 사회초년생, 그리고 국내주식 ETF(일반계좌에서도 매매차익 비과세)를 담는 사람에게는 답이 다를 수 있습니다.
또 "연금계좌에서는 리밸런싱(비중 되돌리기)에 세금이 없다"는 장점이 실제로 얼마나 큰지도 함께 봤습니다.
""",
        한_일=f"""
- 같은 1원을 ① 공제받는 연금저축(공제율 16.5%·13.2% 두 단계) ② 공제 못 받는 연금저축 ③ 일반계좌 ETF에 넣고, 국내주식·미국주식 각각, 55세 전에 꺼내는 경우와 55세 뒤 연금으로 받는 경우의 세후 금액을 비교했습니다(파일럿 T3, 한국 월간 2004-07~·1991-04~, 보유 1~30년의 모든 시작 월). 공제 환급금은 납입월에 따라 2~13개월 뒤 들어오므로 두 끝값(2개월·13개월)을 합쳐 범위로 보였습니다.
- 결정 나무의 표시는 파일럿 결과를 본 뒤 이 그림을 만들면서 정한 규칙입니다(사전에 등록한 규칙 아님): 2004~ 표본에서 보유 5년 이상의 모든 보유기간·두 환급 시점에서 연금저축이 나은 시작 월이 50%를 넘으면 "연금저축", 모두 50% 미만이면 "일반계좌", 그 밖은 "갈림".
- 5번(T6): 72가지 조건(포트폴리오 2 × 기간 3 × 수수료 2 × 리밸런싱 방식 6)에서 일반계좌가 연금계좌보다 리밸런싱으로 더 깎이는 몫을 부트스트랩으로 쟀습니다.
""",
        결과=f"""
- **공제를 못 받는 사람이 국내주식을 55세 전에 꺼낼 거면 일반계좌가 낫다.** 5년 이상 보유에서 연금저축이 나은 시작 월은 {rr(nd)}(= 일반계좌가 나은 비율 {100 - L[nd]['근거'][0]['KR 2004~ 최대'] * 100:.0f}~100%). 1~4년 보유에서도 연금저축이 나은 비율 {L[nd]['단기_최소'] * 100:.0f}~{L[nd]['단기_최대'] * 100:.0f}%.
- **미국주식을 55세 뒤 연금으로 받으면 공제 여부·공제율과 상관없이 연금저축이 낫다**(5년 이상 보유의 모든 시작 월, 연금소득세 5.5% 대 일반계좌 15.4%). 공제를 받는 사람의 국내주식 55세 뒤 연금도 연금저축이 나은 비율 {min(L[(c, '국내주식', '55세 이')]['근거'][j]['KR 2004~ 최소'] for c in ('16.5%', '13.2%') for j in (0, 1)) * 100:.0f}% 이상이었습니다.
- **공제를 받는 사람이 국내주식을 55세 전에 꺼내면 환급금을 어디 두느냐가 중요하다.** 5년 이상 보유에서 연금저축이 나은 비율(환급 2~13개월): 환급금을 예금(CD)에 두면 공제율 16.5%에서 {rr(('16.5%', '국내주식', '55세 전'), 1)}, 13.2%에서 {rr(('13.2%', '국내주식', '55세 전'), 1)}로 일반계좌가 나았고, 같은 자산에 다시 넣으면 16.5%에서 {rr(('16.5%', '국내주식', '55세 전'), 0)}, 13.2%에서 {rr(('13.2%', '국내주식', '55세 전'), 0)}로 갈렸습니다.
  - 참고(문서의 45~100%·0~46%와 같은 조건): 공제율 16.5%·환급 2개월·보유 1년 이상·두 표본이면 같은 자산 {ah('같은자산 일반계좌')}, CD {ah('CD(세후)')}. 환급이 13개월 뒤면 같은 자산 쪽 비율이 크게 낮아집니다(2004~·보유 5년 이상: 환급 2개월 {d13(2)} → 13개월 {d13(13)}).
- 공제율 13.2%인 사람의 미국주식 55세 전 인출은 환급금을 같은 자산에 넣으면 {rr(('13.2%', '미국주식', '55세 전'), 0)}(연금저축), 예금에 두면 {rr(('13.2%', '미국주식', '55세 전'), 1)}(갈림)이었습니다.
- 공제 못 받는 사람의 국내주식 55세 뒤 연금({rr(('못 받음', '국내주식', '55세 이')) }), 미국주식 55세 전({rr(('못 받음', '미국주식', '55세 전'))})은 보유기간에 따라 갈렸습니다.
- **공짜 리밸런싱의 이득은 작다.** 72칸 중 95% 구간이 0을 뺀 칸은 2004~ {t6['KR 2004~']['배제']}칸(원 결과의 'Holm형 조정(검정 아님)' 열 기준 {t6['KR 2004~']['holm']}칸), 1991~ {t6['KR 1991~']['배제']}칸(조정 후 {t6['KR 1991~']['holm']}칸). 10년 누적 차이 중앙값 {t6['KR 2004~']['lo10']:+.2f}~{t6['KR 2004~']['hi10']:+.2f}%p(2004~), {t6['KR 1991~']['lo10']:+.2f}~{t6['KR 1991~']['hi10']:+.2f}%p(1991~).
""",
        말하면_안_되는_것="""
- "연금저축은 무조건 이득이다" / "연금저축은 손해다" — 공제 여부·자산·꺼내는 시점에 따라 갈립니다.
- 비율을 "확률"로 말하기 — 겹치는 시작 월의 비율이라 독립 관측이 아니고, 21년 보유는 안 겹친 창이 1개뿐입니다.
- "리밸런싱 이득이 없다" — 작다는 것이지 0이라는 증거는 아닙니다.
""",
        한계="""
- 공제율 16.5%와 55세 전 인출세 16.5%가 같아서, 공제받는 사람의 결론은 환급금을 어떻게 쓰느냐에 크게 좌우됩니다(기준 시나리오는 정하지 않고 둘 다 보임).
- 미국주식 분배금은 S&P500 지수 배당으로 근사했고, 연금 수령한도·1,500만 원 분리과세 한도·세법 개정은 넣지 않았습니다.
- 한국 표본이 짧고 2025~26년 급등의 비중이 큽니다. 1991~ 표본 범위는 `fig_T3T6_결정나무_data.csv`에 같이 실었습니다.
- 국내 선행연구는 정요섭(2016) 수리모형 하나로 확인했습니다(파일럿 판정 문서 기준).
""")
    return dict(leaves=pd.DataFrame(data), t6=t6, allh={k: ah(k) for k in ("같은자산 일반계좌", "CD(세후)")})


# ── 4번 T5: 목돈 한 번에 vs 나눠 넣기 ──────────────────────────────────────────
def t5():
    o = out("04_목돈_vs_나눠넣기")
    fh = read(rf"{P7}\T5_french_hist.csv"); sh = read(rf"{P7}\T5_hist.csv")
    fb = read(rf"{P7}\T5_french_boot.csv"); sb = read(rf"{P7}\T5_boot.csv")
    PN = {"French 22개국(달러)": "22개국(달러)", "OECD 17개국(현지통화, 대기 = 현지 3개월 금리)": "17개국(현지통화)"}
    ST = ["전체", "최고점(낙폭 0)", "약세장(낙폭≤−20%)"]
    a = fh[(fh["분할"] == 3) & (fh["대기자금"] == "대기 0%")]
    s = sh[(sh["포트폴리오"] == "주식100") & (sh["분할"] == 3) & (sh["대기자금"] == "대기 0%") & (sh["상태정의"] == "가격지수") & (sh["시작상태"] == "최고점(낙폭 0)")]
    SN = {"US 1965~": "미국 1965~", "KR 1980~ 코스피 가격(배당 제외)": "한국 1980~", "KR 1991~": "한국 1991~", "KR 2004~": "한국 2004~"}
    cs = ["CER차(LS−CA) γ=3", "CER차(LS−CA) γ=6", "CER차(LS−CA) γ=10"]
    cb = pd.concat([sb[(sb["포트폴리오"] == "주식100") & (sb["분할"] == 3) & (sb["대기자금"] == "대기 0%") & sb["표본"].isin(["KR 2004~", "KR 1991~", "US 1965~"])].assign(표=lambda x: x["표본"]),
                    fb[(fb["분할"] == 3) & (fb["대기자금"] == "대기 0%")].assign(표=lambda x: x["패널"])])
    cer = cb.groupby("표", sort=False)[cs].agg(["min", "max"]) * 100
    g10_all = pd.concat([sb.assign(표=sb["표본"] + " " + sb["포트폴리오"]), fb.assign(표=fb["패널"])])
    pos10 = g10_all[g10_all["CER차(LS−CA) γ=10"] > 0][["표", "분할", "대기자금", "CER차(LS−CA) γ=10"]]

    fig = plt.figure(figsize=(9, 5.4))
    ax = fig.add_axes([0.08, 0.22, 0.50, 0.56]); bx = fig.add_axes([0.68, 0.22, 0.30, 0.56])
    ax.axhline(50, color="black", lw=0.6); x, ticks = 0, []
    for p, d in a.groupby("패널", sort=False):
        for st in ST:
            r = d[d["시작상태"] == st].iloc[0]
            c = BLUE if st.startswith("최고점") else GREY
            ax.vlines(x, r["나라군집 부트 2.5%"] * 100, r["나라군집 부트 97.5%"] * 100, color=c, lw=2)
            ax.scatter(x, r["LS 승률(안 겹친)"] * 100, color=c, s=22, zorder=3)
            ax.text(x, r["나라군집 부트 97.5%"] * 100 + 1.5, f"{r['LS 승률(안 겹친)'] * 100:.0f}", ha="center", fontsize=8, color=c)
            ticks.append((x, {"전체": "전체", "최고점(낙폭 0)": "고점", "약세장(낙폭≤−20%)": "약세장"}[st])); x += 1
        ax.text(x - 2, 21, PN[p] + f"\n안 겹친 창 {int(d['n(안 겹친 창)'].max())}개", ha="center", fontsize=8, color="#333"); x += 0.6
    for _, r in s.set_index("표본").reindex(list(SN)).reset_index().iterrows():
        ax.vlines(x, r["Wilson 95% 하"] * 100, r["Wilson 95% 상"] * 100, color=LGREY, lw=2)
        ax.scatter(x, r["LS 승률(안 겹친, 시작 0)"] * 100, color=BLUE, marker="D", s=16, zorder=3)
        ax.text(x, r["Wilson 95% 상"] * 100 + 1.5, f"{r['LS 승률(안 겹친, 시작 0)'] * 100:.0f}", ha="center", fontsize=8, color=BLUE)
        ticks.append((x, f"{SN[r['표본']].replace(' ', chr(10))}\n고점\n{int(r['n(안 겹친 창)'])}창")); x += 1
    ax.set_xticks([t[0] for t in ticks], [t[1] for t in ticks], fontsize=7, rotation=0)
    ax.set_ylim(10, 103); ax.set_xlim(-0.6, x - 0.4)
    ax.set_ylabel("한 번에 넣기가 1년 뒤 앞선 비율 (%)")
    ax.set_title("승률: 다국가는 고점에서도 한 번에 넣기가 앞섬(단일국은 엇갈림)", loc="left", fontsize=9, color="#222")
    order = ["KR 2004~", "KR 1991~", "US 1965~", "French 22개국(달러)", "OECD 17개국(현지통화, 대기 = 현지 3개월 금리)"]
    lab = ["한국 2004~", "한국 1991~", "미국 1965~", "22개국(달러)", "17개국(현지)"]
    bx.axvline(0, color="black", lw=0.6)
    for j, (cname, c, off) in enumerate(zip(cs, [LGREY, GREY, BLUE], [-0.22, 0, 0.22])):
        for i, k in enumerate(order):
            lo, hi = cer.loc[k, (cname, "min")], cer.loc[k, (cname, "max")]
            bx.barh(i + off, (lo + hi) / 2, 0.2, color=c, label=cname[-4:] if i == 0 else None)
    bx.set_yticks(range(len(order)), lab, fontsize=8); bx.invert_yaxis()
    bx.set_xlabel("확실성등가 차이, 한 번에 − 나눠 (%p)", fontsize=8)
    bx.legend(fontsize=7.5, frameon=False, loc="upper left", title="위험회피 γ", title_fontsize=7.5)
    bx.set_title("효용: 위험을 많이 싫어하면(γ=10)\n모든 표본에서 나눠 넣기가 나음", loc="left", fontsize=9, color="#222")
    w = a[a["시작상태"] == "전체"]["LS 승률(안 겹친)"] * 100; pk = a[a["시작상태"].str.startswith("최고점")]["LS 승률(안 겹친)"] * 100
    fig.set_size_inches(9, 5.9)
    ax.set_position([0.08, 0.25, 0.50, 0.44]); bx.set_position([0.70, 0.25, 0.28, 0.44])
    head(fig, f"목돈은 한 번에 넣는 쪽이 {w.min():.0f}~{w.max():.0f}% 이겼고 고점에서도 {pk.min():.0f}~{pk.max():.0f}%였지만,\n"
                 "위험을 많이 싫어하는 사람에겐 나눠 넣기가 낫다",
            "한 번에 넣기(LS) 대 3개월에 나눠 넣기(CA, 기다리는 돈 이자 0%), 주식 100%, 1년 뒤 비교\n"
            "다국가 = French 22개국 1975~(달러)·OECD 17개국(현지통화). 고점 = 시작 월 낙폭 0",
            "왼쪽 점 = 안 겹친 1년 창의 LS 승률, 선 = 나라 묶음 부트스트랩 95%(다국가) 또는 Wilson 95%(단일국, 마름모).\n"
            f"오른쪽 = Finlay & Zorn(2023) 방식 확실성등가(CER) 차이, 부트스트랩, 막대 = 블록 길이별 범위의 가운데. 주식 100%에서 γ=10 최댓값 {cer[(cs[2], 'max')].max():+.1f}%p.\n"
            f"60/40·40/60 포트폴리오는 미국·한국 2004~ 일부 칸에서 γ=10에도 한 번에 넣기가 조금 나음(최대 {pos10['CER차(LS−CA) γ=10'].max() * 100:+.1f}%p, {len(pos10)}칸).\n"
            "단일국 고점 창은 6~31개뿐이라 범위가 넓음(한국 1991~ 8창은 38%로 반대). 한국 1980~은 배당 없는 가격지수. 출처: pilot7_20261008 T5_french_hist·T5_hist·T5_french_boot·T5_boot.csv.")
    save(fig, "fig_T5_목돈_나눠넣기", pd.concat([a.assign(구분="다국가 승률"), s.assign(구분="단일국 고점 승률"),
                                               cer.reset_index().droplevel(1, axis=1).set_axis(["표"] + [f"{c} {m}" for c in cs for m in ("min", "max")], axis=1).assign(구분="CER %p")]))
    sg = s.set_index("표본")
    tr = sh[(sh["포트폴리오"] == "주식100") & (sh["분할"] == 3) & (sh["대기자금"] == "대기 0%") & (sh["상태정의"] == "총수익(민감도)") & (sh["시작상태"] == "최고점(낙폭 0)")].set_index("표본")
    sc = lambda k: f"{sg.loc[k, 'LS 승률(안 겹친, 시작 0)'] * 100:.0f}%({int(sg.loc[k, 'n(안 겹친 창)'])}창, Wilson {sg.loc[k, 'Wilson 95% 하'] * 100:.0f}~{sg.loc[k, 'Wilson 95% 상'] * 100:.0f}%)"
    c10 = lambda k: f"{cer.loc[k, (cs[2], 'min')]:+.1f}" + ("" if abs(cer.loc[k, (cs[2], 'min')] - cer.loc[k, (cs[2], 'max')]) < 0.05 else f"~{cer.loc[k, (cs[2], 'max')]:+.1f}")
    c3 = cer[(cs[0], "max")]
    readme(o, "4. 목돈 한 번에 vs 나눠 넣기 — 보험에서 옮긴 목돈, 고점이면 나눠 넣어야 할까",
        문제의식="""
보험·신탁에서 연금저축펀드로 목돈을 옮기는 사람이 많습니다(보도: 2024년~2026년 1분기 누적 9조 2,585억 원, 2차 출처, 의원실 원문 미확인). 옮긴 날이 마침 주가 고점이면 "몇 달에 나눠 넣는 게 안전하다"는 말을 흔히 듣습니다. 평균으로 이기는 쪽과 그 사람에게 나은 쪽이 같은지 따져 봤습니다.
""",
        한_일="""
- 한 번에 넣기(LS)와 3개월에 나눠 넣기(CA)의 1년 뒤 금액을 비교했습니다(파일럿 T5). 기다리는 돈의 이자는 0%와 단기금리 두 가지.
- 자료: 한국 2004~·1991~·1980~(코스피 가격), 미국 1965~, French 22개국 1975~(달러), OECD 17개국(현지통화). 시작 월이 고점(낙폭 0)·약세장(낙폭 −20% 이하)인 경우를 따로 셌습니다.
- 승률 외에 위험을 싫어하는 정도(γ=3·6·10)를 반영한 확실성등가(CER) 차이를 Finlay & Zorn(2023) 방식으로 계산했습니다.
- 차별점(국내 선행연구 박영규·이상엽 2010 등 대비): 고점 시작 + 다국가 + 효용. 선행연구 목록은 파일럿 문서 기준이며 이번에 다시 대조하지 않았습니다.
""",
        결과=f"""
- **평균으로는 한 번에 넣기가 이긴다.** 안 겹친 1년 창 승률: 22개국 {w.iloc[0]:.0f}%, 17개국 {w.iloc[1]:.0f}%(주식 100%, 3개월 분할, 이자 0%).
- **다국가 자료에서는 고점에서 시작해도 마찬가지였다.** 22개국 {pk.iloc[0]:.0f}%, 17개국 {pk.iloc[1]:.0f}%.
- **단일국 고점 창은 엇갈렸다:** 미국 {sc('US 1965~')}, 한국 1980~ {sc('KR 1980~ 코스피 가격(배당 제외)')}, 한국 1991~ {sc('KR 1991~')}, 한국 2004~ {sc('KR 2004~')} — 창이 적어 범위가 넓습니다.
- **위험을 많이 싫어하는 사람(γ=10)에게는 모든 표본에서 나눠 넣기가 나았다**(주식 100%). CER 차이(한 번에 − 나눠): 한국 2004~ {c10('KR 2004~')}%p, 한국 1991~ {c10('KR 1991~')}%p, 미국 {c10('US 1965~')}%p, 22개국 {c10('French 22개국(달러)')}%p, 17개국 {c10('OECD 17개국(현지통화, 대기 = 현지 3개월 금리)')}%p.
- γ=3이면 표본에 따라 한 번에 넣기가 조금 낫거나 비슷했습니다(최댓값 {c3.max():+.1f}%p).
""",
        말하면_안_되는_것=f"""
- "고점이면 나눠 넣어라" — 다국가 고점 창에서도 한 번에 넣기가 약 3분의 2를 이겼습니다.
- "한 번에 넣는 게 정답" — 위험을 많이 싫어하는 사람에게는 나눠 넣기가 더 나았습니다.
- "모든 포트폴리오에서 γ=10이면 나눠 넣기" — 60/40·40/60에서는 미국·한국 2004~ 일부 칸({len(pos10)}칸)에서 반대였습니다(최대 {pos10['CER차(LS−CA) γ=10'].max() * 100:+.1f}%p).
""",
        한계="""
- 단일국 고점 창은 6~31개뿐이라 단일국 결과로는 판단하기 어렵습니다(한국 1991~ 8창은 38%로 반대). 이 값은 가격지수 기준이고, 원 결과의 '총수익(민감도)'으로 보면 TRX로 달라집니다.
""".replace("TRX", ", ".join(f"{SN.get(k, k)} {r['LS 승률(안 겹친, 시작 0)'] * 100:.0f}%({int(r['n(안 겹친 창)'])}창)" for k, r in tr.iterrows())) + """- 한국 1980~은 배당이 없는 가격지수라 주식 수익이 낮게 잡힙니다. 22개국은 달러 기준이라 원화 투자자와 다릅니다.
- 3개월 분할 외 4~6개월, 기다리는 돈에 단기금리를 준 결과는 원 결과 파일(pilot7 `T5_*.csv`)에 있습니다(이자를 주면 승률이 조금 낮아짐). 60/40·40/60의 반대 칸 수에는 한국 2004~의 2024년까지 부분 표본도 들어 있습니다.
- 보험·신탁에서 펀드로 옮긴 공식 통계는 찾지 못했습니다.
""")
    return dict(w=w, pk=pk, s=s, cer=cer, pos10=pos10)


# ── 7번 T2 + A: 운용사별 2055 TDF ──────────────────────────────────────────────
def t2a():
    o = out("07_운용사별_2055TDF")
    A = r"pilot9_20261013\A_simple_20261017"
    gl = read(rf"{A}\L2_inputs_glide_fee_by_month.csv")
    other = read(r"pilot9_20261013\decisions_survey\D1_glide_2055_annual.csv")
    ck = read(r"pilot9_20261013\C_real_20261017\inputs\C2_check_index_vs_real_overlap.csv")
    bp = read(rf"{A}\L2b_boot_pairs.csv"); pt = read(rf"{A}\L1_common_pair_t.csv"); st = read(rf"{A}\L1_real_nav_stats.csv")
    vs = read(r"pilot9_20261013\A_window_mde_20261026\vintage_summary.csv")
    reg = read(rf"{P7}\T2_panel_ext_reg.csv")
    cw = read(r"pilot9_20261013\A_window_mde_20261026\common_window.csv").set_index("vintage")
    M5 = ["KB", "미래에셋", "삼성", "신한", "한국투자"]
    COLS = {"KB": "KB_UH", "미래에셋": "미래에셋", "삼성": "삼성_H", "신한": "신한", "한국투자": "한국투자_UH"}   # A 층1과 같은 5계열(KB·한국투자 UH판, 삼성 H판)
    ca = ck[ck["nav_lag_bdays"].isin([0, 1, 2]) & ck["index_model"].str.endswith("total") & ck["real"].isin(COLS.values())].copy()
    ca["se"] = ca["te_pctpa"] / np.sqrt(ca["n"] / 12); ca["t"] = ca["mean_diff_pctpa"] / ca["se"]
    assert ca.groupby("nav_lag_bdays").size().eq(5).all()
    c = ca[ca["nav_lag_bdays"] == 0].copy()          # 그림 점 = 시차 0일, 범위 문장 = 시차 0~2일 전체(감사 HIGH-1)
    TE = f"{ca['te_pctpa'].min():.1f}~{ca['te_pctpa'].max():.1f}"
    r = bp[(bp["블록"].astype(str) == "1") & (bp["보수"] == "총보수")].copy(); r["비"] = np.maximum(r["비_중앙"], 1 / r["비_중앙"])
    p = pt[(pt["판본"] == "UH") & (pt["C_P앞잇기"] == "없음")]
    sr = st[(st["판본"] == "UH") & (st["C_P앞잇기"] == "없음") & (st["구간"] == "공통")]
    m55 = vs[vs["vintage"] == 2055].iloc[0]
    base = reg[reg["모형"] == "사건×빈티지FE (기본)"]

    fig = plt.figure(figsize=(9, 5.2))
    ax = fig.add_axes([0.08, 0.20, 0.50, 0.58]); bx = fig.add_axes([0.70, 0.20, 0.28, 0.58])
    for m, d in other[~other["manager"].isin(M5)].groupby("manager"):
        ax.plot(d["T"] + 60, d["risky_pct"], color=LGREY, lw=0.8, zorder=1)
    ax.plot([], [], color=LGREY, lw=0.8, label="다른 운용사 7곳")
    ends = {}
    for m in M5:
        y = gl[f"w_{m}"] * 100
        hi = m == "신한"
        ax.plot(gl["age"], y, color=BLUE if hi else GREY, lw=1.8 if hi else 1.1, zorder=3 if hi else 2)
        ends[m] = y.iloc[-1]
    for i, (m, y) in enumerate(sorted(ends.items(), key=lambda kv: kv[1])):
        ax.text(60.4, y + (i - 2.5) * 2.2 if m != "신한" else y, m, fontsize=8, color=BLUE if m == "신한" else "#444", va="center")
    ax.set_xlim(30, 64); ax.set_ylim(10, 85); ax.set_xlabel("가입자 나이(2055년에 60세)"); ax.set_ylabel("공시 위험자산(주식 등) 비중 (%)")
    ax.legend(fontsize=7.5, frameon=False, loc="lower left")
    ax.set_title(f"투자설명서대로면 30년 뒤 금액이 쌍별 {r['비'].min():.2f}~{r['비'].max():.2f}배 차이", loc="left", fontsize=9, color="#222")
    c = c.set_index("real").loc[list(COLS.values())]
    yy = np.arange(len(c))
    bx.axvline(0, color="black", lw=0.6)
    bx.hlines(yy, c["mean_diff_pctpa"] - 1.96 * c["se"], c["mean_diff_pctpa"] + 1.96 * c["se"], color=GREY, lw=2)
    bx.scatter(c["mean_diff_pctpa"], yy, color=BLUE, s=20, zorder=3)
    bx.set_yticks(yy, [f"{m} ({int(n)}개월)" for m, n in zip(COLS, c["n"])], fontsize=8); bx.invert_yaxis()
    bx.set_xlabel("실제 − 설명서대로 계산, 연 %p\n(점 = 평균, 선 = ±1.96 표준오차)", fontsize=8)
    bx.set_title(f"실제는 설명서 계산과 연 {TE}%p씩\n흔들림(추적오차, 기준가 시차 0~2일)\n점·선 = 시차 0일", loc="left", fontsize=9, color="#222")
    fig.set_size_inches(9, 5.8)
    ax.set_position([0.08, 0.25, 0.50, 0.44]); bx.set_position([0.72, 0.25, 0.26, 0.44])
    head(fig, "같은 2055 TDF라도 운용사마다 주식 비중 계획이 다르지만,\n짧은 실제 수익률로는 그 차이를 가려낼 수 없다",
            f"왼쪽 = 5대 운용사 2055 TDF 투자설명서 글라이드패스(30년 계산 입력) + 다른 7곳 공시. 오른쪽 = 실제 기준가 대 '공시 비중 × 지수 − 총보수' 계산\n"
            f"5대 실제 공통 {int(sr['개월'].max())}개월({sr['시작'].iloc[0]}~{sr['끝'].iloc[0]}) 연수익 {sr['ann_ret'].min() * 100:.1f}~{sr['ann_ret'].max() * 100:.1f}%, 운용사 쌍별 월 차이 |t| 최대 {p['t'].abs().max():.2f}",
            f"30년 금액 비 = 2004-07~2026-08 한국 표본 부트스트랩(블록 1, 1만 경로) 중앙값, 총보수 기준, 큰 쪽 ÷ 작은 쪽(최대 = KB/신한). 공시대로 운용·비용이라는 가정의 값.\n"
            f"2055 빈티지 5대 공통 {int(m55['T'])}개월로 구별할 수 있는 최소 연 차이(검정력 80%) 중앙값 {m55['mde_med']:.1f}%p.\n"
            f"19개 운용사 패널: 같은 빈티지 안 급락 손실 차이에 대한 공시 위험자산 비중 기울기 p = {base['p'].min():.2f}~{base['p'].max():.2f}(0과 구분 안 됨).\n"
            "KB·삼성·한국투자는 클래스·환헤지(H/UH)가 섞인 상품 차이. 현재 남은 펀드만 봄. 출처: pilot9 A_simple·A_window_mde·C_real\\inputs, pilot7 T2_panel_ext_reg.csv.")
    save(fig, "fig_T2A_운용사별_글라이드", pd.concat([c.reset_index().assign(구분="실제-계산"), r.assign(구분="30년 비")]))   # 공시 글라이드 값(원 _data.csv '글라이드' 행)은 재배포 조건 미확인이라 뺌
    v4 = vs[vs["vintage"].between(2030, 2045)]
    readme(o, "7. 운용사별 2055 TDF — 짧은 수익률 순위로 TDF를 고르면 안 되는 이유",
        문제의식="""
이름이 같은 "TDF 2055"라도 운용사마다 나이에 따라 주식을 줄여 가는 계획(글라이드패스)이 다릅니다. 가입자는 보통 최근 1~2년 수익률 순위를 보고 고릅니다. 그 순위가 운용사 차이를 말해 주는지 따져 봤습니다.
""",
        한_일=f"""
- 5대 운용사(KB·미래에셋·삼성·신한·한국투자) 2055 TDF의 투자설명서 글라이드패스를 그대로 따랐다고 보고, 2004-07~2026-08 한국 자료를 다시 뽑은 같은 시장 경로 1만 개에서 30년 적립 금액을 비교했습니다(10월 19일 A).
- 실제 기준가와 '공시 비중 × 지수 − 총보수' 계산을 겹치는 달끼리 대조해, 실제가 설명서 가정에서 얼마나 벗어나는지 쟀습니다.
- 운용사를 19곳으로 늘린 패널(파일럿 T2)로, 같은 빈티지 안 급락 손실 차이가 공시 위험자산 비중으로 설명되는지 회귀로 봤습니다(운용사 군집 표준오차·wild cluster bootstrap).
- 그림: `fig_T2A_운용사별_글라이드`(왼쪽 공시 경로, 오른쪽 실제 − 계산).
""",
        결과=f"""
- **설명서대로라면 운용사 사이 30년 금액이 {r['비'].min():.2f}~{r['비'].max():.2f}배 차이**(블록 1, 총보수, 중앙값, 큰 쪽 ÷ 작은 쪽). 가장 큰 쌍은 KB/신한으로, 신한의 60세 위험자산 비중이 {ends['신한']:.0f}%로 다른 네 곳({min(v for k, v in ends.items() if k != '신한'):.0f}~{max(ends.values()):.0f}%)보다 낮습니다.
- **그러나 실제 수익률은 설명서 계산과 연 {TE}%p씩 흔들렸다**(추적오차, 실제 기준가를 계산과 0·1·2 영업일 어긋나게 맞춘 세 경우 전체, 운용사별 {int(ca['n'].min())}~{int(ca['n'].max())}개월). 평균 차는 운용사별 {ca['mean_diff_pctpa'].min():+.2f}~{ca['mean_diff_pctpa'].max():+.2f}%p/년이었고 |t| ≤ {ca['t'].abs().max():.2f}로 0과 구분되지 않았습니다. 추적오차는 시차 0일일 때 가장 커서({c['te_pctpa'].min():.1f}~{c['te_pctpa'].max():.1f}%p) 일부는 기준가 날짜 어긋남 때문일 수 있습니다.
- **실제 기록이 짧아 순위를 가려낼 수 없다.** 5대 공통 {int(sr['개월'].max())}개월 연수익은 {sr['ann_ret'].min() * 100:.1f}~{sr['ann_ret'].max() * 100:.1f}%였지만 운용사 쌍별 |t| 최대 {p['t'].abs().max():.2f}. 2055 빈티지 5대 공통 {int(m55['T'])}개월로 구별할 수 있는 최소 연 차이(검정력 80%)는 중앙값 {m55['mde_med']:.1f}%p, 기록이 긴 2030~2045 빈티지(공통 {int(v4['T'].min())}개월)도 {v4['mde_med'].min():.1f}~{v4['mde_med'].max():.1f}%p입니다.
- **19개 운용사로 늘려도** 같은 빈티지 안 급락 손실 차이는 공시 위험자산 비중으로 설명되지 않았습니다(기울기 {base['기울기'].min():+.3f}~{base['기울기'].max():+.3f}, p = {base['p'].min():.2f}~{base['p'].max():.2f}, WCB p = {base['p(운용사 WCB, Webb)'].min():.2f}~{base['p(운용사 WCB, Webb)'].max():.2f}).
- 그래서 "짧은 수익률 순위로 고르면 안 되는 이유": 실제 수익률은 설명서 계산에서 해마다 연 {TE}%p씩 흔들리고, 2055 빈티지의 2년 남짓한 공통 기록으로는 연 약 {m55['mde_med']:.1f}%p보다 작은 진짜 차이를 안정적으로 구별하기 어렵습니다. 그래서 최근 순위는 운용사 차이보다 우연을 더 많이 담고 있을 수 있습니다.
""",
        말하면_안_되는_것="""
- "어느 운용사가 더 잘한다" / "신한 TDF가 30년 뒤 20% 덜 번다" — 30년 비는 설명서대로 운용하고 비용이 설명서대로라는 가정의 값이고, 실제 운용사 차이의 크기·순서를 말해 주지 않습니다.
- "운용사 차이가 없다" — 차이가 없다는 증거가 아니라, 이 기록으로는 가려낼 수 없다는 뜻입니다.
""",
        한계="""
- KB·삼성·한국투자 실제 기준가는 클래스·환헤지(H/UH) 판이 섞여 있어 "운용사 차이"가 아니라 "클래스·헤지를 포함한 상품 차이"입니다.
- 30년 동안 현행 공시 글라이드를 그대로 따른다고 가정했습니다(실제로는 글라이드가 바뀐 적이 있음 — 9번 주제).
- 현재 남아 있는 펀드만 봤습니다(생존편향). 국내 선행연구(홍원구 2026, 최재윤·박영규 2025)가 있어 "새 발견"이 아니라 "자료를 넓혀 다시 확인한 분석"입니다(선행연구 목록은 포트폴리오 문서 기준, 이번에 원문 재대조 안 함).
- 실제 수익률 비교(원 A, {0})와 구별 가능 최소 차이 계산(10월 26일, {1})은 구간 정의가 달라 개월 수가 다릅니다.
""".replace("{0}", f"{sr['시작'].iloc[0]}~{sr['끝'].iloc[0]} {int(sr['개월'].max())}개월")
   .replace("{1}", "{} 기준 공통 {}개월".format(cw.loc[2055, "start"][:7] + "~" + cw.loc[2055, "end"][:7], int(cw.loc[2055, "months"]))))
    return dict(r=r[["쌍", "비"]], c=c[["n", "te_pctpa", "mean_diff_pctpa", "t"]], m55=m55, base=base[["규칙", "기울기", "p", "p(운용사 WCB, Webb)"]], ends=ends)


if __name__ == "__main__":
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", 20)
    which = sys.argv[1:] or ["t1", "t3t6", "t5"] + (["t2a"] if DATA else [])
    R = {k: globals()[k]() for k in which}
    for k, v in R.items():
        print("=====", k); print(v)
