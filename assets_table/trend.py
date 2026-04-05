import streamlit as st
import pandas as pd
import gspread
from ui.formatters import fmt_num
from config import SHEET_NAMES


def render(spreadsheet):
    st.subheader("📋 종합 자산 추이")

    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["trend"])
    except gspread.exceptions.WorksheetNotFound:
        st.info("'자산추이' 시트가 아직 없습니다. Google Sheets에 해당 시트를 추가하면 이 화면에 표시됩니다.")
        st.markdown("""
        **권장 컬럼 구성 (시트명: `자산추이`)**
        | 기준일 | 국내자산 | 해외자산 | 가상자산 | 현금성자산 | 부동산 | 기타 | 부채 | 순자산 |
        |---|---|---|---|---|---|---|---|---|
        """)
        return

    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("자산추이 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    numeric_cols = [c for c in df.columns if c != "기준일"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    if "순자산" in df.columns and not df["순자산"].dropna().empty:
        latest = df.iloc[-1]
        st.markdown(f"""
        <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
            <div>최근 순자산: {fmt_num(latest.get("순자산", 0))} 원</div>
        </div>
        """, unsafe_allow_html=True)

    display_df = df.copy()
    for col in numeric_cols:
        display_df[col] = display_df[col].apply(fmt_num)

    st.dataframe(display_df, use_container_width=True)
