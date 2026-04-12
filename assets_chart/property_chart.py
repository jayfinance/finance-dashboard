import streamlit as st
import pandas as pd
import plotly.express as px
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw):
    st.subheader("📊 부동산자산 차트")

    sheet = spreadsheet.worksheet(SHEET_NAMES["property"])
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("부동산자산 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    for col in ["매입가", "현재 시세"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

    if "매입가" not in df.columns or "현재 시세" not in df.columns:
        st.error("매입가 또는 현재 시세 컬럼이 없습니다.")
        return

    df["평가손익(KRW)"] = df["현재 시세"] - df["매입가"]
    name_col = "구분" if "구분" in df.columns else df.columns[0]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 항목별 현재 시세 비중")
        fig = px.pie(df, values="현재 시세", names=name_col, hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("##### 항목별 평가손익")
        fig2 = px.bar(df, x=name_col, y="평가손익(KRW)",
                      color="평가손익(KRW)", color_continuous_scale=["#ef553b", "#636efa", "#00cc96"])
        fig2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig2, width="stretch")

    st.markdown("##### 항목별 매입가 vs 현재 시세")
    df_bar = df.melt(id_vars=name_col, value_vars=["매입가", "현재 시세"], var_name="항목", value_name="금액(KRW)")
    fig3 = px.bar(df_bar, x=name_col, y="금액(KRW)", color="항목", barmode="group")
    st.plotly_chart(fig3, width="stretch")
