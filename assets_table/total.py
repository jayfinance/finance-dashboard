import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct
from config import SHEET_NAMES


# ── 카테고리별 KRW 합산 헬퍼 ──────────────────────────────────────────────────

def _sum_domestic(spreadsheet, get_kr_price, gold_override):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["domestic"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
        df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
        df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")
        df["매입총액"] = df["보유수량"] * df["매수단가"]
        df["현재가"] = [get_kr_price(t, n, gold_override) for t, n in zip(df["종목코드"], df["종목명"])]
        df["평가총액"] = df["보유수량"] * df["현재가"]
        return df["매입총액"].sum(), df["평가총액"].sum()
    except Exception:
        return 0, 0


def _sum_overseas(spreadsheet, get_usdkrw, get_us_price):
    try:
        usdkrw = get_usdkrw()
        sheet = spreadsheet.worksheet(SHEET_NAMES["overseas"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df.rename(columns={"매입가": "매수단가"}, inplace=True)
        df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
        df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")
        df["매입환율"] = pd.to_numeric(df["매입환율"].str.replace(",", ""), errors="coerce")
        df["매입총액(KRW)"] = df["보유수량"] * df["매수단가"] * df["매입환율"]
        df["현재가"] = df["종목티커"].apply(get_us_price)
        df["평가총액(KRW)"] = df["보유수량"] * df["현재가"] * (usdkrw or 0)
        return df["매입총액(KRW)"].sum(), df["평가총액(KRW)"].sum()
    except Exception:
        return 0, 0


def _sum_crypto(spreadsheet, get_usdkrw, get_crypto_prices):
    try:
        usdkrw = get_usdkrw()
        sheet = spreadsheet.worksheet(SHEET_NAMES["crypto"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["수량(qty)"] = pd.to_numeric(df["수량(qty)"].astype(str).str.replace(",", ""), errors="coerce")
        df["평균매수가(avg_price)"] = pd.to_numeric(df["평균매수가(avg_price)"].astype(str).str.replace(",", ""), errors="coerce")
        df["coingecko_id"] = df["coingecko_id"].astype(str).str.strip().str.lower()
        df["통화"] = df["통화"].astype(str).str.strip().str.upper().replace({"원": "KRW", "KR": "KRW", "달러": "USD", "US": "USD"})
        all_ids = df["coingecko_id"].dropna().unique().tolist()
        price_map = get_crypto_prices(tuple(all_ids)) or st.session_state.get("last_crypto_prices", {})

        def to_krw(r, col):
            val = r[col]
            if r["통화"] == "KRW":
                return val
            return val * usdkrw if usdkrw else float("nan")

        df["매입총액"] = df["수량(qty)"] * df["평균매수가(avg_price)"]
        df["매입총액(KRW)"] = df.apply(lambda r: to_krw(r, "매입총액"), axis=1)

        def get_price(row):
            info = price_map.get(row["coingecko_id"], {})
            return info.get("krw") if row["통화"] == "KRW" else info.get("usd")

        df["현재가"] = df.apply(get_price, axis=1)
        df["평가총액"] = df["수량(qty)"] * df["현재가"]
        df["평가총액(KRW)"] = df.apply(lambda r: to_krw(r, "평가총액"), axis=1)
        return df["매입총액(KRW)"].sum(), df["평가총액(KRW)"].sum()
    except Exception:
        return 0, 0


def _sum_cash(spreadsheet, get_usdkrw):
    try:
        usdkrw = get_usdkrw()
        sheet = spreadsheet.worksheet(SHEET_NAMES["cash"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["금액"] = pd.to_numeric(df["금액"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["통화"] = df["통화"].astype(str).str.strip().str.upper()
        df["금액(KRW)"] = df.apply(
            lambda r: r["금액"] if r["통화"] == "KRW" else (r["금액"] * usdkrw if usdkrw else 0), axis=1
        )
        total = df["금액(KRW)"].fillna(0).sum()
        return total, total
    except Exception:
        return 0, 0


def _sum_property(spreadsheet):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["property"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        buy = pd.to_numeric(df["매입가"].astype(str).str.replace(",", ""), errors="coerce").fillna(0).sum()
        cur = pd.to_numeric(df["현재 시세"].astype(str).str.replace(",", ""), errors="coerce").fillna(0).sum()
        return buy, cur
    except Exception:
        return 0, 0


def _sum_etc(spreadsheet):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["etc"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        buy = pd.to_numeric(df["매입가"].astype(str).str.replace(",", ""), errors="coerce").fillna(0).sum()
        cur = pd.to_numeric(df["현재 시세"].astype(str).str.replace(",", ""), errors="coerce").fillna(0).sum()
        return buy, cur
    except Exception:
        return 0, 0


def _sum_debt(spreadsheet, get_usdkrw):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["debt"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["현재부채"] = pd.to_numeric(df["현재부채"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        return df["현재부채"].sum()
    except Exception:
        return 0


# ── 메인 렌더 ─────────────────────────────────────────────────────────────────

def render(spreadsheet, get_usdkrw, get_kr_price, get_us_price, get_crypto_prices, gold_override):
    st.subheader("📋 종합 자산 요약")

    with st.spinner("전체 자산 데이터 로딩 중..."):
        dom_buy, dom_eval   = _sum_domestic(spreadsheet, get_kr_price, gold_override)
        ovs_buy, ovs_eval   = _sum_overseas(spreadsheet, get_usdkrw, get_us_price)
        cry_buy, cry_eval   = _sum_crypto(spreadsheet, get_usdkrw, get_crypto_prices)
        cash_buy, cash_eval = _sum_cash(spreadsheet, get_usdkrw)
        prop_buy, prop_eval = _sum_property(spreadsheet)
        etc_buy, etc_eval   = _sum_etc(spreadsheet)
        debt_total          = _sum_debt(spreadsheet, get_usdkrw)

    rows = [
        {"자산 종류": "국내 투자자산", "취득금액 (KRW)": dom_buy,  "현재금액 (KRW)": dom_eval},
        {"자산 종류": "해외 투자자산", "취득금액 (KRW)": ovs_buy,  "현재금액 (KRW)": ovs_eval},
        {"자산 종류": "가상자산",      "취득금액 (KRW)": cry_buy,  "현재금액 (KRW)": cry_eval},
        {"자산 종류": "현금성자산",    "취득금액 (KRW)": cash_buy, "현재금액 (KRW)": cash_eval},
        {"자산 종류": "부동산자산",    "취득금액 (KRW)": prop_buy, "현재금액 (KRW)": prop_eval},
        {"자산 종류": "기타자산",      "취득금액 (KRW)": etc_buy,  "현재금액 (KRW)": etc_eval},
    ]
    df = pd.DataFrame(rows)
    df["평가손익 (KRW)"] = df["현재금액 (KRW)"] - df["취득금액 (KRW)"]
    df["수익률 (%)"] = (df["현재금액 (KRW)"] / df["취득금액 (KRW)"].replace(0, float("nan")) - 1) * 100

    total_assets = df["현재금액 (KRW)"].sum()
    total_buy    = df["취득금액 (KRW)"].sum()
    net_assets   = total_assets - debt_total
    total_yield  = (total_assets / total_buy - 1) * 100 if total_buy else 0

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>총 취득금액: {fmt_num(total_buy)} 원</div>
        <div>총 자산: {fmt_num(total_assets)} 원</div>
        <div>부채: {fmt_num(debt_total)} 원</div>
        <div>순자산: {fmt_num(net_assets)} 원</div>
        <div>전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    # 부채 행 추가
    debt_row = pd.DataFrame([{
        "자산 종류": "부채",
        "취득금액 (KRW)": debt_total,
        "현재금액 (KRW)": debt_total,
        "평가손익 (KRW)": 0,
        "수익률 (%)": float("nan"),
    }])
    display_df = pd.concat([df, debt_row], ignore_index=True)

    fmt_df = display_df.copy()
    for col in ["취득금액 (KRW)", "현재금액 (KRW)", "평가손익 (KRW)"]:
        fmt_df[col] = fmt_df[col].apply(fmt_num)
    fmt_df["수익률 (%)"] = fmt_df["수익률 (%)"].apply(fmt_pct)

    st.dataframe(fmt_df, use_container_width=True)
