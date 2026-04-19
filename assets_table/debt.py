import streamlit as st
import pandas as pd
from ui.formatters import fmt_num
from ui.filters import render_table_filters
from ui.navigation import to_chart_button
from config import SHEET_NAMES
from service.sheets import load_sheet_data


def render(spreadsheet, get_usdkrw):
    col_t, col_b = st.columns([5, 1])
    with col_t:
        st.subheader("📋 부채 테이블")
    with col_b:
        to_chart_button("부채 차트")

    rows = load_sheet_data(spreadsheet, SHEET_NAMES["debt"])
    if not rows or len(rows) < 2:
        st.warning("부채 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required_cols = ["소유", "구분", "현재부채"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"부채 시트에 누락된 컬럼: {missing}")
        st.write("실제 컬럼:", df.columns.tolist())
        return

    df = df[required_cols].copy()
    df["현재부채"] = pd.to_numeric(df["현재부채"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

    # ── 필터 ──────────────────────────────────────────────
    df = render_table_filters(df, ["소유", "구분"], "debt")

    total_debt = df["현재부채"].sum()

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>총 부채: {fmt_num(total_debt)} 원</div>
    </div>
    """, unsafe_allow_html=True)

    display_df = df.copy()
    display_df["현재부채"] = display_df["현재부채"].apply(fmt_num)

    st.dataframe(display_df, width="stretch")
