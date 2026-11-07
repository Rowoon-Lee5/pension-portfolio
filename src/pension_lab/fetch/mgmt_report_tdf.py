"""TDF 5개 운용사 31개 펀드의 분기 '자산운용보고서'(PDF) 수집 + 보유종목/자산구성 추출 (2026-10-09).

목적: 운용보고서의 '주요 자산보유 현황'(상위 10종목·자산총액 5% 초과 종목)과 '자산구성현황'을 분기별로 모아
보유종목 기반 DIY 포트폴리오를 재구성하기 위함. 로그인·CAPTCHA 우회 없음, 요청 간격 ≥2.5초.

저장 위치: $PENSION_DATA_ROOT/raw/fund_tdf/mgmt_reports/
  {manager}\\{code}_{YYYYMMDD 운용기간 말일}.pdf, index_20261009.csv,
  holdings_20261009.csv, assetmix_20261009.csv  (_download_log.jsonl = 원시 다운로드 기록)

실행:
  Windows(다운로드):  set "PYTHONPATH=" && python <repo>\\src\\pension_lab\\fetch\\mgmt_report_tdf.py download
  추출(pymupdf 필요): python mgmt_report_tdf.py extract   (PDF 첫 페이지의 '운용기간'으로 period_end 확정·파일명 변경 후 CSV 작성)
  환경변수 MGMT_REPORT_ROOT 로 저장 루트 변경 가능.

운용사별 URL 규칙(2026-10-09 브라우저 네트워크 캡처로 확인):
- 삼성자산운용: 상품 페이지 m.samsungfund.com/fund/product/view.do?id={표준코드} (클라이언트 렌더링).
  분기보고서 PDF = https://www.samsungfund.com/upload/announce/{YYYYMMDD}_030200{내부코드}_1.pdf
  (YYYYMMDD = 운용기간 말일. 2025~2045: 01/04/07/10월 20일, 2050: 02/05/08/11월 10일; 2021년 이전 일부는 '_1(1).pdf').
  내부코드: 2025=2MC500, 2030=2MC400, 2035=2MC300, 2040=2MC200, 2045=2MC100, 2050=2MCA00. 사이트 라벨(예 '2026-09')은 말일과 어긋나므로 무시.
- 신한자산운용: www.shinhanfund.com/ko/pc/fund/view?fundCd={내부코드} 의 <select id=f-fund-report> 옵션값(YYYYMM)
  → https://www.shinhanfund.com/file/download/fundReport/report/{내부코드}/{YYYYMM}
  내부코드(종류C-re 페이지, 같은 펀드라 보고서 동일): 2025=252726, 2030=252728, 2035=252734, 2040=252736, 2045=252738, 2050=254792.
- 한국투자신탁운용(구 kitmc.com → kim.koreainvestment.com): API https://papi.kitmc.com/api/funds/{표준코드} 의 managedocList[].download_URL
  (https://ftp.kim.co.kr/doc/...(운용기간 시작-말일) 펀드명(모).pdf, '(모)'=종류형 모클래스 기준 보고서).
- KB자산운용: API https://kbam.co.kr/api/products/funds/{내부코드}/reports 의 reports.asset_management_reports[].file_url (kbam.co.kr 상대경로).
  내부코드(H, C-E 클래스): 2025=2X15, 2030=2X25, 2035=2X35, 2040=2X45, 2045=2X55, 2050=2X65, 2055=30B5.
- 미래에셋자산운용: investments.miraeasset.com/magi/fund/view.do?fundGb=2&fundCd={내부코드} 에 '최신 1건'만 노출:
  docDownload('[1-N]{내부코드}_{펀드명}_{YYYYMMDD}.pdf','/files/fund_data_M') → /magi/file/download.do?name=..&path=/files/fund_data_M
  N은 업로드 배치 순번이라 과거분 URL을 추정할 수 없음(시험: 2050의 직전분만 우연히 N-1로 존재, 나머지 실패) → 과거분 수집 불가.
  내부코드: 2025=537360, 2030=537370, 2035=537380, 2040=537390, 2045=537400, 2050=537480.
  (KOFIA 전자공시 '펀드공시검색' 정기공시는 회사 단위 영업보고서만 반환 → 대체 출처 아님)

추출 규칙(표준 서식 '자산운용보고서'):
- period_end: 첫 2쪽 텍스트의 '운용기간 YYYY.MM.DD ~ YYYY.MM.DD' 의 말일 (없으면 '기준일').
- 보유종목: '주요 자산보유 현황' 이후 '▶ {자산종류}' 블록별 표(종목명·비중·수량·평가금액…). pymupdf 단어 좌표로 행을 재구성,
  종목명이 여러 줄로 쪼개진 경우 같은 행 영역의 이름 조각을 합침. weight_pct는 보고서에 인쇄된 '비중'(펀드 자산총액 대비 %),
  weight_basis='printed_pct_of_total_assets'. 평가금액은 인쇄 단위(백만원)를 원으로 환산(amount_krw).
  ※ 상위 10종목 위주 공시이므로 합계는 100%가 아님(전체 보유내역은 보고서에 없음).
- level: 'fund' = 펀드 자체 보유(미래에셋 '펀드의 구성' 모펀드별 투자비중 포함), 'mother' = 자투자신탁(CHILD)의 보고서가
  싣는 모투자신탁 기준(룩스루) 보유종목, 'underlying_fund' = 신한 2025-09~ '피투자집합투자기구 상위 10개 보유종목'
  (피투자펀드 자산 대비 %, 출처 제로인 — 합산 금지).
- 유의: 삼성 '▶ 기타' 표(미수 등)와 신한 2026-06 '미수입금'(30~50%)도 인쇄된 그대로 holding_type='기타'로 담음 → 보고서-수준 합계가
  100%를 넘을 수 있음. 미래에셋은 사이트에 최신 1건뿐, 자산구성현황은 그림(텍스트 없음)이라 assetmix 없음.
- 회전 페이지(신한)는 rotation_matrix로 좌표 변환, 자간 벌린 머리('종 목 명')는 합침, 2단 배치에서 오른쪽 단 → 다음 쪽 왼쪽 단으로
  이어지는 표는 x를 반 페이지 옮겨 이어 읽음.
- 자산구성현황: '합계' 행의 (구성비중 %) 값을 열 머리(주식/채권/어음/집합투자증권/장내·장외파생/부동산/실물·기타 특별자산/단기대출및예금/기타)에 매핑.
"""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(os.environ.get("MGMT_REPORT_ROOT", Path(os.environ.get("PENSION_DATA_ROOT", ".")) / "raw" / "fund_tdf" / "mgmt_reports"))
SINCE = "20220101"          # 이 날짜 이후 말일 보고서만 (2023Q4~ 필수, 2022~ 보너스)
SLEEP = 2.5
MGR_SLEEP = {"samsung": 15.0, "shinhan": 60.0, "kim": 6.0, "kb": 6.0, "mirae": 6.0}
# 2.5초 간격 시험: 삼성 13번째 요청 HTTP 429, 신한 22번째 요청부터 HTTP 403(JSON). 신한은 20초 간격에서도 약 50건 뒤
# '너무 많은 요청 … 1시간뒤 다시 시도'(HTTP 403) → 신한 60초 간격. 429/403 시 5분 쉬고 1회 재시도 후 해당 운용사 중단(재실행 시 이어받기)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}

SAMSUNG = {"K55105BC8937": "2MC500", "K55105BC8648": "2MC400", "K55105BC8515": "2MC300",
           "K55105BC8390": "2MC200", "K55105BC7780": "2MC100", "K55105CK1519": "2MCA00"}
SHINHAN = {"K55210BR6233": "252726", "K55210BR6365": "252728", "K55210BR6498": "252734",
           "K55210BR6621": "252736", "K55210BR6753": "252738", "K55210CO3752": "254792"}
KIM = ["K55101BK8584", "K55101BK7347", "K55101BK7461", "K55101BK6919", "K55101BK7040", "K55101CU1578"]
KB = {"K55223BT0833": "2X15", "K55223BT0999": "2X25", "K55223BT1146": "2X35", "K55223BT1351": "2X45",
      "K55223BT1617": "2X55", "K55223BT1807": "2X65", "K55223D26691": "30B5"}
MIRAE = {"K55301BM7939": "537360", "K55301BM7681": "537370", "K55301BM7582": "537380",
         "K55301BM7400": "537390", "K55301BM7509": "537400", "K55301D51180": "537480"}
# 자투자신탁(모자형) — 보고서의 보유종목은 모투자신탁 기준(룩스루)이므로 level='mother'
CHILD = {"K55210BR6365", "K55210BR6498", "K55210BR6621", "K55210BR6753", "K55210CO3752", "K55101CU1578",
         "K55223BT0999", "K55223BT1146", "K55223BT1351", "K55223BT1617", "K55223BT1807", "K55223D26691", *MIRAE}
MANAGER = {**{c: "samsung" for c in SAMSUNG}, **{c: "shinhan" for c in SHINHAN}, **{c: "kim" for c in KIM},
           **{c: "kb" for c in KB}, **{c: "mirae" for c in MIRAE}}


# ----------------------------------------------------------------------------- 목록(후보 URL) 만들기
def _quarter_dates(mmdd: list[str], start="2022", end="2026") -> list[str]:
    return [f"{y}{md}" for y in range(int(start), int(end) + 1) for md in mmdd]


def list_samsung(S) -> list[dict]:
    out = []
    for code, cd in SAMSUNG.items():
        mmdd = ["0210", "0510", "0810", "1110"] if cd == "2MCA00" else ["0120", "0420", "0720", "1020"]
        for d in _quarter_dates(mmdd):
            if SINCE <= d <= time.strftime("%Y%m%d"):
                out.append(dict(code=code, key=d, url=f"https://www.samsungfund.com/upload/announce/{d}_030200{cd}_1.pdf",
                                alt=f"https://www.samsungfund.com/upload/announce/{d}_030200{cd}_1(1).pdf"))
    return out


def list_shinhan(S) -> list[dict]:
    out = []
    for code, cd in SHINHAN.items():
        h = S.get(f"https://www.shinhanfund.com/ko/pc/fund/view?fundCd={cd}", timeout=60).text
        seg = h[h.find("f-fund-report"):][:20000]
        for ym in re.findall(r'option value="(\d{6})"', seg):
            if ym + "01" >= SINCE[:6] + "01":
                out.append(dict(code=code, key=ym, url=f"https://www.shinhanfund.com/file/download/fundReport/report/{cd}/{ym}"))
        time.sleep(SLEEP)
    return out


def list_kim(S) -> list[dict]:
    out = []
    for code in KIM:
        j = S.get(f"https://papi.kitmc.com/api/funds/{code}", timeout=60).json()
        docs = j.get("managedocList") or (j.get("data") or {}).get("managedocList") or []
        for d in docs:
            m = re.search(r"\((\d{8})-(\d{8})\)", d["download_URL"])
            key = m.group(2) if m else d["make_YMD"]
            if key >= SINCE:
                out.append(dict(code=code, key=key, url=d["download_URL"]))
        time.sleep(SLEEP)
    return out


def list_kb(S) -> list[dict]:
    out = []
    for code, cd in KB.items():
        j = S.get(f"https://kbam.co.kr/api/products/funds/{cd}/reports", timeout=60).json()
        for d in j["reports"].get("asset_management_reports") or []:
            fn = d["file_name"]
            m = re.match(r"(\d{8})_", fn) or re.match(r"(\d{6})_", fn)
            key = m.group(1) if m else fn
            if key[:6] >= SINCE[:6]:
                out.append(dict(code=code, key=key, url="https://kbam.co.kr" + d["file_url"]))
        time.sleep(SLEEP)
    return out


def list_mirae(S) -> list[dict]:
    out = []
    for code, cd in MIRAE.items():
        h = S.get(f"https://investments.miraeasset.com/magi/fund/view.do?fundGb=2&fundCd={cd}", timeout=60).text
        for name, path in re.findall(r"docDownload\('([^']+)','(/files/fund_data_M)'", h):
            m = re.search(r"_(\d{8})\.pdf$", name)
            out.append(dict(code=code, key=m.group(1) if m else name,
                            url="https://investments.miraeasset.com/magi/file/download.do?name=" + quote(name) + "&path=" + quote(path)))
        time.sleep(SLEEP)
    return out


LISTERS = {"samsung": list_samsung, "shinhan": list_shinhan, "kim": list_kim, "kb": list_kb, "mirae": list_mirae}


# ----------------------------------------------------------------------------- 다운로드
def download(managers=None) -> None:
    import requests
    S = requests.Session(); S.headers.update(UA)
    ROOT.mkdir(parents=True, exist_ok=True)
    done = set()
    for lg in ROOT.glob("_download_log*.jsonl"):
        for ln in lg.read_text(encoding="utf-8").splitlines():
            r = json.loads(ln)
            if r.get("ok") or "HTTP 404" in r.get("note", ""):
                done.add((r["code"], r["key"]))
    for mgr in managers or LISTERS:
        log = ROOT / f"_download_log_{mgr}.jsonl"
        try:
            items = LISTERS[mgr](S)
        except Exception as e:                       # 목록 실패는 기록 후 다음 운용사
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps(dict(manager=mgr, code="", key="", url="", ok=False, note=f"list failed: {e!r}"[:300]), ensure_ascii=False) + "\n")
            continue
        print(mgr, "candidates", len(items), flush=True)
        (ROOT / mgr).mkdir(exist_ok=True)
        for it in items:
            if (it["code"], it["key"]) in done:
                continue
            fn = ROOT / mgr / f"_raw_{it['code']}_{it['key']}.pdf"
            rec = dict(manager=mgr, code=it["code"], key=it["key"], url=it["url"], file=str(fn), ok=False, bytes=0, note="")
            gap = MGR_SLEEP.get(mgr, SLEEP)
            for u in [it["url"]] + ([it["alt"]] if it.get("alt") else []):
                try:
                    r = S.get(u, timeout=90)
                    time.sleep(gap)
                    if r.status_code in (429, 403):     # 한 번만 길게 쉬고 재시도, 또 막히면 해당 운용사 중단
                        print(mgr, r.status_code, "-> sleep 300s", r.text[:120], flush=True); time.sleep(300)
                        r = S.get(u, timeout=90); time.sleep(gap)
                except Exception as e:
                    rec["note"] = f"error {e!r}"[:200]; time.sleep(gap); continue
                if r.status_code in (429, 403):
                    rec["note"] = f"HTTP {r.status_code} (blocked/rate limited) - stop manager: {r.text[:100]}"; break
                if r.status_code == 200 and b"%PDF-" in r.content[:1024]:
                    fn.write_bytes(r.content)
                    rec.update(url=u, ok=True, bytes=len(r.content), note="")
                    break
                rec["note"] = f"HTTP {r.status_code} {r.headers.get('content-type','')} {len(r.content)}B {r.text[:80] if len(r.content) < 2000 else ''}"
                if r.content[:16].startswith(b"<DOCUMENT SAFER"):
                    rec["note"] = "DRM 암호화 파일(<DOCUMENT SAFER> 헤더, content-type은 pdf) - 판독 불가"
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(mgr, it["code"], it["key"], rec["ok"], rec["bytes"], rec["note"], flush=True)
            if "stop manager" in rec["note"]:
                break


try:
    import pymupdf                      # 추출 단계에서만 필요(다운로드는 requests만)
except ImportError:
    pymupdf = None
# ----------------------------------------------------------------------------- 추출
NUM = re.compile(r"^-?\d{1,3}(,\d{3})*(\.\d+)?$|^-?\d+(\.\d+)?$")
PCT = re.compile(r"^-?\d+(\.\d+)?%?$")
NAME_HDR = ("종목명", "종목명/업종명", "모펀드명칭")
WEIGHT_HDR = ("비중", "투자비중")
AMT_HDR = ("평가금액", "평가액", "순자산금액", "금액", "평가금액(원)")
STOP_PREFIX = ("※", "●", "◈", "▶", "■", "주1)", "주)", "*")
TYPE_WORDS = ["단기대출 및 예금", "단기대출및예금", "집합투자증권", "주식", "채권", "어음", "파생상품", "장내파생상품",
              "장외파생상품", "부동산", "특별자산", "기타", "유동성", "예금", "외화예금", "콜론"]


def _period(doc) -> tuple[str, str]:
    txt = "".join(doc[i].get_text() for i in range(min(6, doc.page_count)))
    t = re.sub(r"\s+", "", txt)
    m = re.search(r"운용기간.{0,6}?(\d{4})[.년-](\d{1,2})[.월-](\d{1,2})일?[~\-](\d{4})[.년-](\d{1,2})[.월-](\d{1,2})", t)
    if m:
        a = m.groups()
        return f"{a[0]}{int(a[1]):02d}{int(a[2]):02d}", f"{a[3]}{int(a[4]):02d}{int(a[5]):02d}"
    m = re.search(r"기준일[:：]?\(?(\d{4})[.년-](\d{1,2})[.월-](\d{1,2})", t)
    if m:
        return "", f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    return "", ""


def _lines(words, ytol=2.5):
    """단어를 y중심으로 묶어 줄 목록 [(yc, [words...])] (x순)."""
    ws = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    out = []
    for w in ws:
        yc = (w[1] + w[3]) / 2
        if out and abs(out[-1][0] - yc) <= ytol:
            out[-1][1].append(w)
        else:
            out.append([yc, [w]])
    return [(yc, sorted(ws_, key=lambda w: w[0])) for yc, ws_ in out]


def _join(frags):
    s = ""
    for f in frags:
        if not s:
            s = f; continue
        a, b = s[-1], f[0]
        hang = lambda ch: "가" <= ch <= "힣"
        if hang(a) and hang(b) or b in ")]/,." or a in "([-/":
            s += f
        else:
            s += " " + f
    return s.strip()


def _cx(w):
    return (w[0] + w[2]) / 2


def _find_headers(lines):
    """'종목명'(또는 대체 머리)과 '비중' 머리가 같은 줄(±12pt)에 있는 표 머리 후보."""
    heads = []
    for i, (yc, ws) in enumerate(lines):
        texts = [w[4] for w in ws]
        if not any(t in WEIGHT_HDR for t in texts):
            continue
        band = [w for (y2, ws2) in lines if abs(y2 - yc) <= 7 and (y2 <= yc + 1.5 or all(
            len(w[4]) <= 5 and not re.search(r"[A-Za-z0-9]", w[4]) for w in ws2)) for w in ws2]
        bt = [w[4] for w in band]
        name_w = [w for w in band if w[4] in NAME_HDR]
        if not name_w and "모펀드" in bt:
            name_w = [w for w in band if w[4] == "모펀드"]
        if not name_w and "금융기관" in bt and "구분" in bt:           # 미래에셋 예금표: 이름=구분
            name_w = [w for w in band if w[4] == "구분"]
        if not name_w:
            continue
        wt = [w for w in ws if w[4] in WEIGHT_HDR][0]
        heads.append(dict(y=yc, ybot=max(w[3] for w in band), band=band,
                          name=name_w[0], weight=wt, underlying=any("피투자" in t for t in bt)))
    # 같은 표 머리가 두 줄로 잡히는 경우 중복 제거
    uniq = []
    for h in heads:
        if not any(abs(h["y"] - u["y"]) < 14 and abs(_cx(h["weight"]) - _cx(u["weight"])) < 30 for u in uniq):
            uniq.append(h)
    return uniq


def _parse_table(page, words, h, prev_type, page_no, pw, ymax=None, carry=False):
    band = h["band"]
    namew, wtw = h["name"], h["weight"]
    hx = [w for w in band if abs(_cx(w) - _cx(wtw)) < 400]
    # 표의 가로 범위: 머리 단어들 중 이 표에 속하는 것(이름 머리~비고 머리) — 두 단 배치면 반쪽으로 제한
    left_lim, right_lim = 0, pw
    if _cx(namew) > pw / 2 and _cx(wtw) > pw / 2:
        left_lim = pw / 2 - 10
    elif _cx(namew) < pw / 2 and _cx(wtw) < pw / 2:
        right_lim = pw / 2 + 10
    cols = sorted([w for w in band if left_lim <= _cx(w) <= right_lim], key=_cx)
    amt = [w for w in cols if w[4] in AMT_HDR]
    amt = amt[0] if amt else None
    qty = [w for w in cols if w[4].startswith("수량") or w[4] in ("보유수량", "설정원본")]
    qty = qty[0] if qty else None
    kind = [w for w in cols if w[4] == "종류" and _cx(w) > _cx(namew)]
    kind = kind[0] if kind else None
    typ_col = [w for w in cols if w[4] == "구분" and w is not namew and _cx(w) < _cx(namew)]
    typ_col = typ_col[0] if typ_col else None
    und_col = typ_col if h.get("underlying") else None      # 피투자 집합투자기구 표: 구분은 행마다 있음
    if und_col is not None:
        typ_col = None
    # 이름 열 오른쪽 경계 = 이름 머리 다음 열 머리와의 중간
    right_heads = [w for w in cols if _cx(w) > _cx(namew) + 5 and w[4] not in NAME_HDR]
    name_right = max((_cx(namew) + _cx(right_heads[0])) / 2, right_heads[0][0] - 2) if right_heads else _cx(namew) + 80
    if right_heads and right_heads[0][4] in ("종류",):   # 한국투자: 종목명|종류|자산운용사
        name_right = right_heads[0][0] - 2
    name_left = (_cx(typ_col) + _cx(namew)) / 2 if typ_col else ((_cx(und_col) + _cx(namew)) / 2 if und_col is not None else left_lim)
    # 아래쪽 경계: 다음 STOP 줄 / 다음 표 머리 / 페이지 끝
    region = [w for w in words if w[1] > h["ybot"] + 0.5 and left_lim <= _cx(w) <= right_lim]
    lines = _lines(region)
    ystop, stopped = page.rect.height - 30, False
    tleft = min(w[0] for w in cols)
    for yc, ws in lines:
        ws = [w for w in ws if w[0] >= tleft - 40]
        if ws and "단위" in " ".join(w[4] for w in ws) and yc > h["ybot"] + 2:
            ystop, stopped = yc - 1, True
            break
        if not ws or ws[0][0] > tleft + 60:          # 다른 단(오른쪽 글상자)에서 시작하는 줄은 무시
            continue
        t0 = ws[0][4]
        txt = " ".join(w[4] for w in ws)
        if carry and re.search(r"Class|종류\(|수익률|보수|비용|운용전문인력|매매회전율|기준가격", txt):
            ystop, stopped = yc - 1, True
            break
        if t0.startswith(STOP_PREFIX) or "단위" in txt and "(" in txt or ("종목명" in txt and yc > h["ybot"] + 5) \
                or re.match(r"^\d+\.\s", txt) or txt.startswith("주요 자산") or txt.startswith("자산구성"):
            ystop, stopped = yc - 1, True
            if os.environ.get("MR_DEBUG"): print("STOP", page_no, round(yc), txt[:60])
            break
    if ymax is not None and ymax < ystop:
        ystop = ymax
    region = [w for w in region if (w[1] + w[3]) / 2 < ystop]
    wcx = _cx(wtw)
    rows = []
    for w in region:
        if abs(_cx(w) - wcx) <= max(18, (wtw[2] - wtw[0])) and PCT.match(w[4].replace(",", "")):
            v = float(w[4].replace(",", "").rstrip("%"))
            if abs(v) <= 100:
                rows.append(dict(yc=(w[1] + w[3]) / 2, weight=v))
    rows.sort(key=lambda r: r["yc"])
    # 같은 줄 중복 제거
    rr = []
    for r in rows:
        if not rr or abs(rr[-1]["yc"] - r["yc"]) > 3:
            rr.append(r)
    rows = rr
    if not rows:
        return [], stopped, prev_type
    bounds = []
    for i, r in enumerate(rows):
        lo = (rows[i - 1]["yc"] + r["yc"]) / 2 if i else r["yc"] - (12 if carry else 22)
        hi = (rows[i + 1]["yc"] + r["yc"]) / 2 if i + 1 < len(rows) else r["yc"] + 22
        bounds.append((lo, hi))
    for r, (lo, hi) in zip(rows, bounds):
        rw = [w for w in region if lo <= (w[1] + w[3]) / 2 < hi]
        nm = [w for w in rw if name_left <= _cx(w) < name_right]
        r["name"] = _join([w[4] for w in sorted(nm, key=lambda w: (round((w[1] + w[3]) / 2 / 3), w[0]))])
        if amt is not None:
            a = sorted([w for w in rw if abs(_cx(w) - _cx(amt)) <= 35 and NUM.match(w[4])], key=lambda w: abs(_cx(w) - _cx(amt)))
            r["amount"] = float(a[0][4].replace(",", "")) if a else None
        else:
            r["amount"] = None
        if kind is not None:
            kw = [w for w in rw if abs(_cx(w) - _cx(kind)) <= 30 and not NUM.match(w[4])]
            r["kind"] = _join([w[4] for w in kw])
        rest = sorted([w for w in rw if _cx(w) > wcx + 12 and not NUM.match(w[4])], key=lambda w: (round((w[1] + w[3]) / 2 / 3), w[0]))
        r["note"] = _join([w[4] for w in rest])[:80]
        if und_col is not None:
            r["type"] = _join([w[4] for w in rw if abs(_cx(w) - _cx(und_col)) < 30])
            r["underlying"] = True
    # 구분 열(병합 셀) → 행 블록에 배정: 라벨 y와 블록 중심이 가장 가깝게 분할
    if typ_col is not None:
        labs = []
        for yc, ws in _lines([w for w in region if _cx(w) < name_left]):
            labs.append((yc, _join([w[4] for w in ws])))
        labs = [l for l in labs if l[1]]
        # 여러 줄 라벨 합치기
        merged = []
        for l in labs:
            if merged and l[0] - merged[-1][0] < 12 and not any(l[1] == t for t in TYPE_WORDS):
                merged[-1] = (merged[-1][0], merged[-1][1] + " " + l[1])
            else:
                merged.append(l)
        labs = merged
        if labs:
            import itertools
            n, k = len(rows), len(labs)
            best, bestcut = 1e18, None
            for cut in itertools.combinations(range(1, n), k - 1) if k > 1 else [()]:
                idx = [0, *cut, n]
                cost = 0
                for j in range(k):
                    blk = rows[idx[j]:idx[j + 1]]
                    if not blk:
                        cost += 1e9; continue
                    cost += abs((blk[0]["yc"] + blk[-1]["yc"]) / 2 - labs[j][0])
                if cost < best:
                    best, bestcut = cost, idx
            if bestcut and k <= n:
                for j in range(k):
                    for r in rows[bestcut[j]:bestcut[j + 1]]:
                        r["type"] = labs[j][1]
            # 라벨이 첫 행보다 위에 없으면(페이지 넘어감) 이전 유형 유지
    if und_col is not None:
        fw = sorted([w for w in region if _cx(w) < _cx(und_col) - 30], key=lambda w: (round((w[1] + w[3]) / 2 / 3), w[0]))
        und_name = _join([w[4] for w in fw])
        for r in rows:
            r["note"] = ("피투자펀드: " + und_name + " " + r.get("note", "")).strip()[:160]
    if carry and amt is not None:                    # 이어지는 쪽에서는 평가금액이 있는 행만 인정(오탐 방지)
        rows = [r for r in rows if r.get("amount") and len(r.get("name", "")) >= 2]
    for r in rows:
        r.setdefault("type", prev_type)
        r["page"] = page_no
    return rows, stopped, rows[-1]["type"] if rows else prev_type


def _merge_spaced(W):
    """자간을 벌려 '종 목 명'처럼 한 글자씩 쪼개진 한글 단어를 합침(한국투자 2022~2023 서식)."""
    W = sorted(W, key=lambda w: (round((w[1] + w[3]) / 2), w[0]))
    out = []
    for w in W:
        if out:
            p = out[-1]
            same = abs((p[1] + p[3]) / 2 - (w[1] + w[3]) / 2) < 1.5
            if same and len(w[4]) == 1 and "\uac00" <= w[4] <= "\ud7a3" and 0 <= w[0] - p[2] < 3.5 \
                    and all("\uac00" <= c <= "\ud7a3" for c in p[4]) and len(p[4]) <= 3 and (len(p[4]) == 1 or p[-1] == "m"):
                out[-1] = (p[0], min(p[1], w[1]), w[2], max(p[3], w[3]), p[4] + w[4], *p[5:-1], "m") if len(p) > 5 else \
                          (p[0], min(p[1], w[1]), w[2], max(p[3], w[3]), p[4] + w[4])
                continue
        out.append(tuple(w) if len(w) <= 5 else (*w[:8], "s"))
    return [w[:8] if len(w) > 8 else w for w in out]


def _vis_words(page):
    """회전된 페이지(신한 등)도 보이는 방향 좌표로 변환한 단어 목록."""
    W = _merge_spaced(page.get_text("words"))
    if page.rotation == 0:
        return W
    m = page.rotation_matrix
    out = []
    for w in W:
        r = (pymupdf.Rect(w[:4]) * m).normalize()
        out.append((r.x0, r.y0, r.x1, r.y1, *w[4:]))
    return out


def _section_type(lines, y, xlo=0, xhi=1e9):
    """표 머리 위쪽 가장 가까운 '▶ 유형' 또는 단독 유형 제목(같은 단 안에서만)."""
    best = None
    for yc, ws in lines:
        if yc >= y:
            break
        ws = [w for w in ws if xlo <= _cx(w) <= xhi]
        if not ws:
            continue
        txt = " ".join(w[4] for w in ws).strip()
        m = re.match(r"^▶\s*(.+)$", txt)
        if m:
            best = m.group(1).strip()
        elif txt in TYPE_WORDS or txt in ("단기대출 및 예금",):
            best = txt
    return best


def parse_holdings(doc) -> list[dict]:
    out = []
    started = False
    carry = None                      # (머리 dict, 섹션, 마지막 유형) — 페이지 끝까지 이어진 표
    for pi in range(doc.page_count):
        page = doc[pi]
        txt = page.get_text()
        if not started and re.search(r"주요\s*자산\s*보유|상위\s*10개\s*보유종목|보유종목|펀드의\s*구성", txt):
            started = True
        if not started:
            continue
        words = _vis_words(page)
        pw = page.rect.width
        lines = _lines(words)
        heads = _find_headers(lines)
        if carry is not None:
            h0, st0, ty0 = carry
            first_y = min([h["y"] for h in heads if abs(_cx(h["weight"]) - _cx(h0["weight"])) < 150] + [1e9])
            top = [yc for yc, ws in lines if yc > 25][:1]
            sh = lambda w, dx: (w[0] + dx, w[1], w[2] + dx, w[3], *w[4:])
            rows = []
            for dx in ([-pw / 2, 0] if _cx(h0["weight"]) > pw / 2 else [0]):   # 2단 배치: 오른쪽 단 → 다음 쪽 왼쪽 단
                hc = dict(h0, ybot=(top[0] + 8) if top else 40, band=[sh(w, dx) for w in h0["band"]],
                          name=sh(h0["name"], dx), weight=sh(h0["weight"], dx))
                rows, stopped, _ = _parse_table(page, words, hc, ty0, pi + 1, pw, ymax=first_y - 1, carry=True)
                if rows:
                    break
            for r in rows:
                r["section"] = st0; r["continued"] = True
            out += rows
            carry = None
        for h in heads:
            xlo, xhi = (pw / 2 - 10, pw) if _cx(h["name"]) > pw / 2 and _cx(h["weight"]) > pw / 2 else \
                       ((0, pw / 2 + 10) if _cx(h["weight"]) < pw / 2 else (0, pw))
            st = _section_type(lines, h["y"], xlo, xhi) or ("모투자신탁" if h["name"][4].startswith("모펀드") else None)
            rows, stopped, lt = _parse_table(page, words, h, st, pi + 1, pw)
            for r in rows:
                r["section"] = st
            out += rows
            later = [h2 for h2 in heads if h2["y"] > h["y"] and abs(_cx(h2["weight"]) - _cx(h["weight"])) < 150]
            if (rows or h["y"] > 0.8 * page.rect.height) and not stopped and not later:   # 표가 다음 쪽으로 이어짐
                carry = (h, st, lt)
    return out


ASSET_CANON = [("집합투자증권", "집합투자증권"), ("투자증권", "집합투자증권"), ("집합", "집합투자증권"), ("주식", "주식"),
               ("채권", "채권"), ("어음", "어음"), ("장내", "파생상품_장내"), ("장외", "파생상품_장외"),
               ("부동산", "부동산"), ("임대", "부동산"), ("대여차입", "부동산"), ("실물자산", "특별자산_실물"), ("실물", "특별자산_실물"),
               ("단기", "단기대출및예금"), ("예금", "단기대출및예금"), ("손익", "손익"), ("총액", "자산총액"), ("자산총액", "자산총액"),
               ("합계", "자산총액")]


def parse_assetmix(doc) -> list[dict]:
    """'자산구성현황' 통화별 표의 '합계' 행 (구성비중%)을 열 머리에 x좌표로 매핑. 표가 없으면 신한식 '자산별 구성 비중' 목록."""
    for pi in range(doc.page_count):
        page = doc[pi]
        txt = page.get_text()
        if not re.search(r"자산\s*구성|통화별", txt):
            continue
        words = _vis_words(page)
        lines = _lines(words)
        for li, (yc, ws) in enumerate(lines):
            if not ws or ws[0][4] != "합계":
                continue
            x_l = ws[0][0]
            # 머리: 위쪽 160pt 안의 '통화별' 또는 '구분' 줄부터 합계 직전까지
            hdr_top = [y for y, w2 in lines if yc - 200 < y < yc and any(w[4] in ("통화별", "통화별구분") for w in w2) and abs(w2[0][0] - x_l) < 40]
            if not hdr_top:
                continue
            y0 = max(hdr_top) - 12
            hw = [w for y, w2 in lines if y0 <= y < yc for w in w2 if w[0] > x_l + 15]
            labs = []
            gita = sorted([w for w in hw if w[4] == "기타" and (w[1] + w[3]) / 2 < y0 + 60], key=_cx)
            for w in hw:
                for key, canon in ASSET_CANON:
                    if w[4] == key or (len(key) > 2 and w[4].startswith(key)):
                        labs.append((_cx(w), canon)); break
            for i, w in enumerate(gita):
                labs.append((_cx(w), "특별자산_기타" if (len(gita) > 1 and i == 0) else "기타"))
            # 머리가 '총액'만 있고 '자산'이 따로 있으면 그대로 자산총액
            band = [w for y, w2 in lines if yc - 7 <= y <= yc + 16 for w in w2 if w[0] > x_l + 15]
            vals = [w for w in band if re.match(r"^\(-?[\d,]*\.?\d+\)$", w[4])]
            if not vals or not labs:
                continue
            out = {}
            for w in vals:
                c = min(labs, key=lambda l: abs(l[0] - _cx(w)))
                if abs(c[0] - _cx(w)) > 45:
                    continue
                out[c[1]] = out.get(c[1], 0.0) + float(w[4].strip("()").replace(",", ""))
            if out:
                return [dict(asset_type=k, weight_pct=round(v, 4), page=pi + 1, basis="currency_table_total_row") for k, v in out.items()]
    # KB 2026~ 전치형: 행=자산종류, 열=통화, '합계(비중)' 열의 괄호값
    for pi in range(doc.page_count):
        page = doc[pi]
        if "합계(비중)" not in page.get_text().replace(" ", ""):
            continue
        words = _vis_words(page)
        hw = [w for w in words if w[4].startswith("합계(비중)")]
        if not hw:
            continue
        hx, hy = _cx(hw[0]), hw[0][3]
        canon = {"주식": "주식", "채권": "채권", "어음": "어음", "집합투자증권": "집합투자증권", "장내": "파생상품_장내",
                 "장외": "파생상품_장외", "부동산": "부동산", "실물자산": "특별자산_실물", "예금": "단기대출및예금"}
        out, seen_gita = {}, 0
        for yc, ws in _lines([w for w in words if w[1] > hy and w[1] < hy + 260]):
            lab = [w for w in ws if w[2] < hx - 60]
            val = [w for w in ws if abs(_cx(w) - hx) < 45 and re.search(r"\((-?[\d.]+)\)", w[4])]
            names = [w[4] for w in lab]
            key = None
            for n in names[::-1]:
                if n in canon:
                    key = canon[n]; break
                if n == "기타":
                    seen_gita += 1
                    key = "특별자산_기타" if seen_gita == 1 and "특별자산_실물" in out or (seen_gita == 1 and any(x == "실물자산" for x in names)) else "기타"
                    break
            if any(n.startswith("자산총액") for n in names):
                break
            if key and val:
                out[key] = float(re.search(r"\((-?[\d.]+)\)", val[0][4]).group(1))
        if out:
            return [dict(asset_type=k, weight_pct=v, page=pi + 1, basis="asset_rows_total_column") for k, v in out.items()]
    # 신한식(투자자용) '내 펀드가 보유하고 있는 자산현황' 목록
    for pi in range(doc.page_count):
        t = doc[pi].get_text()
        i = t.find("자산현황")
        if "자산별 구성 비중" not in t or i < 0:
            continue
        seg = [s.strip() for s in t[i:].split("\n")[1:40] if s.strip()]
        labels, pcts = [], []
        for s in seg:
            if re.match(r"^-?\d+(\.\d+)?\s*%$", s):
                pcts.append(float(s.replace("%", "").strip()))
            elif not pcts and len(s) <= 12 and not re.search(r"\d", s):
                labels.append(s)
            elif pcts:
                break
        if labels and len(labels) == len(pcts):
            return [dict(asset_type=l.replace(" ", ""), weight_pct=p, page=pi + 1, basis="asset_class_list") for l, p in zip(labels, pcts)]
    for pi in range(min(6, doc.page_count)):               # 신한 신서식: 차트(그림)만 있고 문장에 집합투자증권 편입비중만 있음
        t = re.sub(r"\s+", "", doc[pi].get_text())
        m = re.search(r"집합투자증권편입비중은(-?[\d.]+)%", t)
        if m:
            return [dict(asset_type="집합투자증권", weight_pct=float(m.group(1)), page=pi + 1, basis="text_sentence_only")]
    return []


def _level_info(doc, fund_name_hint=""):
    t = re.sub(r"\s+", "", "".join(doc[i].get_text() for i in range(min(6, doc.page_count))))
    is_child = "자투자신탁" in t[:3000] or "자투자신탁" in fund_name_hint
    lookthrough = bool(re.search(r"모(펀드|투자신탁|집합투자기구)의?자산구성|모자형구조|모펀드의자산구성|모펀드투자비중을감안|모펀드각각의투자비중", t)) \
        or "자펀드인경우자산구성현황은모펀드투자비중을감안" in t
    return is_child, lookthrough


def extract() -> None:
    import csv, hashlib
    recs = {}
    for lg in sorted(ROOT.glob("_download_log*.jsonl")):
        for ln in lg.read_text(encoding="utf-8").splitlines():
            r = json.loads(ln)
            if r.get("code"):
                k = (r["code"], r["key"])
                if r.get("ok") or k not in recs:
                    recs[k] = r
    idx, hold, mix = [], [], []
    for (code, key), r in sorted(recs.items()):
        mgr = r["manager"]
        row = dict(code=code, manager=mgr, period_start="", period_end="", url=r["url"], file="", bytes=r.get("bytes", 0),
                   ok=bool(r.get("ok")), note=r.get("note", ""), url_key=key)
        if not r.get("ok"):
            if row["note"].startswith("HTTP 200 application/pdf"):     # 한국투자 2022-03분: DRM(Document Safer) 암호화본
                row["note"] = "DRM 암호화 파일(<DOCUMENT SAFER> 헤더, content-type은 pdf) - 판독 불가"
            idx.append(row); continue
        raw = ROOT / mgr / f"_raw_{code}_{key}.pdf"
        final_guess = sorted((ROOT / mgr).glob(f"{code}_*.pdf"))
        src = raw if raw.exists() else None
        if src is None:                              # 이미 이름이 바뀐 경우: 다운로드 기록의 key로 찾기
            m = [p for p in final_guess if p.with_suffix(".key").exists() and p.with_suffix(".key").read_text() == key]
            src = m[0] if m else None
        if src is None:
            row.update(ok=False, note="file missing"); idx.append(row); continue
        try:
            doc = pymupdf.open(src)
        except Exception as e:
            row.update(ok=False, note=f"pdf open error {e!r}"[:120]); idx.append(row); continue
        if sum(len(doc[i].get_text().strip()) for i in range(doc.page_count)) < 200:
            row["note"] = "no text layer (image-only PDF?)"
        ps, pe = _period(doc)
        row.update(period_start=ps, period_end=pe)
        if pe:
            dst = ROOT / mgr / f"{code}_{pe}.pdf"
            if src != dst:
                if dst.exists():
                    if hashlib.md5(dst.read_bytes()).hexdigest() != hashlib.md5(src.read_bytes()).hexdigest():
                        dst = ROOT / mgr / f"{code}_{pe}_dup_{key}.pdf"
                        row["note"] += " duplicate period_end with different content"
                if not dst.exists():
                    doc.close(); os.replace(src, dst); doc = pymupdf.open(dst)
                    dst.with_suffix(".key").write_text(key)
            src = dst
        row["file"] = str(src)
        is_child, lookthrough = _level_info(doc)
        H = parse_holdings(doc)
        has_mother_tbl = any((h.get("section") or "") == "모투자신탁" for h in H)
        for h in H:
            sec = h.get("section") or ""
            if sec == "모투자신탁":
                level, basis = "fund", "printed_pct_mother_fund_weight_in_child_fund"
            elif h.get("underlying"):
                level, basis = "underlying_fund", "printed_pct_of_underlying_fund_assets(zeroin)"
            else:
                level = "mother" if (has_mother_tbl or code in CHILD) else "fund"
                basis = "printed_pct_of_total_assets"
            name = h["name"]
            if "/" in name and mgr == "mirae" and sec == "주식":
                name = name.split("/")[0].strip()
            htype = h.get("type") or sec or h.get("kind") or ""
            hold.append(dict(code=code, manager=mgr, period_end=pe, level=level, holding_name=name, holding_type=htype,
                             holding_kind=h.get("kind", ""), amount_krw=(round(h["amount"] * 1e6) if h.get("amount") is not None else ""),
                             weight_pct=h["weight"], weight_basis=basis, page=h["page"], note=h.get("note", ""),
                             continued_from_prev_page=bool(h.get("continued"))))
        for a in parse_assetmix(doc):
            mix.append(dict(code=code, manager=mgr, period_end=pe, asset_type=a["asset_type"], weight_pct=a["weight_pct"],
                            page=a["page"], basis=a["basis"]))
        row["n_holdings"] = len(H)
        idx.append(row)
        doc.close()
    def w(name, rows, cols):
        with open(ROOT / name, "w", newline="", encoding="utf-8-sig") as f:
            wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); wr.writeheader(); wr.writerows(rows)
    w("index_20261009.csv", idx, ["code", "manager", "period_start", "period_end", "url", "file", "bytes", "ok", "note", "url_key", "n_holdings"])
    w("holdings_20261009.csv", hold, ["code", "manager", "period_end", "level", "holding_name", "holding_type", "holding_kind",
                                      "amount_krw", "weight_pct", "weight_basis", "page", "note", "continued_from_prev_page"])
    w("assetmix_20261009.csv", mix, ["code", "manager", "period_end", "asset_type", "weight_pct", "page", "basis"])
    print("index", len(idx), "holdings", len(hold), "assetmix", len(mix))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "download"
    if cmd == "download":
        download(sys.argv[2:] or None)
    elif cmd == "extract":
        extract()


# ── 환헤지 비율 추출(2026-10-09 추가) ────────────────────────────────────────
def extract_hedge() -> "pd.DataFrame":
    """보고서 '환헤지에 관한 사항'의 '기준일 현재 환헤지 비율'(총 외화자산 평가액 대비 헤지 규모, %) 추출 → mgmt_reports/hedge_ratio_20261009.csv.
    규칙: '환헤지 비율' 머리글 줄부터 6줄 안에서, 선도계약 줄('CURRENCY'·'선도'·'매도'·'매수' 포함)은 건너뛰고, 목표범위('60~110', '80-110', '70%이상')를 뺀
    첫 소수(0~150)를 씀. 신한은 비율을 숫자로 싣지 않아(문장으로 '유연하게 조절') 빈칸. 10 미만 숫자는 각주·쪽번호 잔재로 버림. 100 초과·40 미만은 flag=check(원문 확인 필요). 미래에셋은 최신 1건뿐(분석 제외)."""
    import re, subprocess
    import pandas as pd
    from .. import paths
    base = paths.FUND_TDF / "mgmt_reports"; rows = []
    for f in sorted(base.glob("*/*.pdf")):
        if f.parent.name.startswith("_"):
            continue
        try:
            t = subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True, timeout=60).stdout
        except Exception:
            t = ""
        L = t.splitlines(); val = None; ctx = ""
        for i, l in enumerate(L):
            if re.search(r"환헤지\s*비율", l) and not re.search(r"비율은|비율로|비율 및", l):
                for k in range(i, min(i + 6, len(L))):
                    s = L[k]
                    if re.search(r"CURRENCY|선도|매도|매수|USD\s|주\d?\)", s):
                        continue
                    s = re.sub(r"\d+\s*[~\-]\s*\d+|\d+%\s*이상|\d+%\s*내외", " ", s)
                    nums = [float(x) for x in re.findall(r"(?<![\d.])(\d{1,3}(?:\.\d+)?)(?![\d.%])", s) if 0 <= float(x) <= 150]
                    nums = [x for x in nums if x >= 10]          # 10 미만은 각주 번호·쪽 번호 등 파싱 잔재(실제 비율은 50~105 범위)
                    if nums:
                        val = nums[0]; ctx = L[k].strip()[:120]; break
                if val is not None:
                    break
        code, pe = f.stem.split("_")[:2]
        rows.append({"manager": f.parent.name, "code": code, "period_end": pe, "hedge_pct": val,
                     "flag": "check" if val is not None and (val > 100 or val < 40) else "", "ctx": ctx})
    d = pd.DataFrame(rows); d.to_csv(base / "hedge_ratio_20261009.csv", index=False, encoding="utf-8-sig")
    return d


def _krw_sec(seg: list, mgr: str):
    """통화별 표에서 원화 증권(주식·채권·어음·집합투자증권 열) ÷ 전체 자산총액 × 100 (12차 감사 🔴: 원화 예금·파생·기타는 뺌).
    KB 신양식(세로 표): '어음' 줄부터 '장내' 줄 전까지의 금액 중 'KRW(비중)' 머리글 열에 더 가까운 것 ÷ '자산총액' 둘째 금액('-'면 0).
    삼성: 괄호 비중 줄 — '합계' 비중 줄의 괄호 위치로 열을 정하고(총액 = 맨 오른쪽, 집합투자증권 = 총액 뺀 최대), KRW 비중 줄 괄호 중 첫 열 시작 ~ 집합투자증권 열(+6자) 안의 것을 더함(맨 왼쪽 '(1.0)'은 기준환율이라 제외).
    한국투자·KB 구양식: 같은 방식을 금액 줄에 적용(합계 금액 줄의 총액 위치 오른쪽 글자는 옆 표라 버림)."""
    import re
    amt = lambda l: [(m.start(), m.end(), float(m.group().replace(",", ""))) for m in re.finditer(r"(?<![\d.(,])-?\d[\d,]*(?:\.\d+)?(?![\d),])", l)
                     if not re.fullmatch(r"-?\d", m.group())]
    par = lambda l: [(m.start(), m.end(), float(m.group(1))) for m in re.finditer(r"\((-?\d+(?:\.\d+)?)\)", l)]
    hdr = next((l for l in seg if "KRW(비중)" in l and "합계(비중)" in l), None)
    if mgr == "kb" and hdr is not None:
        kp, hp = hdr.index("KRW(비중)") + 4, hdr.index("합계(비중)") + 4
        tl = next((l for l in seg if "자산총액" in l), None)
        i1 = next((i for i, l in enumerate(seg) if re.search(r"어음", l)), None); i2 = next((i for i, l in enumerate(seg) if re.search(r"장내", l)), None)
        if tl is None or i1 is None or i2 is None or len(amt(tl)) != 2: return None
        v = sum(x for l in seg[i1:i2] for a, b, x in amt(l) if abs((a + b) / 2 - kp) < abs((a + b) / 2 - hp))
        return 100 * v / amt(tl)[1][2]
    j = next((j for j, l in enumerate(seg) if re.match(r"^\s*(KRW|원)\b", l)), None)
    h = next((k for k, l in enumerate(seg) if re.match(r"^\s*합계", l)), None)
    if j is None or h is None or h <= j: return None
    fn = par if mgr == "samsung" else amt
    cand = [seg[k] for k in range(max(h - 1, 0), min(h + 2, len(seg)))]
    hl = max(cand, key=lambda l: len(fn(l))); ht = fn(hl)
    if len(ht) < 3: return None
    tot = ht[-1]; right = tot[1] + 2; ht = [x for x in ht if x[1] <= right]
    col = max(ht[:-1], key=lambda x: x[2]); cc = (col[0] + col[1]) / 2; left = ht[0][0] - 3
    kl = max([seg[k] for k in range(j, min(j + 4, h)) if seg[k] is not hl] or [""], key=lambda l: len([x for x in fn(l) if x[1] <= right]))
    v = sum(x for a, b, x in fn(kl) if b <= right and a >= left and (a + b) / 2 <= cc + 6)
    return v if mgr == "samsung" else (100 * v / tot[2] if tot[2] > 0 else None)


def extract_krw() -> "pd.DataFrame":
    """보고서 자산구성현황 '통화별 구분' 표의 원화(KRW) 비중(자산총액 대비 %, 모펀드 룩스루) 추출 → mgmt_reports/krw_share_20261009.csv.
    용도: 상위 보유종목에 안 실린 비중(평균 27%) 가운데 원화 자산(국내주식·국내채권·원화 현금·원화 상장 ETF)이 얼마인지 → T7 hold_diy rem='krw'.
    규칙(금액 기준): KRW 합계 금액 ÷ 전체 합계 금액. KB 신양식 = '자산총액' 줄(KRW, 합계 두 숫자); 그 밖 = 'KRW'·'원' 줄부터 3줄 안 가장 큰 금액 ÷ '합계' 줄 ±1줄 안 가장 큰 금액.
    검산: 삼성·한국투자는 KRW 줄 괄호 비중(합계 열, 전체 대비)도 저장(krw_pct_paren) — KB 구양식 괄호는 KRW 소계 대비라 안 씀. 차이 1%p 넘으면 flag.
    신한·미래에셋은 표 양식이 달라 비어도 분석(3개사)에는 영향 없음."""
    import re, subprocess
    import pandas as pd
    from .. import paths
    num = lambda l: [float(x.replace(",", "")) for x in re.findall(r"(?<![\d.(])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d)])|(?<![\d.(,])-?\d+\.\d+(?![\d)])|(?<![\d.(,])\d{2,}(?![\d.,)])", l)]
    base = paths.FUND_TDF / "mgmt_reports"; rows = []
    for f in sorted(base.glob("*/*.pdf")):
        if f.parent.name.startswith("_"):
            continue
        try:
            t = subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True, timeout=60).stdout
        except Exception:
            t = ""
        L = t.splitlines(); val = paren = None; ctx = ""; mgr = f.parent.name
        i0 = next((i for i, l in enumerate(L) if "통화별" in l), None)
        if i0 is not None:
            seg = L[i0:i0 + 80]
            tot_line = next((l for l in seg if "자산총액" in l), None) if mgr == "kb" else None
            if tot_line is not None and len(num(tot_line)) == 2:
                a = num(tot_line); val = 100 * a[0] / a[1] if a[1] > 0 else None; ctx = tot_line.strip()[:120]
            else:
                j = next((j for j, l in enumerate(seg) if re.match(r"^\s*(KRW|원)\b", l)), None)
                h = next((k for k, l in enumerate(seg) if re.match(r"^\s*합계", l)), None)
                if j is not None and h is not None and h > j:
                    ka = [x for l in seg[j:min(j + 3, h)] for x in num(l)]
                    ta = [x for l in seg[max(h - 1, 0):h + 2] for x in num(l)]
                    if ka and ta and max(ta) > 0:
                        val = 100 * max(ka) / max(ta); ctx = f"KRW {max(ka)} / 합계 {max(ta)}"
                    if mgr != "kb":
                        best = []
                        for k in range(j, min(j + 4, h)):
                            p_ = [float(x) for x in re.findall(r"\((-?\d+(?:\.\d+)?)\)", seg[k])]
                            if len(p_) > len(best): best = p_
                        paren = best[-1] if best else None
        sec = _krw_sec(seg, mgr) if i0 is not None else None                                # 12차 감사 🔴: 원화 '증권'(주식·채권·어음·집합투자증권)만 — 예금·파생·기타 제외
        if val is not None and not (0 <= val <= 100):
            val = None
        amt = val
        if mgr != "kb":                                   # 삼성·한국투자: 괄호 비중(전체 대비)을 주값으로 — 삼성 표는 금액 열이 줄을 넘나들어 금액 방식이 틀리는 경우가 있음(검산 열 krw_pct_amount)
            val = paren if paren is not None and 0 <= paren <= 100 else None
        code, pe = f.stem.split("_")[:2]
        rows.append({"manager": mgr, "code": code, "period_end": pe, "krw_pct": val, "krw_sec_pct": sec, "krw_pct_amount": amt, "krw_pct_paren": paren,
                     "flag": "check" if (amt is not None and paren is not None and abs(amt - paren) > 1) else "", "ctx": ctx})
    d = pd.DataFrame(rows); d.to_csv(base / "krw_share_20261009.csv", index=False, encoding="utf-8-sig")
    return d


def extract_hedge_shinhan() -> "pd.DataFrame":
    """신한 보고서는 환헤지 비율을 숫자로 싣지 않음 → '환헤지를 위한 파생상품' 표의 선물환 계약으로 추정(2026-10-09).
    순매도 = Σ(USD 매도 취득가격) − Σ(USD 매수 취득가격) [백만원, 계약금액 다음 열]; 외화자산 = '자산총액' 당기말 × 실린 보유종목 중 외화 자산 비중
    (holding_class_map에서 해외 자산군이면서 원화 상장 ETF가 아닌 것 ÷ 실린 전체 — 안 실린 비중도 같은 구성이라고 가정 ⚠).
    hedge_pct = 순매도 ÷ 외화자산 × 100. 40 미만·110 초과는 flag=check. → mgmt_reports/hedge_ratio_shinhan_est_20261009.csv"""
    import re, subprocess
    import pandas as pd
    from .. import paths
    base = paths.FUND_TDF / "mgmt_reports"
    h = pd.read_csv(base / "holdings_20261009.csv", dtype={"period_end": str}); m = pd.read_csv(base / "holding_class_map_20261009.csv")
    h = h[(h.manager == "shinhan") & h.level.isin(["fund", "mother"])].merge(m[["holding_name", "asset_class"]], on="holding_name", how="left")
    h = h.groupby(["code", "period_end", "level", "holding_name", "asset_class"], dropna=False)["weight_pct"].max().reset_index()
    cov = h.groupby(["code", "period_end", "level"])["weight_pct"].sum().reset_index()
    best = cov.sort_values("weight_pct").groupby(["code", "period_end"]).tail(1)
    h = h.merge(best[["code", "period_end", "level"]])
    nm = h.holding_name.astype(str)
    fx = h.asset_class.isin(["US_EQ", "DM_EXUS_EQ", "EM_EQ", "GLOBAL_EQ", "GLOBAL_BD", "ALT", "MIXED"]) & ~nm.str.match(r"^(한국투자\s*)?(ACE|RISE|KODEX|TIGER|KBSTAR|SOL|HANARO|ARIRANG|PLUS|KOSEF|KIWOOM)")
    ff = (h.weight_pct * fx).groupby([h.code, h.period_end]).sum() / h.groupby(["code", "period_end"]).weight_pct.sum()
    pat = re.compile(r"해외파생.*?USD\s+(매도|매수)\s+\d{4}\.\d{2}\.\d{2}\s+[\d,]+\s+([\d,]+)")
    rows = []
    for f in sorted((base / "shinhan").glob("*.pdf")):
        t = subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True, timeout=60).stdout
        sell = buy = 0.0; n = 0
        for l in t.splitlines():
            mm = pat.search(l)
            if mm:
                v = float(mm.group(2).replace(",", "")); n += 1
                if mm.group(1) == "매도": sell += v
                else: buy += v
        ta = next((l for l in t.splitlines() if re.match(r"^\s*자산총액\s", l)), None)
        tot = float(re.findall(r"[\d,]+", ta)[-1].replace(",", "")) if ta else None
        code, pe = f.stem.split("_")[:2]
        fr = ff.get((code, pe), None)
        hp = 100 * (sell - buy) / (tot * fr) if (tot and fr and n) else None
        rows.append({"manager": "shinhan", "code": code, "period_end": pe, "hedge_pct": hp, "net_sell_mn": sell - buy, "n_contracts": n,
                     "total_assets_mn": tot, "foreign_frac_covered": fr, "flag": "check" if hp is not None and not (40 <= hp <= 110) else ""})
    d = pd.DataFrame(rows); d.to_csv(base / "hedge_ratio_shinhan_est_20261009.csv", index=False, encoding="utf-8-sig")
    return d


def extract_hedge_pnl(out_csv: str) -> "pd.DataFrame":
    """환헤지 표의 '환헤지 비용'(기간)·'환헤지로 인한 손익'(기준일 현재) 열 추출(2026-10-10, 주제2 P6).
    KB·한국투자 표 머리글(원 PDF 확인): 투자설명서상의 목표 환헤지 비율 | 기준일 현재 환헤지 비율 | (기간) 환헤지 비용 | 기준일 현재 환헤지로 인한 손익, (단위: %, 원).
    값은 보고서 표기 그대로(원, 부호 그대로, '-'는 빈 값으로 두고 raw 열에 원문 보존). 표가 없거나 열을 못 찾으면 note에 사유."""
    import re, subprocess
    import pandas as pd
    from .. import paths
    base = paths.FUND_TDF / "mgmt_reports"; rows = []
    NUM = re.compile(r"(?<![\w.,%-])-?\d[\d,]*(?:\.\d+)?(?![\w%.,])|(?<!\S)-(?!\S)")
    for f in sorted(base.glob("*/*.pdf")):
        if f.parent.name.startswith("_"): continue
        L = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(f), "-"], capture_output=True, timeout=60).stdout.decode("utf-8", "replace").splitlines()
        code, pe = f.stem.split("_")[:2]; r = dict(manager=f.parent.name, code=code, period_end=pe, file=f"{f.parent.name}/{f.name}")
        j = next((j for j, l in enumerate(L) if "환헤지로 인한 손익" in l), None)      # 손익 칸 → 그 바로 위 4줄 안의 '환헤지 비용' 머리글
        hd = lambda l: re.search(r"환헤지\s*비용", l) and not re.search(r"비용은|비용을|비용이|비용 등|비용 산출|비용을 별도", l)
        i = next((k for k in range(j, max(-1, j - 5), -1) if hd(L[k])), None) if j is not None else None
        if i is None:                     # 삼성·미래에셋·신한 양식엔 손익 칸이 없음(삼성·미래: '비용 별도 산출 불가' 각주)
            rows.append({**r, "note": "환헤지로 인한 손익 칸 없음" if j is None else "손익 칸 위 환헤지 비용 머리글 없음"}); continue
        hdr = " ".join(L[max(0, i - 3):i + 2])
        per = re.search(r"\((\d{4}\.\d{2}\.\d{2})\s*~\s*(\d{4}\.\d{2}\.\d{2})\)", hdr); unit = re.search(r"\(단위\s*:\s*([^)]+)\)", hdr)
        k = next((k for k in range(i + 1, min(i + 6, len(L))) if NUM.search(re.sub(r"\d+\s*%|\d+\s*-\s*\d+", " ", L[k]))), None)
        nums = NUM.findall(re.sub(r"\d+\s*%|\d+\s*-\s*\d+", " ", L[k])) if k is not None else []
        pl = next(((m, n) for n in range(j + 1, min(j + 5, len(L))) for m in [L[n].strip()] if re.fullmatch(r"-?[\d,]+|-", m)), (None, None)) if j is not None else (None, None)
        f2 = lambda s: None if s in (None, "-") else float(s.replace(",", ""))
        rows.append({**r, "cost_period_start": per.group(1) if per else None, "cost_period_end": per.group(2) if per else None, "unit": unit.group(1).strip() if unit else None,
                     "hedge_pct_tbl": f2(nums[0]) if len(nums) > 0 else None, "hedge_cost_krw": f2(nums[1]) if len(nums) > 1 else None, "hedge_cost_raw": nums[1] if len(nums) > 1 else None,
                     "hedge_pnl_krw": f2(pl[0]), "hedge_pnl_raw": pl[0], "line_hdr": i + 1, "line_val": (k + 1) if k is not None else None, "line_pnl": (pl[1] + 1) if pl[1] is not None else None,
                     "note": ""})
    d = pd.DataFrame(rows)
    med = d.groupby("code").hedge_pnl_krw.transform(lambda s: s.abs().median())   # 같은 펀드 분기 중앙값의 1/1000 미만 = 단위 표기 의심(표시만, 값은 그대로)
    d["flag"] = (d.hedge_pnl_krw.abs() < med / 1000).map({True: "check_scale", False: ""})
    d.to_csv(out_csv, index=False, encoding="utf-8-sig")
    return d
