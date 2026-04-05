import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_num2, fmt_pct
from ui.components import exchange_rate_header
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw, get_us_price):

    usdkrw = get_usdkrw()
    exchange_rate_header("📋 해외 투자자산 평가 테이블", usdkrw)

    view_option = st.radio("표시 통화 옵션", ["모두 보기", "LC로 보기", "KRW로 보기"], horizontal=True)

    sheet = spreadsheet.worksheet(SHEET_NAMES["overseas"])
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
    df.rename(columns={"매입가": "매수단가"}, inplace=True)

    required = ["증권사", "소유", "종목티커", "계좌구분", "성격", "보유수량", "매수단가", "매입환율"]
    df = df[required].copy()

    df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")
    df["매입환율"] = pd.to_numeric(df["매입환율"].str.replace(",", ""), errors="coerce")

    df["매입총액(LC)"] = df["보유수량"] * df["매수단가"]
    df["매입총액(KRW)"] = df["매입총액(LC)"] * df["매입환율"]

    df["현재가"] = df["종목티커"].apply(get_us_price)
    df["평가총액(LC)"] = df["보유수량"] * df["현재가"]
    df["평가총액(KRW)"] = df["평가총액(LC)"] * usdkrw
    df["수익률(KRW)"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

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

    display_df = df.copy()
    display_df["매입환율"] = display_df["매입환율"].apply(fmt_num2)
    display_df["매입총액(LC)"] = display_df["매입총액(LC)"].apply(fmt_num2)
    display_df["매입총액(KRW)"] = display_df["매입총액(KRW)"].apply(fmt_num)
    display_df["평가총액(LC)"] = display_df["평가총액(LC)"].apply(fmt_num2)
    display_df["평가총액(KRW)"] = display_df["평가총액(KRW)"].apply(fmt_num)
    display_df["수익률(KRW)"] = display_df["수익률(KRW)"].apply(fmt_pct)

    base_cols = ["증권사", "소유", "종목티커", "계좌구분", "성격", "보유수량", "매수단가", "현재가"]

    if view_option == "LC로 보기":
        cols = base_cols + ["매입총액(LC)", "평가총액(LC)"]
    elif view_option == "KRW로 보기":
        cols = base_cols + ["매입총액(KRW)", "평가총액(KRW)", "수익률(KRW)"]
    else:
        cols = base_cols + ["매입총액(LC)", "평가총액(LC)", "매입총액(KRW)", "평가총액(KRW)", "수익률(KRW)"]

    st.dataframe(display_df[cols], use_container_width=True)
