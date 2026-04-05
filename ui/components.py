import streamlit as st


def exchange_rate_header(title: str, usdkrw):
    """제목(좌) + 환율(우) 헤더"""
    left, right = st.columns([4, 1])
    with left:
        st.subheader(title)
    with right:
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
