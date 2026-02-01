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
        gold_usd = yf.Ticker("GC=F").history(period="5d")["Close"].dropna().iloc[-1]
        usdkrw = get_usdkrw()
        return (gold_usd * usdkrw) / 31.1035
    except:
        return None

# -------------------------------
# 현재가 조회
# -------------------------------
@st.cache_data(ttl=600)
def get_current_price(ticker, name, gold_override):
    try:
        if name == "금현물" or ticker.upper() == "GOLD":
            return float(gold_override) if gold_override > 0 else get_gold_price_krw_per_g()
        return yf.Ticker(f"{ticker}.KS").history(period="1d")["Close"].iloc[-1]
    except:
        return None

# -------------------------------
# 국내 투자자산
# -------------------------------
if menu == "Table" and submenu == "국내 투자자산":
    sheet = spreadsheet.worksheet("국내자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df.columns = df.columns.str.strip()

    df = df[["증권사","소유","종목명","종목코드","계좌구분","성격","보유수량","매수단가"]]

    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")

    df["매입총액 (KRW)"] = df["보유수량"] * df["매수단가"]

    prices = [get_current_price(t, n, local_gold_override) for t,n in zip(df["종목코드"], df["종목명"])]
    df["현재가"] = pd.to_numeric(prices, errors="coerce")

    df["평가총액 (KRW)"] = df["보유수량"] * df["현재가"]
    df["평가손익 (KRW)"] = df["평가총액 (KRW)"] - df["매입총액 (KRW)"]
    df["수익률 (%)"] = (df["평가총액 (KRW)"] / df["매입총액 (KRW)"] - 1) * 100

    # 합계 계산
    total_buy = df["매입총액 (KRW)"].sum()
    total_eval = df["평가총액 (KRW)"].sum()
    total_profit = df["평가손익 (KRW)"].sum()
    final_yield = (total_eval / total_buy - 1) * 100 if total_buy != 0 else 0

    st.markdown(f"""
    <div style='display: flex; gap: 32px; font-size: 1.1em; font-weight: bold;'>
        <div>매입총액 합계: {fmt(total_buy)} 원</div>
        <div>평가총액 합계: {fmt(total_eval)} 원</div>
        <div>평가손익 합계: {fmt(total_profit)} 원</div>
        <div>최종 수익률: {final_yield:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

    def fmt(x): return "-" if pd.isna(x) else f"{x:,.0f}"

    st.subheader("📋 국내 투자자산 평가 테이블")
    display_df = df.copy()
    for col in ["보유수량","매수단가","현재가","매입총액 (KRW)","평가총액 (KRW)","평가손익 (KRW)"]:
        display_df[col] = display_df[col].apply(fmt)
    display_df["수익률 (%)"] = display_df["수익률 (%)"].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

    st.dataframe(display_df, use_container_width=True)

# -------------------------------
# 해외 투자자산
# -------------------------------
if menu == "Table" and submenu == "해외 투자자산":
    usdkrw = get_usdkrw()
    st.markdown(f"### 💱 현재 환율: **1 USD = {usdkrw:,.2f} KRW**")

    view_option = st.radio("표시 통화 옵션", ["모두 보기", "LC로 보기", "KRW로 보기"], horizontal=True)

    sheet = spreadsheet.worksheet("해외자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df.columns = df.columns.str.strip()

    df = df[["증권사","소유","종목티커","계좌구분","성격","보유수량","매수단가","매입환율"]]

    if "매입환율" not in df.columns:
        st.error("해외자산 시트에 '매입환율' 칼럼이 없습니다. 시트를 확인해 주세요.")
        st.stop()

    df["보유수량"] = pd.to_numeric(df["보유수량"], errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"], errors="coerce")
    df["매입환율"] = pd.to_numeric(df["매입환율"], errors="coerce")

    df["매입총액(LC)"] = df["보유수량"] * df["매수단가"]
    df["매입총액(KRW)"] = df["매입총액(LC)"] * df["매입환율"]

    @st.cache_data(ttl=600)
    def get_us_price(ticker):
        try: return yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
        except: return None

    df["현재가"] = df["종목티커"].apply(get_us_price)

    df["평가총액(LC)"] = df["보유수량"] * df["현재가"]
    df["평가총액(KRW)"] = df["평가총액(LC)"] * usdkrw

    df["평가손익(LC)"] = df["평가총액(LC)"] - df["매입총액(LC)"]
    df["평가손익(KRW)"] = df["평가총액(KRW)"] - df["매입총액(KRW)"]

    df["수익률(LC)"] = (df["평가총액(LC)"] / df["매입총액(LC)"] - 1) * 100
    df["수익률(KRW)"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

    def fmt(x): return "-" if pd.isna(x) else f"{x:,.0f}"
    def fmt_pct(x): return "-" if pd.isna(x) else f"{x:.2f}%"

    display_df = df.copy()
    num_cols = ["보유수량","매수단가","매입환율","현재가",
                "매입총액(LC)","평가총액(LC)","평가손익(LC)",
                "매입총액(KRW)","평가총액(KRW)","평가손익(KRW)"]

    for col in num_cols: display_df[col] = display_df[col].apply(fmt)
    display_df["수익률(LC)"] = display_df["수익률(LC)"].apply(fmt_pct)
    display_df["수익률(KRW)"] = display_df["수익률(KRW)"].apply(fmt_pct)

    base_cols = ["증권사","소유","종목티커","계좌구분","성격","보유수량","매수단가","현재가"]

    if view_option == "LC로 보기":
        cols = base_cols + ["매입총액(LC)","평가총액(LC)","평가손익(LC)","수익률(LC)"]
    elif view_option == "KRW로 보기":
        cols = base_cols + ["매입총액(KRW)","평가총액(KRW)","평가손익(KRW)","수익률(KRW)"]
    else:
        cols = base_cols + ["매입총액(LC)","평가총액(LC)","평가손익(LC)","수익률(LC)",
                            "매입총액(KRW)","평가총액(KRW)","평가손익(KRW)","수익률(KRW)"]

    st.subheader("📋 해외 투자자산 평가 테이블")
    st.dataframe(display_df[cols], use_container_width=True)
