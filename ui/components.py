import streamlit as st


def exchange_rate_header(title: str, usdkrw, nav_label: str = None, nav_section: str = None, nav_page: str = None):
    """제목(좌) + 선택적 네비게이션 버튼(중) + 환율(우) 헤더"""
    if nav_label and nav_page:
        col_t, col_n, col_r = st.columns([4, 1, 1])
    else:
        col_t, col_r = st.columns([4, 1])
        col_n = None

    with col_t:
        st.subheader(title)

    if col_n is not None:
        with col_n:
            from ui.navigation import _nav_button
            _nav_button(nav_label, nav_section, nav_page)

    with col_r:
        if usdkrw is not None:
            st.markdown(
                f"<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: {usdkrw:,.2f} KRW/USD</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div style='text-align:right;font-size:0.9em;color:gray;'>현재 환율: -</div>",
                unsafe_allow_html=True
            )


def summary_bar(items: list):
    """상단 합계 박스 — items: [(label, formatted_value), ...]"""
    parts = "".join(f"<div>{label}: {value}</div>" for label, value in items)
    st.markdown(
        f"<div style='display:flex;gap:40px;font-size:1.1em;font-weight:bold;'>{parts}</div>",
        unsafe_allow_html=True
    )
