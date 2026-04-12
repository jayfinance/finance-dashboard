import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct


def render(spreadsheet, get_kr_price, local_gold_override):

    st.subheader("📋 국내 투자자산 평가 테이블")

    sheet = spreadsheet.worksheet("국내자산")
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required = ["증권사","소유","종목명","종목코드","계좌구분","성격","보유수량","매수단가"]
    df = df[required].copy()
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")

    df["매입총액 (KRW)"] = df["보유수량"] * df["매수단가"]
    df["현재가"] = [get_kr_price(t, n, local_gold_override) for t, n in zip(df["종목코드"], df["종목명"])]
    df["평가총액 (KRW)"] = df["보유수량"] * df["현재가"]
    df["평가손익 (KRW)"] = df["평가총액 (KRW)"] - df["매입총액 (KRW)"]
    df["수익률 (%)"] = (df["평가총액 (KRW)"] / df["매입총액 (KRW)"] - 1) * 100

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

    display_df = df.copy()
    for col in ["보유수량","매수단가","매입총액 (KRW)","현재가","평가총액 (KRW)","평가손익 (KRW)"]:
        display_df[col] = display_df[col].apply(fmt_num)
    display_df["수익률 (%)"] = display_df["수익률 (%)"].apply(fmt_pct)

    st.dataframe(display_df, width="stretch")
