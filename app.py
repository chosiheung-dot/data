# -*- coding: utf-8 -*-
"""
app.py - 통합 웹앱 진입점
사이드바에서 '신뢰성분석' / '추세분석기(Raw Data 분석)' 중 하나를 선택합니다.
"""
import streamlit as st

st.set_page_config(page_title="신뢰성분석 & 추세분석기", layout="wide")

st.sidebar.title("🔧 메뉴")
page = st.sidebar.radio("프로그램 선택", ["① 신뢰성분석 (가속시험 통합계산기)", "② 추세분석기 (Raw Data 분석)"])
st.sidebar.markdown("---")

if page.startswith("①"):
    import reliability_app
    reliability_app.render()
else:
    import trend_app
    trend_app.render()
