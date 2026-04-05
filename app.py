import streamlit as st

# -------------------------------
# 서비스 계층
# -------------------------------
from service.sheets import get_spreadsheet
from service.market_data import get_usdkrw, get_kr_price, get_us_price
from service.crypto_data import get_crypto_prices

# -------------------------------
# 자산 테이블
# -------------------------------
from assets_table.domestic import render as domestic_table
from assets_table.overseas import render as overseas_table
from assets_table.crypto import render as crypto_table
from assets_table.cash import render as cash_table
from assets_table.property import render as property_table
from assets_table.etc import render as etc_table
from assets_table.debt import render as debt_table
from assets_table.total import render as total_table
from assets_table.trend import render as trend_table

# -------------------------------
# 자산 차트
# -------------------------------
from assets_chart.domestic_chart import render as domestic_chart
from assets_chart.overseas_chart import render as overseas_chart
from assets_chart.crypto_chart import render as crypto_chart
from assets_chart.cash_chart import render as cash_chart
from assets_chart.property_chart import render as property_chart
from assets_chart.etc_chart import render as etc_chart
from assets_chart.debt_chart import render as debt_chart
from assets_chart.total_chart import render as total_chart
from assets_chart.trend_chart import render as trend_chart

# -------------------------------
# 배당 테이블
# -------------------------------
from divident_table.domestic_dv import render as domestic_dv_table
from divident_table.overseas_dv import render as overseas_dv_table

# -------------------------------
# 배당 차트
# -------------------------------
from divident_chart.domestic_dv_chart import render as domestic_dv_chart
from divident_chart.overseas_dv_chart import render as overseas_dv_chart

# =========================================================
# 앱 초기화
# =========================================================
st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("📊 Finance Dashboard")

spreadsheet = get_spreadsheet()

# =========================================================
# 사이드바 메뉴
# =========================================================
st.sidebar.markdown("## 📂 메뉴")
section = st.sidebar.radio("대분류", ["Table", "Chart"])

page = None

if section == "Table":
    with st.sidebar.expander("💼 자산", expanded=True):
        page = st.radio(
            "선택",
            [
                "국내 투자자산",
                "해외 투자자산",
                "가상자산",
                "현금성자산",
                "부동산자산",
                "기타자산",
                "부채",
                "종합",
                "추이",
            ],
            key="table_assets"
        )
    with st.sidebar.expander("💰 배당"):
        div_page = st.radio(
            "선택",
            ["국내 배당", "해외 배당"],
            key="table_div"
        )
        if div_page:
            page = div_page

elif section == "Chart":
    with st.sidebar.expander("💼 자산 차트", expanded=True):
        page = st.radio(
            "선택",
            [
                "국내 투자자산 차트",
                "해외 투자자산 차트",
                "가상자산 차트",
                "현금성자산 차트",
                "부동산자산 차트",
                "기타자산 차트",
                "부채 차트",
                "종합 차트",
                "추이 차트",
            ],
            key="chart_assets"
        )
    with st.sidebar.expander("💰 배당 차트"):
        div_chart_page = st.radio(
            "선택",
            ["국내 배당 차트", "해외 배당 차트"],
            key="chart_div"
        )
        if div_chart_page:
            page = div_chart_page

# -------------------------------
# 금 수동 입력 옵션
# -------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🟡 금 보정 옵션")
gold_override = st.sidebar.number_input(
    "국내 금 시세 수동 입력 (원/g)\n0 입력 시 국제 금 환산값 사용",
    min_value=0,
    step=1000,
    value=0
)

# =========================================================
# 라우팅 — 자산 테이블
# =========================================================
if page == "국내 투자자산":
    domestic_table(spreadsheet, get_kr_price, gold_override)

elif page == "해외 투자자산":
    overseas_table(spreadsheet, get_usdkrw, get_us_price)

elif page == "가상자산":
    crypto_table(spreadsheet, get_usdkrw, get_crypto_prices)

elif page == "현금성자산":
    cash_table(spreadsheet, get_usdkrw)

elif page == "부동산자산":
    property_table(spreadsheet, get_usdkrw)

elif page == "기타자산":
    etc_table(spreadsheet, get_usdkrw)

elif page == "부채":
    debt_table(spreadsheet, get_usdkrw)

elif page == "종합":
    total_table(spreadsheet, get_usdkrw, get_kr_price, get_us_price, get_crypto_prices, gold_override)

elif page == "추이":
    trend_table(spreadsheet)

# =========================================================
# 라우팅 — 배당 테이블
# =========================================================
elif page == "국내 배당":
    domestic_dv_table(spreadsheet)

elif page == "해외 배당":
    overseas_dv_table(spreadsheet, get_usdkrw)

# =========================================================
# 라우팅 — 자산 차트
# =========================================================
elif page == "국내 투자자산 차트":
    domestic_chart(spreadsheet, get_kr_price, gold_override)

elif page == "해외 투자자산 차트":
    overseas_chart(spreadsheet, get_usdkrw, get_us_price)

elif page == "가상자산 차트":
    crypto_chart(spreadsheet, get_usdkrw, get_crypto_prices)

elif page == "현금성자산 차트":
    cash_chart(spreadsheet, get_usdkrw)

elif page == "부동산자산 차트":
    property_chart(spreadsheet, get_usdkrw)

elif page == "기타자산 차트":
    etc_chart(spreadsheet, get_usdkrw)

elif page == "부채 차트":
    debt_chart(spreadsheet, get_usdkrw)

elif page == "종합 차트":
    total_chart(spreadsheet, get_usdkrw, get_kr_price, get_us_price, get_crypto_prices, gold_override)

elif page == "추이 차트":
    trend_chart(spreadsheet)

# =========================================================
# 라우팅 — 배당 차트
# =========================================================
elif page == "국내 배당 차트":
    domestic_dv_chart(spreadsheet)

elif page == "해외 배당 차트":
    overseas_dv_chart(spreadsheet, get_usdkrw)
