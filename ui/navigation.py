import streamlit as st


def _nav_button(label: str, target_section: str, target_page: str):
    key = f"nav__{target_section}__{target_page}"
    if st.button(label, key=key):
        # 위젯 렌더링 전 시점에 처리하기 위해 pending 키로 저장
        st.session_state["_pending_nav_section"] = target_section
        st.session_state["_pending_nav_page"] = target_page
        st.rerun()


def to_chart_button(chart_page: str):
    _nav_button("📊 차트 보러가기", "Chart", chart_page)


def to_table_button(table_page: str):
    _nav_button("📋 테이블 보러가기", "Table", table_page)
