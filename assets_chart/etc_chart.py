import streamlit as st
import pandas as pd
import plotly.express as px
from ui.navigation import to_table_button
from ui.formatters import fmt_num, fmt_pct, korean_yaxis, apply_krw_hover
from config import SHEET_NAMES
from service.sheets import load_sheet_data


def render(spreadsheet, get_usdkrw):
    col_t, col_b = st.columns([5, 1])
    with col_t:
        st.subheader("📊 기타자산 차트")
    with col_b:
        to_table_button("기타자산")

    rows = load_sheet_data(spreadsheet, SHEET_NAMES["etc"])
    if not rows or len(rows) < 2:
        st.warning("기타자산 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    for col in ["매입가", "현재 시세"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

    if "매입가" not in df.columns or "현재 시세" not in df.columns:
        st.error("매입가 또는 현재 시세 컬럼이 없습니다.")
        return

    df["평가손익(KRW)"] = df["현재 시세"] - df["매입가"]

    total_buy = df["매입가"].sum()
    total_eval = df["현재 시세"].sum()
    total_pl = total_eval - total_buy
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0
    pl_color = "#ef553b" if total_pl < 0 else "#00cc96"
    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.05em;font-weight:bold;padding:8px 0;'>
        <div>매입가 합계: {fmt_num(total_buy)} 원</div>
        <div>현재 시세 합계: {fmt_num(total_eval)} 원</div>
        <div style='color:{pl_color};'>평가손익: {fmt_num(total_pl)} 원</div>
        <div style='color:{pl_color};'>전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    name_col = "종목명" if "종목명" in df.columns else df.columns[0]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 종목별 현재 시세 비중")
        fig = px.pie(df, values="현재 시세", names=name_col, hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        apply_krw_hover(fig)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("##### 종목별 평가손익")
        fig2 = px.bar(df, x=name_col, y="평가손익(KRW)",
                      color="평가손익(KRW)", color_continuous_scale=["#ef553b", "#636efa", "#00cc96"])
        fig2.update_layout(
            coloraxis_showscale=False,
            yaxis=korean_yaxis(df["평가손익(KRW)"].max(), df["평가손익(KRW)"].min()),
        )
        apply_krw_hover(fig2)
        st.plotly_chart(fig2, width="stretch")

    if "소유" in df.columns:
        col_o1, _ = st.columns(2)
        with col_o1:
            st.markdown("##### 소유자별 평가금액 비중")
            pivot_owner = df.groupby("소유", as_index=False)["현재 시세"].sum()
            fig_o = px.pie(pivot_owner, values="현재 시세", names="소유", hole=0.35)
            fig_o.update_traces(textposition="inside", textinfo="percent+label")
            fig_o.update_layout(showlegend=False, margin=dict(t=20, b=20))
            apply_krw_hover(fig_o)
            st.plotly_chart(fig_o, width="stretch")

    st.markdown("##### 종목별 매입가 vs 현재 시세")
    df_bar = df.melt(id_vars=name_col, value_vars=["매입가", "현재 시세"], var_name="구분", value_name="금액(KRW)")
    fig3 = px.bar(df_bar, x=name_col, y="금액(KRW)", color="구분", barmode="group")
    fig3.update_layout(yaxis=korean_yaxis(df_bar["금액(KRW)"].max()))
    apply_krw_hover(fig3)
    st.plotly_chart(fig3, width="stretch")
