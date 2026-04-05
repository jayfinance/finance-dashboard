import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from ui.components import exchange_rate_header
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw):
    usdkrw = get_usdkrw()
    exchange_rate_header("📊 해외 배당 차트", usdkrw)

    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["overseas_div"])
    except gspread.exceptions.WorksheetNotFound:
        st.info("'해외배당' 시트가 아직 없습니다. 테이블 메뉴의 '해외 배당' 화면에서 시트 구성 가이드를 확인하세요.")
        return

    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("해외배당 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    if "배당금(USD)" not in df.columns:
        st.error("배당금(USD) 컬럼이 없습니다.")
        return

    df["배당금(USD)"] = pd.to_numeric(df["배당금(USD)"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    df["배당금(KRW)"] = df["배당금(USD)"] * usdkrw if usdkrw else float("nan")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 종목별 배당금 비중 (KRW)")
        name_col = "종목티커" if "종목티커" in df.columns else df.columns[0]
        df_grp = df.groupby(name_col)["배당금(KRW)"].sum().reset_index()
        fig = px.pie(df_grp, values="배당금(KRW)", names=name_col, hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### 종목별 배당금 (KRW)")
        df_sorted = df.groupby(name_col)["배당금(KRW)"].sum().reset_index().sort_values("배당금(KRW)", ascending=False)
        fig2 = px.bar(df_sorted, x=name_col, y="배당금(KRW)")
        st.plotly_chart(fig2, use_container_width=True)

    if "배당일" in df.columns:
        st.markdown("##### 월별 배당금 추이 (KRW)")
        df["배당일"] = pd.to_datetime(df["배당일"], errors="coerce")
        df["연월"] = df["배당일"].dt.to_period("M").astype(str)
        df_monthly = df.groupby("연월")["배당금(KRW)"].sum().reset_index()
        fig3 = px.bar(df_monthly, x="연월", y="배당금(KRW)")
        st.plotly_chart(fig3, use_container_width=True)
