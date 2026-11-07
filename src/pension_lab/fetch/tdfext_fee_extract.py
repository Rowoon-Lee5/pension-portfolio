"""TDF 확장 92개 펀드코드(금융투자협회 표준코드)별 '합성 총보수·비용'(%/년) 추출 (2026-10-09).

[대상]  raw/fund_tdf/prospectus/prospectus_index_tdfext_G_20261009.csv 에 있는 92개 표준코드.
[입력]  KOFIA 공시 PDF: {code}_T.pdf(투자설명서 본문), {code}_G.pdf(간이투자설명서).
        펀드명: tdfext_fund_names_kofia_20261008.csv, 운용사: glidepath_disclosed_web_kr_others.csv.
[산출]  raw/fund_tdf/tdfext_fee_kofia_20261009.csv
        (standardCd, manager, vintage, class_label, start, end, fee_pct, fee_ex_sales_pct, source, page, evidence, confidence, note)

[방법]
1) 텍스트화: pdftotext -layout (페이지 구분 \\f → page 번호). 표의 열 정렬이 보존되어 행 단위 숫자 토큰을 읽을 수 있다.
2) 종류(클래스) 식별: 표준코드의 3~7번째 문자(예: K55102ED7128 → 'ED712')가 '펀드코드(금융투자협회)'로
   투자설명서 '1. 집합투자기구의 명칭' 표에 나온다. 그 행이
     - 종류 이름(예: S-P2, 수수료선취-오프라인(A))이면 → 해당 클래스,
     - 펀드 명칭(…투자신탁…) 자체이면 → 모(운용)펀드 코드(class_label='운용(종류형 운용펀드)')
       ※ 종류형 펀드의 운용(모) 코드는 투자설명서 13.보수 표에 행이 없다 → fee_pct 비움 + note.
     - 종류형이 아닌 단일 펀드(ETF·한화 신종개인연금)면 → class_label='단일(종류없음)'.
   식별 결과는 아래 CLASS_EXPECT 와 대조(assert)한다(펀드명에 붙은 Class 표기와도 일치 확인).
3) 보수 추출: 투자설명서 제2부 '13. 보수 및 수수료 → 나. 집합투자기구에 부과되는 보수 및 비용' 표.
   운용사·문서마다 열 순서와 빈 칸이 달라 '마지막 소수' 규칙을 쓸 수 없으므로, 문서별로 수동 확인한
   위치 지정자(LOC)를 명시한다:
     kind='row'  : 기간 머리글(anchor 정규식) 뒤의 n번째 '숫자행'(소수 토큰 mn개 이상)에서 col번째 토큰
                   (토큰 = 소수 또는 '-'; 빈 칸은 토큰이 아님 → 문서별 col 을 따로 지정)
     kind='vert' : 세로형 단일 표 — anchor('합성 총 보수…') 줄 또는 다음 2줄의 첫 소수.
   PDF 원문을 눈으로 읽어 적은 기대값(expect)은 이 코드에 넣지 않고 저장소 밖 CSV(EXPECT_CSV, 만드는 법은
   DATA_SOURCES.md 3-3절)에서 읽는다. 파일이 있으면 추출값과 다를 때 즉시 실패해 수동 판독과 자동 재추출이 서로 검증되고,
   없으면 대조 없이 추출만 한다(경고 출력). 기간(start/end)은 머리글 원문을 보고 명시했다.
   열린 구간은 1900-01-01 / 2200-12-31 (기존 tdf_fee_c_class.csv 관례).
4) 교차검증: 현행(2026-10-09 포함) 구간 값이 간이투자설명서(G) 투자비용 영역에 같은 문자열로 나오면 note 에 '간이일치'.
5) [fee_ex_sales_pct] 모든 행에 '합성 총보수·비용 − 판매회사보수'(판매보수 제외 공통비용)를 추가.
   클래스 행은 그 행의 판매보수를 뺀다(키움 ETF는 지정참가회사보수를 판매보수로 간주).
   운용(모) 코드는 기준가가 판매보수를 부담하지 않으므로 fee_pct 는 비우고, 같은 펀드·같은 기간 표의
   모든 공시 클래스에서 (합성 − 판매)를 구해 0.01%p 이내 일치 시 그 값('class-common, n classes agree', high),
   불일치 시 중앙값(note 에 n·min·max, medium). 열 판별 규칙은 base_common() 위 주석(LAYOUT) 참조.
   [fee_underlying_pct] (주 지표, 2026-10-09 감사 반영) = 합성 총보수·비용 − 총보수(운용+판매+수탁+사무).
   NAV 쌍 비교(운용 vs 클래스 18쌍; 예: 흥국2050 EQ1707 vs C-f 괴리 ≈ C-f 총보수, 신영2040 운용 vs A/C/A-E 괴리
   = 각 클래스 총보수)로 운용(종류형 운용펀드) 코드 기준가는 클래스 총보수를 전혀 부담하지 않고 피투자펀드 보수+기타비용
   (≈ 합성 − 총보수)만 부담함이 확인됨. 운용 코드는 같은 펀드·기간 표의 클래스별 (합성 − 총보수)에 위 class-common 규칙
   (0.01%p 이내 일치 → 그 값/high, 아니면 중앙값+min/max/medium)을 적용. fee_ex_sales_pct 는 참고용으로 유지.
   [class_total_fee_median_pct / class_synthetic_median_pct / pension_class_synthetic_pct]
   운용 코드 행: 같은 펀드·기간 표의 전 클래스 총보수·합성 중앙값, 개인연금/연금저축 클래스(라벨에 '개인연금'·'연금저축';
   KCGI 는 C-P·C-Pe, 신영 전치표는 C-P·C-Pe·S-P 열) 합성의 중앙값(해당 클래스 목록은 note). 클래스·단일 행: 그 행의
   총보수·합성, 연금 클래스이면 합성(아니면 비움).
6) confidence: high = 코드표로 클래스 확정 + 원문 값 판독 일치(+간이 일치 또는 동일 표의 다른 기간),
   medium = 기간 경계를 연혁/주석에서 보정했거나 간이 불일치·미게재, low = 원문 자체가 내부 모순(아래 note).
[범위 밖] DB 2040(EA5524)과 트러스톤 TDF 3개 펀드는 공시 글라이드패스 값이 없어 92개 코드 유니버스
   (prospectus_index_tdfext_G_20261009.csv)에 포함되지 않았으므로 이 표에도 없다.
실행: PYTHONPATH=src python -m pension_lab.fetch.tdfext_fee_extract
"""
from __future__ import annotations

import re
import statistics
import subprocess
from pathlib import Path

import pandas as pd

from .. import paths

FUND_TDF = paths.FUND_TDF
PROS = FUND_TDF / "prospectus"
OUT = FUND_TDF / "tdfext_fee_kofia_20261009.csv"
EXPECT_CSV = FUND_TDF / "tdfext_fee_expect.csv"   # standardCd,start,expect_fee_pct — 사용자가 투자설명서에서 판독(저장소 밖)
TODAY = pd.Timestamp("2026-10-09")
OPEN_S, OPEN_E = "1900-01-01", "2200-12-31"

MGR_SHORT = {"하나자산운용": "하나", "우리자산운용": "우리", "대신자산운용": "대신", "키움투자자산운용": "키움",
             "교보자산운용": "교보", "신영자산운용": "신영", "한화자산운용": "한화", "디비자산운용": "DB",
             "흥국자산운용": "흥국", "엔에이치아문디자산운용": "NH-Amundi", "아이비케이자산운용": "IBK",
             "비엔케이자산운용": "BNK", "마이다스에셋자산운용": "마이다스", "케이씨지아이자산운용": "KCGI"}

SEC = r"(나\.|2\))\s*집합투자기구에\s*부과되는\s*보수\s*및\s*비용"   # 13.보수 및 수수료 → 나.
NUM = re.compile(r"^(\d+\.\d+|\d|-)%?$")

# ---------------------------------------------------------------------------------------------
# 클래스 식별 기대값(자동 식별 결과와 assert). 값: 'base'(종류형의 운용/모 코드), 'single'(종류 없음), 또는 클래스명
# 근거: 각 T PDF '제1부 1. 집합투자기구의 명칭' 표(코드↔종류)와 KOFIA 펀드명 접미어.
CLASS_EXPECT = {
    "K55102ED7128": "S-P2",          # T p12 'S-P2 수수료미징구-온라인슈퍼-퇴직연금 ED712'
    "K55203DN8867": "A",             # T p? '수수료선취-오프라인(A) DN886'
    "K55203E02510": "C-F",           # '수수료미징구-오프라인-기관 (C-F) E0251'
    "K55207CP5439": "Ae", "K55207CP5579": "A", "K55207CP5827": "C", "K55207CP5967": "C",
    "K55207CP6353": "Ae", "K55207CP6502": "A", "K55207EA7331": "Cf",
    "K55209DE4440": "C-P2e",         # 'C-P2e(수수료미징구-온라인-퇴직연금) DE444'
    "K55213C50587": "S-P(연금저축)", "K55213EA0957": "J-Pe(연금저축)",
    "K55216EA5334": "A-E", "K55216EA5722": "A-E",
    "K55232CH8788": "C", "K55232CI3960": "A",
    "K55303DV7785": "C-P1", "K55303DV7991": "Ce", "K55303EN4997": "C-Pe1", "K55303EN5127": "Ae",
    "K55365DA4816": "S",             # 2045 class table: 종류S 수수료후취-온라인슈퍼 DA481 (모 코드는 DA508)
    # 종류 없는 단일 펀드(ETF / 신종개인연금 전환형)
    "K55206DU2520": "single", "K55206DU2538": "single", "K55206DU2546": "single", "K55213DU6050": "single",
    "K55213CC7887": "single", "K55213CC7895": "single", "K55213DP9598": "single",
    "K55213DP9606": "single", "K55213DP9614": "single",
}
# 나머지 코드는 모두 'base'(종류형 펀드의 운용/모 코드)로 기대.
# 클래스 행 중 개인연금(연금저축) 클래스: 코드표 라벨에 '개인연금'/'연금저축' (T 1.명칭 표에서 확인)
PENSION_CLASS_ROWS = {"K55213C50587": ("S-P(연금저축)",), "K55213EA0957": ("J-Pe(연금저축)",),
                      "K55303DV7785": ("C-P1",), "K55303EN4997": ("C-Pe1",),
                      # 한화 신종개인연금 전환형(단일 종류): 펀드 자체가 개인연금 전용 상품
                      **{c: ("single",) for c in ("K55213CC7887", "K55213CC7895", "K55213DP9598", "K55213DP9606", "K55213DP9614")}}   # 마이다스 C-P1/C-Pe1 = 오프라인/온라인-개인연금
# 코드표가 가로형이라 코드 줄에 클래스명이 없는 경우(머리글 줄과 열 위치로 수동 확인):
CLASS_LINE_NO_LABEL = {"K55365DA4816"}   # T p12: 머리글 '종류A 종류Ae 종류AG 종류CI 종류CW 종류CF 종류S' ↔ 'DA509 … DA481'(7번째)

# ---------------------------------------------------------------------------------------------
# 보수 위치 지정자. periods: (anchor 정규식|None, 숫자행 순번, start, end[, col override]). 기대값은 EXPECT_CSV.
# anchor=None → 섹션 시작 직후. col: 숫자 토큰(소수/'-') 인덱스. 'pen' = 뒤에서 두 번째(교보·한화: 증권거래비용 열이 맨 끝).
P = lambda *a: a
LOC = {
    # 하나: 열=집합,판매,수탁,사무,총보수,기타,총보수비용,동종,합성,증권 (T p42). 단일 기간 표.
    "K55102ED7128": dict(adj={"2024-09-03"}, col=8, periods=[P(r"\[최초설정일부터 투자신탁의 해지일까지\]", 15, "2024-09-03", OPEN_E)],
                         note="T p14 연혁: 2024-09-03 종류 S-P2 판매보수 인하 → 현행 요율 적용 시작일로 start 설정, 이전 요율 미공시"),
    # 대신 2055 종류A: 열=집합,판매,신탁,사무,총보수,동종,기타,총보수비용,합성,증권 (T p51-62). 16행 중 0번(A).
    "K55203DN8867": dict(col=8, periods=[
        P(r"최초설정일로부터 투자전략 변경전일까지", 0, OPEN_S, "2023-04-10"),
        P(r"투자전략변경후\(2023년 4월 11일\)", 0, "2023-04-11", "2025-12-31"),
        P(r"\[2026년 1월1일~ 2030년", 0, "2026-01-01", "2030-12-31"),
        P(r"\[2031년 1월 1일~ 2035년", 0, "2031-01-01", "2035-12-31"),
        P(r"\[2036년 1월 1일~ 2040년", 0, "2036-01-01", "2040-12-31"),
        P(r"\[2041년 1월 1일~ 2045년", 0, "2041-01-01", "2045-12-31"),
        P(r"\[2046년 1월 1일~ 2050년", 0, "2046-01-01", "2050-12-31"),
        P(r"\[2051년 1월 1일~ 투자신탁 해지일", 0, "2051-01-01", OPEN_E)]),
    # 대신 2035 종류C-F: 16행 중 5번.
    "K55203E02510": dict(col=8, periods=[
        P(r"\[최초설정일로부터 2025년 12월31일까지\]", 5, OPEN_S, "2025-12-31"),
        P(r"\[2026년 1월 1일부터 2030년 12월 31일까지\]", 5, "2026-01-01", "2030-12-31"),
        P(r"\[2031년 1월 1일부터 투자신탁 해지일까지\]", 5, "2031-01-01", OPEN_E)],
        note="C-F 클래스 첫 기준가 2024-09-30(간이 투자실적표); 표는 '최초설정일'부터로 표기"),
    # 교보: 열=집합,판매,신탁,사무,총보수,기타,총보수비용,동종,합성,증권. 빈칸 때문에 '합성'은 증권열이 있으면 뒤에서 2번째, 없으면 마지막.
    "K55207CP5439": dict(col="pen", periods=[P(None, 1, OPEN_S, OPEN_E)],
                         note="T p52 표에 기간 구분 없음(현행 표만 공시); 과거 기간 요율은 이 문서로 확인 불가"),
    "K55207CP5579": dict(col="pen", periods=[
        P(r"\(1\) 최초설정일로부터 2024년 12월 31일까지", 0, OPEN_S, "2024-12-31", -1),
        P(r"\(2\) 2025년 1월 1일부터 신탁계약 해지일까지", 0, "2025-01-01", OPEN_E)]),
    "K55207CP5827": dict(col="pen", periods=[
        P(r"\(1\) 최초설정일로부터 2024년 12월 31일까지", 2, OPEN_S, "2024-12-31", -1),
        P(r"\(2\) 2025년 1월 1일부터 2029년 12월 31일까지", 2, "2025-01-01", "2029-12-31"),
        P(r"\(3\) 2030년 1월 1일부터 신탁계약 해지일까지", 2, "2030-01-01", OPEN_E, -1)]),
    "K55207CP5967": dict(col="pen", periods=[
        P(r"\(1\) 최초설정일로부터 2024년 12월 31일까지", 2, OPEN_S, "2024-12-31", -1),
        P(r"\(2\) 2025년 1월 1일부터 2029년 12월 31일까지", 2, "2025-01-01", "2029-12-31"),
        P(r"\(3\) 2030년 1월 1일부터 2034년 12월 31일까지", 2, "2030-01-01", "2034-12-31", -1),
        P(r"\(4\) 2035년 1월 1일부터 신탁계약 해지일까지", 2, "2035-01-01", OPEN_E, -1)]),
    "K55207CP6353": dict(col="pen", periods=[
        P(r"\(1\) 최초설정일로부터 2024년 12월 31일까지", 1, OPEN_S, "2024-12-31", -1),
        P(r"\(2\) 2025년 1월 1일부터 2029년 12월 31일까지", 1, "2025-01-01", "2029-12-31"),
        P(r"\(3\) 2030년 1월 1일부터 2034년 12월 31일까지", 1, "2030-01-01", "2034-12-31", -1),
        P(r"\(4\) 2035년 1월 1일부터 2039년 12월 31일까지", 1, "2035-01-01", "2039-12-31", -1),
        P(r"\(5\) 2040년 1월 1일부터 신탁계약 해지일까지", 1, "2040-01-01", OPEN_E, -1)]),
    "K55207CP6502": dict(col="pen", periods=[
        P(r"\(1\) 최초설정일로부터 2024년 12월 31일까지", 0, OPEN_S, "2024-12-31", -1),
        P(r"\(2\) 2025년 1월 1일부터 2029년 12월 31일까지", 0, "2025-01-01", "2029-12-31"),
        P(r"\(3\) 2030년 1월 1일부터 2034년 12월 31일까지", 0, "2030-01-01", "2034-12-31", -1),
        P(r"\(4\) 2035년 1월 1일부터 2039년 12월 31일까지", 0, "2035-01-01", "2039-12-31", -1),
        P(r"\(5\) 2040년 1월 1일부터 2044년 12월 31일까지", 0, "2040-01-01", "2044-12-31", -1),
        P(r"\(6\) 2045년 1월 1일부터 신탁계약 해지일까지", 0, "2045-01-01", OPEN_E, -1)]),
    "K55207EA7331": dict(col="pen", periods=[
        P(r"\(1\) 최초설정일로부터 2029년 12월 31일까지", 4, OPEN_S, "2029-12-31"),
        P(r"\(2\) 2030년 1월 1일부터 2034년 12월 31일까지", 4, "2030-01-01", "2034-12-31", -1),
        P(r"\(3\) 2035년 1월 1일부터 2039년 12월 31일까지", 4, "2035-01-01", "2039-12-31", -1),
        P(r"\(4\) 2040년 1월 1일부터 2044년 12월 31일까지", 4, "2040-01-01", "2044-12-31", -1),
        P(r"\(5\) 2045년 1월 1일부터 2049년 12월 31일까지", 4, "2045-01-01", "2049-12-31", -1),
        P(r"\(6\) 2050년 1월 1일부터 신탁계약 해지일까지", 4, "2050-01-01", OPEN_E, -1)]),
    # 신영 TDF(2020형): 가로·세로 전치 표(T p31). 두 번째 블록(C-P…O) '합성 총보수·비용' 행의 4번째 열 = C-P2e.
    "K55209DE4440": dict(adj={"2022-11-18"}, col=3, sales_row=8, tot_row=11, periods=[P(r"최초 설정일부터 투자신탁 종료일까지 적용하는 투자신탁 보수", 14, "2022-11-18", OPEN_E)],
                         note="전치 표: 블록2 합성행 [C-P,C-Pe,C-P2,C-P2e,S,S-P,S-P2,O] 중 C-P2e. T 연혁 2022-11-18 운용보수 인하 → start 보정, 이전 요율 미공시"),
    # 한화 LIFEPLUS TDF 2020 S-P(연금저축): 20행 중 14번. 열 빈칸 다수 → 'pen'(증권거래비용 존재).
    "K55213C50587": dict(adj={"2022-08-30"}, col="pen", periods=[P(None, 14, "2022-08-30", OPEN_E)],
                         note="T p42 ※: 2022-08-30 집합투자업자보수 인하 → 현행표 적용 start 보정; 이전 합성값 미공시"),
    # 한화 LIFEPLUS 2060 J-Pe(연금저축): 21행 중 18번. 열=…,총보수비용,동종,합성,증권 → idx 8
    "K55213EA0957": dict(col=8, periods=[
        P(r"\[최초설정일로부터 2044년 12월 31일까지 적용하는 투자신탁보수\]", 18, OPEN_S, "2044-12-31"),
        P(r"\[2045년 1월 1일부터 2049년 12월 31일까지 적용하는 투자신탁보수\]", 18, "2045-01-01", "2049-12-31"),
        P(r"\[2050년 1월 1일부터 신탁계약의 해지일까지 적용하는 투자신탁보수\]", 18, "2050-01-01", OPEN_E)]),
    # DB: 열=집합,판매,수탁,사무,총보수,기타,총보수비용(TER),합성,동종,증권 → idx 7. A-E = 1번 행.
    "K55216EA5334": dict(col=7, periods=[P(None, 1, OPEN_S, OPEN_E)],
                         note="T p39 표에 기간 구분 없음(현행 표만 공시)"),
    "K55216EA5722": dict(col=7, periods=[
        P(r"\[최초설정일부터 2039 년 12 월 31 일까지", 1, OPEN_S, "2039-12-31"),
        P(r"\[2040 년 1 월 1 일부터 2049 년 12 월 31 일까지", 1, "2040-01-01", "2049-12-31"),
        P(r"\[2050 년 1 월 1 일부터 신탁계약의 해지일까지", 1, "2050-01-01", OPEN_E)]),
    # NH-Amundi: 열=집합,판매,신탁,사무,총보수,기타,총보수비용,합성,동종,증권 → idx 7. A=0, C=2.
    "K55232CH8788": dict(col=7, periods=[
        P(r"\[최초설정일로부터 2024년 12월 31일까지", 2, OPEN_S, "2024-12-31"),
        P(r"\[2025년 1월 1일부터 2029년 12월 31일까지 적용하는 투자신탁보수\]", 2, "2025-01-01", "2029-12-31"),
        P(r"\[2030년 1월 1일부터 2034년 12월 31일까지", 2, "2030-01-01", "2034-12-31"),
        P(r"\[2035년 1월 1일부터 2039년 12월 31일까지", 2, "2035-01-01", "2039-12-31"),
        P(r"\[2040년 1월 1일부터 신탁계약의 해지일까지", 2, "2040-01-01", OPEN_E)]),
    "K55232CI3960": dict(col=7, periods=[
        P(r"\[최초설정일로부터 2024년 12월 31일까지", 0, OPEN_S, "2024-12-31"),
        P(r"\[2025년 1월 1일부터 2029년 12월 31일까지 적용하는 투자신탁보수\]", 0, "2025-01-01", "2029-12-31"),
        P(r"\[2030년 1월 1일부터 2034년 12월 31일까지", 0, "2030-01-01", "2034-12-31"),
        P(r"\[2035년 1월 1일부터 신탁계약의 해지일까지", 0, "2035-01-01", OPEN_E)]),
    # 마이다스: 열=집합,판매,수탁,사무,총보수,기타,총보수비용,동종,합성,증권 → idx 8. 13행(A,Ae,C,Ce,C-P1,C-Pe1,…)
    "K55303DV7785": dict(col=8, periods=[P(None, 4, OPEN_S, OPEN_E)], note="표에 기간 구분 없음(현행 표만 공시)"),
    "K55303DV7991": dict(col=8, periods=[P(None, 3, OPEN_S, OPEN_E)], note="표에 기간 구분 없음(현행 표만 공시)"),
    "K55303EN4997": dict(col=8, periods=[P(None, 5, OPEN_S, OPEN_E)], note="표에 기간 구분 없음(현행 표만 공시)"),
    "K55303EN5127": dict(col=8, periods=[P(None, 1, OPEN_S, OPEN_E)], note="표에 기간 구분 없음(현행 표만 공시)"),
    # KCGI 2045 종류S: 열=집합,판매,신탁,사무,총보수,동종,기타,총보수비용,합성,증권 → idx 8. 행 라벨 같은 줄(A,Ae,AG,CI,CW,CF,S…)
    "K55365DA4816": dict(col=8, periods=[          # T p81~83, 5개 기간 표, 13행 중 6번(S)
        P(r"\[최초설정일~2025\.12\.31\]", 6, OPEN_S, "2025-12-31"),
        P(r"\[2026\.01\.01~2030\.12\.31\]", 6, "2026-01-01", "2030-12-31"),
        P(r"\[2031\.01\.01~2035\.12\.31\]", 6, "2031-01-01", "2035-12-31"),
        P(r"\[2036\.01\.01~2040\.12\.31\]", 6, "2036-01-01", "2040-12-31"),
        P(r"\[2041\.01\.01~투자신탁해지일\]", 6, "2041-01-01", OPEN_E)]),
    # 키움 KIWOOM ETF: 세로형 단일 표(T p37~).
    "K55206DU2520": dict(kind="vert", anchor=r"합성 총보수ㆍ비용\(피투자신탁의", periods=[P(None, 0, OPEN_S, OPEN_E)],
                         note="ETF(단일 종류); 표에 기간 구분 없음"),
    "K55206DU2538": dict(kind="vert", anchor=r"합성 총보수ㆍ비용\(피투자신탁의", periods=[P(None, 0, OPEN_S, OPEN_E)],
                         note="ETF(단일 종류); 표에 기간 구분 없음"),
    "K55206DU2546": dict(kind="vert", anchor=r"합성 총보수ㆍ비용\(피투자신탁의", periods=[P(None, 0, OPEN_S, OPEN_E)],
                         note="ETF(단일 종류); 표에 기간 구분 없음"),
    # 한화 PLUS ETF 2060: 행 '투자신탁', 열=집합,판매,신탁,사무,총보수,동종,기타,총보수비용,합성,증권 → idx 8
    "K55213DU6050": dict(col=8, mn=3, periods=[
        P(r"\[최초설정일로부터 2039년 12월 31일까지", 0, OPEN_S, "2039-12-31"),
        P(r"\[2040년 1월 1일부터 2049년 12월 31일까지", 0, "2040-01-01", "2049-12-31"),
        P(r"\[2050년 1월 1일부터 2059년 12월 31일까지", 0, "2050-01-01", "2059-12-31"),
        P(r"\[2060년 1월 1일부터 투자신탁 해지일까지", 0, "2060-01-01", OPEN_E)], note="ETF(단일 종류)"),
    # 한화 신종개인연금(전환형, 종류 없음): 세로형 단일 표 또는 '투자신탁' 1행 표
    "K55213CC7887": dict(adj={"2022-09-14"}, kind="vert", anchor=r"합성 총 보수ㆍ비용", periods=[P(None, 0, "2022-09-14", OPEN_E)],
                         note="단일 종류. T 연혁 2022-09-14 집합투자업자 보수 인하 → start 보정, 이전 요율 미공시"),
    "K55213CC7895": dict(adj={"2022-09-14"}, kind="vert", anchor=r"합성 총 보수ㆍ비용", periods=[P(None, 0, "2022-09-14", OPEN_E)],
                         note="단일 종류. T 연혁 2022-09-14 집합투자업자 보수 인하 → start 보정, 이전 요율 미공시"),
    "K55213DP9598": dict(adj={"2022-09-14"}, kind="vert", anchor=r"합성 총 보수ㆍ비용", periods=[P(None, 0, "2022-09-14", "2034-12-31")],
                         note="단일 종류. T p42 ※ 2022-09-14 집합투자업자보수 인하(~2034-12-31 적용) → 구간 보정(2035~ 미공시)"),
    "K55213DP9606": dict(adj={"2022-09-14"}, col="pen", mn=4, periods=[
        P(r"\[최초설정일로부터 2024년 12월 31일까지", 0, "2022-09-14", "2024-12-31"),
        P(r"\[2025년 1월 1일부터 2029년 12월 31일까지", 0, "2025-01-01", "2029-12-31"),
        P(r"\[2030년 1월 1일부터 신탁계약의 해지일까지", 0, "2030-01-01", OPEN_E)],
        note="단일 종류. 첫 표 ※ 2022-09-14 집합투자업자보수 변경 → 첫 구간 start 2022-09-14 보정"),
    "K55213DP9614": dict(adj={"2022-09-14"}, col="pen", mn=4, periods=[
        P(r"\[최초설정일로부터 2034 년 12 월 31 일까지", 0, "2022-09-14", "2034-12-31"),
        P(r"\[2035 년 1 월 1 일부터 2039 년 12 월 31 일까지", 0, "2035-01-01", "2039-12-31"),
        P(r"\[2040 년 1 월 1 일부터 신탁계약의 해지일까지", 0, "2040-01-01", OPEN_E)],
        note="단일 종류. 첫 표 ※ 2022-09-14 집합투자업자보수 변경 → 첫 구간 start 2022-09-14 보정"),
}

# 원문 자체의 이상(수동 판독)으로 confidence 를 낮추는 구간: (code, start) → note
LOW = {
    ("K55232CH8788", "2030-01-01"): "원문 이상: 2030~2034 표의 기타·총보수비용·합성 값이 2025~2029 표와 동일(총보수만 바뀜) — 복사 오류 의심",
    ("K55232CI3960", "2030-01-01"): "원문 이상: 2030~2034 표의 기타·총보수비용·합성 값이 2025~2029 표와 동일(총보수만 바뀜) — 복사 오류 의심",
}


def _expect() -> dict:
    """EXPECT_CSV → {(standardCd, start): 기대값}. 파일이 없으면 빈 dict(대조 생략)."""
    if not EXPECT_CSV.exists():
        print(f"[경고] {EXPECT_CSV} 없음 → 판독 기대값 대조 없이 추출만 함 (DATA_SOURCES.md 3-3절)")
        return {}
    e = pd.read_csv(EXPECT_CSV, dtype={"standardCd": str, "start": str})
    return {(r.standardCd, r.start): float(r.expect_fee_pct) for r in e.itertuples()}


# ---------------------------------------------------------------------------------------------
def _pages(code: str, kind: str) -> list[str]:
    pdf = PROS / f"{code}_{kind}.pdf"
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True).stdout
    return out.decode("utf-8", "replace").split("\f")


def _lines(pages):
    return [(pi, l) for pi, p in enumerate(pages, 1) for l in p.split("\n")]


def _toks(line):
    return [t.replace("%", "") for t in line.split() if NUM.match(t)]


def _ndec(line):
    return sum(1 for t in _toks(line) if "." in t)


def _sec_start(L):
    for i, (pi, l) in enumerate(L):
        if re.search(SEC, l) and pi > 8:   # 요약(간이) 부분 제외
            return i
    raise ValueError("보수 섹션 없음")


def identify(code: str, pages) -> tuple[str, int, str]:
    """표준코드 → ('name'|'class', page, 근거줄). 'name' = 코드가 펀드 명칭 줄에 있음(운용/모 코드 또는 단일 펀드)."""
    short = code[6:11]
    L = _lines(pages)
    hits = [(pi, l) for pi, l in L if pi > 8 and re.search(rf"(?<![A-Z0-9]){short}(?![0-9])", l)]
    if not hits:
        raise ValueError(f"{code}: 코드 {short} 미발견")
    pi, l = hits[0]          # 제1부 '1. 집합투자기구의 명칭' 표(첫 등장)
    txt = re.sub(r"\s+", " ", l).strip()
    if re.search(r"투자신탁|펀드\s*코드\s*[:：]", txt):
        return "name", pi, txt
    return "class", pi, txt


def _is_single(pages) -> bool:
    """제1부 '2. 집합투자기구의 종류 및 형태' 의 '특수형태' 항목(+다음 3줄)에 '종류형'이 없으면 단일(종류 없음) 펀드."""
    L = _lines(pages)
    for k, (pi, l) in enumerate(L):
        if pi > 8 and "...." not in l and re.search(r"집합투자기구의\s*종류\s*및\s*형태", l):
            for j in range(k + 1, min(k + 25, len(L))):
                if re.search(r"특수\s*형태", L[j][1]):
                    return "종류형" not in " ".join(x for _, x in L[j:j + 4])
    raise ValueError("특수형태 항목 없음")


def extract(code: str, pages, exp: dict | None = None) -> list[dict]:
    cfg = LOC[code]
    L = _lines(pages)
    s0 = _sec_start(L)
    kind, mn = cfg.get("kind", "row"), cfg.get("mn", 5)
    recs = []
    for per in cfg["periods"]:
        anchor, ridx, st, en = per[:4]
        col = per[4] if len(per) > 4 else cfg.get("col")
        expect = (exp or {}).get((code, st))
        i = s0
        if anchor:
            i = next(k for k in range(s0, len(L)) if re.search(anchor, L[k][1]))
        if kind == "vert":
            k = next(k for k in range(i, len(L)) if re.search(cfg["anchor"], L[k][1]))
            cand = [(k + d) for d in range(0, 3) if _ndec(L[k + d][1]) >= 1]
            j = cand[0]
            val = float([t for t in _toks(L[j][1]) if "." in t][0])
            ev = re.sub(r"\s+", " ", (L[k][1] + " " + (L[j][1] if j != k else ""))).strip()
            peers = []
            ks = next(q for q in range(i, k) if re.search(r"판매회사\s*보수|지정참가회사\s*보수", L[q][1]))
            sales = float([t for t in _toks(L[ks][1]) if "." in t][0])
            kt = next(q for q in range(i, k) if re.search(r"총\s*보\s*수\s+\d", L[q][1]) and "동종" not in L[q][1])
            total = float([t for t in _toks(L[kt][1]) if "." in t][0])
        else:
            rows = [k for k in range(i + 1, len(L)) if _ndec(L[k][1]) >= mn]
            j = rows[ridx]
            tk = _toks(L[j][1])
            c = -2 if col == "pen" else col
            val = float(tk[c])
            ev = re.sub(r"\s+", " ", L[j][1]).strip()
            if "sales_row" in cfg:      # 전치 표: 판매회사보수·총보수 행(같은 열)
                sales = float(_toks(L[rows[cfg["sales_row"]]][1])[c])
                total = float(_toks(L[rows[cfg["tot_row"]]][1])[c])
            else:
                sales = float(tk[1])    # 행 표: 두 번째 열 = 판매회사보수
                total = float(tk[4])    # 다섯 번째 열 = 총보수(운용+판매+수탁+사무)
            peers = []
            for q in rows[max(0, ridx - 8): ridx + 8]:
                tq = _toks(L[q][1])
                try:
                    peers.append(float(tq[c]))
                except (IndexError, ValueError):
                    pass
        if expect is not None and abs(val - expect) > 1e-9:
            raise AssertionError(f"{code} {st}: 추출 {val} ≠ 판독 {expect} | {ev}")
        if en is None:   # 기간 머리글에서 end 가 '해지일'인데 구성 단순화를 위해 None 표기한 경우
            en = OPEN_E
        hdr = re.sub(r"\s+", " ", L[i][1]).strip() if anchor else ""
        recs.append(dict(start=st, end=en, fee_pct=val, page=L[j][0], evidence=(f"{hdr[:40]} | " if hdr else "") + ev,
                         sales=sales, total=total, row_line=L[j][1], peers=[p for p in peers if p != val]))
    return recs


# ---------------------------------------------------------------------------------------------
# [추가] 운용(모) 코드용 '판매보수 제외 공통비용' = 클래스별 (합성 총보수·비용 − 판매회사보수) 의 기간별 집계.
# 운용 코드의 기준가는 판매보수를 부담하지 않으므로, 같은 펀드·같은 기간 표의 모든 공시 클래스에서
# 합성−판매 를 계산해 0.01%p 이내로 일치하면 그 값(class-common), 아니면 중앙값(+min/max, medium).
# 행 표의 '합성' 열 판별(운용사 레이아웃 유형):
#   A(하나·우리·한화·IBK): 총보수 뒤 [기타?, 총보수비용, 동종?, 합성, 증권?] — 빈칸이 있어 의미 규칙으로 판별
#   B(키움·흥국·KCGI):     총보수 뒤 [동종, 기타, 총보수비용, 합성, 증권] — 증권거래비용('-' 포함)이 항상 맨 끝 → 뒤에서 2번째
#   C(NH-Amundi):          [기타, 총보수비용, 합성, 동종, 증권] → 10토큰 행의 8번째(idx 7)
#   BNK: 집합·신탁·사무 열이 병합되어 행에 [판매, 총보수, 기타, 총보수비용, 동종?, 합성, 증권] → 판매=첫 토큰, 합성=뒤에서 2번째
#   TR(신영): 전치 표(행=보수 항목, 열=클래스). 2번째 숫자행=판매회사보수, '총 보수' 행 뒤 [기타?, 총보수비용, 합성]
LAYOUT = {"하나": "A", "우리": "A", "한화": "A", "IBK": "A", "키움": "B", "흥국": "B", "KCGI": "B",
          "NH-Amundi": "C", "BNK": "BNK", "신영": "TR"}
_PERDATE = re.compile(r"(최초\s*설정일|\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일|\d{4}[./]\s*\d{1,2}[./]\s*\d{1,2})")
_DATE = re.compile(r"(최초\s*설정일|(\d{4})\s*[년.]\s*(\d{1,2})\s*[월.]\s*(\d{1,2})|해지일|종료일)")


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _blocks(L, s0, mn):
    """보수 섹션을 기간 머리글 단위 블록으로 자름: [{hdr, rows:[(page, tokens, line)]}]"""
    out, cur = [], {"hdr": "", "rows": []}
    for k in range(s0 + 1, len(L)):
        l = L[k][1]
        if re.search(r"1,?000\s*만원|1천만원", l):
            break
        if (_PERDATE.search(l) and re.search(r"(~|부터|까지)", l) and len(l.strip()) < 100
                and not re.search(r"직전|(?<!\d)\d\.\d{2}|설정일로부터 \d+개월|1월간", l)):
            out.append(cur)
            cur = {"hdr": re.sub(r"\s+", " ", l).strip(), "rows": []}
            continue
        if _ndec(l) >= mn:
            cur["rows"].append((L[k][0], _toks(l), re.sub(r"\s+", " ", l).strip(), k))
    out.append(cur)
    return [b for b in out if b["rows"]]


def _period(h):
    if not h:
        return OPEN_S, OPEN_E
    out = []
    for m in _DATE.finditer(h):
        g = m.group(0)
        out.append(OPEN_S if "최초" in g else OPEN_E if ("해지" in g or "종료" in g)
                   else "%s-%02d-%02d" % (m.group(2), int(m.group(3)), int(m.group(4))))
    if len(out) == 1:
        out.append(OPEN_E)
    return out[0], out[1]


def _sales_hap(tk, typ):
    if typ == "BNK":
        return ((_f(tk[1]), _f(tk[-2]), _f(tk[4])) if len(tk) >= 10 else (_f(tk[0]), _f(tk[-2]), _f(tk[1])))
    s, t4, rest = _f(tk[1]), _f(tk[4]), tk[5:]
    if typ == "B":
        return s, _f(rest[-2]), t4
    if typ == "C":
        return s, (_f(tk[7]) if len(tk) == 10 else None), t4
    i = 1 if (rest[0] == "-" or (_f(rest[0]) is not None and _f(rest[0]) < t4 - 1e-9)) else 0
    v, rem = _f(rest[i]), rest[i + 1:]
    if len(rem) == 3:
        return s, _f(rem[1]), t4
    if len(rem) == 1:
        return s, _f(rem[0]), t4
    if len(rem) == 2:
        a, b = rem
        return s, (_f(a) if (b == "-" or (_f(b) is not None and _f(b) < v)) else _f(b)), t4
    return s, None, t4


_PEN = re.compile(r"개인연금|연금저축")
_TAG = re.compile(r"\b([A-Z]{1,2}-?P[A-Za-z0-9]*)")
# 신영 전치 표 16열 순서: A,A-E,A-G,C,C-E,C-G,C-I,C-W,C-P,C-Pe,C-P2,C-P2e,S,S-P,S-P2,O → 개인연금 = C-P,C-Pe,S-P
TR_PENSION = {8: "C-P", 9: "C-Pe", 13: "S-P"}


def _pension_tag(L, R, j, mgr):
    """행 표에서 j번째 행이 개인연금/연금저축 클래스인지. 라벨은 숫자 줄과 그 아래 줄(다음 행 전까지)에 걸쳐 있음."""
    k = R[j][3]
    if mgr == "KCGI":       # 행 라벨이 같은 줄의 짧은 코드(C-P, C-Pe = 개인연금; C-P2/C-Pe2 = 퇴직연금)
        m = re.match(r"\s*(C-Pe?)\s", L[k][1])
        return m.group(1) if m else None
    nxt = R[j + 1][3] if j + 1 < len(R) else k + 4
    txt = re.sub(r"\s", "", " ".join(x for x in L[k][1].split() if not NUM.match(x))
                 + "".join(L[q][1] for q in range(k + 1, min(nxt, k + 5))))
    if not _PEN.search(txt):
        return None
    m = _TAG.findall(txt)
    return m[-1] if m else "개인연금"


def base_common(code, mgr, pages):
    typ = LAYOUT[mgr]
    L = _lines(pages)
    s0 = _sec_start(L)
    res = []
    for b in _blocks(L, s0, 4 if typ == "BNK" else 5):
        st, en = _period(b["hdr"])
        vals, bad = [], 0
        R = b["rows"]
        if typ == "TR":
            sal = [_f(x) for x in R[1][1]]
            it = next(k for k, r in enumerate(R) if re.search(r"총\s*보수", r[2]) and "비용" not in r[2])
            tot = [_f(x) for x in R[it][1]]
            ih = it + 3 if "기타" in R[it + 1][2] else it + 2
            for ci, (sv, tv, hv) in enumerate(zip(sal, tot, [_f(x) for x in R[ih][1]])):
                if sv is None or hv is None or tv is None or hv < tv - 1e-9:
                    bad += 1
                    continue
                vals.append((round(hv - sv, 4), R[ih][0], R[ih][2], round(hv - tv, 4), hv, tv,
                             TR_PENSION.get(ci) if len(sal) == 16 else None))
        else:
            for j, (pg, tk, line, _k) in enumerate(R):
                try:
                    sv, hv, t4 = _sales_hap(tk, typ)
                except (IndexError, ValueError):
                    sv = hv = t4 = None
                if sv is None or hv is None or t4 is None or hv < t4 - 1e-9:
                    bad += 1          # 합성 < 총보수 → 원문 오기/열 판별 실패: 집계 제외
                    continue
                vals.append((round(hv - sv, 4), pg, line, round(hv - t4, 4), hv, t4, _pension_tag(L, R, j, mgr)))
        if vals:
            res.append(dict(start=st, end=en, hdr=b["hdr"], vals=vals, bad=bad))
    return res


def _in_g(val: float, gpages) -> bool:
    g = re.sub(r"\s+", " ", " ".join(gpages[:12]))
    s = f"{val}"
    cands = {s, f"{val:.3f}", f"{val:.4f}", f"{val:.2f}"}
    return any(re.search(rf"(?<![\d.]){re.escape(c)}(?!\d)", g) for c in cands)


def run() -> pd.DataFrame:
    idx = pd.read_csv(PROS / "prospectus_index_tdfext_G_20261009.csv", dtype=str)
    names = pd.read_csv(FUND_TDF / "tdfext_fund_names_kofia_20261008.csv", dtype=str).set_index("fund_code").fund_name
    gp = pd.read_csv(FUND_TDF / "glidepath_disclosed_web_kr_others.csv", dtype=str)
    gp["code"] = gp.source_url.str.extract(r"표준코드 (K\w{11})")
    gp = gp.drop_duplicates("code").set_index("code")
    expect = _expect()
    rows = []
    for code in idx.standardCd:
        name = names[code]
        mgr = MGR_SHORT[gp.loc[code, "manager"]]
        m = re.search(r"TDF\s*(\d{4})", name)
        if m:
            vint = int(m.group(1))
        else:   # 신영TDF(목표연도 표기 없음): glidepath 'YYYY (T+k)' → 목표연도 = YYYY - k
            mm = re.match(r"(\d{4}) \(T([+-]\d+)\)", gp.loc[code, "target_year_or_years_to_target"])
            vint = int(mm.group(1)) - int(mm.group(2))
        T, G = _pages(code, "T"), _pages(code, "G")
        kind, pg, ev = identify(code, T)
        exp = CLASS_EXPECT.get(code, "base")
        if kind == "name":
            kind = "single" if _is_single(T) else "base"
        if (exp in ("base", "single")) != (kind in ("base", "single")) or (exp in ("base", "single") and exp != kind):
            raise AssertionError(f"{code}: 클래스 식별 {kind} ≠ 기대 {exp} | {ev}")
        label = {"base": "운용(종류형 운용펀드)", "single": "단일(종류없음)"}.get(exp, exp)
        base = dict(standardCd=code, manager=mgr, vintage=vint, class_label=label)
        if exp == "base":
            for p in base_common(code, mgr, T):
                u = [x[3] for x in p["vals"]]
                v = [x[0] for x in p["vals"]]
                umed = round(statistics.median(u), 4)
                vmed = round(statistics.median(v), 4)
                rep = min(p["vals"], key=lambda x: abs(x[3] - umed))
                hdr = (p["hdr"][:30] + " | ") if p["hdr"] else ""
                nt = [f"종류형 운용펀드 코드(코드표 T p{pg}): 13.보수 표에 이 코드 행 없음 → fee_pct 비움",
                      "fee_underlying_pct = 같은 기간 표 각 클래스 (합성 총보수·비용 − 총보수) [주 지표]"]
                if max(u) - min(u) <= 0.01 + 1e-9:
                    nt.append(f"underlying class-common, {len(u)} classes agree")
                    conf = "high"
                else:
                    nt.append(f"underlying 클래스 간 불일치 → 중앙값 (n={len(u)}, min {min(u):.4f}, max {max(u):.4f})")
                    conf = "medium"
                nt.append("fee_ex_sales_pct(참고, 합성−판매): " + (f"{len(v)} classes agree" if max(v) - min(v) <= 0.01 + 1e-9
                          else f"중앙값 n={len(v)}, min {min(v):.4f}, max {max(v):.4f}"))
                if p["bad"]:
                    nt.append(f"합성<총보수 등 판독불가 행 {p['bad']}개 제외")
                if not p["hdr"]:
                    nt.append("표에 기간 구분 없음(현행 표만 공시)")
                pen = [(x[6], x[4]) for x in p["vals"] if x[6]]
                if pen:
                    nt.append("pension_class_synthetic_pct = 개인연금/연금저축 클래스 합성 중앙값: "
                              + ", ".join(f"{a}={b}" for a, b in pen))
                else:
                    nt.append("개인연금 클래스 행 판별 안 됨 → pension_class_synthetic_pct 비움")
                rows.append({**base, "start": p["start"], "end": p["end"], "fee_pct": None, "fee_ex_sales_pct": vmed,
                             "class_total_fee_median_pct": round(statistics.median(x[5] for x in p["vals"]), 4),
                             "class_synthetic_median_pct": round(statistics.median(x[4] for x in p["vals"]), 4),
                             "pension_class_synthetic_pct": round(statistics.median(b for _, b in pen), 4) if pen else None,
                             "fee_underlying_pct": umed, "source": "KOFIA_투자설명서", "page": rep[1],
                             "evidence": (hdr + rep[2])[:120], "confidence": conf, "note": "; ".join(nt)})
            continue
        if exp not in ("single",) and code not in CLASS_LINE_NO_LABEL and not re.search(re.escape(exp.split("(")[0]).replace("\\-", "[-‐]?"), ev.replace(" ", ""), re.I):
            raise AssertionError(f"{code}: 코드표 줄에 클래스명 {exp} 없음 | {ev}")
        cfg = LOC[code]
        for r in extract(code, T, expect):
            cur = pd.Timestamp(r["start"]) <= TODAY <= pd.Timestamp(r["end"])
            notes = [f"클래스근거 T p{pg}: {ev[:60]}"]
            conf = "high"
            if cfg.get("note"):
                notes.append(cfg["note"])
            if r["start"] in cfg.get("adj", set()):
                conf = "medium"      # 기간 경계를 연혁/주석으로 보정
            if cur:
                if _in_g(r["fee_pct"], G):
                    notes.append("간이일치(현행)")
                elif any(_in_g(v, G) for v in r["peers"]):
                    notes.append("간이에 이 클래스 미게재(동일 표 다른 클래스 값은 간이와 일치)")
                else:
                    notes.append("간이 대조 불가/불일치(현행)")
                    conf = "medium"
            if (code, r["start"]) in LOW:
                notes.append(LOW[(code, r["start"])])
                conf = "low"
            notes.append(f"fee_underlying_pct = 합성 {r['fee_pct']} − 총보수 {r['total']}; fee_ex_sales_pct = 합성 − 판매 {r['sales']}"
                         + (" (ETF: 지정참가회사보수를 판매보수로 간주)" if mgr == "키움" and exp == "single" else ""))
            rows.append({**base, "start": r["start"], "end": r["end"], "fee_pct": r["fee_pct"],
                         "fee_ex_sales_pct": round(r["fee_pct"] - r["sales"], 4),
                         "fee_underlying_pct": round(r["fee_pct"] - r["total"], 4),
                         "class_total_fee_median_pct": r["total"], "class_synthetic_median_pct": r["fee_pct"],
                         "pension_class_synthetic_pct": r["fee_pct"] if exp in PENSION_CLASS_ROWS.get(code, ()) else None,
                         "source": "KOFIA_투자설명서",
                         "page": r["page"], "evidence": r["evidence"][:120], "confidence": conf, "note": "; ".join(notes)})
    df = pd.DataFrame(rows, columns=["standardCd", "manager", "vintage", "class_label", "start", "end", "fee_pct",
                                     "fee_ex_sales_pct", "fee_underlying_pct",
                                     "class_total_fee_median_pct", "class_synthetic_median_pct", "pension_class_synthetic_pct", "source", "page", "evidence", "confidence", "note"])
    _selfcheck(df, idx.standardCd.tolist())
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    return df


def _selfcheck(df, codes):
    assert set(df.standardCd) == set(codes), "누락 코드"
    has = df.groupby("standardCd").apply(lambda g: (g.fee_pct.notna() | g.fee_underlying_pct.notna()).all())
    assert has.all(), f"fee 둘 다 비어있는 코드: {list(has[~has].index)}"
    for col, lo, hi in (("fee_pct", 0.1, 2.5), ("fee_ex_sales_pct", 0.1, 2.5), ("fee_underlying_pct", 0.0, 1.5),
                          ("class_total_fee_median_pct", 0.1, 2.5), ("class_synthetic_median_pct", 0.1, 2.5),
                          ("pension_class_synthetic_pct", 0.1, 2.5)):
        f = df[col].dropna()
        assert f.between(lo, hi).all(), f"{col} 범위 이탈: {f[~f.between(lo, hi)].tolist()}"
    for c, g in df.dropna(subset=["start"]).groupby("standardCd"):
        g = g.sort_values("start")
        s, e = pd.to_datetime(g.start).tolist(), pd.to_datetime(g.end).tolist()
        for k in range(1, len(s)):
            assert s[k] > e[k - 1], f"{c}: 기간 중첩"
        assert all(a <= b for a, b in zip(s, e)), f"{c}: start>end"


if __name__ == "__main__":
    d = run()
    print(d.drop(columns=["evidence", "note"]).to_string())
    print(d.confidence.value_counts())
