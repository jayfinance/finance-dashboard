import yfinance as yf
import streamlit as st

# -------------------------------
# 환율
# -------------------------------
@st.cache_data(ttl=600)
def get_usdkrw():
    try:
        data = yf.Ticker("USDKRW=X").history(period="5d")["Close"].dropna()
        return float(data.iloc[-1]) if not data.empty else None
    except Exception:
        return None


@st.cache_data(ttl=600)
def get_jpykrw():
    try:
        data = yf.Ticker("JPYKRW=X").history(period="5d")["Close"].dropna()
        return float(data.iloc[-1]) if not data.empty else None
    except Exception:
        return None


# -------------------------------
# 금 시세
# -------------------------------
@st.cache_data(ttl=600)
def get_gold_price_krw_per_g():
    try:
        gold_data = yf.Ticker("GC=F").history(period="5d")["Close"].dropna()
        usdkrw = get_usdkrw()
        if gold_data.empty or usdkrw is None:
            return None
        return (float(gold_data.iloc[-1]) * usdkrw) / 31.1035
    except Exception:
        return None


# -------------------------------
# 국내 주식 / 금
# -------------------------------
@st.cache_data(ttl=600)
def get_kr_price(ticker, name, gold_override):
    try:
        if name == "금현물" or str(ticker).upper() == "GOLD":
            return float(gold_override) if gold_override > 0 else get_gold_price_krw_per_g()

        data = yf.Ticker(f"{str(ticker).zfill(6)}.KS").history(period="1d")["Close"]
        return float(data.iloc[-1]) if not data.empty else None
    except Exception:
        return None


# -------------------------------
# 해외 주식
# -------------------------------
@st.cache_data(ttl=600)
def get_us_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1d")["Close"]
        return float(data.iloc[-1]) if not data.empty else None
    except Exception:
        return None
