import streamlit as st
import pandas as pd
from ui.formatters import fmt_num
from config import SHEET_NAMES


def render(spreadsheet, get_usdkrw):
    """부동산자산 테이블
    Google Sheets '부동산자산' 시트 기준.
    예상 컬럼: 구분, 소유, 물건명, 소재지, 취득가(KRW), 현재가(KRW), 담보대출(KRW)
    """
    st.subheader("📋 부동산자산 테이블")
    st.info("🚧 구현 예정입니다.")
