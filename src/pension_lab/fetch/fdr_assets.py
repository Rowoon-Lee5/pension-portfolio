"""FinanceDataReader 자산군 수집: 해외주식·해외채권·원자재·거시.
Adj Close(있으면)=배당재투자 총수익. 실행: python -m pension_lab.fetch.fdr_assets
"""
from __future__ import annotations
import warnings
import FinanceDataReader as fdr
from .. import paths

warnings.filterwarnings("ignore")

# (심볼, 저장폴더, 파일명) — Adj Close 우선
TARGETS = [
    ("SPY",      "EQUITY_GLOBAL", "global_us_spy_tr"),
    ("^GSPC",    "EQUITY_GLOBAL", "global_sp500"),
    ("^IXIC",    "EQUITY_GLOBAL", "global_nasdaq"),
    ("EFA",      "EQUITY_GLOBAL", "global_dev_exus_efa"),
    ("EEM",      "EQUITY_GLOBAL", "global_emerging_eem"),
    ("TLT",      "BOND_GLOBAL",   "global_ustreasury_long_tlt"),
    ("IEF",      "BOND_GLOBAL",   "global_ustreasury_mid_ief"),
    ("AGG",      "BOND_GLOBAL",   "global_us_aggbond_agg"),
    ("TIP",      "BOND_GLOBAL",   "global_us_tips_tip"),
    ("HYG",      "BOND_GLOBAL",   "global_us_highyield_hyg"),
    ("GC=F",     "COMMODITY",     "gold_long"),
    ("CL=F",     "COMMODITY",     "global_wti_oil"),
    ("HG=F",     "COMMODITY",     "global_copper"),
    ("DX-Y.NYB", "MACRO",         "global_usd_index_dxy"),
    ("^VIX",     "MACRO",         "global_vix"),
]


def run(start: str = "2000-01-01") -> None:
    for sym, folder, fname in TARGETS:
        outdir = getattr(paths, folder)
        outdir.mkdir(parents=True, exist_ok=True)
        try:
            d = fdr.DataReader(sym, start)
            if d is None or len(d) == 0:
                print(f"[skip] {sym}: 빈데이터"); continue
            col = "Adj Close" if "Adj Close" in d.columns else "Close"
            s = d[[col]].rename(columns={col: "close"}); s.index.name = "date"
            s.to_csv(outdir / f"{fname}.csv", encoding="utf-8-sig")
            print(f"[ok] {fname:30s} {sym:10s} {len(s)}행 {str(s.index.min())[:10]}~{str(s.index.max())[:10]}")
        except Exception as e:
            print(f"[ERR] {sym}: {e!r}")


if __name__ == "__main__":
    run()
