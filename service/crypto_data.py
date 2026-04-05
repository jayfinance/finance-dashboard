import requests
import streamlit as st


# -------------------------------
# 가상자산 (CoinGecko)
# -------------------------------
@st.cache_data(ttl=300)
def get_crypto_prices(ids):
    try:
        if not ids:
            return {}

        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ",".join(ids), "vs_currencies": "usd,krw"},
            timeout=10
        )

        if res.status_code != 200:
            return None

        data = res.json()
        if not isinstance(data, dict) or not data:
            return None

        return data

    except Exception:
        return None
