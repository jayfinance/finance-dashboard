import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct


def render(spreadsheet, get_usdkrw, get_kr_price, get_us_price, get_crypto_prices, gold_override):
    """종합 자산 요약 테이블
    모든 자산 종류(국내, 해외, 가상, 현금, 부동산, 기타)와 부채를 합산하여
    순자산(총자산 - 부채)을 계산하고 표시합니다.
    """
    st.subheader("📋 종합 자산 요약")
    st.info("🚧 구현 예정입니다.")
