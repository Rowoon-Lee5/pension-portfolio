"""KOFIA(금융투자협회 전자공시) TDF 일별 기준가(NAV).
DataGuide 펀드 시계열이 라이선스상 안 나와서 KOFIA 무료 공시로 우회(로그인 불필요).

엔드포인트: POST https://dis.kofia.or.kr/proframeWeb/XMLSERVICES/  (text/xml)
서비스: DISFundStdPrcStutSO / select
DTO DISCondFuncDTO: tmpV30=시작일 tmpV31=종료일(YYYYMMDD) tmpV10=0 tmpV12=펀드표준코드
응답 DISCondFuncListDTO: tmpV1=기준일자 tmpV2=기준가(NAV)
※ 조회 3년 제한 → 3년 창 분할 후 dedupe.
실행: python -m pension_lab.fetch.kofia_tdf
"""
from __future__ import annotations
import re
import warnings
import requests
import pandas as pd
from .. import paths

warnings.filterwarnings("ignore")
_URL = "https://dis.kofia.or.kr/proframeWeb/XMLSERVICES/"
_H = {"Content-Type": "application/xml", "Referer": "https://dis.kofia.or.kr/"}

# 5대 운용사 × 빈티지(2025~2055) 대표 클래스 표준코드
CODES = [
    "K55301BM7939", "K55301BM7681", "K55301BM7582", "K55301BM7400", "K55301BM7509", "K55301D51180", "K55301EB2732",
    "K55105BC8937", "K55105BC8648", "K55105BC8515", "K55105BC8390", "K55105BC7780", "K55105CK1519", "K55105CX9376",
    "K55223BT0833", "K55223BT0999", "K55223BT1146", "K55223BT1351", "K55223BT1617", "K55223BT1807", "K55223D26691",
    "K55101BK8584", "K55101BK7347", "K55101BK7461", "K55101BK6919", "K55101BK7040", "K55101CU1578", "K55101DR6324",
    "K55210BR6233", "K55210BR6365", "K55210BR6498", "K55210BR6621", "K55210BR6753", "K55210CO3752", "K55210DT9688",
]
_WINDOWS = [("20110101", "20131231"), ("20140101", "20161231"), ("20170101", "20191231"),
            ("20200101", "20221231"), ("20230101", "20251231"), ("20260101", "20261231")]


def _body(code: str, start: str, end: str) -> str:
    return (f'<?xml version="1.0" encoding="utf-8"?><message>'
            f'<proframeHeader><pfmAppName>FS-DIS2</pfmAppName>'
            f'<pfmSvcName>DISFundStdPrcStutSO</pfmSvcName><pfmFnName>select</pfmFnName>'
            f'</proframeHeader><systemHeader></systemHeader>'
            f'<DISCondFuncDTO><tmpV30>{start}</tmpV30><tmpV31>{end}</tmpV31>'
            f'<tmpV10>0</tmpV10><tmpV12>{code}</tmpV12></DISCondFuncDTO></message>')


def _fetch_code(code: str) -> pd.DataFrame:
    recs = []
    for s, e in _WINDOWS:
        r = requests.post(_URL, data=_body(code, s, e).encode("utf-8"), headers=_H, timeout=40)
        for blk in re.findall(r"<DISCondFuncListDTO>(.*?)</DISCondFuncListDTO>", r.text, re.S):
            d = re.search(r"<tmpV1>(\d{8})</tmpV1>", blk)
            v = re.search(r"<tmpV2>([\d.]+)</tmpV2>", blk)
            if d and v:
                recs.append((d.group(1), float(v.group(1))))
    if not recs:
        return pd.DataFrame(columns=["date", "fund_code", "nav"])
    df = pd.DataFrame(recs, columns=["date", "nav"]).drop_duplicates("date")
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df["fund_code"] = code
    return df[["date", "fund_code", "nav"]].sort_values("date")


def run() -> None:
    out = paths.FUND_TDF
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    for c in CODES:
        df = _fetch_code(c)
        frames.append(df)
        print(f"[{'ok' if len(df) else 'EMPTY'}] {c}: {len(df)}행")
    alldf = pd.concat(frames, ignore_index=True)
    alldf.to_csv(out / "tdf_nav_kofia.csv", index=False, encoding="utf-8-sig")
    print(f"저장 tdf_nav_kofia.csv: {len(alldf)}행, 펀드 {alldf.fund_code.nunique()}개")


if __name__ == "__main__":
    run()
