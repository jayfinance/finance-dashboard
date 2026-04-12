import streamlit as st
import pandas as pd
import requests
from ui.formatters import fmt_num, fmt_pct


def render(spreadsheet, get_usdkrw, get_crypto_prices):

    usdkrw = get_usdkrw()

    left, right = st.columns([4,1])
    with left:
        st.subheader("📋 가상자산 평가 테이블")
    with right:
        if usdkrw is None:
            st.markdown("<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: -</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {usdkrw:,.2f} KRW/USD</div>", unsafe_allow_html=True)

    sheet = spreadsheet.worksheet("가상자산")
    rows = sheet.get_all_values()
    raw_df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required_cols = ["증권사","소유","코인","심볼","coingecko_id","통화","수량(qty)","평균매수가(avg_price)"]
    missing = [c for c in required_cols if c not in raw_df.columns]
    if missing:
        st.error(f"가상자산 시트에 다음 컬럼이 없습니다: {missing}")
        st.stop()

    df = raw_df[required_cols].copy()

    # 🔹 숫자 정리
    df["수량(qty)"] = pd.to_numeric(df["수량(qty)"].astype(str).str.replace(",", ""), errors="coerce")
    df["평균매수가(avg_price)"] = pd.to_numeric(df["평균매수가(avg_price)"].astype(str).str.replace(",", ""), errors="coerce")

    # 🔹 coingecko_id 정리
    df["coingecko_id"] = df["coingecko_id"].astype(str).str.strip().str.lower()

    # 🔹 통화 정리
    df["통화"] = df["통화"].astype(str).str.strip().str.upper()
    df["통화"] = df["통화"].replace({
        "원": "KRW",
        "KR": "KRW",
        "달러": "USD",
        "US": "USD"
    })

    # 🔹 모든 코인 ID
    all_ids = df["coingecko_id"].dropna().unique().tolist()

    # 🔹 CoinGecko 호출 (캐시 15분)
    @st.cache_data(ttl=900)
    def fetch_crypto_prices(ids):
        try:
            res = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": "usd,krw"},
                timeout=10
            )
            data = res.json()
            if not data:
                return None
            return data
        except:
            return None

    price_map = fetch_crypto_prices(all_ids)

    # 🔹 실패 시 이전 가격 유지
    if price_map is None:
        st.warning("⚠ CoinGecko 호출 제한 발생 — 이전 가격 사용")
        price_map = st.session_state.get("last_crypto_prices", {})
    else:
        st.session_state["last_crypto_prices"] = price_map

    # 🔹 현재가 매칭
    def get_price(row):
        cid = row["coingecko_id"]
        cur = row["통화"]
        info = price_map.get(cid, {})
        if cur == "KRW":
            return info.get("krw")
        elif cur == "USD":
            return info.get("usd")
        return None

    df["현재가"] = df.apply(get_price, axis=1)

    # 계산
    df["매입총액"] = df["수량(qty)"] * df["평균매수가(avg_price)"]

    df["매입총액(KRW)"] = df.apply(
        lambda r: r["매입총액"] if r["통화"]=="KRW"
        else (r["매입총액"] * usdkrw if usdkrw else float("nan")),
        axis=1
    )

    df["평가총액"] = df["수량(qty)"] * df["현재가"]

    df["평가총액(KRW)"] = df.apply(
        lambda r: r["평가총액"] if r["통화"]=="KRW"
        else (r["평가총액"] * usdkrw if usdkrw else float("nan")),
        axis=1
    )

    df["수익률"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

    total_buy = df["매입총액(KRW)"].sum()
    total_eval = df["평가총액(KRW)"].sum()
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-weight:bold;'>
        <div>가상 자산 매입총액: {fmt_num(total_buy)} 원</div>
        <div>가상 자산 평가총액: {fmt_num(total_eval)} 원</div>
        <div>가상 자산 전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    # 표시용 포맷
    display_df = df.copy()
    display_df["수량(qty)"] = display_df["수량(qty)"].apply(lambda x: f"{x:,.9f}" if pd.notna(x) else "-")

    for col in ["평균매수가(avg_price)", "현재가", "매입총액", "매입총액(KRW)", "평가총액", "평가총액(KRW)"]:
        display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")

    display_df["수익률"] = display_df["수익률"].apply(fmt_pct)

    st.dataframe(display_df, width="stretch")
