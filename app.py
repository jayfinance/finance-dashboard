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
# 메뉴 구성
# -------------------------------
menu = st.sidebar.radio("메뉴 선택", ["Table"])
submenu = st.sidebar.selectbox("자산 구분", ["국내자산"])

# -------------------------------
# 국제 금 가격 → 원화 g당 가격
# -------------------------------
@st.cache_data(ttl=600)
def get_gold_price_krw_per_g():
    try:
        gold_usd = yf.Ticker("GC=F").history(period="1d")["Close"].iloc[-1]
        usdkrw = yf.Ticker("USDKRW=X").history(period="1d")["Close"].iloc[-1]
        return (gold_usd * usdkrw) / 31.1035
    except:
        return None

# -------------------------------
# 현재가 조회 함수
# -------------------------------
@st.cache_data(ttl=600)
def get_current_price(ticker, name):
    try:
        # 금현물 처리
        if name == "금현물" or ticker.upper() == "GOLD":
            return get_gold_price_krw_per_g()

        ticker_yf = f"{ticker}.KS"
        price = yf.Ticker(ticker_yf).history(period="1d")["Close"].iloc[-1]
        return price
    except:
        return None

# -------------------------------
# 국내자산 처리
# -------------------------------
if menu == "Table" and submenu == "국내자산":
    sheet = spreadsheet.worksheet("국내자산")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        st.warning("국내자산 시트에 데이터가 없습니다.")
        st.stop()

    df = df[[
        "증권사", "소유", "종목명", "종목코드", "계좌구분",
        "성격", "보유수량", "매수단가"
    ]]

    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["보유수량"] = pd.to_numeric(df["보유수량"], errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"], errors="coerce")

    df["매입총액 (KRW)"] = df["보유수량"] * df["매수단가"]

    df["현재가"] = df.apply(lambda row: get_current_price(row["종목코드"], row["종목명"]), axis=1)
    df["평가총액 (KRW)"] = df["보유수량"] * df["현재가"]
    df["평가손익 (KRW)"] = df["평가총액 (KRW)"] - df["매입총액 (KRW)"]
    df["수익률 (%)"] = (df["평가총액 (KRW)"] / df["매입총액 (KRW)"] - 1) * 100

    # -------------------------------
    # 포맷 함수
    # -------------------------------
    def format_comma(x):
        try:
            return f"{int(x):,}"
        except:
            return x

    def format_comma_float(x):
        try:
            return f"{x:,.2f}"
        except:
            return x

    df["보유수량"] = df["보유수량"].apply(format_comma)
    df["매수단가"] = df["매수단가"].apply(format_comma)
    df["매입총액 (KRW)"] = df["매입총액 (KRW)"].apply(format_comma)
    df["현재가"] = df["현재가"].apply(format_comma)
    df["평가총액 (KRW)"] = df["평가총액 (KRW)"].apply(format_comma)
    df["평가손익 (KRW)"] = df["평가손익 (KRW)"].apply(format_comma)
    df["수익률 (%)"] = df["수익률 (%)"].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

    st.subheader("📋 국내자산 평가 테이블")
    st.dataframe(df, use_container_width=True)
