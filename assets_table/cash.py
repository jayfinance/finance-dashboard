import streamlit as st
import pandas as pd
import gspread
from ui.formatters import fmt_num
from ui.components import exchange_rate_header
from ui.filters import render_table_filters
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw):
    usdkrw = get_usdkrw()
    exchange_rate_header("📋 현금성자산 테이블", usdkrw, nav_label="📊 차트 보러가기", nav_section="Chart", nav_page="현금성자산 차트")

    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["cash"])
    except gspread.exceptions.WorksheetNotFound:
        st.error("❌ '현금성자산' 시트를 찾을 수 없습니다.")
        st.write("사용 가능한 시트:", [ws.title for ws in spreadsheet.worksheets()])
        st.stop()

    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("현금성자산 시트에 데이터가 없습니다.")
        st.stop()

    raw_df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required_cols = ["증권사", "소유", "계좌구분", "통화", "성격", "금액"]
    missing = [c for c in required_cols if c not in raw_df.columns]
    if missing:
        st.error(f"현금성자산 시트에 누락된 컬럼: {missing}")
        st.stop()

    df = raw_df[required_cols].copy()
    df["금액"] = pd.to_numeric(df["금액"].astype(str).str.replace(",", ""), errors="coerce")

    # ── 필터 ──────────────────────────────────────────────
    df = render_table_filters(df, ["증권사", "소유", "계좌구분", "통화", "성격"], "cash")

    def convert_to_krw(row):
        currency = str(row["통화"]).strip().upper()
        if currency == "KRW":
            return row["금액"]
        elif usdkrw is not None:
            return row["금액"] * usdkrw
        return None

    df["금액(KRW)"] = df.apply(convert_to_krw, axis=1)

    total_cash_krw = df["금액(KRW)"].fillna(0).sum()

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>현금성자산 총액 (KRW): {fmt_num(total_cash_krw)} 원</div>
    </div>
    """, unsafe_allow_html=True)

    display_df = df.copy()
    display_df["금액"] = display_df["금액"].apply(fmt_num)
    display_df["금액(KRW)"] = display_df["금액(KRW)"].apply(fmt_num)

    st.dataframe(display_df, width="stretch")
