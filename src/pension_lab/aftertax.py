"""세후수익 변환 — 일반계좌(과세) vs 연금계좌(3계층: 세액공제·과세이연·인출세).

세율=법제처 1차조문(docs/세제_정리.md, 소득세법 2026-07-01본). 방법=Dammon+2004·Reichenstein2006
(세후 기준 비교, 고회전 자산은 과세이연계좌가 유리). references/SOURCES.md H2·J15.

모델(투명·잠정):
- 일반계좌: 매기 '이자·배당 income'에만 15.4% 과세, **국내주식·금현물 매매차익 비과세**(개인) 가정.
  ⚠따라서 KR에선 주식 회전율↑라도 자본이득세=0 → Dammon '고회전=이연유리' 채널이 **약함**(정직).
  개혁시나리오(자본이득 과세)만 capgain_tax>0으로 회전율×세금 효과가 살아남(민감도).
- 연금계좌 **3계층**(§13/§15 설계):
  ① 납입 세액공제(16.5%/13.2%, §59의3) — 크레딧 재투자.
  ② 운용 과세이연(계좌내 무과세, §20의3·§129⑧).
  ③ 인출 연금소득세(3.3~5.5% 연령별, §129①5의2) — **세액공제분+운용수익(tier③) 전체**에 과세.
- ⚠**미모델(부호 뒤집을 수 있음, 병기)**: 1,500만 분리과세 경계(§14③9다·§64의4), 인출순서
  (과세제외→이연퇴직→tier③, 시행령 §40의3), 종합과세 선택, 연도별 세율개정. docs/세제_정리.md 부록B.
- ⬜회원/교수 결정: 인출 스케줄(나이·연차)·연도별 세율·크레딧 재투자 행선지 → 부록B.
"""
from __future__ import annotations
import pandas as pd

# 법확정 실효세율(지방소득세 10% 포함). docs/세제_정리.md 요약표.
TAX_FINANCIAL = 0.154    # 일반계좌 이자·배당 원천징수 (소득14%+지방1.4%)
CREDIT_LOW = 0.165       # 세액공제율(총급여 5,500만↓/종소 4,500만↓) 15%+지방 = 16.5% (§59의3①)
CREDIT_HIGH = 0.132      # 세액공제율(그 초과) 12%+지방 = 13.2% (§59의3①)
PENSION_UNDER70 = 0.055  # 연금수령세 70세 미만 (소득세법 §129①5의2)
PENSION_70S = 0.044      # 70~80세 미만
PENSION_80 = 0.033       # 80세 이상/종신
ETC_TAX = 0.165          # 연금외수령·중도해지 기타소득세 (§21①21·§129①6나)


def taxable_after_tax_daily(gross_daily: pd.Series, income_daily: pd.Series,
                            capgain_daily: pd.Series | float = 0.0,
                            capgain_tax: float = 0.0) -> pd.Series:
    """일반계좌 세후 일수익 = 총수익 − income×15.4% − 실현자본이득×capgain_tax.

    기본: capgain_tax=0(KR 국내주식·금현물 개인 매매차익 **비과세**) → 종전과 동일(자본이득 비과세).
    개혁시나리오만 capgain_tax>0 + capgain_daily(실현이득 근사)로 회전율×세금 채널을 켠다(민감도).
    """
    at = gross_daily - income_daily * TAX_FINANCIAL
    if capgain_tax:
        at = at - capgain_daily * capgain_tax
    return at


def pension_after_tax_ratio(gross_ratio: float, pension_rate: float = PENSION_UNDER70) -> float:
    """[자산배치 프레임] 연금계좌 세후 배수 = 1 + (총배수−1)×(1−연금세율). **운용수익에만** 저율 과세.

    B/Dammon 자산배치 비교용(이미 내 돈, 계좌만 선택 → 원금은 tier①처럼 과세대상 아님, 이득만 tier③).
    전생애 납입→인출 3계층은 three_tier_pension_multiple을 쓸 것(원금+이득 전체 tier③ 과세).
    """
    return 1.0 + (gross_ratio - 1.0) * (1.0 - pension_rate)


def three_tier_pension_multiple(gross_ratio: float, credit_rate: float = CREDIT_LOW,
                                pension_rate: float = PENSION_UNDER70,
                                credit_reinvest_taxfree: bool = True) -> float:
    """[전생애 3계층] 세전소득 1단위를 연금계좌에 **전액 세액공제 납입** 후 인출까지의 세후 최종배수.

    ① 납입 1 → 세액공제 크레딧 credit_rate 환급 → **재투자**(계좌내 과세이연 성장 gross_ratio).
    ② 계좌내 무과세 성장: 납입원금·크레딧 모두 gross_ratio 배.
    ③ 인출: 세액공제받은 납입액+운용수익(tier③ = 원금 1 성장분 전체)에 pension_rate 과세.
       크레딧 재투자분은 (기본) 미공제 재납입=tier① 비과세로 가정(credit_reinvest_taxfree=True).

    반환 = gross_ratio·[ (1−pension_rate) + credit_rate·(1 if 비과세재투자 else (1−pension_rate)) ].
    비교 상대(일반계좌 전생애)는 노트북에서 taxable_after_tax_daily 누적배수로(연간 income과세·자본이득
    기본 비과세). **세액공제·저율 인출세 = 연금의 전생애 우위 원천**; 회전율보다 income·인출세가 핵심(KR).

    ⚠1,500만 분리과세·인출순서·연령분기·종합과세 미모델 → 부호 뒤집을 수 있음(docs/세제_정리.md 부록B).
    """
    credit_grown = credit_rate * (1.0 if credit_reinvest_taxfree else (1.0 - pension_rate))
    return gross_ratio * ((1.0 - pension_rate) + credit_grown)


if __name__ == "__main__":  # 자기검증
    import numpy as np
    idx = pd.bdate_range("2020-01-01", periods=252)
    gross = pd.Series(np.full(252, 0.0004), index=idx)      # 하루 4bp
    income = pd.Series(np.full(252, 0.0002), index=idx)     # 그중 2bp가 과세 income
    at = taxable_after_tax_daily(gross, income)
    assert (at < gross).all(), "세금이 수익을 못 깎음"
    assert abs((gross - at).mean() - 0.0002 * TAX_FINANCIAL) < 1e-12, "income 과세액 오류"
    # 연금: 총 2배면 세후배수 = 1+1*(1-0.055)=1.945
    assert abs(pension_after_tax_ratio(2.0) - 1.945) < 1e-12
    assert pension_after_tax_ratio(1.0) == 1.0               # 수익0이면 세금0
    # 3계층: 성장 3배·크레딧16.5%비과세재투자·인출5.5% = 3*((1-0.055)+0.165)=3*1.11=3.33
    assert abs(three_tier_pension_multiple(3.0) - 3.0 * (0.945 + 0.165)) < 1e-12
    assert three_tier_pension_multiple(3.0) > pension_after_tax_ratio(3.0), "3계층(크레딧)이 자산배치프레임보다 커야"
    # 자본이득 과세 개혁시나리오: 실현이득 있으면 세후↓
    cg = pd.Series(np.full(252, 0.0002), index=idx)
    at_reform = taxable_after_tax_daily(gross, income, cg, capgain_tax=0.22)
    assert (at_reform < at).all(), "자본이득세 개혁시 세후 더 낮아야"
    print("OK aftertax (3계층·자본이득개혁 포함)")
