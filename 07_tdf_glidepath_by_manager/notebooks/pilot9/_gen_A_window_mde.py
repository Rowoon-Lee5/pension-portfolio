# -*- coding: utf-8 -*-
"""A_window_mde_20261026.ipynb 생성기 — A′ 가능성 점검(빈티지별 5대 공통 구간, 운용사 쌍 최소 구별 차이).
명세 = docs/DECISION_LOG.md 2026-10-26 'A′ 가능성 점검 명세'(결과 전 기록). 판정 없는 기술.
실행: (cmd) set "PYTHONPATH=" 뒤 set PYTHONIOENCODING=utf-8 & python notebooks\\pilot9\\_gen_A_window_mde.py
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT.parent / "src"))
from pension_lab import runrecord as rr, paths  # noqa: E402

NB_PATH = ROOT / "notebooks" / "pilot9" / "A_window_mde_20261026.ipynb"
OUTD = (paths.DATA_ROOT / "results/pilot9_20261013/A_window_mde_20261026")
INPUTS = [(paths.DATA_ROOT / "processed/nav_tdf_clean_v3_20260928.csv"),
          (paths.DATA_ROOT / "raw/fund_tdf/early_class_nav/early_class_nav_20261012.csv")]
nb = nbf.v4.new_notebook(); cells = []
def md(s): cells.append(nbf.v4.new_markdown_cell(s))
def code(s): cells.append(nbf.v4.new_code_cell(s))

md("""# A′ 가능성 점검: 같은 빈티지, 5대 운용사 실제 기록은 얼마나 길고, 얼마만큼의 차이를 구별할 수 있나 (2026-10-26)
**명세.** `docs/DECISION_LOG.md` 2026-10-26 'A′ 가능성 점검 명세'(결과 전 기록) 그대로. **판정 없는 기술.**
- 자료: 5대 TDF 35펀드 결산 보정 기준가(`nav_tdf_clean_v3`), 월말 값 → 월 수익(보수·환헤지·운용이 모두 들어 있는 실제 수익).
- 쌍별 월 수익 차 d로 연평균 차 = 12·mean(d), SE = 12·sd(d)/√T, **MDE = 2.80·SE**(양측 5%·검정력 80% 관행값). MDE보다 작은 연평균 차이는 이 기간으로 구별하기 어렵다는 뜻이다.""")

code(r"""import numpy as np, pandas as pd
from pathlib import Path
from pension_lab import tdf_style as ts, paths
OUTD = (paths.DATA_ROOT / "results/pilot9_20261013/A_window_mde_20261026"); OUTD.mkdir(parents=True, exist_ok=True)
nav = ts.load_nav('clean_v3')
me = nav.resample('ME').last()
cnt = nav.resample('ME').count()
me = me.where(cnt > 0)                                   # 그달 기준가가 없으면 비움
ret = me.pct_change(fill_method=None)
END = pd.Timestamp('2026-08-31')                         # 마지막 완전한 달(자료 끝 2026-09-23)
ret = ret.loc[:END]
info = pd.DataFrame({'mgr': ts.MGR, 'vintage': ts.V}).loc[nav.columns]
assert info.groupby('vintage').mgr.nunique().eq(5).all(), info.groupby('vintage').mgr.nunique()
first = nav.apply(lambda s: s.first_valid_index())
print(info.assign(first_nav=first.dt.date).sort_values(['vintage', 'mgr']).to_string())""")

md("## 1. 빈티지별 5대 공통 구간")
code(r"""rows, R = [], {}
for v, g in info.groupby('vintage'):
    r = ret[g.index].rename(columns=g.mgr)
    full = r.dropna()                                    # 다섯 펀드 모두 수익이 있는 달
    R[v] = full
    rows.append(dict(vintage=v, start=full.index.min().date(), end=full.index.max().date(), months=len(full),
                     years=round(len(full) / 12, 2), latest_starter=g.mgr[first[g.index].idxmax()]))
win = pd.DataFrame(rows); win.to_csv(OUTD / 'common_window.csv', index=False, encoding='utf-8-sig')
print(win.to_string(index=False))""")

md("## 2. 운용사 쌍별 연평균 수익 차와 최소 구별 차이(MDE)\n표의 `mean_diff`·`t`는 참고용 기술이며 판정에 쓰지 않는다(10쌍 다중비교 보정 안 함).")
code(r"""def nw_se(d, L=3):                                     # Newey-West(Bartlett) 평균의 표준오차
    x = d - d.mean(); T = len(x); s = (x @ x) / T
    for l in range(1, L + 1):
        s += 2 * (1 - l / (L + 1)) * (x[l:] @ x[:-l]) / T
    return np.sqrt(s / T)
pr = []
for v, full in R.items():
    T = len(full); cols = list(full.columns)
    for i in range(5):
        for j in range(i + 1, 5):
            d = (full[cols[i]] - full[cols[j]]).to_numpy()
            se = 12 * d.std(ddof=1) / np.sqrt(T); se_nw = 12 * nw_se(d)
            pr.append(dict(vintage=v, pair=f'{cols[i]}−{cols[j]}', T=T, mean_diff_pctpa=1200 * d.mean(),
                           te_pctpa=100 * d.std(ddof=1) * np.sqrt(12), se_pctpa=100 * se, t=d.mean() * 12 / se,
                           mde_pctpa=100 * 2.80 * se, mde_nw_pctpa=100 * 2.80 * se_nw))
pr = pd.DataFrame(pr); pr.to_csv(OUTD / 'pair_mde.csv', index=False, encoding='utf-8-sig')
pd.set_option('display.width', 200)
print(pr.round(2).to_string(index=False))""")

md("## 3. 빈티지별 요약(쌍 10개의 MDE 범위)")
code(r"""sm = pr.groupby('vintage').agg(T=('T', 'first'), mde_min=('mde_pctpa', 'min'), mde_med=('mde_pctpa', 'median'),
                                mde_max=('mde_pctpa', 'max'), mde_nw_med=('mde_nw_pctpa', 'median'),
                                absdiff_med=('mean_diff_pctpa', lambda x: x.abs().median()), te_med=('te_pctpa', 'median')).reset_index()
sm.to_csv(OUTD / 'vintage_summary.csv', index=False, encoding='utf-8-sig')
print(sm.round(2).to_string(index=False))""")

md("""## 4. 참고: 이른 클래스로 늘어날 수 있는 시작일(날짜만)
`early_class_nav`는 같은 펀드의 다른(이른) 클래스 기준가다. 여기서는 **이어 붙이지 않고** 시작 날짜만 본다. MDE는 같은 sd에서 √(T/T′)로 줄인 **추정**이다.""")
code(r"""ec = pd.read_csv((paths.DATA_ROOT / "raw/fund_tdf/early_class_nav/early_class_nav_20261012.csv"), dtype=str)
ec_first = pd.to_datetime(ec.groupby('code31').v1.min())
ext_first = pd.concat([first, ec_first.rename('e')], axis=1).min(axis=1)
rows = []
for v, g in info.groupby('vintage'):
    st = ext_first[g.index].max(); st_m = (st + pd.offsets.MonthEnd(0)) + pd.offsets.MonthEnd(1)   # 그다음 달부터 완전한 월 수익
    Tp = len(pd.date_range(st_m, END, freq='ME')); T = len(R[v])
    rows.append(dict(vintage=v, ext_start=st_m.date(), ext_months=Tp, months_now=T,
                     mde_med_now=sm.set_index('vintage').mde_med[v], mde_med_ext_est=sm.set_index('vintage').mde_med[v] * np.sqrt(T / Tp)))
ext = pd.DataFrame(rows); ext.to_csv(OUTD / 'ext_window_est.csv', index=False, encoding='utf-8-sig')
print(ext.round(2).to_string(index=False))""")

md("""## 한계
- 클래스(C, C1, C-Pe 등)마다 보수가 달라 쌍별 차이에 **보수 차이가 섞여 있다**. 환헤지(H/UH) 차이도 섞여 있다. 운용 실력만의 차이가 아니다.
- 현존 펀드만 있다(생존편향). 10쌍 다중비교 보정은 하지 않았다.
- MDE의 2.80은 양측 5%·검정력 80% 관행값이다. 월 수익 차의 자기상관은 Newey-West(시차 3) 열로만 본다.
- 이른 클래스 연장은 날짜와 √T 추정뿐이다. 실제로 이어 붙이면 클래스 보수 차 보정이 필요하다.""")

nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
os.environ["PYTHONPATH"] = str(ROOT.parent / "src")
NotebookClient(nb, timeout=1800, kernel_name="python3", resources={"metadata": {"path": str(NB_PATH.parent)}}).execute()
rr.save_executed(nb, NB_PATH)
NBM = OUTD / "nb_meta"; NBM.mkdir(parents=True, exist_ok=True)
extra = "".join(f"input {p} sha256={rr.raw_sha256(p)}\n" for p in INPUTS) \
        + "".join(f"result {p.name} sha256={rr.raw_sha256(p)}\n" for p in sorted(OUTD.glob("*.csv")))
rr.write_run_meta(NBM, Path(__file__), ["src/pension_lab/tdf_style.py", "src/pension_lab/glidepath.py"], extra)
print("실행완료 저장:", NB_PATH, NB_PATH.stat().st_size, "bytes")
