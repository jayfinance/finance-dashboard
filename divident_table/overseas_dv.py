import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_num2, fmt_pct


def render(spreadsheet, get_usdkrw):
    """해외 배당 테이블
    Google Sheets '해외배당' 시트 기준.
    예상 컬럼: 증권사, 소유, 종목티커, 배당금(USD), 배당일, 배당수익률(%), 배당금(KRW)
    """
    st.subheader("📋 해외 배당 테이블")
    st.info("🚧 구현 예정입니다.")
