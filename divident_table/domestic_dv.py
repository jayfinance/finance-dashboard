import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct


def render(spreadsheet):
    """국내 배당 테이블
    Google Sheets '국내배당' 시트 기준.
    예상 컬럼: 증권사, 소유, 종목명, 종목코드, 배당금(원), 배당일, 배당수익률(%)
    """
    st.subheader("📋 국내 배당 테이블")
    st.info("🚧 구현 예정입니다.")
