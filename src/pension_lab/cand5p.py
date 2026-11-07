"""후보 5 포트폴리오판(2026-11-06): 동결된 cand5 위에 F1~F4 정정 + N1 퇴직소득세 · N2 건보료 · N3 기초연금.

설계서 = docs/ideas/본연구후보_20261027/후보5_간단테스트/설계서_후보5_포트폴리오판_20261106.md. cand5.py는 고치지 않고 가져다 쓴다.
o["N1"]·o["N2"]·o["N3"]를 모두 False로 두면 'F1~F4만 켠 판'(설계서 4절 회귀 대상)이다.
자가점검(손계산 + 동결 cand5.evaluate 대조): python -m pension_lab.cand5p
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import cand5 as C

P = C.P
INF = float("inf")
# ── 새 상수: (값, 출처). 숫자는 전부 설계서 1·2절에서 옮김. R = references/후보5_추가규칙_1차출처_20261106.md, BP = references/후보5_기초연금_사람3명_근거_20261106.md (행 번호).
NEW = {
    "refund_int": ({36: .20, 60: .30, 72: .40, 168: .70},
                   "F1~F3 해약환급금 = 원금 + 이자×비율(납부 횟수별), 이자 = 노령 기준이율 적립액 − 원금(이자 정의는 원문 미확인). "
                   "이 연구가 쓰는 납부 횟수만 둠(36·60·72회; 168회는 MDE 표 계산에만) — 중소기업중앙회 8899.or.kr 해약환급금 안내"
                   "(2026.1.1. 이후 가입자) 공시값. 전체 표는 재배포 조건 미확인이라 옮기지 않음, R 2-4절"),
    "nhis": (0.0719, "F4·N2 건보료율 7.19% — 건보법 시행령 §44(1만분의 719), R 128행"),
    "nhis_pension": (0.5, "N2 S_hi 연금소득 반영 50% — 건보법 시행규칙 §44②, R 135행. 건보 연금소득엔 §47의2 공제 미적용(references/law_소득세법_47의2_연금소득공제_20261106.md 22행)"),
    "nhis_etc": (1.0, "F4·N2 S_hi 기타소득 반영 100% — 시행규칙 §44②, R 135행"),
    "brackets": (((14e6, .06), (50e6, .15), (88e6, .24), (150e6, .35), (300e6, .38), (500e6, .40), (1e9, .42), (INF, .45)),
                 "N1 소득세법 §55① 8구간(시행 2026.7.1.) — R 53행"),
    "svc_ded": (((5, 0, 1e6, 0), (10, 5e6, 2e6, 5), (20, 15e6, 2.5e6, 10), (INF, 40e6, 3e6, 20)),
                "N1 근속연수공제 §48①1 (상한연수, 기본, 연당, 기준연수) — law.go.kr 이미지 설명 글, BP 23~28행, 국세청 문서 대조 전"),
    "conv_ded": (((8e6, 0, 1.0, 0), (70e6, 8e6, .60, 8e6), (100e6, 45.2e6, .55, 70e6), (300e6, 61.7e6, .45, 100e6), (INF, 151.7e6, .35, 300e6)),
                 "N1 환산급여공제 §48 (상한, 기본, 율, 기준) — 별지 제24호서식(2), R 43~51행"),
    "pen_ded": (((3.5e6, 0, 1.0, 0), (7e6, 3.5e6, .40, 3.5e6), (14e6, 4.9e6, .20, 7e6), (INF, 6.3e6, .10, 14e6)),
                "M1 연금소득공제 §47의2① (상한, 기본, 율, 기준) — references/law_소득세법_47의2_연금소득공제_20261106.md 12~17행(국가법령정보센터 현행 조문 대조 완료(2026.7.1. 시행본), 같은 파일 24~27행)"),
    "pen_ded_cap": (9e6, "M1 연금소득공제 한도 900만 원 — 같은 파일 10행"),
    "bp_sel": (2_470_000, "N3 선정기준액 단독 — 2026 고시 제2026-156호 §2, R 176행·BP 43행"),
    "bp_base": (349_700, "N3 기준연금액 — 같은 고시 §3, R 177행·BP 45행"),
    "bp_min": (34_970, "N3 소득역전 방지 최소액 = 기준연금액의 10% — 기초연금법 시행령 §11①, BP 90~93행"),
    "bp_link": ((524_550, 699_400, 874_250), "N3 국민연금 연계감액 경계(기준연금액 150%·200%·250%) — 기초연금법 §6·시행령 §10, BP 73~85행(금액은 계산)"),
    "bp_home_ded": ({"중소도시": 85e6, "대도시": 135e6, "농어촌": 72.5e6}, "N3 기본재산액(첫째 = 기준, 나머지 = 민감도, 주택 괄호 0 하한) — "
                    "「2026년 기초연금 사업안내」 인쇄 78쪽(원문 발췌는 재배포 조건 미확인으로 저장소에 없음, 쪽 번호만), 고시 §8·BP 48행"),
    "bp_fin_ded": (20e6, "N3 금융재산 공제 2,000만 원(금융재산 괄호 0 하한) — 사업안내 인쇄 78쪽, 고시 §9·R 180행·BP 49행"),
    "bp_conv": (0.04, "N3 재산 소득환산율 연 4% — 사업안내 인쇄 78쪽, 기초연금법 시행규칙 §4·R 171행·BP 54행"),
    "bp_int_ded": (40_000, "N3 이자소득 월 4만 원 공제(이자에서만, 음수면 0, L1) — 고시 §6의2, R 179행·BP 47행"),
    "bp_people": ({"A": (400_000, 1e8, 2e7), "B": (500_000, 4.5e8, None), "C": (1_200_000, 6e8, 3e8)},
                  "N3 사람 3명 (국민연금 월액, 주택, 금융재산) — 통계 분포 참고 가정값(원문 미확인), BP 262행. B 금융재산은 people()에서 풂"),
    "bp_b_ratio": (0.87, "N3 B = 시뮬레이션 저축 없이 2026년(자료 마지막 12개월) 평균 예금 금리로 소득인정액이 선정기준액의 87% — 회원 지시 2026-11-06"),
    "pen_limit": (15e6, "9번 사적연금 연금소득 1,500만 원 이하 = 분리·종합 선택(§14③9다), 초과 = 종합·15% 분리 선택(§64의4) — "
                        "확인: references/law_소득세법_59의3_57의2_129_21_14_20261010.md 203행, docs/ideas/본연구후보_20261027/후보5_제도규칙_1차출처_20261027.md 68·73행, R 206~207행"),
    "pen_sep": (0.15, "9번 1,500만 원 초과 분리과세 15%(+지방세 10%) — §64의4 제2호 가목(L2), 제도규칙 73행·R 207행"),
    "basic_ded": (1_500_000, "r3 M1 사람 (가)의 기본공제(본인) 150만 원 — 소득세법 §50①1, references/law_소득세법_50_기본공제_20261107.md 9~10행"
                             "(국가법령정보센터 현행 조문 대조 완료(2026.7.1. 시행본), 같은 파일 17~20행). 과세표준에 §50 공제가 들어감은 "
                             "references/law_소득세법_59의3_57의2_129_21_14_20261010.md 185행(§14②)"),
}
Q = lambda k: NEW[k][0]
AGE0 = 57                                           # 가상 인물(2026년 만 57세), 시작 해(k=0, 2026년)의 나이
WD0 = P("pension_open_months") // 12                # 연금 인출 시작 해 k=5(2031년, 62세 = 가입 5년 경과)
BP_K0 = 65 - AGE0                                   # 기초연금 첫 해 k=8(2034년, 65세) ~ 평가 해 k=13(70세)

# ── 결정표: cand5.DEC에서 D08 삭제(F3), D11 = 건보료 시나리오(F4·N2). N 스위치는 기본 켬.
DEC = {d: v for d, v in C.DEC.items() if d != "D08"}
DEC["D11"] = ("건보료 시나리오 — ★ 없음, 두 값 나란히(설계서 F4·N2)", {"S_lo": "lo", "S_hi": "hi"})
REC = {**{d: next(iter(c.values())) for d, (_, c) in DEC.items()}, "N1": True, "N2": True, "N3": True}
F_ONLY = {"N1": False, "N2": False, "N3": False}
PAIRS = {**C.PAIRS, "p62": C.PAIRS["p62"] + [("ps", "ny_close"), ("ny_close", "dep")]}   # 8번: 62세 폐업 칸
NOT_COMPUTED = {
    "국민연금 연계감액 중간 구간(52.5만~69.9만 원)": "§5 금액이 설계서에 없음 → 사람 3명은 이 구간 밖(assert)",
    "부트스트랩의 기초연금": "기초연금은 역사 경로 기준 셀만",
    "차이 중앙값의 신뢰구간(감사 r2 M6 부분)": "역사 경로가 겹쳐 독립 구간 2~11개뿐이라 구간을 내지 않음. 불확실성은 부트스트랩 손해 확률·n_eff·MDE로만 표시",
    "71세 이후 기초연금(감사 r2 M4)": "경로 자료가 70세(168개월)에서 끝나 71~75세 연금 수령·잔액을 시뮬레이션할 수 없음 → 65~70세 창만(연기판에 유리한 창, 한계에 적음)",
}
# 앞선 보고(2026-11-06) '판단이 필요한 것' 번호. 결과 문서 '가정' 절에 그대로 나감.
ASSUME = {
    "1. 소득평가액": "국민연금 + 연금저축 연금(K1) + 사업소득 b/12(가정 15) + max(예금 이자 − 월 4만 원, 0)(4만 원은 이자에서만, 고시 §6의2). "
                 "예금 이자: 사람이 처음 가진 금융재산 몫 = 사람을 정할 때 쓴 r̄(2026년 금리)로 고정(H1), 시뮬레이션이 만든 예금(인출 예금·환급/절세 예금·예금 상품) 몫 = 그 달 세전 예금 금리. "
                 "해마다 금융재산은 그해 첫날 잔액으로 고정. B 금융재산은 중소도시·사람 (가) 기준으로 풀고 지역 민감도에서도 그대로 둠. "
                 "r̄ 고정·그해 첫날 잔액·이자 산정 방식은 법령 근거가 아니라 설계 선택(감사 r2 L6). 사업소득을 공제 없이 전액 넣는 것, 금융재산 평가 시점, 이자 산정 방식의 원문 규정은 미확인",
    "2. 62~70세 납입": "동결판과 비교하려고 70세까지 납입을 계속하면서 62세부터 인출. 영향은 표 7 원인 분해, 대조는 가정 16 수령 연기판",
    "3. 인출 시점": "해마다 1월 초 납입 전에 인출, 첫 인출 2031년 1월. 70세 말 남은 잔액은 4.4%로 한 번에 평가(D07 방식, 1,500만 원 기준 적용 안 함). "
                 "근거: 연금수령연차 11년 이후에는 한도가 없어(시행령 §40의2④, R 200행) 한 해 1,500만 원 이하로 나눠 받으면 분리과세 4.4%로 받을 수 있음(시간가치 무시). "
                 "인출은 70세 비교에만 넣고 62세 평가는 기존 그대로. "
                 "⚠ 비대칭(감사 r2 M3): 해마다 꺼내는 돈에는 min(분리, 종합)(가정 9)을 쓰고 70세 잔액에는 4.4%만 써서, 잔액이 큰 연기판(가정 16)에 불리·기본판에 유리 "
                 "(인출분 실효세율 중앙값 (가) 1.56%·(나) 2.20%·(다) 4.39%, 감사 r2 측정). 잔액에도 같은 규칙(1,500만 원 이하 같은 몫으로 나눠 해마다, 시간가치 무시)을 쓴 민감도판 = 표 1-1·표 3·표 5-3",
    "4. 인출 순서": "세액공제 안 받은 원금이 먼저 나옴(K1 과세분만도 이 순서) — 시행령 §40의3① 확인(제도규칙 43행), 연금저축계좌설정약관 기준(하나은행 약관 신구대비표). "
                 "단 추가규칙 209·254행은 같은 조문을 '원문 못 엶 [미확인]'으로 적어 두 근거 파일이 어긋남(감사 r2 L1)",
    "5. 기초연금 기간·합산": "2034~2039년(65~70세) 6년치를 이자 없이 액면으로 더함",
    "6. 금융재산": "인출 예금·세액공제 환급/노란우산 절세 예금·예금 상품 잔액을 넣음. 노란우산 적립금은 기본판에서 넣지 않음 — 납입 중 부금의 금융재산 산입은 미확인(추가규칙 165행). "
                 "넣는 판(그해 첫날 적립금, 이자 없음)을 표 7-1에 나란히 둠(감사 r2 M5). 안 넣는 판의 노란우산 쪽 기초연금은 상한",
    "7. 건보료": "부과 기준 = 과세 대상분(연금소득, 기타소득금액), 연금소득공제 미적용. 62·70세 한꺼번에 평가하는 금액에도 연금소득 50%(D07 연금외16.5% 셀은 기타소득 100%). "
                "기준 셀 = S_lo(동결 기본값 0과 같아 대조 가능). S_hi = 상한 시나리오(공단 실제 부과 여부 미확인)",
    "8. 62세 폐업 수령": "p62에 노란우산 폐업 칸을 새로 둠(폐업 적용이율 적립, 퇴직소득세 뒤)",
    "9. 1,500만 원 기준": "해마다 꺼낸 과세분 x: 1,500만 원 이하 = 분리 5.5%·4.4%(1월 인출 시점 만 나이)와 종합과세 증분 중 작은 쪽(§14③9다 합산 선택), "
                       "초과 = 종합과세 증분과 15%(+지방세) 분리 중 작은 쪽(§64의4). 종합과세 증분 = [§55 8구간(b + 연금소득금액(국민연금 + x)) − §55(b + 연금소득금액(국민연금))] × 1.1, "
                       "연금소득금액 = 총연금액 − §47의2 연금소득공제(한도 900만; references/law_소득세법_47의2_연금소득공제_20261106.md, 국가법령정보센터 현행 조문 대조 완료(2026.7.1. 시행본)), "
                       "b = 그릇에서 §55 역산한 과세표준. 사람 (가)(b = 0)는 연금소득금액에서 기본공제 150만 원(§50①1, references/law_소득세법_50_기본공제_20261107.md, "
                       "국가법령정보센터 현행 조문 대조 완료(2026.7.1. 시행본))을 뺌 — 다른 소득이 기본공제를 쓰지 않는다는 가정(r3 M1). "
                       "65세부터 연금저축 세액공제 여력은 국민연금을 넣은 산출세액으로 다시 잡음(r3 M2). 노란우산 소득공제는 사업소득금액에서만 빠지므로(조특법 §86의3①, references/law_조특법_86의3_노란우산_20261107.md) "
                       "b > 0인 (나)(다)만 같은 여력(합산 과표의 한계세율)을 쓰고, b = 0인 (가)는 국민연금 몫 여력을 쓰지 않음(감사 r3 R3-M1). 국민연금은 65세(2034년)부터 연액 전액을 총연금액에 넣음"
                       "(2002년 이전 납입분 비과세는 넣지 않음 → 연금저축 세금 쪽으로 큰 값). 표 1~4·6·7(사람 (가)(나)(다)만)은 국민연금 0, A·B·C가 붙는 표 5·7-1은 그 사람 국민연금으로 세금을 다시 계산. "
                       "1,500만 원을 넘는 해는 '잔액 ÷ (11 − 연차)' 인출 규칙 때문이며, 법은 상한만 정하므로 한 해 1,500만 원 이하로 나눠 받는 길도 있음. 70세 말 잔액·D07 연금외 셀에는 적용 안 함",
    "10. MDE": "노란우산 해약 쌍(새 환급표)과 62세 폐업 쌍만 새로 계산. 결과 전에 고정한 값이 아님(동결 사전값과의 비교는 결과 문서 판독 범례)",
    "11. 연계감액 중간 구간": "§5 금액이 없어 넣지 않음. 사람 3명은 이 구간 밖이고, 들어오면 assert로 멈춤",
    "12. D07 연금외16.5% 셀": "해마다 꺼내는 돈에도 16.5%",
    "13. 근속연수공제 표": "law.go.kr 이미지 설명 글 값(BP 23~28행), 국세청 문서 대조 전",
    "14. 범위": "기초연금은 기준 셀·역사 경로만(부트스트랩 제외). 결과 문서는 결과 폴더에만, 그림·노트북 없음",
    "15. 사업소득(H3)": "(나)(다)는 65~70세에도 세액공제를 받으므로 그 과세표준 b(그릇에서 §55 역산)를 사업소득으로 보고 b/12를 소득평가액에 더함(예금·노란우산 쪽도 같은 b). "
                    "과세표준 ≤ 소득금액이라 하한값. (가)는 b = 0",
    "16. 수령 연기판(H2)": "62~70세 인출 없음, 70세 잔액 4.4%(가정 3 근거). 기초연금 계산에서 연금저축 연금소득 0, K2 넣음 판은 그해 첫날 연금저축 잔액이 금융재산. "
                         "S_lo에서 70세 연금저축에 닿는 N판 규칙은 인출뿐이라 연기판 연금저축 금액은 F판과 같다(코드 assert). 다른 것은 노란우산(퇴직소득세)과 기초연금뿐. "
                         "⚠ 가정 3의 잔액 세율 비대칭은 연기판에 불리(잔액 규칙 민감도판 = 표 1-1). 기초연금은 65~70세 창만이라 70세 이후 연금이 깎을 기초연금이 빠져 연기판에 유리(표 5 머리말)",
    "17. 원인 분해 단계 (나)": "인출액에 F판 세율(4.4%, D07 연금외 셀 16.5%). 5.5%·종합과세 선택·1,500만 원 처리는 단계 (다)",
}
# 감사 r1 낮음 중 고치지 않고 밝히는 것(결과 문서 '가정과 한계').
LIMITS = {
    "L4 기초연금 첫해": "2034년(65세)을 12개월 전부 지급으로 봄. 실제로는 생일 다음 달부터 → 양쪽 모두 조금 많게 잡힘. "
                     "국민연금 과세도 같음: 2034년 국민연금을 세금에서도 12개월로 계산(연금저축에 불리, 감사 r2 L4)",
    "L5 S_hi 범위": "장기요양보험료를 넣지 않음(요율 원문 미확인) → S_hi 증감이 그만큼 작게 나옴. 지역가입자 재산보험료 생략, 피부양자 아님을 가정. "
                   "또 건보 시행규칙 §44②는 이자소득도 반영하는데(추가규칙 135행) 예금 이자에는 건보료를 매기지 않음 → S_hi만 연금저축에 불리, 약 0.002/년 추정(감사 r2 L5)",
    "L10 인출 해의 시점": "그해 1월에 꺼낸 돈이 그해 연금소득과 1월 1일 금융재산(인출 예금)에 함께 잡힘 — 연금저축에 가장 불리한 시점 처리"
                        "(감사 r1에서 그해 인출분을 금융재산에서 빼 본 최대 차이 0.006, 이번 수정 뒤 다시 재지 않음)",
    "L11 인출 달": "인출은 경로 시작 달 기준(해마다 시작 달). D14 모든달 셀에서는 '1월 초 인출'과 다름. 기준 셀(1월 시작)은 영향 없음",
    "L12 수령 중 납입": "연금 수령을 시작한 계좌에 70세까지 계속 납입할 수 있는지 약관 근거를 확인하지 않음(가정 2). 70세 차이 대부분이 이 가정 줄기에서 나옴",
    "L14 표시 선택": "월 30만 원·주식 100% 표시(표 3·5·7)는 결과를 본 뒤의 표시 선택(동결 문서와 같은 선택). 다른 칸은 F/·N/ CSV",
    "L15 MDE 계산": "MDE는 인출 없는 적립으로 계산. N판 70세는 인출로 분산이 줄어 MDE가 실제보다 클 수 있음(판독 경계선)",
    "L17 사전등록": "설계서에 사전등록 기각 조건이 없고, 빠른 시험 결과값(r̄, f)이 설계서에 들어 있음 → 일부는 실행 뒤에 적음. 이 문서는 판정하지 않는 기술. "
                   "요약의 자동 문장(r1 H2 대체 문장을 r2에서 자동 생성으로 바꿈)과 그 규칙(최악 경로 비교·월 30만 원 기준·부트스트랩 비교·손해 건수)은 결과를 본 뒤 정했다(감사 r2 N-H1·L14)",
    "r2 L3 과세제외 확인 시점": "1월 인출 때 직전 해 세액공제 안 받은 원금까지 과세제외로 씀. 실제 확인은 이듬해 5월 신고 뒤(§40의3② 4호 '확인한 날부터') → 연금저축에 조금 유리",
    "r2 M4 기초연금 창": "기초연금은 65~70세(2034~2039)만 합산. 연기판의 70세 이후 연금소득이 깎을 기초연금이 빠져 연기판에 유리한 창이다. "
                       "수령 전 잔액: 「2026년 기초연금 사업안내」 인쇄 92~93쪽이 연금저축 '최종 잔액'을 금융재산으로, 개시 뒤에는 월 수령액만 연금소득으로 봄 "
                       "→ 사업안내 기준 칸 = 기본판 K2 안넣음·연기판 K2 넣음(K1 전액, 인쇄 70~71쪽). 71~75세로 넓힌 민감도는 경로 자료가 70세에서 끝나 계산하지 않음",
    "사업안내 12개월 초과 적금 이자 추가 공제": "사업안내 인쇄 70쪽: 가입기간 12개월 초과 적금·저축은 초과 개월 수만큼 연 최대 48만 원 이자 추가 공제. 코드 없음. "
                                         "시뮬레이션 예금은 12개월 사다리(D05)라 12개월 초과 조건에 해당하지 않아 결과는 같음. 사람이 처음 가진 금융재산이 12개월 초과 상품이면 "
                                         "이자소득이 월 최대 4만 원 작아짐 → 사람 A·B·C 모두 고유 금융재산 이자가 있어 영향받을 수 있음(상품 기간을 가정하지 않아 미반영·크기 미측정, 특히 B의 87% 경계)",
    "R3-L5 §51·§59의4": "§51①1 경로우대 추가공제(2039 과세연도)와 §59의4⑨ 표준세액공제 7만 원을 넣지 않음(원문 대조 안 함) — 연금저축 세금을 많게 잡는 보수 방향, 크기 작음",
    "R3-L6 잔액 세율·여력": "rem_tax·room65는 80세 이후 몫에도 4.4%를 씀(실제 3.3%). 종합과세를 고른 인출분 세액이 세액공제 여력에 빠짐 — 둘 다 연금저축에 불리한 보수 방향",
    "r2 M9 재현": "r3 코드는 실행 뒤 커밋됨(e01350d, 브랜치 candidate5-20261027). 문서 단계 수정은 그 뒤 커밋. run_meta.txt의 git_head·code_dirty와 "
                 "cand5p.py·_gen_cand5p.py·설계서·근거 파일·SOURCES.md의 sha256으로 대조",
}


def cells():
    """cand5.cells와 같은 규칙(기준 + 결정마다 추천 아닌 후보 하나씩), 결정표만 새것."""
    out = [("base", "", "★", dict(REC))]
    for d, (_, c) in DEC.items():
        out += [(f"{d}:{n}", d, n, {**REC, d: v}) for n, v in list(c.items())[1:]]
    return out


# ── F1~F3 해약환급금 ──────────────────────────────────────────────
def ny_refund(n: int, principal: float, interest):
    """2026.1.1. 이후 가입자 해약환급금 = 원금 + 이자×비율(이자 = 노령 기준이율 적립 − 원금).
    비율은 이 연구가 쓰는 납부 횟수만 있음 — 다른 n은 KeyError(전체 표는 8899.or.kr 해약환급금 안내)."""
    return principal + Q("refund_int")[n] * np.asarray(interest, float)


# ── N1 퇴직소득세 ────────────────────────────────────────────────
def tax_full(base):
    """§55① 8구간 산출세액(소득세분). 배열 가능."""
    b, t, lo = np.asarray(base, float), 0.0, 0.0
    for hi, r in Q("brackets"):
        t = t + (np.clip(b, lo, hi) - lo) * r; lo = hi
    return t


def band(x, table):
    """구간표 (상한, 기본, 율, 기준) → 기본 + 율×(x − 기준)."""
    x = np.asarray(x, float)
    return np.select([x <= row[0] for row in table], [b + r * (x - lo) for _, b, r, lo in table])


def retire_tax(income, months: int):
    """노란우산 퇴직소득세(지방세 포함). income = 공제금 − 소득공제 안 받은 납입 누계(조특법 §86의3③). 근속연수 = 납입월수/12 올림."""
    n = -(-months // 12)
    x = np.maximum(np.asarray(income, float) - band(n, Q("svc_ded")), 0) * 12 / n
    return tax_full(x - band(x, Q("conv_ded"))) / 12 * n * P("local")


def pen_income(y):
    """총연금액 y → 연금소득금액 = y − 연금소득공제(§47의2①, 한도 900만)."""
    y = np.asarray(y, float)
    return y - np.minimum(band(y, Q("pen_ded")), Q("pen_ded_cap"))


def base_with(b: float, y):
    """과표 b인 사람에 총연금액 y를 더한 과세표준. b = 0(사람 (가))이면 기본공제 150만을 연금소득금액에서 뺌(r3 M1, 다른 소득 0 가정)."""
    pi = pen_income(y)
    return b + (np.maximum(pi - Q("basic_ded"), 0) if b == 0 else pi)


def room65(room: float, nps_year: float) -> float:
    """r3 M2: 65세(k ≥ BP_K0)부터 세액공제 여력 = 그릇 + §55(b + 과표화(국민연금)) − §55(b). 연금저축 세액공제·노란우산 절세 둘 다 이 값."""
    b = C.base_for(room)
    return float(room + tax_full(base_with(b, nps_year)) - tax_full(b))


def wd_tax(x, room: float, r: float, nps_year: float = 0.0):
    """해마다 꺼낸 연금소득 과세분 x의 세금(지방세 포함). 종합과세 증분 = §55(b + 연금소득금액(국민연금 + x)) − §55(b + 연금소득금액(국민연금)),
    b = 그릇에서 §55 역산한 과표, nps_year = 그해 국민연금 연액(H3). 1,500만 원 이하 = 분리 r과 종합 중 작은 쪽(M2), 초과 = 15% 분리와 종합 중 작은 쪽(§64의4).
    (가)는 기본공제 150만 반영(r3 M1, base_with)."""
    x, b = np.asarray(x, float), C.base_for(room)
    comb = (tax_full(base_with(b, nps_year + x)) - tax_full(base_with(b, nps_year))) * P("local")
    return np.minimum(comb, np.where(x > Q("pen_limit"), Q("pen_sep") * P("local"), r) * x)


def rem_tax(rem, room: float, r: float, nps_year: float = 0.0):
    """r3 M3 민감도: 70세 잔액을 1,500만 원 이하 같은 몫 n개로 나눠 해마다 받는다고 보고(시간가치 무시) 몫마다 wd_tax(min(분리, 종합)) × n."""
    rem = np.asarray(rem, float); n = np.maximum(np.ceil(rem / Q("pen_limit")), 1)
    return n * wd_tax(rem / n, room, r, nps_year)


# ── N3 기초연금 ──────────────────────────────────────────────────
def basic_pension(nps: float, pen, home: float, fin, home_ded: float, intr=0.0, biz=0.0):
    """월 기초연금(2026 고시 값)과 소득인정액. pen = 연금저축 월 연금, intr = 월 예금 이자, biz = 월 사업소득(H3),
    fin = 금융재산(배열 가능, 브로드캐스트), 부채 0. 4만 원 공제는 이자에서만(L1).
    재산 소득환산 = max(max(주택 − 기본재산액, 0) + max(금융 − 2천만, 0) − 부채, 0) × 4% ÷ 12 — 각 괄호 0 하한(사업안내 인쇄 78쪽, 2026-11-07 회원 지시)."""
    ia = (nps + pen + biz + np.maximum(intr - Q("bp_int_ded"), 0)
          + np.maximum(max(home - home_ded, 0) + np.maximum(fin - Q("bp_fin_ded"), 0), 0) * Q("bp_conv") / 12)
    lo, hi, _ = Q("bp_link")
    assert not lo < nps <= hi, "연계감액 중간 구간: §5 금액 미입력"
    full, sel = (Q("bp_base") if nps <= lo else np.nan), Q("bp_sel")    # nps > hi: A급여 필요 → 선정기준액 초과일 때만 통과
    amt = np.where(ia > sel, 0.0, np.where(ia + full > sel, np.maximum(sel - ia, Q("bp_min")), full))
    assert not np.isnan(amt).any(), "A급여 자료가 필요한 사람이 선정기준액 이하"
    return amt, ia


def people(rbar: float) -> dict:
    """사람 A·B·C (국민연금, 주택, 금융재산, 그 금융재산의 월 이자 = 금융재산 × rbar 고정(H1)). rbar = 2026년 평균 예금 월 금리(세전).
    B 금융재산 f: 국민연금 + (f·rbar − 4만) + (주택 − 기본재산액 + f − 2천만)×4%/12 = 87%×선정기준액 → f = 남는 금액 ÷ (rbar + 4%/12).
    (f·rbar ≥ 4만, f ≥ 2천만일 때의 식 — 아래 assert가 소득인정액을 다시 계산해 확인)"""
    p, hd = dict(Q("bp_people")), Q("bp_home_ded")["중소도시"]
    nps, home, _ = p["B"]; cv = Q("bp_conv") / 12; want = Q("bp_b_ratio") * Q("bp_sel")
    p["B"] = (nps, home, (want - (nps - Q("bp_int_ded")) - (home - hd - Q("bp_fin_ded")) * cv) / (rbar + cv))
    p = {b: (n, h, f, f * rbar) for b, (n, h, f) in p.items()}
    got = {b: basic_pension(n, 0.0, h, f, hd, i0) for b, (n, h, f, i0) in p.items()}
    assert abs(got["B"][1] - want) < 1e-6 and got["A"][0] > 0 and got["C"][0] == 0, got
    return p


def side_at(G: np.ndarray, t: int, amt) -> np.ndarray:
    """cand5.side_account의 중간 시점판: 달 t 말까지 도착한 환급·절세 예금 잔액. amt = 해마다 금액(길이 = 공제받는 해 수, r3 M2로 해마다 다를 수 있음)."""
    v = np.zeros(G.shape[0])
    for k, a in enumerate(amt):
        if 12 * k + 16 <= t:
            v += a * G[:, t] / G[:, 12 * k + 16]
    return v


def side_yrs(G: np.ndarray, H: int, amt) -> np.ndarray:
    """cand5.side_account와 같은 식, 해마다 금액 amt(배열)판. r3 M2의 65세 이후 추가분에만 씀(그 밖은 cand5.side_account 그대로 → 회귀 비트 단위)."""
    v = np.zeros(G.shape[0])
    for k, a in enumerate(amt):
        if a:
            v += a * (G[:, H - 1] / G[:, 12 * k + 16] if 12 * k + 16 <= H - 1 else 1.0)
    return v


# ── 적립: cand5.accumulate + N3 인출 경로 ───────────────────────────
def ps_withdraw(eq, bd, m: float, w_eq: float, mon0=None, wd0: int = WD0):
    """연금저축 잔액(N3): k ≥ wd0 해마다 첫 달 납입 전에 잔액 ÷ (11 − 연차) 인출(연차 = k − wd0 + 1, 시행령 §40의2③ 한도×1.2 안).
    반환 (마지막 달 말 잔액 (n,), 인출액 W (n, 해), 인출 직후 잔액 R (n, 해)). 납입·1월 리밸런싱·수익 순서는 cand5.accumulate와 같음."""
    eq = np.atleast_2d(eq)
    bd = np.zeros_like(eq) if w_eq == 1 else np.atleast_2d(bd)
    n, T = eq.shape
    E, B = np.zeros(n), np.zeros(n)
    W, R = np.zeros((n, max(T // 12 - wd0, 0))), np.zeros((n, max(T // 12 - wd0, 0)))
    mon0 = np.ones(n, int) if mon0 is None else np.asarray(mon0)
    for t in range(T):
        if t % 12 == 0 and t // 12 >= wd0:
            j = t // 12 - wd0; f = 1 / (10 - j)
            W[:, j] = f * (E + B); E, B = E * (1 - f), B * (1 - f); R[:, j] = E + B
        E = E + w_eq * m; B = B + (1 - w_eq) * m
        if w_eq < 1:
            jan = (mon0 - 1 + t) % 12 == 0; tot = E + B
            E, B = np.where(jan, w_eq * tot, E), np.where(jan, (1 - w_eq) * tot, B)
        E = E * (1 + eq[:, t]); B = B * (1 + bd[:, t])
    return E + B, W, R


def accumulate(eq, bd, dep, m, w_eq, o, mon0=None, H=None) -> dict:
    acc = C.accumulate(eq, bd, dep, m, w_eq, o, mon0)
    if o["N3"] and H == P("H70"):
        if o.get("defer"):                               # H2 수령 연기판: 인출 0, '인출 직후 잔액' = 그해 첫날 잔액
            ps, yrs = acc["ps"], H // 12 - WD0
            acc["wd"] = (ps[:, -1], np.zeros((len(ps), yrs)), ps[:, [12 * (WD0 + j) - 1 for j in range(yrs)]])
        else:
            acc["wd"] = ps_withdraw(eq, bd, m, w_eq, mon0)
        acc["dep_r"] = np.atleast_2d(dep)                # 기초연금 이자(시뮬레이션 예금 몫): 그 달 세전 예금 금리(D05 모형)
    return acc


# ── 평가: cand5.evaluate와 같은 골격, 바뀐 곳만 다름 ─────────────────────
def evaluate(acc: dict, m: float, room: float, H: int, mode: str, o: dict, bp: dict | None = None) -> dict:
    """N 스위치를 모두 끄면 노란우산 해약 열 밖은 cand5.evaluate와 같은 연산(자가점검에서 대조).
    bp = people() 결과(주면 p70·N3에서 기초연금 계산). o["wtax"] = "F"면 해마다 꺼낸 돈에 F판 세율(표 7 원인 분해 단계 나, M3).
    o["defer"] = True면 수령 연기판(H2, accumulate에서 인출 0)."""
    i, Y = H - 1, H // 12
    rate, cap = o["D02"]
    c, s = C.pension_credit(12 * m, room, rate), (C.ny_saving(12 * m, room, cap) if o["D12"] else 0.0)
    cy = Y if (mode != "wd" or o["D13"]) else Y - 1
    cyn = Y if (mode == "p70" or o["D13"]) else Y - 1
    nonded = (cy * (12 * m - c / rate) + (Y - cy) * 12 * m) if o["D18"] else 0.0
    k = P("local") if o["D06"] else 0.0
    side_p, side_n, side_nc = (C.side_account(acc["G"], H, k * x, y) for x, y in ((c, cy), (s, cy), (s, cyn)))
    prin = H * m
    ded = min(12 * m, cap, C.base_for(room)) if o["D10"] == "actual" else min(12 * m, cap)
    over = cyn * (12 * m - ded) + (Y - cyn) * 12 * m
    V = acc["ps"][:, i]; taxable = np.maximum(V - nonded, 0)
    hi = o["D11"] == "hi"
    prem = lambda x, share, on=True: Q("nhis") * share * x if (hi and on) else 0.0   # 건보료 1년치(소득 × 반영률 × 7.19%)
    # ponytail: 건보료는 이듬해 1년치로 근사(설계서 N2). 평가 시점 뒤에 내는 몫은 액면으로 뺌.
    etc = o["D07"] != "pen"
    share = Q("nhis_etc") if (mode == "wd" or etc) else Q("nhis_pension")

    def ny_net(ref):
        x = np.maximum(ref - over, 0)                                           # 기타소득금액 = 해약금 − 공제 안 받은 원금(F4)
        return ref - C.ny_cancel_tax(x, room, o["D17"]) - prem(x, Q("nhis_etc")) + side_nc

    res = {"contrib": prin, "dep": acc["dp"][:, i]}
    Yb, Cb = acc["ny_old"][:, i], acc["ny_close"][:, i]
    close = lambda: Cb - (retire_tax(Cb - over, H) if o["N1"] else 0.0) + side_n   # 폐업 수령(폐업 적용이율 적립, N1 퇴직소득세)
    if mode == "wd":
        res["ps"] = V - P("etc") * taxable + side_p - prem(taxable, share, o["N2"])
        res["ny_cancel"] = ny_net(ny_refund(H, prin, Yb - prin))
        res["ny_close"] = close()
        return res
    tr = P("pen62") if mode == "p62" else P("pen70")
    t_rate = P("etc") if etc else tr
    if mode == "p62":
        res["ps"] = V - t_rate * taxable + side_p - prem(taxable, share, o["N2"])
        res["ny_cancel"] = ny_net(ny_refund(H, prin, Yb - prin))
        res["ny_locked"] = Yb + side_n
        res["ny_close"] = close()
        return res
    res["ny_old"] = Yb - (retire_tax(Yb - over, H) if o["N1"] else 0.0) + side_n
    if not o["N3"]:
        res["ps"] = V - t_rate * taxable + side_p - prem(taxable, share, o["N2"])
        return res
    # N3: 62세(k=WD0)부터 해마다 인출 → 세후는 예금으로. 과세제외 원금이 먼저 나옴(시행령 §40의3① 확인, 연금저축계좌설정약관 기준).
    Vn, W, R = acc["wd"]; G = acc["G"]; n = len(Vn); flat = etc or o.get("wtax") == "F"
    nd = np.where(np.arange(Y) < cy, 12 * m - c / rate, 12 * m) if o["D18"] else np.zeros(Y)

    def path(nps: float = 0.0):
        """(연금저축 70세 금액, 해마다 과세분 TX, 인출 예금 DW, 해마다 세액공제 cv, 해마다 노란우산 절세 sv, 노란우산 노령 70세 금액).
        nps = 국민연금 월액 — 65세(k=BP_K0)부터 종합소득에 들어감(H3). 그해부터 세액공제 여력도 국민연금을 넣은 산출세액(r3 M2):
        연금저축 세액공제·과세제외 원금·환급 예금은 여력 r65를 씀(예금 쪽은 세액공제 없음). 노란우산 절세·실제 소득공제(퇴직소득세)는 사업소득금액 b가
        있을 때만 r65, b = 0이면 그릇 그대로(R3-M1, 조특법 §86의3①).
        o["rem"] = "min"이면 70세 잔액도 rem_tax(1,500만 원 이하로 나눠 min(분리, 종합), r3 M3 민감도)."""
        yrs = np.arange(Y); cv, sv = np.where(yrs < cy, c, 0.0), np.where(yrs < cyn, s, 0.0)
        nd_, sp, ny = nd, side_p, res["ny_old"]
        if nps:
            r65 = room65(room, 12 * nps); lp, ln = (yrs >= BP_K0) & (yrs < cy), (yrs >= BP_K0) & (yrs < cyn)
            # R3-M1: 노란우산 소득공제는 사업소득금액에서만 뺀다(조특법 §86의3①) → b = 0(사람 (가))이면 국민연금 몫 여력을 쓰지 않음(rn = 그릇).
            #   b > 0이면 공제가 b 안에 다 들어가(assert) 합산 과표의 한계세율 그대로.
            b0 = C.base_for(room); rn = r65 if b0 > 0 else room
            assert not b0 or min(12 * m, cap) <= b0, "노란우산 공제가 사업소득금액보다 큼"
            c65, s65 = C.pension_credit(12 * m, r65, rate), (C.ny_saving(12 * m, rn, cap) if o["D12"] else 0.0)
            cv2, sv2 = np.where(lp, c65, cv), np.where(ln, s65, sv)
            nd_ = np.where(lp, 12 * m - c65 / rate, nd) if o["D18"] else nd
            sp = side_p + side_yrs(G, H, k * (cv2 - cv))
            d65 = min(12 * m, cap, C.base_for(rn)) if o["D10"] == "actual" else ded
            over65 = over - ln.sum() * (d65 - ded)
            ny = Yb - (retire_tax(Yb - over65, H) if o["N1"] else 0.0) + side_n + side_yrs(G, H, k * (sv2 - sv))
            cv, sv = cv2, sv2
        used, dw, due, TX, DW = np.zeros(n), np.zeros(n), 0.0, np.zeros_like(W), np.zeros_like(W)
        for j in range(W.shape[1]):
            kk = WD0 + j; t = 12 * kk
            free = np.minimum(W[:, j], nd_[:kk].sum() - used); used = used + free
            TX[:, j] = W[:, j] - free
            r = P("pen62") if AGE0 + kk - 1 < 70 else P("pen70")   # L2: 1월 인출 = 그해 생일 전 → 만 나이 AGE0 + kk − 1(§129 '연금수령일 현재')
            tax = t_rate * TX[:, j] if flat else wd_tax(TX[:, j], room, r, 12 * nps * (kk >= BP_K0))
            dw = (dw * G[:, t - 1] / G[:, t - 13] if j else dw) - due + W[:, j] - tax
            due = prem(TX[:, j], share, o["N2"]); DW[:, j] = dw
        rem = np.maximum(Vn - (nd_.sum() - used), 0)
        rtax = rem_tax(rem, room, P("pen70"), 12 * nps) if (o.get("rem") == "min" and not flat) else t_rate * rem
        ps = (Vn - rtax + dw * G[:, i] / G[:, 12 * (WD0 + W.shape[1] - 1) - 1] - due
              - prem(rem, share, o["N2"]) + sp)
        return ps, TX, DW, cv, sv, ny

    res["ps"], TX = path()[:2]
    res["n_over1500"] = (TX > Q("pen_limit")).sum(axis=1)
    if bp:
        # ponytail: (나)(다)의 사업소득 = 과세표준 b(하한값, 과세표준 ≤ 소득금액). 실제 소득금액 자료가 생기면 그 값으로 바꿈.
        res["bp"] = _bp(acc, k, W, R, path, C.base_for(room) / 12, bp)
    return res


def _bp(acc, k, W, R, path, biz, ppl) -> dict:
    """65~70세(k=BP_K0..13) 기초연금 합계(월액 12개월치, 액면). 키 (사람, K1, K2, 지역) → ({ps, dep, ny_old, ny_old_in}, 그 사람 국민연금으로 다시 계산한
    연금저축 70세 금액, 같은 국민연금·여력으로 다시 계산한 노란우산 노령 70세 금액(r3 M2)).
    K1 True = 과세 대상분만 소득, False = 받은 연금 전액. K2 True = 연금저축 잔액을 금융재산에 넣음(이자는 안 붙음).
    금융재산 = 사람 고유 금융재산 + 그 상품 때문에 생긴 예금(인출 예금·환급/절세 예금·예금 상품), 그해 첫날 잔액.
    이자 = 고유 금융재산 몫은 people()의 r̄ 고정 이자 i0(H1) + 시뮬레이션 예금 × 그 달 세전 예금 금리. biz = 월 사업소득(H3).
    노란우산 적립금: ny_old = 안 넣음(산입 여부 미확인, 기본), ny_old_in = 그해 첫날 적립금을 금융재산에 넣음(r3 M5, 이자는 안 붙음)."""
    G, dp, rr, out = acc["G"], acc["dp"], acc["dep_r"], {}
    for b, (nps, home, fin0, i0) in ppl.items():
        psb, TX, DW, cv, sv, nyb = path(nps)
        for k1 in (True, False):
            for k2 in (False, True):
                for reg, hd in Q("bp_home_ded").items():
                    # 한 해 12개월 합: 시뮬레이션 예금 f(이자 붙음), 금융재산 고유 + f + extra, 월 연금 pen. 세 쪽 모두 같은 nps·biz(이 람다 하나로만 계산)
                    yr = lambda pen, f, extra=0.0: basic_pension(nps, pen, home, fin0 + (f + extra)[:, None], hd,
                                                                 i0 + f[:, None] * rr[:, 12 * kk:12 * kk + 12], biz)[0].sum(axis=1)
                    tot = {"ps": 0.0, "dep": 0.0, "ny_old": 0.0, "ny_old_in": 0.0}
                    for kk in range(BP_K0, BP_K0 + 6):
                        j, t = kk - WD0, 12 * kk - 1
                        pen = ((TX[:, j] if k1 else W[:, j]) / 12)[:, None]
                        sn = side_at(G, t, k * sv)
                        tot["ps"] = tot["ps"] + yr(pen, DW[:, j] + side_at(G, t, k * cv), R[:, j] if k2 else 0.0)
                        tot["dep"] = tot["dep"] + yr(0.0, dp[:, t])
                        tot["ny_old"] = tot["ny_old"] + yr(0.0, sn)
                        tot["ny_old_in"] = tot["ny_old_in"] + yr(0.0, sn, acc["ny_old"][:, t])
                    out[(b, "과세분만" if k1 else "전액", "넣음" if k2 else "안넣음", reg)] = (tot, psb, nyb)
    return out


def run(r: pd.DataFrame, o: dict, H: int, mode: str, st=None, bp: dict | None = None):
    """cand5.run과 같은 긴 표 + (bp=True, p70·N3) 기초연금 긴 표. 반환 (표, 기초연금 표 또는 None)."""
    eq, bd, dep, keys = C.windows(r, C.starts(r, o) if st is None else st, H)
    rows, bps = [], []
    for an, w in P("w_eq").items():
        if w < 1 and (not len(keys) or np.isnan(bd).any()):
            continue
        for m in P("monthly"):
            acc = accumulate(eq, bd, dep, m, w, o, [int(x[5:]) for x in keys], H)
            for pn, room in C.rooms(o).items():
                e = evaluate(acc, m, room, H, mode, o, bp)
                bpd = e.pop("bp", None)
                d = pd.DataFrame({x: v for x, v in e.items() if np.ndim(v)}); d["contrib"] = e["contrib"]
                d.insert(0, "path", keys); d.insert(1, "asset", an); d.insert(2, "m", m); d.insert(3, "person", pn)
                rows.append(d)
                for (b, k1, k2, reg), (v, psb, nyb) in (bpd or {}).items():
                    # 연금저축 = 그 사람 국민연금으로 다시 낸 세금(H3), 노란우산 = 같은 국민연금으로 다시 잡은 세액공제 여력(r3 M2)
                    val = {"ps": psb, "dep": e["dep"], "ny_old": nyb, "ny_old_in": nyb}
                    bps.append(pd.DataFrame({"path": keys, "asset": an, "m": m, "person": pn, "b": b, "K1": k1, "K2": k2, "region": reg,
                                             "contrib": e["contrib"], "ps_nps": psb, "ny_nps": nyb, **{f"bp_{x}": y for x, y in v.items()},
                                             **{x: val[x] + y for x, y in v.items()}}))
    df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return df, (pd.concat(bps, ignore_index=True) if bps else None)


def bp_stats(bp: pd.DataFrame) -> pd.DataFrame:
    """기초연금 포함 70세 금액의 손해 통계 + 기초연금 차이 중앙값(÷누적납입)."""
    by = ["asset", "m", "person", "b", "K1", "K2", "region"]
    out = []
    for a, b in C.PAIRS["p70"]:
        g = ((bp[f"bp_{a}"] - bp[f"bp_{b}"]) / bp.contrib).groupby([bp[x] for x in by]).median().rename("bp_gap_median").reset_index()
        out.append(C.loss_stats(bp, a, b, by).merge(g, on=by).assign(쌍=f"{a}<{b}"))
    return pd.concat(out, ignore_index=True)


def mde_table(r: pd.DataFrame) -> pd.DataFrame:
    """cand5.mde_table과 같음. 노란우산 해약 값만 새 환급표(F1~F3)."""
    o = {**REC, "D04": 0.0}
    rows = []
    for kk, H in C.HS.items():
        eq, bd, dep, keys = C.windows(r, list(r.index), H)
        n = C.nstat(r, len(keys), H)
        for an, w in P("w_eq").items():
            if w < 1 and np.isnan(bd).any():
                continue
            a = C.accumulate(eq, bd, dep, 1.0, w, o, [int(x[5:]) for x in keys])
            y = a["ny_old"][:, -1]
            v = {"ps": a["ps"][:, -1], "dep": a["dp"][:, -1], "ny_old": y, "ny_locked": y, "ny_close": a["ny_close"][:, -1],
                 "ny_cancel": ny_refund(H, H, y - H)}
            for x, z in PAIRS[kk]:
                sd =float(np.std((v[x] - v[z]) / H, ddof=1)); ok = sd > 1e-12 and n["n_eff"] > 0
                rows.append({"비교": kk, "쌍": f"{x}<{z}", "asset": an, "sd": sd, **n,
                             "mde": C.P9.mde(sd, n["n_eff"]) if ok else np.nan, "비교불가": not ok})
    return pd.DataFrame(rows)


def constants_table() -> pd.DataFrame:
    a = C.constants_table()
    a = a[~a["키"].str.startswith(("refund_", "D08 ", "D11 "))]
    b = [{"키": x, "값": str(v), "결정": "", "출처": s} for x, (v, s) in NEW.items()]
    d = [{"키": f"D11 후보:{x}", "값": v, "결정": "D11", "출처": ("기준셀(★ 없음) " if i == 0 else "") + DEC["D11"][0]}
         for i, (x, v) in enumerate(DEC["D11"][1].items())]
    e = [{"키": "AGE0", "값": str(AGE0), "결정": "", "출처": "가상 인물: 시작 해(k=0, 2026년)에 만 57세. 1월 인출 세율은 만 나이 AGE0 + k − 1(L2)"},
         {"키": "WD0", "값": str(WD0), "결정": "", "출처": "연금 인출 첫 해 k(2031년, 가입 5년 경과) = pension_open_months ÷ 12"},
         {"키": "BP_K0", "값": str(BP_K0), "결정": "", "출처": "기초연금·국민연금 첫 해 k(2034년, 65세; 이 인물의 출생 구간 노령연금 개시 65세, BP 133행)"},
         {"키": "연금수령한도 배수", "값": "1.2", "결정": "", "출처": "시행령 §40의2③ 평가액 ÷ (11 − 연차) × 120/100, R 199행. 인출 규칙 잔액 ÷ (11 − 연차)는 이 한도 안이라 코드에서 따로 쓰지 않음"}]
    return pd.concat([a, pd.DataFrame(b + d + e)], ignore_index=True)


def _check() -> None:
    # F1~F3 환급표
    assert abs(ny_refund(36, 100, 10) - 102) < 1e-12 and abs(ny_refund(60, 100, 10) - 103) < 1e-12
    assert abs(ny_refund(72, 100, 10) - 104) < 1e-12 and abs(ny_refund(168, 100, 10) - 107) < 1e-12
    # §55 8구간: 3구간 안에서는 cand5.tax55와 같음, 2억 = 84만 + 540만 + 912만 + 2,170만 + 1,900만
    for x in (5e6, 14e6, 3e7, 88e6):
        assert abs(tax_full(x) - C.tax55(x)) < 1e-6
    assert abs(tax_full(2e8) - 56_060_000) < 1e-6
    # N1 손계산. 근속 3년, 퇴직소득 1,000만: 공제 300만 → 환산 2,800만 → 환산공제 800만+60%×2,000만 = 2,000만 → 과표 800만
    #   → 6% = 48만 → ÷12×3 = 12만 → 지방세 포함 132,000
    assert abs(retire_tax(1e7, 36) - 132_000) < 1e-6
    # 근속 14년(168회), 퇴직소득 1억: 공제 1,500만+250만×4 = 2,500만 → 환산 7,500만×12/14 = 64,285,714.29
    #   → 환산공제 800만 + 60%×56,285,714.29 = 41,771,428.57 → 과표 22,514,285.71 → 84만 + 15%×8,514,285.71 = 2,117,142.86
    #   → ÷12×14 = 2,470,000 → ×1.1 = 2,717,000
    assert abs(retire_tax(1e8, 168) - 2_717_000) < 1e-6
    assert retire_tax(2e6, 36) == 0 and abs(band(10, Q("svc_ded")) - 15e6) < 1e-9 and abs(band(3e8, Q("conv_ded")) - 151.7e6) < 1e-6
    # N3 손계산(설계서 4절, 시험 금리 연 3% = 월 0.0025, 중소도시 기본재산액 8,500만):
    #   A: 40만 + 2천만×0.0025(5만) − 4만 = 41만, 재산 (1억 − 8,500만 + 2천만 − 2천만)×4%/12 = 5만 → 46만 → 349,700
    #   B: 금융재산 f = (247만×0.87 − 46만 − (4.5억 − 8,500만 − 2천만)×4%/12) ÷ (0.0025 + 4%/12) = 538,900 ÷ 0.0058333… = 92,382,857.14
    #      → 소득인정액 2,148,900, + 349,700 > 247만 → 247만 − 2,148,900 = 321,100
    #   C: 120만 + 75만 − 4만 = 191만, 재산 (6억 − 8,500만 + 3억 − 2천만)×4%/12 = 265만 → 456만 > 247만 → 0
    hd, ppl = Q("bp_home_ded")["중소도시"], people(0.0025)
    assert abs(ppl["B"][2] - 538_900 / (0.0025 + 0.04 / 12)) < 1e-6 and abs(ppl["B"][2] - 92_382_857.142857) < 1e-3
    for b, want, ia_want in (("A", 349_700, 460_000), ("B", 321_100, 2_148_900), ("C", 0, 4_560_000)):
        nps, home, fin, i0 = ppl[b]; amt, ia = basic_pension(nps, 0.0, home, fin, hd, i0)
        assert abs(amt - want) < 1e-6 and abs(ia - ia_want) < 1e-6 and i0 == fin * 0.0025, (b, amt, ia)
    bB = lambda pen: float(basic_pension(500_000, pen, 4.5e8, ppl["B"][2], hd, ppl["B"][3])[0])
    assert abs(bB(30_000) - 291_100) < 1e-6        # B 경계: 연금 3만 원 → 기초연금 3만 원 감소
    assert abs(bB(300_000) - 34_970) < 1e-6        # 소득인정액 2,448,900 → 247만 − 2,448,900 = 21,100 < 최소액
    assert bB(330_000) == 0                        # 소득인정액 2,478,900 > 247만 → 0
    assert abs(basic_pension(400_000, 0.0, 1e8, 2e7, hd, 10_000)[1] - 450_000) < 1e-6   # L1 4만 원은 이자에서만: 40만 + max(1만 − 4만, 0) + 재산 5만
    assert abs(basic_pension(400_000, 0.0, 1e8, 1e7, hd)[1] - 450_000) < 1e-6           # L3 금융 1천만: 공제 남는 1천만이 주택 몫을 깎지 않음 → 재산 1,500만×4%/12
    # 각 괄호 0 하한(사업안내 인쇄 78쪽): 대도시 기본재산액 1억3,500만, 집 1억, 이자 r̄ = 월 0.25%
    #   금융 2천만 → max(1억 − 1억3,500만, 0) + max(0, 0) = 0 → 재산 환산 0원, 소득인정액 = 40만 + (5만 − 4만) = 41만
    #   금융 3천만 → 0 + 1천만 = 1천만 × 4%/12 = 33,333.33 (옛 식 max(−3,500만 + 1천만, 0) = 0)
    hm = Q("bp_home_ded")["대도시"]
    assert abs(basic_pension(400_000, 0.0, 1e8, 2e7, hm, 2e7 * .0025)[1] - 410_000) < 1e-6
    assert abs(basic_pension(400_000, 0.0, 1e8, 3e7, hm, 3e7 * .0025)[1] - (400_000 + 35_000 + 1e7 * .04 / 12)) < 1e-6
    # 노란우산 소득공제 한도(조특법 §86의3①, 2025. 3. 14. 개정, references/law_조특법_86의3_노란우산_20261107.md 10~13행):
    #   사업소득금액 4천만 이하 600만. 사람 (가)(나)(다)(D01 후보 포함)의 과표 b ≤ 4천만 → 기준 셀 D02 한도 600만과 같음
    assert REC["D02"][1] == 6e6 and all(C.base_for(x) <= 4e7 for x in (*C.rooms(REC).values(), *DEC["D01"][1].values()))
    # H3 사업소득 b/12: (다) 그릇 200만 → b = 1,400만 + (200만 − 84만)/15% = 21,733,333.33 → 월 1,811,111.11
    #   A: 46만 + 1,811,111.11 = 2,271,111.11 > 2,120,300 → 247만 − 2,271,111.11 = 198,888.89
    #   B (나) 그릇 50만 → b = 833만 → 월 694,444.44 → 2,148,900 + 694,444.44 > 247만 → 0
    A, B = ppl["A"], ppl["B"]
    assert abs(basic_pension(A[0], 0.0, A[1], A[2], hd, A[3], C.base_for(2e6) / 12)[0] - 198_888.888889) < 1e-3
    assert basic_pension(B[0], 0.0, B[1], B[2], hd, B[3], C.base_for(5e5) / 12)[0] == 0
    # M1 연금소득공제 §47의2: 1,800만 → 공제 630만 + 400만×10% = 670만 → 연금소득금액 1,130만
    #   (가) 과표 0 → r3 M1 기본공제 150만 → 980만×6%×1.1 = 646,800 < 분리 297만 (r2까지는 1,130만×6.6% = 745,800)
    #   (다) b 21,733,333 → 15%×1,130만×1.1 = 1,864,500 < 297만 (기본공제는 b에 이미 반영)
    assert abs(wd_tax(18e6, 0, .055) - 646_800) < 1e-6 and abs(wd_tax(18e6, 2e6, .055) - 1_864_500) < 1e-6
    # M2 1,500만 이하도 종합과 비교: 1,000만 → 공제 490만 + 300만×20% = 550만 → 450만
    #   (가) (450만 − 150만)×6%×1.1 = 198,000 < 분리 55만 / (다) 15%×450만×1.1 = 742,500 > 분리 550,000 → 550,000
    #   1,500만 (가): 공제 640만 → 860만 − 150만 = 710만×6%×1.1 = 468,600 < 825,000
    assert abs(wd_tax(10e6, 0, .055) - 198_000) < 1e-6 and abs(wd_tax(10e6, 2e6, .055) - 550_000) < 1e-6
    assert abs(wd_tax(15e6, 0, .055) - 468_600) < 1e-6
    # H3 국민연금 포함 증분: 국민연금 600만 + 1,000만 = 1,600만 → 공제 650만 → 950만; 600만만 → 공제 450만 → 150만
    #   (가) 기본공제 150만: max(950만 − 150만, 0) − max(150만 − 150만, 0) = 800만 → ×6%×1.1 = 528,000 < 분리 550,000
    assert abs(wd_tax(10e6, 0, .055, 6e6) - 528_000) < 1e-6 and abs(pen_income(5e7) - 4.1e7) < 1e-6   # 5천만: 공제 한도 900만
    # r3 M2 여력: C (가) 국민연금 120만×12 = 1,440만 → 공제 630만 + 40만×10% = 634만 → 806만 − 기본공제 150만 = 656만 → 6% = 393,600
    #   A (가) 480만 → 공제 350만 + 130만×40% = 402만 → 78만 < 150만 → 0 / B (가) 600만 → 150만 − 150만 → 0
    assert abs(room65(0, 14.4e6) - 393_600) < 1e-6 and room65(0, 4.8e6) == 0 and room65(0, 6e6) == 0
    # r3 M3 잔액 규칙: 4,000만 (가) → 3몫 × 1,333.33만 → 공제 490만 + 20%×633.33만 = 616.67만 → 716.67만 − 150만 = 566.67만
    #   → 6%×1.1 = 374,000 < 분리 4.4%×1,333.33만 = 586,667 → × 3 = 1,122,000 (4.4% 한 번에 = 1,760,000)
    assert abs(rem_tax(40e6, 0, .044) - 1_122_000) < 1e-6 and abs(rem_tax(1e7, 0, .044) - wd_tax(1e7, 0, .044)) < 1e-9
    # N 끈 evaluate = 동결 cand5.evaluate (노란우산 해약 열 밖, 비트 단위). 무작위 수익, 여러 결정 조합.
    rng = np.random.default_rng(1)
    for oo in ({}, {"D07": "etc"}, {"D18": False}, {"D13": True}, {"D09": "dep"}, {"D11": "hi"}, {"D10": "cap", "D17": "sep"}):
        o = {**REC, **F_ONLY, **oo}; oc = {**C.REC, **{x: v for x, v in oo.items() if x != "D11"}}
        for H, mode in ((36, "wd"), (60, "wd"), (72, "p62"), (168, "p70")):
            eq, bd, dp = rng.normal(.007, .05, (4, H)), rng.normal(.003, .01, (4, H)), np.abs(rng.normal(.003, .001, (4, H)))
            for w in (1.0, .5):
                acc = accumulate(eq, bd, dp, 300_000, w, o, [1, 4, 7, 1], H)
                for room in (0, 5e5, 2e6):
                    a, b = evaluate(acc, 300_000, room, H, mode, o), C.evaluate(acc, 300_000, room, H, mode, oc)
                    for x in set(b) - {"ny_cancel"}:
                        assert np.array_equal(np.asarray(a[x]), np.asarray(b[x])), (oo, mode, x)
    # N3 인출: 인출 안 하면 cand5.accumulate와 같음
    eq, bd = rng.normal(.007, .05, (3, 168)), rng.normal(.003, .01, (3, 168))
    for w in (1.0, .5):
        assert np.array_equal(ps_withdraw(eq, bd, 1e5, w, [1, 3, 9], wd0=99)[0], C.accumulate(eq, bd, eq * 0, 1e5, w, REC, [1, 3, 9])["ps"][:, -1])
    # 수익 0: (가) 공제 0 → 원금 전부 과세제외 → 70세 금액 = 원금 1,680만(인출 예금 + 잔액, 세금 0)
    z = np.zeros((1, 168)); o = dict(REC)
    e = evaluate(accumulate(z, z, z, 100_000, 1.0, o, None, 168), 100_000, 0, 168, "p70", o)
    assert abs(e["ps"][0] - 16_800_000) < 1e-6
    # (다) 월 50만: 해마다 공제 90만 → 과세제외 0. 첫 인출(2031년 초) = 3,000만 ÷ 10 = 300만, 세금 5.5%.
    acc = accumulate(z, z, z, 500_000, 1.0, o, None, 168); Vn, W, R = acc["wd"]
    assert abs(W[0, 0] - 3e6) < 1e-6 and abs(R[0, 0] - 27e6) < 1e-6 and abs(W[0, 1] - (27e6 + 6e6) / 9) < 1e-6
    e = evaluate(acc, 500_000, 2e6, 168, "p70", o)
    age = lambda j: AGE0 + WD0 + j - 1                                         # L2: 2031~2039년 1월 인출 = 만 61~69세 → 전부 5.5%
    assert age(W.shape[1] - 1) == 69
    tax = sum(float(wd_tax(W[0, j], 2e6, .055 if age(j) < 70 else .044)) for j in range(W.shape[1])) + .044 * Vn[0]
    assert abs(e["ps"][0] - (84e6 - tax + 14 * 990_000)) < 1e-6
    assert float(wd_tax(W[0, 0], 2e6, .055)) == 0           # 300만 ≤ 공제 350만 → 종합 증분 0 < 분리 165,000(M2)
    # 건보료 S_hi: 첫 해 인출 300만 × 50% × 7.19% = 107,850이 이듬해 예금에서 빠짐
    eh = evaluate(acc, 500_000, 2e6, 168, "p70", {**o, "D11": "hi"})
    prem = sum(.5 * .0719 * W[0, j] for j in range(W.shape[1])) + .5 * .0719 * Vn[0]
    assert abs(e["ps"][0] - eh["ps"][0] - prem) < 1e-6
    # 원인 분해 단계 (나)(M3): 해마다 꺼낸 돈에 F판 세율 4.4% → 수익 0이면 인출 + 잔액 = 원금 8,400만 전부 4.4%
    #   → 84e6 × 0.956 + 환급 예금 1,386만 = 94,164,000 (= F판 = 수령 연기판)
    e0 = evaluate(acc, 500_000, 2e6, 168, "p70", {**o, "wtax": "F"})
    assert abs(e0["ps"][0] - 94_164_000) < 1e-6
    # H2 수령 연기판: 인출 0 → F판과 같은 금액(S_lo), 1,500만 넘는 해 0
    od = {**o, "defer": True}; ad = accumulate(z, z, z, 500_000, 1.0, od, None, 168)
    e1, eF = evaluate(ad, 500_000, 2e6, 168, "p70", od, ppl), evaluate(ad, 500_000, 2e6, 168, "p70", {**o, **F_ONLY})
    assert abs(e1["ps"][0] - 94_164_000) < 1e-6 and abs(eF["ps"][0] - e1["ps"][0]) < 1e-6 and e1["n_over1500"][0] == 0
    # 연기판 기초연금 B (가)·K2 넣음(시험 금리, 예금 금리 0): 그해 첫날 잔액 = 50만 × 96·108·…·156개월 → 재산 +16만·18만·…·26만
    #   → 소득인정액 2,308,900 … 2,408,900 → 기초연금 161,100·141,100·121,100·101,100·81,100·61,100 → × 12 = 7,999,200
    bpd = evaluate(ad, 500_000, 0, 168, "p70", od, ppl)["bp"]
    assert abs(bpd[("B", "과세분만", "넣음", "중소도시")][0]["ps"][0] - 7_999_200) < 1e-6
    # r3 M3 잔액 규칙 연결: 연기판·(가)·과세제외 안 함·월 50만·수익 0 → 70세 잔액 8,400만 전부 과세. 6몫 × 1,400만:
    #   공제 630만 → 770만 − 150만 = 620만 × 6.6% = 409,200 < 분리 616,000 → 2,455,200. 4.4% 한 번에 3,696,000 → 차 1,240,800
    o3 = {**od, "D18": False}; a3 = accumulate(z, z, z, 500_000, 1.0, o3, None, 168)
    gap = evaluate(a3, 500_000, 0, 168, "p70", {**o3, "rem": "min"})["ps"][0] - evaluate(a3, 500_000, 0, 168, "p70", o3)["ps"][0]
    assert abs(gap - 1_240_800) < 1e-6
    # R3-M1 연결: 수익 0·(가)·월 50만, 사람 C. 65세부터 여력 393,600은 연금저축 쪽만. 노란우산은 사업소득금액 0이라 절세 0·실제 소득공제 0 그대로
    #   → 노란우산 노령 = Yb − 퇴직소득세(Yb − 8,400만) = 국민연금 없을 때와 같음 (r3에서는 + 1.1 × 360,000 × 6, 퇴직소득세 Yb − 4,800만이었음)
    e2 = evaluate(acc, 500_000, 0, 168, "p70", o, ppl); Yb = acc["ny_old"][0, -1]
    ny_c = {k[0]: v[2][0] for k, v in e2["bp"].items()}
    assert abs(e2["ny_old"][0] - (Yb - retire_tax(Yb - 84e6, 168))) < 1e-6 and ny_c["A"] == ny_c["B"] == ny_c["C"] == e2["ny_old"][0]
    # (나) 그릇 50만·C: b = 833만 ≥ 공제 → 노란우산도 r65(합산 과표 1,639만, 15% 구간) 그대로 → 국민연금 없을 때(6% 구간)보다 큼
    e3 = evaluate(acc, 500_000, 5e5, 168, "p70", o, ppl)
    assert {k[0]: v[2][0] for k, v in e3["bp"].items()}["C"] > e3["ny_old"][0]
    # r3 M5 노란우산 적립금 넣음: B (가), 해마다 금융재산 + 그해 첫날 적립금 Yt → 소득인정액 2,148,900 + Yt × 4%/12
    #   → 기초연금 = 0 (> 247만) 또는 max(247만 − 소득인정액, 34,970) × 12개월, 65~70세 합. 안 넣음 = 321,100 × 72
    exp = sum(12 * (0 if ia > 2.47e6 else max(2.47e6 - ia, 34_970)) for ia in (2_148_900 + acc["ny_old"][0, 12 * kk - 1] * .04 / 12 for kk in range(8, 14)))
    vB = e2["bp"][("B", "과세분만", "안넣음", "중소도시")][0]
    assert abs(vB["ny_old_in"][0] - exp) < 1e-6 and abs(vB["ny_old"][0] - 321_100 * 72) < 1e-6 and exp < 321_100 * 72
    # 9번 연결: 월 300만, 과세제외 신청 안 함, (가) → 첫 인출 1억8천만 ÷ 10 = 1,800만 > 1,500만 → 종합 646,800(M1, r3 기본공제)
    o9 = {**o, "D18": False}; acc = accumulate(z, z, z, 3e6, 1.0, o9, None, 168); Vn, W, R = acc["wd"]
    assert abs(W[0, 0] - 18e6) < 1e-6 and abs(wd_tax(W[0, 0], 0, .055) - 646_800) < 1e-6
    e = evaluate(acc, 3e6, 0, 168, "p70", o9)
    tax = sum(float(wd_tax(W[0, j], 0, .055 if age(j) < 70 else .044)) for j in range(W.shape[1])) + .044 * Vn[0]
    assert abs(e["ps"][0] - (168 * 3e6 - tax)) < 1e-6 and e["n_over1500"][0] == (W[0] > 15e6).sum() > 0
    # 8번 62세 폐업: 수익 0, 이율 고정 3.7% → 퇴직소득세 = retire_tax(적립 − 공제 안 받은 원금, 72)
    acc = accumulate(z[:, :72], z[:, :72], z[:, :72], 3e6, 1.0, o, None, 72)
    e = evaluate(acc, 3e6, 0, 72, "p62", o); Cb = acc["ny_close"][0, -1]
    assert abs(e["ny_close"][0] - (Cb - retire_tax(Cb - 216e6, 72))) < 1e-6 and retire_tax(Cb - 216e6, 72) > 0
    print("cand5p 자가점검 통과")


if __name__ == "__main__":
    _check()
