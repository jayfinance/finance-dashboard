import streamlit as st
import pandas as pd
import plotly.express as px
from ui.components import exchange_rate_header
from config import SHEET_NAMES


def render(spreadsheet, get_kr_price, gold_override):
    st.subheader("📊 국내 투자자산 차트")

    sheet = spreadsheet.worksheet(SHEET_NAMES["domestic"])
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")
    df["매입총액"] = df["보유수량"] * df["매수단가"]
    df["현재가"] = [get_kr_price(t, n, gold_override) for t, n in zip(df["종목코드"], df["종목명"])]
    df["평가총액"] = df["보유수량"] * df["현재가"]
    df["수익률(%)"] = (df["평가총액"] / df["매입총액"] - 1) * 100

    df_valid = df.dropna(subset=["평가총액"])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 종목별 평가금액 비중")
        fig = px.pie(df_valid, values="평가총액", names="종목명", hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### 종목별 수익률")
        df_sorted = df_valid.sort_values("수익률(%)", ascending=True)
        colors = ["#ef553b" if v < 0 else "#00cc96" for v in df_sorted["수익률(%)"]]
        fig2 = px.bar(df_sorted, x="수익률(%)", y="종목명", orientation="h",
                      color="수익률(%)", color_continuous_scale=["#ef553b", "#636efa", "#00cc96"])
        fig2.update_layout(coloraxis_showscale=False, yaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("##### 종목별 매입총액 vs 평가총액")
    df_bar = df_valid.melt(id_vars="종목명", value_vars=["매입총액", "평가총액"], var_name="구분", value_name="금액(KRW)")
    fig3 = px.bar(df_bar, x="종목명", y="금액(KRW)", color="구분", barmode="group")
    st.plotly_chart(fig3, use_container_width=True)
