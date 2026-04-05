import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_num2, fmt_pct
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw, get_us_price, get_jpykrw):

    usdkrw = get_usdkrw()
    jpykrw = get_jpykrw()

    # ── 환율 드롭다운 헤더 ─────────────────────────────────
    left, right = st.columns([3, 2])
    with left:
        st.subheader("📋 해외 투자자산 평가 테이블")
    with right:
        currency_display = st.selectbox(
            "환율 표시",
            ["USD/KRW", "JPY/KRW"],
            index=0,
            label_visibility="collapsed",
        )
        rate_val = usdkrw if currency_display == "USD/KRW" else jpykrw
        rate_label = "KRW/USD" if currency_display == "USD/KRW" else "KRW/JPY"
        if rate_val is not None:
            st.markdown(
                f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {rate_val:,.2f} {rate_label}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: -</div>",
                unsafe_allow_html=True,
            )

    view_option = st.radio("표시 통화 옵션", ["모두 보기", "LC로 보기", "KRW로 보기"], horizontal=True)

    # ── 시트 로드 ──────────────────────────────────────────
    sheet = spreadsheet.worksheet(SHEET_NAMES["overseas"])
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("해외자산 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required = ["증권사", "소유", "화폐", "종목티커", "계좌구분", "성격", "보유수량", "매수단가", "매입환율"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"누락된 컬럼: {missing}")
        st.write("실제 컬럼:", df.columns.tolist())
        return

    df = df[required].copy()
    df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].astype(str).str.replace(",", ""), errors="coerce")
    df["매입환율"] = pd.to_numeric(df["매입환율"].astype(str).str.replace(",", ""), errors="coerce")

    df = df.dropna(subset=["보유수량", "매수단가"]).reset_index(drop=True)

    # ── 화폐별 현재 환율 매핑 ──────────────────────────────
    rate_map = {"USD": usdkrw, "JPY": jpykrw}
    df["현재환율"] = df["화폐"].str.upper().str.strip().map(rate_map)

    # ── 매입총액 ───────────────────────────────────────────
    df["매입총액(LC)"] = df["보유수량"] * df["매수단가"]
    df["매입총액(KRW)"] = df["보유수량"] * df["매수단가"] * df["매입환율"]

    # ── 현재가 조회 ────────────────────────────────────────
    with st.spinner("Yahoo Finance에서 현재가 조회 중..."):
        df["현재가"] = df["종목티커"].apply(get_us_price)

    # ── 평가 계산 ──────────────────────────────────────────
    df["평가총액(LC)"] = df["보유수량"] * df["현재가"]
    df["평가총액(KRW)"] = df["보유수량"] * df["현재가"] * df["현재환율"]
    df["평가손익(LC)"] = df["평가총액(LC)"] - df["매입총액(LC)"]
    df["평가손익(KRW)"] = df["평가총액(KRW)"] - df["매입총액(KRW)"]
    df["수익률(LC)"] = (df["평가총액(LC)"] / df["매입총액(LC)"] - 1) * 100
    df["수익률(KRW)"] = (df["평가총액(KRW)"] / df["매입총액(KRW)"] - 1) * 100

    # ── 합계 표시 ──────────────────────────────────────────
    if view_option == "LC로 보기":
        # 화폐별 소계
        currencies = df["화폐"].str.upper().str.strip().unique()
        parts = []
        for cur in sorted(currencies):
            sub = df[df["화폐"].str.upper().str.strip() == cur]
            b = sub["매입총액(LC)"].sum()
            e = sub["평가총액(LC)"].sum()
            p = sub["평가손익(LC)"].sum()
            y = (e / b - 1) * 100 if b else 0
            c = "#ef553b" if p < 0 else "#00cc96"
            parts.append(
                f"<div style='border:1px solid #444;border-radius:6px;padding:6px 14px;'>"
                f"<span style='font-size:0.85em;color:gray;'>{cur}</span><br>"
                f"매입: {fmt_num2(b)} | 평가: {fmt_num2(e)} | "
                f"<span style='color:{c};'>손익: {fmt_num2(p)} | {fmt_pct(y)}</span>"
                f"</div>"
            )
        st.markdown(
            f"<div style='display:flex;gap:16px;font-size:1.0em;font-weight:bold;padding:8px 0;flex-wrap:wrap;'>{''.join(parts)}</div>",
            unsafe_allow_html=True,
        )
    else:
        total_buy  = df["매입총액(KRW)"].sum()
        total_eval = df["평가총액(KRW)"].sum()
        total_pl   = df["평가손익(KRW)"].sum()
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

    # ── 표시용 DataFrame ───────────────────────────────────
    display_df = df.copy()
    display_df["매수단가"]     = display_df["매수단가"].apply(fmt_num2)
    display_df["현재가"]       = display_df["현재가"].apply(fmt_num2)
    display_df["매입환율"]     = display_df["매입환율"].apply(fmt_num2)
    display_df["현재환율"]     = display_df["현재환율"].apply(fmt_num2)
    display_df["매입총액(LC)"] = display_df["매입총액(LC)"].apply(fmt_num2)
    display_df["매입총액(KRW)"] = display_df["매입총액(KRW)"].apply(fmt_num)
    display_df["평가총액(LC)"] = display_df["평가총액(LC)"].apply(fmt_num2)
    display_df["평가총액(KRW)"] = display_df["평가총액(KRW)"].apply(fmt_num)
    display_df["평가손익(LC)"] = display_df["평가손익(LC)"].apply(fmt_num2)
    display_df["평가손익(KRW)"] = display_df["평가손익(KRW)"].apply(fmt_num)
    display_df["수익률(LC)"]   = display_df["수익률(LC)"].apply(fmt_pct)
    display_df["수익률(KRW)"]  = display_df["수익률(KRW)"].apply(fmt_pct)

    base_cols = ["증권사", "소유", "화폐", "종목티커", "계좌구분", "성격", "보유수량", "매수단가", "현재가"]

    if view_option == "LC로 보기":
        cols = base_cols + ["매입총액(LC)", "평가총액(LC)", "평가손익(LC)", "수익률(LC)"]
    elif view_option == "KRW로 보기":
        cols = base_cols + ["매입환율", "현재환율", "매입총액(KRW)", "평가총액(KRW)", "평가손익(KRW)", "수익률(KRW)"]
    else:
        cols = base_cols + [
            "매입총액(LC)", "평가총액(LC)", "평가손익(LC)", "수익률(LC)",
            "매입환율", "현재환율", "매입총액(KRW)", "평가총액(KRW)", "평가손익(KRW)", "수익률(KRW)",
        ]

    st.dataframe(display_df[cols], use_container_width=True)
