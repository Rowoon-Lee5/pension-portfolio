"""2004-06 이전 한국 채권 실제 총수익 보완 조사 (2026-10-17).

찾은 공개·무료 실제 총수익: 한경 KIS 채권지수(한국경제신문·KIS채권평가 공동, 기준일 2001-01-01=100, 일별).
datacenter.hankyung.com/kis-bond 화면이 쓰는 공개 JSON(/data/datafile/stock/json/kisBondData.json)을 그대로 받는다.
단계(인자): fetch | parse | compare | all
  fetch  : JSON 원문 저장(있으면 덮지 않음) + manifest.csv(URL·sha256·접속시각·HTTP 상태). 403·429면 중단.
  parse  : 17개 지수 × 총수익·순가격 일별 → kis_daily_2001.csv, 월말 → kis_monthly_2001.csv, 결함 → defects.csv.
  compare: 입력 대조만(전략 결과 아님). ① KIS 국고채권 TR vs 기존 실제 TR(DataGuide FBI.KTB.01.2·KRX 프라임·NICE·KAP) 겹침 월수익
           ② KIS vs pilot7._kr_bond_long 합성(2001-01~2004-06) ③ 1997~1998 합성 월수익(실제 자료 없음 표기).
저장: D:\\pension-lab_data\\raw\\kr_bond_pre2004_20261017\\
실행: cd src && set "PYTHONPATH=." && python -m pension_lab.fetch.kr_bond_pre2004 all
"""
from __future__ import annotations
import csv, hashlib, json, sys
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import requests
from .. import paths

OUT = paths.RAW / "kr_bond_pre2004_20261017"
URL = "https://datacenter.hankyung.com/data/datafile/stock/json/kisBondData.json"
RAWJ = OUT / "hankyung_kisBondData_20261017.json"
KST = timezone(timedelta(hours=9))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def fetch() -> None:
    if RAWJ.exists():
        st, note = "기존", "이미 받음(2026-10-17 curl) → 덮지 않음"
    else:
        r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        if r.status_code in (403, 429) or "captcha" in r.text[:2000].lower():
            sys.exit(f"차단 HTTP {r.status_code} → 중단")
        r.raise_for_status(); RAWJ.write_bytes(r.content); st, note = r.status_code, "새로 받음"
    new = not (OUT / "manifest.csv").exists()
    with (OUT / "manifest.csv").open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new: w.writerow(["file", "url", "http", "sha256", "bytes", "checked_kst", "note"])
        w.writerow([RAWJ.name, URL, st, sha(RAWJ), RAWJ.stat().st_size, datetime.now(KST).isoformat(timespec="seconds"), note])


def parse() -> pd.DataFrame:
    d = json.loads(RAWJ.read_text(encoding="utf-8"))
    cols, bad = {}, []
    for code, v in d.items():
        for t, lab in (("total", "TR"), ("profit", "NP")):
            a = np.array(v["chart"][t], dtype=float)
            s = pd.Series(a[:, 1], index=pd.to_datetime(a[:, 0], unit="ms").normalize(), name=f"{code}_{lab}")
            if s.index.duplicated().any(): bad.append((s.name, "날짜 중복", int(s.index.duplicated().sum())))
            if (s <= 0).any() or s.isna().any(): bad.append((s.name, "0 이하·결측", int(((s <= 0) | s.isna()).sum())))
            r = s.pct_change().abs()
            for dt, x in r[r > 0.03].items(): bad.append((s.name, f"일 변화 3% 초과 {dt.date()}", round(float(x), 4)))
            cols[s.name] = s[~s.index.duplicated()]
    names = pd.DataFrame([(k, v["name"]) for k, v in d.items()], columns=["code", "name"])
    df = pd.DataFrame(cols).sort_index(); df.index.name = "date"
    df.to_csv(OUT / "kis_daily_2001.csv", float_format="%.4f")   # 원문 그대로(오류값 포함)
    # 정제: 수준값이 앞뒤 11개 관측 중앙값의 절반 미만이면 오류값으로 뺀다(원문에 0·음수·0.03 같은 '전일대비'로 보이는 값,
    # 2023-10-04 국고채권 TR 자리에 92.25 등). 0.4~0.9 어느 기준이어도 KTB·GBI·KBI 제거 집합이 같음(REPORT).
    med = df.rolling(11, center=True, min_periods=3).median()
    cl = df.mask(df < 0.5 * med)
    for c in df:
        for dt in df.index[(df[c] < 0.5 * med[c]).to_numpy()]: bad.append((c, f"정제 제거 {dt.date()}", float(df.at[dt, c])))
        g = df[c].dropna().index.to_series().diff().dt.days
        for dt, x in g[g > 10].items(): bad.append((c, f"관측 공백 {x:.0f}일(~{dt.date()})", x))
    cl.to_csv(OUT / "kis_daily_2001_clean.csv", float_format="%.4f")
    cl.resample("ME").last().to_csv(OUT / "kis_monthly_2001_clean.csv", float_format="%.4f")
    names.to_csv(OUT / "kis_codes.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(bad, columns=["series", "defect", "value"]).to_csv(OUT / "defects.csv", index=False, encoding="utf-8-sig")
    print(df.index[0].date(), df.index[-1].date(), df.shape, "결함", len(bad))
    return df


def _m(s: pd.Series) -> pd.Series:
    return s.dropna().resample("ME").last().pct_change(fill_method=None)


def _stats(a: pd.Series, b: pd.Series, la: str, lb: str) -> dict:
    x = pd.concat([a, b], axis=1, keys=[la, lb]).dropna(); e = x[la] - x[lb]
    return {"A": la, "B": lb, "start": x.index[0].strftime("%Y-%m"), "end": x.index[-1].strftime("%Y-%m"), "n": len(x),
            "corr": round(x.corr().iat[0, 1], 4), "meanA_pct": round(100 * x[la].mean(), 3), "meanB_pct": round(100 * x[lb].mean(), 3),
            "mean_diff_pct": round(100 * e.mean(), 3), "sd_diff_pct": round(100 * e.std(), 3), "maxabs_diff_pct": round(100 * e.abs().max(), 3),
            "sdA_pct": round(100 * x[la].std(), 3), "sdB_pct": round(100 * x[lb].std(), 3),
            "annA_pct": round(100 * ((1 + x[la]).prod() ** (12 / len(x)) - 1), 2), "annB_pct": round(100 * ((1 + x[lb]).prod() ** (12 / len(x)) - 1), 2)}


def compare() -> None:
    from .. import pilot7
    k = pd.read_csv(OUT / "kis_daily_2001_clean.csv", index_col=0, parse_dates=True)
    kis = {c: _m(k[f"{c}_TR"]) for c in ("KISKTB", "KISGBI", "KISKBI")}
    bi = paths.BOND_INDEX
    dg = pd.read_excel(paths.DATAGUIDE / "bond_tr_index.xlsx", header=None, skiprows=14, index_col=0).iloc[:, 0]
    dg = pd.to_numeric(dg, errors="coerce"); dg.index = pd.to_datetime(dg.index)
    krx = pd.read_csv(bi / "krx_prime_maturity_TR.csv", index_col=0, parse_dates=True)
    nice = pd.read_csv(bi / "nice_ktb_maturity_TR_FULL.csv", index_col=0, parse_dates=True)
    ref = {"DG_FBI.KTB.01.2": _m(dg), "KRX프라임3Y_TR": _m(krx["a3_1_t"]), "KRX프라임5Y_TR": _m(krx["a5_1_t"]), "KRX프라임10Y_TR": _m(krx["a10_1_t"]),
           "NICE_3~5Y": _m(nice["m36_m60"]), "NICE_7~10Y": _m(nice["m84_m120"])}
    for f in ("2Y3Y", "3Y5Y", "5Y10Y", "over10Y"):
        ref[f"KAP_{f}"] = _m(pd.read_csv(bi / f"kap_ktb_{f}.csv", index_col=0, parse_dates=True)["TotalIndex"])
    syn = pilot7._kr_bond_long()   # TER 전 월수익; 2004-07~ = DG 실제
    rows = [_stats(kis[c].loc["2004-07":], r, f"한경KIS_{c}", n) for c in kis for n, r in ref.items()]
    rows += [_stats(kis[c].loc[:"2004-06"], syn.loc["2001-01":"2004-06"], f"한경KIS_{c}", "pilot7합성(국고3년)") for c in kis]
    pd.DataFrame(rows).to_csv(OUT / "compare_overlap.csv", index=False, encoding="utf-8-sig")
    m = pd.DataFrame({"pilot7합성_TER전": syn.loc["2001-01":"2004-06"], **{f"한경KIS_{c}": kis[c].loc["2001-01":"2004-06"] for c in kis}})
    m["차_KTB−합성"] = m["한경KIS_KISKTB"] - m["pilot7합성_TER전"]
    (100 * m).round(3).to_csv(OUT / "compare_2001_2004_monthly_pct.csv", encoding="utf-8-sig")
    c = pd.DataFrame({"pilot7합성_TER전_pct": (100 * syn.loc["1997-01":"1998-12"]).round(3)})
    c["구간_출처"] = ["국민주택5년 DataGuide 일별 월말 → par_bond_tr(5년)"] * len(c)
    c["실제_총수익_자료"] = "없음(공개·유료 확인 범위에서 2001-01 이전 실제 TR 지수 없음, REPORT 참조)"
    c.to_csv(OUT / "crisis_1997_1998_synthetic_only.csv", encoding="utf-8-sig")
    print(pd.DataFrame(rows).to_string())


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("fetch", "all"): fetch()
    if step in ("parse", "all"): parse()
    if step in ("compare", "all"): compare()
