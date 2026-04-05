import streamlit as st


def render_table_filters(df, cat_cols, key_prefix):
    """
    Excel 스타일 컬럼 필터.
    cat_cols: 필터를 적용할 문자형 컬럼 목록
    반환값: 필터 적용된 DataFrame
    """
    with st.expander("🔍 필터", expanded=False):
        n = len(cat_cols)
        cols = st.columns(min(n, 4))
        filtered = df.copy()
        for i, col in enumerate(cat_cols):
            if col not in df.columns:
                continue
            unique_vals = sorted(df[col].dropna().astype(str).unique().tolist())
            selected = cols[i % len(cols)].multiselect(
                col, unique_vals, default=unique_vals, key=f"{key_prefix}_{col}"
            )
            if selected:
                filtered = filtered[filtered[col].astype(str).isin(selected)]
    return filtered.reset_index(drop=True)
