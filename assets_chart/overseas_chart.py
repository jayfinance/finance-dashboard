import streamlit as st
import pandas as pd
import plotly.express as px
from ui.components import exchange_rate_header
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw, get_us_price):
    usdkrw = get_usdkrw()
    exchange_rate_header("📊 해외 투자자산 차트", usdkrw)

    sheet = spreadsheet.worksheet(SHEET_NAMES["overseas"])
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
    df.rename(columns={"매입가": "매수단가"}, inplace=True)

    df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")
    df["매입환율"] = pd.to_numeric(df["매입환율"].str.replace(",", ""), errors="coerce")
    df["매입총액(KRW)"] = df["보유수량"] * df["매수단가"] * df["매입환율"]
    df["현재가"] = df["종목티커"].apply(get_us_price)
    df["평가총액(KRW)"] = df["보유수량"] * df["현재가"] * (usdkrw or 0)
    df["수익률(%)"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

    df_valid = df.dropna(subset=["평가총액(KRW)"])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 종목별 평가금액 비중 (KRW)")
        fig = px.pie(df_valid, values="평가총액(KRW)", names="종목티커", hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### 종목별 수익률 (KRW 기준)")
        df_sorted = df_valid.sort_values("수익률(%)", ascending=True)
        fig2 = px.bar(df_sorted, x="수익률(%)", y="종목티커", orientation="h",
                      color="수익률(%)", color_continuous_scale=["#ef553b", "#636efa", "#00cc96"])
        fig2.update_layout(coloraxis_showscale=False, yaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("##### 종목별 매입총액 vs 평가총액 (KRW)")
    df_bar = df_valid.melt(id_vars="종목티커", value_vars=["매입총액(KRW)", "평가총액(KRW)"], var_name="구분", value_name="금액(KRW)")
    fig3 = px.bar(df_bar, x="종목티커", y="금액(KRW)", color="구분", barmode="group")
    st.plotly_chart(fig3, use_container_width=True)
