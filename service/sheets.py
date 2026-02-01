import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

@st.cache_resource(show_spinner="📡 Google Sheets 연결 중...")
def get_spreadsheet():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scope
        )
        client = gspread.authorize(creds)

        # 🔹 시트 이름을 secrets에서 읽도록 변경 (운영/테스트 분리 가능)
        sheet_name = st.secrets.get("SPREADSHEET_NAME", "FinanceRaw")

        return client.open(sheet_name)

    except Exception as e:
        st.error("❌ Google Sheets 연결 실패")
        st.exception(e)
        st.stop()
