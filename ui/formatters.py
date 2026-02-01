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
