# -*- coding: utf-8 -*-
"""
app.py - 가속시험 통합계산기 (신뢰성분석) 웹앱
원본 데스크톱 프로그램(신뢰성분석.py)의 5개 탭 구조/입력값/버튼/공식을 그대로 재현합니다.
탭① 온도가속(Arrhenius) / 탭② 온습도가속(Arrhenius-Peck) / 탭③ 열피로가속(Thermal Cycling)
탭④ Weibull 시험시간비 계산기 / 탭⑤ 수명데이터 분석(Weibull MLE)
"""
import math
import pandas as pd
import streamlit as st

import reliability_calc as rc

st.set_page_config(page_title="가속시험 통합계산기", layout="wide")

# ------------------------------------------------------------------
# 공통 스타일 (원본 데스크톱의 결과박스/공식박스 색상 그대로)
# ------------------------------------------------------------------
st.markdown("""
<style>
.result-box{background:#eef2fb;color:#1a3fa0;font-weight:700;font-size:16px;
            padding:14px 16px;border-radius:6px;white-space:pre-wrap;line-height:1.55;
            min-height:60px;}
.detail-box{white-space:pre-wrap;font-size:13px;color:#333;padding:4px 2px;}
.formula-box{background:#f5f5f5;padding:12px 14px;border-radius:6px;white-space:pre-wrap;
             font-size:13px;line-height:1.6;color:#111;}
.warn-note{color:#a33;font-size:13px;margin-top:-6px;}
.gray-note{color:#555;font-size:13px;}
section[data-testid="stSidebar"]{display:none;}
</style>
""", unsafe_allow_html=True)

st.title("⚙️ 가속시험 통합계산기 (신뢰성분석)")


# ====================================================================
# 공통 유틸
# ====================================================================
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default


def result_box(text):
    st.markdown(f'<div class="result-box">{text}</div>', unsafe_allow_html=True)


def formula_box(title, text):
    st.markdown(f"**{title}**")
    st.markdown(f'<div class="formula-box">{text}</div>', unsafe_allow_html=True)


def condition_table(df, key):
    """조건 목록 표시 + 다중 선택(선택 삭제용) - st.dataframe 행 선택 기능 사용"""
    if df.empty:
        st.dataframe(df, use_container_width=True, height=180, key=key)
        return []
    event = st.dataframe(df, use_container_width=True, height=220, hide_index=True,
                          on_select="rerun", selection_mode="multi-row", key=key)
    try:
        return list(event.selection.rows)
    except Exception:
        return []


def fmt(v, nd=2):
    try:
        return f"{v:,.{nd}f}"
    except Exception:
        return str(v)


# ====================================================================
# 큰 모달(팝업) - 원본의 Toplevel 팝업을 큰 화면으로 재현
# ====================================================================
@st.dialog("활성화에너지 DB 검색", width="large")
def ea_db_dialog(target_key):
    st.caption("※ 목록에서 항목을 선택하고 [적용]을 누르면 활성화에너지(E) 입력칸에 자동으로 채워집니다.")
    kw = st.text_input("부품명 검색", key=f"{target_key}_ea_search")
    rows = rc.EA_DB
    if kw.strip():
        rows = [r for r in rows if kw.strip().lower() in r[0].lower()]
    df = pd.DataFrame(rows, columns=["부품", "활성화에너지(eV)", "출처", "비고"])
    st.dataframe(df, use_container_width=True, height=460, hide_index=True)
    options = [f"{r[0]}  |  {r[1]} eV" for r in rows]
    if options:
        sel = st.selectbox("적용할 항목 선택", options, key=f"{target_key}_ea_sel")
        idx = options.index(sel)
        if st.button("적용", type="primary", key=f"{target_key}_ea_apply"):
            ev_text = str(rows[idx][1]).split("~")[0].split("-")[0].replace("eV", "").strip()
            try:
                st.session_state[target_key] = str(float(ev_text))
                st.rerun()
            except ValueError:
                st.warning("이 항목은 단일 숫자값이 아니라 자동입력이 어렵습니다. 직접 입력해주세요.")
    else:
        st.info("검색 결과가 없습니다.")


@st.dialog("Coffin-Manson m지수 선정 가이드", width="large")
def m_guide_dialog():
    st.caption("※ 목록에서 항목을 선택하고 [적용]을 누르면 m지수 입력칸에 자동으로 채워집니다.")
    df = pd.DataFrame(rc.M_GUIDE_DB, columns=["재질/메커니즘", "m지수", "대상 부품(예)"])
    st.dataframe(df, use_container_width=True, height=260, hide_index=True)
    options = [f"{r[0]}  (m={r[1]})" for r in rc.M_GUIDE_DB]
    sel = st.selectbox("적용할 항목 선택", options, key="m_guide_sel")
    idx = options.index(sel)
    if st.button("적용", type="primary", key="m_guide_apply"):
        st.session_state["t3_m"] = str(rc.M_GUIDE_DB[idx][1])
        st.rerun()


@st.dialog("Weibull Beta/Eta 참고 DB", width="large")
def weibull_ref_dialog():
    st.caption("※ 재료/구조 파손 메커니즘별 형상모수(β)·척도모수(η) 참고 범위입니다. (참고용 조회 전용)")
    kw = st.text_input("부품명 검색", key="wb_ref_search")
    rows = rc.WEIBULL_DB
    if kw.strip():
        rows = [r for r in rows if kw.strip().lower() in r[1].lower()]
    df = pd.DataFrame(rows, columns=["분류", "항목", "Beta Low", "Beta Typ", "Beta High",
                                      "Eta Low", "Eta Typ", "Eta High"])
    st.dataframe(df, use_container_width=True, height=520, hide_index=True)


@st.dialog("설명", width="large")
def info_dialog(title, text):
    st.subheader(title)
    st.markdown(f'<div class="formula-box">{text}</div>', unsafe_allow_html=True)


# ====================================================================
# 탭① 온도가속 (Arrhenius)
# ====================================================================
def render_tab1():
    init_state("t1_conditions", [])
    init_state("t1_e", "0.8")
    init_state("t1_tref", "125")
    init_state("t1_ta", "100")
    init_state("t1_time", "200")
    init_state("t1_wb_apply", False)
    init_state("t1_r", "0.99"); init_state("t1_cl", "0.5")
    init_state("t1_n", "6"); init_state("t1_beta", "2")
    init_state("t1_result", "조건을 입력하고 [계산 실행]을 눌러주세요.")
    init_state("t1_detail", "")
    init_state("t1_last", None)

    left, right = st.columns([1, 3])
    with left:
        st.markdown("#### ① 온도가속 (Arrhenius Model)")
        st.markdown('<p class="warn-note">※ 사이클(열충격) 시험이 아닌, 단일 온도 유지 시험(정특성)에 적용합니다.</p>',
                     unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**입력값**")
            c1, c2 = st.columns([3, 1])
            st.session_state.t1_e = c1.text_input("활성화에너지 E (eV)", value=st.session_state.t1_e, key="t1_e_in")
            if c2.button("DB에서 찾기", key="t1_db_btn"):
                ea_db_dialog("t1_e")
            st.session_state.t1_tref = st.text_input("대표(목표) 온도 Tref (℃)", value=st.session_state.t1_tref, key="t1_tref_in")

        with st.container(border=True):
            st.markdown("**시험 조건 (온도 / 시간) 추가**")
            c1, c2, c3 = st.columns([1, 1, 1])
            st.session_state.t1_ta = c1.text_input("조건온도(℃)", value=st.session_state.t1_ta, key="t1_ta_in")
            st.session_state.t1_time = c2.text_input("조건시간(h)", value=st.session_state.t1_time, key="t1_time_in")
            c3.write("")
            if c3.button("추가 +", key="t1_add"):
                try:
                    ta = float(st.session_state.t1_ta); t = float(st.session_state.t1_time)
                    st.session_state.t1_conditions.append({"조건온도(℃)": ta, "조건시간(h)": t})
                except ValueError:
                    st.warning("조건온도/조건시간은 숫자로 입력해주세요.")

        with st.container(border=True):
            st.markdown("**조건 목록**")
            df = pd.DataFrame(st.session_state.t1_conditions)
            sel_rows = condition_table(df, key="t1_table")
            b1, b2 = st.columns(2)
            if b1.button("선택 삭제 🗑", key="t1_del_sel", use_container_width=True):
                for i in sorted(sel_rows, reverse=True):
                    del st.session_state.t1_conditions[i]
                st.rerun()
            if b2.button("전체 삭제", key="t1_del_all", use_container_width=True):
                st.session_state.t1_conditions = []
                st.rerun()

        with st.container(border=True):
            st.markdown("**Weibull 시험시간비 적용 (선택)**")
            st.session_state.t1_wb_apply = st.checkbox("적용", value=st.session_state.t1_wb_apply, key="t1_wb_chk")
            c1, c2 = st.columns(2)
            st.session_state.t1_r = c1.text_input("목표신뢰도 R", value=st.session_state.t1_r, key="t1_r_in")
            st.session_state.t1_cl = c2.text_input("신뢰수준 CL", value=st.session_state.t1_cl, key="t1_cl_in")
            c3, c4 = st.columns(2)
            st.session_state.t1_n = c3.text_input("샘플수 n", value=st.session_state.t1_n, key="t1_n_in")
            st.session_state.t1_beta = c4.text_input("형상모수 β", value=st.session_state.t1_beta, key="t1_beta_in")

        c1, c2 = st.columns(2)
        calc_clicked = c1.button("계산 실행 ▶", type="primary", use_container_width=True, key="t1_calc")
        export_clicked = c2.button("엑셀로 내보내기 📊", use_container_width=True, key="t1_export")

    with right:
        st.markdown("#### 결과")
        result_ph = st.empty()
        result_ph.markdown(f'<div class="result-box">{st.session_state.t1_result}</div>', unsafe_allow_html=True)

        formula_box("계산 공식 (Arrhenius Model)",
            "AF = exp[ (E / k) x (1/Tu - 1/Ta) ]\n\n"
            "여기서  AF : 가속계수\n"
            "        E  : 활성화에너지 (eV)\n"
            "        k  : Boltzmann 상수 (8.6173e-05 eV/K)\n"
            "        Tu : 사용(필드) 온도 (K)\n"
            "        Ta : 가속(시험) 온도 (K)\n\n"
            "등가시험시간 = 조건시간 / AF  (조건온도 -&gt; Tref 로 환산)\n"
            "최종 가속시험시간 = 등가시험시간 합계 x Weibull 시험시간비")
        st.markdown(f'<div class="detail-box">{st.session_state.t1_detail}</div>', unsafe_allow_html=True)

    if calc_clicked:
        conds = st.session_state.t1_conditions
        if not conds:
            st.warning("조건을 1개 이상 추가해주세요.")
        else:
            try:
                E = float(st.session_state.t1_e); Tref = float(st.session_state.t1_tref)
            except ValueError:
                st.warning("E, Tref는 숫자로 입력해주세요."); st.stop()
            rows = []; total = 0.0
            for c in conds:
                ta, t = c["조건온도(℃)"], c["조건시간(h)"]
                af = rc.arrhenius_af(Tref, ta, E)
                eq = t * af
                total += eq
                rows.append((ta, t, af, eq))
            final_time = total; ratio = None
            if st.session_state.t1_wb_apply:
                try:
                    R = float(st.session_state.t1_r); CL = float(st.session_state.t1_cl)
                    n = float(st.session_state.t1_n); beta = float(st.session_state.t1_beta)
                    ratio = rc.weibull_test_time_ratio(R, CL, n, beta)
                    final_time = total * ratio
                except (ValueError, ZeroDivisionError):
                    st.warning("Weibull 파라미터를 확인해주세요."); st.stop()
            lines = [f"총 등가시험시간(@{Tref:.1f}℃) = {fmt(total)} h  ({fmt(total/24)} 일)"]
            if ratio is not None:
                lines.append(f"Weibull 시험시간비 = {ratio:.4f}")
                lines.append(f"최종 가속시험시간 = {fmt(final_time)} h  ({fmt(final_time/24)} 일)")
            st.session_state.t1_result = "\n".join(lines)
            detail = ["[조건별 상세]"]
            for ta, t, af, eq in rows:
                detail.append(f"  {ta:.1f}℃ / {t:.1f}h  -&gt;  AF={af:,.3f}   등가시간={eq:,.2f}h")
            st.session_state.t1_detail = "\n".join(detail)
            st.session_state.t1_last = dict(rows=rows, total=total, ratio=ratio, final=final_time,
                                             tref=Tref, E=E)
            st.rerun()

    if export_clicked:
        last = st.session_state.t1_last
        if not last:
            st.warning("먼저 [계산 실행]을 눌러주세요.")
        else:
            out = pd.DataFrame(last["rows"], columns=["조건온도(℃)", "조건시간(h)", "가속계수 AF", "등가시간(h)"])
            buf = _to_excel_bytes({"온도가속(Arrhenius)": out}, extra=[
                ("활성화에너지 E(eV)", last["E"]), ("대표(목표)온도 Tref(℃)", last["tref"]),
                ("총 등가시험시간(h)", last["total"])] + (
                [("Weibull 시험시간비", last["ratio"]), ("최종 가속시험시간(h)", last["final"])]
                if last["ratio"] is not None else []))
            st.download_button("⬇ 엑셀 파일 다운로드", buf, file_name="온도가속_계산결과.xlsx", key="t1_dl")


def _to_excel_bytes(sheets: dict, extra=None):
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False, startrow=3 if extra else 0)
            if extra:
                ws = writer.sheets[name[:31]]
                for i, (k, v) in enumerate(extra, start=1):
                    ws.cell(row=i, column=1, value=k)
                    ws.cell(row=i, column=2, value=v)
    buf.seek(0)
    return buf


# ====================================================================
# 탭② 온습도가속 (Arrhenius-Peck)
# ====================================================================
def render_tab2():
    init_state("t2_conditions", [])
    init_state("t2_e", "0.79"); init_state("t2_n", "2.66")
    init_state("t2_tu", "23"); init_state("t2_hu", "65")
    init_state("t2_ta", "85"); init_state("t2_ha", "85"); init_state("t2_t", "303")
    init_state("t2_wb_apply", False)
    init_state("t2_r", "0.99"); init_state("t2_cl", "0.5")
    init_state("t2_ns", "6"); init_state("t2_beta", "2")
    init_state("t2_result", "조건을 입력하고 [계산 실행]을 눌러주세요.")
    init_state("t2_detail", "")
    init_state("t2_last", None)

    left, right = st.columns([1, 3])
    with left:
        st.markdown("#### ② 온습도가속 (Arrhenius-Peck Model)")

        with st.container(border=True):
            st.markdown("**입력값**")
            c1, c2 = st.columns([3, 1])
            st.session_state.t2_e = c1.text_input("활성화에너지 E (eV)", value=st.session_state.t2_e, key="t2_e_in")
            if c2.button("DB", key="t2_db_btn"):
                ea_db_dialog("t2_e")
            st.session_state.t2_n = st.text_input("습도항 지수 n", value=st.session_state.t2_n, key="t2_n_in")
            c1, c2 = st.columns(2)
            st.session_state.t2_tu = c1.text_input("사용(필드) 온도 Tu(℃)", value=st.session_state.t2_tu, key="t2_tu_in")
            st.session_state.t2_hu = c2.text_input("사용(필드) 습도 Hu(%RH)", value=st.session_state.t2_hu, key="t2_hu_in")

        with st.container(border=True):
            st.markdown("**가속시험 조건 (온도 / 습도 / 시간) 추가**")
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            st.session_state.t2_ta = c1.text_input("가속온도(℃)", value=st.session_state.t2_ta, key="t2_ta_in")
            st.session_state.t2_ha = c2.text_input("가속습도(%RH)", value=st.session_state.t2_ha, key="t2_ha_in")
            st.session_state.t2_t = c3.text_input("시간(h)", value=st.session_state.t2_t, key="t2_t_in")
            c4.write("")
            if c4.button("추가 +", key="t2_add"):
                try:
                    ta = float(st.session_state.t2_ta); ha = float(st.session_state.t2_ha); t = float(st.session_state.t2_t)
                    st.session_state.t2_conditions.append({"가속온도(℃)": ta, "가속습도(%RH)": ha, "시간(h)": t})
                except ValueError:
                    st.warning("숫자로 입력해주세요.")

        with st.container(border=True):
            st.markdown("**조건 목록**")
            df = pd.DataFrame(st.session_state.t2_conditions)
            sel_rows = condition_table(df, key="t2_table")
            b1, b2 = st.columns(2)
            if b1.button("선택 삭제 🗑", key="t2_del_sel", use_container_width=True):
                for i in sorted(sel_rows, reverse=True):
                    del st.session_state.t2_conditions[i]
                st.rerun()
            if b2.button("전체 삭제", key="t2_del_all", use_container_width=True):
                st.session_state.t2_conditions = []
                st.rerun()

        with st.container(border=True):
            st.markdown("**Weibull 시험시간비 적용 (선택)**")
            st.session_state.t2_wb_apply = st.checkbox("적용", value=st.session_state.t2_wb_apply, key="t2_wb_chk")
            c1, c2 = st.columns(2)
            st.session_state.t2_r = c1.text_input("목표신뢰도 R", value=st.session_state.t2_r, key="t2_r_in")
            st.session_state.t2_cl = c2.text_input("신뢰수준 CL", value=st.session_state.t2_cl, key="t2_cl_in")
            c3, c4 = st.columns(2)
            st.session_state.t2_ns = c3.text_input("샘플수 n", value=st.session_state.t2_ns, key="t2_ns_in")
            st.session_state.t2_beta = c4.text_input("형상모수 β", value=st.session_state.t2_beta, key="t2_beta_in")

        c1, c2 = st.columns(2)
        calc_clicked = c1.button("계산 실행 ▶", type="primary", use_container_width=True, key="t2_calc")
        export_clicked = c2.button("엑셀로 내보내기 📊", use_container_width=True, key="t2_export")

    with right:
        st.markdown("#### 결과")
        st.markdown(f'<div class="result-box">{st.session_state.t2_result}</div>', unsafe_allow_html=True)
        formula_box("계산 공식 (Arrhenius-Peck Model)",
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
            "최종 가속시험시간 = 등가시험시간 합계 x Weibull 시험시간비")
        st.markdown(f'<div class="detail-box">{st.session_state.t2_detail}</div>', unsafe_allow_html=True)

    if calc_clicked:
        conds = st.session_state.t2_conditions
        if not conds:
            st.warning("조건을 1개 이상 추가해주세요.")
        else:
            try:
                E = float(st.session_state.t2_e); n = float(st.session_state.t2_n)
                Tu = float(st.session_state.t2_tu); Hu = float(st.session_state.t2_hu)
            except ValueError:
                st.warning("숫자로 입력해주세요."); st.stop()
            rows = []; total = 0.0
            for c in conds:
                ta, ha, t = c["가속온도(℃)"], c["가속습도(%RH)"], c["시간(h)"]
                af = rc.peck_af(Tu, Hu, ta, ha, E, n)
                eq = t * af
                total += eq
                rows.append((ta, ha, t, af, eq))
            final_time = total; ratio = None
            if st.session_state.t2_wb_apply:
                try:
                    R = float(st.session_state.t2_r); CL = float(st.session_state.t2_cl)
                    ns = float(st.session_state.t2_ns); beta = float(st.session_state.t2_beta)
                    ratio = rc.weibull_test_time_ratio(R, CL, ns, beta)
                    final_time = total * ratio
                except (ValueError, ZeroDivisionError):
                    st.warning("Weibull 파라미터를 확인해주세요."); st.stop()
            lines = [f"총 등가시험시간(@{Tu:.1f}℃/{Hu:.1f}%RH 기준) = {fmt(total)} h  ({fmt(total/24)} 일)"]
            if ratio is not None:
                lines.append(f"Weibull 시험시간비 = {ratio:.4f}")
                lines.append(f"최종 가속시험시간 = {fmt(final_time)} h  ({fmt(final_time/24)} 일)")
            st.session_state.t2_result = "\n".join(lines)
            detail = ["[조건별 상세]"]
            for ta, ha, t, af, eq in rows:
                detail.append(f"  {ta:.1f}℃/{ha:.1f}%RH / {t:.1f}h  -&gt;  AF={af:,.2f}   등가시간={eq:,.2f}h")
            st.session_state.t2_detail = "\n".join(detail)
            st.session_state.t2_last = dict(rows=rows, total=total, ratio=ratio, final=final_time,
                                             Tu=Tu, Hu=Hu, E=E, n=n)
            st.rerun()

    if export_clicked:
        last = st.session_state.t2_last
        if not last:
            st.warning("먼저 [계산 실행]을 눌러주세요.")
        else:
            out = pd.DataFrame(last["rows"], columns=["가속온도(℃)", "가속습도(%RH)", "시간(h)", "AF", "등가시간(h)"])
            buf = _to_excel_bytes({"온습도가속(Peck)": out}, extra=[
                ("E(eV)", last["E"]), ("n", last["n"]), ("Tu(℃)", last["Tu"]), ("Hu(%RH)", last["Hu"]),
                ("총 등가시험시간(h)", last["total"])] + (
                [("Weibull 시험시간비", last["ratio"]), ("최종 가속시험시간(h)", last["final"])]
                if last["ratio"] is not None else []))
            st.download_button("⬇ 엑셀 파일 다운로드", buf, file_name="온습도가속_계산결과.xlsx", key="t2_dl")


# ====================================================================
# 탭③ 열피로가속 (Thermal Cycling)
# ====================================================================
PROFILE_ROWS = [("low", "저온(℃)"), ("low_dwell", "저온유지시간(분)"), ("ramp_up", "승온시간(분, 저온→고온)"),
                 ("high", "고온(℃)"), ("high_dwell", "고온유지시간(분)"), ("ramp_down", "하강시간(분, 고온→저온)")]


def _profile_group(prefix, title, defaults, with_target=False):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        for key, label in PROFILE_ROWS:
            sk = f"{prefix}_{key}"
            init_state(sk, str(defaults.get(key, "")))
            st.session_state[sk] = st.text_input(label, value=st.session_state[sk], key=f"{sk}_in")
        if with_target:
            sk = f"{prefix}_target_cycle"
            init_state(sk, str(defaults.get("target_cycle", 1000)))
            st.session_state[sk] = st.text_input("필드 목표 사이클수", value=st.session_state[sk], key=f"{sk}_in")


def render_tab3():
    init_state("t3_model", "coffin")
    init_state("t3_m", "2.5")
    init_state("t3_wb_apply", False)
    init_state("t3_r", "0.99"); init_state("t3_cl", "0.5")
    init_state("t3_ns", "6"); init_state("t3_beta", "2")
    init_state("t3_result", "프로파일을 입력하고 [계산 실행]을 눌러주세요.")
    init_state("t3_last", None)

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### ③ 열피로가속 (Thermal Cycling)")
        st.markdown('<p class="warn-note">※ 챔버 승온형 온도사이클(Thermal Cycling) 전용입니다. '
                     '(엘리베이터형 Thermal Shock 시험은 전환시간이 거의 0으로, 별도 모델이 필요합니다)</p>',
                     unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            _profile_group("t3_field", "사용조건(필드) 사이클 프로파일",
                            dict(low=-40, low_dwell=10, ramp_up=30, high=85, high_dwell=10, ramp_down=30,
                                 target_cycle=1000), with_target=True)
        with c2:
            _profile_group("t3_test", "시험조건 사이클 프로파일",
                            dict(low=-40, low_dwell=10, ramp_up=30, high=125, high_dwell=40, ramp_down=10))

        st.markdown('<p class="gray-note">예) -40℃(30분) ↔ 125℃(30분), 승온/하강 각 10분  형태로 입력하시면 됩니다.</p>',
                     unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**가속 모델 선택**")
            gc1, gc2 = st.columns([1, 1])
            with gc1:
                st.session_state.t3_model = st.radio("모델", ["coffin", "norris"],
                    format_func=lambda v: "Coffin-Manson (단순, ΔT만 반영)" if v == "coffin"
                                            else "Modified Norris-Landzberg (정밀, dwell/ramp/온도 반영)",
                    index=0 if st.session_state.t3_model == "coffin" else 1,
                    key="t3_model_radio", label_visibility="collapsed")
                mc1, mc2 = st.columns([1, 1])
                st.session_state.t3_m = mc1.text_input("m지수", value=st.session_state.t3_m, key="t3_m_in")
                if mc2.button("m지수 가이드", key="t3_mguide_btn"):
                    m_guide_dialog()
            with gc2:
                st.markdown("**언제 어떤 모델을 써야 하나요?**")
                st.markdown(f'<div class="formula-box">{rc.MODEL_GUIDE_TEXT}</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**Weibull 시험시간비 적용 (선택)**")
            st.session_state.t3_wb_apply = st.checkbox("적용", value=st.session_state.t3_wb_apply, key="t3_wb_chk")
            c1, c2 = st.columns(2)
            st.session_state.t3_r = c1.text_input("목표신뢰도 R", value=st.session_state.t3_r, key="t3_r_in")
            st.session_state.t3_cl = c2.text_input("신뢰수준 CL", value=st.session_state.t3_cl, key="t3_cl_in")
            c3, c4 = st.columns(2)
            st.session_state.t3_ns = c3.text_input("샘플수 n", value=st.session_state.t3_ns, key="t3_ns_in")
            st.session_state.t3_beta = c4.text_input("형상모수 β", value=st.session_state.t3_beta, key="t3_beta_in")

        c1, c2 = st.columns(2)
        calc_clicked = c1.button("계산 실행 ▶", type="primary", use_container_width=True, key="t3_calc")
        export_clicked = c2.button("엑셀로 내보내기 📊", use_container_width=True, key="t3_export")

    with right:
        st.markdown("#### 결과")
        st.markdown(f'<div class="result-box">{st.session_state.t3_result}</div>', unsafe_allow_html=True)
        if st.session_state.t3_model == "coffin":
            txt = ("[Coffin-Manson Model]\n\n"
                   "AF = ( ΔT_test / ΔT_field ) ^ m\n\n"
                   "여기서  AF : 가속계수\n"
                   "        ΔT : 온도변화폭(사이클 최고온도-최저온도)\n"
                   "        m  : 재료/구조에 따른 경험적 지수 (보통 1.9~5)\n\n"
                   "필요 시험 사이클수 = 필드 목표 사이클수 / AF\n"
                   "1cycle 시간 = 저온유지 + 승온시간 + 고온유지 + 하강시간\n"
                   "총 소요시간 = 필요 시험 사이클수 x 1cycle 시간")
        else:
            txt = ("[Modified Norris-Landzberg Model]\n\n"
                   "AF = (ΔT_test/ΔT_field)^2.65\n"
                   "     x (Dwell_test/Dwell_field)^0.136\n"
                   "     x (1.22 x RampRate_test^-0.0757)\n"
                   "     x exp[2185 x (1/Tmax_field(K) - 1/Tmax_test(K))]\n\n"
                   "여기서  Dwell : 고온유지시간,  RampRate : 승온속도(℃/분)\n"
                   "        Tmax  : 사이클 최고온도(K)\n"
                   "        (계수 n=2.65, m=0.136, Ea/k=2185 는 Pb-free 솔더 접합 문헌 기준 근사값)\n\n"
                   "필요 시험 사이클수 = 필드 목표 사이클수 / AF\n"
                   "1cycle 시간 = 저온유지 + 승온시간 + 고온유지 + 하강시간\n"
                   "총 소요시간 = 필요 시험 사이클수 x 1cycle 시간")
        formula_box("계산 공식", txt)

    if calc_clicked:
        try:
            field = {k: float(st.session_state[f"t3_field_{k}"]) for k, _ in PROFILE_ROWS}
            field["target_cycle"] = float(st.session_state["t3_field_target_cycle"])
            test = {k: float(st.session_state[f"t3_test_{k}"]) for k, _ in PROFILE_ROWS}
        except ValueError:
            st.warning("프로파일 값을 모두 숫자로 입력해주세요."); st.stop()

        dT_field = abs(field["high"] - field["low"])
        dT_test = abs(test["high"] - test["low"])
        cycle_time_field = rc.profile_cycle_time_min(field["low_dwell"], field["ramp_up"], field["high_dwell"], field["ramp_down"])
        cycle_time_test = rc.profile_cycle_time_min(test["low_dwell"], test["ramp_up"], test["high_dwell"], test["ramp_down"])

        if st.session_state.t3_model == "coffin":
            try:
                m = float(st.session_state.t3_m)
            except ValueError:
                st.warning("m지수를 숫자로 입력해주세요."); st.stop()
            af = rc.coffin_manson_af(dT_field, dT_test, m)
        else:
            ramp_test_rate = dT_test / test["ramp_up"] if test["ramp_up"] > 0 else 0.0001
            af = rc.norris_landzberg_af(dT_field, dT_test, field["high_dwell"], test["high_dwell"],
                                          ramp_test_rate, field["high"], test["high"])

        target_cycle = field.get("target_cycle", 0)
        need_cycle = target_cycle / af if af > 0 else float("inf")
        total_min = need_cycle * cycle_time_test
        total_hour = total_min / 60
        total_day = total_hour / 24

        final_cycle = need_cycle; final_min = total_min; ratio = None
        if st.session_state.t3_wb_apply:
            try:
                R = float(st.session_state.t3_r); CL = float(st.session_state.t3_cl)
                ns = float(st.session_state.t3_ns); beta = float(st.session_state.t3_beta)
                ratio = rc.weibull_test_time_ratio(R, CL, ns, beta)
                final_cycle = need_cycle * ratio
                final_min = final_cycle * cycle_time_test
            except (ValueError, ZeroDivisionError):
                st.warning("Weibull 파라미터를 확인해주세요."); st.stop()

        lines = [
            f"ΔT(필드/시험) = {dT_field:.1f}℃ / {dT_test:.1f}℃",
            f"1cycle 시간(필드/시험) = {cycle_time_field:.1f}분 / {cycle_time_test:.1f}분",
            "",
            f"가속계수 AF = {af:,.3f}",
            f"필요 시험 사이클수 = {fmt(need_cycle)} cycle",
            f"총 소요시간 = {total_min:,.1f}분 = {fmt(total_hour)}시간 = {fmt(total_day)}일",
        ]
        if ratio is not None:
            lines.append("")
            lines.append(f"Weibull 시험시간비 = {ratio:.4f}")
            lines.append(f"최종 가속시험 사이클수 = {fmt(final_cycle)} cycle "
                         f"({fmt(final_min/60)}시간 = {fmt(final_min/60/24)}일)")
        st.session_state.t3_result = "\n".join(lines)
        st.session_state.t3_last = dict(dT_field=dT_field, dT_test=dT_test, af=af, need_cycle=need_cycle,
                                          cycle_time_test=cycle_time_test, total_hour=total_hour, total_day=total_day,
                                          ratio=ratio, final_cycle=final_cycle, final_hour=final_min/60,
                                          model=st.session_state.t3_model)
        st.rerun()

    if export_clicked:
        last = st.session_state.t3_last
        if not last:
            st.warning("먼저 [계산 실행]을 눌러주세요.")
        else:
            rows = [("모델", "Coffin-Manson" if last["model"] == "coffin" else "Modified Norris-Landzberg"),
                    ("ΔT_field(℃)", last["dT_field"]), ("ΔT_test(℃)", last["dT_test"]),
                    ("가속계수 AF", last["af"]), ("필요 시험 사이클수", last["need_cycle"]),
                    ("1cycle 시험시간(분)", last["cycle_time_test"]),
                    ("총 소요시간(시간)", last["total_hour"]), ("총 소요시간(일)", last["total_day"])]
            if last["ratio"] is not None:
                rows += [("Weibull 시험시간비", last["ratio"]), ("최종 가속시험 사이클수", last["final_cycle"]),
                         ("최종 가속시험시간(시간)", last["final_hour"])]
            out = pd.DataFrame(rows, columns=["항목", "값"])
            buf = _to_excel_bytes({"열피로가속": out})
            st.download_button("⬇ 엑셀 파일 다운로드", buf, file_name="열피로가속_계산결과.xlsx", key="t3_dl")


# ====================================================================
# 탭④ Weibull 시험시간비 계산기
# ====================================================================
def render_tab4():
    init_state("t4_r", "0.99"); init_state("t4_cl", "0.5")
    init_state("t4_n", "6"); init_state("t4_beta", "2")
    init_state("t4_result", "값을 입력하고 [계산 실행]을 눌러주세요.")

    left, right = st.columns([1, 3])
    with left:
        st.markdown("#### ④ Weibull 시험시간비 계산기")
        with st.container(border=True):
            st.markdown("**입력값**")
            st.session_state.t4_r = st.text_input("목표신뢰도 R", value=st.session_state.t4_r, key="t4_r_in")
            st.session_state.t4_cl = st.text_input("신뢰수준 CL", value=st.session_state.t4_cl, key="t4_cl_in")
            st.session_state.t4_n = st.text_input("샘플수 n", value=st.session_state.t4_n, key="t4_n_in")
            st.session_state.t4_beta = st.text_input("형상모수 β", value=st.session_state.t4_beta, key="t4_beta_in")

        if st.button("Beta 참고DB 열기", use_container_width=True, key="t4_refdb_btn"):
            weibull_ref_dialog()
        calc_clicked = st.button("계산 실행 ▶", type="primary", use_container_width=True, key="t4_calc")

    with right:
        st.markdown("#### 결과")
        st.markdown(f'<div class="result-box">{st.session_state.t4_result}</div>', unsafe_allow_html=True)
        formula_box("계산 공식",
            "시험시간비 = [ (-ln CL) / (n x -ln R) ] ^ (1/β)\n\n"
            "최종 가속시험시간(또는 사이클수) = 등가시험시간(사이클수) x 시험시간비")

    if calc_clicked:
        try:
            R = float(st.session_state.t4_r); CL = float(st.session_state.t4_cl)
            n = float(st.session_state.t4_n); beta = float(st.session_state.t4_beta)
            ratio = rc.weibull_test_time_ratio(R, CL, n, beta)
        except (ValueError, ZeroDivisionError):
            st.warning("값을 확인해주세요."); st.stop()
        st.session_state.t4_result = f"시험시간비 = {ratio:.4f}"
        st.rerun()


# ====================================================================
# 탭⑤ 수명데이터 분석 (Weibull)
# ====================================================================
def render_tab5():
    init_state("t5_rows", [])  # (time, is_failure)
    init_state("t5_time", "")
    init_state("t5_status", "고장")
    init_state("t5_result", "데이터를 입력하고 [Weibull 적합(MLE) 실행]을 눌러주세요. (고장 데이터 2개 이상 필요)")
    init_state("t5_mttf", "-")
    init_state("t5_rt", "-")
    init_state("t5_t", "1000")
    init_state("t5_fit", None)

    left, right = st.columns([1, 3])
    with left:
        st.markdown("#### ⑤ 수명데이터 분석 (Weibull)")
        with st.container(border=True):
            st.markdown("**고장/미고장 데이터 입력**")
            c1, c2, c3 = st.columns([1, 1, 1])
            st.session_state.t5_time = c1.text_input("시간(h 또는 cycle)", value=st.session_state.t5_time, key="t5_time_in")
            st.session_state.t5_status = c2.radio("상태", ["고장", "미고장"],
                index=0 if st.session_state.t5_status == "고장" else 1, key="t5_status_in", horizontal=True)
            c3.write("")
            if c3.button("추가 +", key="t5_add"):
                try:
                    t = float(st.session_state.t5_time)
                    if t <= 0:
                        raise ValueError
                    st.session_state.t5_rows.append((t, st.session_state.t5_status == "고장"))
                    st.session_state.t5_time = ""
                    st.rerun()
                except ValueError:
                    st.warning("시간을 올바르게 입력해주세요. (0보다 큰 값)")
            st.markdown('<p class="gray-note">※ 미고장 = 관찰(시험) 종료 시점까지 고장이 발생하지 않은 데이터</p>',
                         unsafe_allow_html=True)

            df = pd.DataFrame([{"시간": f"{t:.2f}", "상태": "고장" if f else "미고장"} for t, f in st.session_state.t5_rows])
            sel_rows = condition_table(df, key="t5_table")
            b1, b2, b3 = st.columns(3)
            if b1.button("선택 삭제", key="t5_del_sel", use_container_width=True):
                for i in sorted(sel_rows, reverse=True):
                    del st.session_state.t5_rows[i]
                st.rerun()
            if b2.button("전체 삭제", key="t5_del_all", use_container_width=True):
                st.session_state.t5_rows = []
                st.rerun()
            if b3.button("예시데이터 불러오기", key="t5_example", use_container_width=True):
                example = [(185, True), (260, True), (312, True), (355, True), (398, True),
                           (430, True), (470, True), (520, True), (610, True),
                           (700, False), (700, False), (700, False), (700, False), (700, False), (700, False)]
                st.session_state.t5_rows = example
                st.rerun()

        fit_clicked = st.button("Weibull 적합(MLE) 실행 ▶", type="primary", use_container_width=True, key="t5_fit_btn")
        export_clicked = st.button("엑셀로 내보내기", use_container_width=True, key="t5_export")

    with right:
        st.markdown("#### 적합 결과")
        st.markdown(f'<div class="result-box">{st.session_state.t5_result}</div>', unsafe_allow_html=True)

        if st.button("이 β값을 ④ Weibull 탭으로 보내기 →", key="t5_send_beta"):
            if st.session_state.t5_fit is None:
                st.warning("먼저 [Weibull 적합(MLE) 실행]을 눌러주세요.")
            else:
                beta, eta = st.session_state.t5_fit
                st.session_state["t4_beta"] = f"{beta:.4f}"
                st.session_state["_active_tab"] = 3
                st.success(f"β = {beta:.4f} 값을 ④ Weibull 시험시간비 탭으로 보냈습니다.")
                st.rerun()

        c1, c2 = st.columns([5, 1])
        c1.markdown("**대표수명 지표 (MTTF / B10 / B1)**")
        if c2.button("ⓘ", key="t5_mttf_info"):
            info_dialog("MTTF / B10 / B1 수명 - 왜 필요한가?",
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
                "  안전과 직결되는 부품이나 높은 신뢰성이 요구되는 부품에 사용합니다.")
        st.markdown(f'<div class="detail-box">{st.session_state.t5_mttf}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns([5, 1])
        c1.markdown("**임의 시점 신뢰도 계산**")
        if c2.button("ⓘ", key="t5_rt_info"):
            info_dialog("임의 시점 신뢰도 계산 - 왜 필요한가?",
                "이 계산은 '시험을 얼마나 오래 했는지'와는 무관하게, 사용자가 알고 싶은\n"
                "특정 시점(t) 하나를 골라서 그 시점의 신뢰도를 계산해주는 기능입니다.\n\n"
                "예를 들어 시험 데이터를 1500시간까지 수집해 β/η을 추정해 놓은 상태에서:\n"
                "  · t=200을 입력하면 → '200시간 시점까지 생존할 확률'\n"
                "  · t=1500을 입력하면 → '시험 종료 시점까지 생존할 확률'\n"
                "  · t=87600(필드수명 10년)을 입력하면 → '실제 필드수명 시점에서의 예상 생존율'\n"
                "을 즉시 확인할 수 있습니다.")
        rc1, rc2 = st.columns([2, 1])
        st.session_state.t5_t = rc1.text_input("임의 시점 t =", value=st.session_state.t5_t, key="t5_t_in")
        rt_clicked = rc2.button("계산", key="t5_rt_calc")
        st.markdown(f'<div class="detail-box">{st.session_state.t5_rt}</div>', unsafe_allow_html=True)

        st.markdown("**Weibull 확률도표**")
        plot_ph = st.empty()

    if fit_clicked:
        rows = st.session_state.t5_rows
        if len(rows) < 3:
            st.warning("데이터를 3개 이상 입력해주세요 (고장 데이터 2개 이상 포함).")
        else:
            times = [r[0] for r in rows]; is_failure = [r[1] for r in rows]
            n_fail = sum(is_failure)
            if n_fail < 2:
                st.warning("고장(Failure) 데이터가 2개 이상 필요합니다.")
            else:
                result = rc.fit_weibull_mle(times, is_failure)
                if result is None:
                    st.warning("Weibull 적합에 실패했습니다. 데이터를 확인해주세요.")
                else:
                    beta, eta = result
                    st.session_state.t5_fit = (beta, eta)
                    if beta < 1.0:
                        interp = "β<1 : 초기고장(Infant Mortality) 특성 - 시간이 지날수록 고장률이 감소"
                    elif beta < 1.3:
                        interp = "β≈1 : 우발고장(Random Failure) 특성 - 고장률이 시간과 거의 무관"
                    else:
                        interp = "β>1 : 마모성고장(Wear-out) 특성 - 시간이 지날수록 고장률이 증가"
                    n_total = len(rows)
                    st.session_state.t5_result = (
                        f"형상모수 β = {beta:.4f}   척도모수 η = {eta:,.2f}\n"
                        f"(총 {n_total}개 데이터 : 고장 {n_fail}개 / 미고장 {n_total - n_fail}개)\n"
                        f"{interp}")
                    mttf = rc.weibull_mttf(beta, eta)
                    b10 = rc.weibull_bpercentile(beta, eta, 10)
                    b1 = rc.weibull_bpercentile(beta, eta, 1)
                    st.session_state.t5_mttf = (
                        f"MTTF(평균수명)   = {mttf:,.2f}\n"
                        f"B10 수명(F=10%) = {b10:,.2f}\n"
                        f"B1 수명(F=1%)   = {b1:,.2f}")
                    st.rerun()

    if rt_clicked:
        if st.session_state.t5_fit is None:
            st.warning("먼저 [Weibull 적합(MLE) 실행]을 눌러주세요.")
        else:
            try:
                t = float(st.session_state.t5_t)
                if t <= 0:
                    raise ValueError
                beta, eta = st.session_state.t5_fit
                r = rc.weibull_reliability(t, beta, eta)
                f = 1 - r
                h = rc.weibull_failure_rate(t, beta, eta)
                st.session_state.t5_rt = (
                    f"R({t:g}) = {r*100:.3f} %   (t시점까지 생존할 확률)\n"
                    f"F({t:g}) = {f*100:.3f} %   (t시점까지 고장날 확률)\n"
                    f"h({t:g}) = {h:.6f}   (t시점에서의 고장률)")
                st.rerun()
            except ValueError:
                st.warning("시점 t를 올바르게 입력해주세요.")

    # 확률도표 (있으면 그림)
    if st.session_state.t5_fit is not None and st.session_state.t5_rows:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        beta, eta = st.session_state.t5_fit
        times = [r[0] for r in st.session_state.t5_rows]
        is_failure = [r[1] for r in st.session_state.t5_rows]
        ranks = rc.weibull_rank_adjustment(times, is_failure)
        fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=90)
        if ranks:
            xs = [math.log(t) for t, _ in ranks]
            ys = [math.log(-math.log(1 - mr)) for _, mr in ranks]
            ax.scatter(xs, ys, color="#2f6fed", label="관측 데이터(고장)")
        tmin = min(times); tmax = max(times)
        t_line = [tmin * (tmax / tmin) ** (i / 50.0) if tmin > 0 else tmax * i / 50.0 for i in range(51)]
        x_line = [math.log(t) for t in t_line if t > 0]
        y_line = [beta * (math.log(t) - math.log(eta)) for t in t_line if t > 0]
        ax.plot(x_line, y_line, color="#e2483a", label=f"MLE 적합선 (β={beta:.2f}, η={eta:,.1f})")
        ax.set_xlabel("ln(시간)"); ax.set_ylabel("ln(-ln(1-F))")
        ax.set_title("Weibull 확률도표"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
        fig.tight_layout()
        plot_ph.pyplot(fig)
    else:
        plot_ph.info("적합을 실행하면 확률도표가 표시됩니다.")

    if export_clicked:
        rows = st.session_state.t5_rows
        if not rows:
            st.warning("입력된 데이터가 없습니다.")
        else:
            df1 = pd.DataFrame([(t, "고장" if f else "미고장") for t, f in rows], columns=["시간", "상태"])
            fit_rows = []
            if st.session_state.t5_fit is not None:
                beta, eta = st.session_state.t5_fit
                fit_rows = [("형상모수 β", beta), ("척도모수 η", eta),
                            ("MTTF(평균수명)", rc.weibull_mttf(beta, eta)),
                            ("B10 수명", rc.weibull_bpercentile(beta, eta, 10)),
                            ("B1 수명", rc.weibull_bpercentile(beta, eta, 1))]
            else:
                fit_rows = [("안내", "적합을 먼저 실행해주세요.")]
            df2 = pd.DataFrame(fit_rows, columns=["항목", "값"])
            buf = _to_excel_bytes({"수명데이터": df1, "적합결과": df2})
            st.download_button("⬇ 엑셀 파일 다운로드", buf, file_name="수명데이터분석_결과.xlsx", key="t5_dl")


# ====================================================================
# 메인
# ====================================================================
def main():
    tab_labels = [" ① 온도가속(Arrhenius) ", " ② 온습도가속(Arrhenius-Peck) ",
                  " ③ 열피로가속(Thermal Cycling) ", " ④ Weibull 시험시간비 ", " ⑤ 수명데이터 분석 "]
    tabs = st.tabs(tab_labels)
    with tabs[0]:
        render_tab1()
    with tabs[1]:
        render_tab2()
    with tabs[2]:
        render_tab3()
    with tabs[3]:
        render_tab4()
    with tabs[4]:
        render_tab5()


main()
