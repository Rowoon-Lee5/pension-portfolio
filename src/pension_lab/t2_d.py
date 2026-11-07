"""공개판 발췌: 원본 `t2_d.py`(공개 범위 밖 주제)에서 `settle_return` 한 함수만 남겼다.

`01_downturn_timing/notebooks/pilot9/_build_C_real_inputs.py`가 이 함수만 import한다. 식은 원본과 같다.
"""
from __future__ import annotations
import numpy as np


def settle_return(nav_prev, nav_t, kofia_adj, form: str = "add"):
    """덧셈식 결산일 수익 R = (nav_t + kofia_adj)/nav_{t−1} − 1 (기준가 + 공시 분배액)."""
    if form != "add":
        raise ValueError("덧셈식(form='add')만 채택됨")
    return (np.asarray(nav_t, float) + np.asarray(kofia_adj, float)) / np.asarray(nav_prev, float) - 1
