import datetime
import streamlit as st
import pandas as pd
import gspread
from ui.formatters import fmt_num, fmt_pct
from config import SHEET_NAMES
from assets_table.total import (
    _byowner_domestic, _byowner_overseas, _byowner_crypto,
    _byowner_cash, _byowner_property, _byowner_etc, _byowner_debt,
)

# Short names matching 자산추이 sheet column headers
_ASSET_SHORTS = ["국내자산", "해외자산", "가상자산", "현금성자산", "부동산", "기타"]


def _compute_snapshot(spreadsheet, get_usdkrw, get_kr_price, get_us_price,
                      get_crypto_prices, gold_override, get_jpykrw):
    """
    Call all _byowner_* helpers and build a flat dict matching the
    자산추이 sheet column layout.
    Returns (snapshot_dict, [owners_list])
    """
    eval_dom, buy_dom = _byowner_domestic(spreadsheet, get_kr_price, gold_override)
    eval_ov,  buy_ov  = _byowner_overseas(spreadsheet, get_usdkrw, get_us_price, get_jpykrw)
    eval_cry, buy_cry = _byowner_crypto(spreadsheet, get_usdkrw, get_crypto_prices)
    eval_csh, buy_csh = _byowner_cash(spreadsheet, get_usdkrw)
    eval_prp, buy_prp = _byowner_property(spreadsheet)
    eval_etc, buy_etc = _byowner_etc(spreadsheet)
    debt_by           = _byowner_debt(spreadsheet)

    eval_lists = [eval_dom, eval_ov, eval_cry, eval_csh, eval_prp, eval_etc]
    buy_lists  = [buy_dom,  buy_ov,  buy_cry,  buy_csh,  buy_prp,  buy_etc]

    all_owners = sorted(set(
        o for d in eval_lists + buy_lists + [debt_by] for o in d
    ))

    row = {"기준일": datetime.date.today().strftime("%Y-%m-%d")}

    total_eval_net = 0
    total_buy_net  = 0

    for owner in all_owners:
        eval_vals = [d.get(owner, 0) for d in eval_lists]
        buy_vals  = [d.get(owner, 0) for d in buy_lists]
        debt_val  = debt_by.get(owner, 0)

        for short, ev, bv in zip(_ASSET_SHORTS, eval_vals, buy_vals):
            row[f"매입-{short}({owner})"] = round(bv)
            row[f"평가-{short}({owner})"] = round(ev)

        # 부채: 매입·평가 동일 값
        row[f"매입-부채({owner})"] = round(debt_val)
        row[f"평가-부채({owner})"] = round(debt_val)

        owner_buy_net  = sum(buy_vals)  - debt_val
        owner_eval_net = sum(eval_vals) - debt_val
        row[f"매입-순자산({owner})"] = round(owner_buy_net)
        row[f"평가-순자산({owner})"] = round(owner_eval_net)

        total_buy_net  += owner_buy_net
        total_eval_net += owner_eval_net

    row["매입 총 순자산"] = round(total_buy_net)
    row["평가 총 순자산"] = round(total_eval_net)

    # 총 현금성 자산 비중 = 전체 현금성자산 평가합 / 전체 순자산 평가합 × 100
    total_eval_cash = sum(eval_csh.get(o, 0) for o in all_owners)
    cash_ratio = (total_eval_cash / total_eval_net * 100) if total_eval_net else 0
    row["총 현금성 자산 비중"] = round(cash_ratio, 2)

    return row, all_owners


def render(spreadsheet, get_usdkrw, get_kr_price, get_us_price,
           get_crypto_prices, gold_override, get_jpykrw):

    st.subheader("📋 종합 자산 추이")

    # ── 시트 로드 ──────────────────────────────────────────
    try:
        sheet = spreadsheet.worksheet(SHEET_NAMES["trend"])
        rows = sheet.get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        st.info("'자산추이' 시트가 아직 없습니다. Google Sheets에 해당 시트를 추가하면 이 화면에 표시됩니다.")
        return
    except gspread.exceptions.APIError as e:
        st.error("Google Sheets API 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
        if st.button("🔄 새로고침", key="trend_api_retry"):
            st.rerun()
        return

    # ── 현재 스냅샷 계산 ───────────────────────────────────
    with st.spinner("현재 자산 스냅샷 계산 중..."):
        snapshot, owners = _compute_snapshot(
            spreadsheet, get_usdkrw, get_kr_price, get_us_price,
            get_crypto_prices, gold_override, get_jpykrw,
        )

    st.markdown("#### 현재 스냅샷")

    def _fmt_snap_val(k, v):
        if k == "기준일":
            return v
        if k == "총 현금성 자산 비중":
            return f"{v:.2f}%"
        return f"{v:,.0f}"

    snap_rows = [{"항목": k, "값": _fmt_snap_val(k, v)} for k, v in snapshot.items()]
    st.dataframe(pd.DataFrame(snap_rows), use_container_width=True, hide_index=True)

    # ── 입력 버튼 ──────────────────────────────────────────
    st.markdown("---")
    if st.button("📥 현재 데이터 입력", type="primary"):
        if not rows:
            # 시트가 비어있으면 헤더 + 첫 행 추가
            sheet.append_row(list(snapshot.keys()))
            sheet.append_row(list(snapshot.values()))
        else:
            headers = rows[0]
            new_row = [snapshot.get(h, "") for h in headers]
            sheet.append_row(new_row)
        st.success(f"✅ {snapshot['기준일']} 데이터가 입력되었습니다.")
        st.rerun()

    # ── 이력 테이블 ───────────────────────────────────────
    if not rows or len(rows) < 2:
        st.info("저장된 이력 데이터가 없습니다.")
        return

    st.markdown("---")
    st.markdown("#### 이력 데이터")

    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=lambda x: x.strip())

    numeric_cols = [c for c in df.columns if c != "기준일"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    display_df = df.copy()
    for col in numeric_cols:
        if "비중" in col:
            display_df[col] = display_df[col].apply(
                lambda v: f"{v:.2f}%" if pd.notna(v) else "-"
            )
        else:
            display_df[col] = display_df[col].apply(
                lambda v: fmt_num(v) if pd.notna(v) else "-"
            )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── 행 삭제 ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 행 삭제")

    row_labels = df["기준일"].tolist() if "기준일" in df.columns else [str(i + 1) for i in range(len(df))]
    selected_label = st.selectbox("삭제할 행 선택 (기준일)", row_labels, index=len(row_labels) - 1, key="trend_delete_select")

    # 2단계 확인
    if "trend_delete_step" not in st.session_state:
        st.session_state["trend_delete_step"] = 0
        st.session_state["trend_delete_target"] = None

    if st.button("🗑️ 선택 행 삭제", key="trend_delete_btn1"):
        st.session_state["trend_delete_step"] = 1
        st.session_state["trend_delete_target"] = selected_label

    if st.session_state.get("trend_delete_step") == 1:
        target = st.session_state["trend_delete_target"]
        st.warning(f"⚠️ '{target}' 행을 삭제하려고 합니다. 계속하시겠습니까?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("예, 삭제합니다", key="trend_delete_confirm1"):
                st.session_state["trend_delete_step"] = 2
        with c2:
            if st.button("취소", key="trend_delete_cancel1"):
                st.session_state["trend_delete_step"] = 0
                st.session_state["trend_delete_target"] = None
                st.rerun()

    if st.session_state.get("trend_delete_step") == 2:
        target = st.session_state["trend_delete_target"]
        st.error(f"🚨 정말 '{target}' 행을 영구 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("최종 확인, 삭제합니다", key="trend_delete_confirm2"):
                # 시트 행 인덱스 탐색 (1-indexed, 헤더 행 +1)
                target_row_idx = None
                for i, label in enumerate(row_labels):
                    if label == target:
                        target_row_idx = i + 2  # +1 헤더, +1 1-인덱스
                        break
                if target_row_idx is not None:
                    sheet.delete_rows(target_row_idx)
                    st.success(f"✅ '{target}' 행이 삭제되었습니다.")
                st.session_state["trend_delete_step"] = 0
                st.session_state["trend_delete_target"] = None
                st.rerun()
        with c2:
            if st.button("취소", key="trend_delete_cancel2"):
                st.session_state["trend_delete_step"] = 0
                st.session_state["trend_delete_target"] = None
                st.rerun()
