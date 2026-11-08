# -*- coding: utf-8 -*-
"""후보 5 포트폴리오판 생성기(2026-11-06). 설계서 = docs/ideas/본연구후보_20261027/후보5_간단테스트/설계서_후보5_포트폴리오판_20261106.md.
순서: 자가점검 → F판(F1~F4만, N 끔) 계산 → 동결 결과(run_20261027_0410)와 대조(assert) → 포트폴리오판(N1~N3 켬) 계산 → 결과 문서(md·PDF).
실행(git bash): PYTHONPATH= PYTHONIOENCODING=utf-8 python notebooks/candidate5/_gen_cand5p.py
빠른 시험: C5P_QUICK=1 → 격자 셀 4개·부트스트랩 300경로(역사 경로는 전부: 동결 결과와 칸 단위로 대조하려고).
출력 = $PENSION_DATA_ROOT/results/candidate5_portfolio_20261106/{run|quick}_YYYYMMDD_HHMM/ (F/·N/ 하위). 이 폴더 밖에는 쓰지 않는다.
"""
from __future__ import annotations
import datetime, functools, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pension_lab import cand5 as C, cand5p as CP, pilot7 as P7, bootstrap as BS, runrecord as rr, paths  # noqa: E402
from _gen_cand5 import md_to_pdf  # noqa: E402
from _doc_cand5 import md_table, NAME, WHEN, pair, f3  # noqa: E402

QUICK = os.environ.get("C5P_QUICK") == "1"
OUT = paths.RESULTS / "candidate5_portfolio_20261106"
FROZEN = C.OUT / "run_20261027_0410"
FROZEN_MDE = C.OUT / "cand5_mde_prerun.csv"
QUICK_CELLS = ("base", "D11:S_hi", "D07:연금외16.5%", "D18:안함")
CELL_MAP = {"D11:7.1%": "D11:S_hi"}           # 동결 셀 이름 → 새 이름. D08:95%는 F3로 삭제.
M = 300_000                                   # 문서 본문 표 = 월 30만 원(동결 문서와 같음)
P = C.P
log = lambda s: print(f"[{datetime.datetime.now():%H:%M:%S}] {s}", flush=True)
INPUT = functools.cache(lambda d05, d15, d16: C.inputs({**C.REC, "D05": d05, "D15": d15, "D16": d16}))
inp = lambda o: INPUT(o["D05"], o["D15"], o["D16"])
mode = lambda k: "wd" if k.startswith("wd") else k


def rate_2026() -> tuple[float, str]:
    """기초연금 사람 B를 풀 금리: 기준 셀 예금 금리 모형(D05·D16)의 마지막 12개월 평균 월 금리(세전)와 그 기간."""
    s = C.deposit_return(C.deposit_rate_monthly(CP.REC["D16"]), CP.REC["D05"]).iloc[-12:]
    return float(s.mean()), f"{s.index[0]:%Y-%m}~{s.index[-1]:%Y-%m}"


def boot_blocks(r: pd.DataFrame) -> dict:
    """부트스트랩 평균 블록 길이(C.BOOT_BLOCKS 순서): Politis–White 주식·예금, 12개월."""
    b = {"PW_eq": P7.pw_block(r["eq"].to_numpy()), "PW_dep": P7.pw_block(r["dep"].to_numpy()), "12개월": 12.0}
    assert tuple(b) == C.BOOT_BLOCKS
    return b


def compute(out: Path, flags: dict, mde: pd.DataFrame, ppl: dict) -> None:
    """_gen_cand5.stage_results와 같은 표를 새 엔진(cand5p)으로. flags = N 스위치, ppl = 기초연금 사람 3명."""
    out.mkdir(parents=True)
    save = lambda df, name: (df.to_csv(out / name, index=False, encoding="utf-8-sig"), log(f"{out.name}/{name} {len(df)}행"))
    stats, cov = [], []
    for cid, d, cand, o in CP.cells():
        if QUICK and cid not in QUICK_CELLS:
            continue
        o = {**o, **flags}; r = inp(o)
        for k, H in C.HS.items():
            df, bp = CP.run(r, o, H, mode(k), bp=(ppl if cid == "base" and k == "p70" and o["N3"] else None))
            if cid == "base":
                save(df, f"base_hist_{k}.csv")
            if bp is not None:
                save(bp, "bp_hist_p70.csv"); save(CP.bp_stats(bp), "bp_stats.csv")
            n = C.nstat(r, df.path.nunique() if len(df) else 0, H)
            for a, b in CP.PAIRS[k]:
                for an in P("w_eq"):
                    sub = df[df.asset == an] if len(df) else df
                    why = "" if len(sub) else ("1980~ 표본은 채권 자료 없음 → (B) 비교 불가" if o["D15"] == "s7" and an == "B" else "경로 0개")
                    cov.append({"cell": cid, "D": d, "후보": cand, "비교": k, "쌍": f"{a}<{b}", "asset": an, "rows": len(sub), "이유": why})
                    if len(sub):
                        stats.append(C.loss_stats(sub, a, b).assign(cell=cid, D=d, 후보=cand, 비교=k, 쌍=f"{a}<{b}", n_eff=n["n_eff"]))
    cov += [{"cell": "전체", "D": "", "후보": "", "비교": "", "쌍": k, "asset": "", "rows": 0, "이유": f"계산 안 함: {v}"} for k, v in CP.NOT_COMPUTED.items()]
    cov = pd.DataFrame(cov); save(cov, "coverage.csv")
    assert ((cov.rows > 0) | (cov["이유"] != "")).all(), "계산도 이유도 없는 칸"
    st = pd.concat(stats, ignore_index=True); save(st, "grid_stats.csv")
    key = ["비교", "쌍", "asset", "m", "person"]
    base = st[st.cell == "base"][key + ["n", "loss_n", "p_loss", "median_gap", "worst"]]
    ch = st[st.cell != "base"].merge(base, on=key, suffixes=("", "_base")).merge(mde[["비교", "쌍", "asset", "mde", "비교불가"]], on=["비교", "쌍", "asset"], how="left")
    ch["d_p"] = ch.p_loss - ch.p_loss_base; ch["d_med"] = ch.median_gap - ch.median_gap_base
    ch["warn"] = (ch.d_p.abs() >= 1 / ch.n_base - 1e-12) | (ch.d_med.abs() >= ch.mde)
    save(ch, "change_table.csv")
    save(ch.groupby(["D", "후보", "비교", "쌍"]).agg(셀=("warn", "size"), 경고=("warn", "sum"), 최대Δp=("d_p", lambda x: x.abs().max()),
                                               최대Δ중앙값=("d_med", lambda x: x.abs().max())).reset_index(), "change_summary.csv")
    o0 = {**CP.REC, **flags}; r = inp(o0)
    lv = (1 + P7.kospi200_px()).cumprod(); crash = []
    for e in [lv.loc[y].idxmin() for y in ("2008", "2020")]:
        for H in (36, 60):
            s = r.index[r.index.get_loc(e) - H + 1]
            crash.append(CP.run(r, o0, H, "wd", st=[s])[0].assign(폭락달=e.strftime("%Y-%m"), H=H))
    save(pd.concat(crash), "crash_cases.csv")
    rows = []
    for k in C.HS:
        d = pd.read_csv(out / f"base_hist_{k}.csv")
        w = d.pivot_table(index=["path", "asset", "m"], columns="person", values="ps").join(d.groupby(["path", "asset", "m"])["contrib"].first())
        for p in ("나", "다"):
            x = (w[p] - w["가"]) / w["contrib"]
            rows.append(x.groupby(level=["asset", "m"]).agg(["min", "median", "max"]).reset_index().assign(비교=k, 차이=f"({p})−(가)"))
    save(pd.concat(rows), "tax_effect.csv")
    blocks = boot_blocks(r)
    NB = 300 if QUICK else P("n_boot"); bst, bsd = [], []
    od = {**o0, "defer": True}                    # r3 N-H1: 연기판 부트스트랩(같은 재표본 경로, 70세 연금저축 쌍)
    for bn, blk in blocks.items():
        EQ, BD, DP = BS.paired_resample_paths([r["eq"], r["bd"], r["dep"]], NB, P("H70"), mean_block=blk, seed=P("seed"))
        for k, H in C.HS.items():
            rows, rd = [], []
            for an, w in P("w_eq").items():
                for m in P("monthly"):
                    acc = CP.accumulate(EQ[:, :H], BD[:, :H], DP[:, :H], m, w, o0, None, H)
                    ad = CP.accumulate(EQ[:, :H], BD[:, :H], DP[:, :H], m, w, od, None, H) if k == "p70" and flags["N3"] else None
                    for pn, room in C.rooms(o0).items():
                        for a_, oo, rs in ((acc, o0, rows), (ad, od, rd)):
                            if a_ is None:
                                continue
                            e = CP.evaluate(a_, m, room, H, mode(k), oo)
                            dd = pd.DataFrame({kk: v for kk, v in e.items() if np.ndim(v)}); dd["contrib"] = e["contrib"]
                            dd["asset"], dd["m"], dd["person"] = an, m, pn; rs.append(dd)
            if rd:
                dd = pd.concat(rd, ignore_index=True)
                bsd += [C.loss_stats(dd, a_, b_).assign(블록=bn, 비교=k, 쌍=f"{a_}<{b_}") for a_, b_ in CP.PAIRS[k] if a_ == "ps"]
            dd = pd.concat(rows, ignore_index=True)
            if k == "p70" and bn == C.BOOT_BLOCKS[0]:
                dd["gap_dep"] = (dd.ps - dd.dep) / dd.contrib
                save(dd[(dd.m == M)][["asset", "person", "gap_dep"]], "boot_p70_m30_gap.csv")
            for a_, b_ in CP.PAIRS[k]:
                bst.append(C.loss_stats(dd, a_, b_).assign(블록=bn, 비교=k, 쌍=f"{a_}<{b_}"))
        log(f"{out.name} 부트스트랩 {bn} 블록 {blk:.2f} 끝")
    save(pd.concat(bst), "boot_stats.csv")
    if bsd:
        save(pd.concat(bsd), "defer_boot_stats.csv")
    json.dump({"blocks": blocks, "n_boot": NB, "seed": P("seed"), "flags": flags}, open(out / "boot_meta.json", "w", encoding="utf-8"), ensure_ascii=False)


def same(name: str, a: pd.DataFrame, b: pd.DataFrame, key: list) -> tuple[int, float]:
    """키가 같은 행끼리 공통 열 비교(숫자 = 상대차 ≤ 1e-12, NaN 위치 같음, 그 밖 = 값 같음). 키 집합이 다르면 멈춤."""
    j = a.merge(b, on=key, how="outer", suffixes=("_old", "_new"), indicator=True)
    assert (j["_merge"] == "both").all(), f"{name}: 키 불일치 {j['_merge'].value_counts().to_dict()}"
    worst = 0.0
    for c in [c for c in a.columns if c in b.columns and c not in key]:
        x, y = j[c + "_old"], j[c + "_new"]
        if pd.api.types.is_numeric_dtype(x) and not pd.api.types.is_bool_dtype(x):
            assert (x.isna() == y.isna()).all(), f"{name}.{c}: NaN 위치 다름"
            worst = max(worst, float(np.nan_to_num(((x - y).abs() / np.maximum(x.abs(), 1)).max())))
        else:
            assert (x.astype(str) == y.astype(str)).all(), f"{name}.{c}: 값 다름"
    assert worst <= 1e-12, f"{name}: 최대 상대차 {worst}"
    return len(j), worst


def regress(run: Path) -> pd.DataFrame:
    """설계서 4절: F판(N 끔) = 동결 결과, 노란우산 해약 칸(ny_cancel 열·쌍)과 F3로 지운 D08:95% 셀만 빼고.
    8번으로 새로 생긴 62세 폐업 칸(p62 ny_close 열·쌍)은 동결판에 없어 대조 밖."""
    F, rows = run / "F", []
    old, new = (lambda f: pd.read_csv(FROZEN / f)), (lambda f: pd.read_csv(F / f))
    keep = lambda df: df[~df["쌍"].str.contains("ny_cancel") & ~((df["비교"] == "p62") & df["쌍"].str.contains("ny_close"))]
    for k in C.HS:
        a, b = old(f"base_hist_{k}.csv"), new(f"base_hist_{k}.csv"); key = ["path", "asset", "m", "person"]
        n, w = same(f"base_hist_{k}", a.drop(columns="ny_cancel", errors="ignore"), b.drop(columns="ny_cancel", errors="ignore"), key)
        moved = int((a.merge(b, on=key).pipe(lambda j: (j.ny_cancel_x - j.ny_cancel_y).abs() > 1e-6)).sum()) if "ny_cancel" in a else 0
        rows.append({"파일": f"base_hist_{k}.csv", "대조 행": n, "최대 상대차": w, "제외": "ny_cancel 열", "노란우산 해약 바뀐 행": moved})
    for f in ("grid_stats.csv", "change_table.csv"):
        a = old(f); a["cell"] = a.cell.replace(CELL_MAP); d08 = int((a.cell == "D08:95%").sum()); a = a[a.cell != "D08:95%"]
        a = a[a.cell.isin(QUICK_CELLS)] if QUICK else a
        b = new(f); key = ["cell", "비교", "쌍", "asset", "m", "person"]
        n, w = same(f, keep(a).drop(columns=["D", "후보"]), keep(b).drop(columns=["D", "후보"]), key)
        moved = int((a[a["쌍"].str.contains("ny_cancel")].merge(b, on=key).pipe(lambda j: (j.median_gap_x - j.median_gap_y).abs() > 1e-12)).sum())
        rows.append({"파일": f, "대조 행": n, "최대 상대차": w, "제외": f"ny_cancel 쌍, D08:95% 셀 {d08}행", "노란우산 해약 바뀐 행": moved})
    a, b = old("crash_cases.csv"), new("crash_cases.csv")
    n, w = same("crash_cases", a.drop(columns="ny_cancel"), b.drop(columns="ny_cancel"), ["폭락달", "H", "path", "asset", "m", "person"])
    rows.append({"파일": "crash_cases.csv", "대조 행": n, "최대 상대차": w, "제외": "ny_cancel 열", "노란우산 해약 바뀐 행": np.nan})
    n, w = same("tax_effect", old("tax_effect.csv"), new("tax_effect.csv"), ["비교", "차이", "asset", "m"])
    rows.append({"파일": "tax_effect.csv", "대조 행": n, "최대 상대차": w, "제외": "", "노란우산 해약 바뀐 행": np.nan})
    a, b = pd.read_csv(FROZEN_MDE), pd.read_csv(run / "mde.csv")
    n, w = same("mde", keep(a), keep(b), ["비교", "쌍", "asset"])
    rows.append({"파일": "mde.csv(동결 cand5_mde_prerun.csv 대비)", "대조 행": n, "최대 상대차": w, "제외": "ny_cancel 쌍(F1로 다시 계산)", "노란우산 해약 바뀐 행": np.nan})
    if QUICK:
        rows.append({"파일": "boot_stats.csv", "대조 행": 0, "최대 상대차": np.nan, "제외": "빠른 시험: 경로 수가 달라 건너뜀", "노란우산 해약 바뀐 행": np.nan})
    else:
        n, w = same("boot_stats", keep(old("boot_stats.csv")), keep(new("boot_stats.csv")), ["블록", "비교", "쌍", "asset", "m", "person"])
        rows.append({"파일": "boot_stats.csv", "대조 행": n, "최대 상대차": w, "제외": "ny_cancel 쌍", "노란우산 해약 바뀐 행": np.nan})
    t = pd.DataFrame(rows)
    assert t.loc[t["파일"] == "base_hist_wd36.csv", "노란우산 해약 바뀐 행"].iloc[0] > 0, "F1이 36회 해약 칸을 바꾸지 않음"
    return t


def hand_checks() -> pd.DataFrame:
    """설계서 4절 손계산(값은 cand5p._check 주석의 손계산)."""
    rows = [{"항목": "퇴직소득세 근속 3년, 퇴직소득 1,000만 원", "손계산": 132_000, "코드": float(CP.retire_tax(1e7, 36))},
            {"항목": "퇴직소득세 근속 14년, 퇴직소득 1억 원", "손계산": 2_717_000, "코드": float(CP.retire_tax(1e8, 168))}]
    hd, rt = CP.Q("bp_home_ded")["중소도시"], 0.0025
    ppl = CP.people(rt)
    rows.append({"항목": "B 금융재산(시험 금리 월 0.25%): 538,900 ÷ (0.0025 + 4%/12)", "손계산": 92_382_857.14, "코드": round(ppl["B"][2], 2)})
    for b, want in (("A", 349_700), ("B", 321_100), ("C", 0)):
        nps, home, fin, i0 = ppl[b]
        rows.append({"항목": f"기초연금 {b} (월, 시험 금리 월 0.25%, 사람 (가))", "손계산": want, "코드": float(CP.basic_pension(nps, 0.0, home, fin, hd, i0)[0])})
    A, B = ppl["A"], ppl["B"]
    rows += [{"항목": "H3 기초연금 A, 사람 (다) 사업소득 21,733,333 ÷ 12: 247만 − 2,271,111", "손계산": 198_888.89,
              "코드": round(float(CP.basic_pension(A[0], 0.0, A[1], A[2], hd, A[3], C.base_for(2e6) / 12)[0]), 2)},
             {"항목": "H3 기초연금 B, 사람 (나) 사업소득 8,333,333 ÷ 12: 소득인정액 > 247만", "손계산": 0,
              "코드": float(CP.basic_pension(B[0], 0.0, B[1], B[2], hd, B[3], C.base_for(5e5) / 12)[0])},
             {"항목": "M1(r3) 연금소득 1,800만 원, (가) 과표 0: (1,800만 − 공제 670만 − 기본공제 150만) × 6% × 1.1", "손계산": 646_800, "코드": float(CP.wd_tax(18e6, 0, .055))},
             {"항목": "M1 연금소득 1,800만 원, (다) 과표 21,733,333: 1,130만 × 15% × 1.1 < 분리 297만", "손계산": 1_864_500, "코드": float(CP.wd_tax(18e6, 2e6, .055))},
             {"항목": "M2 연금소득 1,000만 원, (가): 종합 (450만 − 기본공제 150만) × 6% × 1.1 < 분리 55만", "손계산": 198_000, "코드": float(CP.wd_tax(10e6, 0, .055))},
             {"항목": "M1(r3) 연금소득 1,500만 원, (가): (860만 − 기본공제 150만) × 6% × 1.1 < 분리 825,000 (R3-L9)", "손계산": 468_600, "코드": float(CP.wd_tax(15e6, 0, .055))},
             {"항목": "H3 연금소득 1,000만 원 + 국민연금 600만, (가): (950만 − 150만) − (150만 − 150만) = 800만 × 6% × 1.1", "손계산": 528_000, "코드": float(CP.wd_tax(10e6, 0, .055, 6e6))},
             {"항목": "M2(r3) 65세 이후 여력, C (가): 국민연금 1,440만 → 806만 − 150만 = 656만 × 6%", "손계산": 393_600, "코드": CP.room65(0, 14.4e6)},
             {"항목": "M3(r3) 70세 잔액 4,000만 원, (가): 3몫 × min(374,000, 586,667)", "손계산": 1_122_000, "코드": float(CP.rem_tax(40e6, 0, .044))},
             {"항목": "L1 4만 원은 이자에서만: 40만 + max(1만 − 4만, 0) + 재산 5만", "손계산": 450_000, "코드": float(CP.basic_pension(400_000, 0.0, 1e8, 2e7, hd, 10_000)[1])},
             {"항목": "L3 금융 1천만: 2천만 공제가 주택 몫을 깎지 않음 → 재산 1,500만 × 4% ÷ 12 + 40만", "손계산": 450_000, "코드": float(CP.basic_pension(400_000, 0.0, 1e8, 1e7, hd)[1])},
             {"항목": "각 괄호 0 하한(사업안내 78쪽), 대도시·집 1억·금융 2천만·이자 월 0.25%: 재산 환산 0 → 40만 + (5만 − 4만)", "손계산": 410_000,
              "코드": float(CP.basic_pension(400_000, 0.0, 1e8, 2e7, CP.Q("bp_home_ded")["대도시"], 2e7 * rt)[1])},
             {"항목": "각 괄호 0 하한, 대도시·집 1억·금융 3천만: 0 + 1천만 × 4% ÷ 12 + 40만 + (7.5만 − 4만)", "손계산": 468_333.33,
              "코드": round(float(CP.basic_pension(400_000, 0.0, 1e8, 3e7, CP.Q("bp_home_ded")["대도시"], 3e7 * rt)[1]), 2)}]
    o = {**CP.REC, "defer": True}; z = np.zeros((1, 168)); acc = CP.accumulate(z, z, z, 500_000, 1.0, o, None, 168)
    rows.append({"항목": "H2 수령 연기판, 수익 0·(다)·월 50만: 8,400만 × 0.956 + 환급 예금 1,386만", "손계산": 94_164_000,
                 "코드": float(CP.evaluate(acc, 500_000, 2e6, 168, "p70", o)["ps"][0])})
    rows.append({"항목": "H2 연기판 기초연금 B (가)·K2 넣음, 수익 0·월 50만: (161,100 + 141,100 + … + 61,100) × 12", "손계산": 7_999_200,
                 "코드": float(CP.evaluate(acc, 500_000, 0, 168, "p70", o, ppl)["bp"][("B", "과세분만", "넣음", "중소도시")][0]["ps"][0])})
    o3 = {**o, "D18": False}; a3 = CP.accumulate(z, z, z, 500_000, 1.0, o3, None, 168)
    rows.append({"항목": "M3(r3) 연결: 연기판·(가)·과세제외 안 함·월 50만·수익 0, 잔액 8,400만: 4.4% 3,696,000 − 6몫 × 409,200", "손계산": 1_240_800,
                 "코드": float(CP.evaluate(a3, 500_000, 0, 168, "p70", {**o3, "rem": "min"})["ps"][0] - CP.evaluate(a3, 500_000, 0, 168, "p70", o3)["ps"][0])})
    a5 = CP.accumulate(z, z, z, 500_000, 1.0, CP.REC, None, 168)
    exp = sum(12 * (0 if ia > 2.47e6 else max(2.47e6 - ia, 34_970)) for ia in (2_148_900 + a5["ny_old"][0, 12 * kk - 1] * .04 / 12 for kk in range(8, 14)))
    rows.append({"항목": "M5(r3) 노란우산 적립금 넣음, B (가)·월 50만: Σ 12 × max(247만 − (2,148,900 + 그해 첫날 적립금 × 4% ÷ 12), 34,970)", "손계산": round(exp, 2),
                 "코드": round(float(CP.evaluate(a5, 500_000, 0, 168, "p70", CP.REC, ppl)["bp"][("B", "과세분만", "안넣음", "중소도시")][0]["ny_old_in"][0]), 2)})
    e2 = CP.evaluate(a5, 500_000, 0, 168, "p70", CP.REC, ppl); Yb = a5["ny_old"][0, -1]
    rows.append({"항목": "R3-M1 사람 (가)·C, 수익 0·월 50만: 노란우산 노령 = 적립금 − 퇴직소득세(적립금 − 8,400만) (사업소득 0 → 국민연금 여력 안 씀)",
                 "손계산": round(float(Yb - CP.retire_tax(Yb - 84e6, 168)), 2), "코드": round(float(e2["bp"][("C", "과세분만", "안넣음", "중소도시")][2][0]), 2)})
    H5, z5 = CP.Q("H75"), np.zeros((1, CP.Q("H75")))                  # 설계서 8절
    a75 = CP.accumulate(z5, z5, z5, 500_000, 1.0, o, None, H5)
    a75b, a75k = (CP.accumulate(z5, z5, z5, mm, 1.0, CP.REC, None, H5) for mm in (500_000, 100_000))
    z8 = np.zeros((1, CP.Q("H80"))); a80 = CP.accumulate(z8, z8, z8, 500_000, 1.0, o, None, CP.Q("H80"))
    z9 = np.zeros((1, CP.Q("H90"))); a90 = CP.accumulate(z9, z9, z9, 500_000, 1.0, o, None, CP.Q("H90"))
    d8 = np.zeros((1, 168)); d8[0, 72:96] = .003; ax = CP.accumulate(z, z, d8, 500_000, 1.0, CP.REC, None, 168)
    vx = {g: CP.evaluate(ax, 500_000, 0, 168, "p70", {**CP.REC, "int_t": g}, {"X": (500_000, 5.65e8, 0.0, 0.0)})["bp"][("X", "과세분만", "안넣음", "중소도시")][0]["dep"][0]
          for g in ("same", "guide")}
    rows += [{"항목": "8-1 연기판 70세 개시 첫해(2040년 1월) 인출, 수익 0·월 50만: 70세 말 잔액 8,400만 ÷ 10", "손계산": 8_400_000, "코드": float(a75["wd"][1][0, 9])},
             {"항목": "8-1 연기판 기초연금 B (가)·과세분만·K2 개시 전만, 65~75세: 7,999,200 + (293,100 + 265,100 + 237,100 + 209,100 + 181,100) × 12", "손계산": 22_225_200,
              "코드": float(CP.evaluate(a75, 500_000, 0, H5, "p70", o, ppl)["bp"][("B", "과세분만", "넣음", "중소도시")][0]["ps"][0])},
             {"항목": "8-1 기본판(감사 H1), 수익 0·월 50만: 2039년 말 잔액 19,973,809.52(2039년 1월 27,947,619.05 ÷ 2 + 600만) → 2040~44년 ÷ 10·÷ 9·…·÷ 6 → 75세 말 절반",
              "손계산": 9_986_904.76, "코드": round(float(a75b["wd"][0][0]), 2)},
             {"항목": "8-1 ★ K1 전액 기본판 B (가)·K2 안넣음, 수익 0·월 10만(감사 L1): Σ 12 × max(247만 − (2,148,900 + 그해 인출 ÷ 12 + 인출 누계 × 4% ÷ 12), 34,970) "
                    "(인출액 = cand5p._check의 손 점화식)", "손계산": 25_220_514.29,
              "코드": round(float(CP.evaluate(a75k, 100_000, 0, H5, "p70", CP.REC, ppl)["bp"][("B", "전액", "안넣음", "중소도시")][0]["ps"][0]), 2)},
             {"항목": "80세 판(표 5-6) 연기판 기초연금 B (가)·과세분만·K2 개시 전만, 수익 0·월 50만, 65~80세: 7,999,200 + 12 × Σ(321,100 − 28,000n, n = 1~10)", "손계산": 28_051_200,
              "코드": float(CP.evaluate(a80, 500_000, 0, CP.Q("H80"), "p70", o, ppl)["bp"][("B", "과세분만", "넣음", "중소도시")][0]["ps"][0])},
             {"항목": "11절 90세 판(표 5-8) 같은 조건, 65~90세: 28,051,200 + 81~90세 인출 예금 8,400만 → (247만 − 2,428,900) × 12 × 10", "손계산": 32_983_200,
              "코드": float(CP.evaluate(a90, 500_000, 0, CP.Q("H90"), "p70", o, ppl)["bp"][("B", "과세분만", "넣음", "중소도시")][0]["ps"][0])},
             {"항목": "이자 시점 기준(사업안내 70쪽 표, 2026-11-08) 65세 첫해, 민감도(그해 이자)와의 차: 금리 2032·33년만 월 0.3%, 사람 X(국민연금 50만·집 5억6,500만) 예금 쪽, 2034년 1~3월 = 2032년 이자 "
                    "3,600만 × 0.3% = 108,000, 4월~ = 2033년 이자는 신규 수급자·그해 이자 0이라 미반영 → guide − same = −(108,000 − 40,000) × 3", "손계산": -204_000,
              "코드": float(vx["guide"] - vx["same"])},
             {"항목": "8-2 사업안내 70쪽 예시(5년 적금 40개월 해지, 이자 180만): (180만 − 40 × 4만) ÷ 12", "손계산": 16_666.67,
              "코드": round(float(CP.basic_pension(0, 0.0, 0.0, 0.0, hd, CP.term_income(1.8e6, 40, "예시"))[1]), 2)},
             {"항목": "8-2 같은 예시를 '추가 공제 만기 해 48만 상한'으로 읽으면: (180만 − 48만) ÷ 12 − 4만 (예시와 다름 → 기준 = 예시 해석)", "손계산": 70_000,
              "코드": float(CP.basic_pension(0, 0.0, 0.0, 0.0, hd, CP.term_income(1.8e6, 40, "상한"))[1])}]
    t = pd.DataFrame(rows); assert (t["손계산"] - t["코드"]).abs().max() < 1e-2
    return t


def people_table(ppl: dict, rbar: float) -> pd.DataFrame:
    """시뮬레이션 저축 없을 때 사람 A·B·C × 세금 그릇 (가)(나)(다)의 소득인정액·비율·기초연금(2026년 평균 예금 금리, 중소도시). 사업소득 = b/12(H3)."""
    hd, rows = CP.Q("bp_home_ded")["중소도시"], []
    for b, (nps, home, fin, i0) in ppl.items():
        for pn, room in C.rooms(CP.REC).items():
            biz = C.base_for(room) / 12; amt, ia = CP.basic_pension(nps, 0.0, home, fin, hd, i0, biz)
            rows.append({"사람": b, "세금 그릇": f"({pn})", "국민연금(월)": nps, "사업소득(월)": round(biz), "주택": int(home), "금융재산": round(fin),
                         "예금 이자(월, r̄ 고정)": round(i0), "소득인정액(월)": round(float(ia)), "선정기준액 대비": round(float(ia) / CP.Q("bp_sel"), 4),
                         "기초연금(월)": round(float(amt))})
    return pd.DataFrame(rows)


# 감사 r1 H2 대체 문장 앞 두 문장(감사 보고서 그대로). 최악 경로 문장은 build_doc이 CSV에서 만들고 '점검 3'에서 assert.
H2_HEAD = ("70세 N판 연금저축은 62세부터 해마다 잔액의 1/10~1/2을 꺼내 예금으로 옮긴다고 가정했다. F판 대비 중앙값 감소 대부분은 이 재배분 단계에서 나오며, "
           "세금·건보료 규칙의 몫이 아니다.")
# L16 점검 표 반올림: 실수 열은 소수 둘째 자리(끝 0 지움), 아주 작은 값은 지수 표기
num = lambda df: df.apply(lambda c: c.map(lambda v: "" if pd.isna(v) else (f"{v:.1e}" if 0 < abs(v) < 1e-3 else f"{v:,.2f}".rstrip("0").rstrip(".")))
                          if pd.api.types.is_float_dtype(c) else c)

GUIDE = ("**사업안내 기준 칸(★, 값 굵게) = K1 전액, 기본판 K2 안넣음, 연기판 K2 넣음** — 「2026년 기초연금 사업안내」(보건복지부, "
         "원문 발췌는 재배포 조건 미확인으로 저장소에 없음, 쪽 번호만) 인쇄 70~71쪽(조회되는 연금 월 수령액을 그대로 연금소득으로), 인쇄 92~93쪽(연금저축 = '정기 지급액 또는 최종 잔액', "
         "개시 뒤에는 연금소득으로만 → 개시 전 잔액만 금융재산). 나머지 K1·K2 칸 = 법 문언 해석(참고).")


def star(d: pd.DataFrame, cols, dcols=()) -> pd.DataFrame:
    """사업안내 기준 칸 표시: K1 전액·K2 안넣음 행의 기본판 열(cols), K1 전액·K2 넣음 행의 연기판 열(dcols)을 굵게 + '사업안내 기준' 열."""
    d = d.copy(); sb = (d.K1 == "전액") & (d.K2 == "안넣음"); sd = (d.K1 == "전액") & (d.K2 == "넣음") & bool(dcols)
    for mk, cs in ((sb, cols), (sd, dcols)):
        for c in cs:
            d[c] = d[c].astype(str).where(~mk, "**" + d[c].astype(str) + "**")
    lb = ("★ 기본판 열" + ("(연기판 열은 참고)" if dcols else ""), "★ 연기판 열(기본판 열은 참고)")
    d.insert(0, "사업안내 기준", np.where(sb, lb[0], np.where(sd, lb[1], "법 문언 해석(참고)")))
    return d


STAGES = {"가": "F판", "나": "F판 + 해마다 인출(인출액 F판 세율 4.4%, 건보·기초연금 없이)",
          "다": "(나) + N판 인출 과세(5.5%·종합과세 선택·1,500만 원 처리)", "라": "(다) + 건보료 S_hi"}


def decompose(out: Path, ppl: dict, x: dict = {}) -> None:
    """2번: 70세 연금저축(기준 셀, 역사 경로)을 단계별로 다시 계산. 단계 (마) = (다)·(라) + 기초연금(연금저축 쪽, 중소도시).
    x = 덧붙일 스위치(이자 시점 대조판 int_alt; 그때는 F판·N판 대조를 건너뜀)."""
    o0 = {**CP.REC, **x}; r = inp(o0); H = P("H70"); key = ["path", "asset", "m", "person"]
    opts = {"가": {**o0, **CP.F_ONLY}, "나": {**o0, "wtax": "F"}, "다": o0, "라": {**o0, "D11": "hi"}}
    w, bps = None, []
    for s, o in opts.items():
        df, bp = CP.run(r, o, H, "p70", bp=ppl if s in ("다", "라") else None)
        d = df[key + ["contrib", "ps"]].rename(columns={"ps": s}); w = d if w is None else w.merge(d, on=key + ["contrib"])
        if bp is not None:
            bps.append(bp[bp.region == "중소도시"][key + ["b", "K1", "K2", "bp_ps", "bp_dep", "bp_ny_old", "bp_ny_old_in"]].assign(기준=s))
    for s, f in () if x else (("가", "F"), ("다", "N")):           # 단계 (가)·(다) = F판·N판 기준 셀 그대로
        chk = w.merge(pd.read_csv(out.parent / f / "base_hist_p70.csv"), on=key)
        assert np.allclose(chk[s], chk.ps, rtol=1e-12, atol=0), f"원인 분해 ({s}) ≠ {f}판"
    w.to_csv(out / "decomp_p70.csv", index=False, encoding="utf-8-sig")
    pd.concat(bps).to_csv(out / "decomp_bp_p70.csv", index=False, encoding="utf-8-sig")
    log(f"{out.name}/decomp_p70.csv {len(w)}행")


VARIANTS = {"defer": {"defer": True},                       # H2 수령 연기판: 62~70세 인출 없음, 70세 잔액 4.4%
            "rem": {"rem": "min"},                          # r3 M3: 기본판 + 70세 잔액도 min(분리, 종합)(1,500만 원 이하로 나눠, 시간가치 무시)
            "defer_rem": {"defer": True, "rem": "min"}}     # r3 M3: 연기판 + 같은 잔액 규칙


def defer_run(out: Path, ppl: dict, x: dict = {}) -> None:
    """기준 셀 70세 대조판(VARIANTS). 표 1·3·5의 '연기판' 열(defer)과 표 1-1·3·5-3의 잔액 규칙 민감도판(rem·defer_rem). 파일 = {이름}_*.csv."""
    for v, flag in VARIANTS.items():
        o = {**CP.REC, **flag, **x}
        df, bp = CP.run(inp(o), o, P("H70"), "p70", bp=ppl)
        for d, name in ((df, f"{v}_hist_p70.csv"), (bp, f"{v}_bp_hist_p70.csv"), (CP.bp_stats(bp), f"{v}_bp_stats.csv"),
                        (pd.concat([C.loss_stats(df, a, b).assign(비교="p70", 쌍=f"{a}<{b}") for a, b in CP.PAIRS["p70"]]), f"{v}_stats.csv")):
            d.to_csv(out / name, index=False, encoding="utf-8-sig"); log(f"{out.name}/{name} {len(d)}행")


PANS = {"base": {}, "defer": {"defer": True}}
# 75세 판 민감도(한계 메우기 감사): H1 옛 '한꺼번에'(기본판 2040년 잔액 전부). M1 '이자 1년 늦게'는 사업안내 시점이 기준이 되며 지움(설계서 9절)
EXT_SENS = {"lump": ("base", {"lump75": True})}
K2M = lambda d: d.assign(K2뜻="넣음 = 개시 전 잔액만(사업안내 92~93쪽), 표 5의 '넣음'과 다름")   # 감사 L3, ext75·80·85·90 bp CSV
TERMS = {"ii": CP.Q("term"), "ii_만기+1년": (36, "예시", 1), "ii_만기+2년": (36, "예시", 2), "ii_상한": (36, "상한", 0)}   # 8-2, 판 (i) = 기존 bp_stats


def ext_inputs(rbar: float, H: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """8-1 입력: 실제 자료 r, (b)용 r_b(자료 끝 뒤 H(기본 75세)까지 주식·채권·예금 모두 r̄), 70세 비교 경로 시작 연도 st70."""
    H, h, r = H or CP.Q("H75"), P("H70"), inp(CP.REC)
    fut = pd.date_range(r.index[-1] + pd.offsets.MonthEnd(1), periods=H - h, freq="ME")
    return r, pd.concat([r, pd.DataFrame(rbar, index=fut, columns=r.columns)]), [s for s in C.starts(r, CP.REC) if r.index.get_loc(s) + h <= len(r)]


def ext_run(out: Path, ppl: dict, rbar: float, x: dict = {}) -> None:
    """설계서 8절. 8-1 75세 판: (a) 228개월 실제 자료가 있는 시작 연도만, (b) 70세 비교 경로 전부 + 자료 끝 뒤 달은 주식·채권·예금 모두 r̄.
    (b)에서 (a)와 겹치는 경로는 (a)와 같은 값인지 대조. 80세 판(표 5-6): (a)만. 8-2 3년 정기예금 판(65~70세 창): TERMS × 기본·연기판.
    x = 덧붙일 스위치(이자 시점 대조판 int_alt; 그때는 EXT_SENS 민감도와 잔액 비율을 건너뜀)."""
    H, h = CP.Q("H75"), P("H70"); r, r_b, st70 = ext_inputs(rbar)
    npath = lambda n: sum(r.index.get_loc(s) + n <= len(r) for s in C.starts(r, CP.REC))   # 실제 자료가 n개월 있는 시작 연도 수
    save = lambda d, name: (d.to_csv(out / name, index=False, encoding="utf-8-sig"), log(f"{out.name}/{name} {len(d)}행"))
    k2m, kh = K2M, ["path", "asset", "m", "person"]
    runs = {pan: ({**CP.REC, **flag, **x}, ("hist", "bp_hist", "bp_stats")) for pan, flag in PANS.items()}
    runs.update({nm: ({**CP.REC, **PANS[pan], **flag}, ("hist", "bp_hist", "bp_stats")) for nm, (pan, flag) in ({} if x else EXT_SENS).items()})
    for nm, (o, keep) in runs.items():
        got = {}
        for src, rr_, st in (("a", r, None), ("b", r_b, st70)):
            df, bp = CP.run(rr_, o, H, "p70", st=st, bp=ppl); got[src] = (df, bp)
            for d, f in ((df, "hist"), (k2m(bp), "bp_hist"), (k2m(CP.bp_stats(bp)), "bp_stats")):
                if f in keep:
                    save(d, f"ext75{src}_{nm}_{f}.csv")
        (da, ba), (db, bb) = got["a"], got["b"]
        assert da.path.nunique() < db.path.nunique() == len(st70)
        same(f"ext75 {nm} (b)=(a)", da, db[db.path.isin(da.path)], kh)
        same(f"ext75 {nm} bp (b)=(a)", ba, bb[bb.path.isin(ba.path)], kh + ["b", "K1", "K2", "region"])
        assert da.path.nunique() == npath(H)
    H8 = CP.Q("H80")                                     # 표 5-6: 80세 판, (a) 실제 자료만(75세 판 (a)와 같은 규칙)
    for pan, flag in PANS.items():
        df, bp = CP.run(r, {**CP.REC, **flag, **x}, H8, "p70", bp=ppl)
        assert df.path.nunique() == npath(H8) and set(df.path) <= set(pd.read_csv(out / f"ext75a_{pan}_hist.csv").path)
        save(df, f"ext80a_{pan}_hist.csv"); save(k2m(bp), f"ext80a_{pan}_bp_hist.csv"); save(k2m(CP.bp_stats(bp)), f"ext80a_{pan}_bp_stats.csv")
    save(pd.DataFrame({"나이": [70, 75, 80, 81], "개월": [h, H, H8, H8 + 12], "시작 연도": [npath(n) for n in (h, H, H8, H8 + 12)]}), "ext_paths.csv")
    if not x:                                            # 재감사 중간 1: 75세 말 잔액 ÷ 2040년 초(인출 전) 잔액, (a) 경로·자산 A
        eq, bd, dep, keys = C.windows(r, C.starts(r, CP.REC), H)
        wd = {pan: CP.accumulate(eq, bd, dep, M, P("w_eq")["A"], {**CP.REC, **flag}, [int(s[5:]) for s in keys], H)["wd"] for pan, flag in PANS.items()}
        rat = pd.DataFrame({"path": keys, **{pan: v[0] / (10 * v[1][:, h // 12 - CP.WD0]) for pan, v in wd.items()}})
        assert np.allclose(rat.base, rat.defer, rtol=1e-12, atol=0)   # 2040년부터 두 판 같은 ÷ 10 … 계획·같은 수익 → 비율 같음
        save(rat, "ext75a_rem_ratio.csv")
    for pan, flag in PANS.items():
        for nm, t in TERMS.items():
            bp = CP.run(r, {**CP.REC, **flag, **x, "term": t}, h, "p70", bp=ppl)[1]          # 감사 L2: 경로별 표도 저장
            save(bp, f"term_{nm}_{pan}_bp_hist.csv"); save(CP.bp_stats(bp), f"term_{nm}_{pan}_bp_stats.csv")
    hd, rows = CP.Q("bp_home_ded")["중소도시"], []
    for b, (nps, home, fin, i0) in ppl.items():
        for pn, room in C.rooms(CP.REC).items():
            biz = C.base_for(room) / 12
            for nm, t, mat in [("i", None, "해마다")] + [(nm, t, x) for nm, t in TERMS.items() if t[2] == 0 for x in ("만기 해", "만기 아닌 해")]:
                intr = i0 if t is None else (CP.term_income(i0 * t[0], t[0], t[1]) if mat == "만기 해" else 0.0)
                amt, ia = CP.basic_pension(nps, 0.0, home, fin, hd, intr, biz)
                # 감사 H2: 3년(36개월) 동안 소득인정액에 들어가는 이자(월 4만 공제 뒤) 합 — (i) 36 × max(i0 − 4만, 0), (ii) 만기 해 12 × max(월 이자 − 4만, 0)
                tot3 = 36 * max(i0 - CP.Q("bp_int_ded"), 0) if t is None else 12 * max(CP.term_income(i0 * t[0], t[0], t[1]) - CP.Q("bp_int_ded"), 0)
                rows.append({"사람": b, "세금 그릇": f"({pn})", "판": nm, "해": mat, "이자소득(월, 4만 공제 전)": round(intr),
                             "소득인정액(월)": round(float(ia)), "선정기준액 대비": round(float(ia) / CP.Q("bp_sel"), 4), "기초연금(월)": round(float(amt)),
                             "3년 인정 이자 합": round(tot3)})
    tp = pd.DataFrame(rows); save(tp, "term_people.csv")
    t3 = tp[tp["사람"] == "B"].groupby("판")["3년 인정 이자 합"].first()
    assert abs(t3["i"] - t3["ii"]) <= 1 and t3["ii_상한"] > t3["ii"], t3   # 예시 해석 = 1년 상품 셋(i0 ≥ 4만이면 식이 같음), 상한 해석은 공제가 적어 더 큼


LATE = {85: "H85", 90: "H90"}
NB_C, CH = 1000, 100                                  # (c) 꼬리 수(회원 지시, 빠른 시험도 같음), 한 번에 계산할 꼬리 수(메모리)
FEW, FEWC = 5, "표본 부족(경로 5개 미만)"               # (a) 표시 기준(설계서 11절, 결과 전에 정함), CSV 열 이름(감사 L1)


def ext_late(out: Path, ppl: dict, rbar: float) -> None:
    """설계서 11절, 표 5-8: 85·90세 판(75·80세 판과 같은 규칙). (a) 실제 자료가 H개월 있는 시작 연도만, (b) 70세 비교 경로 전부 + 자료 끝 뒤 주식·채권·예금 모두 r̄,
    (c) (b)에서 자료 끝 뒤 주식 월수익만 입력 주식 월수익 전체(1991-04~)에서 정상 블록 부트스트랩(평균 블록 12개월 = 기존 '12개월' 블록, seed)한 NB_C 꼬리로 — ★ 칸만.
    꼬리 j 하나를 모든 시작 연도에 같은 순서로(자료 끝 다음 달 = 꼬리 첫 달), 85세는 90세 꼬리의 앞부분. (c) 손해 = 꼬리마다 경로 중 연금저축 < 예금 수."""
    save = lambda d, name: (d.to_csv(out / name, index=False, encoding="utf-8-sig"), log(f"{out.name}/{name} {len(d)}행"))
    kh, k2s, paths_, rows = ["path", "asset", "m", "person"], {"base": "안넣음", "defer": "넣음"}, [], []
    r0 = inp(CP.REC)
    T = BS.paired_resample_paths([r0["eq"]], NB_C, CP.Q("H90") - P("H70"), mean_block=boot_blocks(r0)["12개월"], seed=P("seed"))[0]
    for age, hk in LATE.items():
        H = CP.Q(hk); r, r_b, st70 = ext_inputs(rbar, H)
        real = np.array([len(r) - r.index.get_loc(s) for s in st70])         # 시작 달부터 자료 끝까지 개월 수
        fill, na = H - real[real < H], int((real >= H).sum())
        eq, bd, dep, keys = C.windows(r_b, st70, H); off = np.arange(H) - real[:, None]
        assert keys == [s.strftime("%Y-%m") for s in st70] and off.max() < T.shape[1]
        moved = np.zeros(len(keys), bool)                                    # 감사 M1: 꼬리에 따라 값이 바뀐 경로(★ 칸 어디서든)
        for pan, flag in PANS.items():
            o = {**CP.REC, **flag}; got = {}
            for src, rx, st in (("a", r, None), ("b", r_b, st70)):
                df, bp = CP.run(rx, o, H, "p70", st=st, bp=ppl); got[src] = (df, bp)
                tag = (lambda d: d.assign(**{FEWC: na < FEW})) if src == "a" else (lambda d: d)   # 감사 L1
                save(tag(df), f"ext{age}{src}_{pan}_hist.csv"); save(tag(K2M(bp)), f"ext{age}{src}_{pan}_bp_hist.csv")
                save(tag(K2M(CP.bp_stats(bp))), f"ext{age}{src}_{pan}_bp_stats.csv")
            (da, ba), (db, bb) = got["a"], got["b"]
            assert da.path.nunique() == (real >= H).sum() and db.path.nunique() == len(st70)
            assert set(da.path) <= set(pd.read_csv(out / f"ext80a_{pan}_hist.csv").path)
            same(f"ext{age} {pan} (b)=(a)", da, db[db.path.isin(da.path)], kh)
            same(f"ext{age} {pan} bp (b)=(a)", ba, bb[bb.path.isin(ba.path)], kh + ["b", "K1", "K2", "region"])
            # (c): 꼬리 −1 = r̄(점검: (b)와 같아야 함), 0..NB_C−1 = 부트스트랩
            sb = bb[(bb.asset == "A") & (bb.m == M) & (bb.K1 == "전액") & (bb.K2 == k2s[pan]) & (bb.region == "중소도시")]
            Tx = np.vstack([np.full(T.shape[1], rbar), T]); D = np.arange(-1, NB_C)
            for J in (D[i:i + CH] for i in range(0, len(D), CH)):
                E = np.concatenate([np.where(off >= 0, Tx[j + 1][np.clip(off, 0, None)], eq) for j in J])
                rep = lambda x: np.tile(x, (len(J), 1))
                acc = CP.accumulate(E, rep(bd), rep(dep), M, P("w_eq")["A"], o, [int(k[5:]) for k in keys] * len(J), H)
                for pn, room in C.rooms(o).items():
                    e = CP.evaluate(acc, M, room, H, "p70", o, ppl)
                    for b in ppl:
                        tot, psb, _ = e["bp"][(b, "전액", k2s[pan], "중소도시")]
                        x = ((psb + tot["ps"]) - (e["dep"] + tot["dep"])).reshape(len(J), -1) / e["contrib"]
                        y = (tot["ps"] - tot["dep"]).reshape(len(J), -1) / e["contrib"]
                        g = sb[(sb.person == pn) & (sb.b == b)].set_index("path").loc[keys]
                        xb = ((g.ps - g.dep) / g.contrib).to_numpy()
                        assert np.allclose(x[:, real >= H], xb[real >= H], rtol=1e-12, atol=0)    # 꼬리 없는 경로 = (a)·(b) 값, 모든 꼬리에서
                        if J[0] == -1:
                            assert np.allclose(x[0], xb, rtol=1e-12, atol=1e-15)                 # 꼬리 r̄ = (b)
                        k = J >= 0
                        moved |= ~np.isclose(x[k], xb, rtol=1e-12, atol=0).all(0)
                        rows.append(pd.DataFrame({"나이": age, "판": pan, "person": pn, "b": b, "draw": J[k], "n": x.shape[1],
                                                  "loss_n": (x[k] < 0).sum(1), "median_gap": np.median(x[k], 1), "bp_gap_median": np.median(y[k], 1)}))
            log(f"ext{age} {pan} (c) {NB_C}꼬리 끝")
        # 감사 M1: 바뀐 경로 = 꼬리가 있는 경로 중 가장 늦게 시작한 연도들(이른 경로는 꼬리 시작 전 잔액 0). 꼬리 평균 > r̄(평균도 올린 판)
        tm = float(T[:, :H - P("H70")].mean())
        assert moved.any() and not moved[real >= H].any() and (np.flatnonzero(moved) == np.arange(len(keys) - moved.sum(), len(keys))).all() and tm > rbar
        paths_.append({"나이": age, "개월": H, "(a) 경로": na, "(b) 경로": len(st70), "채운 경로": len(fill),
                       "채운 달 최소": int(fill.min()), "채운 달 최대": int(fill.max()), FEWC: na < FEW, "(c) 꼬리로 바뀐 경로": int(moved.sum()),
                       "(c) 바뀐 경로 시작": f"{keys[np.flatnonzero(moved)[0]][:4]}~{keys[-1][:4]}", "(c) 꼬리 주식 월평균": tm, "(c) 꼬리 평균 ÷ r̄": tm / rbar})
    save(pd.DataFrame(paths_), "ext_late_paths.csv"); save(pd.concat(rows, ignore_index=True), "ext_late_c.csv")


def guide_check(N: Path) -> None:
    """각 괄호 0 하한 수정(2026-11-07) 대조: 수정 전 r3 코드로 사업안내식을 따로 계산한 guide_floor_check_20261107.csv(바뀌는 칸 = 사람 A·대도시만)의
    *_guide 값 = 이번 bp_stats(기본판)·defer_bp_stats(연기판)."""
    g = pd.read_csv(OUT / "guide_floor_check_20261107.csv")
    assert (g.b == "A").all() and (g.region == "대도시").all()
    key = ["asset", "m", "person", "b", "K1", "K2", "region", "쌍"]
    for pan, f in (("기본판", "bp_stats.csv"), ("연기판", "defer_bp_stats.csv")):
        gg = g[g["판"] == pan]; j = gg.merge(pd.read_csv(N / f), on=key, how="left")
        assert len(j) == len(gg) > 0
        for c in [c[:-6] for c in g.columns if c.endswith("_guide")]:
            assert np.allclose(j[c], j[c + "_guide"], rtol=1e-12, atol=0, equal_nan=True), (pan, c)
    log(f"사업안내 각 괄호 0 하한 대조 통과({len(g)}행)")


INT_ALT = {"int_t": "same" if CP.REC["int_t"] == "guide" else "guide"}
INT_NAME = {"same": "그해 이자를 그해 소득(연구자 가정)", "guide": "사업안내 70쪽 표(1~3월 전전년도·4~12월 전년도 이자)"}


def int_alt(N: Path, ppl: dict, rbar: float) -> None:
    """이자 반영 시점 대조판: 기초연금이 들어가는 표(5·5-1~5-6·7-1)의 입력을 REC와 반대 int_t로 다시 계산해 N/intalt/에 같은 파일 이름으로."""
    d = N / "intalt"; d.mkdir(); o = {**CP.REC, **INT_ALT}
    bp = CP.run(inp(o), o, P("H70"), "p70", bp=ppl)[1]
    bp.to_csv(d / "bp_hist_p70.csv", index=False, encoding="utf-8-sig"); CP.bp_stats(bp).to_csv(d / "bp_stats.csv", index=False, encoding="utf-8-sig")
    decompose(d, ppl, INT_ALT); defer_run(d, ppl, INT_ALT); ext_run(d, ppl, rbar, INT_ALT)


def int_compare(N: Path) -> tuple[pd.DataFrame, bool]:
    """표 5·5-1·5-2·5-3·5-4·5-5·5-6·7-1에 실리는 칸(월 30만 원·주식 100%, 반올림 전 값): N(기준 int_t) 대 N/intalt.
    반환 (표별 요약, 기준을 바꿀 조건 = 손해 건수 바뀐 칸 0 · 차이 중앙값 변화 모두 < 0.01). 바뀐 칸 = N/int_timing_cells.csv."""
    k2s, ix, pn = {"base": "안넣음", "defer": "넣음"}, ["asset", "m", "person", "b", "K1", "K2", "region"], {"base": "기본판", "defer": "연기판"}

    def rd(f, **kw):                                   # 표에 실리는 칸: 월 30만·자산 A(stats 파일은 연금저축 < 예금 쌍) + kw 조건
        d = pd.read_csv(f); keep = (d.m == M) & (d.asset == "A")
        if "쌍" in d:
            keep &= d["쌍"] == "ps<dep"
        for c, v in kw.items():
            keep &= d[c].isin(v)
        return d[keep]
    st = lambda f, **kw: rd(f, **kw).set_index(ix)[["loss_n", "median_gap", "bp_gap_median"]]

    def hs(f, by, **kw):                               # 경로별 표: 손해 = ps < dep, 중앙값 ÷ 누적 납입
        d = rd(f, region=["중소도시"], **kw); d = d.assign(구간=np.where(d.path.str[:4].astype(int) <= 2002, "~2002", "2003~"))
        g = d.assign(l=d.ps < d.dep, x=(d.ps - d.dep) / d.contrib, y=(d.bp_ps - d.bp_dep) / d.contrib).groupby(by)
        return pd.DataFrame({"loss_n": g.l.sum(), "median_gap": g.x.median(), "bp_gap_median": g.y.median()})
    cat = lambda R, fs, f: pd.concat({nm: f(R / fn) for nm, fn in fs.items()}, names=["판"])
    pan2 = {"기본판": "bp_stats.csv", "연기판": "defer_bp_stats.csv"}
    T = {"표 5": lambda R: cat(R, pan2, lambda p: st(p, region=["중소도시"])),
         "표 5-1": lambda R: st(R / "bp_stats.csv", b=["B"]),
         "표 5-2": lambda R: hs(R / "bp_hist_p70.csv", ["구간", "K1", "K2", "person"], b=["B"]),
         "표 5-3": lambda R: cat(R, {**pan2, "잔액 min": "rem_bp_stats.csv", "연기판·잔액 min": "defer_rem_bp_stats.csv"}, lambda p: st(p, region=["중소도시"])),
         "표 5-4": lambda R: pd.concat({(s, pn[pan]): hs(R / f"ext75{s}_{pan}_bp_hist.csv", ["person", "b"], K1=["전액"], K2=[k2s[pan]])
                                        for s in "ab" for pan in PANS}, names=["자료", "판"]),
         "표 5-5": lambda R: pd.concat({(pn[pan], nm): st(R / (f"term_{nm}_{pan}_bp_stats.csv" if nm != "i" else {"base": "bp_stats.csv", "defer": "defer_bp_stats.csv"}[pan]),
                                                      region=["중소도시"], K1=["전액"], K2=[k2s[pan]], b=["A", "B"])
                                        for pan in PANS for nm in ["i", *TERMS]}, names=["판", "해석"]),
         "표 5-6": lambda R: pd.concat({pn[pan]: hs(R / f"ext80a_{pan}_bp_hist.csv", ["person", "b"], K1=["전액"], K2=[k2s[pan]])   # 감사 L3(2026-11-08)
                                        for pan in PANS}, names=["판"]),
         "표 7-1": lambda R: rd(R / "decomp_bp_p70.csv").groupby(["기준", "b", "K1", "K2", "person"])[       # 이 파일은 중소도시만
             ["bp_ps", "bp_dep", "bp_ny_old", "bp_ny_old_in"]].median() / (P("H70") * M)}   # 표 번호 순서(정리 감사 L1)
    rows, cells = [], []
    for nm, f in T.items():
        a, b = f(N), f(N / "intalt"); j = a.join(b, rsuffix="_alt", how="outer")
        assert len(j) == len(a) == len(b) > 0, nm
        mc = [c for c in a.columns if c != "loss_n"]
        dl = (j.loss_n_alt - j.loss_n) if "loss_n" in a else pd.Series(0, index=j.index)
        dm = pd.concat([(j[c + "_alt"] - j[c]).abs() for c in mc], axis=1).max(axis=1)
        rows.append({"표": nm, "칸": len(j), "손해 건수 바뀐 칸": int((dl != 0).sum()) if "loss_n" in a else "—(손해 열 없음)",
                     "손해 건수 최대 변화": int(dl.abs().max()), "차이 중앙값 최대 변화": float(dm.max()), "변화 ≥ 0.01 칸": int((dm >= 0.01).sum())})
        cells.append(j[(dl != 0) | (dm >= 0.01)].reset_index().assign(표=nm))
    s = pd.DataFrame(rows); ok = bool((s["손해 건수 최대 변화"] == 0).all() and (s["차이 중앙값 최대 변화"] < 0.01).all())
    s.to_csv(N / "int_timing_compare.csv", index=False, encoding="utf-8-sig")
    pd.concat(cells, ignore_index=True).to_csv(N / "int_timing_cells.csv", index=False, encoding="utf-8-sig")
    log(f"이자 시점 대조(기준 {CP.REC['int_t']} 대 {INT_ALT['int_t']}): 기준 바꿀 조건 {ok}\n" + s.to_string(index=False))
    return s, ok


STAR = {"예시": "기준(원문 예시: 그해 4월~이듬해 3월만 0)", "1~3월도": "대안 ①(첫해 1~3월도 0)", "없음": "대안 ②(※ 안 씀)"}


def star_alt(N: Path, ppl: dict, rbar: float) -> None:
    """감사 M1(2026-11-08): 65세 첫해 신규 수급자 ※ 해석(cand5p.guide_int star)별 표 5-5 칸(판 (i)·(ii) 5해석 × 기본판·연기판, 창 70세).
    정리 감사 L2: 표 5-4(75세 (a)·(b))·표 5-6(80세 (a)) 판도(해석 i). 기준 행 = 이미 있는 bp_stats·defer_bp_stats·term_*·ext*_bp_stats,
    대안 ①·② = 다시 계산 → N/int_star_alt.csv(bp_stats 열 + ※·판·해석·창). 75·80세 판은 기준도 다시 계산해 기존 파일과 같은지 대조."""
    rows = []
    for pan, flag in PANS.items():
        for nm in ["i", *TERMS]:
            f = N / (f"term_{nm}_{pan}_bp_stats.csv" if nm != "i" else {"base": "bp_stats.csv", "defer": "defer_bp_stats.csv"}[pan])
            rows.append(pd.read_csv(f).assign(**{"※": "예시", "판": pan, "해석": nm, "창": "70세"}))
            for s in ("1~3월도", "없음"):
                o = {**CP.REC, **flag, "int_star": s, **({"term": TERMS[nm]} if nm != "i" else {})}
                rows.append(CP.bp_stats(CP.run(inp(o), o, P("H70"), "p70", bp=ppl)[1]).assign(**{"※": s, "판": pan, "해석": nm, "창": "70세"}))
    r, r_b, st70 = ext_inputs(rbar)
    for w, (fn, H, rx, st) in {"75세 (a)": ("ext75a", CP.Q("H75"), r, None), "75세 (b)": ("ext75b", CP.Q("H75"), r_b, st70),
                               "80세 (a)": ("ext80a", CP.Q("H80"), r, None)}.items():
        for pan, flag in PANS.items():
            for s in STAR:
                o = {**CP.REC, **flag, "int_star": s}; d = CP.bp_stats(CP.run(rx, o, H, "p70", st=st, bp=ppl)[1])
                if s == "예시":
                    same(f"star_alt {w} {pan}", pd.read_csv(N / f"{fn}_{pan}_bp_stats.csv").drop(columns="K2뜻"), d, ["asset", "m", "person", "b", "K1", "K2", "region", "쌍"])
                rows.append(d.assign(**{"※": s, "판": pan, "해석": "i", "창": w}))
    d = pd.concat(rows, ignore_index=True); d.to_csv(N / "int_star_alt.csv", index=False, encoding="utf-8-sig"); log(f"N/int_star_alt.csv {len(d)}행")


def build_doc(run: Path, rbar: float, period: str) -> Path:
    """결과 md: 표·숫자는 전부 run 폴더 CSV에서. 판정 없는 기술."""
    F, N = run / "F", run / "N"
    ppl = pd.read_csv(run / "people_2026.csv")
    fB = ppl.loc[ppl["사람"] == "B", "금융재산"].iloc[0]
    key, frac = ["비교", "쌍", "asset", "m", "person"], lambda k, n: f"{int(k)}/{int(n)}"
    dc = pd.read_csv(N / "decomp_p70.csv"); dc = dc[(dc.m == M) & (dc.asset == "A")]
    md1 = lambda x, p: (x / dc.contrib)[dc.person == p].median()
    med = lambda x: {f"사람 ({p})": f3(md1(x, p)) for p in ("가", "나", "다")}
    t7 = pd.DataFrame([{"단계": "(가) F판 70세 금액", **med(dc["가"])}] +
                      [{"단계": f"({b}) − ({a}): {STAGES[b]}", **med(dc[b] - dc[a])} for a, b in (("가", "나"), ("나", "다"), ("다", "라"))] +
                      [{"단계": "합계 (다) − (가) = 표 3 연금저축 70세 중앙값", **med(dc["다"] - dc["가"])}])
    db = pd.read_csv(N / "decomp_bp_p70.csv"); db = db[(db.m == M) & (db.asset == "A")]
    g7 = db.groupby(["기준", "b", "K1", "K2", "person"])
    t7b = pd.concat([(g7[c].median() / (P("H70") * M)).map(f3).unstack("person").rename(columns=lambda p, nm=nm: f"{nm} ({p})")
                     for c, nm in (("bp_ps", "연금저축"), ("bp_dep", "예금"), ("bp_ny_old", "노란우산 안넣음"), ("bp_ny_old_in", "노란우산 넣음"))], axis=1).reset_index()
    t7b["기준"] = "(마) = (" + t7b["기준"] + ") + 기초연금"
    mde = pd.read_csv(run / "mde.csv")
    stN, stF, chN = pd.read_csv(N / "grid_stats.csv"), pd.read_csv(F / "grid_stats.csv"), pd.read_csv(N / "change_table.csv")
    boot = pd.read_csv(N / "boot_stats.csv").pivot_table(index=key, columns="블록", values="p_loss")[list(C.BOOT_BLOCKS)]
    boot = boot.apply(lambda r: "/".join(f"{x:.3f}" for x in r), axis=1).rename("boot").reset_index()
    bootD = pd.read_csv(N / "defer_boot_stats.csv").pivot_table(index=key, columns="블록", values="p_loss")[list(C.BOOT_BLOCKS)]   # R3-L4
    boot = boot.merge(bootD.apply(lambda r: "/".join(f"{x:.3f}" for x in r), axis=1).rename("boot_D").reset_index(), on=key, how="left")
    dfs = (pd.read_csv(N / "defer_stats.csv").rename(columns={"loss_n": "loss_n_D", "median_gap": "median_gap_D", "worst": "worst_D"})
           [key + ["loss_n_D", "median_gap_D", "worst_D"]])
    base = (stN[(stN.cell == "base") & (stN.m == M)].merge(stF[stF.cell == "base"][key + ["loss_n", "median_gap", "worst"]], on=key, suffixes=("", "_F"))
            .merge(mde[["비교", "쌍", "asset", "mde"]], on=["비교", "쌍", "asset"], how="left")
            .merge(boot, on=key, how="left").merge(dfs, on=key, how="left"))
    # L9: MDE가 NaN이면 'MDE 이상'이 아니라 '비교 불가'
    tag = lambda r: "비교 불가" if pd.isna(r.mde) else (C.sentence("", r.median_gap, r.mde).strip(" ()") or "MDE 이상")
    BOOT_COL = f"부트스트랩 손해 확률({'/'.join(C.BOOT_BLOCKS)})"

    def loss_table(keys):
        b = base[base["비교"].isin(keys)].copy()
        b["손해 경로"] = [frac(k, n) for k, n in zip(b.loss_n, b.n)]
        b["손해 경로(F판)"] = [frac(k, n) for k, n in zip(b.loss_n_F, b.n)]
        b["차이 중앙값"], b["차이 중앙값(F판)"], b["최악"] = b.median_gap.map(f3), b.median_gap_F.map(f3), b.worst.map(f3)
        b["MDE"] = b.mde.map(lambda x: f"{x:.3f}"); b["판독"] = b.apply(tag, axis=1)
        b["n_eff"], b[BOOT_COL] = b.n_eff.astype(int), b.boot
        b["시점"], b["비교 쌍"], b["사람"] = b["비교"].map(WHEN), b["쌍"].map(pair), "(" + b.person + ")"
        cols = ["시점", "비교 쌍", "asset", "사람", "손해 경로", "차이 중앙값", "손해 경로(F판)", "차이 중앙값(F판)", "최악", "n_eff", BOOT_COL, "MDE", "판독"]
        if "p70" in keys:                                   # H2 수령 연기판 열(70세만), L11 연기판 최악
            b["손해 경로(연기판)"] = [frac(k, n) if pd.notna(k) else "—" for k, n in zip(b.loss_n_D, b.n)]
            b["차이 중앙값(연기판)"] = b.median_gap_D.map(lambda x: "—" if pd.isna(x) else f3(x))
            b["최악(연기판)"] = b.worst_D.map(lambda x: "—" if pd.isna(x) else f3(x))
            cols[6:6] = ["손해 경로(연기판)", "차이 중앙값(연기판)"]
            cols.insert(cols.index("최악") + 1, "최악(연기판)")
            b[BOOT_COL + "(연기판)"] = b.boot_D.fillna("—")
            cols.insert(cols.index(BOOT_COL) + 1, BOOT_COL + "(연기판)")
        return md_table(b[cols].rename(columns={"asset": "자산"}))

    meta = json.load(open(N / "boot_meta.json", encoding="utf-8"))
    # M5 판독 범례: 독립 구간 수와 동결 사전 MDE 대조는 CSV에서
    fz = pd.read_csv(FROZEN_MDE).merge(mde, on=["비교", "쌍", "asset"], suffixes=("_old", ""))
    dmax = float((fz.mde_old - fz.mde).abs().max())
    newp = sorted(set(mde["비교"].map(WHEN) + " " + mde["쌍"].map(pair)) - set(fz["비교"].map(WHEN) + " " + fz["쌍"].map(pair)))
    ne = base.n_eff.astype(int)
    # M8: n_eff가 작아 정규근사 대신 t분포(자유도 n_eff − 1)면 MDE가 몇 배인지, 그 기준이면 'MDE 이상' 중 문턱 아래로 가는 칸
    from scipy.stats import norm, t as tdist
    tmul = lambda n: (tdist.ppf(.975, n - 1) + tdist.ppf(.8, n - 1)) / (norm.ppf(.975) + norm.ppf(.8))
    big = base[base.apply(tag, axis=1) == "MDE 이상"]
    tlow = big[big.median_gap.abs() < big.mde * big.n_eff.map(tmul)]
    cell = lambda r: f"{WHEN[r['비교']]} {pair(r['쌍'])} 자산 {r['asset']} ({r['person']})"
    cells = lambda d: ", ".join(cell(r) for _, r in d.iterrows()) or "없음"
    nreg = int(pd.read_csv(run / "regress_F_vs_frozen.csv").set_index("파일").filter(like="mde", axis=0)["대조 행"].iloc[0])
    legend = (f"판독: '식별 안 됨' = |차이 중앙값| < MDE. 'MDE 이상'은 통계적 식별을 뜻하지 않는다(독립 구간 {ne.min()}~{ne.max()}개). "
              + (f"새로 계산한 MDE는 동결된 사전값(`cand5_mde_prerun.csv`)과 같다(같은 쌍 {len(fz)}행, 최대 차 {dmax:.1e})." if dmax < 1e-12
                 else f"⚠ 새로 계산한 MDE가 동결 사전값과 다르다(최대 차 {dmax:.3g}).")
              + (f" 사전값이 따로 없는 새 쌍: {', '.join(newp)}." if newp else "")
              + f" (점검 1의 mde.csv 대조 {nreg}행은 노란우산 해약 쌍을 뺀 행이고, 여기 {len(fz)}행은 해약 쌍까지 넣은 같은 쌍 전체다 — L15.)"
              + f" MDE는 정규근사(z = 2.802)다. 자유도 n_eff − 1의 t분포면 MDE가 n_eff {ne.max()}에서 ×{tmul(ne.max()):.2f}, {ne.min()}에서 ×{tmul(ne.min()):.2f}가 되고, "
              f"그 기준이면 'MDE 이상' {len(big)}칸 중 {len(tlow)}칸({cells(tlow)})이 문턱 아래다. MDE는 동결 사전값이라 판독 칸은 정규근사 그대로 둔다. "
              f"표 1·2의 {len(base)}칸에 다중비교 보정은 하지 않았다(감사 r2 M8).")
    # ── 요약 자동 문장(감사 r2 N-H1). 최악 비교는 연금저축 쌍만, 같은 규칙에서 인출만 다른 연기판과(노란우산 < 예금 쪽 변화는 퇴직소득세 몫).
    # 이 규칙(역사 최악 비교·월 30만 기준 + 부트스트랩·손해 건수·납입액별 개수·잔액 규칙판)은 결과를 본 뒤 정했다(문장에도 적음).
    ps70 = lambda d: d[(d["비교"] == "p70") & d["쌍"].str.startswith("ps<")]
    eps = 1e-12

    def cmp(d):                                       # L9: 같음·NaN을 '나빠짐'으로 세지 않음
        assert d[["worst", "worst_D"]].notna().all().all(), "최악 NaN"
        return d.worst > d.worst_D + eps, d.worst < d.worst_D - eps
    p70 = ps70(base); up, dn_ = cmp(p70); eq_ = ~up & ~dn_
    dn, neg, more = p70[dn_], p70[p70.worst < 0], p70[p70.loss_n > p70.loss_n_D]
    allm = ps70(stN[stN.cell == "base"]).merge(pd.read_csv(N / "defer_stats.csv"), on=key, suffixes=("", "_D"))
    bym = {m: f"{int(cmp(g)[0].sum())}/{len(g)}" for m, g in allm.groupby("m")}
    bN, bD = ps70(pd.read_csv(N / "boot_stats.csv")), pd.read_csv(N / "defer_boot_stats.csv")
    bb = bN[bN.m == M].merge(bD, on=key + ["블록"], suffixes=("", "_D"))
    bwin = bb.assign(w=(bb.p_loss < bb.p_loss_D) & (bb.worst > bb.worst_D)).groupby(["쌍", "asset", "person"]).w.all()
    # R3-L1 납입액별 부트스트랩 칸 수, R3-L2 세 블록 손해 확률 범위·연기판과의 차이 범위, R3-L3 손해가 줄어든 칸
    bwm = {m: g.assign(w=(g.p_loss < g.p_loss_D) & (g.worst > g.worst_D)).groupby(["쌍", "asset", "person"]).w.all()
           for m, g in bN.merge(bD, on=key + ["블록"], suffixes=("", "_D")).groupby("m")}
    bA = bb[(bb["쌍"] == "ps<dep") & (bb.asset == "A")]
    brng = ", ".join(f"{bn} {bA[bA['블록'] == bn].p_loss.min():.3f}~{bA[bA['블록'] == bn].p_loss.max():.3f}" for bn in C.BOOT_BLOCKS)
    dpl = bb.p_loss_D - bb.p_loss
    less = p70[p70.loss_n < p70.loss_n_D]
    rem = ps70(pd.read_csv(N / "rem_stats.csv")).merge(pd.read_csv(N / "defer_rem_stats.csv"), on=key, suffixes=("", "_D"))
    rem = rem[rem.m == M]; rup = cmp(rem)[0]
    n70, ne70 = int(p70.n.iloc[0]), int(p70.n_eff.iloc[0])
    ch_ = lambda d: ", ".join(f"{cell(r)} {int(r.loss_n_D)}→{int(r.loss_n)}/{int(r.n)}" for _, r in d.iterrows()) or "없음"
    auto = (f"역사 {n70}경로(독립 구간 {ne70}개)·월 30만 원 기준으로, 최악 경로는 연금저축 쌍 {len(p70)}칸 중 {int(up.sum())}칸에서 기본판(62세부터 인출)이 연기판보다 낫고, "
            f"{int(dn_.sum())}칸({cells(dn)})에서는 나쁘다" + (f"(같은 칸 {int(eq_.sum())}개)" if eq_.any() else "") + ". "
            f"기본판 최악이 0 아래인 칸: {cells(neg)}. "
            f"손해 경로 수가 연기판보다 늘어난 칸: {ch_(more)}, 줄어든 칸: {ch_(less)}. "
            f"최악이 나은 칸 수는 납입액에 따라 바뀐다(월 " + "·".join(f"{m // 10_000}만 {v}" for m, v in bym.items()) + "). "
            f"부트스트랩({meta['n_boot']:,}경로, 블록 {'/'.join(C.BOOT_BLOCKS)})에서는 {int(bwin.sum())}/{len(bwin)}칸에서 세 블록 모두 기본판의 손해 확률이 연기판보다 낮고 최악이 덜 나쁘며"
            f"(납입액별 월 " + "·".join(f"{m // 10_000}만 {int(w.sum())}/{len(w)}칸" for m, w in bwm.items()) + "), "
            f"월 30만 원에서 손해 확률 차이(연기판 − 기본판)는 {dpl.min():.3f}~{dpl.max():.3f}다. "
            f"연금저축 < 예금 자산 A의 기본판 손해 확률은 블록별 {brng}이다. "
            f"70세 잔액에도 인출분과 같은 세금 규칙을 쓴 민감도판(표 1-1)에서는 최악이 나은 칸이 {int(rup.sum())}/{len(rem)}칸이다. "
            "이 비교 규칙(표시 블록 포함)은 결과를 본 뒤 정했다.")
    H2 = f"**{H2_HEAD}** {auto}"
    # 점검 3: 자동 문장의 숫자를 base 병합을 거치지 않고 grid_stats·defer_stats·boot 파일에서 다시 세어 대조
    g = ps70(stN[(stN.cell == "base") & (stN.m == M)]).merge(pd.read_csv(N / "defer_stats.csv"), on=key, suffixes=("", "_D"))
    gw = g[g.worst < g.worst_D - eps]
    assert f"쌍 {len(g)}칸 중 {int((g.worst > g.worst_D + eps).sum())}칸" in auto and all(cell(r) in auto for _, r in gw.iterrows()), auto
    assert "손해 아님" not in auto and f"역사 {int(g.n.iloc[0])}경로(독립 구간 {int(g.n_eff.iloc[0])}개)" in auto, auto
    assert all(f"{int(r.loss_n_D)}→{int(r.loss_n)}/" in auto for _, r in g[g.loss_n != g.loss_n_D].iterrows()), auto
    for m, gm in allm.groupby("m"):
        assert f"{m // 10_000}만 {int((gm.worst > gm.worst_D + eps).sum())}/{len(gm)}" in auto, (m, auto)
    gb = pd.read_csv(N / "boot_stats.csv")
    gb = (gb[(gb.m == M) & (gb["비교"] == "p70")]
          .merge(pd.read_csv(N / "defer_boot_stats.csv"), on=key + ["블록"], suffixes=("", "_D")))
    nb = int(((gb.p_loss < gb.p_loss_D) & (gb.worst > gb.worst_D)).groupby([gb["쌍"], gb.asset, gb.person]).all().sum())
    assert f"{nb}/{len(g)}칸에서 세 블록 모두" in auto and "결과를 본 뒤 정했다" in auto, auto
    ga = pd.read_csv(N / "boot_stats.csv"); ga = ga[ga["비교"] == "p70"].merge(pd.read_csv(N / "defer_boot_stats.csv"), on=key + ["블록"], suffixes=("", "_D"))
    for m, gm in ga.groupby("m"):                     # R3-L1 납입액별 부트스트랩 칸 수
        w = ((gm.p_loss < gm.p_loss_D) & (gm.worst > gm.worst_D)).groupby([gm["쌍"], gm.asset, gm.person]).all()
        assert f"{m // 10_000}만 {int(w.sum())}/{len(w)}칸" in auto, (m, auto)
    # L10: '대부분' = 재배분 단계 중앙값이 합계 (다)−(가) 중앙값의 절반 이상(크기 비교만이 아니라 몫으로)
    share = lambda p: md1(dc["나"] - dc["가"], p) / md1(dc["다"] - dc["가"], p)
    claims = pd.DataFrame([{"문장": f"사람 ({p}): 재배분 단계 (나)−(가)가 합계 (다)−(가)의 대부분(몫 > 0.5, 중앙값끼리)",
                            "값": f"{f3(md1(dc['나'] - dc['가'], p))} ÷ {f3(md1(dc['다'] - dc['가'], p))} = {share(p):.2f} (인출 과세 단계 {f3(md1(dc['다'] - dc['나'], p))})",
                            "맞음": bool(share(p) > 0.5)} for p in ("가", "나", "다")] +
                          [{"문장": f"자동 문장(월 30만 원): {auto}",
                            "값": f"최악 나음 {int(up.sum())}/{len(p70)}칸; 나쁜 칸 " + (", ".join(
                                f"{cell(r)} {f3(r['worst'])} < {f3(r['worst_D'])}" for _, r in dn.iterrows()) or "없음")
                                 + f"; 부트스트랩 {int(bwin.sum())}/{len(bwin)}칸; 잔액 규칙판 {int(rup.sum())}/{len(rem)}칸",
                            "맞음": True}])                       # 위 assert를 모두 통과해야 여기 옴
    # M6 D15·M7 시기·M8 S_hi 뒤집힘
    d15 = stN[(stN.cell == "D15:1980~가격") & (stN.m == M) & (stN.asset == "A") & (stN.person == "가") & (stN["쌍"] == "ps<dep")]
    d15l = ("- D15 표본 민감도(1980~ 가격지수, 자산 A·사람 (가)·연금저축 < 예금): "
            + ", ".join(f"{WHEN[r['비교']]} 손해 {frac(r['loss_n'], r['n'])}·최악 {f3(r['worst'])}" for _, r in d15.iterrows())
            if len(d15) else "- D15 표본 민감도: 빠른 시험이라 계산 안 함(전체 실행에서 채워짐).")

    def years(k, a, b):
        d = pd.read_csv(N / f"base_hist_{k}.csv"); d = d[(d.m == M) & (d.asset == "A") & (d.person == "가")]
        y = sorted(d.path[d[a] < d[b]].str[:4].astype(int))
        return f"- {WHEN[k]} {pair(f'{a}<{b}')} (자산 A·사람 (가)): 손해 {len(y)}/{len(d)}, 손해 경로 시작 연도 {', '.join(map(str, y)) or '—'}"
    fl = chN[(chN.cell == "D11:S_hi") & (chN.m == M) & (np.sign(chN.median_gap) != np.sign(chN.median_gap_base))]
    flips = [f"- {WHEN[r['비교']]} {pair(r['쌍'])} 자산 {r['asset']} ({r['person']}): S_lo {f3(r['median_gap_base'])} → S_hi {f3(r['median_gap'])}"
             for _, r in fl.iterrows()] or ["- 없음(차이 중앙값 부호가 바뀌는 칸 0개)"]

    # 퇴직소득세·연금 인출이 바꾼 크기: 같은 경로 (N판 − F판) ÷ 누적 납입. 70세는 수령 연기판 − F판도.
    eff, dh = [], pd.read_csv(N / "defer_hist_p70.csv")
    for k, col in (("wd36", "ny_close"), ("wd60", "ny_close"), ("p62", "ny_close"), ("p70", "ny_old"), ("p70", "ps")):
        a, b = pd.read_csv(F / f"base_hist_{k}.csv"), pd.read_csv(N / f"base_hist_{k}.csv")
        j = a.merge(b, on=["path", "asset", "m", "person"], suffixes=("_F", "_N"))
        if k == "p70":
            j = j.merge(dh[["path", "asset", "m", "person", col]].rename(columns={col: col + "_D"}), on=["path", "asset", "m", "person"])
        j = j[(j.m == M) & (j.asset == "A")]
        x = (j[col + "_N"] - j[col + "_F"]) / j.contrib_F
        for p, g in x.groupby(j.person):
            gd = ((j[col + "_D"] - j[col + "_F"]) / j.contrib_F)[j.person == p] if k == "p70" else None
            eff.append({"시점": WHEN[k], "상품": NAME[col], "사람": f"({p})", "최소": f3(g.min()), "중앙값": f3(g.median()), "최대": f3(g.max()),
                        **{f"연기판 {s}": (f3(getattr(gd, fn)()) if gd is not None else "—") for s, fn in (("최소", "min"), ("중앙값", "median"), ("최대", "max"))}})
    # r3 M3 잔액 규칙 민감도판: (기본판·잔액 min − F판), 연기판 열 = (연기판·잔액 min − F판)
    kk = ["path", "asset", "m", "person"]
    j = (pd.read_csv(F / "base_hist_p70.csv")[kk + ["ps", "contrib"]]
         .merge(pd.read_csv(N / "rem_hist_p70.csv")[kk + ["ps"]].rename(columns={"ps": "ps_R"}), on=kk)
         .merge(pd.read_csv(N / "defer_rem_hist_p70.csv")[kk + ["ps"]].rename(columns={"ps": "ps_DR"}), on=kk))
    j = j[(j.m == M) & (j.asset == "A")]
    for p, g in j.groupby("person"):
        x, y = (g.ps_R - g.ps) / g.contrib, (g.ps_DR - g.ps) / g.contrib
        eff.append({"시점": WHEN["p70"], "상품": f"{NAME['ps']}(70세 잔액도 min 규칙, 표 1-1)", "사람": f"({p})", "최소": f3(x.min()), "중앙값": f3(x.median()),
                    "최대": f3(x.max()), "연기판 최소": f3(y.min()), "연기판 중앙값": f3(y.median()), "연기판 최대": f3(y.max())})
    nh = chN[(chN.cell == "D11:S_hi") & (chN.m == M)].copy()
    nh = nh.assign(시점=nh["비교"].map(WHEN), 쌍=nh["쌍"].map(pair), 자산=nh.asset, 사람="(" + nh.person + ")",
                   손해=nh.loss_n.astype(int).astype(str) + "/" + nh.n.astype(int).astype(str) + " (S_lo " + nh.loss_n_base.astype(int).astype(str) + ")",
                   Δ중앙값=nh.d_med.map(f3))[["시점", "쌍", "자산", "사람", "손해", "Δ중앙값"]]
    sel = lambda d: d[(d.m == M) & (d.asset == "A") & (d["쌍"] == "ps<dep")]
    bp, dbp = sel(pd.read_csv(N / "bp_stats.csv")), sel(pd.read_csv(N / "defer_bp_stats.csv"))
    gl = lambda d, k2: {r.region: frac(r.loss_n, r.n) for _, r in d[(d.b == "B") & (d.person == "가") & (d.K1 == "전액") & (d.K2 == k2)].iterrows()}
    gbb, gdd = gl(bp, "안넣음"), gl(dbp, "넣음")
    gtt = gl(sel(pd.read_csv(N / "term_ii_base_bp_stats.csv")), "안넣음")["중소도시"]            # 한계 메우기 감사 M5(회원 승인)
    gia = gl(sel(pd.read_csv(N / "intalt" / "bp_stats.csv")), "안넣음")                          # 표 5-7 이자 시점 반대 판
    guide_l = (f"- **사업안내 기준(K1 전액·기본판 K2 안넣음·연기판 K2 넣음, 표 5의 ★ 칸)에서 사람 B (가)의 연금저축 < 예금(기초연금 포함, 주식 100%·월 30만 원) 손해 경로는 "
               f"기본판 중소도시 {gbb['중소도시']}(3년 만기 예금 — 3년치 이자가 만기 뒤 12개월 소득에 몰린다는 연구자 가정 — 으로 보면 {gtt}, 표 5-5; 이자 반영 시점 민감도 — {INT_NAME[INT_ALT['int_t']]} — {gia['중소도시']}, 표 5-7), "
               f"대도시 {gbb['대도시']}다**(농어촌 {gbb['농어촌']}; 연기판 중소도시 {gdd['중소도시']}·대도시 {gdd['대도시']}·농어촌 {gdd['농어촌']}). "
               f"다른 K1·K2 칸은 법 문언 해석(참고)이다. 이자소득은 {INT_NAME[CP.REC['int_t']]} 시점으로 넣었다(2026-11-08 회원 결정). "
               "근거 = 「2026년 기초연금 사업안내」 인쇄 70~71·92~93쪽(표 5 머리말).")
    fmt = lambda d: d.assign(손해=d.loss_n.astype(int).astype(str) + "/" + d.n.astype(int).astype(str), 차이중앙값=d.median_gap.map(f3),
                             기초연금차=d.bp_gap_median.map(f3), 사람=d.person.map(lambda p: f"({p})"))
    bk, dcols = ["region", "K1", "K2", "person", "b"], {"손해": "손해(연기판)", "차이중앙값": "차이중앙값(연기판)", "기초연금차": "기초연금차(연기판)"}
    both = fmt(bp).merge(fmt(dbp)[bk + list(dcols)].rename(columns=dcols), on=bk)
    t9 = (both[both.region == "중소도시"].sort_values(["K1", "K2", "person", "b"])[["K1", "K2", "사람", "b", "손해", "차이중앙값", "기초연금차", *dcols.values()]]
          .rename(columns={"b": "사람(기초연금)"}))                                  # L12
    reg = fmt(bp[(bp.b == "B")]).sort_values(["region", "K1", "K2", "person"])[["region", "K1", "K2", "사람", "손해", "차이중앙값", "기초연금차"]]
    # r3 M3 표 5-3: 잔액 규칙 민감도판(기본판·연기판), 같은 칸
    rc = lambda v, nm: fmt(sel(pd.read_csv(N / f"{v}_bp_stats.csv")))[bk + ["손해", "차이중앙값"]].rename(columns={"손해": f"손해({nm})", "차이중앙값": f"차이중앙값({nm})"})
    t53 = (fmt(bp)[bk + ["사람", "손해", "차이중앙값"]].merge(rc("rem", "잔액 min"), on=bk).merge(rc("defer", "연기판"), on=bk).merge(rc("defer_rem", "연기판·잔액 min"), on=bk))
    t53 = t53[t53.region == "중소도시"].sort_values(["K1", "K2", "person", "b"]).drop(columns=["region", "person"]).rename(columns={"b": "사람(기초연금)"})
    t53 = t53[["K1", "K2", "사람", "사람(기초연금)", *[c for c in t53.columns if c.startswith(("손해", "차이"))]]]
    # 설계서 8-1 표 5-4: 75세 판 ★ 칸(K1 전액·기본판 K2 안넣음·연기판 K2 넣음 = 개시 전 잔액만), 같은 경로의 70세 판(표 5 규칙) 나란히
    k2s, pann = {"base": "안넣음", "defer": "넣음"}, {"base": "기본판", "defer": "연기판"}
    star_ = lambda d, pan: d[(d.m == M) & (d.asset == "A") & (d.region == "중소도시") & (d.K1 == "전액") & (d.K2 == k2s[pan])]
    rl = lambda g, x: f3((x / g.contrib).median())
    t54 = []
    for src in ("a", "b"):
        for pan in PANS:
            g5 = star_(pd.read_csv(N / f"ext75{src}_{pan}_bp_hist.csv"), pan)
            g0 = star_(pd.read_csv(N / ("bp_hist_p70.csv" if pan == "base" else "defer_bp_hist_p70.csv")), pan)
            for (p, b), g in g5.groupby(["person", "b"]):
                g7 = g0[(g0.person == p) & (g0.b == b) & g0.path.isin(g.path)]
                assert len(g7) == len(g)
                t54.append({"자료": src, "판": pann[pan], "사람": f"({p})", "사람(기초연금)": b, "경로": len(g),
                            "손해(75세)": frac(((g.ps - g.dep) < 0).sum(), len(g)), "차이중앙값(75세)": rl(g, g.ps - g.dep),
                            "기초연금 연금저축(65~75)": rl(g, g.bp_ps), "기초연금 예금(65~75)": rl(g, g.bp_dep), "기초연금차(65~75)": rl(g, g.bp_ps - g.bp_dep),
                            "손해(70세·같은 경로)": frac(((g7.ps - g7.dep) < 0).sum(), len(g7)), "차이중앙값(70세·같은 경로)": rl(g7, g7.ps - g7.dep),
                            "기초연금차(65~70·같은 경로)": rl(g7, g7.bp_ps - g7.bp_dep)})
    t54 = pd.DataFrame(t54)
    # 재감사 중간 1: 75세 말 잔액 ÷ 2040년 1월 인출 전 잔액(CSV, (a) 경로·주식 100%, 두 판 같은 값)
    rat = pd.read_csv(N / "ext75a_rem_ratio.csv")["base"]
    rat_s = f"2040년 1월 인출 전 잔액 대비 {rat.min():.2f}~{rat.max():.2f}배, 중앙값 {rat.median():.2f}배 — (a) {len(rat)}경로·주식 100%, 두 판 같은 값; 수익 0이면 정확히 0.5배"
    # 표 5-6: 80세 판 (a), 같은 경로의 75세 판 나란히
    ep = pd.read_csv(N / "ext_paths.csv").set_index("나이")["시작 연도"]
    t56 = []
    for pan in PANS:
        g8, g5 = (star_(pd.read_csv(N / f"ext{a}a_{pan}_bp_hist.csv"), pan) for a in (80, 75))
        for (p, b), g in g8.groupby(["person", "b"]):
            g7 = g5[(g5.person == p) & (g5.b == b) & g5.path.isin(g.path)]
            assert len(g7) == len(g)
            t56.append({"판": pann[pan], "사람": f"({p})", "사람(기초연금)": b, "경로": len(g),
                        "손해(80세)": frac(((g.ps - g.dep) < 0).sum(), len(g)), "차이중앙값(80세)": rl(g, g.ps - g.dep),
                        "기초연금 연금저축(65~80)": rl(g, g.bp_ps), "기초연금 예금(65~80)": rl(g, g.bp_dep), "기초연금차(65~80)": rl(g, g.bp_ps - g.bp_dep),
                        "손해(75세·같은 경로)": frac(((g7.ps - g7.dep) < 0).sum(), len(g7)), "차이중앙값(75세·같은 경로)": rl(g7, g7.ps - g7.dep),
                        "기초연금차(65~75·같은 경로)": rl(g7, g7.bp_ps - g7.bp_dep)})
    t56 = pd.DataFrame(t56)
    # 표 5-8(설계서 11절): 85·90세 판 (a)·(b)·(c). (a) 경로 5개 미만이면 칸에 '표본 부족, 해석하지 말 것'
    lp, cc, t58 = pd.read_csv(N / "ext_late_paths.csv").set_index("나이"), pd.read_csv(N / "ext_late_c.csv"), []
    for age in lp.index:
        for pan in PANS:
            ga, gb = (star_(pd.read_csv(N / f"ext{age}{s}_{pan}_bp_hist.csv"), pan) for s in "ab")
            for (p, b), g in gb.groupby(["person", "b"]):
                a_ = ga[(ga.person == p) & (ga.b == b)]
                c_ = cc[(cc["나이"] == age) & (cc["판"] == pan) & (cc.person == p) & (cc.b == b)]; q = (c_.loss_n / c_.n).quantile([0, .05, .5, .95, 1])
                few = " (표본 부족, 해석하지 말 것)" if len(a_) < FEW else ""
                assert len(c_) == NB_C and (c_.n == len(g)).all()
                t58.append({"나이": age, "판": pann[pan], "사람": f"({p})", "사람(기초연금)": b,
                            "(a) 손해": frac(((a_.ps - a_.dep) < 0).sum(), len(a_)) + few, "(a) 차이중앙값": rl(a_, a_.ps - a_.dep) + few,
                            "(a) 기초연금차": rl(a_, a_.bp_ps - a_.bp_dep) + few,
                            "(b) 손해": frac(((g.ps - g.dep) < 0).sum(), len(g)), "(b) 차이중앙값": rl(g, g.ps - g.dep), "(b) 기초연금차": rl(g, g.bp_ps - g.bp_dep),
                            "(c) 손해 비율 5%·50%·95%": "·".join(f"{q[x]:.0%}" for x in (.05, .5, .95)), "(c) 최소~최대": f"{q[0]:.0%}~{q[1]:.0%}"})
    t58 = pd.DataFrame(t58)
    l58 = lambda age, c: int(lp.loc[age, c])
    a2 = lambda c, f: "·".join(f"{a}세 {f(lp.loc[a, c])}" for a in lp.index)
    c58 = (f"(c)의 꼬리 주식 월평균은 {a2('(c) 꼬리 주식 월평균', '{:.3%}'.format)}로 r̄(월 {rbar:.3%})의 {a2('(c) 꼬리 평균 ÷ r̄', '{:.1f}배'.format)}라, "
           "위험과 함께 평균 수익도 올린 판이다(연금저축에 유리한 쪽이 섞임). "
           f"꼬리로 값이 바뀐 경로는 {l58(85, '(b) 경로')}경로 중 {a2('(c) 꼬리로 바뀐 경로', '{}경로'.format)}"
           f"({a2('(c) 바뀐 경로 시작', '{}년 시작'.format)})뿐이다(나머지는 꼬리 시작 전에 연금저축 잔액이 이미 0). "
           "채권·예금 꼬리는 r̄ 고정이라 주식과 함께 움직이지 않는다. 그래서 (c)의 손해 비율 0%를 '주식 위험을 넣어도 손해 0'의 근거로 쓰면 안 된다")
    assert (cc.loss_n == 0).all()                       # c58의 '0%'
    r0_period = "{:%Y-%m}~{:%Y-%m}".format(*inp(CP.REC).index[[0, -1]])
    # 표 5-7: 이자 반영 시점 민감도(int_compare). 기준 = 사업안내 표(2026-11-08 회원 결정, 2026-11-07 조건의 만족 여부와 별개 — 문장에 둘 다 적음)
    t57 = pd.read_csv(N / "int_timing_compare.csv")
    ok57 = bool((t57["손해 건수 최대 변화"] == 0).all() and (t57["차이 중앙값 최대 변화"] < 0.01).all())
    t57["차이 중앙값 최대 변화"] = t57["차이 중앙값 최대 변화"].map("{:.4f}".format)
    c57 = pd.read_csv(N / "int_timing_cells.csv"); c57 = c57[c57.loss_n.notna() & (c57.loss_n != c57.loss_n_alt)]
    lab = [c for c in ("판", "자료", "해석", "구간", "region", "K1", "K2", "person", "b") if c in c57 and c57[c].notna().any()]
    alt_s = {"same": "그해 이자", "guide": "사업안내"}[INT_ALT["int_t"]]
    t57c = c57.assign(**{f"손해(기준 → {alt_s})": [f"{int(a)} → {int(b)}" for a, b in zip(c57.loss_n, c57.loss_n_alt)],
                         f"차이중앙값(기준 → {alt_s})": [f"{f3(a)} → {f3(b)}" for a, b in zip(c57.median_gap, c57.median_gap_alt)]})[
        ["표", *lab, f"손해(기준 → {alt_s})", f"차이중앙값(기준 → {alt_s})"]].fillna("")
    # 감사 M1: ※ 해석별 표 5-5 칸(int_compare의 표 5-5와 같은 칸: ★·사람 A·B·중소도시·월 30만·자산 A·연금저축 < 예금)
    sa = pd.read_csv(N / "int_star_alt.csv")
    sa = sa[(sa.m == M) & (sa.asset == "A") & (sa["쌍"] == "ps<dep") & (sa.region == "중소도시") & (sa.K1 == "전액") & (sa.K2 == sa["판"].map(k2s))]
    sw = sa[(sa["창"] == "70세") & sa.b.isin(["A", "B"])].pivot_table(index=["판", "해석", "person", "b"], columns="※", values=["n", "loss_n", "median_gap", "bp_gap_median"])
    assert len(sw) == 60 and sw.notna().all().all(), len(sw)                       # 2판 × 5해석 × 사람 (가)(나)(다) × A·B
    sx = sa[sa["창"] != "70세"].pivot_table(index=["창", "판", "person", "b"], columns="※", values=["loss_n", "median_gap", "bp_gap_median"])
    assert len(sx) == 54 and sx.notna().all().all(), len(sx)                       # 정리 감사 L2: 3창 × 2판 × 사람 (가)(나)(다) × A·B·C

    def sline(s, sw=sw, lab=None):
        dl, dm = sw["loss_n"][s] != sw["loss_n"]["예시"], pd.concat([(sw[c][s] - sw[c]["예시"]).abs() for c in ("median_gap", "bp_gap_median")], axis=1).max(axis=1)
        return f"{lab or STAR[s]} 손해 건수 바뀐 칸 {int(dl.sum())}, 차이중앙값·기초연금차 최대 변화 {dm.max():.4f}"
    star_x = ("같은 ※ 해석 민감도, 표 5-4(75세)·표 5-6(80세) 판(정리 감사 L2; 창마다 기본판·연기판 × ★ 칸 사람 A·B·C (가)(나)(다) = 18칸, 반올림 전, 기준 대비): "
              + "; ".join(f"{w} — " + ", ".join(sline(s, sx.xs(w, level="창"), STAR[s].split("(")[0]) for s in ("1~3월도", "없음"))
                          for w in sx.index.unique("창")) + ". 세부 = `N/int_star_alt.csv`(창 열). "
              "판 (i)(1년 예금)에서는 ※ 규정이 작동할 이자 공백이 없어 변화가 0이고, ※가 작동하는 판 (ii)(3년 만기)는 75·80세에서 계산하지 않았다.")
    assert all((sx[c][s] == sx[c]["예시"]).all() for c in ("loss_n", "median_gap", "bp_gap_median") for s in ("1~3월도", "없음")), "75·80세 ※ 변화 0 아님 → 문장 고칠 것"   # 낮음 2
    bm = sw.loc[("defer", "ii_만기+1년", "가", "B")]
    star_l = (f"65세 첫해 ※ 해석 민감도(감사 M1; 표 5-5의 {len(sw)}칸 = 판 (i)·(ii) 5해석 × 기본판·연기판 × ★ 칸 사람 A·B (가)(나)(다), 반올림 전, 기준 대비): "
              + "; ".join(sline(s) for s in ("1~3월도", "없음")) + ". 연기판 (ii) 만기 1년 늦게 사람 B (가): "
              + ", ".join(f"{STAR[s]} 손해 {frac(bm['loss_n'][s], bm['n'][s])} · 차이중앙값 {f3(bm['median_gap'][s])} · 기초연금차 {f3(bm['bp_gap_median'][s])}" for s in STAR)
              + f" → 차이중앙값 범위 {f3(bm['median_gap'].min())}~{f3(bm['median_gap'].max())}. 세부 = `N/int_star_alt.csv`.")
    pick = lambda d, **kw: d.loc[np.logical_and.reduce([d[k] == v for k, v in kw.items()])].iloc[0]
    bga = lambda s, pn: pick(t54, 자료=s, 판=pn, 사람="(가)", **{"사람(기초연금)": "B"})
    fill = {"c58": c58, "t54": "; ".join(
        f"({s}) {bga(s, '기본판')['경로']}경로" + ("(228개월 실제 자료, 기준)" if s == "a" else "(자료 끝 뒤 r̄, 민감도)") + ", 사람 B (가)·★ 연금저축 < 예금 손해 "
        + ", ".join(f"{pn} {bga(s, pn)['손해(75세)']}(같은 경로 70세 판 {bga(s, pn)['손해(70세·같은 경로)']}, 65~75세 기초연금차 중앙값 {bga(s, pn)['기초연금차(65~75)']})"
                    for pn in pann.values()) for s in ("a", "b"))}
    # 한계 메우기 감사 H1·M1 민감도 한 줄: ★ 칸 사람 (가) A·B·C 손해 경로(표 5-4와 같은 정의)
    def l54(f, pan):
        g = star_(pd.read_csv(N / f), pan); g = g[g.person == "가"]
        return "·".join(f"{b} {frac(((d.ps - d.dep) < 0).sum(), len(d))}" for b, d in g.groupby("b"))
    sens54 = ("민감도(★ 칸, 사람 (가), 연금저축 < 예금 손해 경로 A·B·C): " + "; ".join(
        f"({s}) {pd.read_csv(N / f'ext75{s}_base_hist.csv').path.nunique()}경로 — 기본판 나눠 받기(기준) {l54(f'ext75{s}_base_bp_hist.csv', 'base')}, "
        f"기본판 2040년 한꺼번에(옛 판) {l54(f'ext75{s}_lump_bp_hist.csv', 'base')}" for s in ("a", "b"))
        + ". 옛 판 = 2040년 1월에 잔액 전부를 꺼내 그해 연금소득(÷ 12)으로 넣고 1,500만 원 넘으면 min(종합, 15% 분리) — 가정 3·사업안내 71쪽 일시금 원칙과 어긋나 민감도로만 둠. "
          f"이자를 {INT_NAME[INT_ALT['int_t']]}로 넣은 75세 판은 표 5-7. 세부 = `N/ext75*_lump_*.csv`.")
    # 감사 M3: (b)에만 있는 경로의 r̄ 합성 꼬리 개월 수(자료 끝 = period 끝 달)
    ey, em = map(int, period[-7:].split("-"))
    pa, pb = (set(pd.read_csv(N / f"ext75{s}_base_hist.csv").path) for s in ("a", "b"))
    tail = sorted((int(p[:4]) * 12 + int(p[5:7]) - 1 + CP.Q("H75") - 1) - (ey * 12 + em - 1) for p in pb - pa)
    assert len(tail) and min(tail) > 0
    # 설계서 8-2 표 5-5: 판 (i) = 기존 bp_stats·defer_bp_stats, (ii) = term_*. ★ 칸, 사람 A·B
    tn = {"i": "(i) 1년", "ii": "(ii) 3년·예시 해석", "ii_만기+1년": "(ii) 만기 1년 늦게", "ii_만기+2년": "(ii) 만기 2년 늦게", "ii_상한": "(ii) 문구 상한 해석"}
    parts = []
    for pan in PANS:
        fs = {"i": N / ("bp_stats.csv" if pan == "base" else "defer_bp_stats.csv"), **{nm: N / f"term_{nm}_{pan}_bp_stats.csv" for nm in TERMS}}
        for nm, f in fs.items():
            d = sel(pd.read_csv(f)); d = d[(d.region == "중소도시") & (d.K1 == "전액") & (d.K2 == k2s[pan]) & d.b.isin(["A", "B"])]
            parts.append(d.assign(판=pann[pan], 해석=tn[nm], v=[f"{frac(a, n)} · {f3(x)}" for a, n, x in zip(d.loss_n, d.n, d.median_gap)]))
    t55l = pd.concat(parts)
    t55 = (t55l.pivot_table(index=["판", "person", "b"], columns="해석", values="v", aggfunc="first")[list(tn.values())].reset_index()
           .assign(person=lambda d: "(" + d.person + ")").rename(columns={"person": "사람", "b": "사람(기초연금)"}))
    tp = pd.read_csv(N / "term_people.csv"); tpB = tp[tp["사람"] == "B"]
    rB = lambda nm, yr: f"{pick(tpB, **{'세금 그릇': '(가)'}, 판=nm, 해=yr)['선정기준액 대비']:.1%}"
    lB = lambda pan, nm: pick(t55l, 판=pan, 해석=tn[nm], person="가", b="B")["v"].split(" · ")[0]
    # 감사 H2: B 손해 증가의 원인 = 이자가 만기 해에 몰림(3년 인정 이자 합은 판 (i)과 같음). 문장의 전제를 assert
    tp3 = tpB[tpB["세금 그릇"] == "(가)"].groupby("판")["3년 인정 이자 합"].first()
    rawB = lambda nm, yr: pick(tpB, **{"세금 그릇": "(가)"}, 판=nm, 해=yr)
    assert rawB("ii", "만기 해")["선정기준액 대비"] > 1 >= rawB("ii", "만기 아닌 해")["선정기준액 대비"] and lB("기본판", "ii_상한") == lB("기본판", "ii")
    bg = lambda nm: f3(pick(t55l, 판="기본판", 해석=tn[nm], person="가", b="B")["bp_gap_median"])
    h2s = (f"사람 B (가) 기본판 손해가 {lB('기본판', 'i')} → {lB('기본판', 'ii')}로 늘어난 것은 추가 공제 때문이 아니다. 예시 해석에서는 3년 동안 소득인정액에 들어가는 이자 합"
           f"(월 4만 원 공제 뒤)이 판 (ii) {tp3['ii']:,}원으로 1년 상품 셋인 판 (i) {tp3['i']:,}원과 같다. 차이는 시점에서 온다: 3년치 이자가 12개월에 몰려 그 12개월 소득인정액이 "
           f"시뮬레이션 저축 없이도 선정기준액의 {rB('ii', '만기 해')}라 연금저축·예금 쪽 모두 기초연금 0원이고, 나머지 달에는 {rB('ii', '만기 아닌 해')}로 여유가 생겨 "
           f"연금저축 연금(K1 전액)이 그 여유만큼 기초연금을 깎는다(65~70세 기초연금차 중앙값 {bg('i')} → {bg('ii')}). "
           f"공제를 덜 하는 문구 상한 해석(3년 인정 이자 {tp3['ii_상한']:,}원)에서도 {lB('기본판', 'ii_상한')}다.")
    fill["t55"] = (f"사람 B (가)(시뮬레이션 저축 없음) 소득인정액 ÷ 선정기준액 = 판 (i) {rB('i', '해마다')} → 판 (ii) 만기 아닌 해 {rB('ii', '만기 아닌 해')}·만기 해 "
                   f"{rB('ii', '만기 해')}(문구 상한 해석 {rB('ii_상한', '만기 해')}). ★ 연금저축 < 예금 손해(65~70세 창) " + ", ".join(
                       f"{pn} {lB(pn, 'i')} → {lB(pn, 'ii')}(만기 1·2년 늦게 {lB(pn, 'ii_만기+1년')}·{lB(pn, 'ii_만기+2년')}, 상한 해석 {lB(pn, 'ii_상한')})"
                       for pn in pann.values()) + f". {h2s} 3년 상품·만기 시점은 연구자 가정, 만기 이자의 반영 달은 {INT_NAME[CP.REC['int_t']]}(표 5-7에 반대 판)")
    # 감사 L7: 보조표 표기(판 이름·비율 %·천 단위)
    tpd = tpB.drop(columns="사람").assign(판=lambda d: d["판"].map(tn), **{"선정기준액 대비": lambda d: d["선정기준액 대비"].map("{:.1%}".format)})
    tpd = tpd.apply(lambda c: c.map("{:,}".format) if pd.api.types.is_integer_dtype(c) else c)
    # r3 M3 표 1-1: 70세 연금저축 쌍, 잔액 규칙 민감도판
    st_ = lambda v: pd.read_csv(N / f"{v}_stats.csv")
    t11 = None
    for v, nm in (("rem", "기본판·잔액 min"), ("defer_rem", "연기판·잔액 min")):
        d = ps70(st_(v)); d = d[d.m == M].assign(**{f"손해 경로({nm})": lambda x: [frac(a, b) for a, b in zip(x.loss_n, x.n)],
                                                   f"차이 중앙값({nm})": lambda x: x.median_gap.map(f3), f"최악({nm})": lambda x: x.worst.map(f3)})
        d = d[key + [c for c in d.columns if "(" in c]]
        t11 = d if t11 is None else t11.merge(d, on=key)
    t11 = (ps70(base)[key + ["worst", "worst_D"]].merge(t11, on=key)
           .assign(**{"비교 쌍": lambda x: x["쌍"].map(pair), "사람": lambda x: "(" + x.person + ")", "최악(기본판)": lambda x: x.worst.map(f3),
                      "최악(연기판)": lambda x: x.worst_D.map(f3)}).rename(columns={"asset": "자산"}))
    t11 = t11[["비교 쌍", "자산", "사람", "최악(기본판)", "최악(연기판)", *[c for c in t11.columns if "잔액 min" in c]]]
    # H1(c) 사람 B 시작 연도 두 구간
    bh = pd.read_csv(N / "bp_hist_p70.csv"); bh = bh[(bh.b == "B") & (bh.region == "중소도시") & (bh.m == M) & (bh.asset == "A")].copy()
    y0 = bh.path.str[:4].astype(int); bh["구간"] = np.where(y0 <= 2002, f"{y0.min()}~2002", f"2003~{y0.max()}")
    rel = lambda d, x: f3((x / d.contrib).median())
    t52 = (bh.groupby(["구간", "K1", "K2", "person"]).apply(lambda d: pd.Series({
        "손해": frac(((d.ps - d.dep) < 0).sum(), len(d)), "차이중앙값": rel(d, d.ps - d.dep), "기초연금 연금저축": rel(d, d.bp_ps),
        "기초연금 예금": rel(d, d.bp_dep), "기초연금 노란우산": rel(d, d.bp_ny_old), "기초연금차": rel(d, d.bp_ps - d.bp_dep)}), include_groups=False)
        .reset_index().assign(person=lambda d: "(" + d.person + ")").rename(columns={"person": "사람"}))
    h70 = pd.read_csv(N / "base_hist_p70.csv")
    o15 = h70.groupby(["asset", "m", "person"]).n_over1500.agg(경로=("size"), 넘는경로=lambda x: int((x > 0).sum()), 최대해수="max").reset_index()
    cs = chN[chN.m == M].groupby(["D", "후보"]).agg(경고셀=("warn", "sum"), 셀=("warn", "size")).reset_index()
    pv = lambda s, g, c: ppl.loc[(ppl["사람"] == s) & (ppl["세금 그릇"] == f"({g})"), c].iloc[0]
    m7 = (f"87% 경계와 'A 받음'은 사람 (가) 기준이다. 사업소득 b/12가 붙는 (나)(다)에서는 B가 선정기준액의 {pv('B', '나', '선정기준액 대비'):.0%}·{pv('B', '다', '선정기준액 대비'):.0%}"
          f"(기초연금 {pv('B', '나', '기초연금(월)'):,}·{pv('B', '다', '기초연금(월)'):,}원), A (다)는 {pv('A', '다', '선정기준액 대비'):.1%}(월 {pv('A', '다', '기초연금(월)'):,}원, 감액 구간)다(감사 r2 M7).")
    t5head = ("⚠ 기초연금은 65~70세(2034~2039)만 더한다. 연기판의 70세 이후 연금소득이 깎을 기초연금이 빠져 있어 **연기판에 유리한 창**이다. "
              "수령 전 잔액은 시행령 §14 문구('정기 지급액 또는 최종 잔액', 기초연금 근거 106행)와 사업안내 인쇄 92~93쪽 모두 금융재산으로 본다(연기판 ★ = K2 넣음). "
              "75세(2044년)까지 넓힌 판은 표 5-4(설계서 8-1), 80세(2049년)까지는 표 5-6, 85·90세까지는 표 5-8. "
              f"이자소득 반영 시점 = {INT_NAME[CP.REC['int_t']]}(65세 첫해 신규 수급자 ※ 포함, 설계서 9절), 민감도({INT_NAME[INT_ALT['int_t']]})는 표 5-7.")
    L = [
        "# 후보 5 포트폴리오판 결과 — 50대 자영업자: 연금저축 vs 노란우산공제 vs 예금 (2026-11-06)",
        "",
        *(["> **빠른 시험 출력**: 격자 셀 " + ", ".join(QUICK_CELLS) + f" · 부트스트랩 {meta['n_boot']}경로. 결과로 인용하지 말 것.", ""] if QUICK else []),
        f"- 실행 폴더: `{run}` · 설계서 `설계서_후보5_포트폴리오판_20261106.md` · 동결 비교 대상 `{FROZEN}`.",
        "- F판 = 설계서 1절(F1~F4)만 고친 판, N판 = 2절(N1 퇴직소득세·N2 건보료·N3 기초연금)까지 켠 판. 비율은 모두 누적 납입 대비다.",
        "- 이 문서의 표와 숫자는 `notebooks/candidate5/_gen_cand5p.py`가 run 폴더 CSV에서 만들었다. 판정하지 않는 기술이다. 상수는 `N/constants.csv`.",
        "- 감사 r1(`run_20261106_2251/audit/AUDIT_r1_20261106.md`)·재감사 r2(`run_20261107_0023/audit/AUDIT_r2_20261107.md`) 반영판(r3). "
        "바뀐 규칙은 설계서 'r2 변경'·'r3 변경' 절과 아래 '가정과 한계'.",
        "",
        "## 요약",
        "",
        f"- {H2}",
        "  - 대조: '70세까지 수령 연기' 판(가정 16)을 표 1·3·5에 기본판 옆 열로, 70세 잔액에도 같은 세금 규칙을 쓴 민감도판을 표 1-1·표 3·표 5-3에 실었다.",
        f"- **사람 B의 87% 경계는 2026년 금리(연 {12 * rbar:.2%}) 기준이다.** 사람이 처음 가진 금융재산의 이자는 이 금리로 고정했고, "
        "시뮬레이션이 만든 예금(예금 상품·인출 예금·환급/절세 예금)에만 그 경로의 과거 예금 금리를 붙였다. 시작 연도 두 구간 보조표는 표 5-2. " + m7,
        guide_l,
        "- 노란우산 폐업·노령 대 예금 결과는 사실상 과거 예금 금리 수준을 반영한다(노란우산 이율은 D09 고정값이라 모든 경로에서 같고, 예금만 과거 금리를 따른다). "
        "노란우산 해약 < 예금은 해약 환급표 몫이라 손해가 전 시기에 걸친다. 시작 연도는 표 2 아래.",
        "- 표 1·2·5의 기준 셀은 건보료 S_lo 판이다. S_hi(상한 시나리오)에서 차이 중앙값 부호가 바뀌는 칸은 표 4 아래.",
        "",
        "## 점검 1. F판 = 동결 결과 (노란우산 해약 칸 제외, 상대차 ≤ 1e-12)",
        "",
        md_table(num(pd.read_csv(run / "regress_F_vs_frozen.csv"))),
        "",
        "`F/coverage.csv`는 비교하지 않는다('계산 안 함' 이유 문장 행만 늘어남, 결과 숫자 아님 — 감사 r3 R3-L7). 동결 규칙 12의 `notebooks/_regress_check.py`에는 후보5 패턴이 없어, "
        "이 생성기의 regress()(위 표)와 실행 간 칸 비교 `notebooks/candidate5/_diff_runs_cand5p.py`로 대신한다(R3-L8).",
        "",
        "## 점검 2. 손계산",
        "",
        md_table(num(pd.read_csv(run / "hand_checks.csv"))),
        "",
        "## 점검 3. 요약 문장과 숫자 대조 (표 1·7에서)",
        "",
        "자동 문장의 숫자(경로 수·독립 구간·칸 수·나쁜 칸·손해 건수·납입액별 개수·부트스트랩 칸 수)는 `grid_stats`·`defer_stats`·`boot_stats`·`defer_boot_stats`에서 "
        "다시 세어 코드에서 assert했다. r1 H2 대체 문장(감사 보고서 문장)을 r2에서 자동 문장으로 바꿨고, 그 규칙은 결과를 본 뒤 정했다(L14).",
        "",
        md_table(claims),
        "",
        "## 사람 A·B·C (시뮬레이션 저축 없을 때, 중소도시)",
        "",
        f"- 예금 금리 r̄ = 기준 셀 예금 금리 모형(D05 12개월사다리, 세전)의 자료 마지막 12개월({period}) 평균 = 월 {rbar:.6f}(연 {12 * rbar:.4%}).",
        "- 소득인정액 = 국민연금 + 연금저축 연금 + 사업소득 b/12 + max(예금 이자 − 4만, 0) + max(주택 − 기본재산액 8,500만 + max(금융재산 − 2,000만, 0), 0) × 4% ÷ 12. "
        "b = 세금 그릇에서 §55 역산한 과세표준((가) 0, 가정 15).",
        f"- B 금융재산 f: 50만 + (f·r̄ − 4만) + (4.5억 − 8,500만 + f − 2,000만) × 4% ÷ 12 = 247만 × 0.87 → f = 538,900 ÷ (r̄ + 0.0033333) = **{fB:,.0f}원** (사람 (가) 기준). "
        "국민연금 50만·주택 4억5천만 그대로.",
        "- 예금 이자(월) = 금융재산 × r̄, 경로와 상관없이 고정. 해마다 같은 이자라 전년도·전전년도 이자(사업안내 시점)도 같은 값 → 87% 경계는 이자 반영 시점과 무관(cand5p.people assert). A·C는 금융재산을 그대로 두었다(사람 (가)에서 A 받음, C 못 받음을 코드에서 assert).",
        "",
        md_table(ppl),
        "",
        "## 표 1. 끝까지 쌓아 둘 때 (62·70세, 월 30만 원, N판 기준 셀 = 건보료 S_lo 판)",
        "",
        H2,
        "",
        "70세 연금저축은 62세부터 해마다 인출해 예금에 넣은 금액을 포함한다. 연기판 = 62~70세 인출 없이 70세 잔액 4.4%(가정 16). "
        "70세 노란우산 노령 지급과 62세 노란우산 폐업 수령은 퇴직소득세 뒤 금액이다. 기초연금은 표 5에 따로 둔다. 사람 (가)(나)(다)는 국민연금 0(가정 9).",
        "",
        "S_lo에서 70세 연금저축에 닿는 N판 규칙은 인출뿐이라, 연기판 연금저축 금액은 F판과 같다(정의상 같은 값, 독립 대조 아님). "
        "다른 것은 노란우산(퇴직소득세)과 기초연금뿐이다(감사 r2 M6).",
        "",
        legend,
        "",
        loss_table(["p62", "p70"]),
        "",
        "### 표 1-1. 70세 잔액 세금 규칙 민감도 (연금저축 쌍, 월 30만 원, S_lo)",
        "",
        "기본판은 해마다 꺼낸 돈에 min(분리, 종합)을, 70세 잔액에는 4.4%만 썼다(가정 3의 비대칭). 여기서는 잔액도 1,500만 원 이하 같은 몫으로 나눠 해마다 받는다고 보고"
        "(시간가치 무시) 같은 min 규칙을 썼다. 기본판·연기판 모두 이 규칙으로 다시 계산했다. 세부 = `N/rem_*.csv`·`N/defer_rem_*.csv`.",
        "",
        md_table(t11),
        "",
        "## 표 2. 중간에 전부 꺼낼 때 (36·60개월째, 월 30만 원, N판 기준 셀 = 건보료 S_lo 판)",
        "",
        "노란우산 해약 = 2026.1.1. 이후 가입자 환급표(F1·F2). 노란우산 폐업 = 퇴직소득세 뒤(N1).",
        "",
        legend,
        "",
        loss_table(["wd36", "wd60"]),
        "",
        "### 시기·표본 참고",
        "",
        "노란우산 폐업·노령 대 예금 결과는 사실상 과거 예금 금리 수준을 반영한다. 노란우산 해약 < 예금은 해약 환급표 몫이라 손해가 전 시기에 걸친다. 손해 경로의 시작 연도:",
        "",
        years("p62", "ny_close", "dep"),
        years("p62", "ny_cancel", "dep"),
        years("p70", "ny_old", "dep"),
        "",
        "표본 민감도(L16):",
        "",
        d15l,
        "",
        "## 표 3. N판이 F판보다 바꾼 크기 (같은 경로, 주식 100%, 월 30만 원, 기준 셀 S_lo, (N판 − F판) ÷ 누적 납입)",
        "",
        "연기판 열 = (수령 연기판 − F판) ÷ 누적 납입(70세만). '70세 잔액도 min 규칙' 행 = 표 1-1 민감도판(기본판·연기판 각각) − F판.",
        "",
        md_table(pd.DataFrame(eff)),
        "",
        "## 표 4. 건보료 S_hi(상한 시나리오) − S_lo(부과 안 함) (월 30만 원, 자산 A·B)",
        "",
        "Δ중앙값 = S_hi 차이 중앙값 − S_lo 차이 중앙값(중앙값끼리의 차). 표 7의 (라) − (다)는 같은 경로 차이의 중앙값이라 값이 다를 수 있다.",
        "",
        md_table(nh),
        "",
        "S_hi에서 차이 중앙값 부호가 바뀌는 칸(월 30만 원):",
        "",
        *flips,
        "",
        "## 표 5. 기초연금 포함 70세 금액: 연금저축 < 예금 (주식 100%, 월 30만 원, 중소도시, S_lo 판)",
        "",
        "사람 (가)(나)(다) = 세금 수준(사업소득 b/12 포함, 가정 15), A·B·C = 기초연금 처지(설계서 N3 가정값, B = 2026년 금리 기준 선정기준액의 87%). "
        "연금저축 세금은 그 사람 국민연금을 넣어 다시 계산했다(가정 9). 차이중앙값 = (연금저축 + 기초연금) − (예금 + 기초연금), 기초연금차 = 기초연금 합계 차이(65~70세, 액면). "
        "K1 과세분만 = 세액공제 안 받은 원금 몫을 소득에서 뺌, 전액 = 받은 연금 전액. K2 넣음 = 연금저축 잔액을 금융재산에 넣음. 연기판 = 가정 16. "
        "65세부터 연금저축 세액공제 여력은 그 사람 국민연금을 넣은 산출세액이다. 노란우산 절세는 사업소득금액이 있는 (나)(다)만 같은 여력을 쓰고 (가)는 쓰지 않는다(조특법 §86의3①, 가정 9·감사 r3 R3-M1).",
        "",
        GUIDE,
        "",
        t5head,
        "",
        md_table(star(t9, ["손해", "차이중앙값", "기초연금차"], list(dcols.values()))),
        "",
        "### 표 5-3. 70세 잔액 세금 규칙 민감도 (표 5와 같은 칸, 잔액도 1,500만 원 이하로 나눠 min 규칙, 표 1-1)",
        "",
        GUIDE,
        "",
        md_table(star(t53, ["손해", "차이중앙값", "손해(잔액 min)", "차이중앙값(잔액 min)"],
                      ["손해(연기판)", "차이중앙값(연기판)", "손해(연기판·잔액 min)", "차이중앙값(연기판·잔액 min)"])),
        "",
        "### 표 5-1. 지역 민감도 (사람 B, 기본재산액만 바꿈, 기본판)",
        "",
        GUIDE,
        "",
        md_table(star(reg, ["손해", "차이중앙값", "기초연금차"])),
        "",
        "### 표 5-2. 사람 B, 시작 연도 두 구간 (중소도시, 기본판, 65~70세 합계 ÷ 누적 납입의 중앙값)",
        "",
        GUIDE,
        "",
        md_table(star(t52[["구간", "K1", "K2", "사람", "손해", "차이중앙값", "기초연금 연금저축", "기초연금 예금", "기초연금 노란우산", "기초연금차"]],
                      ["손해", "차이중앙값", "기초연금 연금저축", "기초연금차"])),
        "",
        "### 표 5-4. 기초연금을 75세(2044년)까지: 75세 금액 + 65~75세 기초연금, 연금저축 < 예금 (★ 칸만, 주식 100%, 월 30만 원, 중소도시, S_lo)",
        "",
        "설계서 8-1. 납입은 70세(2039년 말)에 끝. **2040년 1월부터 기본판·연기판 모두 남은 잔액을 ÷ 10, ÷ 9, …로 나눠 받는다**(75세까지 ÷ 10~÷ 6; 연기판의 10년 나눠 받기 계획은 회원 지시). "
        "기본판은 2031~2039년 인출(잔액 ÷ (11 − 연차)) 뒤 2040년에 이 계획을 다시 센다 — 70세 판 가정 3(잔액을 1,500만 원 이하로 나눠 받으면 4.4%)과 같은 원칙(한계 메우기 감사 H1, 회원 결정). "
        "연기판은 2040년 1월 개시(법정 연금수령연차는 2031년부터 세므로 2040년은 10년차 — 한도 안). 꺼낸 돈은 기존 해마다 규칙으로 과세(가정 9) 뒤 예금이고, 기초연금에서는 그해 인출 ÷ 12가 월 연금소득. "
        "75세 말 남은 잔액은 4.4%(가정 3과 같은 방식). 일시금 원칙: 사업안내 인쇄 71쪽 '일시금으로 수령하는 경우 금융재산으로 산정'을 두 상품에 같게 쓴다 — 노란우산 70세 지급금(퇴직소득세 뒤)은 "
        "금융재산(예금)으로 75세까지, 연금저축은 기준판에서 일시금을 꺼내지 않는다. 예금 상품도 75세까지 예금. "
        "★ = K1 전액, 기본판 K2 안넣음, 연기판 K2 넣음 — 이 표의 K2 넣음은 **개시 전 잔액만**(사업안내 인쇄 92~93쪽: 개시 뒤에는 월 수령액만 연금소득; CSV `K2뜻` 열). "
        f"자료 (a) = 228개월 실제 자료가 있는 시작 연도만(기준), (b) = 70세 비교 경로 전부, {period[-7:]} 뒤 달은 주식·채권·예금 모두 r̄(민감도; (a)와 겹치는 경로는 (a)와 같은 값임을 코드에서 대조). "
        f"(b)에만 있는 {len(tail)}경로는 끝 {tail[0]}~{tail[-1]}개월이 r̄ 합성이라 그 기간 주식 위험 프리미엄·변동성이 0이다 — 75세까지 주식 100%인 잔액의 손실 위험을 작게 잡는 방향(감사 M3). "
        "'같은 경로' 열 = 같은 경로의 70세 판(표 5 규칙: 70세 금액 + 65~70세 기초연금). 금액 ÷ 누적 납입(70세까지), 기초연금은 액면 합. "
        "'기초연금차' 열 = 경로별 (연금저축 쪽 − 예금 쪽) 기초연금 차의 중앙값이라, 앞 두 열(각각의 중앙값)의 차와 다를 수 있다(감사 L6). 세부 = `N/ext75*.csv`.",
        "",
        f"⚠ 75세 창도 연기판에 유리할 수 있다: 두 판 모두 75세 말에 연금저축 잔액이 남고({rat_s}, `N/ext75a_rem_ratio.csv`), 연기판은 2031~2039년에 꺼내지 않아 잔액이 더 크다. "
        "이 잔액이 76~80세 연금소득으로 깎는 기초연금은 표 5-6((a) 경로만)에 있다.",
        "",
        md_table(pd.DataFrame(t54)),
        "",
        sens54,
        "",
        "### 표 5-6. 기초연금을 80세(2049년)까지: 80세 금액 + 65~80세 기초연금, 연금저축 < 예금 (★ 칸만, 주식 100%, 월 30만 원, 중소도시, S_lo, 자료 (a)만)",
        "",
        f"표 5-4와 같은 규칙(납입 70세 끝, 2040년부터 ÷ 10, ÷ 9, … — 2049년 1월 ÷ 1로 잔액 전부를 꺼내 80세 말 연금저축 잔액 0). 실제 시장 자료가 288개월(80세 말) 있는 시작 연도만: "
        f"**{ep[80]}경로**(75세 판 (a) {ep[75]}경로, 70세 판 {ep[70]}경로 중). 자료 끝 뒤를 r̄로 채우는 (b)는 만들지 않았다. "
        "'같은 경로' 열 = 같은 경로의 75세 판(표 5-4 규칙). 금액 ÷ 누적 납입(70세까지), 기초연금은 액면 합. "
        f"실제 자료가 81세 말(300개월)까지 있는 시작 연도는 {ep[81]}개다. 85·90세까지는 표 5-8(자료 끝 뒤를 채운 판 포함). "
        "세부 = `N/ext80a_*.csv`, 경로 수 = `N/ext_paths.csv`.",
        "",
        md_table(t56),
        "",
        "### 표 5-8. 기초연금을 85·90세(2054·2059년)까지: 그 나이 금액 + 65세부터 기초연금, 연금저축 < 예금 (★ 칸만, 주식 100%, 월 30만 원, 중소도시, S_lo)",
        "",
        "설계서 11절(2026-11-08 회원 지시). 표 5-4·5-6과 같은 인출·세금·기초연금 규칙이다. 2049년 1월에 연금저축 잔액을 전부 꺼내므로 81세부터 연금저축 연금소득은 0이고, "
        "꺼낸 돈은 인출 예금(금융재산)으로 남아 기초연금을 깎는다. 기초연금 금액은 2026 고시 값 그대로(N3 근사), 76세 이후도 같은 규칙. "
        "**사망률을 넣지 않았다(모두 90세까지 산다고 가정).** 85세 말 = 348개월, 90세 말 = 408개월. "
        f"(a) = 실제 자료가 그 개월 수만큼 있는 시작 연도만: 85세 {l58(85, '(a) 경로')}경로, 90세 {l58(90, '(a) 경로')}경로(5개 미만이면 칸에 '표본 부족, 해석하지 말 것'). "
        f"(b) = 70세 비교 {l58(85, '(b) 경로')}경로 전부, {period[-7:]} 뒤 달은 주식·채권·예금 모두 r̄(월 {rbar:.6f}). 채운 달 수: 85세 {l58(85, '채운 경로')}경로 "
        f"{l58(85, '채운 달 최소')}~{l58(85, '채운 달 최대')}개월, 90세 {l58(90, '채운 경로')}경로 {l58(90, '채운 달 최소')}~{l58(90, '채운 달 최대')}개월. "
        "**자료 끝 뒤는 주식 위험 0인 가정이라 연금저축 쪽 위험을 과소평가함.** (b)에서 (a)와 겹치는 경로는 (a)와 같은 값임을 코드에서 대조했다. "
        f"(c) = 민감도: (b)에서 자료 끝 뒤 주식 월수익만 r̄ 대신 입력 주식 월수익 표본({r0_period})에서 정상 블록 부트스트랩(평균 블록 12개월 — 부트스트랩 '12개월' 블록과 같은 함수, "
        f"시드 {P('seed')})으로 뽑은 꼬리 {NB_C}개로 채움(채권·예금 꼬리는 r̄ 그대로). 꼬리 하나를 {l58(85, '(b) 경로')}경로 모두에 같은 순서로 쓰고(85세 = 90세 꼬리의 앞부분), "
        "꼬리마다 손해 경로 비율을 센 분포의 5%·50%·95% 값과 최소~최대. 꼬리가 없는 경로는 모든 꼬리에서 (a)·(b)와 같은 값이고 꼬리를 r̄로 두면 (b)와 같은 값임을 코드에서 대조했다. "
        f"**{c58}.** "
        "금액 ÷ 누적 납입(70세까지), 기초연금차 = 경로별 (연금저축 쪽 − 예금 쪽) 기초연금 합 차의 중앙값 ÷ 누적 납입. "
        "세부 = `N/ext85*.csv`·`N/ext90*.csv`(전 칸), `N/ext_late_c.csv`(꼬리별 ★ 칸), `N/ext_late_paths.csv`.",
        "",
        md_table(t58),
        "",
        "### 표 5-5. 사람이 처음 가진 금융재산을 3년 만기 정기예금으로 볼 때 (65~70세 창 = 표 5와 같은 칸, ★ 칸, 사람 A·B)",
        "",
        "설계서 8-2. 사업안내 인쇄 70쪽 원문: \"이자소득 발생 적금･저축 등의 가입기간을 확인하여 12개월 초과 상품인 경우 초과된 개월수(월단위 산정)만큼 연간 최대 48만원 (월4만원)범위 내에서 추가 공제 가능\". "
        "**기준 = 예시 해석**(같은 쪽 예시 '40개월 × 4만원'과 맞게 추가 공제 = 4만 × 초과 개월), **민감도 = 문구 상한 해석**(추가 공제를 만기 해 48만 원으로 자름). "
        "판 (i) = 기존(1년 상품, 표 5). 판 (ii) = 단리 r̄ 3년 만기(3년 기간 프리미엄 무시), 이자 36개월치를 만기 해에 한꺼번에 소득으로, "
        "그해 공제 = 기본 월 4만 원 + 추가 공제 4만 × 24개월(점검 2). 만기 해 이자는 사업안내 70쪽 표대로 이듬해 4~12월·그다음 해 1~3월(9:3)의 월 소득이고 그 밖의 달 이자소득은 0"
        "(그해 이자를 그해 소득으로 넣는 옛 판 = 표 5-7, 한계 M1). 아래 보조표의 '만기 해' = 그 이자가 들어가는 12개월, '만기 아닌 해' = 나머지 달. "
        "기준 만기 해 = 2029·2032·2035·2038년(2026년 1월 가입, 연구자 가정), "
        "만기 1·2년 늦게 = 같은 판에서 만기 해만 옮김. '문구 상한 해석' = 추가 공제를 만기 해 48만 원으로 자름(예시와 맞지 않음). 사람 B 금융재산은 판 (i)로 푼 값 그대로. "
        "시뮬레이션 예금은 12개월 사다리라 해당 없음(코드 assert). 칸 = 손해 경로 · 차이 중앙값((연금저축 + 기초연금) − (예금 + 기초연금), ÷ 누적 납입). 세부 = `N/term_*.csv`.",
        "",
        h2s,
        "",
        md_table(t55),
        "",
        "사람 B, 시뮬레이션 저축 없을 때(중소도시) 소득인정액 — 판 (i)와 판 (ii)의 만기 해·만기 아닌 해('3년 인정 이자 합' = 36개월 동안 소득인정액에 들어가는 이자, 월 4만 원 공제 뒤):",
        "",
        md_table(tpd),
        "",
        "### 표 5-7. 기초연금 이자소득 반영 시점 민감도 (표 5·5-1·5-2·5-3·5-4·5-5·5-6·7-1에 실리는 칸, 반올림 전 값)",
        "",
        f"기준 = {INT_NAME[CP.REC['int_t']]}(2026-11-08 회원 결정, 설계서 9절). 민감도 = {INT_NAME[INT_ALT['int_t']]}. 사업안내 판: 「2026년 기초연금 사업안내」 인쇄 70쪽 표('23년 이자 → '24년 4월~'25년 3월 적용 …)대로 "
        "해 y의 1~3월에 (y − 2)년, 4~12월에 (y − 1)년 이자(연간 이자 ÷ 12)를 넣고, 같은 쪽 ※(요지: 그해 신규 수급(권)자이고 그해 이자소득이 0이면 전년도 이자소득 미반영, 원문 발췌는 저장소에 없음·쪽 번호만)을 "
        "65세 첫해(2034년)에 그해 이자가 0인 경로에만 씀(그 2033년 이자가 걸리는 2034년 4월~2035년 3월이 0; 1~3월의 2032년 이자는 예시에 없어 그대로 — 원문 해석, 점검 2). "
        "고유 금융재산 이자는 해마다 같아(r̄ 고정) 시점이 바뀌어도 같고(사람 B의 87% 경계도 시점과 무관, 코드 assert), 바뀌는 것은 시뮬레이션 예금 이자(잔액·금리가 해마다 달라 한두 해 늦은 값이 들어감)와 표 5-5 만기 이자(이듬해·그다음 해에 9:3으로 나뉨)다. "
        f"2026-11-07 회원 규칙(손해 건수 바뀐 칸 0, 차이 중앙값 변화 모두 0.01 미만이면 기준 변경)은 {'만족한다' if ok57 else '만족하지 않는다'}. "
        "'차이 중앙값 최대 변화'는 절댓값으로, 표의 차이중앙값·기초연금차(표 7-1은 네 기초연금 열) 중 가장 큰 변화. 대조판 = `N/intalt/`, 칸 목록 = `N/int_timing_cells.csv`.",
        "",
        md_table(t57),
        "",
        "손해 건수가 바뀐 칸:",
        "",
        md_table(t57c),
        "",
        star_l,
        "",
        star_x,
        "",
        "## 표 6. 연금저축 연금소득(과세분)이 한 해 1,500만 원을 넘는 경로 (N판, 70세 비교, 국민연금 0)",
        "",
        "넘는 해는 종합과세 증분과 15%(+지방세) 분리 중 작은 쪽, 넘지 않는 해는 분리 5.5%와 종합과세 증분 중 작은 쪽으로 세금을 냈다(가정 9).",
        "",
        md_table(o15),
        "",
        "## 표 7. 70세 연금저축 원인 분해 (기준 셀 S_lo, 주식 100%, 월 30만 원, 같은 경로 차이의 중앙값 ÷ 누적 납입)",
        "",
        "단계 (가) F판 → (나) 62세부터 해마다 인출(인출액 F판 세율 4.4%, 건보·기초연금 없이, 70세 말 잔액 4.4%) → (다) N판 인출 과세(5.5%·종합과세 선택·1,500만 원 처리 = N판 기준 셀) "
        "→ (라) 건보료 S_hi. (가)·(다)는 F판·N판 기준 셀과 같은지 코드에서 대조했다. 세부 = `N/decomp_p70.csv`.",
        "단계 행은 경로별 차이의 중앙값이라 더해도 합계 행과 같지 않다(중앙값은 더해지지 않음).",
        "",
        md_table(t7),
        "",
        "### 표 7-1. 단계 (마): (다)·(라)에 더해지는 기초연금 (연금저축·예금·노란우산 쪽, 65~70세 합계 ÷ 누적 납입, 중소도시, 중앙값)",
        "",
        "예금·노란우산 쪽은 K1·K2와 무관하다(같은 값이 반복). 노란우산 안넣음 = 적립금을 금융재산에서 뺌(기본, 노란우산 쪽 기초연금의 상한), "
        "넣음 = 그해 첫날 적립금을 금융재산에 넣음(납입 중 부금의 산입 여부는 미확인, 감사 r2 M5; 사업안내 인쇄 79쪽 금융재산 정의에 '부금'이 있어 넣음 판이 정의에 가깝다). "
        "세부 = `N/decomp_bp_p70.csv`.",
        "",
        GUIDE + " 이 표는 기본판만이라 ★ = K1 전액·K2 안넣음 행의 연금저축 열(K1·K2는 연금저축 쪽에만 걸림).",
        "",
        md_table(star(t7b.rename(columns={"b": "사람(기초연금)"}), ["연금저축 (가)", "연금저축 (나)", "연금저축 (다)"])),
        "",
        "## ⚠ 후보를 바꾸면 결과가 바뀌는 결정 (N판, 월 30만 원)",
        "",
        md_table(cs.assign(결정=cs.D.map(lambda d: CP.DEC[d][0]))[["D", "결정", "후보", "경고셀", "셀"]]),
        "",
        "## 가정과 한계",
        "",
        "가정(앞선 보고 '판단이 필요한 것' 번호, 15~17은 감사 r1 반영):",
        "",
        *[f"- {k}: {v}" for k, v in CP.ASSUME.items()],
        "",
        "한계(감사 r1·r2 중 고치지 않고 밝히는 것):",
        "",
        *[f"- {k}: {v.format(**fill)}" for k, v in CP.LIMITS.items()],
        "",
        "## 계산하지 않은 것",
        "",
        *[f"- {k}: {v}" for k, v in CP.NOT_COMPUTED.items()],
        "",
        "## 재현",
        "",
        "`PYTHONPATH= PYTHONIOENCODING=utf-8 python notebooks/candidate5/_gen_cand5p.py` (빠른 시험은 `C5P_QUICK=1`). 세부 표는 F/·N/ 폴더 CSV. "
        "입력 자료 파일과 입력 표(주식·채권·예금 월수익), 코드·설계서·근거 파일의 sha256과 git_head·code_dirty는 `run_meta.txt`(한계 'r2 M9').",
    ]
    text = "\n".join(L) + "\n"
    bad = [w for w in C.FORBID if w in text]
    assert not bad, f"금지어 {bad}"
    md = run / f"후보5_포트폴리오판_결과_{'quick_' if QUICK else ''}20261106.md"
    md.write_text(text, encoding="utf-8")
    pdf = md_to_pdf(md); doc_check(md)
    return pdf


def doc_diff(md: str, html: str, pdf: str) -> list[str]:
    """숫자 토큰 = 부호(+, -; 유니코드 마이너스 − = 하이픈) 붙은 숫자, 끝 마침표·쉼표 뗌. md → html: 표 수·칸 수·칸마다 토큰, 본문 전체(표·문장)
    토큰이 같은 순서로 같음. pdf: md 본문 전체 토큰이 개수까지 모두 있음(쪽마다 되풀이되는 표 머리 때문에 pdf에 더 있는 것은 허용). 반환 = 문제 목록.
    정리 재감사 낮음 1(2026-11-08): 표 칸만·부호 없이 보던 것을 본문 문장·부호까지 넓힘."""
    import html as H, re
    from collections import Counter
    tok = lambda s: [t.rstrip(".,") for t in re.findall(r"[+-]?\d[\d,.]*", s.replace("−", "-"))]
    L = md.splitlines(); nt, nh = sum(l.startswith("|---") for l in L), html.count("<table")
    mc = [tok(c) for l in L if l.startswith("|") and not l.startswith("|---") for c in l.strip()[1:-1].split(" | ")]
    hc = [tok(H.unescape(re.sub(r"<[^>]+>", "", c))) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", html, re.S)]
    a = tok(re.sub(r"(?m)^([-*] )?\d+\. ", "", md))                                  # 목록 번호(mistune이 <ol>로 바꿔 글자로 안 남음)는 뺌
    b = tok(H.unescape(re.sub(r"<[^>]+>", " ", html.split("<body>", 1)[-1])))
    k = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None if len(a) == len(b) else min(len(a), len(b)))
    miss = Counter(a) - Counter(tok(pdf))
    return ([f"표 수 md {nt} ≠ html {nh}"] if nt != nh else []) + ([f"칸 수 md {len(mc)} ≠ html {len(hc)}"] if len(mc) != len(hc) else []) \
        + [f"칸 {j} 숫자 md {x} ≠ html {y}" for j, (x, y) in enumerate(zip(mc, hc)) if x != y][:5] \
        + ([f"본문 숫자 {k}번째부터 md {a[k:k + 3]} ≠ html {b[k:k + 3]} (md {len(a)}개·html {len(b)}개)"] if k is not None else []) \
        + ([f"pdf 대조 숫자 {len(a)}개뿐"] if len(a) < 100 else []) + ([f"pdf에 없거나 모자란 숫자 {sum(miss.values())}개: {list(miss)[:5]}"] if miss else [])


def doc_check(md: Path) -> None:
    """정리 감사 L3(2026-11-08): html·pdf가 md와 같은 내용인지(doc_diff). 다르면 실행을 멈춘다."""
    import fitz, re
    with fitz.open(md.with_suffix(".pdf")) as d:
        pdf = "".join(p.get_text() for p in d)
    txt, html = md.read_text(encoding="utf-8"), md.with_suffix(".html").read_text(encoding="utf-8")
    bad = doc_diff(txt, html, pdf)
    assert not bad, "결과 문서 html·pdf ≠ md: " + "; ".join(bad)
    assert doc_diff(txt, html.replace("<td>", "<td>9", 1), pdf) and doc_diff(txt, html, pdf[:len(pdf) // 2])   # 점검이 바뀐 html·잘린 pdf를 잡는지
    s = "+0.167" if "+0.167" in html else re.search(r"\+\d[\d.]*", html).group()   # 낮음 1: 부호만 뒤집은 가짜(+0.167 → −0.167)도 잡는지
    fake = doc_diff(txt, html.replace(s, "−" + s[1:], 1), pdf.replace(s, "−" + s[1:], 1))
    assert any("html" in x for x in fake) and any("pdf" in x for x in fake), fake
    log(f"문서 대조 통과: 표 {html.count('<table')}개·칸 {html.count('<td>') + html.count('<th>')}개·본문 숫자 md = html, pdf 숫자 확인; "
        f"가짜 부호({s} → −{s[1:]}) 점검이 멈춤: {fake}")


if __name__ == "__main__":
    t0 = time.time()
    C._check(); CP._check()
    run = OUT / f"{'quick' if QUICK else 'run'}_{datetime.datetime.now():%Y%m%d_%H%M}"; run.mkdir(parents=True)
    lf = open(run / "run_log.txt", "w", encoding="utf-8", buffering=1)   # 감사 L3: 화면 출력·오류를 실행 폴더에도

    class Tee:
        def __init__(s, a): s.a = a
        def write(s, x): s.a.write(x); lf.write(x)
        def flush(s): s.a.flush(); lf.flush()
        def __getattr__(s, k): return getattr(s.a, k)               # encoding·isatty 등은 원래 스트림
    sys.stdout, sys.stderr = Tee(sys.stdout), Tee(sys.stderr)
    log(f"시작 {run} (빠른 시험={QUICK})")
    mde = CP.mde_table(inp(CP.REC)); mde.to_csv(run / "mde.csv", index=False, encoding="utf-8-sig")
    hand_checks().to_csv(run / "hand_checks.csv", index=False, encoding="utf-8-sig")
    rbar, period = rate_2026(); ppl = CP.people(rbar)
    pt = people_table(ppl, rbar); pt.to_csv(run / "people_2026.csv", index=False, encoding="utf-8-sig")
    log(f"r̄ {period} 월 {rbar:.6f}\n" + pt.to_string(index=False))
    compute(run / "F", CP.F_ONLY, mde, ppl)
    reg = regress(run); reg.to_csv(run / "regress_F_vs_frozen.csv", index=False, encoding="utf-8-sig")
    log("F판 = 동결 결과 대조 통과\n" + reg.to_string(index=False))
    compute(run / "N", {"N1": True, "N2": True, "N3": True}, mde, ppl)
    decompose(run / "N", ppl)
    defer_run(run / "N", ppl)
    ext_run(run / "N", ppl, rbar)
    ext_late(run / "N", ppl, rbar)
    int_alt(run / "N", ppl, rbar); int_compare(run / "N"); star_alt(run / "N", ppl, rbar)
    guide_check(run / "N" if CP.REC["int_t"] == "same" else run / "N" / "intalt")   # 대조 CSV는 같은 해 판으로 만든 값
    CP.constants_table().to_csv(run / "N" / "constants.csv", index=False, encoding="utf-8-sig")
    mods = [f"src/pension_lab/{m}.py" for m in ("cand5", "cand5p", "pilot7", "pilot9", "lifecycle", "bootstrap", "paths", "runrecord")] + \
           ["notebooks/candidate5/_gen_cand5.py", "notebooks/candidate5/_doc_cand5.py", "notebooks/candidate5/_diff_runs_cand5p.py",   # 감사 R2-L2·L4: 비교 도구
            # 감사 r2 M9: 커밋하지 않으므로(회원 지시) 설계서·근거 파일·SOURCES.md의 sha256도 남김
            "docs/ideas/본연구후보_20261027/후보5_간단테스트/설계서_후보5_포트폴리오판_20261106.md",
            "references/후보5_추가규칙_1차출처_20261106.md", "references/후보5_기초연금_사람3명_근거_20261106.md",
            "references/law_소득세법_47의2_연금소득공제_20261106.md", "references/law_소득세법_50_기본공제_20261107.md",   # R3-M2
            "references/law_조특법_86의3_노란우산_20261107.md"]   # 사업안내 발췌·SOURCES.md는 공개본에 없어 뺌(쪽 번호만 남김)
    ins = [paths.DATA_ROOT / "processed" / "pilot9_ecos_deposit_rates_monthly.csv", paths.DATA_ROOT / "raw" / "kr_hist_20261016" / "kr_deposit_annual_kostat2015_1945_2014.csv",
           paths.EQUITY_KR / "idx_kospi200.csv", paths.EQUITY_KR / "idx_kospi200_fundamental.csv",       # L13 주식 입력(pilot7가 직접 읽는 파일)
           paths.DATAGUIDE / "dg_econ_divyield_rates_19900101.csv", paths.DATAGUIDE / "dg_kospi_k200_tr_daily_19800104.csv"]
    # L13: 채권·현금은 io.asset_series를 거쳐 파일이 여럿이라, 실제로 쓴 월 입력 표(eq·bd·dep) 자체의 해시도 남김
    tabs = {d15: hashlib.sha256(inp({**CP.REC, "D15": d15}).to_csv().encode("utf-8")).hexdigest() for d15 in ("main", "s7")}
    rr.write_run_meta(run, Path(__file__), mods, f"quick={QUICK}\nfrozen={FROZEN}\n"
                      "doc=결과 md를 이 실행에서 만들고 같은 실행에서 html·pdf로 변환(_gen_cand5.md_to_pdf). code_dirty가 clean이 아니면 실행 코드 = 뒤 커밋 중 dep sha256이 같은 커밋\n" + "".join(f"input {p} sha256={rr.raw_sha256(p)}\n" for p in ins)
                      + "".join(f"input_table D15={k} (C.inputs eq·bd·dep, to_csv) sha256={v}\n" for k, v in tabs.items()))
    log(f"문서 {build_doc(run, rbar, period)}")
    log(f"끝 {time.time() - t0:.0f}초")
