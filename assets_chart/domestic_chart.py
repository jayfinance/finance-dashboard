import streamlit as st
import pandas as pd


def render(spreadsheet, get_kr_price, gold_override):
    """국내 투자자산 차트 대시보드
    assets_table/domestic.py 데이터를 기반으로 차트를 렌더링합니다.
    예: 종목별 비중 파이차트, 수익률 바차트, 섹터별 분포
    """
    st.subheader("📊 국내 투자자산 차트")
    st.info("🚧 구현 예정입니다.")
