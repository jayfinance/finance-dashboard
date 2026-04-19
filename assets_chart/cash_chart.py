import streamlit as st
import pandas as pd
import plotly.express as px
from ui.components import exchange_rate_header
from ui.formatters import fmt_num
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw):
    usdkrw = get_usdkrw()
    exchange_rate_header("📊 현금성자산 차트", usdkrw, nav_label="📋 테이블 보러가기", nav_section="Table", nav_page="현금성자산")

    sheet = spreadsheet.worksheet(SHEET_NAMES["cash"])
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("현금성자산 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
    df["금액"] = pd.to_numeric(df["금액"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    df["통화"] = df["통화"].astype(str).str.strip().str.upper()
    df["금액(KRW)"] = df.apply(
        lambda r: r["금액"] if r["통화"] == "KRW" else (r["금액"] * usdkrw if usdkrw else 0), axis=1
    )

    total_cash = df["금액(KRW)"].sum()
    st.markdown(f"""
<div style='display:flex;gap:40px;font-size:1.05em;font-weight:bold;padding:8px 0;'>
    <div>현금성자산 총액: {fmt_num(total_cash)} 원</div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 성격별 현금 비중 (KRW)")
        group_col = "성격" if "성격" in df.columns else "계좌구분"
        df_grp = df.groupby(group_col)["금액(KRW)"].sum().reset_index()
        fig = px.pie(df_grp, values="금액(KRW)", names=group_col, hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("##### 통화별 현금 비중 (KRW)")
        df_cur = df.groupby("통화")["금액(KRW)"].sum().reset_index()
        fig2 = px.pie(df_cur, values="금액(KRW)", names="통화", hole=0.3)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig2, width="stretch")

    if "소유" in df.columns:
        col_o1, _ = st.columns(2)
        with col_o1:
            st.markdown("##### 소유자별 평가금액 비중")
            pivot_owner = df.groupby("소유", as_index=False)["금액(KRW)"].sum()
            fig_o = px.pie(pivot_owner, values="금액(KRW)", names="소유", hole=0.35)
            fig_o.update_traces(textposition="inside", textinfo="percent+label")
            fig_o.update_layout(showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig_o, width="stretch")

    st.markdown("##### 증권사/기관별 현금 보유액 (KRW)")
    if "증권사" in df.columns:
        df_inst = df.groupby("증권사")["금액(KRW)"].sum().reset_index().sort_values("금액(KRW)", ascending=False)
        fig3 = px.bar(df_inst, x="증권사", y="금액(KRW)")
        st.plotly_chart(fig3, width="stretch")
