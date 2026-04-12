import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct
from ui.filters import render_table_filters
from config import SHEET_NAMES


def render(spreadsheet, get_kr_price, gold_override):

    st.subheader("📋 국내 투자자산 평가 테이블")

    # ── 시트 로드 ──────────────────────────────────────────
    sheet = spreadsheet.worksheet(SHEET_NAMES["domestic"])
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        st.warning("국내자산 시트에 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    required = ["증권사", "소유", "종목명", "종목코드", "계좌구분", "성격", "보유수량", "매수단가"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"누락된 컬럼: {missing}")
        st.write("실제 컬럼:", df.columns.tolist())
        return

    df = df[required].copy()
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
    df["매수단가"] = pd.to_numeric(df["매수단가"].astype(str).str.replace(",", ""), errors="coerce")

    # 빈 행 제거 (보유수량·매수단가 없는 행)
    df = df.dropna(subset=["보유수량", "매수단가"]).reset_index(drop=True)

    # ── 필터 ──────────────────────────────────────────────
    df = render_table_filters(df, ["증권사", "소유", "종목명", "계좌구분", "성격"], "domestic")

    # ── 매입총액 계산 ──────────────────────────────────────
    df["매입총액 (KRW)"] = df["보유수량"] * df["매수단가"]

    # ── 현재가 조회 (Yahoo Finance) ───────────────────────
    with st.spinner("Yahoo Finance에서 현재가 조회 중..."):
        df["현재가"] = [
            get_kr_price(t, n, gold_override)
            for t, n in zip(df["종목코드"], df["종목명"])
        ]

    # ── 평가 계산 ──────────────────────────────────────────
    df["평가총액 (KRW)"] = df["보유수량"] * df["현재가"]
    df["평가손익 (KRW)"] = df["평가총액 (KRW)"] - df["매입총액 (KRW)"]
    df["수익률 (%)"] = (df["평가총액 (KRW)"] / df["매입총액 (KRW)"] - 1) * 100

    # ── 현재가 미조회 종목 안내 ────────────────────────────
    no_price = df[df["현재가"].isna()]["종목명"].tolist()
    if no_price:
        st.warning(f"현재가 조회 실패 종목 (Yahoo Finance 미지원 또는 오류): {', '.join(no_price)}")

    # ── 합계 ──────────────────────────────────────────────
    total_buy   = df["매입총액 (KRW)"].sum()
    total_eval  = df["평가총액 (KRW)"].sum()
    total_pl    = df["평가손익 (KRW)"].sum()
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
    for col in ["보유수량", "매수단가", "매입총액 (KRW)", "현재가", "평가총액 (KRW)", "평가손익 (KRW)"]:
        display_df[col] = display_df[col].apply(fmt_num)
    display_df["수익률 (%)"] = display_df["수익률 (%)"].apply(fmt_pct)

    st.dataframe(display_df, use_container_width=True)

    # ── 종목명별 요약 테이블 ───────────────────────────────
    st.markdown("---")
    st.markdown("##### 종목별 요약")

    pivot = (
        df.groupby("종목명", as_index=False)
        .agg(보유수량=("보유수량", "sum"), **{"평가총액 (KRW)": ("평가총액 (KRW)", "sum")})
        .sort_values("평가총액 (KRW)", ascending=False)
        .reset_index(drop=True)
    )
    total_eval_p = pivot["평가총액 (KRW)"].sum()
    pivot["평가총액 비율"] = pivot["평가총액 (KRW)"] / total_eval_p * 100 if total_eval_p else 0

    sum_row = pd.DataFrame([{
        "종목명": "Sum",
        "보유수량": pivot["보유수량"].sum(),
        "평가총액 (KRW)": pivot["평가총액 (KRW)"].sum(),
        "평가총액 비율": 100.0,
    }])
    pivot_num = pd.concat([pivot, sum_row], ignore_index=True)

    non_sum_idx = pivot_num.index[pivot_num["종목명"] != "Sum"]

    def _highlight_sum(row):
        if row["종목명"] == "Sum":
            return ["background-color: rgba(204, 255, 255, 0.25); font-weight: bold"] * len(row)
        return [""] * len(row)

    styler = (
        pivot_num.style
        .background_gradient(
            subset=pd.IndexSlice[non_sum_idx, ["평가총액 비율"]],
            cmap="Blues",
        )
        .apply(_highlight_sum, axis=1)
        .format({
            "보유수량":      fmt_num,
            "평가총액 (KRW)": fmt_num,
            "평가총액 비율": fmt_pct,
        })
    )

    st.dataframe(styler, use_container_width=True)
