
# -*- coding: utf-8 -*-
"""
가속시험 통합계산기 (신뢰성분석) - Streamlit 웹앱
① 온도가속 ② 온습도가속 ③ 열피로가속 ④ Weibull 시험시간비 ⑤ 수명데이터 분석
"""
import math
import io
import numpy as np
import pandas as pd
import streamlit as st

import reliability_calc as rc

st.set_page_config(page_title="가속시험 통합계산기 (신뢰성분석)", page_icon="🚀", layout="wide")

# ---------------------------------------------------------------------------
# 공통 스타일
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .result-box {
        background-color:#eef2fb;
        color:#1a3fa0;
        padding:18px 20px;
        border-radius:10px;
        font-size:16px;
        line-height:1.7;
        border:1px solid #c9d6f2;
    }
    .result-box b { color:#0d2570; }
    div[data-testid="stDialog"] div[role="dialog"] { max-height: 85vh; overflow-y:auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚀 가속시험 통합계산기 (신뢰성분석)")

# ---------------------------------------------------------------------------
# 공용: DB 검색 모달 (큰 모달로 통일)
# ---------------------------------------------------------------------------
@st.dialog("활성화에너지 DB 검색 (Ea)", width="large")
def dlg_ea_db(target_key: str):
    st.caption(f"전체 {len(rc.EA_DB)}개 항목 · 부품/재료명으로 검색해서 활성화에너지(Ea) 값을 적용하세요.")
    kw = st.text_input("검색어 (재료/부품명)", key=f"{target_key}_ea_kw")
    df = pd.DataFrame(rc.EA_DB, columns=["부품/재료", "Ea_min (eV)", "Ea_max (eV)"])
    if kw:
        df = df[df["부품/재료"].str.contains(kw, case=False, na=False)]
    df = df.reset_index(drop=True)
    st.dataframe(df, use_container_width=True, height=520)

    st.divider()
    if len(df) > 0:
        options = df["부품/재료"].tolist()
        sel = st.selectbox("적용할 항목 선택", options, key=f"{target_key}_ea_sel")
        row = df[df["부품/재료"] == sel].iloc[0]
        mid = round((row["Ea_min (eV)"] + row["Ea_max (eV)"]) / 2, 3)
        st.write(f"선택 항목: **{sel}**  ·  권장 Ea 범위: {row['Ea_min (eV)']} ~ {row['Ea_max (eV)']} eV  ·  중간값: **{mid} eV**")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("이 값(중간값) 적용", use_container_width=True, type="primary", key=f"{target_key}_ea_apply"):
                st.session_state[f"{target_key}_ea"] = float(mid)
                st.rerun()
        with c2:
            if st.button("닫기", use_container_width=True, key=f"{target_key}_ea_close"):
                st.rerun()
    else:
        st.info("검색 결과가 없습니다.")


@st.dialog("Weibull β·η 참고 DB", width="large")
def dlg_weibull_db(target_key: str):
    st.caption(f"전체 {len(rc.WEIBULL_REF_DB)}개 항목 · 파손모드/부품 유형별 대표 형상모수(β) 참고값입니다.")
    kw = st.text_input("검색어 (부품/파손모드)", key=f"{target_key}_wb_kw")
    df = pd.DataFrame(rc.WEIBULL_REF_DB, columns=["부품/파손모드", "β (typical)", "비고"])
    if kw:
        df = df[df["부품/파손모드"].str.contains(kw, case=False, na=False)]
    df = df.reset_index(drop=True)
    st.dataframe(df, use_container_width=True, height=460)

    st.divider()
    if len(df) > 0:
        options = ["-"] + df["부품/파손모드"].tolist()
        sel = st.selectbox("적용할 항목 선택", options, key=f"{target_key}_wb_sel")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("이 β값 적용", use_container_width=True, type="primary", key=f"{target_key}_wb_apply"):
                if sel != "-":
                    beta_val = float(df[df["부품/파손모드"] == sel]["β (typical)"].iloc[0])
                    st.session_state[f"{target_key}_beta"] = beta_val
                    st.rerun()
        with c2:
            if st.button("닫기", use_container_width=True, key=f"{target_key}_wb_close"):
                st.rerun()
    else:
        st.info("검색 결과가 없습니다.")


@st.dialog("열피로 가속모델 선택 가이드", width="large")
def dlg_model_guide():
    st.markdown(
        """
### Coffin-Manson 모델
가장 기본적인 열피로 가속모델로, 온도변화폭(ΔT)만으로 가속계수를 계산합니다.

**AF = (ΔT_test / ΔT_use)^m**

- 사이클 주파수, 최고온도 영향을 별도로 고려하지 않는 단순 모델
- m(피로지수)은 파손모드/재질에 따라 통상 1.9~6.0 범위

---
### Norris-Landzberg 모델
Coffin-Manson에 **사이클 주파수**와 **최고온도(Ea 기반 Arrhenius 항)**를 추가로 반영한 확장 모델로,
솔더 조인트 등 온도사이클 시험에서 더 정밀한 가속계수 산출에 사용됩니다.

**AF = (ΔT_test/ΔT_use)^m × (f_use/f_test)^(1/3) × exp[ Ea/k × (1/Tmax_use − 1/Tmax_test) ]**

---
### 어떤 모델을 선택해야 하나?
| 상황 | 권장 모델 |
|---|---|
| 단순 온도사이클, 주파수/최고온도 영향 무시 가능 | Coffin-Manson |
| 솔더 조인트 열피로, 사이클 주파수·최고온도 영향 큼 | Norris-Landzberg |
| JEDEC JESD22-A104 등 표준 절차 준수 필요 | Norris-Landzberg |
        """
    )
    if st.button("닫기", use_container_width=True):
        st.rerun()


@st.dialog("m지수(피로지수) 참고 가이드", width="large")
def dlg_m_guide(target_key: str):
    st.caption("파손모드/구조에 따른 대표적인 m지수(피로지수) 참고범위입니다.")
    df = pd.DataFrame(rc.M_EXPONENT_GUIDE, columns=["구조/파손모드", "m_min", "m_max", "비고"])
    st.dataframe(df, use_container_width=True, height=260)
    st.divider()
    options = df["구조/파손모드"].tolist()
    sel = st.selectbox("적용할 항목 선택", options, key=f"{target_key}_m_sel")
    row = df[df["구조/파손모드"] == sel].iloc[0]
    mid = round((row["m_min"] + row["m_max"]) / 2, 2)
    st.write(f"선택 항목: **{sel}**  ·  권장 범위: {row['m_min']} ~ {row['m_max']}  ·  중간값: **{mid}**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("이 값(중간값) 적용", use_container_width=True, type="primary", key=f"{target_key}_m_apply"):
            st.session_state[f"{target_key}_m"] = float(mid)
            st.rerun()
    with c2:
        if st.button("닫기", use_container_width=True, key=f"{target_key}_m_close"):
            st.rerun()


@st.dialog("왜 필요한가?", width="large")
def dlg_why(text: str):
    st.markdown(text)
    if st.button("닫기", use_container_width=True):
        st.rerun()


@st.dialog("MTTF · B10 · B1 · R(t) 설명", width="large")
def dlg_life_metrics_guide():
    st.markdown(
        """
### 용어 설명

- **MTTF (Mean Time To Failure)**: 평균수명. Weibull 분포에서 `η × Γ(1 + 1/β)`로 계산됩니다.
- **B10 Life**: 누적고장률 10%에 도달하는 시점(수명). 즉 100개 중 10개가 고장 나는 시간.
- **B1 Life**: 누적고장률 1%에 도달하는 시점. 초기 신뢰성 보증 기준으로 자주 사용됩니다.
- **R(t)**: 특정 시점 t에서의 신뢰도(생존확률). `R(t) = exp[-(t/η)^β]`
- **β (형상모수, shape parameter)**:
    - β < 1: 초기고장기 (DFR, 감소고장률)
    - β = 1: 우발고장기 (지수분포와 동일, 일정고장률)
    - β > 1: 마모고장기 (IFR, 증가고장률)
- **η (척도모수, scale parameter)**: 누적고장률 63.2%에 도달하는 시점 (특성수명)
        """
    )
    if st.button("닫기", use_container_width=True):
        st.rerun()


def result_box(html: str):
    st.markdown(f'<div class="result-box">{html}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 탭 구성
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["① 온도가속", "② 온습도가속", "③ 열피로가속", "④ Weibull 시험시간비", "⑤ 수명데이터 분석"]
)

# =========================== ① 온도가속 (Arrhenius) ==========================
with tab1:
    st.subheader("① 온도가속 (Arrhenius)")

    if st.button("ℹ️ 왜 필요한가", key="t1_why_btn"):
        dlg_why(
            "온도가속시험은 제품의 실사용 온도보다 높은 온도에서 시험해 "
            "짧은 시간 안에 열화/고장을 유도하고, 그 결과를 Arrhenius 모델로 환산하여 "
            "실사용 조건에서의 수명을 추정하기 위해 사용합니다.\n\n"
            "가속계수(AF)가 클수록 시험시간을 단축할 수 있지만, 과도한 고온은 "
            "실제로 일어나지 않는 새로운 고장모드를 유발할 수 있으므로 "
            "활성화에너지(Ea)와 온도 조건 선정에 주의가 필요합니다."
        )

    c_left, c_right = st.columns([1, 3])
    with c_left:
        st.markdown("**사용온도 Tu (°C)**")
        t_use = st.number_input("사용온도 Tu (°C)", value=25.0, step=1.0, key="t1_tu", label_visibility="collapsed")

        st.markdown("**시험온도 Tt (°C)**")
        t_test = st.number_input("시험온도 Tt (°C)", value=85.0, step=1.0, key="t1_tt", label_visibility="collapsed")

        st.markdown("**활성화에너지 Ea (eV)**")
        ea = st.number_input(
            "활성화에너지 Ea (eV)", value=st.session_state.get("t1_ea", 0.5),
            step=0.05, format="%.3f", key="t1_ea", label_visibility="collapsed"
        )
        if st.button(f"🔎 활성화에너지 DB 검색 ({len(rc.EA_DB)}개 항목)", key="t1_ea_db_btn", use_container_width=True):
            dlg_ea_db("t1")

        st.markdown("**실사용 목표시간 (h)**")
        field_h = st.number_input("실사용 목표시간 (h)", value=8760.0, step=100.0, key="t1_field_h", label_visibility="collapsed")

        run1 = st.button("▶ 계산 실행", type="primary", use_container_width=True, key="t1_run")

    with c_right:
        st.markdown("### 결과")
        if run1:
            af = rc.arrhenius_af(ea, t_use, t_test)
            test_h = rc.arrhenius_test_time(field_h, ea, t_use, t_test)
            result_box(
                f"가속계수 <b>AF = {af:,.3f}</b> 배<br>"
                f"실사용 목표시간 <b>{field_h:,.0f} h</b> 를 만족하기 위한 시험시간은<br>"
                f"<b>{test_h:,.2f} 시간</b> (약 {test_h/24:,.2f}일) 입니다."
            )
            df_out = pd.DataFrame({
                "항목": ["사용온도(°C)", "시험온도(°C)", "Ea(eV)", "가속계수 AF", "실사용목표시간(h)", "환산 시험시간(h)"],
                "값": [t_use, t_test, ea, af, field_h, test_h],
            })
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_out.to_excel(writer, sheet_name="온도가속_결과", index=False)
            st.download_button("📥 엑셀로 내보내기", data=buf.getvalue(),
                                file_name="온도가속_결과.xlsx", key="t1_dl")
        else:
            result_box("좌측에서 값을 입력하고 [계산 실행 ▶]을 눌러주세요.")

# =========================== ② 온습도가속 (Peck) ==========================
with tab2:
    st.subheader("② 온습도가속 (Peck)")

    if st.button("ℹ️ 왜 필요한가", key="t2_why_btn"):
        dlg_why(
            "온습도가속시험(HAST, 85/85 등)은 습기침투/부식으로 인한 고장모드를 "
            "가속하기 위해 온도와 상대습도를 동시에 높여 시험합니다.\n\n"
            "Peck 모델은 온도(Arrhenius 항)와 상대습도(RH 지수항)를 함께 반영하여 "
            "가속계수를 계산하며, 커넥터 부식, MLCC 절연파괴 등 습도민감 고장모드에 주로 적용됩니다."
        )

    c_left, c_right = st.columns([1, 3])
    with c_left:
        st.markdown("**사용온도 Tu (°C)**")
        t_use2 = st.number_input("사용온도 Tu (°C)", value=25.0, step=1.0, key="t2_tu", label_visibility="collapsed")
        st.markdown("**시험온도 Tt (°C)**")
        t_test2 = st.number_input("시험온도 Tt (°C)", value=85.0, step=1.0, key="t2_tt", label_visibility="collapsed")
        st.markdown("**사용습도 RHu (%)**")
        rh_use = st.number_input("사용습도 RHu (%)", value=60.0, step=1.0, key="t2_rhu", label_visibility="collapsed")
        st.markdown("**시험습도 RHt (%)**")
        rh_test = st.number_input("시험습도 RHt (%)", value=85.0, step=1.0, key="t2_rht", label_visibility="collapsed")

        st.markdown("**활성화에너지 Ea (eV)**")
        ea2 = st.number_input(
            "활성화에너지 Ea (eV)", value=st.session_state.get("t2_ea", 0.5),
            step=0.05, format="%.3f", key="t2_ea", label_visibility="collapsed"
        )
        if st.button(f"🔎 활성화에너지 DB 검색 ({len(rc.EA_DB)}개 항목)", key="t2_ea_db_btn", use_container_width=True):
            dlg_ea_db("t2")

        st.markdown("**습도지수 n**")
        n_rh = st.number_input("습도지수 n", value=2.5, step=0.1, key="t2_n", label_visibility="collapsed")

        st.markdown("**실사용 목표시간 (h)**")
        field_h2 = st.number_input("실사용 목표시간 (h)", value=8760.0, step=100.0, key="t2_field_h", label_visibility="collapsed")

        run2 = st.button("▶ 계산 실행", type="primary", use_container_width=True, key="t2_run")

    with c_right:
        st.markdown("### 결과")
        if run2:
            af2 = rc.peck_af(ea2, n_rh, t_use2, t_test2, rh_use, rh_test)
            test_h2 = rc.peck_test_time(field_h2, ea2, n_rh, t_use2, t_test2, rh_use, rh_test)
            result_box(
                f"가속계수 <b>AF = {af2:,.3f}</b> 배<br>"
                f"실사용 목표시간 <b>{field_h2:,.0f} h</b> 를 만족하기 위한 시험시간은<br>"
                f"<b>{test_h2:,.2f} 시간</b> (약 {test_h2/24:,.2f}일) 입니다."
            )
            df_out2 = pd.DataFrame({
                "항목": ["사용온도(°C)", "시험온도(°C)", "사용습도(%)", "시험습도(%)", "Ea(eV)", "n",
                        "가속계수 AF", "실사용목표시간(h)", "환산 시험시간(h)"],
                "값": [t_use2, t_test2, rh_use, rh_test, ea2, n_rh, af2, field_h2, test_h2],
            })
            buf2 = io.BytesIO()
            with pd.ExcelWriter(buf2, engine="openpyxl") as writer:
                df_out2.to_excel(writer, sheet_name="온습도가속_결과", index=False)
            st.download_button("📥 엑셀로 내보내기", data=buf2.getvalue(),
                                file_name="온습도가속_결과.xlsx", key="t2_dl")
        else:
            result_box("좌측에서 값을 입력하고 [계산 실행 ▶]을 눌러주세요.")

# =========================== ③ 열피로가속 ==========================
with tab3:
    st.subheader("③ 열피로가속 (Coffin-Manson / Norris-Landzberg)")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("ℹ️ 모델 선택 가이드", key="t3_guide_btn", use_container_width=True):
            dlg_model_guide()
    with c2:
        model = st.selectbox("가속모델 선택", ["Coffin-Manson", "Norris-Landzberg"], key="t3_model")

    col_left, col_right = st.columns([1, 1])  # 원본에서 이 탭만 1:1 비율
    with col_left:
        st.markdown("#### 입력값")
        dt_use = st.number_input("실사용 온도변화폭 ΔTuse (°C)", value=40.0, step=1.0, key="t3_dtuse")
        dt_test = st.number_input("시험 온도변화폭 ΔTtest (°C)", value=100.0, step=1.0, key="t3_dttest")

        st.markdown("**m지수 (피로지수)**")
        m_val = st.number_input(
            "m지수", value=st.session_state.get("t3_m", 2.2), step=0.1, format="%.2f",
            key="t3_m", label_visibility="collapsed"
        )
        if st.button("📖 m지수 참고 가이드", key="t3_m_guide_btn", use_container_width=True):
            dlg_m_guide("t3")

        field_cycles = st.number_input("실사용 목표 사이클수 (cycles)", value=10000.0, step=100.0, key="t3_field_cycles")

        if model == "Norris-Landzberg":
            st.markdown("##### Norris-Landzberg 추가 입력")
            f_use = st.number_input("실사용 사이클 주파수 (cycle/day)", value=4.0, step=0.5, key="t3_fuse")
            f_test = st.number_input("시험 사이클 주파수 (cycle/day)", value=24.0, step=1.0, key="t3_ftest")
            t_max_use = st.number_input("실사용 최고온도 (°C)", value=60.0, step=1.0, key="t3_tmaxuse")
            t_max_test = st.number_input("시험 최고온도 (°C)", value=125.0, step=1.0, key="t3_tmaxtest")

            st.markdown("**활성화에너지 Ea (eV)**")
            ea3 = st.number_input(
                "활성화에너지 Ea (eV)", value=st.session_state.get("t3_ea", 0.12),
                step=0.01, format="%.3f", key="t3_ea", label_visibility="collapsed"
            )
            if st.button(f"🔎 활성화에너지 DB 검색 ({len(rc.EA_DB)}개 항목)", key="t3_ea_db_btn", use_container_width=True):
                dlg_ea_db("t3")

        run3 = st.button("▶ 계산 실행", type="primary", use_container_width=True, key="t3_run")

    with col_right:
        st.markdown("#### 결과")
        if run3:
            if model == "Coffin-Manson":
                af3 = rc.coffin_manson_af(dt_use, dt_test, m_val)
            else:
                af3 = rc.norris_landzberg_af(
                    dt_use, dt_test, m_val, f_use, f_test, ea3, t_max_use, t_max_test
                )
            test_cycles = rc.thermal_cycle_test_time(field_cycles, af3)
            result_box(
                f"선택 모델: <b>{model}</b><br>"
                f"가속계수 <b>AF = {af3:,.3f}</b> 배<br>"
                f"실사용 목표 <b>{field_cycles:,.0f} cycles</b> 를 만족하기 위한 시험 사이클수는<br>"
                f"<b>{test_cycles:,.2f} cycles</b> 입니다."
            )
            out_dict = {
                "항목": ["모델", "ΔTuse(°C)", "ΔTtest(°C)", "m지수", "가속계수 AF",
                        "실사용목표 사이클", "환산 시험 사이클"],
                "값": [model, dt_use, dt_test, m_val, af3, field_cycles, test_cycles],
            }
            if model == "Norris-Landzberg":
                out_dict["항목"] += ["f_use(cycle/day)", "f_test(cycle/day)", "Tmax_use(°C)", "Tmax_test(°C)", "Ea(eV)"]
                out_dict["값"] += [f_use, f_test, t_max_use, t_max_test, ea3]
            df_out3 = pd.DataFrame(out_dict)
            buf3 = io.BytesIO()
            with pd.ExcelWriter(buf3, engine="openpyxl") as writer:
                df_out3.to_excel(writer, sheet_name="열피로가속_결과", index=False)
            st.download_button("📥 엑셀로 내보내기", data=buf3.getvalue(),
                                file_name="열피로가속_결과.xlsx", key="t3_dl")
        else:
            result_box("좌측에서 값을 입력하고 [계산 실행 ▶]을 눌러주세요.")

# =========================== ④ Weibull 시험시간비 ==========================
with tab4:
    st.subheader("④ Weibull 시험시간비 (무고장시험 계획)")

    if st.button("ℹ️ 왜 필요한가", key="t4_why_btn"):
        dlg_why(
            "목표수명과 요구 신뢰도(R)·신뢰수준(C)을 만족하는지 확인하기 위해 "
            "몇 개의 샘플을, 얼마 동안(목표수명 대비 몇 배) 무고장으로 시험해야 하는지 "
            "Weibull 형상모수(β)를 반영해 계산합니다.\n\n"
            "β값은 파손모드의 성격(초기고장/우발고장/마모고장)에 따라 달라지므로, "
            "정확한 시험시간 산출을 위해서는 대상 부품/파손모드에 맞는 β값을 사용해야 합니다."
        )

    c_left, c_right = st.columns([1, 3])
    with c_left:
        target_life = st.number_input("목표수명 (h 또는 cycles)", value=10000.0, step=100.0, key="t4_target")
        reliability = st.slider("요구 신뢰도 R", 0.50, 0.999, 0.90, step=0.001, key="t4_r")
        confidence = st.slider("신뢰수준 C", 0.50, 0.999, 0.90, step=0.001, key="t4_c")
        n_samples = st.number_input("시료 수 n", value=10, step=1, min_value=1, key="t4_n")

        st.markdown("**형상모수 β**")
        beta4 = st.number_input(
            "형상모수 β", value=st.session_state.get("t4_beta", 2.0), step=0.1, format="%.3f",
            key="t4_beta", label_visibility="collapsed"
        )
        if st.button("🔎 Weibull β·η 참고 DB 검색", key="t4_wb_db_btn", use_container_width=True):
            dlg_weibull_db("t4")

        run4 = st.button("▶ 계산 실행", type="primary", use_container_width=True, key="t4_run")

    with c_right:
        st.markdown("### 결과")
        if run4:
            try:
                ratio = rc.weibull_test_ratio(reliability, confidence, beta4, int(n_samples))
                req_time = rc.weibull_required_test_time(target_life, reliability, confidence, beta4, int(n_samples))
                result_box(
                    f"시료 <b>{int(n_samples)}개</b>를 무고장으로 시험할 경우,<br>"
                    f"목표수명 대비 시험시간비 <b>{ratio:,.4f}</b> 배<br>"
                    f"필요 시험시간(수명) <b>{req_time:,.2f}</b> (목표수명 {target_life:,.0f} 기준)<br>"
                    f"→ 요구 신뢰도 R={reliability:.3f}, 신뢰수준 C={confidence:.3f}, β={beta4:.3f} 조건을 만족합니다."
                )
                df_out4 = pd.DataFrame({
                    "항목": ["목표수명", "요구신뢰도 R", "신뢰수준 C", "시료수 n", "형상모수 β",
                            "시험시간비", "필요 시험시간(수명)"],
                    "값": [target_life, reliability, confidence, n_samples, beta4, ratio, req_time],
                })
                buf4 = io.BytesIO()
                with pd.ExcelWriter(buf4, engine="openpyxl") as writer:
                    df_out4.to_excel(writer, sheet_name="Weibull시험시간비_결과", index=False)
                st.download_button("📥 엑셀로 내보내기", data=buf4.getvalue(),
                                    file_name="Weibull시험시간비_결과.xlsx", key="t4_dl")
            except Exception as e:
                st.error(f"계산 중 오류: {e}")
        else:
            result_box("좌측에서 값을 입력하고 [계산 실행 ▶]을 눌러주세요.")

# =========================== ⑤ 수명데이터 분석 ==========================
with tab5:
    st.subheader("⑤ 수명데이터 분석 (Weibull MLE)")

    if st.button("ℹ️ MTTF·B10·B1·R(t) 설명", key="t5_guide_btn"):
        dlg_life_metrics_guide()

    c_left, c_right = st.columns([1, 3])
    with c_left:
        st.markdown("#### 데이터 입력")
        use_sample = st.checkbox("예시 데이터 사용", value=True, key="t5_use_sample")

        if use_sample:
            sample_df = pd.DataFrame({
                "시간": [120, 340, 560, 780, 900, 1050, 1200, 1500, 1800, 2100],
                "중도절단(1=중단,0=고장)": [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            })
            st.session_state["life_data"] = sample_df
        else:
            if "life_data" not in st.session_state:
                st.session_state["life_data"] = pd.DataFrame({
                    "시간": [0.0],
                    "중도절단(1=중단,0=고장)": [0],
                })

        edited = st.data_editor(
            st.session_state["life_data"], num_rows="dynamic",
            use_container_width=True, key="t5_editor", height=280,
        )
        st.session_state["life_data"] = edited

        t_point = st.number_input("임의 시점 t (신뢰도 R(t) 계산용)", value=1000.0, step=50.0, key="t5_tpoint")
        run5 = st.button("▶ Weibull MLE 적합 실행", type="primary", use_container_width=True, key="t5_run")

    with c_right:
        st.markdown("### 결과")
        if run5:
            df5 = st.session_state["life_data"].dropna()
            try:
                times = df5["시간"].astype(float).values
                censored = df5["중도절단(1=중단,0=고장)"].astype(int).values.astype(bool)
                beta_hat, eta_hat = rc.weibull_mle(times, censored)
                mttf = rc.weibull_mttf(beta_hat, eta_hat)
                b10 = rc.weibull_bxx(beta_hat, eta_hat, 10)
                b1 = rc.weibull_bxx(beta_hat, eta_hat, 1)
                r_t = rc.weibull_reliability(t_point, beta_hat, eta_hat)

                result_box(
                    f"형상모수 <b>β = {beta_hat:,.4f}</b>  ·  척도모수 <b>η = {eta_hat:,.2f}</b><br>"
                    f"MTTF (평균수명) = <b>{mttf:,.2f}</b><br>"
                    f"B10 Life = <b>{b10:,.2f}</b>  ·  B1 Life = <b>{b1:,.2f}</b><br>"
                    f"시점 t={t_point:,.0f} 에서의 신뢰도 R(t) = <b>{r_t*100:,.2f}%</b>"
                )

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("➡ 이 β값을 ④ Weibull 시험시간비 탭으로 보내기", key="t5_send_beta", use_container_width=True):
                        st.session_state["t4_beta"] = float(beta_hat)
                        st.success("④ 탭의 β값에 반영되었습니다. ④ 탭에서 확인해주세요.")

                buf5 = io.BytesIO()
                with pd.ExcelWriter(buf5, engine="openpyxl") as writer:
                    st.session_state["life_data"].to_excel(writer, sheet_name="입력데이터", index=False)
                    pd.DataFrame({
                        "항목": ["β", "η", "MTTF", "B10", "B1", "R(t) 계산시점", "R(t)"],
                        "값": [beta_hat, eta_hat, mttf, b10, b1, t_point, r_t],
                    }).to_excel(writer, sheet_name="결과", index=False)
                with c2:
                    st.download_button("📥 엑셀로 내보내기", data=buf5.getvalue(),
                                        file_name="수명데이터분석_결과.xlsx", key="t5_dl")
            except Exception as e:
                st.error(f"계산 중 오류가 발생했습니다: {e}")
        else:
            result_box("좌측에서 데이터를 입력/확인하고 [Weibull MLE 적합 실행 ▶]을 눌러주세요.")
