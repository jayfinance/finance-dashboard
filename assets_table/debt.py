import streamlit as st
import pandas as pd
from ui.formatters import fmt_num
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw):
    """부채 테이블
    Google Sheets '부채' 시트 기준.
    예상 컬럼: 금융기관, 소유, 대출종류, 통화, 잔액, 금리(%), 만기일
    """
    st.subheader("📋 부채 테이블")
    st.info("🚧 구현 예정입니다.")
