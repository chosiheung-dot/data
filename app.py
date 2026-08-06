# -*- coding: utf-8 -*-
"""
app.py — 가속시험 통합계산기 (Streamlit 웹 버전)
원본 tkinter 데스크톱 프로그램(신뢰성분석.py)의 레이아웃/버튼/문구를 그대로 재현:
  탭① 온도가속(Arrhenius)
  탭② 온습도가속(Arrhenius-Peck)
  탭③ 열피로가속(Thermal Cycling) - Coffin-Manson / Modified Norris-Landzberg
  탭④ Weibull 시험시간비 계산기 + 참고 DB
  탭⑤ 수명데이터 분석 - 고장/미고장 데이터 -> Weibull MLE -> MTTF/B10/B1/R(t) + 확률도표
각 탭 구조 : 좌측(입력) / 우측(결과, 연한 파란 배경 #eef2fb + 파란 글씨 #1a3fa0) 2단 배치
"""
import io
import math

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['axes.unicode_minus'] = False

import reliability_calc as rc

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


st.set_page_config(page_title="가속시험 통합계산기", layout="wide")

# ---------------------------------------------------------------
# 원본 tkinter 톤(파란 버튼 #2f6fed / 결과박스 #eef2fb, 글씨 #1a3fa0)을
# 최대한 재현하기 위한 공통 CSS + 헬퍼
# ---------------------------------------------------------------
st.markdown("""
<style>
div.stButton > button[kind="primary"] {
    background-color: #2f6fed; color: white; font-weight: 700;
}
.result-box {
    background-color: #eef2fb; color: #1a3fa0; font-weight: 700;
    font-size: 15px; padding: 14px 16px; border-radius: 6px;
    white-space: pre-wrap; line-height: 1.55; min-height: 60px;
}
.detail-box {
    color: #333; font-size: 13.5px; white-space: pre-wrap; line-height: 1.5;
    padding: 6px 2px;
}
.warn-text { color: #a33; font-size: 13px; }
</style>
""", unsafe_allow_html=True)


def result_box(text: str):
    st.markdown(f'<div class="result-box">{text}</div>', unsafe_allow_html=True)


def detail_box(text: str):
    st.markdown(f'<div class="detail-box">{text}</div>', unsafe_allow_html=True)


def df_to_excel_bytes(sheets: dict):
    """{시트명: (헤더행 목록, 데이터행 목록)} -> xlsx bytes"""
    output = io.BytesIO()
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    header_fill = PatternFill("solid", fgColor="DCE6F1")
    bold = Font(bold=True)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name[:31])
        for i, row in enumerate(rows):
            ws.append(row)
            if i == 0:
                for c in ws[1]:
                    c.font = bold
                    c.fill = header_fill
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 20
    wb.save(output)
    return output.getvalue()


st.title("가속시험 통합계산기")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    " ① 온도가속(Arrhenius) ",
    " ② 온습도가속(Arrhenius-Peck) ",
    " ③ 열피로가속(Thermal Cycling) ",
    " ④ Weibull 시험시간비 ",
    " ⑤ 수명데이터 분석 ",
])

# =================================================================
# 공통 세션 상태 초기화
# =================================================================
def _init_state():
    ss = st.session_state
    ss.setdefault("t1_conditions", [])       # 탭① (Ta, t)
    ss.setdefault("t2_conditions", [])       # 탭② (Ta, Ha, t)
    ss.setdefault("t5_rows", [])             # 탭⑤ (time, is_failure)
    ss.setdefault("t5_fit_result", None)     # (beta, eta)
    ss.setdefault("t4_beta_override", None)  # ⑤->④ 연동값
    ss.setdefault("goto_tab4_msg", None)

_init_state()


# =================================================================
# 탭① 온도가속 (Arrhenius)
# =================================================================
with tab1:
    left, right = st.columns([2, 3])

    with left:
        st.markdown("##### ① 온도가속 (Arrhenius Model)")
        st.markdown('<p class="warn-text">※ 사이클(열충격) 시험이 아닌, 단일 온도 유지 시험(정특성)에 적용합니다.</p>',
                    unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**입력값**")
            c1, c2 = st.columns([3, 1])
            e_val = c1.number_input("활성화에너지 E (eV)", value=0.8, step=0.01, format="%.4f", key="t1_e")
            with c2:
                st.write("")
                st.write("")
                with st.popover("DB에서 찾기"):
                    key = st.text_input("부품명 검색:", key="t1_db_search")
                    rows = [r for r in rc.EA_DB if key.strip().lower() in r[0].lower()] if key.strip() else rc.EA_DB
                    df = pd.DataFrame(rows, columns=["부품", "활성화에너지(eV)", "출처", "비고"])
                    st.dataframe(df, height=260, use_container_width=True)
                    st.caption("※ 활성화에너지가 단일 숫자값(범위 아님)인 행만 적용됩니다.")
                    sel_label = st.selectbox("적용할 항목 선택", options=list(range(len(df))),
                                              format_func=lambda i: f"{df.iloc[i]['부품']} ({df.iloc[i]['활성화에너지(eV)']})",
                                              key="t1_db_select") if len(df) else None
                    if st.button("선택값 적용", key="t1_db_apply") and sel_label is not None:
                        ev_text = str(df.iloc[sel_label]["활성화에너지(eV)"]).split("~")[0].split("-")[0].replace("eV", "").strip()
                        try:
                            st.session_state["t1_e"] = float(ev_text)
                            st.rerun()
                        except ValueError:
                            st.warning("이 항목은 단일 숫자값이 아니라 자동입력이 어렵습니다. 직접 입력해주세요.")
            tref = st.number_input("대표(목표) 온도 Tref (℃)", value=125.0, step=1.0, key="t1_tref")

        with st.container(border=True):
            st.markdown("**시험 조건 (온도 / 시간) 추가**")
            cc1, cc2, cc3 = st.columns([1, 1, 1])
            ta_in = cc1.number_input("조건온도(℃)", value=100.0, step=1.0, key="t1_ta_in")
            time_in = cc2.number_input("조건시간(h)", value=200.0, step=1.0, key="t1_time_in")
            with cc3:
                st.write("")
                if st.button("추가 +", key="t1_add"):
                    st.session_state.t1_conditions.append((ta_in, time_in))

            st.markdown("**조건 목록**")
            if st.session_state.t1_conditions:
                cond_df = pd.DataFrame(st.session_state.t1_conditions, columns=["조건온도(℃)", "조건시간(h)"])
                st.dataframe(cond_df, use_container_width=True, height=180)
            else:
                cond_df = pd.DataFrame(columns=["조건온도(℃)", "조건시간(h)"])
                st.caption("추가된 조건이 없습니다.")

            bd1, bd2 = st.columns(2)
            del_idx = bd1.number_input("삭제할 행 번호(0부터)", min_value=0, value=0, step=1, key="t1_del_idx",
                                        disabled=not st.session_state.t1_conditions)
            if bd1.button("선택 삭제 🗑", key="t1_del_sel", disabled=not st.session_state.t1_conditions):
                if 0 <= int(del_idx) < len(st.session_state.t1_conditions):
                    st.session_state.t1_conditions.pop(int(del_idx))
                    st.rerun()
            if bd2.button("전체 삭제", key="t1_del_all", disabled=not st.session_state.t1_conditions):
                st.session_state.t1_conditions = []
                st.rerun()

        with st.container(border=True):
            st.markdown("**Weibull 시험시간비 적용 (선택)**")
            wb_apply = st.checkbox("적용", key="t1_wb_apply")
            w1, w2, w3, w4 = st.columns(4)
            r_var = w1.number_input("목표신뢰도 R", value=0.99, format="%.4f", key="t1_r")
            cl_var = w2.number_input("신뢰수준 CL", value=0.5, format="%.4f", key="t1_cl")
            n_var = w3.number_input("샘플수 n", value=6.0, step=1.0, key="t1_n")
            beta_var = w4.number_input("형상모수 β", value=2.0, step=0.1, key="t1_beta")

        b1, b2 = st.columns(2)
        calc_clicked = b1.button("계산 실행 ▶", type="primary", use_container_width=True, key="t1_calc")

        if calc_clicked:
            if not st.session_state.t1_conditions:
                st.warning("조건을 1개 이상 추가해주세요.")
            else:
                last_rows = []
                total = 0.0
                for ta, t in st.session_state.t1_conditions:
                    af = rc.arrhenius_af(tref, ta, e_val)
                    eq = t * af
                    total += eq
                    last_rows.append((ta, t, af, eq))
                final_time = total
                ratio = None
                if wb_apply:
                    try:
                        ratio = rc.weibull_test_time_ratio(r_var, cl_var, n_var, beta_var)
                        final_time = total * ratio
                    except (ValueError, ZeroDivisionError):
                        st.warning("Weibull 파라미터를 확인해주세요.")
                st.session_state["t1_last"] = dict(rows=last_rows, total=total, ratio=ratio,
                                                    final=final_time, tref=tref, e=e_val)

        with right:
            st.markdown("##### 결과")
            last = st.session_state.get("t1_last")
            if last:
                lines = [f"총 등가시험시간(@{last['tref']:.1f}℃) = {last['total']:,.2f} h  ({last['total']/24:,.2f} 일)"]
                if last["ratio"] is not None:
                    lines.append(f"Weibull 시험시간비 = {last['ratio']:.4f}")
                    lines.append(f"최종 가속시험시간 = {last['final']:,.2f} h  ({last['final']/24:,.2f} 일)")
                result_box("\n".join(lines))
            else:
                result_box("조건을 입력하고 [계산 실행]을 눌러주세요.")

            with st.expander("계산 공식 (Arrhenius Model)", expanded=True):
                st.text(
                    "AF = exp[ (E / k) x (1/Tu - 1/Ta) ]\n\n"
                    "여기서  AF : 가속계수\n"
                    "        E  : 활성화에너지 (eV)\n"
                    "        k  : Boltzmann 상수 (8.6173e-05 eV/K)\n"
                    "        Tu : 사용(필드) 온도 (K)\n"
                    "        Ta : 가속(시험) 온도 (K)\n\n"
                    "등가시험시간 = 조건시간 / AF  (조건온도 -> Tref 로 환산)\n"
                    "최종 가속시험시간 = 등가시험시간 합계 x Weibull 시험시간비"
                )

            if last:
                detail = ["[조건별 상세]"]
                for ta, t, af, eq in last["rows"]:
                    detail.append(f"  {ta:.1f}℃ / {t:.1f}h  ->  AF={af:,.3f}   등가시간={eq:,.2f}h")
                detail_box("\n".join(detail))

            if last and HAS_OPENPYXL:
                sheets = {
                    "온도가속(Arrhenius)": [
                        ["활성화에너지 E(eV)", last["e"], "대표(목표)온도 Tref(℃)", last["tref"]],
                        ["조건온도(℃)", "조건시간(h)", "가속계수 AF", "등가시간(h)"],
                        *[[ta, t, af, eq] for ta, t, af, eq in last["rows"]],
                    ]
                }
                sheets["온도가속(Arrhenius)"].append(["총 등가시험시간(h)", last["total"]])
                if last["ratio"] is not None:
                    sheets["온도가속(Arrhenius)"].append(["Weibull 시험시간비", last["ratio"]])
                    sheets["온도가속(Arrhenius)"].append(["최종 가속시험시간(h)", last["final"]])
                b2.download_button("엑셀로 내보내기 📊", df_to_excel_bytes(sheets),
                                    file_name="온도가속_계산결과.xlsx", use_container_width=True, key="t1_dl")
            else:
                b2.button("엑셀로 내보내기 📊", disabled=True, use_container_width=True, key="t1_dl_disabled")


# =================================================================
# 탭② 온습도가속 (Arrhenius-Peck)
# =================================================================
with tab2:
    left, right = st.columns([2, 3])

    with left:
        st.markdown("##### ② 온습도가속 (Arrhenius-Peck Model)")

        with st.container(border=True):
            st.markdown("**입력값**")
            c1, c2, c3 = st.columns([2, 1, 2])
            e_val2 = c1.number_input("활성화에너지 E (eV)", value=0.79, step=0.01, format="%.4f", key="t2_e")
            with c2:
                st.write("")
                st.write("")
                with st.popover("DB"):
                    key = st.text_input("부품명 검색:", key="t2_db_search")
                    rows = [r for r in rc.EA_DB if key.strip().lower() in r[0].lower()] if key.strip() else rc.EA_DB
                    df = pd.DataFrame(rows, columns=["부품", "활성화에너지(eV)", "출처", "비고"])
                    st.dataframe(df, height=260, use_container_width=True)
                    sel = st.selectbox("적용할 항목 선택", options=list(range(len(df))),
                                        format_func=lambda i: f"{df.iloc[i]['부품']} ({df.iloc[i]['활성화에너지(eV)']})",
                                        key="t2_db_select") if len(df) else None
                    if st.button("선택값 적용", key="t2_db_apply") and sel is not None:
                        ev_text = str(df.iloc[sel]["활성화에너지(eV)"]).split("~")[0].split("-")[0].replace("eV", "").strip()
                        try:
                            st.session_state["t2_e"] = float(ev_text)
                            st.rerun()
                        except ValueError:
                            st.warning("이 항목은 단일 숫자값이 아니라 자동입력이 어렵습니다. 직접 입력해주세요.")
            n_val = c3.number_input("습도항 지수 n", value=2.66, step=0.01, key="t2_n")

            d1, d2 = st.columns(2)
            tu_val = d1.number_input("사용(필드) 온도 Tu(℃)", value=23.0, step=1.0, key="t2_tu")
            hu_val = d2.number_input("사용(필드) 습도 Hu(%RH)", value=65.0, step=1.0, key="t2_hu")

        with st.container(border=True):
            st.markdown("**가속시험 조건 (온도 / 습도 / 시간) 추가**")
            cc1, cc2, cc3, cc4 = st.columns([1, 1, 1, 1])
            ta_in = cc1.number_input("가속온도(℃)", value=85.0, step=1.0, key="t2_ta_in")
            ha_in = cc2.number_input("가속습도(%RH)", value=85.0, step=1.0, key="t2_ha_in")
            t_in = cc3.number_input("시간(h)", value=303.0, step=1.0, key="t2_t_in")
            with cc4:
                st.write("")
                if st.button("추가 +", key="t2_add"):
                    st.session_state.t2_conditions.append((ta_in, ha_in, t_in))

            st.markdown("**조건 목록**")
            if st.session_state.t2_conditions:
                cond_df = pd.DataFrame(st.session_state.t2_conditions,
                                        columns=["가속온도(℃)", "가속습도(%RH)", "시간(h)"])
                st.dataframe(cond_df, use_container_width=True, height=180)
            else:
                st.caption("추가된 조건이 없습니다.")

            bd1, bd2 = st.columns(2)
            del_idx2 = bd1.number_input("삭제할 행 번호(0부터)", min_value=0, value=0, step=1, key="t2_del_idx",
                                         disabled=not st.session_state.t2_conditions)
            if bd1.button("선택 삭제 🗑", key="t2_del_sel", disabled=not st.session_state.t2_conditions):
                if 0 <= int(del_idx2) < len(st.session_state.t2_conditions):
                    st.session_state.t2_conditions.pop(int(del_idx2))
                    st.rerun()
            if bd2.button("전체 삭제", key="t2_del_all", disabled=not st.session_state.t2_conditions):
                st.session_state.t2_conditions = []
                st.rerun()

        with st.container(border=True):
            st.markdown("**Weibull 시험시간비 적용 (선택)**")
            wb_apply2 = st.checkbox("적용", key="t2_wb_apply")
            w1, w2, w3, w4 = st.columns(4)
            r_var2 = w1.number_input("목표신뢰도 R", value=0.99, format="%.4f", key="t2_r")
            cl_var2 = w2.number_input("신뢰수준 CL", value=0.5, format="%.4f", key="t2_cl")
            n_var2 = w3.number_input("샘플수 n", value=6.0, step=1.0, key="t2_ns")
            beta_var2 = w4.number_input("형상모수 β", value=2.0, step=0.1, key="t2_beta")

        b1, b2 = st.columns(2)
        calc_clicked2 = b1.button("계산 실행 ▶", type="primary", use_container_width=True, key="t2_calc")

        if calc_clicked2:
            if not st.session_state.t2_conditions:
                st.warning("조건을 1개 이상 추가해주세요.")
            else:
                last_rows = []
                total = 0.0
                for ta, ha, t in st.session_state.t2_conditions:
                    af = rc.peck_af(tu_val, hu_val, ta, ha, e_val2, n_val)
                    eq = t * af
                    total += eq
                    last_rows.append((ta, ha, t, af, eq))
                final_time = total
                ratio = None
                if wb_apply2:
                    try:
                        ratio = rc.weibull_test_time_ratio(r_var2, cl_var2, n_var2, beta_var2)
                        final_time = total * ratio
                    except (ValueError, ZeroDivisionError):
                        st.warning("Weibull 파라미터를 확인해주세요.")
                st.session_state["t2_last"] = dict(rows=last_rows, total=total, ratio=ratio, final=final_time,
                                                    tu=tu_val, hu=hu_val, e=e_val2, n=n_val)

        with right:
            st.markdown("##### 결과")
            last = st.session_state.get("t2_last")
            if last:
                lines = [f"총 등가시험시간(@{last['tu']:.1f}℃/{last['hu']:.1f}%RH 기준) = "
                         f"{last['total']:,.2f} h  ({last['total']/24:,.2f} 일)"]
                if last["ratio"] is not None:
                    lines.append(f"Weibull 시험시간비 = {last['ratio']:.4f}")
                    lines.append(f"최종 가속시험시간 = {last['final']:,.2f} h  ({last['final']/24:,.2f} 일)")
                result_box("\n".join(lines))
            else:
                result_box("조건을 입력하고 [계산 실행]을 눌러주세요.")

            with st.expander("계산 공식 (Arrhenius-Peck Model)", expanded=True):
                st.text(
                    "AF = Lu/La = exp[(E/k) x (1/Tu - 1/Ta)] x (Hu/Ha)^(-n)\n\n"
                    "여기서  AF : 가속계수(Acceleration Factor)\n"
                    "        L  : 제품의 수명(h)\n"
                    "        E  : 활성화 에너지(Activation Energy), eV\n"
                    "        k  : Boltzmann 상수(=8.6173e-05 eV/K)\n"
                    "        T  : 절대 온도(K)\n"
                    "        H  : 상대 습도(% RH)\n"
                    "        n  : 습도항 지수\n"
                    "        첨자 a : 가속조건 / 첨자 u : 비가속조건 또는 사용자 환경조건\n\n"
                    "등가시험시간 = 조건시간 / AF\n"
                    "최종 가속시험시간 = 등가시험시간 합계 x Weibull 시험시간비"
                )

            if last:
                detail = ["[조건별 상세]"]
                for ta, ha, t, af, eq in last["rows"]:
                    detail.append(f"  {ta:.1f}℃/{ha:.1f}%RH / {t:.1f}h  ->  AF={af:,.2f}   등가시간={eq:,.2f}h")
                detail_box("\n".join(detail))

            if last and HAS_OPENPYXL:
                sheets = {
                    "온습도가속(Peck)": [
                        ["E(eV)", last["e"], "n", last["n"], "Tu(℃)", last["tu"], "Hu(%RH)", last["hu"]],
                        ["가속온도(℃)", "가속습도(%RH)", "시간(h)", "AF", "등가시간(h)"],
                        *[[ta, ha, t, af, eq] for ta, ha, t, af, eq in last["rows"]],
                    ]
                }
                sheets["온습도가속(Peck)"].append(["총 등가시험시간(h)", last["total"]])
                if last["ratio"] is not None:
                    sheets["온습도가속(Peck)"].append(["Weibull 시험시간비", last["ratio"]])
                    sheets["온습도가속(Peck)"].append(["최종 가속시험시간(h)", last["final"]])
                b2.download_button("엑셀로 내보내기 📊", df_to_excel_bytes(sheets),
                                    file_name="온습도가속_계산결과.xlsx", use_container_width=True, key="t2_dl")
            else:
                b2.button("엑셀로 내보내기 📊", disabled=True, use_container_width=True, key="t2_dl_disabled")


# =================================================================
# 탭③ 열피로가속 (Thermal Cycling)
# =================================================================
with tab3:
    left, right = st.columns([1, 1])

    with left:
        st.markdown("##### ③ 열피로가속 (Thermal Cycling)")
        st.markdown('<p class="warn-text">※ 챔버 승온형 온도사이클(Thermal Cycling) 전용입니다. '
                    '(엘리베이터형 Thermal Shock 시험은 전환시간이 거의 0으로, 별도 모델이 필요합니다)</p>',
                    unsafe_allow_html=True)

        def profile_group(title, defaults, key_prefix, has_target=False):
            with st.container(border=True):
                st.markdown(f"**{title}**")
                low = st.number_input("저온(℃)", value=defaults["low"], key=f"{key_prefix}_low")
                low_dwell = st.number_input("저온유지시간(분)", value=defaults["low_dwell"], key=f"{key_prefix}_ld")
                ramp_up = st.number_input("승온시간(분, 저온→고온)", value=defaults["ramp_up"], key=f"{key_prefix}_ru")
                high = st.number_input("고온(℃)", value=defaults["high"], key=f"{key_prefix}_high")
                high_dwell = st.number_input("고온유지시간(분)", value=defaults["high_dwell"], key=f"{key_prefix}_hd")
                ramp_down = st.number_input("하강시간(분, 고온→저온)", value=defaults["ramp_down"], key=f"{key_prefix}_rd")
                target = None
                if has_target:
                    target = st.number_input("필드 목표 사이클수", value=defaults.get("target_cycle", 1000.0),
                                              key=f"{key_prefix}_tc")
                return dict(low=low, low_dwell=low_dwell, ramp_up=ramp_up, high=high,
                            high_dwell=high_dwell, ramp_down=ramp_down, target_cycle=target)

        pc1, pc2 = st.columns(2)
        with pc1:
            field = profile_group("사용조건(필드) 사이클 프로파일",
                                   dict(low=-40.0, low_dwell=10.0, ramp_up=30.0, high=85.0,
                                        high_dwell=10.0, ramp_down=30.0, target_cycle=1000.0),
                                   "t3_field", has_target=True)
        with pc2:
            test = profile_group("시험조건 사이클 프로파일",
                                  dict(low=-40.0, low_dwell=10.0, ramp_up=30.0, high=125.0,
                                       high_dwell=40.0, ramp_down=10.0),
                                  "t3_test", has_target=False)

        st.caption("예) -40℃(30분) ↔ 125℃(30분), 승온/하강 각 10분  형태로 입력하시면 됩니다.")

        with st.container(border=True):
            st.markdown("**가속 모델 선택**")
            mc1, mc2 = st.columns([1, 1])
            with mc1:
                model_sel = st.radio("모델", options=["coffin", "norris"],
                                      format_func=lambda v: "Coffin-Manson (단순, ΔT만 반영)" if v == "coffin"
                                      else "Modified Norris-Landzberg (정밀, dwell/ramp/온도 반영)",
                                      key="t3_model", label_visibility="collapsed")
                mm1, mm2 = st.columns([1, 1])
                m_val = mm1.number_input("m지수", value=2.5, step=0.1, key="t3_m")
                with mm2:
                    st.write("")
                    with st.popover("m지수 가이드"):
                        gdf = pd.DataFrame(rc.M_GUIDE_DB, columns=["재질/메커니즘", "m지수", "대상 부품(예)"])
                        st.dataframe(gdf, use_container_width=True, height=180)
                        gsel = st.selectbox("적용할 항목 선택", options=list(range(len(gdf))),
                                             format_func=lambda i: f"{gdf.iloc[i]['재질/메커니즘']} (m={gdf.iloc[i]['m지수']})",
                                             key="t3_m_select")
                        if st.button("선택값 적용", key="t3_m_apply"):
                            st.session_state["t3_m"] = float(gdf.iloc[gsel]["m지수"])
                            st.rerun()
            with mc2:
                st.markdown("**언제 어떤 모델을 써야 하나요?**")
                st.text(rc.MODEL_GUIDE_TEXT)

        with st.container(border=True):
            st.markdown("**Weibull 시험시간비 적용 (선택)**")
            wb_apply3 = st.checkbox("적용", key="t3_wb_apply")
            w1, w2, w3, w4 = st.columns(4)
            r_var3 = w1.number_input("목표신뢰도 R", value=0.99, format="%.4f", key="t3_r")
            cl_var3 = w2.number_input("신뢰수준 CL", value=0.5, format="%.4f", key="t3_cl")
            n_var3 = w3.number_input("샘플수 n", value=6.0, step=1.0, key="t3_ns")
            beta_var3 = w4.number_input("형상모수 β", value=2.0, step=0.1, key="t3_beta")

        b1, b2 = st.columns(2)
        calc_clicked3 = b1.button("계산 실행 ▶", type="primary", use_container_width=True, key="t3_calc")

        if calc_clicked3:
            dT_field = abs(field["high"] - field["low"])
            dT_test = abs(test["high"] - test["low"])
            cycle_time_field = rc.profile_cycle_time_min(field["low_dwell"], field["ramp_up"],
                                                           field["high_dwell"], field["ramp_down"])
            cycle_time_test = rc.profile_cycle_time_min(test["low_dwell"], test["ramp_up"],
                                                          test["high_dwell"], test["ramp_down"])
            if model_sel == "coffin":
                af = rc.coffin_manson_af(dT_field, dT_test, m_val)
            else:
                ramp_test_rate = dT_test / test["ramp_up"] if test["ramp_up"] > 0 else 0.0001
                af = rc.norris_landzberg_af(dT_field, dT_test, field["high_dwell"], test["high_dwell"],
                                             ramp_test_rate, field["high"], test["high"])

            target_cycle = field["target_cycle"] or 0
            need_cycle = target_cycle / af if af > 0 else float("inf")
            total_min = need_cycle * cycle_time_test
            total_hour = total_min / 60
            total_day = total_hour / 24

            final_cycle = need_cycle
            final_min = total_min
            ratio = None
            if wb_apply3:
                try:
                    ratio = rc.weibull_test_time_ratio(r_var3, cl_var3, n_var3, beta_var3)
                    final_cycle = need_cycle * ratio
                    final_min = final_cycle * cycle_time_test
                except (ValueError, ZeroDivisionError):
                    st.warning("Weibull 파라미터를 확인해주세요.")

            st.session_state["t3_last"] = dict(dT_field=dT_field, dT_test=dT_test,
                                                cycle_time_field=cycle_time_field, cycle_time_test=cycle_time_test,
                                                af=af, need_cycle=need_cycle, total_min=total_min,
                                                total_hour=total_hour, total_day=total_day, ratio=ratio,
                                                final_cycle=final_cycle, final_min=final_min,
                                                model=model_sel)

        with right:
            st.markdown("##### 결과")
            last = st.session_state.get("t3_last")
            if last:
                lines = [
                    f"ΔT(필드/시험) = {last['dT_field']:.1f}℃ / {last['dT_test']:.1f}℃",
                    f"1cycle 시간(필드/시험) = {last['cycle_time_field']:.1f}분 / {last['cycle_time_test']:.1f}분",
                    "",
                    f"가속계수 AF = {last['af']:,.3f}",
                    f"필요 시험 사이클수 = {last['need_cycle']:,.2f} cycle",
                    f"총 소요시간 = {last['total_min']:,.1f}분 = {last['total_hour']:,.2f}시간 = {last['total_day']:,.2f}일",
                ]
                if last["ratio"] is not None:
                    lines.append("")
                    lines.append(f"Weibull 시험시간비 = {last['ratio']:.4f}")
                    lines.append(f"최종 가속시험 사이클수 = {last['final_cycle']:,.2f} cycle "
                                 f"({last['final_min']/60:,.2f}시간 = {last['final_min']/60/24:,.2f}일)")
                result_box("\n".join(lines))
            else:
                result_box("프로파일을 입력하고 [계산 실행]을 눌러주세요.")

            with st.expander("계산 공식", expanded=True):
                if (last and last["model"] == "coffin") or (not last and model_sel == "coffin"):
                    st.text(
                        "[Coffin-Manson Model]\n\n"
                        "AF = ( ΔT_test / ΔT_field ) ^ m\n\n"
                        "여기서  AF : 가속계수\n"
                        "        ΔT : 온도변화폭(사이클 최고온도-최저온도)\n"
                        "        m  : 재료/구조에 따른 경험적 지수 (보통 1.9~5)\n\n"
                        "필요 시험 사이클수 = 필드 목표 사이클수 / AF\n"
                        "1cycle 시간 = 저온유지 + 승온시간 + 고온유지 + 하강시간\n"
                        "총 소요시간 = 필요 시험 사이클수 x 1cycle 시간"
                    )
                else:
                    st.text(
                        "[Modified Norris-Landzberg Model]\n\n"
                        "AF = (ΔT_test/ΔT_field)^2.65\n"
                        "     x (Dwell_test/Dwell_field)^0.136\n"
                        "     x (1.22 x RampRate_test^-0.0757)\n"
                        "     x exp[2185 x (1/Tmax_field(K) - 1/Tmax_test(K))]\n\n"
                        "여기서  Dwell : 고온유지시간,  RampRate : 승온속도(℃/분)\n"
                        "        Tmax  : 사이클 최고온도(K)\n"
                        "        (계수 n=2.65, m=0.136, Ea/k=2185 는 Pb-free 솔더 접합 문헌 기준 근사값)\n\n"
                        "필요 시험 사이클수 = 필드 목표 사이클수 / AF\n"
                        "1cycle 시간 = 저온유지 + 승온시간 + 고온유지 + 하강시간\n"
                        "총 소요시간 = 필요 시험 사이클수 x 1cycle 시간"
                    )

            if last and HAS_OPENPYXL:
                model_name = "Coffin-Manson" if last["model"] == "coffin" else "Modified Norris-Landzberg"
                sheets = {
                    "열피로가속(Thermal Cycling)": [
                        ["항목", "값"],
                        ["모델", model_name],
                        ["ΔT_field(℃)", last["dT_field"]],
                        ["ΔT_test(℃)", last["dT_test"]],
                        ["가속계수 AF", last["af"]],
                        ["필요 시험 사이클수", last["need_cycle"]],
                        ["1cycle 시험시간(분)", last["cycle_time_test"]],
                        ["총 소요시간(시간)", last["total_hour"]],
                        ["총 소요시간(일)", last["total_day"]],
                    ]
                }
                if last["ratio"] is not None:
                    sheets["열피로가속(Thermal Cycling)"].extend([
                        ["Weibull 시험시간비", last["ratio"]],
                        ["최종 가속시험 사이클수", last["final_cycle"]],
                        ["최종 가속시험시간(시간)", last["final_min"] / 60],
                    ])
                b2.download_button("엑셀로 내보내기 📊", df_to_excel_bytes(sheets),
                                    file_name="열피로가속_계산결과.xlsx", use_container_width=True, key="t3_dl")
            else:
                b2.button("엑셀로 내보내기 📊", disabled=True, use_container_width=True, key="t3_dl_disabled")


# =================================================================
# 탭④ Weibull 시험시간비 계산기 + 참고 DB
# =================================================================
with tab4:
    left, right = st.columns([2, 3])

    with left:
        st.markdown("##### ④ Weibull 시험시간비 계산기")

        default_beta = st.session_state.get("t4_beta_override") or 2.0

        with st.container(border=True):
            st.markdown("**입력값**")
            r4 = st.number_input("목표신뢰도 R", value=0.99, format="%.4f", key="t4_r")
            cl4 = st.number_input("신뢰수준 CL", value=0.5, format="%.4f", key="t4_cl")
            n4 = st.number_input("샘플수 n", value=6.0, step=1.0, key="t4_n")
            beta4 = st.number_input("형상모수 β", value=float(default_beta), step=0.1, key="t4_beta")

        with st.popover("Beta 참고DB 열기", use_container_width=True):
            key = st.text_input("부품명 검색:", key="t4_db_search")
            rows = [r for r in rc.WEIBULL_DB if key.strip().lower() in r[1].lower()] if key.strip() else rc.WEIBULL_DB
            wdf = pd.DataFrame(rows, columns=["분류", "항목", "Beta Low", "Beta Typ", "Beta High",
                                               "Eta Low", "Eta Typ", "Eta High"])
            st.dataframe(wdf, use_container_width=True, height=300)
            wsel = st.selectbox("적용할 항목 선택", options=list(range(len(wdf))),
                                 format_func=lambda i: f"{wdf.iloc[i]['항목']} (β={wdf.iloc[i]['Beta Typ']})",
                                 key="t4_db_select") if len(wdf) else None
            if st.button("Beta(Typical) 값 적용", key="t4_db_apply") and wsel is not None:
                st.session_state["t4_beta"] = float(wdf.iloc[wsel]["Beta Typ"])
                st.rerun()

        calc4 = st.button("계산 실행 ▶", type="primary", use_container_width=True, key="t4_calc")

        if calc4:
            try:
                ratio4 = rc.weibull_test_time_ratio(r4, cl4, n4, beta4)
                st.session_state["t4_result"] = ratio4
            except (ValueError, ZeroDivisionError):
                st.warning("값을 확인해주세요.")

        if st.session_state.get("goto_tab4_msg"):
            st.success(st.session_state["goto_tab4_msg"])
            st.session_state["goto_tab4_msg"] = None

    with right:
        st.markdown("##### 결과")
        ratio4 = st.session_state.get("t4_result")
        if ratio4 is not None:
            result_box(f"시험시간비 = {ratio4:.4f}")
        else:
            result_box("값을 입력하고 [계산 실행]을 눌러주세요.")

        with st.expander("계산 공식", expanded=True):
            st.text(
                "시험시간비 = [ (-ln CL) / (n x -ln R) ] ^ (1/β)\n\n"
                "최종 가속시험시간(또는 사이클수) = 등가시험시간(사이클수) x 시험시간비"
            )


# =================================================================
# 탭⑤ 수명데이터 분석
# =================================================================
with tab5:
    left, right = st.columns([2, 3])

    with left:
        st.markdown("##### ⑤ 수명데이터 분석 (Weibull)")

        with st.container(border=True):
            st.markdown("**고장/미고장 데이터 입력**")
            rc1, rc2, rc3 = st.columns([1, 1, 1])
            time_in5 = rc1.number_input("시간(h 또는 cycle)", min_value=0.0, value=0.0, step=1.0, key="t5_time_in")
            status_in5 = rc2.radio("상태", options=["고장", "미고장"], key="t5_status_in", horizontal=True)
            with rc3:
                st.write("")
                if st.button("추가 +", key="t5_add"):
                    if time_in5 > 0:
                        st.session_state.t5_rows.append((time_in5, status_in5 == "고장"))
                    else:
                        st.warning("시간을 올바르게 입력해주세요. (0보다 큰 값)")

            st.caption("※ 미고장 = 관찰(시험) 종료 시점까지 고장이 발생하지 않은 데이터")

            if st.session_state.t5_rows:
                rows_df = pd.DataFrame(
                    [(f"{t:.2f}", "고장" if f else "미고장") for t, f in st.session_state.t5_rows],
                    columns=["시간", "상태"])
                st.dataframe(rows_df, use_container_width=True, height=220)
            else:
                st.caption("입력된 데이터가 없습니다.")

            bb1, bb2, bb3, bb4 = st.columns(4)
            del_idx5 = bb1.number_input("삭제 행 번호(0부터)", min_value=0, value=0, step=1, key="t5_del_idx",
                                         disabled=not st.session_state.t5_rows, label_visibility="collapsed")
            if bb1.button("선택 삭제", key="t5_del_sel", disabled=not st.session_state.t5_rows):
                if 0 <= int(del_idx5) < len(st.session_state.t5_rows):
                    st.session_state.t5_rows.pop(int(del_idx5))
                    st.rerun()
            if bb2.button("전체 삭제", key="t5_del_all", disabled=not st.session_state.t5_rows):
                st.session_state.t5_rows = []
                st.session_state.t5_fit_result = None
                st.rerun()
            if bb3.button("예시데이터 불러오기", key="t5_example"):
                example = [
                    (185, True), (260, True), (312, True), (355, True), (398, True),
                    (430, True), (470, True), (520, True), (610, True),
                    (700, False), (700, False), (700, False), (700, False), (700, False), (700, False),
                ]
                st.session_state.t5_rows = example
                st.rerun()

        fit_clicked = st.button("Weibull 적합(MLE) 실행 ▶", type="primary", use_container_width=True, key="t5_fit")

        if fit_clicked:
            rows = st.session_state.t5_rows
            if len(rows) < 3:
                st.warning("데이터를 3개 이상 입력해주세요 (고장 데이터 2개 이상 포함).")
            else:
                times = [r[0] for r in rows]
                is_failure = [r[1] for r in rows]
                n_fail = sum(is_failure)
                if n_fail < 2:
                    st.warning("고장(Failure) 데이터가 2개 이상 필요합니다.")
                else:
                    result = rc.fit_weibull_mle(times, is_failure)
                    if result is None:
                        st.warning("Weibull 적합에 실패했습니다. 데이터를 확인해주세요.")
                    else:
                        st.session_state.t5_fit_result = result
                        st.session_state.t5_times = times
                        st.session_state.t5_is_failure = is_failure

        # 엑셀 내보내기 버튼(항상 표시, 데이터 있을 때만 활성)
        if HAS_OPENPYXL and st.session_state.t5_rows:
            sheets = {
                "수명데이터": [["시간", "상태"]] +
                             [[t, "고장" if f else "미고장"] for t, f in st.session_state.t5_rows],
            }
            fr = st.session_state.t5_fit_result
            fit_rows = [["항목", "값"]]
            if fr is not None:
                beta, eta = fr
                fit_rows += [["형상모수 β", beta], ["척도모수 η", eta],
                             ["MTTF(평균수명)", rc.weibull_mttf(beta, eta)],
                             ["B10 수명", rc.weibull_bpercentile(beta, eta, 10)],
                             ["B1 수명", rc.weibull_bpercentile(beta, eta, 1)]]
            else:
                fit_rows.append(["안내", "적합을 먼저 실행해주세요."])
            sheets["적합결과"] = fit_rows
            st.download_button("엑셀로 내보내기", df_to_excel_bytes(sheets),
                                file_name="수명데이터분석_결과.xlsx", use_container_width=True, key="t5_dl")
        else:
            st.button("엑셀로 내보내기", disabled=True, use_container_width=True, key="t5_dl_disabled")

    with right:
        st.markdown("##### 적합 결과")
        fr = st.session_state.t5_fit_result
        if fr is not None:
            beta, eta = fr
            times = st.session_state.get("t5_times", [])
            is_failure = st.session_state.get("t5_is_failure", [])
            n_fail = sum(is_failure)
            n_total = len(times)
            if beta < 1.0:
                interp = "β<1 : 초기고장(Infant Mortality) 특성 - 시간이 지날수록 고장률이 감소"
            elif beta < 1.3:
                interp = "β≈1 : 우발고장(Random Failure) 특성 - 고장률이 시간과 거의 무관"
            else:
                interp = "β>1 : 마모성고장(Wear-out) 특성 - 시간이 지날수록 고장률이 증가"
            result_box(
                f"형상모수 β = {beta:.4f}   척도모수 η = {eta:,.2f}\n"
                f"(총 {n_total}개 데이터 : 고장 {n_fail}개 / 미고장 {n_total - n_fail}개)\n"
                f"{interp}"
            )
        else:
            result_box("데이터를 입력하고 [Weibull 적합(MLE) 실행]을 눌러주세요. (고장 데이터 2개 이상 필요)")

        if st.button("이 β값을 ④ Weibull 탭으로 보내기 →", disabled=(fr is None), key="t5_send_beta"):
            beta, eta = fr
            st.session_state["t4_beta_override"] = beta
            st.session_state["t4_beta"] = beta
            st.session_state["goto_tab4_msg"] = f"β = {beta:.4f} 값을 ④ Weibull 시험시간비 탭으로 보냈습니다. (④ 탭에서 확인하세요)"
            st.rerun()

        st.markdown("**대표수명 지표 (MTTF / B10 / B1)**")
        with st.popover("ⓘ 왜 필요한가?"):
            st.text(
                "β(형상모수)와 η(척도모수)만으로는 '이 제품이 실제로 몇 시간/사이클을 버티는지'가\n"
                "바로 감이 오지 않기 때문에, 실무에서 바로 쓸 수 있는 대표수명값으로 변환한 지표입니다.\n\n"
                "· MTTF (평균수명)\n"
                "  전체 제품의 평균적인 고장 시점입니다. '평균적으로 이 정도 시간에 고장난다'는 의미이며,\n"
                "  설계수명과 비교해 여유(마진)가 있는지 확인하는 데 씁니다.\n\n"
                "· B10 수명\n"
                "  전체 중 10%가 고장 나는 시점입니다. 자동차/전자부품 업계에서 널리 쓰이는\n"
                "  표준 신뢰성 판정 지표로, '고객에게 보증할 수명'을 정할 때 기준으로 많이 사용합니다.\n\n"
                "· B1 수명\n"
                "  전체 중 1%가 고장 나는 시점입니다. B10보다 더 보수적인(엄격한) 기준이며,\n"
                "  안전과 직결되는 부품이나 높은 신뢰성이 요구되는 부품에 사용합니다.\n\n"
                "즉 세 지표 모두 β/η 모델을 '몇 % 고장 시점이 언제인지'로 쉽게 풀어서\n"
                "리포트나 고객 스펙 비교에 바로 활용할 수 있게 해주는 값입니다."
            )
        if fr is not None:
            beta, eta = fr
            mttf = rc.weibull_mttf(beta, eta)
            b10 = rc.weibull_bpercentile(beta, eta, 10)
            b1 = rc.weibull_bpercentile(beta, eta, 1)
            detail_box(f"MTTF(평균수명)   = {mttf:,.2f}\nB10 수명(F=10%) = {b10:,.2f}\nB1 수명(F=1%)   = {b1:,.2f}")
        else:
            detail_box("-")

        st.markdown("**임의 시점 신뢰도 계산**")
        with st.popover("ⓘ 왜 필요한가?"):
            st.text(
                "이 계산은 '시험을 얼마나 오래 했는지'와는 무관하게, 사용자가 알고 싶은\n"
                "특정 시점(t) 하나를 골라서 그 시점의 신뢰도를 계산해주는 기능입니다.\n\n"
                "예를 들어 시험 데이터를 1500시간까지 수집해 β/η을 추정해 놓은 상태에서:\n"
                "  · t=200을 입력하면 → '200시간 시점까지 생존할 확률'\n"
                "  · t=1500을 입력하면 → '시험 종료 시점까지 생존할 확률'\n"
                "  · t=87600(필드수명 10년)을 입력하면 → '실제 필드수명 시점에서의 예상 생존율'\n"
                "을 즉시 확인할 수 있습니다.\n\n"
                "실무에서는 초기불량 구간(짧은 t) 확인, 시험 통과 확률의 사후 검증(시험시간과 같은 t),\n"
                "그리고 필드 목표수명 시점의 신뢰도 예측(긴 t) 등의 용도로 가장 많이 사용합니다.\n\n"
                "※ 주의: t가 실제 관측한 데이터 범위를 크게 벗어나면(외삽, extrapolation)\n"
                "모델의 예측 오차가 커질 수 있으므로, 참고값으로만 활용하시기 바랍니다."
            )
        rt1, rt2 = st.columns([2, 1])
        t_query = rt1.number_input("임의 시점 t =", value=1000.0, step=10.0, key="t5_t_query",
                                    label_visibility="collapsed")
        rt_calc = rt2.button("계산", key="t5_rt_calc", disabled=(fr is None))
        if rt_calc and fr is not None:
            beta, eta = fr
            r_ = rc.weibull_reliability(t_query, beta, eta)
            f_ = 1 - r_
            h_ = rc.weibull_failure_rate(t_query, beta, eta)
            st.session_state["t5_rt_text"] = (
                f"R({t_query:g}) = {r_*100:.3f} %   (t시점까지 생존할 확률)\n"
                f"F({t_query:g}) = {f_*100:.3f} %   (t시점까지 고장날 확률)\n"
                f"h({t_query:g}) = {h_:.6f}   (t시점에서의 고장률)"
            )
        detail_box(st.session_state.get("t5_rt_text", "-"))

        st.markdown("**Weibull 확률도표**")
        if fr is not None:
            beta, eta = fr
            times = st.session_state.get("t5_times", [])
            is_failure = st.session_state.get("t5_is_failure", [])
            ranks = rc.weibull_rank_adjustment(times, is_failure)
            fig, ax = plt.subplots(figsize=(6.2, 4.4), dpi=100)
            if ranks:
                xs = [math.log(t) for t, _ in ranks]
                ys = [math.log(-math.log(1 - mr)) for _, mr in ranks]
                ax.scatter(xs, ys, color="#2f6fed", label="관측 데이터(고장)")
            tmin = min(times); tmax = max(times)
            t_line = [tmin * (tmax / tmin) ** (i / 50.0) if tmin > 0 else tmax * i / 50.0 for i in range(51)]
            x_line = [math.log(t) for t in t_line if t > 0]
            y_line = [beta * (math.log(t) - math.log(eta)) for t in t_line if t > 0]
            ax.plot(x_line, y_line, color="#e2483a", label=f"MLE 적합선 (β={beta:.2f}, η={eta:,.1f})")
            ax.set_xlabel("ln(시간)")
            ax.set_ylabel("ln(-ln(1-F))")
            ax.set_title("Weibull 확률도표")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
            fig.tight_layout()
            st.pyplot(fig)
        else:
            st.caption("적합을 실행하면 확률도표가 표시됩니다.")
