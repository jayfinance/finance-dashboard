import math
import pandas as pd

def _to_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, str):
            x = x.replace(",", "").replace("%", "").strip()
            if x == "":
                return None
        if pd.isna(x):
            return None
        return float(x)
    except:
        return None


def fmt_num(x):  # 천단위 콤마, 정수
    v = _to_float(x)
    return "-" if v is None else f"{v:,.0f}"


def fmt_num2(x):  # 천단위 콤마 + 소수점 2자리
    v = _to_float(x)
    return "-" if v is None else f"{v:,.2f}"


def fmt_pct(x):  # 퍼센트 소수점 2자리
    v = _to_float(x)
    return "-" if v is None else f"{v:.2f}%"


def korean_yaxis(max_val: float, min_val: float = 0) -> dict:
    """Plotly yaxis layout dict with Korean 억원/만원 tick labels."""
    max_abs = max(abs(max_val), abs(min_val))
    if max_abs == 0:
        return {}

    div    = 1e8 if max_abs >= 1e8 else 1e4
    suffix = "억원" if div == 1e8 else "만원"

    scaled = max_abs / div
    mag    = 10 ** math.floor(math.log10(max(scaled, 1e-9)))
    step_s = 1
    for nice in [1, 2, 5, 10]:
        step_s = nice * mag
        if scaled / step_s <= 6:
            break
    step = step_s * div

    lo = math.floor(min_val / step) - 1
    hi = math.ceil(max_val / step) + 1
    tick_vals = [i * step for i in range(lo, hi + 1)]
    tick_text = [f"{v / div:,.0f}{suffix}" for v in tick_vals]
    return dict(tickvals=tick_vals, ticktext=tick_text)
