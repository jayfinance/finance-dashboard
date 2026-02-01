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

@st.cache_data(ttl=300)
def get_crypto_prices(ids):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": ",".join(ids), "vs_currencies": "usd,krw"}
        return requests.get(url, params=params).json()
    except:
        return {}

def fmt_num(x):
    if pd.isna(x): return "-"
    try: return f"{x:,.0f}"
    except: return "-"

def fmt_pct(x):
    if pd.isna(x): return "-"
    try: return f"{x:.2f}%"
    except: return "-"

# =========================================================
# 🇰🇷 국내 투자자산
# =========================================================
if menu == "Table" and submenu == "국내 투자자산":
    sheet = spreadsheet.worksheet("국내자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required = ["증권사","소유","종목명","종목코드","계좌구분","성격","보유수량","매수단가"]
    df = df[required].copy()

    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")

    df["매입총액"] = df["보유수량"] * df["매수단가"]
    df["현재가"] = [get_kr_price(t, n, local_gold_override) for t, n in zip(df["종목코드"], df["종목명"])]
    df["평가총액"] = df["보유수량"] * df["현재가"]
    df["수익률"] = (df["평가총액"] / df["매입총액"] - 1) * 100

    total_buy = df["매입총액"].sum()
    total_eval = df["평가총액"].sum()
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-weight:bold;'>
        <div>국내 자산 매입총액: {fmt_num(total_buy)} 원</div>
        <div>국내 자산 평가총액: {fmt_num(total_eval)} 원</div>
        <div>국내 자산 전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(df, use_container_width=True)

# =========================================================
# 🌍 해외 투자자산
# =========================================================
if menu == "Table" and submenu == "해외 투자자산":
    usdkrw = get_usdkrw()
    view_option = st.radio("표시 통화 옵션", ["모두 보기", "LC로 보기", "KRW로 보기"], horizontal=True)

    sheet = spreadsheet.worksheet("해외자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
    df.rename(columns={"매입가": "매수단가"}, inplace=True)

    df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")
    df["매입환율"] = pd.to_numeric(df["매입환율"].str.replace(",", ""), errors="coerce")

    df["매입총액(LC)"] = df["보유수량"] * df["매수단가"]
    df["현재가"] = df["종목티커"].apply(get_us_price)
    df["평가총액(LC)"] = df["보유수량"] * df["현재가"]
    df["평가총액(KRW)"] = df["평가총액(LC)"] * usdkrw

    total_buy = (df["매입총액(LC)"] * df["매입환율"]).sum()
    total_eval = df["평가총액(KRW)"].sum()
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0

    left, right = st.columns([4,1])
    with left: st.subheader("📋 해외 투자자산 평가 테이블")
    with right: st.markdown(f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {usdkrw:,.2f} KRW/USD</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-weight:bold;'>
        <div>해외 자산 매입총액: {fmt_num(total_buy)} 원</div>
        <div>해외 자산 평가총액: {fmt_num(total_eval)} 원</div>
        <div>해외 자산 전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(df, use_container_width=True)

# =========================================================
# 🪙 가상자산
# =========================================================
if menu == "Table" and submenu == "가상자산":
    usdkrw = get_usdkrw()

    left, right = st.columns([4,1])
    with left: st.subheader("📋 가상자산 평가 테이블")
    with right: st.markdown(f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {usdkrw:,.2f} KRW/USD</div>", unsafe_allow_html=True)

    sheet = spreadsheet.worksheet("가상자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    df["수량(qty)"] = pd.to_numeric(df["수량(qty)"].str.replace(",", ""), errors="coerce")
    df["평균매수가(avg_price)"] = pd.to_numeric(df["평균매수가(avg_price)"].str.replace(",", ""), errors="coerce")

    price_data = get_crypto_prices(df["coingecko_id"].dropna().unique().tolist())

    def get_price(row):
        cid = row["coingecko_id"]
        return price_data.get(cid, {}).get("krw" if row["통화"].upper()=="KRW" else "usd")

    df["현재가"] = df.apply(get_price, axis=1)
    df["매입총액"] = df["수량(qty)"] * df["평균매수가(avg_price)"]
    df["평가총액"] = df["수량(qty)"] * df["현재가"]
    df["평가총액(KRW)"] = df.apply(lambda r: r["평가총액"] if r["통화"].upper()=="KRW" else r["평가총액"]*usdkrw, axis=1)

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

    st.dataframe(df, use_container_width=True)
