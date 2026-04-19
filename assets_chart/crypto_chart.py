import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ui.components import exchange_rate_header
from ui.formatters import fmt_num, fmt_pct
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw, get_crypto_prices):
    usdkrw = get_usdkrw()
    exchange_rate_header("📊 가상자산 차트", usdkrw)

    sheet = spreadsheet.worksheet(SHEET_NAMES["crypto"])
    rows = sheet.get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    df["수량(qty)"] = pd.to_numeric(df["수량(qty)"].astype(str).str.replace(",", ""), errors="coerce")
    df["평균매수가(avg_price)"] = pd.to_numeric(df["평균매수가(avg_price)"].astype(str).str.replace(",", ""), errors="coerce")
    df["coingecko_id"] = df["coingecko_id"].astype(str).str.strip().str.lower()
    df["통화"] = df["통화"].astype(str).str.strip().str.upper().replace({"원": "KRW", "KR": "KRW", "달러": "USD", "US": "USD"})

    all_ids = df["coingecko_id"].dropna().unique().tolist()
    price_map = get_crypto_prices(tuple(all_ids))
    if price_map is None:
        st.warning("⚠ CoinGecko 호출 제한 발생 — 이전 가격 사용")
        price_map = st.session_state.get("last_crypto_prices", {})
    else:
        st.session_state["last_crypto_prices"] = price_map

    def get_price(row):
        info = price_map.get(row["coingecko_id"], {})
        return info.get("krw") if row["통화"] == "KRW" else info.get("usd")

    df["현재가"] = df.apply(get_price, axis=1)
    df["매입총액"] = df["수량(qty)"] * df["평균매수가(avg_price)"]
    df["매입총액(KRW)"] = df.apply(
        lambda r: r["매입총액"] if r["통화"] == "KRW" else (r["매입총액"] * usdkrw if usdkrw else float("nan")), axis=1
    )
    df["평가총액"] = df["수량(qty)"] * df["현재가"]
    df["평가총액(KRW)"] = df.apply(
        lambda r: r["평가총액"] if r["통화"] == "KRW" else (r["평가총액"] * usdkrw if usdkrw else float("nan")), axis=1
    )
    df["수익률(%)"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

    df_valid = df.dropna(subset=["평가총액(KRW)"])

    # ── 요약 바 ───────────────────────────────────────────
    total_buy   = df_valid["매입총액(KRW)"].sum()
    total_eval  = df_valid["평가총액(KRW)"].sum()
    total_yield = (total_eval / total_buy - 1) * 100 if total_buy else 0
    pl_color = "#ef553b" if total_yield < 0 else "#00cc96"
    st.markdown(f"""
<div style='display:flex;gap:40px;font-size:1.05em;font-weight:bold;padding:8px 0;'>
    <div>매입총액: {fmt_num(total_buy)} 원</div>
    <div>평가총액: {fmt_num(total_eval)} 원</div>
    <div style='color:{pl_color};'>전체 수익률: {fmt_pct(total_yield)}</div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 코인별 평가금액 비중 (KRW)")
        fig = px.pie(df_valid, values="평가총액(KRW)", names="코인", hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("##### 코인별 수익률")
        pivot_yield = (
            df_valid.groupby("코인", as_index=False)
            .apply(lambda g: pd.Series({
                "매입총액(KRW)": g["매입총액(KRW)"].sum(),
                "평가총액(KRW)": g["평가총액(KRW)"].sum(),
            }))
            .assign(**{"수익률(%)": lambda d: (d["평가총액(KRW)"] / d["매입총액(KRW)"] - 1) * 100})
            .sort_values("수익률(%)", ascending=True)
            .reset_index(drop=True)
        )
        colors = ["#ef553b" if v < 0 else "#00cc96" for v in pivot_yield["수익률(%)"]]
        fig2 = go.Figure(go.Bar(
            x=pivot_yield["수익률(%)"],
            y=pivot_yield["코인"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:.1f}%" for v in pivot_yield["수익률(%)"]],
            textposition="outside",
        ))
        fig2.update_layout(yaxis_title=None, xaxis_title="수익률 (%)", margin=dict(t=20))
        st.plotly_chart(fig2, width="stretch")

    if "소유" in df_valid.columns:
        st.markdown("---")
        col_o1, _ = st.columns(2)
        with col_o1:
            st.markdown("##### 소유자별 평가금액 비중")
            pivot_owner = df_valid.groupby("소유", as_index=False)["평가총액(KRW)"].sum()
            fig_o = px.pie(pivot_owner, values="평가총액(KRW)", names="소유", hole=0.35)
            fig_o.update_traces(textposition="inside", textinfo="percent+label")
            fig_o.update_layout(showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig_o, width="stretch")

    st.markdown("##### 코인별 매입총액 vs 평가총액 (KRW)")
    pivot_bar = (
        df_valid.groupby("코인", as_index=False)[["매입총액(KRW)", "평가총액(KRW)"]].sum()
        .sort_values("평가총액(KRW)", ascending=False)
    )
    df_bar = pivot_bar.melt(id_vars="코인", value_vars=["매입총액(KRW)", "평가총액(KRW)"],
                            var_name="구분", value_name="금액(KRW)")
    fig3 = px.bar(df_bar, x="코인", y="금액(KRW)", color="구분", barmode="group",
                  color_discrete_map={"매입총액(KRW)": "#636efa", "평가총액(KRW)": "#00cc96"})
    fig3.update_layout(xaxis_title=None, margin=dict(t=20))
    st.plotly_chart(fig3, width="stretch")
