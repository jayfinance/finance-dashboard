import streamlit as st
import pandas as pd
import plotly.express as px
from ui.components import exchange_rate_header
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw):
    usdkrw = get_usdkrw()
    exchange_rate_header("📊 부채 차트", usdkrw, nav_label="📋 테이블 보러가기", nav_section="Table", nav_page="부채")

    sheet = spreadsheet.worksheet(SHEET_NAMES["debt"])
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("부채 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    if "현재부채" not in df.columns:
        st.error("현재부채 컬럼이 없습니다.")
        return

    df["현재부채"] = pd.to_numeric(df["현재부채"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    group_col = "구분" if "구분" in df.columns else df.columns[0]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 구분별 부채 비중")
        df_grp = df.groupby(group_col)["현재부채"].sum().reset_index()
        fig = px.pie(df_grp, values="현재부채", names=group_col, hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("##### 소유자별 부채")
        if "소유" in df.columns:
            df_own = df.groupby("소유")["현재부채"].sum().reset_index()
            fig2 = px.bar(df_own, x="소유", y="현재부채")
            st.plotly_chart(fig2, width="stretch")

    st.markdown("##### 구분별 부채 금액")
    df_sorted = df.sort_values("현재부채", ascending=False)
    fig3 = px.bar(df_sorted, x=group_col, y="현재부채")
    st.plotly_chart(fig3, width="stretch")
