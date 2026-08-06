# -*- coding: utf-8 -*-
"""
app.py (통합 진입점)
사이드바에서 ①신뢰성분석 / ②추세분석기(Raw Data 분석) 중 선택해서 사용합니다.
"""
import streamlit as st

st.set_page_config(page_title="신뢰성분석 & 추세분석기", layout="wide")

st.markdown("""
<style>
.result-box{
    background-color:#eef2fb; color:#1a3fa0; padding:14px 16px; border-radius:6px;
    font-weight:700; font-size:15px; white-space:pre-wrap; line-height:1.7;
    border:1px solid #d7e0f5;
}
.formula-box{
    background-color:#f5f5f5; padding:12px 14px; border-radius:6px;
    white-space:pre-wrap; font-size:13px; line-height:1.6; color:#333;
    border:1px solid #e2e2e2;
}
.detail-box{
    font-size:13px; color:#333; white-space:pre-wrap; line-height:1.6; padding:4px 2px;
}
.note-red{color:#a33; font-size:13px;}
.note-gray{color:#666; font-size:12px;}
div.stButton > button[kind="primary"]{
    background-color:#2f6fed; color:white; font-weight:700;
}
div.stButton > button[kind="primary"]:hover{
    background-color:#255bc4; color:white;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🧰 분석 도구 선택")
mode = st.sidebar.radio("도구", ["① 신뢰성분석 (가속시험 계산기)", "② 추세분석기 (Raw Data 분석)"],
                         key="app_mode")
st.sidebar.divider()
st.sidebar.caption(
    "① 신뢰성분석: Arrhenius/Peck/Weibull 등 가속시험 계산기 5개 탭\n\n"
    "② 추세분석기: raw data(CSV) 업로드 -> 전체추세/정밀분석/두시간대비교/신뢰성분석(TTF·RUL)\n\n"
    "※ 추세분석기의 '폴더 감시' 탭은 웹 환경 특성상 '새 파일 다시 업로드해서 비교'하는 방식으로 대체되었습니다."
)

if mode.startswith("①"):
    import reliability_app
    reliability_app.render()
else:
    import trend_app
    trend_app.render()
