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
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open("FinanceRaw")

# -------------------------------
# 사이드바 메뉴
# -------------------------------
menu = st.sidebar.radio("메뉴 선택", ["Table"])
submenu = st.sidebar.selectbox("자산 구분", ["국내 투자자산", "해외 투자자산"])

st.sidebar.markdown("### 🟡 금(보정 옵션)")
local_gold_override = st.sidebar.number_input(
    "국내 금 시세 수동 입력 (원/g)\n0 입력 시 국제 금 환산값 사용",
    min_value=0,
    step=1000,
    value=0
)

# -------------------------------
# 환율 함수
# -------------------------------
@st.cache_data(ttl=600)
def get_usdkrw():
    try:
        return float(yf.Ticker("USDKRW=X").history(period="5d")["Close"].dropna().iloc[-1])
    except:
        return None

# -------------------------------
# 국제 금 가격
# -------------------------------
@st.cache_data(ttl=600)
def get_gold_price_krw_per_g():
    try:
        gold_usd = float(yf.Ticker("GC=F").history(period="5d")["Close"].dropna().iloc[-1])
        usdkrw = get_usdkrw()
        if usdkrw is None:
            return None
        return (gold_usd * usdkrw) / 31.1035
    except:
        return None

# -------------------------------
# 국내 현재가 조회 (KR 주식 + 금현물)
# -------------------------------
@st.cache_data(ttl=600)
def get_kr_current_price(ticker, name, gold_override):
    try:
        if name == "금현물" or str(ticker).upper() == "GOLD":
            return float(gold_override) if gold_override > 0 else get_gold_price_krw_per_g()

        ticker_yf = f"{str(ticker).zfill(6)}.KS"
        return float(yf.Ticker(ticker_yf).history(period="1d")["Close"].iloc[-1])
    except:
        return None

# -------------------------------
# 미국 주식 현재가 조회
# -------------------------------
@st.cache_data(ttl=600)
def get_us_price(ticker):
    try:
        return float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
    except:
        return None

def fmt_num(x):
    if pd.isna(x):
        return "-"
    try:
        return f"{x:,.0f}"
    except:
        return "-"

def fmt_pct(x):
    if pd.isna(x):
        return "-"
    try:
        return f"{x:.2f}%"
    except:
        return "-"

# -------------------------------
# 국내 투자자산
# -------------------------------
if menu == "Table" and submenu == "국내 투자자산":
    sheet = spreadsheet.worksheet("국내자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df.columns = df.columns.str.strip()

    required = ["증권사","소유","종목명","종목코드","계좌구분","성격","보유수량","매수단가"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"국내자산 시트에 다음 컬럼이 없습니다: {missing}")
        st.stop()

    df = df[required].copy()

    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].astype(str).str.replace(",", ""), errors="coerce")

    df["매입총액 (KRW)"] = df["보유수량"] * df["매수단가"]

    prices = []
    for t, n in zip(df["종목코드"], df["종목명"]):
        prices.append(get_kr_current_price(t, n, local_gold_override))
    df["현재가"] = pd.to_numeric(prices, errors="coerce")

    df["평가총액 (KRW)"] = df["보유수량"] * df["현재가"]
    df["평가손익 (KRW)"] = df["평가총액 (KRW)"] - df["매입총액 (KRW)"]
    df["수익률 (%)"] = (df["평가총액 (KRW)"] / df["매입총액 (KRW)"] - 1) * 100

    # ✅ 국내는 “항상 보여줄 컬럼”을 명시 (문제 1 해결)
    show_cols = [
        "증권사","소유","종목명","종목코드","계좌구분","성격",
        "보유수량","매수단가","매입총액 (KRW)","현재가","평가총액 (KRW)","평가손익 (KRW)","수익률 (%)"
    ]

    display_df = df[show_cols].copy()
    for col in ["보유수량","매수단가","매입총액 (KRW)","현재가","평가총액 (KRW)","평가손익 (KRW)"]:
        display_df[col] = display_df[col].apply(fmt_num)
    display_df["수익률 (%)"] = display_df["수익률 (%)"].apply(fmt_pct)

    st.subheader("📋 국내 투자자산 평가 테이블")
    st.dataframe(display_df, use_container_width=True)

# -------------------------------
# 해외 투자자산
# -------------------------------
if menu == "Table" and submenu == "해외 투자자산":
    usdkrw = get_usdkrw()
    if usdkrw is None:
        st.warning("⚠️ 현재 환율(USDKRW)을 가져오지 못했습니다. 평가(KRW) 계산이 일부 누락될 수 있어요.")
    else:
        st.markdown(f"### 💱 현재 환율: **1 USD = {usdkrw:,.2f} KRW**")

    view_option = st.radio("표시 통화 옵션", ["모두 보기", "LC로 보기", "KRW로 보기"], horizontal=True)

    sheet = spreadsheet.worksheet("해외자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df.columns = df.columns.str.strip()

    # 시트 컬럼명: 매입가 → 매수단가로 통일
    df.rename(columns={"매입가": "매수단가"}, inplace=True)

    required = ["증권사","소유","종목티커","계좌구분","성격","보유수량","매수단가","매입환율"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"해외자산 시트에 다음 컬럼이 없습니다: {missing}")
        st.stop()

    df = df[required].copy()

    df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].astype(str).str.replace(",", ""), errors="coerce")
    df["매입환율"] = pd.to_numeric(df["매입환율"].astype(str).str.replace(",", ""), errors="coerce")

    df["매입총액(LC)"] = df["보유수량"] * df["매수단가"]
    df["매입총액(KRW)"] = df["매입총액(LC)"] * df["매입환율"]

    df["현재가"] = df["종목티커"].apply(get_us_price)

    df["평가총액(LC)"] = df["보유수량"] * df["현재가"]
    df["평가총액(KRW)"] = df["평가총액(LC)"] * (usdkrw if usdkrw is not None else float("nan"))

    df["평가손익(LC)"] = df["평가총액(LC)"] - df["매입총액(LC)"]
    df["평가손익(KRW)"] = df["평가총액(KRW)"] - df["매입총액(KRW)"]

    df["수익률(LC)"] = (df["평가총액(LC)"] / df["매입총액(LC)"] - 1) * 100
    df["수익률(KRW)"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

    # ✅ 해외 base_cols에 매입환율 포함 (문제 2 해결)
    base_cols = ["증권사","소유","종목티커","계좌구분","성격","보유수량","매수단가","매입환율","현재가"]

    if view_option == "LC로 보기":
        show_cols = base_cols + ["매입총액(LC)","평가총액(LC)","평가손익(LC)","수익률(LC)"]
    elif view_option == "KRW로 보기":
        show_cols = base_cols + ["매입총액(KRW)","평가총액(KRW)","평가손익(KRW)","수익률(KRW)"]
    else:
        show_cols = base_cols + [
            "매입총액(LC)","평가총액(LC)","평가손익(LC)","수익률(LC)",
            "매입총액(KRW)","평가총액(KRW)","평가손익(KRW)","수익률(KRW)"
        ]

    display_df = df[show_cols].copy()

    # 숫자 포맷
    money_cols = [
        "보유수량","매수단가","매입환율","현재가",
        "매입총액(LC)","평가총액(LC)","평가손익(LC)",
        "매입총액(KRW)","평가총액(KRW)","평가손익(KRW)"
    ]
    for col in money_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(fmt_num)

    if "수익률(LC)" in display_df.columns:
        display_df["수익률(LC)"] = display_df["수익률(LC)"].apply(fmt_pct)
    if "수익률(KRW)" in display_df.columns:
        display_df["수익률(KRW)"] = display_df["수익률(KRW)"].apply(fmt_pct)

    st.subheader("📋 해외 투자자산 평가 테이블")
    st.dataframe(display_df, use_container_width=True)
