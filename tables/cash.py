import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct


def render(spreadsheet, get_usdkrw):
    try:
        usdkrw = get_usdkrw()

        left, right = st.columns([4, 1])
        with left:
            st.subheader("📋 현금성자산 테이블")
        with right:
            st.markdown(
                f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {usdkrw:,.2f} KRW/USD</div>"
                if usdkrw else "현재 환율: -",
                unsafe_allow_html=True
            )

        sheet = spreadsheet.worksheet("현금성자산")
        rows = sheet.get_all_values()
        raw_df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

        required_cols = ["증권사", "소유", "계좌구분", "통화", "성격", "금액"]
        missing = [c for c in required_cols if c not in raw_df.columns]
        if missing:
            st.error(f"현금성자산 시트에 다음 컬럼이 없습니다: {missing}")
            st.stop()

        df = raw_df[required_cols].copy()
        df["금액"] = pd.to_numeric(df["금액"].astype(str).str.replace(",", ""), errors="coerce")

        df["금액(KRW)"] = df.apply(
            lambda r: r["금액"] if str(r["통화"]).upper() == "KRW"
            else (r["금액"] * usdkrw if usdkrw else float("nan")),
            axis=1
        )

        total_cash_krw = df["금액(KRW)"].sum()

        st.markdown(f"""
        <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
            <div>현금성자산 총액 (KRW): {fmt_num(total_cash_krw)} 원</div>
        </div>
        """, unsafe_allow_html=True)

        display_df = df.copy()
        display_df["금액"] = display_df["금액"].apply(fmt_num)
        display_df["금액(KRW)"] = display_df["금액(KRW)"].apply(fmt_num)

        st.dataframe(display_df, use_container_width=True)
    except Exception as e:
        st.error(f"현금성자산 테이블 렌더링 중 오류 발생: {e}")
        st.info("현금성자산 기능은 추후 구현 예정입니다.")
