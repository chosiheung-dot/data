# -*- coding: utf-8 -*-
"""
reliability_app.py - 가속시험 통합계산기 웹앱
원본 데스크톱(tkinter) 5개 탭 구조를 그대로 재현:
  ① 온도가속(Arrhenius) ② 온습도가속(Arrhenius-Peck) ③ 열피로가속(Coffin-Manson/Norris-Landzberg)
  ④ Weibull 시험시간비 계산기 + 참고DB ⑤ 수명데이터 분석(Weibull MLE, MTTF/B10/B1/R(t))
레이아웃: 좌측(입력) / 우측(결과, 연한 파란 배경 박스) 2단 구조
"""
import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import reliability_calc as C

RESULT_BOX_CSS = """
<style>
.rel-result-box {
    background-color: #eef2fb;
    color: #1a3fa0;
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 15px;
    line-height: 1.7;
    white-space: pre-wrap;
}
.rel-formula-box {
    background-color: #f5f5f5;
    color: #444;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-family: monospace;
    white-space: pre-wrap;
}
</style>
"""


def _result_box(text):
    st.markdown(RESULT_BOX_CSS + f'<div class="rel-result-box">{text}</div>', unsafe_allow_html=True)


def _formula_box(text):
    st.markdown(f'<div class="rel-formula-box">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- 탭① 온도가속
def tab_temp_accel():
    left, right = st.columns([2, 3])
    with left:
        st.subheader("① 온도가속 (Arrhenius)")
        with st.popover("ⓘ 왜 필요한가"):
            st.write("사용 조건보다 높은 온도로 가속시험을 진행할 때, 가속인자(AF)를 이용해 "
                     "필드에서 발생할 고장을 훨씬 짧은 시험시간 안에 재현할 수 있습니다.")
        with st.form("temp_accel_form"):
            Tu = st.number_input("사용온도 Tu (℃)", value=25.0, step=1.0)
            Ta = st.number_input("가속(시험)온도 Ta (℃)", value=85.0, step=1.0)
            E = st.number_input("활성화에너지 Ea (eV)", value=0.7, step=0.01, format="%.3f")
            t_field = st.number_input("필드 요구시간 t_field (h)", value=8760.0, step=1.0)
            submitted = st.form_submit_button("계산 실행 ▶", type="primary", use_container_width=True)

        with st.popover("활성화에너지 DB 검색 (190개 항목)"):
            q = st.text_input("검색어(재료/부품명)", key="ea_q")
            df_ea = pd.DataFrame(C.EA_DB, columns=["부품/재료", "Ea(eV)", "출처", "비고"])
            if q:
                df_ea = df_ea[df_ea["부품/재료"].str.contains(q, case=False, na=False)]
            st.dataframe(df_ea, use_container_width=True, height=250)

    with right:
        st.subheader("결과")
        if submitted:
            af = C.arrhenius_af(Tu, Ta, E)
            t_test = C.equiv_time_single(t_field, af)
            _result_box(f"가속인자 AF = {af:,.4f}\n"
                        f"등가 시험시간 t_test = t_field / AF = {t_field:,.1f}h / {af:,.4f} = {t_test:,.2f}h "
                        f"({t_test/24:,.2f}일)")
            _formula_box("AF = exp[ (Ea/k) × (1/Tu − 1/Ta) ],  k = 8.6173e-05 eV/K\n"
                         "t_test = t_field / AF")
        else:
            st.info("좌측에서 값을 입력하고 [계산 실행 ▶]을 눌러주세요.")


# ---------------------------------------------------------------- 탭② 온습도가속
def tab_humid_accel():
    left, right = st.columns([2, 3])
    with left:
        st.subheader("② 온습도가속 (Arrhenius-Peck)")
        with st.form("humid_accel_form"):
            Tu = st.number_input("사용온도 Tu (℃)", value=25.0, step=1.0, key="h_Tu")
            Hu = st.number_input("사용습도 Hu (%RH)", value=60.0, step=1.0, key="h_Hu")
            Ta = st.number_input("가속온도 Ta (℃)", value=85.0, step=1.0, key="h_Ta")
            Ha = st.number_input("가속습도 Ha (%RH)", value=85.0, step=1.0, key="h_Ha")
            E = st.number_input("활성화에너지 Ea (eV)", value=0.7, step=0.01, format="%.3f", key="h_E")
            n = st.number_input("습도 지수 n", value=2.66, step=0.01, format="%.3f", key="h_n")
            t_field = st.number_input("필드 요구시간 t_field (h)", value=8760.0, step=1.0, key="h_t")
            submitted = st.form_submit_button("계산 실행 ▶", type="primary", use_container_width=True)

        with st.popover("활성화에너지 / 습도지수 DB 검색"):
            q = st.text_input("검색어", key="ea_q2")
            df_ea = pd.DataFrame(C.EA_DB, columns=["부품/재료", "Ea(eV)", "출처", "비고"])
            if q:
                df_ea = df_ea[df_ea["부품/재료"].str.contains(q, case=False, na=False)]
            st.dataframe(df_ea, use_container_width=True, height=250)

    with right:
        st.subheader("결과")
        if submitted:
            af = C.peck_af(Tu, Hu, Ta, Ha, E, n)
            t_test = C.equiv_time_single(t_field, af)
            _result_box(f"가속인자 AF = {af:,.4f}\n"
                        f"등가 시험시간 t_test = {t_field:,.1f}h / {af:,.4f} = {t_test:,.2f}h "
                        f"({t_test/24:,.2f}일)")
            _formula_box("AF = exp[ (Ea/k)×(1/Tu−1/Ta) ] × (Hu/Ha)^(−n)")
        else:
            st.info("좌측에서 값을 입력하고 [계산 실행 ▶]을 눌러주세요.")


# ---------------------------------------------------------------- 탭③ 열피로가속
def tab_thermal_cycle():
    left, right = st.columns([2, 3])
    with left:
        st.subheader("③ 열피로가속 (Coffin-Manson / Modified Norris-Landzberg)")
        with st.popover("ⓘ 모델 선택 가이드"):
            st.text(C.MODEL_GUIDE_TEXT)
        model = st.radio("모델 선택", ["Coffin-Manson(단순)", "Modified Norris-Landzberg(정밀)"],
                          key="tc_model")

        with st.popover("m지수(Coffin-Manson) 참고 가이드"):
            df_m = pd.DataFrame(C.M_GUIDE_DB, columns=["파손 메커니즘", "m지수", "적용 대상"])
            st.dataframe(df_m, use_container_width=True)

        with st.form("thermal_form"):
            dT_field = st.number_input("필드 ΔT (℃)", value=40.0, step=1.0)
            dT_test = st.number_input("시험 ΔT (℃)", value=100.0, step=1.0)
            N_field = st.number_input("필드 요구 사이클수", value=10000.0, step=100.0)
            if model == "Coffin-Manson(단순)":
                m = st.number_input("m 지수", value=2.65, step=0.01, format="%.3f")
                submitted = st.form_submit_button("계산 실행 ▶", type="primary", use_container_width=True)
            else:
                dwell_field = st.number_input("필드 고온유지시간(min)", value=30.0, step=1.0)
                dwell_test = st.number_input("시험 고온유지시간(min)", value=15.0, step=1.0)
                ramp_test = st.number_input("시험 승온속도(℃/min)", value=10.0, step=0.5)
                Tmax_field = st.number_input("필드 최고온도(℃)", value=85.0, step=1.0)
                Tmax_test = st.number_input("시험 최고온도(℃)", value=125.0, step=1.0)
                submitted = st.form_submit_button("계산 실행 ▶", type="primary", use_container_width=True)

    with right:
        st.subheader("결과")
        if submitted:
            if model == "Coffin-Manson(단순)":
                af = C.coffin_manson_af(dT_field, dT_test, m)
                formula = "AF = (ΔT_test / ΔT_field) ^ m"
            else:
                af = C.norris_landzberg_af(dT_field, dT_test, dwell_field, dwell_test,
                                            ramp_test, Tmax_field, Tmax_test)
                formula = ("AF = (ΔTtest/ΔTfield)^2.65 × (dwell_test/dwell_field)^0.136 "
                           "× 1.22×ramp_test^(−0.0757) × exp[2185×(1/Tmax_field_K − 1/Tmax_test_K)]")
            N_test = C.equiv_time_single(N_field, af)
            _result_box(f"가속인자 AF = {af:,.4f}\n"
                        f"등가 시험 사이클수 N_test = N_field / AF = {N_field:,.0f} / {af:,.4f} "
                        f"= {N_test:,.1f} 사이클")
            _formula_box(formula)
        else:
            st.info("좌측에서 값을 입력하고 [계산 실행 ▶]을 눌러주세요.")


# ---------------------------------------------------------------- 탭④ Weibull 시험시간비
def tab_weibull_ratio():
    left, right = st.columns([2, 3])
    with left:
        st.subheader("④ Weibull 시험시간비 계산기")
        with st.form("weibull_ratio_form"):
            Rt = st.number_input("목표신뢰도 R", value=0.99, step=0.001, format="%.4f")
            CL = st.number_input("신뢰수준 CL", value=0.5, step=0.01, format="%.3f")
            n_sample = st.number_input("샘플수 n", value=6, step=1)
            beta_default = st.session_state.get("beta_from_tab5", 2.0)
            beta = st.number_input("형상모수 β", value=float(beta_default), step=0.01, format="%.3f",
                                    key="w_beta")
            submitted = st.form_submit_button("계산 실행 ▶", type="primary", use_container_width=True)

        with st.popover("Beta 참고DB 열기 (69개 항목)"):
            q = st.text_input("검색어(부품명/카테고리)", key="wdb_q")
            df_w = pd.DataFrame(C.WEIBULL_DB, columns=["분류", "부품", "β_low", "β_typ", "β_high",
                                                        "η_low(h)", "η_typ(h)", "η_high(h)"])
            if q:
                df_w = df_w[df_w["부품"].str.contains(q, case=False, na=False) |
                            df_w["분류"].str.contains(q, case=False, na=False)]
            st.dataframe(df_w, use_container_width=True, height=280)
            pick = st.selectbox("β_typ 값 적용할 행 선택", ["-"] + list(df_w["부품"]), key="wdb_pick")
            if st.button("선택값 β_typ 적용", key="wdb_apply"):
                row = df_w[df_w["부품"] == pick]
                if not row.empty:
                    st.session_state["beta_from_tab5"] = float(row.iloc[0]["β_typ"])
                    st.rerun()

    with right:
        st.subheader("결과")
        if submitted:
            ratio = C.weibull_test_time_ratio(Rt, CL, n_sample, beta)
            _result_box(f"시험시간비 = {ratio:,.4f}\n"
                        f"→ 목표 사용시간(수명) 대비 시험시간을 이 비율만큼만 시험하면 됩니다.\n"
                        f"예) 목표수명이 1,000h이면 시험시간 ≈ {1000*ratio:,.1f}h")
            _formula_box("시험시간비 = [ (−ln CL) / (n × −ln R) ] ^ (1/β)")
        else:
            st.info("좌측에서 값을 입력하고 [계산 실행 ▶]을 눌러주세요. "
                    "(⑤ 수명데이터 분석에서 추정한 β값을 여기로 보낼 수도 있습니다)")


# ---------------------------------------------------------------- 탭⑤ 수명데이터 분석
def tab_life_data():
    left, right = st.columns([2, 3])
    with left:
        st.subheader("⑤ 수명데이터 분석 (Weibull MLE)")
        with st.popover("ⓘ MTTF / B10 / B1 / R(t) 란?"):
            st.write("MTTF: 평균수명. B10: 전체의 10%가 고장나는 시점(설계수명 기준으로 흔히 사용). "
                     "B1: 1%가 고장나는 시점(안전/보증 설계에 사용). R(t): 특정 시점 t에서의 생존율(신뢰도).")

        st.caption("데이터를 표로 직접 입력하세요. '고장'이 아니면 미고장(중도절단) 데이터로 처리됩니다.")
        default_df = pd.DataFrame({"시간(h)": [120.0, 340.0, 560.0, 900.0, 1200.0, 1500.0],
                                    "고장여부": [True, True, True, True, True, False]})
        data_df = st.data_editor(st.session_state.get("life_data_df", default_df),
                                  num_rows="dynamic", key="life_data_editor",
                                  column_config={"고장여부": st.column_config.CheckboxColumn()})
        st.session_state["life_data_df"] = data_df

        c1, c2 = st.columns(2)
        R_t_query = c1.number_input("R(t) 계산 시점(h)", value=1000.0, step=10.0)
        run = c2.button("계산 실행 ▶", type="primary", use_container_width=True)

    with right:
        st.subheader("결과")
        if run:
            times = data_df["시간(h)"].astype(float).tolist()
            is_failure = data_df["고장여부"].astype(bool).tolist()
            fit = C.fit_weibull_mle(times, is_failure)
            if fit is None:
                st.warning("고장 데이터가 2개 이상 필요합니다.")
            else:
                beta, eta = fit
                mttf = C.weibull_mttf(beta, eta)
                b10 = C.weibull_bpercentile(beta, eta, 10)
                b1 = C.weibull_bpercentile(beta, eta, 1)
                r_t = C.weibull_reliability(R_t_query, beta, eta)
                _result_box(f"형상모수 β = {beta:,.4f}\n"
                            f"척도모수 η = {eta:,.2f} h\n"
                            f"MTTF(평균수명) = {mttf:,.2f} h\n"
                            f"B10 수명 = {b10:,.2f} h\n"
                            f"B1 수명 = {b1:,.2f} h\n"
                            f"R({R_t_query:,.0f}h) = {r_t*100:,.2f} %")
                _formula_box("MTTF = η·Γ(1+1/β)\n"
                             "B(p) = η·(−ln(1−p))^(1/β)\n"
                             "R(t) = exp[−(t/η)^β]")

                st.session_state["beta_from_tab5"] = beta
                if st.button("이 β값을 ④(Weibull 시험시간비)로 보내기"):
                    st.session_state["beta_from_tab5"] = beta
                    st.success(f"β={beta:.4f} 를 ④탭으로 전달했습니다. ④탭에서 확인하세요.")

                # 확률도표(Weibull Plot)
                ranks = C.weibull_rank_adjustment(times, is_failure)
                if ranks:
                    xs = [math.log(t) for t, _ in ranks]
                    ys = [math.log(-math.log(1 - p)) for _, p in ranks]
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name="관측데이터(Rank Adj.)"))
                    if len(xs) >= 2:
                        import numpy as np
                        a, b = np.polyfit(xs, ys, 1)
                        xs_line = np.linspace(min(xs), max(xs), 50)
                        fig.add_trace(go.Scatter(x=xs_line, y=a*xs_line+b, mode="lines", name="MLE 적합선"))
                    fig.update_layout(title="Weibull 확률도표 (ln t vs ln[-ln(1-F)])",
                                       xaxis_title="ln(시간)", yaxis_title="ln(-ln(1-F))", height=420)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("좌측에서 데이터를 입력하고 [계산 실행 ▶]을 눌러주세요.")


def render():
    st.title("🧪 가속시험 통합계산기 (신뢰성분석)")
    st.caption("원본 데스크톱 프로그램의 5개 탭을 그대로 재현했습니다.")
    tabs = st.tabs(["① 온도가속", "② 온습도가속", "③ 열피로가속", "④ Weibull 시험시간비", "⑤ 수명데이터 분석"])
    with tabs[0]:
        tab_temp_accel()
    with tabs[1]:
        tab_humid_accel()
    with tabs[2]:
        tab_thermal_cycle()
    with tabs[3]:
        tab_weibull_ratio()
    with tabs[4]:
        tab_life_data()
