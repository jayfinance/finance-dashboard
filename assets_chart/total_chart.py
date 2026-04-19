import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ui.formatters import fmt_num, fmt_pct, korean_yaxis, apply_krw_hover
from ui.navigation import to_table_button
from assets_table.total import (
    _sum_domestic, _sum_overseas, _sum_crypto,
    _sum_cash, _sum_property, _sum_etc, _sum_debt,
    _byowner_domestic, _byowner_overseas, _byowner_crypto,
    _byowner_cash, _byowner_property, _byowner_etc, _byowner_debt,
)


def render(spreadsheet, get_usdkrw, get_kr_price, get_us_price, get_crypto_prices, gold_override, get_jpykrw):
    col_t, col_b = st.columns([5, 1])
    with col_t:
        st.subheader("📊 종합 자산 차트")
    with col_b:
        to_table_button("종합")

    with st.spinner("전체 자산 데이터 로딩 중..."):
        dom_buy,  dom_eval  = _sum_domestic(spreadsheet, get_kr_price, gold_override)
        ovs_buy,  ovs_eval  = _sum_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw)
        cry_buy,  cry_eval  = _sum_crypto(spreadsheet, get_usdkrw, get_crypto_prices)
        cash_buy, cash_eval = _sum_cash(spreadsheet, get_usdkrw)
        prop_buy, prop_eval = _sum_property(spreadsheet)
        etc_buy,  etc_eval  = _sum_etc(spreadsheet)
        debt_total          = _sum_debt(spreadsheet)

    categories  = ["국내 투자자산", "해외 투자자산", "가상자산", "현금성자산", "부동산자산", "기타자산"]
    buy_values  = [dom_buy,  ovs_buy,  cry_buy,  cash_buy,  prop_buy,  etc_buy]
    eval_values = [dom_eval, ovs_eval, cry_eval, cash_eval, prop_eval, etc_eval]

    df_assets = pd.DataFrame({
        "자산 종류":      categories,
        "매입금액 (KRW)": buy_values,
        "평가금액 (KRW)": eval_values,
    })
    df_assets["평가손익 (KRW)"] = df_assets["평가금액 (KRW)"] - df_assets["매입금액 (KRW)"]
    df_assets["수익률 (%)"] = (
        df_assets["평가금액 (KRW)"] / df_assets["매입금액 (KRW)"].replace(0, float("nan")) - 1
    ) * 100

    total_buy    = sum(buy_values)
    total_assets = sum(eval_values)
    net_assets   = total_assets - debt_total
    total_pl     = total_assets - total_buy
    net_pl       = total_pl - debt_total
    total_yield  = (total_assets / total_buy - 1) * 100 if total_buy else 0
    npl_color    = "#ef553b" if net_pl < 0 else "#00cc96"

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.05em;font-weight:bold;padding:8px 0;'>
        <div>총 매입금액: {fmt_num(total_buy)} 원</div>
        <div>총 자산: {fmt_num(total_assets)} 원</div>
        <div>부채: {fmt_num(debt_total)} 원</div>
        <div>순자산: {fmt_num(net_assets)} 원</div>
        <div style='color:{npl_color};'>순 평가손익: {fmt_num(net_pl)} 원</div>
        <div>전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 차트 1 & 2: 비중 / 자산-부채-순자산 ───────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 자산 종류별 비중")
        fig1 = px.pie(
            df_assets[df_assets["평가금액 (KRW)"] > 0],
            values="평가금액 (KRW)", names="자산 종류", hole=0.3,
        )
        fig1.update_traces(textposition="inside", textinfo="percent+label")
        apply_krw_hover(fig1)
        st.plotly_chart(fig1, width="stretch")

    with col2:
        st.markdown("##### 총자산 / 부채 / 순자산")
        df_net = pd.DataFrame({
            "구분":        ["총자산", "부채", "순자산"],
            "금액 (KRW)":  [total_assets, debt_total, net_assets],
        })
        fig2 = px.bar(
            df_net, x="구분", y="금액 (KRW)", color="구분",
            color_discrete_sequence=["#636efa", "#ef553b", "#00cc96"],
        )
        fig2.update_layout(showlegend=False, yaxis=korean_yaxis(max(total_assets, debt_total, net_assets)))
        apply_krw_hover(fig2)
        st.plotly_chart(fig2, width="stretch")

    # ── 차트 3: 매입 vs 평가 ────────────────────────────────
    st.markdown("##### 자산 종류별 매입 vs 평가")
    df_melt = df_assets.melt(
        id_vars="자산 종류",
        value_vars=["매입금액 (KRW)", "평가금액 (KRW)"],
        var_name="구분", value_name="금액 (KRW)",
    )
    fig3 = px.bar(df_melt, x="자산 종류", y="금액 (KRW)", color="구분", barmode="group")
    fig3.update_layout(yaxis=korean_yaxis(df_melt["금액 (KRW)"].max()))
    apply_krw_hover(fig3)
    st.plotly_chart(fig3, width="stretch")

    # ── 차트 4: 수익률 ──────────────────────────────────────
    st.markdown("##### 자산 종류별 수익률")
    df_yield = df_assets.dropna(subset=["수익률 (%)"]).copy()
    fig4 = go.Figure(go.Bar(
        x=df_yield["자산 종류"],
        y=df_yield["수익률 (%)"],
        marker_color=["#ef553b" if v < 0 else "#00cc96" for v in df_yield["수익률 (%)"]],
    ))
    fig4.update_layout(yaxis_ticksuffix="%", showlegend=False)
    st.plotly_chart(fig4, width="stretch")

    # ── 차트 5 & 6: 소유자별 ────────────────────────────────
    with st.spinner("소유자별 데이터 로딩 중..."):
        dom_eval_by,  _ = _byowner_domestic(spreadsheet, get_kr_price, gold_override)
        ovs_eval_by,  _ = _byowner_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw)
        cry_eval_by,  _ = _byowner_crypto(spreadsheet, get_usdkrw, get_crypto_prices)
        cash_eval_by, _ = _byowner_cash(spreadsheet, get_usdkrw)
        prop_eval_by, _ = _byowner_property(spreadsheet)
        etc_eval_by,  _ = _byowner_etc(spreadsheet)
        debt_by         = _byowner_debt(spreadsheet)

    asset_labels = ["국내 투자자산", "해외 투자자산", "가상자산", "현금성자산", "부동산자산", "기타자산"]
    eval_dicts   = [dom_eval_by, ovs_eval_by, cry_eval_by, cash_eval_by, prop_eval_by, etc_eval_by]
    all_owners   = sorted({o for d in eval_dicts + [debt_by] for o in d})

    owner_rows = [
        {
            "소유":        owner,
            "순자산 (KRW)": sum(d.get(owner, 0) for d in eval_dicts) - debt_by.get(owner, 0),
        }
        for owner in all_owners
    ]
    df_owner = pd.DataFrame(owner_rows)

    col5, col6 = st.columns(2)

    with col5:
        st.markdown("##### 소유자별 순자산 비중")
        fig5 = px.pie(
            df_owner[df_owner["순자산 (KRW)"] > 0],
            values="순자산 (KRW)", names="소유", hole=0.3,
        )
        fig5.update_traces(textposition="inside", textinfo="percent+label")
        apply_krw_hover(fig5)
        st.plotly_chart(fig5, width="stretch")

    with col6:
        st.markdown("##### 소유자별 자산 구성")
        stacked_rows = [
            {"소유": owner, "자산 종류": label, "금액 (KRW)": d.get(owner, 0)}
            for owner in all_owners
            for label, d in zip(asset_labels, eval_dicts)
        ]
        df_stacked = pd.DataFrame(stacked_rows)
        max_stacked = df_stacked.groupby("소유")["금액 (KRW)"].sum().max()
        fig6 = px.bar(df_stacked, x="소유", y="금액 (KRW)", color="자산 종류", barmode="stack")
        fig6.update_layout(yaxis=korean_yaxis(max_stacked))
        apply_krw_hover(fig6)
        st.plotly_chart(fig6, width="stretch")
