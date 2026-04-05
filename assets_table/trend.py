import streamlit as st
import pandas as pd
from ui.formatters import fmt_num, fmt_pct


def render(spreadsheet):
    """종합 자산 추이 테이블
    월별/분기별 자산 변화 추이를 표시합니다.
    Google Sheets '자산추이' 시트 기준.
    예상 컬럼: 기준일, 국내자산, 해외자산, 가상자산, 현금성자산, 부동산, 기타, 부채, 순자산
    """
    st.subheader("📋 종합 자산 추이")
    st.info("🚧 구현 예정입니다.")
