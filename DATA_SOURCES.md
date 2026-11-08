# 자료 출처와 재배포 판정

확인일: 2026-11-07(04~07·08~11 폴더 추가분 2026-11-08). 아래 재배포 조건은 각 사이트의 공개 약관·저작권 정책을 읽고 정리한 것으로, 법률 자문이 아닙니다.

## 1. 판정 규칙
1. **에프앤가이드 DataGuide 원자료와 그것을 가공한 원시 표는 넣지 않습니다.** 받는 방법(4절)만 적습니다.
2. 공공 출처 원자료는 재배포 조건을 확인한 것만 넣고 조건을 적습니다. 조건을 확인하지 못했거나 허락이 필요한 것은 넣지 않고 받는 코드·주소만 둡니다.
3. 출처가 불명확한 파일은 넣지 않습니다.
4. 결과 파일(`results/`, `figures/*_data.csv`)은 이 연구가 만든 **요약 통계**(1만 경로의 중앙값·분위수·비율, 검정 통계, 시작 연도별 시뮬레이션 금액)입니다. 원자료 시계열(월 수익률, 지수, 기준가)은 들어 있지 않습니다. 다만 국내 주식·채권 입력이 DataGuide 자료이므로, 결과는 그 자료로 계산한 값입니다. 04~07의 `results/`도 같은 요약 표입니다(04 `T1_events.csv`는 약세장 진입 사건별 12개월 수익·최저 한 줄씩, 07 `L1_real_nav_stats.csv`는 실제 기준가로 계산한 운용사별 연수익·변동성·낙폭·적립 배수, `C2_check_index_vs_real_overlap.csv`는 상관·평균차·추적오차). 07 그림 왼쪽 선은 공시 글라이드패스를 그린 것이고, 그 값 표와 선 좌표가 그대로 남는 `.svg`는 넣지 않았습니다(`.png`만, 3-2절). 08~11의 `results/`도 요약 표입니다: 08 `T6_shelter_events.csv`는 하락장 사건별 피신 ÷ 보유 비율과 그 기간 주식·안전자산 누적 수익 한 줄씩, `T6_flow_vs_nonbear.csv`는 순설정 ÷ 순자산 비율과 비교 창 분위수(순설정·순자산 원값 없음), 09 `T9_cf_by_fund.csv`는 펀드별 금액 차이·판정(공시 위험자산 비중 값 열은 뺌), 10은 보고서별 '실제 − 목표' 격차와 판정만(보유내역 원행·비중 값·공시 목표 값은 뺌 — 비중과 격차를 함께 두면 공시 글라이드 값이 되살아나므로), 11 `results/simpletest_T2/`는 원 연구 T2의 동결 요약 표(경로 비율·하락 국면별 누적 수익·구별 가능 최소 차이)입니다. 08~11 그림은 `.svg`도 넣었습니다(사건별 비율·격차·공시일 점·요약 값만 그리고 공시 글라이드 값이나 원 시계열은 그리지 않음; 09 왼쪽 점은 투자설명서 공시일).

## 2. 넣은 원자료

| 파일 (`data/` 아래) | 내용 | 출처 | 재배포 조건 | 쓰는 곳 |
|---|---|---|---|---|
| `raw/macro_fx_vol/ecos_cpi_long.csv` | 소비자물가지수 월 1990~ (901Y009) | 한국은행 ECOS | 조건부 가능(아래) | 01 실질 환산, 11(원 T2 계산) |
| `raw/bond_kr/ecos_cd91_long.csv` | CD 91일 금리 일별 1995~ (817Y002) | 한국은행 ECOS | 조건부 가능 | 01 현금·02 헤지 비용, 11(원 T2 계산) |
| `raw/macro_fx_vol/ecos_usdkrw_long.csv` | 원/달러 환율 일별 1990~ (731Y001) | 한국은행 ECOS | 조건부 가능 | 01·02 원화 환산, 11(원 T2 계산) |
| `raw/bond_kr/ecos_ktb3y_long.csv` | 국고채 3년 금리 일별 1998~ (817Y002) | 한국은행 ECOS | 조건부 가능 | 01 T4 채권, 11(원 T2 계산) |
| `raw/bond_kr/ecos_nhb5y_monthly_1987.csv` | 국민주택채권 5년 금리 월 1987~ (721Y001) | 한국은행 ECOS | 조건부 가능 | 01 T4 채권(1990년대), 11(원 T2 계산) |
| `raw/bond_kr/ecos_ktb3y_monthly_1995.csv` | 국고채 3년 금리 월 1995~ (721Y001) | 한국은행 ECOS | 조건부 가능 | 01 T4 채권, 11(원 T2 계산) |
| `raw/bond_kr/ecos_shortrate_monthly_1989_1996.csv` | CD·통안증권 금리 월 1989~1996 (721Y001) | 한국은행 ECOS | 조건부 가능 | 01 T4 현금(1990년대), 11(원 T2 계산) |
| `processed/pilot9_ecos_deposit_rates_monthly.csv` | 예금은행 수신금리 월 (121Y002 여러 계열) | 한국은행 ECOS | 조건부 가능 | 03 예금 금리 |

- ECOS 파일은 받은 값에서 열 이름·날짜 형식만 바꿨습니다(값 가공 없음). 받는 코드: `src/pension_lab/fetch/ecos_macro_long.py`(API 키는 환경변수 `ECOS_API_KEY`).
- **조건**: 한국은행 저작권정책 — 공표해 홈페이지에 게시한 공공데이터는 별도 절차 없이 이용 가능, 출처가 한국은행임을 밝히고 수정·가공했으면 그 사실을 밝힐 것. 목록에 없는 정보는 사전 승인 필요. ECOS 자체 이용약관 페이지는 열리지 않아 한국은행 전체 정책으로 판단했습니다. https://www.bok.or.kr/portal/main/contents.do?menuNo=200228 (공공데이터포털의 한국은행 통계 API는 '이용허락범위 제한 없음': https://www.data.go.kr/data/15059638/openapi.do)
- **출처 표시**: 자료: 한국은행 경제통계시스템(ECOS). 열 이름·날짜 형식 변경.

| 파일 (`03_selfemployed_50s/references/`) | 출처 | 조건 |
|---|---|---|
| `law_소득세법_47의2_…`, `law_소득세법_50_…`, `law_소득세법_59의3_…`, `law_소득세법시행령_40의2_…`, `law_조특법_86의3_노란우산_…`, `law_조특법_91의18_…`, `candidate5_law_check_…` | 국가법령정보센터 법령 원문(일부는 같은 원문을 전재한 casenote.kr에서 받고 국가법령정보센터 현행 조문과 대조) | 저작권법 제7조(보호받지 못하는 저작물) — 영리 목적 포함 자유 이용. 이 파일은 공식 법령이 아니며 효력은 관보 기준. https://www.law.go.kr/LSW/lawPetitionForm.do?menuId=13&subMenuId=79 |
| `후보5_*_1차출처_*.md`, `후보5_기초연금_사람3명_근거_*.md` | 작성자 메모(법령·사업안내·노란우산 안내를 읽고 요약한 규칙과 숫자, 출처 주소) | CC BY 4.0(작성자 글). 인용 대상 기관 자료의 원문을 옮기지 않고 요약·쪽 번호만 적었습니다. |

## 3. 넣지 않은 원자료

D = DataGuide 유래 여부. '받는 법'에 코드가 있으면 `src/pension_lab/fetch/` 아래 파일입니다.

### 3-1. DataGuide(에프앤가이드) — 유료 라이선스, 넣지 않음

| 파일 | 내용 | 쓰는 곳 | D | 받는 법 |
|---|---|---|---|---|
| `dataguide/kodex200_adj.xlsx` | KODEX 200 수정주가 | 01 T4, 02 T7 (국내 주식) | 예 | 4절 |
| `dataguide/bond_tr_index.xlsx` | 국고채 총수익지수 (코드 `FBI.KTB.01.2`) | 01 T4, 02 T7 (국내 채권), 11(원 T2 계산) | 예 | 4절 |
| `dataguide/dg_econ_divyield_rates_19900101.csv` | 시장 평균배당수익률(월)·CD·국민주택5년·국고3년·회사채AA-·국고5년 금리(일) — `kospi_k200_tr_1980.xlsx` Sheet2에서 옮김 | 01 T4 (1990년대 배당·채권), 03, 11(원 T2 계산) | 예 | 4절 |
| `dataguide/dg_kospi_k200_tr_daily_19800104.csv` | KOSPI·KOSPI200·KOSPI200 TR 일별 — `kospi_k200_tr_1980.xlsx` Sheet1 | 01 D·I1(아래 C2 경유), 03, 11(원 T2 계산) | 예 | 4절 |
| `results/.../C_real_20261017/inputs/C2_components_monthly.csv` | 월 주식·채권·코스피 묶음 수익률 (연구가 만든 파일) | 01 D·I1, 07(실제 대 계산 입력), 09(시장 경로) | **예(가공)** — 채권·코스피 열은 DataGuide, 주식 열은 DataGuide TR + 한국거래소 + French + ECOS 환율 혼합 | `01_downturn_timing/notebooks/pilot9/_build_C_real_inputs.py`(`load_comps`)로 위 자료에서 만듦 |
| `results/.../C_real_20261017/inputs/C3_dd_events.csv` | 하락장 날짜표 (C2 계열 + TDF 기준가) | 01 D 자기 점검, 08 자금흐름의 하락장 상태 달 | **예(가공)** | 같은 스크립트 |
| `results/pilot9_20261013/C_kr_real_20261017/events.csv` | 한국 하락장 확인월(코스피 가격) | 08 자금흐름 사건 월 | **예(가공)** | 원 연구 저장소 `notebooks/pilot9/_gen_C_kr_real.py`(이 저장소에 없음) |
| `results/pilot9_20261013/c1_korea/c1_ps_bear_phases_v2_20261014.csv` | 한국·미국 약세 국면 고점·바닥 월(Pagan–Sossounov 날짜매기기, 연구가 만든 파일) | 11(원 T2 계산, 국면별 누적 수익) | **예(가공)** — KR = DataGuide 코스피 월말, US = Yahoo S&P500 | 원 연구 저장소 `results/pilot9_20261013/c1_korea/c1_rule_compare_v2_20261014.py`(이 저장소에 없음) |

- 08의 한국 표본(`src/pension_lab/pilot7.py`의 `samples()["KR 1991~"]`: KOSPI200+배당·CD91·국고채 TR)과 11의 원 계산(원 연구 T2, `11_krw_30y/notebooks/simpletest/`)도 위 DataGuide 자료와 2절 ECOS 자료로 만듭니다. 11 원 계산이 읽는 파일 전체는 `_gen_T2.py`의 `input_files()`이고, 표마다 쓰는 곳 칸에 '11(원 T2 계산)'으로 적었습니다. 그 밖에 저장소 안의 `01_downturn_timing/results/pilot7/T4_level.csv`(원 연구 pilot7 결과, 원 연구에서는 `$PENSION_DATA_ROOT/results/pilot7_20261008/`)를 재현 대조에 읽습니다.

### 3-2. 공공·공개 출처지만 재배포 조건을 확인하지 못했거나 허락이 필요한 것 — 넣지 않음

| 파일 | 내용 | 쓰는 곳 | D | 넣지 않은 이유 | 받는 법 |
|---|---|---|---|---|---|
| `raw/equity_kr/idx_kospi200.csv`, `idx_kospi200_fundamental.csv` | 코스피200 가격·배당수익률 | 01 T4, 02 T7, 03, 07(C2 경유), 11(원 T2 계산) | 아니오 | 한국거래소: 사전 동의 없이 복제·배포 금지(https://info.krx.co.kr/contents/KRX/06/06070200/KRX06070200.jsp) | `pykrx` `get_index_ohlcv_by_date('1028')`, `get_index_fundamental` (자동 수집은 KRX 약관 제10조 위험 — DataGuide로 대체 권장) |
| `raw/equity_global/global_us_spy_tr.csv`, `global_dev_exus_efa.csv`, `global_emerging_eem.csv`, `bond_global/global_us_aggbond_agg.csv`, `global_ustreasury_mid_ief.csv`, `commodity/gold_long.xlsx`, `equity_global/sp500_fdr.csv` | 해외 ETF·지수·금 가격 | 01 T4, 02 T7, 11(원 T2 계산) | 아니오 | Yahoo 약관: 자동 수집·대체 데이터베이스 금지(https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) | `fetch/fdr_assets.py` (FinanceDataReader) |
| `raw/equity_global/sp500_price_yf_1965.csv`, `sp500tr_yf_1988.csv` | S&P500 가격·총수익 | 01 T4 미국 표본, 11(원 T2 계산) | 아니오 | 같은 Yahoo 약관 | `yfinance`(`^GSPC`, `^SP500TR`) |
| `raw/macro_fx_vol/fred_dtb3.csv`, `fred_cpiaucsl.csv`, `fred_oecd_*.csv`(5개) | 미국 3개월 국채·CPI, OECD 장단기 금리·CPI | 01 T4, 02 T7, 11(원 T2 계산) | 아니오 | FRED 약관: FRED 내용의 저장·보관·데이터베이스 수록 금지(https://fred.stlouisfed.org/legal/). 원 출처(BLS·OECD)에서 받으면 공개 가능할 수 있으나 그렇게 받지 않았음 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=<계열> |
| `raw/macro_fx_vol/oecd_sdmx_cpi_raw_20261009.csv`, `bis_long_cpi_monthly_20261009.csv` | OECD·BIS 월 CPI | 01 T4, 11(원 T2 계산) | 아니오 | OECD는 2024-07부터 CC BY 4.0이라는 2차 자료만 확인(oecd.org 403). BIS 조건 미확인 | `fetch/oecd_sdmx_cpi.py` |
| `raw/equity_global/french/F-F_Research_Data_Factors.csv`, `french_intl/*.Dat`(21개) | Fama–French 미국 요인·국가별 주식 수익 | 01 전부, 08(9개국 주식), 11(원 T2 계산) | 아니오 | 재배포 허락 문구 없음(저작권 표시만) | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html (`F-F_International_Countries`), `fetch/pilot9_global_equity.py` |
| `raw/equity_global/shiller_ie_data_20260928.xls` | Shiller 미국 장기 자료 | 01 T4, 11(원 T2 계산) | 아니오 | 조건 미확인 | http://www.econ.yale.edu/~shiller/data.htm |
| `raw/multicountry_20261017/JSTdatasetR6.xlsx` | Jordà–Schularick–Taylor 거시사 자료 | 01 T4(수준 지표만) | 아니오 | 조건 미확인 | https://www.macrohistory.net/database/ |
| `processed/multicountry_returns_20261017.csv` | 9개국 국채 총수익·CPI 패널 (연구가 만든 파일; JST·Swinkels(2023)·OECD·BIS·IMF·FRED에서) | 01 D·I1 다국가, 08(9개국 OECD 3개월 금리·Swinkels 10년 국채), 11(원 T2 계산) | 아니오 | 재료의 조건 미확인·FRED 포함 | 원 연구 저장소 `raw/multicountry_20261017/build_multicountry_20261017.py`(이 저장소에 없음) |
| `results/pilot9_20261013/C_multi_20261017/events_monthly.csv` | 9개국 하락장 날짜표(확인월·회복월·재무장월, 연구가 만든 파일) | 08(사건표 재현 확인) | 아니오 | 위 French·multicountry 자료에서 만든 표(재료 조건 미확인) | 원 연구 저장소 `notebooks/pilot9/_gen_C_multi.py`(이 저장소에 없음). 08 스크립트가 같은 사건표를 `dd_detail`로 다시 만들고 같은지 확인함 |
| `raw/kr_bond_pre2004_20261017/kis_monthly_2001_clean.csv` | KIS채권평가 국고채 총수익지수 2001~2004 (한경 데이터센터) | 01 D·I1 (KR-b) | 아니오 | 조건 미확인 | `fetch/kr_bond_pre2004.py` |
| `raw/fund_tdf/glidepath_disclosed_prospectus.csv`, `glidepath_disclosed_web_kr_others.csv`, `glidepath_disclosed_hist_20261012fix.csv`(5대 운용사 35펀드 1,004판 판본표) | TDF 공시 글라이드패스 | 01 D·I1, 02 T7, 07, 09(판본표) | 아니오 | 금융투자협회·운용사 공시: 재배포 조건 없음("All rights reserved"), 공시 문서 저작권은 운용사에 있을 가능성(미검증) | 금융투자협회 전자공시(https://dis.kofia.or.kr) 투자설명서에서 직접 읽음. 받는 코드는 공개 범위 밖 주제와 묶여 있어 넣지 않음 |
| `raw/fund_tdf/tdf_fee_c_class.csv`, `tdf_fee_underlying_c_class_20261009.csv`, `tdfext_fee_kofia_20261009.csv`, `tdfext_fund_names_kofia_20261008.csv`, `results/.../fee_pclass_20261016/pclass_fee_table.csv` | TDF 보수·펀드명 | 01, 02, 07 | 아니오 | 같은 이유(KOFIA) | `fetch/tdf_fee_extract.py`, `fetch/tdfext_fee_extract.py`(내려받은 투자설명서 PDF에서 추출). `tdfext_fee_extract.py`의 판독 대조값은 코드에 없고 사용자가 만드는 `raw/fund_tdf/tdfext_fee_expect.csv`에서 읽음(3-3절) |
| `processed/nav_tdf_clean_v3_20260928.csv`, `nav_tdfext_clean_v3_20260928.csv` | TDF 기준가(정제본) | 02 T7, 07 | 아니오 | 같은 이유(KOFIA) | `fetch/kofia_tdf.py` |
| `results/pilot9_20261013/C_real_20261017/inputs/C1_real_tdf2055_cpe_monthly.csv` | 5대 운용사 2055 TDF 실제 기준가 월 수익(연구가 만든 파일) | 07 실제 수익 비교(`_gen_A_simple.py`) | 아니오 | 같은 이유(KOFIA 기준가) | `01_downturn_timing/notebooks/pilot9/_build_C_real_inputs.py`가 기준가에서 만듦 |
| `raw/fund_tdf/early_class_nav/early_class_nav_20261012.csv` | TDF 같은 펀드의 가장 이른 대표 클래스 일별 기준가 | 07 구별 가능 최소 차이(`_gen_A_window_mde.py`) | 아니오 | 같은 이유(KOFIA) | 원 연구 저장소 `fetch/pilot9_kofia_cov.py`(의존 모듈이 공개 범위 밖이라 옮기지 않음). 같은 금융투자협회 기준가 조회는 `fetch/kofia_tdf.py`·`fetch/kofia_h_uh_nav.py` |
| `raw/fund_tdf/mgmt_reports/holdings_20261009.csv`, `hedge_ratio_20261011fix.csv`, `krw_share_20261011fix.csv`, `holding_class_map_20261009.csv` | 자산운용보고서 보유내역·헤지비율(분류표는 작성자 수작업) | 02 T7, 10(아래 비중 표 경유) | 아니오 | 운용사 공시: 재배포 조건 미확인 | `fetch/mgmt_report_tdf.py` |
| `results/pilot10_20261017/T1_rebuy/T1c_calib_points.csv`, `results/pilot8_20261010/T1d_desc/t1d_rows.csv` | 보고서별 위험자산 비중(점·경계, 보유내역에서 연구가 만든 파일) | 10 | 아니오 | 보유내역 가공 값이고, 10 격차와 합치면 공시 글라이드 값이 되살아남 | 원 연구 저장소 `notebooks/pilot10/_gen_T1c_navstyle.py`·`notebooks/pilot8/_gen_T1d_desc.py`(이 저장소에 없음) |
| `results/pilot8_20261010/T1_reduced/t1r_glide_at_reports.csv` | 보고서 날짜에 유효했던 공시 글라이드 목표(연구가 만든 파일) | 10 | 아니오 | 위 글라이드패스와 같은 이유 | 원 연구 저장소 pilot8(이 저장소에 없음) |
| `results/simpletest_20261027/T3/full_r1_20261027_0433/T3_07_decision_events.csv`, `T3_13b_cf_floor_used.csv` | 글라이드 변경 사건 날짜·판독 잡음 바닥선(원 연구 T3 결과) | 09 | 아니오 | 위 판본표에서 만든 원 연구 중간 결과(공개 범위 밖 주제와 묶임) | 원 연구 저장소 `notebooks/simpletest/_gen_T3.py`(이 저장소에 없음). 09 그림 `_data.csv`에 변경 9번 날짜는 있음 |
| `results/pilot10_20261017/I2x_hist/results_lt2020/lt2020_events.csv` | 한국 하락 국면 날짜(LT 20/20, 코스피 일별에서 만듦) | 09 그림 음영 | 확인 안 함(코스피 일별 원천) | 원 연구 중간 결과 | 원 연구 저장소 `notebooks/pilot10/_lt2020_events.py`(이 저장소에 없음) |
| `results/pilot10_20261017/T3_flow/T3_monthly_group_T3a.csv`, `T3_monthly_group.csv` | 연금 펀드 클래스 월 순설정·순자산 묶음 합계(연구가 만든 파일) | 08 자금흐름 | 아니오 | 금융투자협회 자료 가공(같은 이유) | 원 연구 저장소 `notebooks/pilot10/_gen_T3_simple.py`(이 저장소에 없음). 원천은 금융투자협회 펀드 자료이고 수집 코드도 원 연구 저장소에만 있음 |
| `results/pilot9_20261013/A_simple_20261017/L2_inputs_glide_fee_by_month.csv`, `results/pilot9_20261013/decisions_survey/D1_glide_2055_annual.csv` | 5대 운용사 2055 TDF의 월별 공시 위험자산 비중·총보수(30년 계산 입력), 다른 운용사 공시 글라이드 연별 값 (연구가 만든 파일) | 07 그림 왼쪽·30년 계산 | 아니오 | 위 글라이드패스·보수와 같은 이유(KOFIA·운용사 공시를 옮긴 값) | `07_tdf_glidepath_by_manager/notebooks/pilot9/_gen_A_simple.py`가 `01_downturn_timing/notebooks/pilot9/_build_C_real_inputs.py`(`glide_w`·`fee_pct`)로 만듦. 07 그림·README를 다시 만들려면 `$PENSION_DATA_ROOT/results/` 아래 같은 경로에 두어야 함 |
| `results/pilot9_20261013/C_real_20261017/inputs/C2_glide_by_remaining_years.csv` | 5대 운용사 2055 TDF 공시 글라이드 잔여연수별 값과 그 평균(`mean5`, 연구가 만든 파일) | 11(원 T2 계산, ⑤ TDF 비중) | 아니오 | 위 글라이드패스와 같은 이유(공시 값을 옮긴 것) | `01_downturn_timing/notebooks/pilot9/_build_C_real_inputs.py`(`glide_table`)가 공시 글라이드에서 만듦 |
| `raw/global_equity_20261016/french_region_mkt_monthly_usd.csv` | Fama–French 지역 시장 총수익 월(달러, Developed 등 7개 지역) | 11(원 T2 계산, French developed 원화 열) | 아니오 | 위 French와 같은 이유(허락 문구 없음) | `fetch/pilot9_global_equity.py` |
| `raw/kr_hist_20261016/kr_usdkrw_monthly_1964.csv` | 원/달러 환율 월 1964-05~ (ECOS 731Y004) | 11(원 T2 계산, 1990년 이전 환율) | 아니오 | ECOS라 2절 조건으로 넣을 수 있으나, 11 원 계산은 다른 입력 때문에 이 저장소만으로 돌지 않아 넣지 않음 | 원 연구 저장소 `fetch/pilot9_kr_hist.py`(이 저장소에 없음), ECOS API 731Y004 |
| `raw/simpletest_20261027/T2/`(7개) | 한국은행 환율제도 간행물 PDF·쪽 발췌, 한국은행·French Data Library 웹 페이지 저장본 | 11(원 T2 계산, 입력 해시 기록만 — 계산에 쓰지 않음) | 아니오 | 간행물·웹 페이지 저작권(재배포 조건 확인 안 함) | 한국은행 『한국의 외환제도와 외환시장』(2016), French Data Library 페이지 |
| `raw/kr_hist_20261016/kr_deposit_annual_kostat2015_1945_2014.csv` | 장기 예금 금리 연간 1945~2014 | 03 | 아니오 | 통계청 자료로 보이나 KOSIS DB인지 간행물인지 확인 못 함(간행물이면 공공누리 유형 따로) | 통계청 KOSIS(https://kosis.kr) |
| 「2026년 기초연금 사업안내」 원문 발췌 | 보건복지부 지침 PDF 발췌 | 03 | 아니오 | 게시물에 공공누리 표시 없음 → 사전 협의 필요(https://www.mohw.go.kr/menu.es?mid=a10103010400) | https://www.mohw.go.kr/board.es?mid=a10409020000&bid=0026&list_no=1488765&act=view 첨부 1 |
| 노란우산 약관·안내문 원문, 해약환급금 표 전체 | 중소기업중앙회 | 03 | 아니오 | 중기중앙회 이용약관: 허가 없는 게시물 사용·인용 금지(https://www.kbiz.or.kr/ko/contents/contents/contents.do?mnSeq=661). 재배포 조건 미확인 | https://www.8899.or.kr 해약환급금 안내(https://www.8899.or.kr/cmnsCnts/view?menuId=C080403000). 계산 재현에 꼭 필요한 공시 사실값 4개(36·60·72·168회 해약 때 이자 반영 비율 20·30·40·70%)만 `src/pension_lab/cand5p.py`의 `refund_int`, `03_selfemployed_50s/results/N/constants.csv`, `references/후보5_추가규칙_1차출처_20261106.md` 2-4절에 남기고 표 전체는 옮기지 않음 |

### 3-3. TDF 보수 판독 대조값 CSV 만들기 (`tdfext_fee_extract.py`용)

`src/pension_lab/fetch/tdfext_fee_extract.py`는 투자설명서 PDF에서 '합성 총보수·비용'을 자동으로 읽고, 사람이 PDF를 눈으로 읽어 적은 값과 대조합니다. 대조값은 금융투자협회 공시 내용이라(재배포 조건 확인 못 함) 코드에 넣지 않았습니다. 대조하려면 아래 CSV를 직접 만들어 `$PENSION_DATA_ROOT/raw/fund_tdf/tdfext_fee_expect.csv`에 둡니다. 파일이 없으면 대조 없이 추출만 하고 경고를 출력합니다.

1. 금융투자협회 전자공시(https://dis.kofia.or.kr)에서 코드의 `LOC`에 있는 표준코드마다 투자설명서(본문)를 받아 `$PENSION_DATA_ROOT/raw/fund_tdf/prospectus/{표준코드}_T.pdf`로 저장합니다(간이투자설명서는 `_G.pdf`).
2. 각 PDF의 제2부 '13. 보수 및 수수료 → 나. 집합투자기구에 부과되는 보수 및 비용' 표를 엽니다.
3. `LOC[표준코드]["periods"]`의 기간마다(기간 머리글 정규식이 첫째 인자, 시작일이 셋째 인자), 그 클래스 행(코드 주석의 '몇 번째 행')의 **'합성 총보수·비용'(%/년)** 값을 표에 적힌 그대로 옮깁니다. 세로형 표(`kind="vert"`)는 '합성 총보수ㆍ비용' 줄의 값입니다.
4. 열은 `standardCd,start,expect_fee_pct` 세 개, 한 기간에 한 행입니다. `start`는 `LOC`의 시작일 그대로(`OPEN_S`는 `1900-01-01`), 예: `K55203DN8867,2023-04-11,<표의 값>`.
5. 행 수는 `LOC`의 기간 수(현재 82개)와 같아야 합니다. 값이 PDF 추출값과 다르면 스크립트가 그 표준코드·기간을 적고 멈춥니다.

## 4. DataGuide 자료 받는 방법
DataGuide는 에프앤가이드의 유료 엑셀 애드인입니다(대학 도서관 등 기관 라이선스). 자동 수집 코드는 없고, 아래처럼 엑셀에서 받아 **가공하지 않고** 저장합니다. 로더(`src/pension_lab/io.py`의 `load_dg_series`)가 DataGuide 머리말 형식을 읽습니다.

1. 엑셀 → **DataGuide 탭 → 시계열(Time Series)**.
2. 코드 유형을 고르고 코드를 담습니다.
   - 지수(IDX): `코스피`, `코스피 200`, `코스피 200 TR`(`I.158`)
   - 채권지수: 국고채 총수익지수 `FBI.KTB.01.2`
   - ETF/주식: `KODEX 200`(수정주가)
   - 경제 항목: 시장 평균배당수익률, CD 91일, 국민주택채권 5년, 국고채 3년·5년, 회사채 AA- 금리
3. 아이템: 지수는 **종가지수(포인트)**(`I31000040F`), ETF는 수정주가, 경제 항목은 해당 값.
4. 출력주기 **일간**(배당수익률은 월간·말일), 비영업일 **제외**, 원화, 오름차순, 기간 `19800101` ~ 최근.
5. 시트에 뿌린 뒤 머리말(코드·아이템·집계주기 줄)을 지우지 말고 그대로 저장합니다. 파일 이름은 3-1절 표의 이름, 위치는 `$PENSION_DATA_ROOT/dataguide/`.
6. `dg_econ_divyield_rates_19900101.csv`·`dg_kospi_k200_tr_daily_19800104.csv`는 원 연구에서 한 엑셀 파일(`kospi_k200_tr_1980.xlsx`)의 두 시트를 CSV로 옮긴 것입니다.

위 코드 가운데 `I.158`, `I31000040F`, `FBI.KTB.01.2`는 받은 파일 머리말에서 확인한 값이고, 나머지 코드명은 받을 때 머리말에서 확인해야 합니다.

## 5. 재배포 조건 확인 요약 (2026-11-07)

| 출처 | 판정 | 근거 |
|---|---|---|
| 한국은행 ECOS | 조건부 가능(출처 표시, 가공 표시) | 한국은행 저작권정책(위 2절) |
| 국가법령정보센터 법령 원문 | 가능 | 저작권법 제7조, law.go.kr 저작권정책 |
| 보건복지부 사업안내 | 사전 협의 필요 | 공공누리 표시 없음 |
| 금융투자협회 공시 | 확인 못 함 | 이용약관·저작권정책 페이지 없음 |
| DART 공시(투자설명서·운용보고서) | 확인 못 함 | 재배포 조항 없음, 저작권법·공공데이터법에 맡김 |
| FRED | 불가(FRED에서 받은 파일) | FRED 이용약관 |
| BLS CPI | 가능(원 출처에서 받을 때) | 공공 영역, 출처 표시 요청 |
| OECD | 조건부(CC BY 4.0, 2차 확인) | 2024-07 발표(원문 403) |
| Kenneth French Data Library | 확인 못 함 | 허락 문구 없음 |
| Yahoo Finance | 불가 | 약관 2(d)(ix)(x) |
| 한국거래소 | 불가(사전 동의 필요) | KRX 법적고지 |
| 통계청 KOSIS | 조건부 가능(출처 표시) | KOSIS 이용안내 — 해당 파일의 원천 확인 못 해 넣지 않음 |
| 중소기업중앙회(노란우산) | 불가(허가 필요) | 중기중앙회 이용약관 제15조 |
| 에프앤가이드 DataGuide | 확인 못 함 → 넣지 않음 | 약관 페이지 접속 실패, 유료 라이선스 |

## 6. 글에 인용한 상품 조건 (파일 아님)

| 값 | 쓰는 곳 | 출처 | 비고 |
|---|---|---|---|
| 연금저축계좌 담보대출: 연 5.00%(2026.01.01 기준), 한도 펀드평가액의 50%·최대 4,000만 원, 담보유지비율 140%, 기간 365일 | 04 (`src/pension_lab/pilot7.py` `LOAN`·`LOAN_LTV`·`LOAN_MAINT`·`LOAN_TERM_M`, 04 스크립트 `LOAN_CAP`) | 신한투자증권 연금저축계좌 서비스 안내 https://www.shinhansec.com/siw/pension/saving-info/saving_account_service1/view.do (1차, 원 연구의 2026-10-08 근거 대장 기록값) | 원문 스냅샷은 넣지 않음(재배포 조건 확인 안 함). 2026-11-08에 다시 열어 보지 못함. 중도상환수수료는 확인하지 못해 0으로 둠 |
| 비교 대출 금리: 은행 일반신용대출 연 6.33%, 소액대출 연 6.55%(예금은행 신규취급액 기준, 2026년 8월) | 04 `results/pilot7/T1_boot.csv`의 비교 행 (`src/pension_lab/pilot7.py` `LOAN`) | 한국은행 ECOS 121Y006(`BECBLA03051`·`BECBLA0301`) — 코드 주석 | 값 2개만 코드에 둠(2절 ECOS 조건). '그때 단기금리+가산폭' 행은 같은 달 CD91 평균과의 차이를 가산폭으로 씀 |
| 세율: 연금저축 세액공제 16.5%·13.2%, 55세 전 인출(기타소득세) 16.5%, 연금소득세 5.5%, 일반계좌 배당소득세 15.4% | 04·05 (`src/pension_lab/aftertax.py` `CREDIT_LOW`·`CREDIT_HIGH`·`ETC_TAX`·`PENSION_UNDER70`·`TAX_FINANCIAL`) | 소득세법 §59의3①·§21①21·§129①5의2·§129①6나 등(국가법령정보센터) — 조문은 코드 주석 | 2026년 기준. 세법 개정 반영 안 함 |
