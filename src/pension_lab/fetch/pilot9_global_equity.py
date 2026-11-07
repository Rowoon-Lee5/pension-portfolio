"""pilot9 판정용 해외주식(전 세계) 월별 총수익 수집 (2026-10-16).

1) MSCI 웹은 2026-10-16 reCAPTCHA + 약관상 자동 수집 금지 → 요청하지 않음(규칙 19). 증거: msci_eod_probe_response.html·manifest.csv.
2) Kenneth French Data Library 지역 시장수익(월별, USD, 배당 포함): 시장 총수익 = (Mkt-RF) + RF.
3) 비교용 ETF 총수익(배당 재투자 수정종가, yfinance): ACWI(MSCI ACWI 추종)·URTH(MSCI World 추종).
4) 검증: 겹치는 달에 기존 SPY·EFA·EEM 총수익, French 미국 시장, French 국가별(일본)과 월수익 상관·평균차.
산출: raw\\global_equity_20261016\\ (원 파일 그대로 + 정리 CSV + manifest.csv + validation.csv)
실행: cd src && set "PYTHONPATH=." && python -m pension_lab.fetch.pilot9_global_equity
"""
from __future__ import annotations
import csv, hashlib, io, re, zipfile
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
from .. import paths

OUT = paths.RAW / "global_equity_20261016"
EG = paths.EQUITY_GLOBAL
H = {"User-Agent": "Mozilla/5.0 (pension-lab research)"}
KST = timezone(timedelta(hours=9))
FF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
REGIONS = {"developed": "Developed_3_Factors", "developed_ex_us": "Developed_ex_US_3_Factors",
           "emerging": "Emerging_5_Factors", "north_america": "North_America_3_Factors",
           "europe": "Europe_3_Factors", "japan": "Japan_3_Factors",
           "asia_pacific_ex_japan": "Asia_Pacific_ex_Japan_3_Factors"}
ETFS = ["ACWI", "URTH"]


def now() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def manifest(url: str, path, content: bytes, status, note: str = "") -> None:
    mp = OUT / "manifest.csv"
    new = not mp.exists()
    with mp.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["source_url", "saved_path", "sha256", "bytes", "http_status", "retrieved_at_kst", "note"])
        w.writerow([url, str(path), hashlib.sha256(content).hexdigest(), len(content), status, now(), note])


def get(url: str, name: str, note: str = "") -> tuple[int, bytes]:
    r = requests.get(url, headers=H, timeout=60)
    (OUT / name).write_bytes(r.content)
    manifest(url, OUT / name, r.content, r.status_code, note)
    return r.status_code, r.content


def parse_ff_monthly(text: str) -> pd.DataFrame:
    """French CSV 첫 블록(월별, YYYYMM 행)만 읽음. 연간 블록은 'Annual' 줄 뒤라 제외."""
    lines = text.splitlines()
    hi = next(i for i, l in enumerate(lines) if l.strip().startswith(",Mkt-RF"))
    rows = []
    for l in lines[hi + 1:]:
        if not re.match(r"^\s*\d{6}\s*,", l):
            break
        rows.append([c.strip() for c in l.split(",")])
    df = pd.DataFrame(rows, columns=["yyyymm"] + [c.strip() for c in lines[hi].split(",")[1:]])
    return df.set_index("yyyymm").astype(float)


def french() -> pd.DataFrame:
    out = []
    for reg, stem in REGIONS.items():
        st, b = get(FF + stem + "_CSV.zip", stem + "_CSV.zip", f"French {reg}")
        z = zipfile.ZipFile(io.BytesIO(b))
        nm = z.namelist()[0]
        txt = z.read(nm).decode("latin-1")
        (OUT / nm).write_text(txt, encoding="utf-8")
        d = parse_ff_monthly(txt)
        out.append(pd.DataFrame({"yyyymm": d.index, "region": reg, "mkt_rf_pct": d["Mkt-RF"].values,
                                 "rf_pct": d["RF"].values, "mkt_tr_pct": (d["Mkt-RF"] + d["RF"]).round(4).values}))
    df = pd.concat(out, ignore_index=True)
    df.to_csv(OUT / "french_region_mkt_monthly_usd.csv", index=False, encoding="utf-8-sig")
    return df


def etfs() -> None:
    import yfinance as yf
    for t in ETFS:
        d = yf.download(t, period="max", interval="1d", auto_adjust=True, progress=False)["Close"][t].dropna()
        p = OUT / f"etf_{t.lower()}_tr_daily_yf.csv"
        d.rename("total_return_close").to_csv(p, index_label="date", encoding="utf-8-sig")
        manifest(f"yfinance download {t} period=max auto_adjust=True", p, p.read_bytes(), "", "Yahoo 수정종가(배당 재투자) 2차")


def monthly_from_daily(p) -> pd.Series:
    s = pd.read_csv(p, index_col=0, parse_dates=True, encoding="utf-8-sig").iloc[:, 0].dropna()
    m = s.resample("ME").last()
    r = (m.pct_change() * 100).iloc[1:]   # 첫 달은 월중 시작이라 버림
    r.index = r.index.strftime("%Y%m")
    return r


def validate(ff: pd.DataFrame) -> pd.DataFrame:
    reg = {k: g.set_index("yyyymm")["mkt_tr_pct"] for k, g in ff.groupby("region")}
    us = parse_ff_monthly((EG / "french" / "F-F_Research_Data_Factors.csv").read_text(encoding="latin-1"))
    us = (us["Mkt-RF"] + us["RF"])
    jl = [l.split()[:2] for l in (EG / "french_intl" / "Japan.Dat").read_text(encoding="latin-1").splitlines()
          if re.match(r"^\s*\d{6}\s", l)]
    jp = pd.Series({k: float(v) for k, v in reversed(jl)})   # 같은 달이 여러 블록이면 첫 블록(달러 가치가중 Mkt) 값이 남음
    ser = {"SPY": monthly_from_daily(EG / "global_us_spy_tr.csv"), "EFA": monthly_from_daily(EG / "global_dev_exus_efa.csv"),
           "EEM": monthly_from_daily(EG / "global_emerging_eem.csv"), "ACWI_ETF": monthly_from_daily(OUT / "etf_acwi_tr_daily_yf.csv"),
           "URTH_ETF": monthly_from_daily(OUT / "etf_urth_tr_daily_yf.csv"), "FF_US_mkt": us, "FF_intl_Japan_country": jp}
    pairs = [("developed_ex_us", "EFA"), ("emerging", "EEM"), ("north_america", "SPY"), ("north_america", "FF_US_mkt"),
             ("developed", "URTH_ETF"), ("developed", "ACWI_ETF"), ("developed", "SPY"), ("japan", "FF_intl_Japan_country")]
    rows = []
    for a, b in pairs:
        x = pd.concat([reg[a], ser[b]], axis=1, join="inner").dropna()
        d = x.iloc[:, 0] - x.iloc[:, 1]
        rows.append(dict(french_region=a, compare=b, n_months=len(x), start=x.index.min(), end=x.index.max(),
                         corr=round(x.corr().iloc[0, 1], 4), mean_french_pct=round(x.iloc[:, 0].mean(), 4),
                         mean_compare_pct=round(x.iloc[:, 1].mean(), 4), mean_diff_pct_per_month=round(d.mean(), 4),
                         mean_diff_pct_annualized_x12=round(d.mean() * 12, 3), mean_abs_diff_pct=round(d.abs().mean(), 4),
                         te_pct_annualized=round(d.std() * 12 ** 0.5, 3)))
    v = pd.DataFrame(rows)
    v.to_csv(OUT / "validation.csv", index=False, encoding="utf-8-sig")
    return v


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ff = french()
    print(ff.groupby("region")["yyyymm"].agg(["min", "max", "count"]))
    etfs()
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(validate(ff))


if __name__ == "__main__":
    main()
