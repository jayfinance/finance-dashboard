import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ui.formatters import fmt_num, fmt_pct, apply_krw_hover
from ui.navigation import to_table_button
from config import SHEET_NAMES
from service.sheets import load_sheet_data


def render(spreadsheet, get_usdkrw, get_us_price, get_jpykrw):
    col_t, col_b = st.columns([5, 1])
    with col_t:
        st.subheader("📊 해외 투자자산 차트")
    with col_b:
        to_table_button("해외 투자자산")

    usdkrw = get_usdkrw()
    jpykrw = get_jpykrw()
    rate_map = {"USD": usdkrw, "JPY": jpykrw}

    # ── 데이터 로드 ───────────────────────────────────────
    rows = load_sheet_data(spreadsheet, SHEET_NAMES["overseas"])
    if not rows or len(rows) < 2:
        st.warning("해외자산 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required = ["증권사", "소유", "화폐", "종목티커", "계좌구분", "성격", "보유수량", "매수단가", "매입환율"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"누락된 컬럼: {missing}")
        return

    df = df[required].copy()
    df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].astype(str).str.replace(",", ""), errors="coerce")
    df["매입환율"] = pd.to_numeric(df["매입환율"].astype(str).str.replace(",", ""), errors="coerce")
    df = df.dropna(subset=["보유수량", "매수단가"]).reset_index(drop=True)

    df["현재환율"] = df["화폐"].str.upper().str.strip().map(rate_map)
    df["매입총액(KRW)"] = df["보유수량"] * df["매수단가"] * df["매입환율"]

    with st.spinner("Yahoo Finance에서 현재가 조회 중..."):
        df["현재가"] = df["종목티커"].apply(get_us_price)

    df["평가총액(KRW)"] = df["보유수량"] * df["현재가"] * df["현재환율"]
    df["수익률(%)"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

    df_valid = df.dropna(subset=["평가총액(KRW)", "현재가"]).copy()

    # ── 요약 바 ───────────────────────────────────────────
    total_buy   = df_valid["매입총액(KRW)"].sum()
    total_eval  = df_valid["평가총액(KRW)"].sum()
    total_pl    = total_eval - total_buy
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0
    pl_color = "#ef553b" if total_pl < 0 else "#00cc96"
    st.markdown(f"""
<div style='display:flex;gap:40px;font-size:1.05em;font-weight:bold;padding:8px 0;'>
    <div>매입총액: {fmt_num(total_buy)} 원</div>
    <div>평가총액: {fmt_num(total_eval)} 원</div>
    <div style='color:{pl_color};'>평가손익: {fmt_num(total_pl)} 원</div>
    <div style='color:{pl_color};'>전체 수익률: {fmt_pct(total_yield)}</div>
</div>
""", unsafe_allow_html=True)

    # ── 1행: 종목별 비중 | 소유자별 비중 ─────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 종목별 평가금액 비중")
        pivot_item = (
            df_valid.groupby("종목티커", as_index=False)["평가총액(KRW)"].sum()
            .sort_values("평가총액(KRW)", ascending=False)
        )
        fig1 = px.pie(pivot_item, values="평가총액(KRW)", names="종목티커", hole=0.35)
        fig1.update_traces(textposition="inside", textinfo="percent+label")
        fig1.update_layout(showlegend=False, margin=dict(t=20, b=20))
        apply_krw_hover(fig1)
        st.plotly_chart(fig1, width="stretch")

    with col2:
        st.markdown("##### 소유자별 평가금액 비중")
        pivot_owner = df_valid.groupby("소유", as_index=False)["평가총액(KRW)"].sum()
        fig2 = px.pie(pivot_owner, values="평가총액(KRW)", names="소유", hole=0.35)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(showlegend=False, margin=dict(t=20, b=20))
        apply_krw_hover(fig2)
        st.plotly_chart(fig2, width="stretch")

    # ── 2행: 성격별 비중 | 계좌구분별 비중 ───────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("##### 성격별 평가금액 비중")
        pivot_nature = df_valid.groupby("성격", as_index=False)["평가총액(KRW)"].sum()
        fig3 = px.pie(pivot_nature, values="평가총액(KRW)", names="성격", hole=0.35)
        fig3.update_traces(textposition="inside", textinfo="percent+label")
        fig3.update_layout(showlegend=False, margin=dict(t=20, b=20))
        apply_krw_hover(fig3)
        st.plotly_chart(fig3, width="stretch")

    with col4:
        st.markdown("##### 계좌구분별 평가금액 비중")
        pivot_acct = df_valid.groupby("계좌구분", as_index=False)["평가총액(KRW)"].sum()
        fig4 = px.pie(pivot_acct, values="평가총액(KRW)", names="계좌구분", hole=0.35)
        fig4.update_traces(textposition="inside", textinfo="percent+label")
        fig4.update_layout(showlegend=False, margin=dict(t=20, b=20))
        apply_krw_hover(fig4)
        st.plotly_chart(fig4, width="stretch")

    # ── 3행: 종목별 수익률 ────────────────────────────────
    st.markdown("---")
    st.markdown("##### 종목별 수익률")
    pivot_yield = (
        df_valid.groupby("종목티커", as_index=False)
        .apply(lambda g: pd.Series({
            "매입총액(KRW)": g["매입총액(KRW)"].sum(),
            "평가총액(KRW)": g["평가총액(KRW)"].sum(),
        }))
        .assign(**{"수익률(%)": lambda d: (d["평가총액(KRW)"] / d["매입총액(KRW)"] - 1) * 100})
        .sort_values("수익률(%)", ascending=True)
        .reset_index(drop=True)
    )
    colors = ["#ef553b" if v < 0 else "#00cc96" for v in pivot_yield["수익률(%)"]]
    fig5 = go.Figure(go.Bar(
        x=pivot_yield["수익률(%)"],
        y=pivot_yield["종목티커"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in pivot_yield["수익률(%)"]],
        textposition="outside",
    ))
    fig5.update_layout(yaxis_title=None, xaxis_title="수익률 (%)", margin=dict(t=20))
    st.plotly_chart(fig5, width="stretch")

    # ── 4행: 매입총액 vs 평가총액 ────────────────────────
    st.markdown("---")
    st.markdown("##### 종목별 매입총액 vs 평가총액")
    pivot_bar = (
        df_valid.groupby("종목티커", as_index=False)[["매입총액(KRW)", "평가총액(KRW)"]].sum()
        .sort_values("평가총액(KRW)", ascending=False)
    )
    df_melt = pivot_bar.melt(id_vars="종목티커", value_vars=["매입총액(KRW)", "평가총액(KRW)"],
                             var_name="구분", value_name="금액(KRW)")
    fig6 = px.bar(df_melt, x="종목티커", y="금액(KRW)", color="구분", barmode="group",
                  color_discrete_map={"매입총액(KRW)": "#636efa", "평가총액(KRW)": "#00cc96"})
    fig6.update_layout(xaxis_title=None, margin=dict(t=20))
    apply_krw_hover(fig6)
    st.plotly_chart(fig6, width="stretch")
