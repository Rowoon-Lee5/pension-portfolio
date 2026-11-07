# -*- coding: utf-8 -*-
"""후보 5 간단 테스트 생성기. 명세 = docs/ideas/본연구후보_20261027/후보5_간단테스트/후보5_명세_결정표_20261027.md (+정정 r1).
단계: check(자가점검·constants·coverage 틀) → mde(결과 전 MDE, 커밋) → results(격자 전부, run 폴더) → nb(실행본 노트북) → doc(결과 md·PDF).
실행(git bash): PYTHONPATH= PYTHONIOENCODING=utf-8 python notebooks/candidate5/_gen_cand5.py --stage results
출력 = D:/pension-lab_data/results/candidate5_20261027/run_YYYYMMDD_HHMM/ (새 실행마다 새 폴더, 기존 폴더 비우지 않음). 판정 없는 기술.
"""
from __future__ import annotations
import argparse, datetime, functools, hashlib, json, subprocess, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pension_lab import cand5 as C, pilot7 as P7, bootstrap as BS, runrecord as rr  # noqa: E402

DOC = ROOT / "docs" / "ideas" / "본연구후보_20261027" / "후보5_간단테스트"
MDE_CSV = DOC / "data" / "cand5_mde_prerun.csv"
log = lambda s: print(f"[{datetime.datetime.now():%H:%M:%S}] {s}", flush=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
INPUT = functools.cache(lambda d05, d15, d16: C.inputs({**C.REC, "D05": d05, "D15": d15, "D16": d16}))
inp = lambda o: INPUT(o["D05"], o["D15"], o["D16"])


def latest_run() -> Path:
    return sorted(p for p in C.OUT.glob("run_2*") if p.is_dir())[-1]


def stage_check():
    C._check()
    DOC.joinpath("data").mkdir(exist_ok=True)
    C.constants_table().to_csv(DOC / "data" / "cand5_constants.csv", index=False, encoding="utf-8-sig")
    log(f"constants {len(C.constants_table())}행, 셀 {len(C.cells())}개")


def stage_mde():
    """결과 전: 세금 규칙 없이 '적립 주식 − 적립 예금'의 퍼짐으로 MDE. sha256을 찍어 커밋."""
    t = C.mde_table(inp(C.REC)); t.to_csv(MDE_CSV, index=False, encoding="utf-8-sig")
    log(f"MDE 저장 {MDE_CSV} sha256 {sha(MDE_CSV)}"); print(t.to_string(index=False))


def stage_results():
    run = C.OUT / f"run_{datetime.datetime.now():%Y%m%d_%H%M}"; run.mkdir(parents=True)
    mde = pd.read_csv(MDE_CSV); (run / "mde_used_sha256.txt").write_text(sha(MDE_CSV))
    save = lambda df, name: (df.to_csv(run / name, index=False, encoding="utf-8-sig"), log(f"저장 {name} {len(df)}행"))
    C.constants_table().to_csv(run / "constants.csv", index=False, encoding="utf-8-sig")
    stats, cov = [], []
    for cid, d, cand, o in C.cells():
        r = inp(o)
        for k, H in C.HS.items():
            df = C.run(r, o, H, "wd" if k.startswith("wd") else k)
            if cid == "base":
                save(df, f"base_hist_{k}.csv")
            n = C.nstat(r, df.path.nunique() if len(df) else 0, H)
            for a, b in C.PAIRS[k]:
                for an in C.P("w_eq"):
                    sub = df[df.asset == an] if len(df) else df
                    why = "" if len(sub) else ("1980~ 표본은 채권 자료 없음 → (B) 비교 불가" if o["D15"] == "s7" and an == "B" else "경로 0개")
                    cov.append({"cell": cid, "D": d, "후보": cand, "비교": k, "쌍": f"{a}<{b}", "asset": an, "rows": len(sub), "이유": why})
                    if len(sub):
                        stats.append(C.loss_stats(sub, a, b).assign(cell=cid, D=d, 후보=cand, 비교=k, 쌍=f"{a}<{b}", n_eff=n["n_eff"]))
    cov += [{"cell": "전체", "D": "", "후보": "", "비교": "", "쌍": k, "asset": "", "rows": 0, "이유": f"계산 안 함: {v}"} for k, v in C.NOT_COMPUTED.items()]
    cov = pd.DataFrame(cov); save(cov, "coverage.csv")
    assert ((cov.rows > 0) | (cov["이유"] != "")).all(), "계산도 이유도 없는 칸"
    st = pd.concat(stats, ignore_index=True); save(st, "grid_stats.csv")
    # 후보를 바꾸면 결과가 바뀌나: 기준(base) 대비 손해 비율 변화 ≥ 1/n_base 또는 |Δ중앙값| ≥ MDE → ⚠
    key = ["비교", "쌍", "asset", "m", "person"]
    base = st[st.cell == "base"][key + ["n", "loss_n", "p_loss", "median_gap", "worst"]]
    ch = st[st.cell != "base"].merge(base, on=key, suffixes=("", "_base")).merge(mde[["비교", "쌍", "asset", "mde", "비교불가"]], on=["비교", "쌍", "asset"], how="left")
    ch["d_p"] = ch.p_loss - ch.p_loss_base; ch["d_med"] = ch.median_gap - ch.median_gap_base
    ch["warn"] = (ch.d_p.abs() >= 1 / ch.n_base - 1e-12) | (ch.d_med.abs() >= ch.mde)   # mde NaN(비교 불가) → 경로 수 기준만
    save(ch, "change_table.csv")
    save(ch.groupby(["D", "후보", "비교", "쌍"]).agg(셀=("warn", "size"), 경고=("warn", "sum"), 최대Δp=("d_p", lambda x: x.abs().max()),
                                               최대Δ중앙값=("d_med", lambda x: x.abs().max())).reset_index(), "change_summary.csv")
    # 폭락 달 인출(기술용): KOSPI200 가격의 2008·2020년 최저 월말
    r = inp(C.REC); lv = (1 + P7.kospi200_px()).cumprod(); crash = []
    for e in [lv.loc[y].idxmin() for y in ("2008", "2020")]:
        for H in (36, 60):
            s = r.index[r.index.get_loc(e) - H + 1]
            crash.append(C.run(r, C.REC, H, "wd", st=[s]).assign(폭락달=e.strftime("%Y-%m"), H=H))
    save(pd.concat(crash), "crash_cases.csv")
    # 세금 효과: 같은 경로에서 (나)−(가), (다)−(가) 연금저축 세후 차이 ÷ 누적납입
    rows = []
    for k in C.HS:
        d = pd.read_csv(run / f"base_hist_{k}.csv")
        w = d.pivot_table(index=["path", "asset", "m"], columns="person", values="ps").join(d.groupby(["path", "asset", "m"])["contrib"].first())
        for p in ("나", "다"):
            x = (w[p] - w["가"]) / w["contrib"]
            rows.append(x.groupby(level=["asset", "m"]).agg(["min", "median", "max"]).reset_index().assign(비교=k, 차이=f"({p})−(가)"))
    save(pd.concat(rows), "tax_effect.csv")
    # 블록 부트스트랩(기준 셀만): (eq, bd, dep) 같은 달 묶음, 평균 블록 3후보(정정r1 BOOT)
    blocks = {"PW_eq": P7.pw_block(r["eq"].to_numpy()), "PW_dep": P7.pw_block(r["dep"].to_numpy()), "12개월": 12.0}
    assert tuple(blocks) == C.BOOT_BLOCKS
    NB = C.P("n_boot"); bst = []
    for bn, blk in blocks.items():
        EQ, BD, DP = BS.paired_resample_paths([r["eq"], r["bd"], r["dep"]], NB, C.P("H70"), mean_block=blk, seed=C.P("seed"))
        for k, H in C.HS.items():
            o = C.REC; rows = []
            for an, w in C.P("w_eq").items():
                for m in C.P("monthly"):
                    acc = C.accumulate(EQ[:, :H], BD[:, :H], DP[:, :H], m, w, o)
                    for pn, room in C.rooms(o).items():
                        e = C.evaluate(acc, m, room, H, "wd" if k.startswith("wd") else k, o)
                        dd = pd.DataFrame({kk: v for kk, v in e.items() if np.ndim(v)}); dd["contrib"] = e["contrib"]
                        dd["asset"], dd["m"], dd["person"] = an, m, pn; rows.append(dd)
            dd = pd.concat(rows, ignore_index=True)
            if k == "p70" and bn == C.BOOT_BLOCKS[0]:
                dd["gap_dep"] = (dd.ps - dd.dep) / dd.contrib
                save(dd[(dd.m == 300_000)][["asset", "person", "gap_dep"]], "boot_p70_m30_gap.csv")
            for a_, b_ in C.PAIRS[k]:
                bst.append(C.loss_stats(dd, a_, b_).assign(블록=bn, 비교=k, 쌍=f"{a_}<{b_}"))
        log(f"부트스트랩 {bn} 블록 {blk:.2f} 끝")
    save(pd.concat(bst), "boot_stats.csv")
    json.dump({"blocks": blocks, "n_boot": NB, "seed": C.P("seed")}, open(run / "boot_meta.json", "w", encoding="utf-8"), ensure_ascii=False)
    mods = [f"src/pension_lab/{m}.py" for m in ("cand5", "pilot7", "pilot9", "lifecycle", "bootstrap", "paths", "runrecord")] + ["notebooks/candidate5/_doc_cand5.py"]
    ins = [C.paths.DATA_ROOT / "processed" / "pilot9_ecos_deposit_rates_monthly.csv", C.paths.DATA_ROOT / "raw" / "kr_hist_20261016" / "kr_deposit_annual_kostat2015_1945_2014.csv"]
    rr.write_run_meta(run, Path(__file__), mods, f"mde_sha256={sha(MDE_CSV)}\n" + "".join(f"input {p} sha256={sha(p)}\n" for p in ins))
    log(f"끝 {run}")


NB_CELLS = [
("md", "# 후보 5 간단 테스트 — 50대(2026년 만 57세) 자영업자: 연금저축 vs 노란우산 vs 예금\n명세 `docs/ideas/본연구후보_20261027/후보5_간단테스트/후보5_명세_결정표_20261027.md` + 정정r1. "
       "계산은 생성기 `--stage results`가 run 폴더에 저장, 이 노트북은 그 CSV를 읽어 보여 준다. 판정 없는 기술. 비율은 누적 납입 대비."),
("code", """import sys, json, pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path.cwd().resolve().parents[1]; sys.path.insert(0, str(ROOT / 'src'))
from pension_lab import cand5 as C
RUN = Path(r'{RUN}'); print(RUN.name, (RUN / 'run_meta.txt').read_text(encoding='utf-8'))
rd = lambda f: pd.read_csv(RUN / f)
plt.rcParams['font.family'] = 'Malgun Gothic'; plt.rcParams['axes.unicode_minus'] = False
FIG = ROOT / 'docs/ideas/본연구후보_20261027/후보5_간단테스트/fig'; FIG.mkdir(exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)"""),
("md", "## 상수·결정 후보·격자 coverage"),
("code", "print(rd('constants.csv').to_string(index=False))"),
("code", "cov = rd('coverage.csv'); print(cov.groupby(['D', '후보']).agg(칸=('rows', 'size'), 빈칸=('rows', lambda x: (x == 0).sum())).to_string()); print(cov[cov.rows == 0].drop_duplicates(['cell', '이유'])[['cell', '이유']].to_string(index=False))"),
("md", "## MDE (결과 전 고정)"),
("code", "print(pd.read_csv(ROOT / 'docs/ideas/본연구후보_20261027/후보5_간단테스트/data/cand5_mde_prerun.csv').to_string(index=False))"),
("md", "## 표 1·2·3 — 기준 셀(모든 결정 추천안)"),
("code", """st = rd('grid_stats.csv'); b = st[st.cell == 'base']
for k in C.HS:
    print('==', k); print(b[(b['비교'] == k)].pivot_table(index=['쌍', 'person', 'm'], columns='asset', values=['loss_n', 'n', 'n_eff', 'worst', 'median_gap'], sort=False).round(3).to_string())"""),
("md", "## ⚠ 후보를 바꾸면 결과가 바뀌나"),
("code", "cs = rd('change_summary.csv'); print(cs[cs['경고'] > 0].to_string(index=False)); print('경고 없는 결정·후보:', sorted(set(cs.D + ':' + cs['후보']) - set((cs[cs['경고'] > 0].D + ':' + cs[cs['경고'] > 0]['후보']))))"),
("md", "## 폭락 달 인출(기술용)·세금 효과·부트스트랩"),
("code", "cc = rd('crash_cases.csv'); cc = cc[cc.m == 300_000]; print(cc[['폭락달', 'H', 'path', 'asset', 'person', 'contrib', 'ps', 'dep', 'ny_cancel', 'ny_close']].round(0).to_string(index=False))"),
("code", "print(rd('tax_effect.csv').round(3).to_string(index=False))"),
("code", "print(json.load(open(RUN / 'boot_meta.json', encoding='utf-8'))); bs = rd('boot_stats.csv'); print(bs[bs.m == 300_000][['블록', '비교', '쌍', 'asset', 'person', 'n', 'p_loss', 'worst', 'median_gap']].round(3).to_string(index=False))"),
("md", "## 그림"),
("code", """yr = lambda d: d.path.str[:4].astype(int)
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
d0 = rd('base_hist_p70.csv')
for a, axx in zip('AB', ax):
    d = d0[(d0.m == 300_000) & (d0.asset == a)]
    for p, mk in zip('가나다', 'os^'):
        g = d[d.person == p]; axx.plot(yr(g), (g.ps - g.dep) / g.contrib, marker=mk, label=f'연금저축({p}) − 예금')
    g = d[d.person == '가']; axx.plot(yr(g), (g.ny_old - g.dep) / g.contrib, 'k--', label='노란우산(가) − 예금 (퇴직소득세 전)')
    axx.axhline(0, color='gray', lw=.8); axx.set_title(f'70세 시점, 월 30만 원, 자산 {a}'); axx.set_xlabel('역사 시작 연도(=2026년 1월로 봄)')
ax[0].set_ylabel('세후 금액 차이 ÷ 누적 납입'); ax[1].legend(fontsize=8); fig.tight_layout(); fig.savefig(FIG / 'fig1_p70_by_start.png', dpi=150)"""),
("code", """fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
for k, axx in zip(('wd36', 'wd60'), ax):
    d = rd(f'base_hist_{k}.csv'); d = d[(d.m == 300_000) & (d.asset == 'A')]
    for p, mk in zip('가나다', 'os^'):
        g = d[d.person == p]; axx.plot(yr(g), g.ps / g.contrib, marker=mk, label=f'연금저축({p})')
        axx.plot(yr(g), g.ny_cancel / g.contrib, ls=':', marker=mk, ms=3, label=f'노란우산 해약({p})')
    g = d[d.person == '가']; axx.plot(yr(g), g.dep / g.contrib, 'k-', lw=2, label='예금')
    axx.axhline(1, color='gray', lw=.8); axx.set_title(f'{k[2:]}개월째 전부 인출, 월 30만 원, 주식 100%'); axx.set_xlabel('역사 시작 연도')
ax[0].set_ylabel('세후 금액 ÷ 누적 납입'); ax[1].legend(fontsize=7, ncol=2); fig.tight_layout(); fig.savefig(FIG / 'fig2_withdraw.png', dpi=150)"""),
("code", """g = rd('boot_p70_m30_gap.csv'); fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
for a, axx in zip('AB', ax):
    for p in '가다':
        x = g[(g.asset == a) & (g.person == p)].gap_dep; axx.hist(x, bins=80, alpha=.5, density=True, label=f'({p}) 예금보다 적은 경로 {(x < 0).mean():.1%}')
    axx.axvline(0, color='k', lw=.8); axx.set_title(f'블록 부트스트랩 1만 경로, 70세, 월 30만 원, 자산 {a}'); axx.set_xlabel('(연금저축 − 예금) ÷ 누적 납입'); axx.legend()
fig.tight_layout(); fig.savefig(FIG / 'fig3_boot_p70.png', dpi=150)"""),
]


def stage_nb():
    import nbformat as nbf
    from nbclient import NotebookClient
    run = latest_run()
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(c) if t == "md" else nbf.v4.new_code_cell(c.replace("{RUN}", str(run))) for t, c in NB_CELLS]
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    path = ROOT / "notebooks" / "candidate5" / "cand5_simple_20261027.ipynb"
    NotebookClient(nb, timeout=1800, kernel_name="python3", resources={"metadata": {"path": str(path.parent)}}).execute()
    rr.save_executed(nb, path, run / "executed_notebooks")
    log(f"{path} {path.stat().st_size:,} bytes")


def md_to_pdf(md_path: Path) -> Path:
    """md → HTML(mistune, 맑은고딕) → Edge headless PDF."""
    import mistune
    html = mistune.create_markdown(plugins=["table"])(md_path.read_text(encoding="utf-8"))
    css = ("body{font-family:'Malgun Gothic',sans-serif;font-size:10.5pt;line-height:1.55;margin:18mm}"
           "table{border-collapse:collapse;font-size:8.5pt;margin:6px 0}td,th{border:1px solid #999;padding:2px 5px}"
           "th{background:#eee}img{max-width:100%}h1{font-size:17pt}h2{font-size:13.5pt;border-bottom:1px solid #ccc}code{font-size:8.5pt}")
    h = md_path.with_suffix(".html")
    h.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{html}</body></html>", encoding="utf-8")
    pdf = md_path.with_suffix(".pdf"); edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", h.as_uri()], check=True, timeout=120)
    assert pdf.exists() and pdf.stat().st_size > 10_000, "PDF 생성 실패"
    return pdf


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", required=True, choices=["check", "mde", "results", "nb", "doc", "pdf"])
    ap.add_argument("--md"); a = ap.parse_args()
    t0 = time.time(); log(f"stage {a.stage} 시작")
    if a.stage == "pdf":
        log(md_to_pdf(Path(a.md)))
    elif a.stage == "doc":
        import _doc_cand5; _doc_cand5.build(latest_run(), md_to_pdf)
    else:
        globals()[f"stage_{a.stage}"]()
    log(f"stage {a.stage} 끝 {time.time() - t0:.0f}초")
