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
# 사이드바
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

# =========================================================
# 🇰🇷 국내 투자자산
# =========================================================
if menu == "Table" and submenu == "국내 투자자산":
    sheet = spreadsheet.worksheet("국내자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

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
    df["현재가"] = [get_kr_price(t, n, local_gold_override) for t, n in zip(df["종목코드"], df["종목명"])]
    df["평가총액 (KRW)"] = df["보유수량"] * df["현재가"]
    df["평가손익 (KRW)"] = df["평가총액 (KRW)"] - df["매입총액 (KRW)"]
    df["수익률 (%)"] = (df["평가총액 (KRW)"] / df["매입총액 (KRW)"] - 1) * 100

    # 상단 합계
    total_buy = df["매입총액 (KRW)"].sum()
    total_eval = df["평가총액 (KRW)"].sum()
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>국내 자산 매입총액: {fmt_num(total_buy)} 원</div>
        <div>국내 자산 평가총액: {fmt_num(total_eval)} 원</div>
        <div>국내 자산 전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

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

# =========================================================
# 🌍 해외 투자자산
# =========================================================
if menu == "Table" and submenu == "해외 투자자산":
    usdkrw = get_usdkrw()

    # 옵션 복구 (디폴트: 모두 보기)
    view_option = st.radio("표시 통화 옵션", ["모두 보기", "LC로 보기", "KRW로 보기"], horizontal=True)

    sheet = spreadsheet.worksheet("해외자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    # 메모 컬럼이 있더라도 무시 (요구사항: 제거)
    # 시트 컬럼명: 매입가 -> 매수단가로 통일
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

    # 계산: LC / KRW
    df["매입총액(LC)"] = df["보유수량"] * df["매수단가"]
    df["매입총액(KRW)"] = df["매입총액(LC)"] * df["매입환율"]

    df["현재가"] = df["종목티커"].apply(get_us_price)

    df["평가총액(LC)"] = df["보유수량"] * df["현재가"]
    df["평가총액(KRW)"] = df["평가총액(LC)"] * (usdkrw if usdkrw is not None else float("nan"))

    df["평가손익(LC)"] = df["평가총액(LC)"] - df["매입총액(LC)"]
    df["평가손익(KRW)"] = df["평가총액(KRW)"] - df["매입총액(KRW)"]

    df["수익률(LC)"] = (df["평가총액(LC)"] / df["매입총액(LC)"] - 1) * 100
    df["수익률(KRW)"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

    # ✅ 해외 상단 합계 (KRW 기준)
    total_buy = df["매입총액(KRW)"].sum()
    total_eval = df["평가총액(KRW)"].sum()
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>해외 자산 매입총액: {fmt_num(total_buy)} 원</div>
        <div>해외 자산 평가총액: {fmt_num(total_eval)} 원</div>
        <div>해외 자산 전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    # ✅ 테이블 제목 우측에 환율 작게 표시
    left, right = st.columns([4, 1])
    with left:
        st.subheader("📋 해외 투자자산 평가 테이블")
    with right:
        if usdkrw is None:
            st.markdown("<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: -</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {usdkrw:,.2f} KRW/USD</div>",
                unsafe_allow_html=True
            )

    # ✅ 요구한 “정확한 출력 컬럼” (순서 고정)
    all_cols = [
        "증권사","소유","종목티커","계좌구분","성격","보유수량","매수단가","매입환율",
        "매입총액(LC)","매입총액(KRW)","현재가",
        "평가총액(LC)","평가총액(KRW)","평가손익(LC)","평가손익(KRW)",
        "수익률(LC)","수익률(KRW)"
    ]

    # ✅ 옵션에 따른 컬럼 선택
    base_cols = ["증권사","소유","종목티커","계좌구분","성격","보유수량","매수단가","매입환율","현재가"]

    if view_option == "LC로 보기":
        show_cols = base_cols + ["매입총액(LC)","평가총액(LC)","평가손익(LC)","수익률(LC)"]
    elif view_option == "KRW로 보기":
        show_cols = base_cols + ["매입총액(KRW)","평가총액(KRW)","평가손익(KRW)","수익률(KRW)"]
    else:
        show_cols = all_cols  # 모두 보기(디폴트)

    # 표시용 포맷
    display_df = df[show_cols].copy()

    money_cols = [
        "보유수량","매수단가","매입환율","현재가",
        "매입총액(LC)","매입총액(KRW)",
        "평가총액(LC)","평가총액(KRW)",
        "평가손익(LC)","평가손익(KRW)"
    ]
    for col in money_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(fmt_num)

    if "수익률(LC)" in display_df.columns:
        display_df["수익률(LC)"] = display_df["수익률(LC)"].apply(fmt_pct)
    if "수익률(KRW)" in display_df.columns:
        display_df["수익률(KRW)"] = display_df["수익률(KRW)"].apply(fmt_pct)

    st.dataframe(display_df, use_container_width=True)
