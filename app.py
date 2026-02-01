import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("📊 Finance Dashboard")

# -------------------------------
# Google Sheets 연결
# -------------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)
spreadsheet = client.open("FinanceRaw")

# -------------------------------
# 사이드바 메뉴
# -------------------------------
menu = st.sidebar.radio("메뉴 선택", ["Table"])
submenu = st.sidebar.selectbox("자산 구분", ["국내 투자자산"])

st.sidebar.markdown("### 🟡 금(보정 옵션)")
local_gold_override = st.sidebar.number_input(
    "국내 금 시세 수동 입력 (원/g)\n0 입력 시 국제 금 환산값 사용",
    min_value=0,
    step=1000,
    value=0
)

# -------------------------------
# 국제 금 가격 → 원화 g당 가격
# -------------------------------
@st.cache_data(ttl=600)
def get_gold_price_krw_per_g():
    try:
        gold_hist = yf.Ticker("GC=F").history(period="5d")
        fx_hist = yf.Ticker("USDKRW=X").history(period="5d")

        gold_usd_per_oz = float(gold_hist["Close"].dropna().iloc[-1])
        usdkrw = float(fx_hist["Close"].dropna().iloc[-1])

        return (gold_usd_per_oz * usdkrw) / 31.1035
    except:
        return None

# -------------------------------
# 현재가 조회 함수
# -------------------------------
@st.cache_data(ttl=600)
def get_current_price(ticker, name, gold_override):
    try:
        if name == "금현물" or ticker.upper() == "GOLD":
            if gold_override and gold_override > 0:
                return float(gold_override)
            return get_gold_price_krw_per_g()

        ticker_yf = f"{ticker}.KS"
        return yf.Ticker(ticker_yf).history(period="1d")["Close"].iloc[-1]
    except:
        return None

# -------------------------------
# 국내 투자자산 처리
# -------------------------------
if menu == "Table" and submenu == "국내 투자자산":
    sheet = spreadsheet.worksheet("국내자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])

    if df.empty:
        st.warning("국내자산 시트에 데이터가 없습니다.")
        st.stop()

    df.columns = df.columns.str.strip()

    df = df[[
        "증권사", "소유", "종목명", "종목코드", "계좌구분",
        "성격", "보유수량", "매수단가"
    ]]

    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].astype(str).str.replace(",", ""), errors="coerce")

    df["매입총액 (KRW)"] = df["보유수량"] * df["매수단가"]

    # 🔥 apply 대신 안전한 방식으로 현재가 계산
    prices = []
    for ticker, name in zip(df["종목코드"], df["종목명"]):
        prices.append(get_current_price(ticker, name, local_gold_override))

    df["현재가"] = pd.to_numeric(prices, errors="coerce")

    df["평가총액 (KRW)"] = df["보유수량"] * df["현재가"]
    df["평가손익 (KRW)"] = df["평가총액 (KRW)"] - df["매입총액 (KRW)"]
    df["수익률 (%)"] = (df["평가총액 (KRW)"] / df["매입총액 (KRW)"] - 1) * 100

    # -------------------------------
    # 합계
    # -------------------------------
    total_buy = df["매입총액 (KRW)"].sum()
    total_eval = df["평가총액 (KRW)"].sum()
    total_profit = df["평가손익 (KRW)"].sum()
    final_yield = (total_eval / total_buy - 1) * 100 if total_buy != 0 else 0

    def format_comma(x):
        if pd.isna(x):
            return "-"
        return f"{x:,.0f}"

    st.markdown(f"""
    <div style='display: flex; gap: 32px; font-size: 1.1em; font-weight: bold;'>
        <div>매입총액 합계: {format_comma(total_buy)} 원</div>
        <div>평가총액 합계: {format_comma(total_eval)} 원</div>
        <div>평가손익 합계: {format_comma(total_profit)} 원</div>
        <div>최종 수익률: {final_yield:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------
    # 표시용 DataFrame
    # -------------------------------
    display_df = df.copy()
    display_df["보유수량"] = display_df["보유수량"].apply(format_comma)
    display_df["매수단가"] = display_df["매수단가"].apply(format_comma)
    display_df["매입총액 (KRW)"] = display_df["매입총액 (KRW)"].apply(format_comma)
    display_df["현재가"] = display_df["현재가"].apply(format_comma)
    display_df["평가총액 (KRW)"] = display_df["평가총액 (KRW)"].apply(format_comma)
    display_df["평가손익 (KRW)"] = display_df["평가손익 (KRW)"].apply(format_comma)
    display_df["수익률 (%)"] = display_df["수익률 (%)"].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

    st.subheader("📋 국내 투자자산 평가 테이블")
    st.dataframe(display_df, use_container_width=True)
