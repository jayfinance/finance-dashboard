import streamlit as st
import pandas as pd


def render(spreadsheet, get_usdkrw, get_kr_price, get_us_price, get_crypto_prices, gold_override):
    """종합 자산 차트 대시보드
    assets_table/total.py 데이터를 기반으로 차트를 렌더링합니다.
    예: 자산 종류별 비중 파이차트, 총자산 vs 부채 vs 순자산 바차트
    """
    st.subheader("📊 종합 자산 차트")
    st.info("🚧 구현 예정입니다.")
