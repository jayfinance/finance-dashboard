import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from config import SHEET_NAMES


def render(spreadsheet):
    st.subheader("📊 종합 자산 추이 차트")

    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["trend"])
    except gspread.exceptions.WorksheetNotFound:
        st.info("'자산추이' 시트가 아직 없습니다. 테이블 메뉴의 '추이' 화면에서 시트 구성 가이드를 확인하세요.")
        return

    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("자산추이 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    numeric_cols = [c for c in df.columns if c != "기준일"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    if "순자산" in df.columns:
        st.markdown("##### 순자산 추이")
        fig = px.line(df, x="기준일", y="순자산", markers=True)
        fig.update_layout(xaxis_title=None)
        st.plotly_chart(fig, width="stretch")

    asset_cols = [c for c in ["국내자산", "해외자산", "가상자산", "현금성자산", "부동산", "기타"] if c in df.columns]
    if asset_cols:
        st.markdown("##### 자산 종류별 추이 (스택)")
        df_melt = df.melt(id_vars="기준일", value_vars=asset_cols, var_name="자산 종류", value_name="금액(KRW)")
        fig2 = px.area(df_melt, x="기준일", y="금액(KRW)", color="자산 종류")
        fig2.update_layout(xaxis_title=None)
        st.plotly_chart(fig2, width="stretch")

    if "부채" in df.columns and "순자산" in df.columns:
        st.markdown("##### 총자산 / 부채 / 순자산 추이")
        total_cols = [c for c in ["순자산", "부채"] if c in df.columns]
        df_melt2 = df.melt(id_vars="기준일", value_vars=total_cols, var_name="구분", value_name="금액(KRW)")
        fig3 = px.line(df_melt2, x="기준일", y="금액(KRW)", color="구분", markers=True)
        fig3.update_layout(xaxis_title=None)
        st.plotly_chart(fig3, width="stretch")
