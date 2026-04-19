import streamlit as st


def _nav_button(label: str, target_section: str, target_page: str):
    key = f"nav__{target_section}__{target_page}"
    if st.button(label, key=key):
        st.session_state["main_section"] = target_section
        if target_section == "Chart":
            st.session_state["chart_assets"] = target_page
            st.session_state["chart_active_section"] = "assets"
        else:
            st.session_state["table_assets"] = target_page
            st.session_state["table_active_section"] = "assets"
        st.rerun()


def to_chart_button(chart_page: str):
    _nav_button("📊 차트 보러가기", "Chart", chart_page)


def to_table_button(table_page: str):
    _nav_button("📋 테이블 보러가기", "Table", table_page)
