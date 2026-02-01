import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import requests

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
submenu = st.sidebar.selectbox("자산 구분", ["국내 투자자산"])

# -------------------------------
# 국제 금 가격 → 원화 g당 가격
# -------------------------------
@st.cache_data(ttl=600)
def get_gold_price_krw_per_g():
    try:
        # 금 가격을 최근 평균 값으로 설정 (2026년 기준 약 2,500 USD/oz)
        gold_usd_per_oz = 2500  # USD per ounce
        
        # 환율 가져오기 (yfinance 사용)
        usdkrw = yf.Ticker("USDKRW=X").history(period="1d")["Close"].iloc[-1]
        
        # 1 온스 = 31.1035 그램
        return (gold_usd_per_oz * usdkrw) / 31.1035
    except Exception as e:
        print(f"Error fetching gold price: {e}")
        # 실패 시 최근 평균 가격 사용 (예: 100,000 원/g)
        return 100000

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
if menu == "Table" and submenu == "국내 투자자산":
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
    # 합계 및 최종 수익률 계산
    # -------------------------------
    total_buy = df["매입총액 (KRW)"].sum()
    total_eval = df["평가총액 (KRW)"].sum()
    total_profit = df["평가손익 (KRW)"].sum()
    final_yield = (total_eval / total_buy - 1) * 100 if total_buy != 0 else 0

    # 포맷 함수 재사용
    def format_comma(x):
        try:
            return f"{int(x):,}"
        except:
            return x

    st.markdown(f"""
    <div style='display: flex; gap: 32px; font-size: 1.1em; font-weight: bold;'>
        <div>매입총액 합계: {format_comma(total_buy)} 원</div>
        <div>평가총액 합계: {format_comma(total_eval)} 원</div>
        <div>평가손익 합계: {format_comma(total_profit)} 원</div>
        <div>최종 수익률: {final_yield:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

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

    st.subheader("📋 국내 투자자산 평가 테이블")
    st.dataframe(df, use_container_width=True)
