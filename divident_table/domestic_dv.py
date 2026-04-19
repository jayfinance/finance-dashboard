import streamlit as st
import pandas as pd
import gspread
from ui.formatters import fmt_num, fmt_pct
from config import SHEET_NAMES
from service.sheets import load_sheet_data


def render(spreadsheet):
    st.subheader("📋 국내 배당 테이블")

    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["domestic_div"])
    except gspread.exceptions.WorksheetNotFound:
        st.info("'국내배당' 시트가 아직 없습니다. Google Sheets에 해당 시트를 추가하면 이 화면에 표시됩니다.")
        st.markdown("""
        **권장 컬럼 구성 (시트명: `국내배당`)**
        | 증권사 | 소유 | 종목명 | 종목코드 | 배당금(원) | 배당일 | 배당수익률(%) |
        |---|---|---|---|---|---|---|
        """)
        return

    rows = load_sheet_data(spreadsheet, SHEET_NAMES["domestic_div"])
    if not rows or len(rows) < 2:
        st.warning("국내배당 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required_cols = ["증권사", "소유", "종목명", "종목코드", "배당금(원)", "배당일", "배당수익률(%)"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"국내배당 시트에 누락된 컬럼: {missing}")
        st.write("실제 컬럼:", df.columns.tolist())
        return

    df = df[required_cols].copy()
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["배당금(원)"] = pd.to_numeric(df["배당금(원)"].astype(str).str.replace(",", ""), errors="coerce")
    df["배당수익률(%)"] = pd.to_numeric(
        df["배당수익률(%)"].astype(str).str.replace(",", "").str.replace("%", ""), errors="coerce"
    )

    total_div = df["배당금(원)"].fillna(0).sum()

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>국내 배당금 합계: {fmt_num(total_div)} 원</div>
    </div>
    """, unsafe_allow_html=True)

    display_df = df.copy()
    display_df["배당금(원)"] = display_df["배당금(원)"].apply(fmt_num)
    display_df["배당수익률(%)"] = display_df["배당수익률(%)"].apply(fmt_pct)

    st.dataframe(display_df, width="stretch")
