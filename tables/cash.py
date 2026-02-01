import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct


def render(spreadsheet, get_usdkrw):
    st.subheader("📋 현금성자산 평가 테이블")
    st.info("현금성자산 기능은 추후 구현 예정입니다.")