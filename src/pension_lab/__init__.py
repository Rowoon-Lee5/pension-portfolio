"""pension_lab — 연금 자산배분/방어 오버레이 연구 공통 코드.

하위 모듈:
- paths     : 데이터 루트·경로 (환경변수 PENSION_DATA_ROOT로 override)
- io        : 데이터 로더 (DataGuide xlsx / CSV / 자산군 시계열)
- backtest  : 백테스트 엔진 (수익률→지수, 거래비용·리밸런싱·MDD·지표)
- glidepath : 합성 TDF(글라이드패스)
- fetch/    : 원천 데이터 수집 스크립트 (재현용)
"""
__all__ = ["paths", "io", "backtest", "glidepath", "aftertax", "decumulation",
           "lifecycle", "bootstrap", "perfstats", "regime_ml"]
__version__ = "0.1.0"
