import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct
from ui.filters import render_table_filters
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw):
    st.subheader("📋 부동산자산 테이블")

    sheet = spreadsheet.worksheet(SHEET_NAMES["property"])
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("부동산 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required_cols = ["소유", "구분", "매입가", "현재 시세"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"부동산 시트에 누락된 컬럼: {missing}")
        st.write("실제 컬럼:", df.columns.tolist())
        return

    df = df[required_cols].copy()
    df["매입가"] = pd.to_numeric(df["매입가"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    df["현재 시세"] = pd.to_numeric(df["현재 시세"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

    # ── 필터 ──────────────────────────────────────────────
    df = render_table_filters(df, ["소유", "구분"], "property")

    df["평가손익(KRW)"] = df["현재 시세"] - df["매입가"]
    df["수익률(%)"] = (df["평가손익(KRW)"] / df["매입가"].replace(0, float("nan"))) * 100

    total_buy  = df["매입가"].sum()
    total_eval = df["현재 시세"].sum()
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>매입가 합계: {fmt_num(total_buy)} 원</div>
        <div>현재 시세 합계: {fmt_num(total_eval)} 원</div>
        <div>평가손익: {fmt_num(total_eval - total_buy)} 원</div>
        <div>전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    display_df = df.copy()
    for col in ["매입가", "현재 시세", "평가손익(KRW)"]:
        display_df[col] = display_df[col].apply(fmt_num)
    display_df["수익률(%)"] = display_df["수익률(%)"].apply(fmt_pct)

    st.dataframe(display_df, use_container_width=True)
