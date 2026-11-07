"""TDF 35개 펀드(분석 종류 = C/C1)의 합성 총보수·비용(%/년)을 간이투자설명서(KOFIA) PDF에서 자동 추출(2026-09-28).

표의 열 순서: 총보수, 판매보수, 동종유형 총보수, 총보수·비용(합성) → 분석 종류 행에서 '마지막 소수 숫자'(1,000만원 예시 정수 앞)를 취한다.
기간별 보수(미래에셋: 기간마다 표, 신한: 행 안에 기간)도 읽어 (시작, 끝, 보수) 구간으로 저장한다.
과거 투자설명서(DART, prospectus_hist)에도 같은 함수를 적용해 시점별 보수를 얻는다(파일이 있으면).
산출: raw/fund_tdf/tdf_fee_c_class.csv. 실행: PYTHONPATH=src python -m pension_lab.fetch.tdf_fee_extract
"""
from __future__ import annotations
import re
import pandas as pd
from .. import paths

LABEL = {"한국투자": r"\(C\)", "삼성": r"오프라인\(C\)", "KB": r"오프라인\(C\)", "미래에셋": r"오프라인\(C\)", "신한": r"오프라[\s|]*인[\s|]*\(?[\s|]*C1\)"}
PER = r"(최초설정일|\d{4}\.\d{1,2}\.\d{1,2})[\s|]*~[\s|]*(\d{4}\.\d{1,2}\.\d{1,2}|투자신탁[\s|]*해지일)"


def _text(pdf) -> str:
    import fitz
    t = "".join(p.get_text() for p in fitz.open(pdf))
    return re.sub(r"\s*\n\s*", " | ", t)


def _date(s, start):
    if s.startswith("최초"):
        return pd.Timestamp("1900-01-01")
    if "해지" in s:
        return pd.Timestamp("2200-12-31")
    y, m, d = map(int, s.split("."))
    return pd.Timestamp(y, m, d)


def _last_decimal(tokens, both=False):
    """both=True면 (총보수 = 첫 소수, 합성 총보수·비용 = 마지막 소수) — 피투자펀드 보수 등 = 합성 − 총보수(2026-10-09, T7 하위펀드 보수 분리)."""
    dec = []
    for tk in tokens:
        tk = tk.replace("%", "").replace(",", "").strip()
        if re.fullmatch(r"\d+\.\d+", tk):
            dec.append(float(tk))
        elif tk and dec:   # 소수 뒤 첫 비소수 토큰(1,000만원 예시 정수·다음 행 글자)에서 멈춤
            break
    if len(dec) < 3:                                   # 총보수·판매보수·(동종)·총보수비용 → 최소 3개
        return None
    return (dec[0], dec[-1]) if both else dec[-1]


def parse(pdf, manager, both=False) -> list[dict]:
    t = _text(pdf)
    def _rec(fee):
        return {"fee_pct": fee[1], "total_fee_pct": fee[0], "underlying_pct": round(fee[1] - fee[0], 4)} if both else {"fee_pct": fee}
    out = []
    for m in re.finditer(LABEL[manager] + r"\s*\|\s*(없음|-)", t):
        seg = t[m.end():m.end() + 700]
        inline = list(re.finditer(PER, seg[:500]))
        if inline and inline[0].start() < 40:          # 신한형: 행 안에 기간
            for i, pm in enumerate(inline):
                if i and pm.group(1).startswith("최초"):   # 다음 종류(클래스)의 기간 시작 → 중단
                    break
                nxt = inline[i + 1].start() if i + 1 < len(inline) else len(seg)
                toks = re.split(r"[|\s]+", seg[pm.end():nxt])
                fee = _last_decimal(toks, both)
                if fee is not None:
                    out.append({"start": _date(pm.group(1), 1), "end": _date(pm.group(2), 0), **_rec(fee)})
        else:                                            # 표 단위 기간(미래에셋) 또는 단일
            prev = [pm for pm in re.finditer(PER, t[:m.start()])]
            pm = prev[-1] if prev and m.start() - prev[-1].end() < 2500 else None
            fee = _last_decimal(re.split(r"[|\s]+", seg[:300]), both)
            if fee is not None:
                out.append({"start": _date(pm.group(1), 1) if pm else pd.Timestamp("1900-01-01"),
                            "end": _date(pm.group(2), 0) if pm else pd.Timestamp("2200-12-31"), **_rec(fee)})
        if manager != "미래에셋" and out:
            break                                        # 요약표 첫 행만(본문 뒤 표 중복 방지)
    return [dict(o) for o in {(o["start"], o["end"]): o for o in out}.values()]


def run(both: bool = False) -> pd.DataFrame:
    """both=True → raw/fund_tdf/tdf_fee_underlying_c_class_20261009.csv(총보수·합성·합성−총보수, 기존 tdf_fee_c_class.csv는 그대로)."""
    from ..glidepath import _TDF_CODES, CODE2VINTAGE
    rows = []
    for mgr, codes in _TDF_CODES.items():
        for std in codes:
            srcs = [(paths.FUND_TDF / "prospectus" / f"{std}_G.pdf", "KOFIA_간이_현행")]
            h = paths.FUND_TDF / "prospectus_hist" / "prospectus_hist_index.csv"
            if h.exists():
                hi = pd.read_csv(h, dtype=str)
                hi = hi[(hi.standardCd == std) & hi.path.fillna("").str.len().gt(3)]
                srcs += [(p, f"DART_투자설명서_{d}") for p, d in zip(hi.path, hi.rcept_dt)]
            for pdf, src in srcs:
                try:
                    recs = parse(pdf, mgr, both)
                except Exception as e:  # 손상 PDF 등
                    recs, src = [], f"{src}(오류 {type(e).__name__})"
                if not recs:
                    rows.append({"standardCd": std, "manager": mgr, "vintage": CODE2VINTAGE[std], "source": src, "fee_pct": None})
                for r in recs:
                    rows.append({"standardCd": std, "manager": mgr, "vintage": CODE2VINTAGE[std], "source": src, **r})
    df = pd.DataFrame(rows)
    df.to_csv(paths.FUND_TDF / ("tdf_fee_underlying_c_class_20261009.csv" if both else "tdf_fee_c_class.csv"), index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    d = run()
    print(d[d.source.str.startswith("KOFIA")].to_string())
