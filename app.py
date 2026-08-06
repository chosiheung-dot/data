# -*- coding: utf-8 -*-
"""
통합 웹앱 : 신뢐성분석 + 추세 분석기 (Trend Analyzer)
- 좌측 사이드바에서 사이트(신뢰성분석 / 추세분석기)를 전환합니다.
"""
import io
import math
import os
import glob as globmod
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go

import reliability_calc as R
import trend_calc as T

st.set_page_config(page_title="신뢐성분석 & 추세분석기", layout="wide")

# ------------------------------------------------------------------
# 사이드바 : 사이트 선택
# ------------------------------------------------------------------
st.sidebar.title("🧭 사이트 선택")
site = st.sidebar.radio("이동", ["🔧 신뢐성 분석", "📈 추세 분석기"], label_visibility="collapsed")

# ====================================================================
# 🔧 신뢐성 분석
# ====================================================================
if site == "🔧 신뢐성 분석":
    st.title("🔧 신뢐성 분석 (가속시험 통합계산기)")
    tabs = st.tabs(["① 온도가속(Arrhenius)", "② 온습도가속(Peck)", "③ 열피로가속",
                    "④ Weibull 시험시간비", "⑤ 수명데이터 분석"])

    # ---------------- ① 온도가속 ----------------
    with tabs[0]:
        st.subheader("① 온도가속 (Arrhenius)")
        c1, c2 = st.columns([1, 1])
        with c1:
            field_h = st.number_input("필드 목표시간(h)", value=87600.0, step=100.0, key="t1_field")
            ea = st.number_input("활성화에너지 Ea(eV)", value=0.5, step=0.01, format="%.3f", key="t1_ea")
            t_use = st.number_input("사용(필드) 온도(℃)", value=60.0, step=1.0, key="t1_use")
            t_test = st.number_input("시험 온도(℃)", value=105.0, step=1.0, key="t1_test")
            use_weibull = st.checkbox("Weibull 시험시간비 적용", key="t1_wb")
            if use_weibull:
                wc1, wc2, wc3, wc4 = st.columns(4)
                R_target = wc1.number_input("목표신뢐도 R", value=0.99, step=0.01, format="%.3f", key="t1_R")
                CL = wc2.number_input("신뢐수준 CL", value=0.5, step=0.05, format="%.3f", key="t1_CL")
                n_sample = wc3.number_input("샘플수 n", value=6, step=1, key="t1_n")
                beta = wc4.number_input("형상모수 β", value=2.0, step=0.1, key="t1_beta")

            with st.expander("Ea 참고 DB 검색"):
                q = st.text_input("부품명 검색", key="t1_q")
                rows = [r for r in R.EA_DB if q.lower() in r[0].lower()] if q else R.EA_DB
                st.dataframe(pd.DataFrame(rows, columns=["부품", "Ea(eV)", "출처", "비고"]), height=250)

        with c2:
            if st.button("계산 실행", key="t1_run"):
                af, test_h = R.arrhenius_test_time(field_h, ea, t_use, t_test)
                ratio = None
                if use_weibull:
                    ratio = R.weibull_test_ratio(R_target, CL, int(n_sample), beta)
                    test_h_final = test_h * ratio
                else:
                    test_h_final = test_h
                st.metric("가속계수 AF", f"{af:,.4f}")
                st.metric("등가시험시간(h)", f"{test_h:,.2f}")
                if use_weibull:
                    st.metric("Weibull 시험시간비", f"{ratio:,.4f}")
                    st.metric("최종 시험시간(h) [보정 반영]", f"{test_h_final:,.2f}")
                else:
                    st.info("체크박스를 켜지 않으면 위 등가시험시간에는 R/CL 통계적 보장이 포함되어 있지 않습니다. "
                            "목표 R/CL이 있다면 Weibull 시험시간비 적용을 켜주세요.")

    # ---------------- ② 온습도가속 ----------------
    with tabs[1]:
        st.subheader("② 온습도가속 (Arrhenius-Peck)")
        c1, c2 = st.columns([1, 1])
        with c1:
            field_h2 = st.number_input("필드 목표시간(h)", value=87600.0, step=100.0, key="t2_field")
            ea2 = st.number_input("활성화에너지 Ea(eV)", value=0.5, step=0.01, format="%.3f", key="t2_ea")
            n_exp = st.number_input("습도지수 n", value=2.7, step=0.1, key="t2_n")
            t_use2 = st.number_input("사용(필드) 온도(℃)", value=60.0, step=1.0, key="t2_use_t")
            t_test2 = st.number_input("시험 온도(℃)", value=85.0, step=1.0, key="t2_test_t")
            rh_use = st.number_input("사용(필드) 습도(%RH)", value=60.0, step=1.0, key="t2_use_h")
            rh_test = st.number_input("시험 습도(%RH)", value=85.0, step=1.0, key="t2_test_h")
            use_weibull2 = st.checkbox("Weibull 시험시간비 적용", key="t2_wb")
            if use_weibull2:
                wc1, wc2, wc3, wc4 = st.columns(4)
                R2_target = wc1.number_input("목표신뢐도 R", value=0.99, step=0.01, format="%.3f", key="t2_R")
                CL2 = wc2.number_input("신뢐수준 CL", value=0.5, step=0.05, format="%.3f", key="t2_CL")
                n2_sample = wc3.number_input("샘플수 n", value=6, step=1, key="t2_n_sample")
                beta2 = wc4.number_input("형상모수 β", value=2.0, step=0.1, key="t2_beta")
        with c2:
            if st.button("계산 실행", key="t2_run"):
                af_total, af_t, af_rh = R.peck_af(ea2, t_use2, t_test2, rh_use, rh_test, n_exp)
                test_h2 = field_h2 / af_total
                st.metric("온도항 AF", f"{af_t:,.4f}")
                st.metric("습도항 AF", f"{af_rh:,.4f}")
                st.metric("전체 가속계수 AF", f"{af_total:,.4f}")
                st.metric("등가시험시간(h)", f"{test_h2:,.2f}")
                if use_weibull2:
                    ratio2 = R.weibull_test_ratio(R2_target, CL2, int(n2_sample), beta2)
                    st.metric("Weibull 시험시간비", f"{ratio2:,.4f}")
                    st.metric("최종 시험시간(h)", f"{test_h2*ratio2:,.2f}")

    # ---------------- ③ 열피로가속 ----------------
    with tabs[2]:
        st.subheader("③ 열피로가속 (Coffin-Manson / Norris-Landzberg)")
        model_kind = st.radio("모델 선택", ["Coffin-Manson", "Modified Norris-Landzberg"], horizontal=True, key="t3_model")
        c1, c2 = st.columns([1, 1])
        with c1:
            field_cycles = st.number_input("필드 목표 사이클수", value=10000.0, step=100.0, key="t3_field_c")
            dt_field = st.number_input("필드 ΔT(℃)", value=40.0, step=1.0, key="t3_dtf")
            dt_test = st.number_input("시험 ΔT(℃)", value=100.0, step=1.0, key="t3_dtt")
            with st.expander("m지수 가이드 DB"):
                st.dataframe(pd.DataFrame(R.M_GUIDE_DB, columns=["고장모드", "m지수", "적용대상"]), height=200)
            m_exp = st.number_input("피로지수 m", value=2.65, step=0.05, key="t3_m")
            if model_kind == "Modified Norris-Landzberg":
                f_field = st.number_input("필드 사이클 주파수(cycle/day 등)", value=0.1, step=0.01, key="t3_ff")
                f_test = st.number_input("시험 사이클 주파수", value=4.0, step=0.1, key="t3_ft")
                t_field_max = st.number_input("필드 최대온도(℃)", value=80.0, step=1.0, key="t3_tfm")
                t_test_max = st.number_input("시험 최대온도(℃)", value=125.0, step=1.0, key="t3_ttm")
                ea3 = st.number_input("활성화에너지 Ea(eV)", value=0.12, step=0.01, format="%.3f", key="t3_ea")
        with c2:
            if st.button("계산 실행", key="t3_run"):
                if model_kind == "Coffin-Manson":
                    af3 = R.coffin_manson_af(dt_field, dt_test, m_exp)
                else:
                    af3 = R.norris_landzberg_af(dt_field, dt_test, f_field, f_test, t_field_max, t_test_max, m_exp, ea3)
                req_cycles = R.thermal_cycling_required_cycles(field_cycles, af3)
                st.metric("가속계수 AF", f"{af3:,.4f}")
                st.metric("필요 시험 사이클수", f"{req_cycles:,.2f}")
                if model_kind == "Coffin-Manson":
                    st.caption("※ Coffin-Manson: ΔT 변화만 반영하는 단순 모델입니다.")
                else:
                    st.caption("※ Modified Norris-Landzberg: ΔT + 사이클 주파수 + 최대온도(Ea)까지 반영하는 확장 모델입니다.")

    # ---------------- ④ Weibull 시험시간비 ----------------
    with tabs[3]:
        st.subheader("④ Weibull 시험시간비 계산기")
        c1, c2 = st.columns([1, 1])
        with c1:
            R4 = st.number_input("목표신뢐도 R", value=st.session_state.get("beta_from_tab5_R", 0.99), step=0.01, format="%.3f", key="t4_R")
            CL4 = st.number_input("신뢐수준 CL", value=0.5, step=0.05, format="%.3f", key="t4_CL")
            n4 = st.number_input("샘플수 n", value=6, step=1, key="t4_n")
            beta4_default = st.session_state.get("beta_from_tab5", 2.0)
            beta4 = st.number_input("형상모수 β", value=float(beta4_default), step=0.1, format="%.4f", key="t4_beta")
            if "beta_from_tab5" in st.session_state:
                st.success(f"⑤탭에서 전달된 β={st.session_state['beta_from_tab5']:.4f} 가 기본값으로 반영되어 있습니다.")
            with st.expander("β 참고 DB(고장모드별)"):
                st.dataframe(pd.DataFrame(R.WEIBULL_DB, columns=["분류", "부품/고장모드", "β_min", "β_typ", "β_max",
                                                                    "η_min", "η_typ", "η_max"]), height=250)
        with c2:
            if st.button("계산 실행", key="t4_run"):
                ratio4 = R.weibull_test_ratio(R4, CL4, int(n4), beta4)
                st.metric("시험시간비(ratio)", f"{ratio4:,.4f}")
                st.caption("등가시험시간 × 이 비율 = 목표 R/CL을 통계적으로 담보하는 최종 시험시간")

    # ---------------- ⑤ 수명데이터 분석 ----------------
    with tabs[4]:
        st.subheader("⑤ 수명데이터 분석 (Weibull MLE)")
        st.caption("실제 고장/미고장(=시험·관찰 종료 시점까지 고장나지 않음) 데이터를 입력해 β·η을 추정합니다.")

        if "life_data" not in st.session_state:
            st.session_state["life_data"] = pd.DataFrame({
                "시간(h 또는 cycle)": [120.0, 340.0, 560.0, 800.0, 950.0, 1000.0, 1000.0, 1000.0],
                "상태": ["고장", "고장", "고장", "고장", "고장", "미고장", "미고장", "미고장"],
            })

        st.markdown("**데이터 입력** (표를 직접 편집하거나 행을 추가/삭제하세요)")
        edited = st.data_editor(
            st.session_state["life_data"], num_rows="dynamic", key="life_editor",
            column_config={
                "상태": st.column_config.SelectboxColumn("상태", options=["고장", "미고장"]),
            },
        )
        st.session_state["life_data"] = edited
        st.caption("※ 미고장 = 관찰(시험) 종료 시점까지 고장이 발생하지 않은 데이터")

        colA, colB = st.columns([1, 2])
        run5 = colA.button("Weibull 적합 실행", key="t5_run")

        if run5 or "life_result" in st.session_state:
            df = st.session_state["life_data"].dropna()
            times = df["시간(h 또는 cycle)"].astype(float).tolist()
            is_failure = (df["상태"] == "고장").tolist()

            if run5:
                if len(times) < 2 or sum(is_failure) < 2:
                    st.warning("최소 2개 이상의 '고장' 데이터가 필요합니다.")
                else:
                    beta_hat, eta_hat, _ = R.weibull_mle(times, is_failure)
                    st.session_state["life_result"] = (beta_hat, eta_hat, times, is_failure)

            if "life_result" in st.session_state:
                beta_hat, eta_hat, times, is_failure = st.session_state["life_result"]

                m1, m2, m3 = st.columns(3)
                m1.metric("형상모수 β", f"{beta_hat:.4f}")
                m2.metric("척도모수 η", f"{eta_hat:,.2f}")
                if beta_hat < 1:
                    m3.info("β<1 : 초기고장(감소형) 경향")
                elif beta_hat < 1.5:
                    m3.info("β≈1 : 우발고장(일정) 경향")
                else:
                    m3.info("β>1 : 마모성고장(증가형) 경향")

                mttf = R.mttf_weibull(beta_hat, eta_hat)
                b10 = R.b_life(beta_hat, eta_hat, 0.10)
                b1 = R.b_life(beta_hat, eta_hat, 0.01)

                c1, c2, c3 = st.columns(3)
                c1.metric("MTTF(평균수명)", f"{mttf:,.2f}")
                c2.metric("B10 수명", f"{b10:,.2f}")
                c3.metric("B1 수명", f"{b1:,.2f}")

                with st.expander("ℹ️ MTTF / B10 / B1 이 왜 필요한가요?"):
                    st.markdown(
                        "- **β, η만으로는 실무적으로 감이 오지 않기 때문에**, 대표 수명값으로 변환해서 보는 지표입니다.\n"
                        "- **MTTF(평균수명)**: 평균적으로 몇 시간/사이클에서 고장나는지 (전체 경향 파악용)\n"
                        "- **B10 수명**: 10%가 고장나는 시점. **자동차/부품 업계에서 가장 널리 쓰는 판정기준**입니다.\n"
                        "  (예: \"B10 수명이 목표 필드수명보다 짧다\" → 설계 변경 필요)\n"
                        "- **B1 수명**: 1%가 고장나는 시점. 초기불량률에 더 민감한 기준이 필요할 때 사용합니다."
                    )

                st.markdown("**임의 시점 신뢐도 계산**")
                t_input = st.number_input("확인할 시점 t (h 또는 cycle)", value=float(round(mttf/2, 1)), key="t5_t")
                Rt = R.reliability_at(beta_hat, eta_hat, t_input)
                Ft = R.cdf_at(beta_hat, eta_hat, t_input)
                ht = R.hazard_at(beta_hat, eta_hat, t_input)
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric(f"R({t_input:g}) 신뢐도", f"{Rt*100:,.2f}%")
                rc2.metric(f"F({t_input:g}) 누적고장률", f"{Ft*100:,.2f}%")
                rc3.metric(f"h({t_input:g}) 고장률", f"{ht:.6f}")

                with st.expander("ℹ️ 임의 시점 신뢐도 계산은 왜 하는 건가요?"):
                    st.markdown(
                        "- 이 계산은 **관찰(시험)한 기간과 무관하게, 알고 싶은 임의의 시점(t)에서의 신뢐도를 역산**하는 기능입니다.\n"
                        "- 예: 시험은 1000시간까지 진행했더라도, t=200을 입력하면 **'200시간을 버틸 확률'**을 계산해줍니다.\n"
                        "- t=필드 목표수명(예: 10년=87,600h)을 넣으면 **'이 모델대로면 필드수명 시점 생존율이 얼마인지'** 사전 예측에 활용합니다.\n"
                        "- ⚠️ **주의**: t가 관찰된 데이터 범위를 훨씬 벗어나면(외삽), 예측 오차가 커질 수 있습니다. "
                        "가능하면 관찰범위 안의 값을 우선 확인하세요."
                    )

                # Weibull 확률도표
                rows = R.johnson_rank_adjustment(times, is_failure)
                if len(rows) >= 2:
                    fig, ax = plt.subplots(figsize=(6, 4.5))
                    xs = [math.log(r[0]) for r in rows]
                    ys = [math.log(-math.log(1 - r[2])) for r in rows]
                    ax.scatter(xs, ys, label="데이터(고장)")
                    xs_line = np.linspace(min(xs) - 0.5, max(xs) + 0.5, 50)
                    ys_line = beta_hat * (xs_line - math.log(eta_hat))
                    ax.plot(xs_line, ys_line, color="red", label="MLE 적합선")
                    ax.set_xlabel("ln(t)")
                    ax.set_ylabel("ln(-ln(1-F))")
                    ax.set_title("Weibull Probability Plot")
                    ax.legend()
                    ax.grid(alpha=0.3)
                    st.pyplot(fig)
                else:
                    st.info("확률도표를 그리려면 고장 데이터가 2개 이상 필요합니다.")

                if st.button("이 β값을 ④ Weibull 탭으로 보내기", key="t5_send"):
                    st.session_state["beta_from_tab5"] = beta_hat
                    st.success(f"β={beta_hat:.4f} 가 ④탭 기본값으로 반영되었습니다. 상단 ④ 탭에서 확인하세요.")

                # 엑셀 내보내기
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    st.session_state["life_data"].to_excel(writer, sheet_name="입력데이터", index=False)
                    pd.DataFrame({
                        "항목": ["β", "η", "MTTF", "B10", "B1"],
                        "값": [beta_hat, eta_hat, mttf, b10, b1],
                    }).to_excel(writer, sheet_name="결과", index=False)
                st.download_button("엑셀로 내보내기", data=buf.getvalue(),
                                    file_name="수명데이터분석_결과.xlsx", key="t5_dl")

# ====================================================================
# 📈 추세 분석기
# ====================================================================
else:
    st.title("📈 추세 분석기 (Trend Analyzer)")
    tabs = st.tabs(["전체추세", "정밀분석", "두 시간대 비교", "신뢐성분석(TTF·RUL)"])

    st.sidebar.markdown("---")
    st.sidebar.subheader("데이터 불러오기")
    mode = st.sidebar.radio("방식", ["폴더 경로 입력(로컬 실행 시)", "파일 업로드"], key="tr_mode")

    files_info = []  # (파일명, text)
    if mode == "폴더 경로 입력(로컬 실행 시)":
        folder = st.sidebar.text_input("CSV 폴더 경로", key="tr_folder")
        if folder and os.path.isdir(folder):
            paths = sorted(globmod.glob(os.path.join(folder, "*.csv")))
            for p in paths:
                try:
                    files_info.append((os.path.basename(p), T.decode_raw(p)))
                except Exception:
                    pass
    else:
        uploaded = st.sidebar.file_uploader("CSV 파일 업로드(여러개 가능)", type=["csv"], accept_multiple_files=True, key="tr_upload")
        if uploaded:
            for uf in uploaded:
                raw = uf.read()
                files_info.append((uf.name, T._decode_raw_bytes(raw)))

    if not files_info:
        st.info("좌측에서 폴더 경로를 입력하거나 CSV 파일을 업로드하세요.")
        st.stop()

    # 파일명 내 타임스탬프로 정렬(가능하면), 아니면 이름 정렬
    def sort_key(item):
        name, _ = item
        ts = T.parse_timestamp(name)
        return (0, ts) if ts else (1, name)

    files_info.sort(key=sort_key)
    st.sidebar.success(f"{len(files_info)}개 파일 로드됨")

    # 헤더(항목) 추출
    items_all = T.get_header_items(files_info[0][1])
    focus_items = st.sidebar.multiselect("분석할 항목 선택", items_all, default=items_all[: min(6, len(items_all))])

    if st.sidebar.button("전체 스캔 실행", key="tr_scan"):
        recs = []
        nrows_list = []
        for name, text in files_info:
            rec, cols, nrows = T.summarize_file(text, focus_items)
            rec["파일명"] = name
            recs.append(rec)
            nrows_list.append(nrows)
        df_summary = pd.DataFrame(recs)
        hours = T.cumulative_hours(nrows_list)
        df_summary["누적작동시간(h)"] = hours
        st.session_state["tr_summary"] = df_summary
        st.session_state["tr_files_info"] = files_info
        st.session_state["tr_focus_items"] = focus_items
        st.success("스캔 완료")

    if "tr_summary" not in st.session_state:
        st.info("좌측 '전체 스캔 실행' 버튼을 눌러주세요.")
        st.stop()

    df_summary = st.session_state["tr_summary"]

    # ---------------- 전체추세 ----------------
    with tabs[0]:
        st.subheader("전체 추세")
        item_sel = st.selectbox("항목 선택", st.session_state["tr_focus_items"], key="tr_t1_item")
        stat_sel = st.selectbox("통계량", ["평균", "최대", "최소", "표준편차"], key="tr_t1_stat")
        col = f"{item_sel}_{stat_sel}"
        if col in df_summary.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_summary["누적작동시간(h)"], y=df_summary[col], mode="lines+markers", name=col))
            fig.update_layout(xaxis_title="누적작동시간(h)", yaxis_title=col, height=500)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_summary[["파일명", "누적작동시간(h)", col]])
        else:
            st.warning("해당 항목/통계 조합의 데이터가 없습니다.")

    # ---------------- 정밀분석 ----------------
    with tabs[1]:
        st.subheader("정밀분석 (개별 파일 원본 파형)")
        fname_sel = st.selectbox("파일 선택", [n for n, _ in st.session_state["tr_files_info"]], key="tr_t2_file")
        noise_mode = st.selectbox("노이즈 필터", ["없음", "이동중앙값", "이동평균", "3시그마제거"], key="tr_t2_noise")
        items_sel2 = st.multiselect("겹쳐볼 항목(다중선택 가능)", st.session_state["tr_focus_items"],
                                     default=st.session_state["tr_focus_items"][:1], key="tr_t2_items")
        text2 = dict(st.session_state["tr_files_info"])[fname_sel]
        df2 = T.load_csv_text(text2, usecols=items_sel2)
        fig2 = go.Figure()
        for it in items_sel2:
            if it in df2.columns:
                y = df2[it].to_numpy()
                if noise_mode != "없음":
                    y = T.apply_noise_filter(y, noise_mode)
                x = np.arange(len(y)) * T.DT
                fig2.add_trace(go.Scatter(x=x, y=y, mode="lines", name=it))
        fig2.update_layout(xaxis_title="시간(초)", height=550)
        st.plotly_chart(fig2, use_container_width=True)

    # ---------------- 두 시간대 비교 ----------------
    with tabs[2]:
        st.subheader("두 시간대 비교")
        names_all = [n for n, _ in st.session_state["tr_files_info"]]
        cA, cB = st.columns(2)
        f1 = cA.selectbox("비교 파일 1(초기)", names_all, index=0, key="tr_t3_f1")
        f2 = cB.selectbox("비교 파일 2(후기)", names_all, index=len(names_all)-1, key="tr_t3_f2")
        item3 = st.selectbox("비교 항목", st.session_state["tr_focus_items"], key="tr_t3_item")
        d = dict(st.session_state["tr_files_info"])
        df_f1 = T.load_csv_text(d[f1], usecols=[item3])
        df_f2 = T.load_csv_text(d[f2], usecols=[item3])
        fig3 = go.Figure()
        if item3 in df_f1.columns:
            fig3.add_trace(go.Scatter(x=np.arange(len(df_f1))*T.DT, y=df_f1[item3], mode="lines", name=f"{f1}(초기)"))
        if item3 in df_f2.columns:
            fig3.add_trace(go.Scatter(x=np.arange(len(df_f2))*T.DT, y=df_f2[item3], mode="lines", name=f"{f2}(후기)"))
        fig3.update_layout(xaxis_title="시간(초)", height=550)
        st.plotly_chart(fig3, use_container_width=True)

    # ---------------- 신뢐성분석(TTF·RUL) ----------------
    with tabs[3]:
        st.subheader("신뢐성분석 - TTF(고장시점) / RUL(잔존수명) 예측")
        item4 = st.selectbox("판정 항목", st.session_state["tr_focus_items"], key="tr_t4_item")
        c1, c2 = st.columns(2)
        use_lsl = c1.checkbox("LSL(하한) 설정", key="tr_t4_uselsl")
        lsl = c1.number_input("LSL 값", value=0.0, key="tr_t4_lsl") if use_lsl else None
        use_usl = c2.checkbox("USL(상한) 설정", key="tr_t4_useusl")
        usl = c2.number_input("USL 값", value=100.0, key="tr_t4_usl") if use_usl else None

        col_max = f"{item4}_최대"
        col_min = f"{item4}_최소"
        if col_max in df_summary.columns and col_min in df_summary.columns:
            hours = df_summary["누적작동시간(h)"].to_numpy()
            ymax = df_summary[col_max].to_numpy()
            ymin = df_summary[col_min].to_numpy()

            ttf = T.detect_ttf(hours, ymax, ymin, lsl, usl)
            if ttf:
                st.error(f"⚠ 스펙 이탈 감지: {ttf['h']:.2f}h 시점, 값={ttf['value']:.3f}, 판정={ttf['kind']} "
                         f"(이후 지속비율 {ttf['persist']*100:.1f}%)")
            else:
                st.success("스펙 이탈이 감지되지 않았습니다.")

            col_mean = f"{item4}_평균"
            if col_mean in df_summary.columns:
                model = T.best_model(hours, df_summary[col_mean].to_numpy())
                if model:
                    st.info(f"추세모델: {model['kind']} (R²={model['r2']:.4f})")
                    cross_u = T.predict_cross(model, hours[-1], usl) if usl is not None else None
                    cross_l = T.predict_cross(model, hours[-1], lsl) if lsl is not None else None
                    if cross_u:
                        st.metric("USL 도달 예상시점(h) [RUL 참고]", f"{cross_u:,.2f}")
                    if cross_l:
                        st.metric("LSL 도달 예상시점(h) [RUL 참고]", f"{cross_l:,.2f}")
                    if not cross_u and not cross_l:
                        st.caption("현재 추세로는 관찰기간의 5배 이내에 스펙 이탈이 예상되지 않습니다.")
        else:
            st.warning("해당 항목의 통계 데이터가 없습니다.")
