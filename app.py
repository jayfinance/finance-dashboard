import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
import requests
from google.oauth2.service_account import Credentials

# -------------------------------
# 모듈 import
# -------------------------------
from service.sheets import get_spreadsheet
from service.market import (
    get_usdkrw,
    get_kr_price,
    get_us_price,
    get_gold_price_krw_per_g,
    get_crypto_prices
)

from ui.formatters import fmt_num, fmt_pct, fmt_num2

from tables.domestic import render as domestic_table
from tables.overseas import render as overseas_table
from tables.crypto import render as crypto_table
from tables.cash import render as cash_table

st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("📊 Finance Dashboard")

# -------------------------------
# Google Sheets 연결
# -------------------------------
spreadsheet = get_spreadsheet()

# =========================================================
# 🌲 사이드바 트리 메뉴
# =========================================================
st.sidebar.markdown("## 📂 메뉴")
section = st.sidebar.radio("대분류", ["Chart", "Table"])

page = None

if section == "Chart":
    with st.sidebar.expander("자산 - Overview Chart", expanded=True):
        page = st.radio(
            "선택",
            ["국내 투자자산 차트", "해외 투자자산 차트", "가상자산 차트", "현금성자산 차트"],
            key="chart_assets"
        )
    with st.sidebar.expander("배당"):
        st.radio(
            "선택",
            ["국내 배당 차트", "해외 배당 차트"],
            key="chart_div"
        )

elif section == "Table":
    with st.sidebar.expander("자산", expanded=True):
        page = st.radio(
            "선택",
            ["국내 투자자산", "해외 투자자산", "가상자산", "현금성자산"],
            key="table_assets"
        )

    with st.sidebar.expander("배당"):
        st.radio(
            "선택",
            ["국내 배당", "해외 배당"],
            key="table_div"
        )

# -------------------------------
# 금 수동 입력 옵션
# -------------------------------
st.sidebar.markdown("### 🟡 금(보정 옵션)")
gold_override = st.sidebar.number_input(
    "국내 금 시세 수동 입력 (원/g)\n0 입력 시 국제 금 환산값 사용",
    min_value=0,
    step=1000,
    value=0
)

# =========================================================
# 📋 테이블 라우팅
# =========================================================
if page == "국내 투자자산":
    domestic_table(spreadsheet, get_kr_price, gold_override)

elif page == "해외 투자자산":
    overseas_table(spreadsheet, get_usdkrw, get_us_price)

elif page == "가상자산":
    crypto_table(spreadsheet, get_usdkrw, get_crypto_prices)

elif page == "현금성자산":
    # cash_table(spreadsheet, get_usdkrw)
    usdkrw = get_usdkrw()

    left, right = st.columns([4, 1])
    with left:
        st.subheader("📋 현금성자산 테이블")
    with right:
        st.markdown(
            f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {usdkrw:,.2f} KRW/USD</div>"
            if usdkrw else "현재 환율: -",
            unsafe_allow_html=True
        )

    sheet = spreadsheet.worksheet("현금성자산")
    rows = sheet.get_all_values()
    raw_df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required_cols = ["증권사", "소유", "계좌구분", "통화", "성격", "금액"]
    missing = [c for c in required_cols if c not in raw_df.columns]
    if missing:
        st.error(f"현금성자산 시트에 다음 컬럼이 없습니다: {missing}")
        st.stop()

    df = raw_df[required_cols].copy()
    df["금액"] = pd.to_numeric(df["금액"].astype(str).str.replace(",", ""), errors="coerce")

    df["금액(KRW)"] = df.apply(
        lambda r: r["금액"] if str(r["통화"]).upper() == "KRW"
        else (r["금액"] * usdkrw if usdkrw else float("nan")),
        axis=1
    )

    total_cash_krw = df["금액(KRW)"].sum()

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>현금성자산 총액 (KRW): {fmt_num(total_cash_krw)} 원</div>
    </div>
    """, unsafe_allow_html=True)

    display_df = df.copy()
    display_df["금액"] = display_df["금액"].apply(fmt_num)
    display_df["금액(KRW)"] = display_df["금액(KRW)"].apply(fmt_num)

    st.dataframe(display_df, use_container_width=True)

# =========================================================
# 📊 차트 라우팅 (추후 구현)
# =========================================================
elif page == "국내 투자자산 차트":
    st.info("국내 투자자산 차트 기능은 추후 구현 예정입니다.")
elif page == "해외 투자자산 차트":
    st.info("해외 투자자산 차트 기능은 추후 구현 예정입니다.")
elif page == "가상자산 차트":
    st.info("가상자산 차트 기능은 추후 구현 예정입니다.")
elif page == "현금성자산 차트":
    st.info("현금성자산 차트 기능은 추후 구현 예정입니다.")