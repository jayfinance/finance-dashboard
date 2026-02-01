import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
import requests
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
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open("FinanceRaw")

# -------------------------------
# 사이드바
# -------------------------------
menu = st.sidebar.radio("메뉴 선택", ["Table"])
submenu = st.sidebar.selectbox("자산 구분", ["국내 투자자산", "해외 투자자산", "가상자산"])

st.sidebar.markdown("### 🟡 금(보정 옵션)")
local_gold_override = st.sidebar.number_input(
    "국내 금 시세 수동 입력 (원/g)\n0 입력 시 국제 금 환산값 사용",
    min_value=0,
    step=1000,
    value=0
)

# -------------------------------
# 공통 함수
# -------------------------------
@st.cache_data(ttl=600)
def get_usdkrw():
    try:
        return float(yf.Ticker("USDKRW=X").history(period="5d")["Close"].dropna().iloc[-1])
    except:
        return None

@st.cache_data(ttl=600)
def get_gold_price_krw_per_g():
    try:
        gold_usd = float(yf.Ticker("GC=F").history(period="5d")["Close"].dropna().iloc[-1])
        usdkrw = get_usdkrw()
        return (gold_usd * usdkrw) / 31.1035 if usdkrw else None
    except:
        return None

@st.cache_data(ttl=600)
def get_kr_price(ticker, name, gold_override):
    try:
        if name == "금현물" or str(ticker).upper() == "GOLD":
            return float(gold_override) if gold_override > 0 else get_gold_price_krw_per_g()
        return float(yf.Ticker(f"{str(ticker).zfill(6)}.KS").history(period="1d")["Close"].iloc[-1])
    except:
        return None

@st.cache_data(ttl=600)
def get_us_price(ticker):
    try:
        return float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
    except:
        return None

# -------------------------------
# CoinGecko 통화별 호출
# -------------------------------
@st.cache_data(ttl=300)
def get_crypto_prices_usd(ids):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": ",".join(ids), "vs_currencies": "usd"}
        return requests.get(url, params=params).json()
    except:
        return {}

@st.cache_data(ttl=300)
def get_crypto_prices_krw(ids):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": ",".join(ids), "vs_currencies": "krw"}
        return requests.get(url, params=params).json()
    except:
        return {}

# -------------------------------
# 포맷 함수
# -------------------------------
def fmt_num(x):
    if pd.isna(x): return "-"
    try: return f"{x:,.0f}"
    except: return "-"

def fmt_pct(x):
    if pd.isna(x): return "-"
    try: return f"{x:.2f}%"
    except: return "-"

# =========================================================
# 🪙 가상자산
# =========================================================
if menu == "Table" and submenu == "가상자산":
    usdkrw = get_usdkrw()

    left, right = st.columns([4,1])
    with left:
        st.subheader("📋 가상자산 평가 테이블")
    with right:
        st.markdown(
            f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {usdkrw:,.2f} KRW/USD</div>" if usdkrw
            else "<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: -</div>",
            unsafe_allow_html=True
        )

    sheet = spreadsheet.worksheet("가상자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    # ❌ 비고 컬럼 제거
    if "비고" in df.columns:
        df.drop(columns=["비고"], inplace=True)

    required = ["증권사","소유","코인","심볼","coingecko_id","통화","수량(qty)","평균매수가(avg_price)"]
    df = df[required].copy()

    df["수량(qty)"] = pd.to_numeric(df["수량(qty)"].str.replace(",", ""), errors="coerce")
    df["평균매수가(avg_price)"] = pd.to_numeric(df["평균매수가(avg_price)"].str.replace(",", ""), errors="coerce")

    ids_usd = df[df["통화"].str.upper()=="USD"]["coingecko_id"].dropna().unique().tolist()
    ids_krw = df[df["통화"].str.upper()=="KRW"]["coingecko_id"].dropna().unique().tolist()

    price_usd = get_crypto_prices_usd(ids_usd) if ids_usd else {}
    price_krw = get_crypto_prices_krw(ids_krw) if ids_krw else {}

    def get_price(row):
        cid = row["coingecko_id"]
        currency = row["통화"].upper()
        if currency == "KRW":
            return price_krw.get(cid, {}).get("krw")
        return price_usd.get(cid, {}).get("usd")

    df["현재가"] = df.apply(get_price, axis=1)

    df["매입총액"] = df["수량(qty)"] * df["평균매수가(avg_price)"]
    df["평가총액"] = df["수량(qty)"] * df["현재가"]
    df["평가총액(KRW)"] = df.apply(
        lambda r: r["평가총액"] if r["통화"].upper()=="KRW" else r["평가총액"] * usdkrw,
        axis=1
    )

    total_buy = df["매입총액"].sum()
    total_eval = df["평가총액(KRW)"].sum()
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-weight:bold;'>
        <div>가상 자산 매입총액: {fmt_num(total_buy)} 원</div>
        <div>가상 자산 평가총액: {fmt_num(total_eval)} 원</div>
        <div>가상 자산 전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    # 표시 포맷 적용
    display_df = df.copy()
    display_df["수량(qty)"] = display_df["수량(qty)"].apply(lambda x: f"{x:,.9f}" if pd.notna(x) else "-")

    for col in ["평균매수가(avg_price)", "현재가", "매입총액", "평가총액", "평가총액(KRW)"]:
        display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")

    st.dataframe(display_df, use_container_width=True)
