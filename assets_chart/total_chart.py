import streamlit as st
import pandas as pd
import plotly.express as px
from assets_table.total import (
    _sum_domestic, _sum_overseas, _sum_crypto,
    _sum_cash, _sum_property, _sum_etc, _sum_debt
)


def render(spreadsheet, get_usdkrw, get_kr_price, get_us_price, get_crypto_prices, gold_override):
    st.subheader("📊 종합 자산 차트")

    with st.spinner("전체 자산 데이터 로딩 중..."):
        _, dom_eval   = _sum_domestic(spreadsheet, get_kr_price, gold_override)
        _, ovs_eval   = _sum_overseas(spreadsheet, get_usdkrw, get_us_price)
        _, cry_eval   = _sum_crypto(spreadsheet, get_usdkrw, get_crypto_prices)
        _, cash_eval  = _sum_cash(spreadsheet, get_usdkrw)
        _, prop_eval  = _sum_property(spreadsheet)
        _, etc_eval   = _sum_etc(spreadsheet)
        debt_total    = _sum_debt(spreadsheet, get_usdkrw)

    categories = ["국내 투자자산", "해외 투자자산", "가상자산", "현금성자산", "부동산자산", "기타자산"]
    values = [dom_eval, ovs_eval, cry_eval, cash_eval, prop_eval, etc_eval]
    df_assets = pd.DataFrame({"자산 종류": categories, "금액 (KRW)": values})
    total_assets = sum(values)
    net_assets = total_assets - debt_total

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 자산 종류별 비중")
        fig = px.pie(df_assets[df_assets["금액 (KRW)"] > 0], values="금액 (KRW)", names="자산 종류", hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("##### 총자산 / 부채 / 순자산")
        df_summary = pd.DataFrame({
            "구분": ["총자산", "부채", "순자산"],
            "금액 (KRW)": [total_assets, debt_total, net_assets]
        })
        colors = ["#636efa", "#ef553b", "#00cc96"]
        fig2 = px.bar(df_summary, x="구분", y="금액 (KRW)", color="구분",
                      color_discrete_sequence=colors)
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, width="stretch")

    st.markdown("##### 자산 종류별 금액 (KRW)")
    df_bar = df_assets.sort_values("금액 (KRW)", ascending=True)
    fig3 = px.bar(df_bar, x="금액 (KRW)", y="자산 종류", orientation="h")
    st.plotly_chart(fig3, width="stretch")
