# 연금 투자 의사결정 시뮬레이션 포트폴리오

개인이 연금저축·TDF·노란우산공제 같은 노후 상품을 고를 때 실제로 부딪히는 질문을, 과거 수익률 재표본(부트스트랩)과 세법·제도 규칙을 넣은 시뮬레이션으로 따져 본 작업입니다. 01~03은 대표작, 04~07은 기존 파일럿 결과를 한 질문씩 정리한 짧은 주제입니다. README 숫자 일부는 저장된 결과 파일에서 다시 계산해 assert합니다(`check_numbers.py`, 확인 범위는 그 파일 맨 위에 적음). 결과가 말해 주지 않는 것과 한계를 따로 적었습니다.

## 대표작

| 주제 | 한 줄 결론 | 보여 주는 능력 | 폴더 |
|---|---|---|---|
| 첫 하락장 앞의 선택: 해지·중단·더 담기 | 첫 하락장에서 해지하면 30년 뒤 실질 자산 중앙값이 다섯 표본 모두 0.8~6.1% 적었다. 하락장에 더 담는 규칙의 이득은 같은 양을 매달 고르게 더 담은 것과 문턱 −20·−30%에서는 거의 같았고, −10%에서는 대부분 더 작았다(규칙이 더 큰 경로 비율: 234칸 전체 0.16~0.59, 문턱 −20% 0.42~0.55, −30% 0.37~0.59, −10% 0.16~0.51). | 블록 부트스트랩, 위약(placebo) 대조군 설계, 다국가 표본, 거래비용 민감도 | [01_downturn_timing](01_downturn_timing/) |
| TDF 대 직접 운용 | 한국 TDF 19개(3개 운용사)와 같은 비중을 직접 운용한 것의 연 수익률 차이는 비교 6개(기간 3 × 직접 운용 방식 2)에서 −0.9~−2.9%p였고, 0과 구분되는 것(HAC p<0.05)은 2개다. 보수는 연 1.28%p이고, 보수 외 나머지는 환헤지 가정에 따라 크게 바뀐다. | 스타일 분석(제약 회귀), 공시 보유내역 재구성, HAC 검정, 차이 분해 | [02_tdf_vs_diy](02_tdf_vs_diy/) |
| 50대 자영업자: 연금저축·노란우산·예금 | 세금을 안 내는 사람(주식 100%·월 30만 원)에게 연금저축은 3·5년째 꺼내면 시작 연도의 40~44%에서 예금보다 적었고, 70세까지 두면 예금보다 적은 시작 연도가 없었다(0/21, 부트스트랩 1만 경로 중에서는 19~22%). 노란우산을 그냥 해약하면 3·5년째는 모든 시작 연도에서, 62세는 29개 중 28개에서 예금보다 적었다. | 세법·기초연금·건보료 규칙을 원문에서 확인해 모형화, 손계산 대조, 결과를 상담표로 번역 | [03_selfemployed_50s](03_selfemployed_50s/) |

## 짧은 주제 (04~07)

| 주제 | 한 줄 결론 | 보여 주는 능력 | 폴더 |
|---|---|---|---|
| 해지 대신 대출 | 공제받은 돈을 꺼낼 바엔 12개월 담보대출이 대체로 쌌다(주식 100%, 대출이 쌀 확률 세 표본 73~88%). 한도(평가액 50%)를 다 빌리면 12개월 안 담보부족 확률이 0.6~9.3%, 30% 이하면 0.2% 이하였다. | 부트스트랩 재실행·회귀 일치(같은 시드), 경로별 담보부족 판정, 세후 비용식 | [04_loan_vs_withdraw](04_loan_vs_withdraw/) |
| 두 통 설계 + 공짜 리밸런싱 | 공제를 못 받는 사람이 국내주식을 55세 전에 꺼내면 연금저축이 나은 시작 월이 0~11%(5년 이상 보유)였고, 미국주식을 55세 뒤 연금으로 받으면 공제 여부와 상관없이 모든 시작 월에서 연금저축이 나았다. 계좌 안 리밸런싱의 이득은 72칸 중 95% 구간이 0을 뺀 칸이 3·4칸뿐이었다. | 세후 계좌 비교, 결정 나무(표시 규칙은 결과를 본 뒤 정함), 쌍 부트스트랩 | [05_two_buckets_free_rebalancing](05_two_buckets_free_rebalancing/) |
| 목돈 한 번에 대 나눠 넣기 | 다국가 1년 창에서 한 번에 넣기가 59·66%, 고점 시작에서도 64·66% 이겼다. 위험회피 γ=10이면 주식 100%의 모든 표본에서 나눠 넣기의 확실성등가가 더 높았다. | 다국가 표본, 나라 묶음 부트스트랩·Wilson 구간, 확실성등가(CER) | [06_lumpsum_vs_dca](06_lumpsum_vs_dca/) |
| 운용사별 2055 TDF | 투자설명서대로면 30년 금액이 운용사 쌍별 1.02~1.20배 달랐지만, 실제 수익률은 설명서 계산과 연 4.7~8.6%p 흔들렸고, 2055 빈티지 공통 23개월로 구별할 수 있는 최소 연 차이는 9.5%p였다. | 공시 비중 복제·추적오차, 검정력(MDE), 운용사 군집 패널(wild cluster bootstrap) | [07_tdf_glidepath_by_manager](07_tdf_glidepath_by_manager/) |

## 폴더 구조

```
README.md  DATA_SOURCES.md  check_numbers.py  requirements.txt  pyproject.toml
LICENSE (코드, MIT)  LICENSE-CC-BY-4.0.md (글·그림·결과 표)
src/pension_lab/         세 주제가 함께 쓰는 계산 모듈 (+ fetch/: 공공 자료 받는 코드)
data/                    재배포 조건을 확인한 공공 원자료만 (한국은행 ECOS) — DATA_SOURCES.md
01_downturn_timing/      README · figures/ · results/ · notebooks/(결과를 만든 코드)
02_tdf_vs_diy/           README · figures/ · results/ · notebooks/
03_selfemployed_50s/     README · results/ · notebooks/ · docs/(설계서) · references/(법령 원문 발췌·근거 메모)
04_loan_vs_withdraw/ ~ 07_tdf_glidepath_by_manager/   README · figures/ · results/ · notebooks/
                         (04~07 그림·README 스크립트: 04_loan_vs_withdraw/notebooks/portfolio/make_topics_a.py)
```

## 재현 방법

1. Python 3.12 이상. `pip install -r requirements.txt` 뒤 `pip install -e .` (공통 모듈 `pension_lab`을 설치).
2. **숫자 대조(원자료 없이 됨)**: `python check_numbers.py` — `results/`·`figures/*_data.csv`에서 01 해지 부호, 01 더 담기 규칙(234칸·문턱별 범위·예시 칸), 03 상담표 전체 칸, 04~07 README 숫자(결과 CSV에서 다시 계산한 값이 각 README와 루트 표에 그대로 있는지)를 다시 계산해 assert합니다. 01 표본별·거래비용 범위와 02 숫자는 표로만 출력하고 assert하지 않습니다.
3. **시뮬레이션 다시 돌리기(원자료 필요)**: 국내 주식·채권 수익률이 에프앤가이드 DataGuide(유료 라이선스) 자료라 이 저장소에 넣지 않았습니다. `DATA_SOURCES.md`의 절차대로 자료를 받아 한 폴더에 두고 환경변수 `PENSION_DATA_ROOT`로 그 폴더를 가리킨 뒤(설정하지 않으면 저장소의 `data/`), 각 주제 README의 '코드' 절 순서대로 실행합니다. 코드는 원래 연구 저장소의 파일을 옮긴 것이라 문서 안 경로는 `$PENSION_DATA_ROOT/...`로 적었고, 폴더 구조가 원 저장소와 달라 일부 스크립트는 경로를 맞춰야 돌아갑니다.
4. 그림: `01_downturn_timing/notebooks/portfolio/make_figures.py`(그림 1·2·3). 저장소의 결과 CSV만 읽어 그립니다(새 계산 없음). `PENSION_DATA_ROOT`를 설정하면 `$PENSION_DATA_ROOT/results/portfolio_figures_20261107/`에도 같은 파일을 씁니다. 04~07의 그림·README는 `04_loan_vs_withdraw/notebooks/portfolio/make_topics_a.py`로 만듭니다(05·06은 저장소 결과만으로, 04는 원자료가 있으면 부트스트랩부터, 07은 공시 글라이드·보수 입력이 있어야 돎 — 각 README '파일' 절).
5. **노트북 출력 지우기**: 노트북 생성기(`_gen_*.py`)는 실행본을 저장소 `.ipynb`에 씁니다. 커밋 전에 출력을 지우도록 `pip install nbstripout` 뒤 저장소에서 `nbstripout --install`을 한 번 실행하세요(`.gitattributes`에 필터가 적혀 있음). 설치하지 않았다면 `jupyter nbconvert --clear-output --inplace <노트북>`으로 지운 뒤 커밋합니다.

## 투자 권유가 아닙니다

이 저장소는 과거 자료로 만든 시뮬레이션 연구 기록입니다. 특정 금융상품의 매수·매도·가입·해지를 권하지 않으며, 개인의 세금·소득·건강 사정에 맞춘 조언이 아닙니다. 과거 경로의 결과는 미래 수익을 보장하지 않습니다. 세법·제도 규칙은 2026년 기준으로 확인한 값이며 바뀔 수 있습니다.

## 라이선스

- 코드(`*.py`, `*.ipynb`, `requirements.txt`, `pyproject.toml`): MIT — [LICENSE](LICENSE)
- 글·그림·결과 표: CC BY 4.0 — [LICENSE-CC-BY-4.0.md](LICENSE-CC-BY-4.0.md)
- 제3자 자료(한국은행 ECOS 자료, 법령 원문 발췌)는 원래 조건을 따릅니다 — [DATA_SOURCES.md](DATA_SOURCES.md)

---

**English summary.** Three simulation studies of retirement-savings decisions in Korea: (1) what a first bear market costs savers who cancel, pause, or buy more (block bootstrap with placebo controls; canceling cost 0.8–6.1% of median 30-year real wealth across five samples, and a "buy the dip" rule gained about as much as adding the same extra equity evenly every month at −20% and −30% drop thresholds, and mostly less at −10%); (2) Korean target-date funds vs. replicating them yourself (point estimates of −0.9 to −2.9 pp a year across six comparisons, two of them distinguishable from zero; fees are 1.28 pp a year); (3) pension savings account vs. the 'Yellow Umbrella' small-business mutual aid vs. bank deposits for a self-employed person in their 50s, with tax, basic-pension and health-insurance rules taken from primary legal sources. Four shorter studies (04–07) reuse pilot results: borrowing against a pension account instead of withdrawing, when the pension account beats a taxable account, lump-sum vs. spreading a transfer, and why short return rankings cannot tell target-date fund managers apart. Not investment advice; licensed-vendor (FnGuide DataGuide) raw data is excluded, see DATA_SOURCES.md.
