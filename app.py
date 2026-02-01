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
    cash_table(spreadsheet, get_usdkrw)

# =========================================================
# 📊 차트 라우팅 (추후 구현)
# =========================================================
# elif page == "국내 투자자산 차트":
#     domestic_chart(...)
# elif page == "해외 투자자산 차트":
#     overseas_chart(...)
# elif page == "가상자산 차트":
#     crypto_chart(...)
# elif page == "현금성자산 차트":
#     cash_chart(...)