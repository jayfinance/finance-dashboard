import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct
from config import SHEET_NAMES

NATURES    = ["금", "배당", "성장", "안정", "채권", "현금", "예금", "펀드", "가상자산"]
ASSET_COLS = ["국내 투자자산", "해외 투자자산", "가상자산", "현금성 자산", "기타자산"]


# ── 카테고리별 KRW 합산 헬퍼 (전체 합계용) ───────────────────────────────────

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


def _sum_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw):
    try:
        usdkrw = get_usdkrw()
        jpykrw = get_jpykrw()
        rate_map = {"USD": usdkrw, "JPY": jpykrw}
        sheet = spreadsheet.worksheet(SHEET_NAMES["overseas"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
        df["매수단가"] = pd.to_numeric(df["매수단가"].astype(str).str.replace(",", ""), errors="coerce")
        df["매입환율"] = pd.to_numeric(df["매입환율"].astype(str).str.replace(",", ""), errors="coerce")
        df["현재환율"] = df["화폐"].str.upper().str.strip().map(rate_map)
        df = df.dropna(subset=["보유수량", "매수단가"])
        df["매입총액(KRW)"] = df["보유수량"] * df["매수단가"] * df["매입환율"]
        df["현재가"] = df["종목티커"].apply(get_us_price)
        df["평가총액(KRW)"] = df["보유수량"] * df["현재가"] * df["현재환율"]
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


def _sum_debt(spreadsheet):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["debt"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["현재부채"] = pd.to_numeric(df["현재부채"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        return df["현재부채"].sum()
    except Exception:
        return 0


# ── 소유별 분류 헬퍼 ────────────────────────────────────────────────────────

def _byowner_domestic(spreadsheet, get_kr_price, gold_override):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["domestic"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
        df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
        df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")
        df = df.dropna(subset=["보유수량", "매수단가"])
        df["매입총액"] = df["보유수량"] * df["매수단가"]
        df["현재가"] = [get_kr_price(t, n, gold_override) for t, n in zip(df["종목코드"], df["종목명"])]
        df["평가총액"] = df["보유수량"] * df["현재가"]
        return (
            df.groupby("소유")["평가총액"].sum().to_dict(),
            df.groupby("소유")["매입총액"].sum().to_dict(),
        )
    except Exception:
        return {}, {}


def _byowner_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw):
    try:
        usdkrw = get_usdkrw()
        jpykrw = get_jpykrw()
        rate_map = {"USD": usdkrw, "JPY": jpykrw}
        sheet = spreadsheet.worksheet(SHEET_NAMES["overseas"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
        df["매수단가"] = pd.to_numeric(df["매수단가"].astype(str).str.replace(",", ""), errors="coerce")
        df["매입환율"] = pd.to_numeric(df["매입환율"].astype(str).str.replace(",", ""), errors="coerce")
        df["현재환율"] = df["화폐"].str.upper().str.strip().map(rate_map)
        df = df.dropna(subset=["보유수량", "매수단가"])
        df["매입총액(KRW)"] = df["보유수량"] * df["매수단가"] * df["매입환율"]
        df["현재가"] = df["종목티커"].apply(get_us_price)
        df["평가총액(KRW)"] = df["보유수량"] * df["현재가"] * df["현재환율"]
        return (
            df.groupby("소유")["평가총액(KRW)"].sum().to_dict(),
            df.groupby("소유")["매입총액(KRW)"].sum().to_dict(),
        )
    except Exception:
        return {}, {}


def _byowner_crypto(spreadsheet, get_usdkrw, get_crypto_prices):
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
            return val if r["통화"] == "KRW" else (val * usdkrw if usdkrw else float("nan"))

        def get_price(row):
            info = price_map.get(row["coingecko_id"], {})
            return info.get("krw") if row["통화"] == "KRW" else info.get("usd")

        df["매입총액"] = df["수량(qty)"] * df["평균매수가(avg_price)"]
        df["매입총액(KRW)"] = df.apply(lambda r: to_krw(r, "매입총액"), axis=1)
        df["현재가"] = df.apply(get_price, axis=1)
        df["평가총액"] = df["수량(qty)"] * df["현재가"]
        df["평가총액(KRW)"] = df.apply(lambda r: to_krw(r, "평가총액"), axis=1)
        return (
            df.groupby("소유")["평가총액(KRW)"].sum().to_dict(),
            df.groupby("소유")["매입총액(KRW)"].sum().to_dict(),
        )
    except Exception:
        return {}, {}


def _byowner_cash(spreadsheet, get_usdkrw):
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
        by = df.groupby("소유")["금액(KRW)"].sum().to_dict()
        return by, by  # 현금은 취득=현재
    except Exception:
        return {}, {}


def _byowner_property(spreadsheet):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["property"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["매입가"] = pd.to_numeric(df["매입가"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["현재 시세"] = pd.to_numeric(df["현재 시세"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        return (
            df.groupby("소유")["현재 시세"].sum().to_dict(),
            df.groupby("소유")["매입가"].sum().to_dict(),
        )
    except Exception:
        return {}, {}


def _byowner_etc(spreadsheet):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["etc"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["매입가"] = pd.to_numeric(df["매입가"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["현재 시세"] = pd.to_numeric(df["현재 시세"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        return (
            df.groupby("소유")["현재 시세"].sum().to_dict(),
            df.groupby("소유")["매입가"].sum().to_dict(),
        )
    except Exception:
        return {}, {}


def _byowner_debt(spreadsheet):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["debt"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["현재부채"] = pd.to_numeric(df["현재부채"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        return df.groupby("소유")["현재부채"].sum().to_dict()
    except Exception:
        return {}


def _build_owner_pivot(eval_dicts, buy_dicts, debt_by, labels):
    """
    eval_dicts / buy_dicts: list of {owner: value} per asset category (same order as labels)
    debt_by: {owner: debt_value}
    labels: column labels for each asset category
    Returns (df_eval, df_buy) pivot DataFrames with Sum row appended.
    """
    all_owners = sorted(set(
        o for d in eval_dicts + buy_dicts + [debt_by] for o in d
    ))

    def build(dicts, debt):
        rows = []
        for owner in all_owners:
            row = {"소유": owner}
            for label, d in zip(labels, dicts):
                row[label] = d.get(owner, 0)
            row["부채"] = debt.get(owner, 0)
            row["Total (순자산)"] = sum(d.get(owner, 0) for d in dicts) - debt.get(owner, 0)
            rows.append(row)
        df = pd.DataFrame(rows)
        sum_row = {c: df[c].sum() for c in df.columns if c != "소유"}
        sum_row["소유"] = "Sum"
        total_net = df["Total (순자산)"].sum()
        df["Rate (비율)"] = df["Total (순자산)"] / total_net * 100 if total_net else 0
        sum_row["Rate (비율)"] = 100.0
        df = pd.concat([df, pd.DataFrame([sum_row])], ignore_index=True)
        return df

    df_eval = build(eval_dicts, debt_by)
    df_buy  = build(buy_dicts,  debt_by)
    return df_eval, df_buy


def _fmt_pivot(df):
    fmt = df.copy()
    money_cols = [c for c in fmt.columns if c not in ("소유", "Rate (비율)")]
    for col in money_cols:
        fmt[col] = fmt[col].apply(fmt_num)
    fmt["Rate (비율)"] = fmt["Rate (비율)"].apply(fmt_pct)
    return fmt


# ── 성격별 헬퍼 ──────────────────────────────────────────────────────────────

def _nature_domestic(spreadsheet, get_kr_price, gold_override):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["domestic"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
        df["보유수량"] = pd.to_numeric(df["보유수량"].str.replace(",", ""), errors="coerce")
        df["매수단가"] = pd.to_numeric(df["매수단가"].str.replace(",", ""), errors="coerce")
        df = df.dropna(subset=["보유수량", "매수단가"])
        df["현재가"] = [get_kr_price(t, n, gold_override) for t, n in zip(df["종목코드"], df["종목명"])]
        df["금액"] = df["보유수량"] * df["현재가"]
        return df[["소유", "성격", "금액"]]
    except Exception:
        return pd.DataFrame(columns=["소유", "성격", "금액"])


def _nature_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw):
    try:
        rate_map = {"USD": get_usdkrw(), "JPY": get_jpykrw()}
        sheet = spreadsheet.worksheet(SHEET_NAMES["overseas"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["보유수량"] = pd.to_numeric(df["보유수량"].astype(str).str.replace(",", ""), errors="coerce")
        df["현재환율"] = df["화폐"].str.upper().str.strip().map(rate_map)
        df = df.dropna(subset=["보유수량"])
        df["현재가"] = df["종목티커"].apply(get_us_price)
        df["금액"] = df["보유수량"] * df["현재가"] * df["현재환율"]
        return df[["소유", "성격", "금액"]]
    except Exception:
        return pd.DataFrame(columns=["소유", "성격", "금액"])


def _nature_crypto(spreadsheet, get_usdkrw, get_crypto_prices):
    try:
        usdkrw = get_usdkrw()
        sheet = spreadsheet.worksheet(SHEET_NAMES["crypto"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["수량(qty)"] = pd.to_numeric(df["수량(qty)"].astype(str).str.replace(",", ""), errors="coerce")
        df["coingecko_id"] = df["coingecko_id"].astype(str).str.strip().str.lower()
        df["통화"] = df["통화"].astype(str).str.strip().str.upper().replace({"원": "KRW", "KR": "KRW", "달러": "USD", "US": "USD"})
        all_ids = df["coingecko_id"].dropna().unique().tolist()
        price_map = get_crypto_prices(tuple(all_ids)) or st.session_state.get("last_crypto_prices", {})

        def get_price(row):
            info = price_map.get(row["coingecko_id"], {})
            return info.get("krw") if row["통화"] == "KRW" else info.get("usd")

        df["현재가"] = df.apply(get_price, axis=1)
        df["평가총액"] = df["수량(qty)"] * df["현재가"]
        df["금액"] = df.apply(
            lambda r: r["평가총액"] if r["통화"] == "KRW" else (r["평가총액"] * usdkrw if usdkrw else float("nan")),
            axis=1,
        )
        df["성격"] = "가상자산"
        return df[["소유", "성격", "금액"]]
    except Exception:
        return pd.DataFrame(columns=["소유", "성격", "금액"])


def _nature_cash(spreadsheet, get_usdkrw):
    try:
        usdkrw = get_usdkrw()
        sheet = spreadsheet.worksheet(SHEET_NAMES["cash"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["금액_raw"] = pd.to_numeric(df["금액"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["통화"] = df["통화"].astype(str).str.strip().str.upper()
        df["금액"] = df.apply(
            lambda r: r["금액_raw"] if r["통화"] == "KRW" else (r["금액_raw"] * usdkrw if usdkrw else 0), axis=1
        )
        return df[["소유", "성격", "금액"]]
    except Exception:
        return pd.DataFrame(columns=["소유", "성격", "금액"])


def _nature_etc(spreadsheet):
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["etc"])
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())
        df["금액"] = pd.to_numeric(df["현재 시세"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        return df[["소유", "성격", "금액"]]
    except Exception:
        return pd.DataFrame(columns=["소유", "성격", "금액"])


def _build_nature_pivot(dfs_by_type, owner_filter=None):
    combined = []
    for asset_type, df in dfs_by_type.items():
        tmp = df.copy()
        tmp["자산유형"] = asset_type
        combined.append(tmp)
    if not combined:
        return pd.DataFrame()

    full = pd.concat(combined, ignore_index=True)
    full["성격"] = full["성격"].astype(str).str.strip()

    if owner_filter:
        full = full[full["소유"].astype(str).str.strip() == owner_filter]

    full = full[full["성격"].isin(NATURES)]

    pivot = full.pivot_table(
        index="성격", columns="자산유형", values="금액", aggfunc="sum", fill_value=0
    )
    for col in ASSET_COLS:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot[ASSET_COLS].reindex(NATURES, fill_value=0).reset_index()
    pivot.columns.name = None

    pivot["Total"] = pivot[ASSET_COLS].sum(axis=1)
    total = pivot["Total"].sum()
    pivot["Rate(비율)"] = pivot["Total"] / total * 100 if total else 0
    return pivot


def _fmt_nature_pivot(df):
    fmt = df.copy()
    for col in ASSET_COLS + ["Total"]:
        if col in fmt.columns:
            fmt[col] = fmt[col].apply(fmt_num)
    fmt["Rate(비율)"] = fmt["Rate(비율)"].apply(fmt_pct)
    return fmt


# ── 메인 렌더 ─────────────────────────────────────────────────────────────────

def render(spreadsheet, get_usdkrw, get_kr_price, get_us_price, get_crypto_prices, gold_override, get_jpykrw):
    st.subheader("📋 종합 자산 요약")

    with st.spinner("전체 자산 데이터 로딩 중..."):
        dom_buy,  dom_eval  = _sum_domestic(spreadsheet, get_kr_price, gold_override)
        ovs_buy,  ovs_eval  = _sum_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw)
        cry_buy,  cry_eval  = _sum_crypto(spreadsheet, get_usdkrw, get_crypto_prices)
        cash_buy, cash_eval = _sum_cash(spreadsheet, get_usdkrw)
        prop_buy, prop_eval = _sum_property(spreadsheet)
        etc_buy,  etc_eval  = _sum_etc(spreadsheet)
        debt_total          = _sum_debt(spreadsheet)

    # ── 종합 요약 테이블 ───────────────────────────────────
    summary_rows = [
        {"자산 종류": "국내 투자자산", "취득금액 (KRW)": dom_buy,  "현재금액 (KRW)": dom_eval},
        {"자산 종류": "해외 투자자산", "취득금액 (KRW)": ovs_buy,  "현재금액 (KRW)": ovs_eval},
        {"자산 종류": "가상자산",      "취득금액 (KRW)": cry_buy,  "현재금액 (KRW)": cry_eval},
        {"자산 종류": "현금성자산",    "취득금액 (KRW)": cash_buy, "현재금액 (KRW)": cash_eval},
        {"자산 종류": "부동산자산",    "취득금액 (KRW)": prop_buy, "현재금액 (KRW)": prop_eval},
        {"자산 종류": "기타자산",      "취득금액 (KRW)": etc_buy,  "현재금액 (KRW)": etc_eval},
    ]
    df_summary = pd.DataFrame(summary_rows)
    df_summary["평가손익 (KRW)"] = df_summary["현재금액 (KRW)"] - df_summary["취득금액 (KRW)"]
    df_summary["수익률 (%)"] = (
        df_summary["현재금액 (KRW)"] / df_summary["취득금액 (KRW)"].replace(0, float("nan")) - 1
    ) * 100

    total_assets  = df_summary["현재금액 (KRW)"].sum()
    total_buy     = df_summary["취득금액 (KRW)"].sum()
    net_assets    = total_assets - debt_total
    total_pl      = df_summary["평가손익 (KRW)"].sum()
    net_pl        = total_pl - debt_total
    total_yield   = (total_assets / total_buy - 1) * 100 if total_buy else 0

    npl_color = "#ef553b" if net_pl < 0 else "#00cc96"

    st.markdown(f"""
    <div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>
        <div>총 취득금액: {fmt_num(total_buy)} 원</div>
        <div>총 자산: {fmt_num(total_assets)} 원</div>
        <div>부채: {fmt_num(debt_total)} 원</div>
        <div>순자산: {fmt_num(net_assets)} 원</div>
        <div style='color:{npl_color};'>순 평가손익: {fmt_num(net_pl)} 원</div>
        <div>전체 수익률: {fmt_pct(total_yield)}</div>
    </div>
    """, unsafe_allow_html=True)

    debt_row = pd.DataFrame([{
        "자산 종류": "부채",
        "취득금액 (KRW)": debt_total,
        "현재금액 (KRW)": debt_total,
        "평가손익 (KRW)": 0,
        "수익률 (%)": float("nan"),
    }])
    display_df = pd.concat([df_summary, debt_row], ignore_index=True)
    fmt_df = display_df.copy()
    for col in ["취득금액 (KRW)", "현재금액 (KRW)", "평가손익 (KRW)"]:
        fmt_df[col] = fmt_df[col].apply(fmt_num)
    fmt_df["수익률 (%)"] = fmt_df["수익률 (%)"].apply(fmt_pct)
    st.dataframe(fmt_df, use_container_width=True)

    # ── 소유별 피벗 테이블 ────────────────────────────────
    st.markdown("---")

    with st.spinner("소유별 분류 계산 중..."):
        dom_eval_by,  dom_buy_by  = _byowner_domestic(spreadsheet, get_kr_price, gold_override)
        ovs_eval_by,  ovs_buy_by  = _byowner_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw)
        cry_eval_by,  cry_buy_by  = _byowner_crypto(spreadsheet, get_usdkrw, get_crypto_prices)
        cash_eval_by, cash_buy_by = _byowner_cash(spreadsheet, get_usdkrw)
        prop_eval_by, prop_buy_by = _byowner_property(spreadsheet)
        etc_eval_by,  etc_buy_by  = _byowner_etc(spreadsheet)
        debt_by                   = _byowner_debt(spreadsheet)

    asset_labels = ["국내 투자자산", "해외 투자자산", "가상자산", "현금성자산", "부동산자산", "기타자산"]
    eval_dicts = [dom_eval_by, ovs_eval_by, cry_eval_by, cash_eval_by, prop_eval_by, etc_eval_by]
    buy_dicts  = [dom_buy_by,  ovs_buy_by,  cry_buy_by,  cash_buy_by,  prop_buy_by,  etc_buy_by]

    df_eval_pivot, df_buy_pivot = _build_owner_pivot(eval_dicts, buy_dicts, debt_by, asset_labels)

    st.markdown("##### 1. 소유 기준 (현재금액(KRW))")
    st.dataframe(_fmt_pivot(df_eval_pivot), use_container_width=True)

    st.markdown("##### 2. 소유 기준 (취득금액(KRW))")
    st.dataframe(_fmt_pivot(df_buy_pivot), use_container_width=True)

    # ── 금융 자산 성격별 비중 ─────────────────────────────
    st.markdown("---")
    st.subheader("📊 금융 자산 성격별 비중")

    with st.spinner("성격별 데이터 로딩 중..."):
        dfs_by_type = {
            "국내 투자자산": _nature_domestic(spreadsheet, get_kr_price, gold_override),
            "해외 투자자산": _nature_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw),
            "가상자산":      _nature_crypto(spreadsheet, get_usdkrw, get_crypto_prices),
            "현금성 자산":   _nature_cash(spreadsheet, get_usdkrw),
            "기타자산":      _nature_etc(spreadsheet),
        }

    st.markdown("##### 전체")
    st.dataframe(_fmt_nature_pivot(_build_nature_pivot(dfs_by_type)), use_container_width=True)

    all_owners = sorted({
        str(r["소유"]).strip()
        for df in dfs_by_type.values()
        for _, r in df.iterrows()
        if pd.notna(r.get("소유")) and str(r.get("소유")).strip()
    })
    for i, owner in enumerate(all_owners, 1):
        st.markdown(f"##### {i}. 소유자: {owner}")
        st.dataframe(_fmt_nature_pivot(_build_nature_pivot(dfs_by_type, owner_filter=owner)), use_container_width=True)
