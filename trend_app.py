# -*- coding: utf-8 -*-
"""
trend_app.py - 내구시험 추세 분석기 (Trend Analyzer) 웹앱
원본 데스크톱(tkinter) 프로그램을 Streamlit으로 재구성.
데이터 입력은 원본과 동일하게 "폴더 경로"를 그대로 지원한다.
- 이 앱을 로컬 PC에서 `streamlit run app.py`로 실행하면(서버=내 PC이므로)
  원본처럼 폴더 경로를 입력하면 그 폴더의 모든 CSV를 자동으로 스캔한다.
- Streamlit Cloud 등 원격 서버에 올린 경우에는 서버가 사용자의 로컬 폴더에
  접근할 수 없으므로, 그 경우에는 CSV 파일 업로드 방식을 사용한다.
"""
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import trend_calc as T

FOCUS_ITEMS = T.FOCUS_ITEMS


def _get_data_source():
    """사이드바에서 '폴더 경로 입력(로컬 실행 시)' 또는 'CSV 파일 업로드' 를 선택.
    반환: {seq: text} 형태의 딕셔너리(시간순 정렬 완료), 파일명 매핑."""
    st.sidebar.markdown("### 📂 Raw Data 불러오기")
    mode = st.sidebar.radio(
        "데이터 입력 방식",
        ["폴더 경로 입력(로컬 실행 시)", "CSV 파일 업로드"],
        help="이 웹앱을 내 PC에서 `streamlit run app.py`로 직접 실행 중이면 "
             "'폴더 경로 입력'을 쓰면 원본 프로그램처럼 폴더 안의 CSV를 전부 자동으로 읽습니다. "
             "Streamlit Cloud 등 외부 서버에 배포한 경우에는 서버가 내 PC 폴더에 접근할 수 없으니 "
             "'CSV 파일 업로드'를 사용하세요.",
    )

    names, texts = {}, {}
    if mode == "폴더 경로 입력(로컬 실행 시)":
        folder = st.sidebar.text_input("CSV 폴더 경로", key="tr_folder",
                                        placeholder=r"예: C:\data\rawdata 또는 /home/user/rawdata")
        if folder:
            if os.path.isdir(folder):
                paths_map, texts = T.scan_folder(folder)
                names = {i: os.path.basename(p) for i, p in paths_map.items()}
                st.sidebar.success(f"{len(names)}개 CSV 파일 발견")
            else:
                st.sidebar.error("해당 경로에서 폴더를 찾을 수 없습니다. (이 서버 기준 경로여야 합니다)")
    else:
        uploaded = st.sidebar.file_uploader(
            "CSV 파일 업로드 (여러 개 선택 가능)", type=["csv"],
            accept_multiple_files=True, key="tr_upload")
        if uploaded:
            files_info = [(uf.name, uf.read()) for uf in uploaded]
            names, texts = T.scan_uploaded(files_info)
            st.sidebar.success(f"{len(names)}개 파일 로드됨")

    return names, texts


def _ensure_summary(names, texts, active_ratio):
    """세션에 요약 통계를 캐시. 파일 목록(이름 집합)이 바뀌면 다시 계산."""
    key = tuple(sorted(names.values()))
    if st.session_state.get("tr_key") == key and st.session_state.get("tr_ratio") == active_ratio \
            and "tr_summary" in st.session_state:
        return (st.session_state["tr_summary"], st.session_state["tr_columns"],
                st.session_state["tr_thr"], st.session_state["tr_franges"])

    sample_text = texts[min(texts.keys())]
    raw_items = T.get_header_items(sample_text) or FOCUS_ITEMS

    with st.spinner("파일을 읽고 요약 통계를 계산 중입니다..."):
        summary, columns, thr, franges = T.build_summary(texts, raw_items, active_ratio=active_ratio)

    st.session_state["tr_key"] = key
    st.session_state["tr_ratio"] = active_ratio
    st.session_state["tr_summary"] = summary
    st.session_state["tr_columns"] = columns
    st.session_state["tr_thr"] = thr
    st.session_state["tr_franges"] = franges
    st.session_state["tr_texts"] = texts
    st.session_state["tr_names"] = names
    return summary, columns, thr, franges


def render():
    st.title("📈 내구시험 추세 분석기 (Trend Analyzer)")
    st.caption("원본 데스크톱 프로그램(v13)을 그대로 웹으로 재구성. "
               "누적 작동시간(h) = 시간순으로 정렬한 파일들의 (행개수×0.1초) 누적합산")

    names, texts = _get_data_source()
    if not texts:
        st.info("좌측 사이드바에서 폴더 경로를 입력하거나 CSV 파일을 업로드하세요.")
        return

    active_ratio = st.sidebar.slider("동작구간 판정 비율(전역)", 0.05, 0.9,
                                      T.ACTIVE_RATIO_DEFAULT, 0.05,
                                      help="전체 파일 최댓값들의 median × 이 비율을 넘는 샘플만 "
                                           "'동작 중'으로 보고 동작구간 중앙값/피크평균을 계산합니다.")

    summary, columns, thr, franges = _ensure_summary(names, texts, active_ratio)
    hours = summary["누적작동시간(h)"].to_numpy()
    total_h = hours.max() if len(hours) else 0.0
    st.success(f"✅ {len(names)}개 파일 로드 완료 · 누적 작동시간 총 {total_h:.2f}h")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["전체 추세", "정밀 분석", "두 시간대 비교", "새 파일 비교(폴더감시 대체)", "신뢰성 분석(TTF·RUL)"])

    # ---------------- 탭1: 전체 추세 ----------------
    with tab1:
        st.subheader("항목별 통계 추세")
        c1, c2, c3 = st.columns(3)
        items = c1.multiselect("항목 선택", columns, default=columns[:min(4, len(columns))])
        stat_options = ["평균", "최대", "최소", "표준편차"]
        for it in columns:
            if f"{it}_동작구간 중앙값" in summary.columns:
                stat_options += ["동작구간 중앙값", "동작구간 피크평균"]
                break
        stat = c2.selectbox("표시 통계", sorted(set(stat_options)))
        noise = c3.selectbox("노이즈 필터", ["없음", "이동중앙값", "이동평균", "3시그마제거"])

        c4, c5 = st.columns(2)
        lo = c4.number_input("제외 범위 최소", value=0.0, key="ex_lo", step=1.0, format="%.4f")
        hi = c5.number_input("제외 범위 최대", value=0.0, key="ex_hi", step=1.0, format="%.4f")
        use_exclude = st.checkbox("제외 범위 적용", value=False)
        show_regression = st.checkbox("회귀선(추세선) 표시", value=True)

        if items:
            fig = go.Figure()
            for it in items:
                col = f"{it}_{stat}"
                if col not in summary.columns:
                    continue
                y = summary[col].to_numpy().astype(float)
                if noise != "없음":
                    y = T.apply_noise_filter(y, noise)
                if use_exclude:
                    y = T.apply_exclude(y, lo, hi)
                fig.add_trace(go.Scatter(x=hours, y=y, mode="lines+markers", name=f"{it} ({stat})"))
                if show_regression:
                    ok = ~np.isnan(y)
                    if ok.sum() >= 2:
                        a, b = np.polyfit(hours[ok], y[ok], 1)
                        fig.add_trace(go.Scatter(x=hours, y=a * hours + b, mode="lines",
                                                  line=dict(dash="dash"), name=f"{it} 회귀선"))
            fig.update_layout(xaxis_title="누적 작동시간(h)", yaxis_title=stat, height=500,
                               legend=dict(orientation="h"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("항목을 1개 이상 선택하세요.")

        with st.expander("요약 통계 표 보기"):
            st.dataframe(summary, use_container_width=True)

    # ---------------- 탭2: 정밀 분석 ----------------
    with tab2:
        st.subheader("특정 시점의 raw 파형 보기")
        target_h = st.number_input("확인할 누적 작동시간(h)", min_value=0.0,
                                    max_value=float(total_h), value=0.0, step=0.1)
        # target_h 가 속하는 파일(seq) 찾기
        seq_hit = None
        for seq, (s, e) in franges.items():
            if s <= target_h <= e:
                seq_hit = seq; break
        if seq_hit is None and franges:
            seq_hit = min(franges, key=lambda k: abs(franges[k][1] - target_h))

        if seq_hit is not None:
            st.caption(f"파일: {names.get(seq_hit,'?')}  (구간 {franges[seq_hit][0]:.2f}h ~ {franges[seq_hit][1]:.2f}h)")
            df_raw = T.load_csv_text(texts[seq_hit], usecols=columns)
            items2 = st.multiselect("겹쳐볼 항목(보조축)", columns,
                                     default=columns[:min(2, len(columns))], key="tr_precise_items")
            if items2:
                fig2 = go.Figure()
                t_axis = np.arange(len(df_raw)) * T.DT
                for i, it in enumerate(items2):
                    if it not in df_raw.columns:
                        continue
                    secondary = i > 0
                    fig2.add_trace(go.Scatter(x=t_axis, y=df_raw[it], mode="lines", name=it,
                                               yaxis="y2" if secondary else "y1"))
                fig2.update_layout(xaxis_title="시간(초, 파일 내부)", height=500,
                                    yaxis=dict(title=items2[0]),
                                    yaxis2=dict(title="보조축", overlaying="y", side="right"))
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("데이터가 없습니다.")

    # ---------------- 탭3: 두 시간대 비교 ----------------
    with tab3:
        st.subheader("두 시점(A/B)의 raw 파형 비교")
        cA, cB = st.columns(2)
        hA = cA.number_input("A 시점(h)", min_value=0.0, max_value=float(total_h), value=0.0, step=0.1)
        hB = cB.number_input("B 시점(h)", min_value=0.0, max_value=float(total_h),
                              value=float(total_h), step=0.1)
        item_cmp = st.selectbox("비교할 항목", columns, key="tr_cmp_item")
        overlay = st.radio("표시 방식", ["겹쳐보기", "위아래로 보기"], horizontal=True)

        def _seq_of(h):
            for seq, (s, e) in franges.items():
                if s <= h <= e:
                    return seq
            return min(franges, key=lambda k: abs(franges[k][1] - h)) if franges else None

        seqA, seqB = _seq_of(hA), _seq_of(hB)
        if seqA is not None and seqB is not None and item_cmp:
            dfA = T.load_csv_text(texts[seqA], usecols=columns)
            dfB = T.load_csv_text(texts[seqB], usecols=columns)
            tA = np.arange(len(dfA)) * T.DT
            tB = np.arange(len(dfB)) * T.DT
            if overlay == "겹쳐보기":
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=tA, y=dfA[item_cmp], mode="lines", name=f"A({hA:.2f}h)"))
                fig3.add_trace(go.Scatter(x=tB, y=dfB[item_cmp], mode="lines", name=f"B({hB:.2f}h)"))
                fig3.update_layout(xaxis_title="시간(초)", yaxis_title=item_cmp, height=500)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                from plotly.subplots import make_subplots
                fig3 = make_subplots(rows=2, cols=1, shared_xaxes=False,
                                      subplot_titles=[f"A({hA:.2f}h)", f"B({hB:.2f}h)"])
                fig3.add_trace(go.Scatter(x=tA, y=dfA[item_cmp], mode="lines", name="A"), row=1, col=1)
                fig3.add_trace(go.Scatter(x=tB, y=dfB[item_cmp], mode="lines", name="B"), row=2, col=1)
                fig3.update_layout(height=650)
                st.plotly_chart(fig3, use_container_width=True)

    # ---------------- 탭4: 새 파일 비교(폴더감시 대체) ----------------
    with tab4:
        st.subheader("새 파일 비교 (원본의 '폴더 실시간 감시' 대체)")
        st.caption("웹 서버는 사용자 PC 폴더를 실시간으로 감시할 수 없어, 새로 생긴 CSV를 "
                   "직접 업로드해 기존 데이터와 비교/이상탐지하는 방식으로 대체했습니다. "
                   "이상탐지 기준(평균 ± Nσ)은 원본과 동일합니다.")
        new_files = st.file_uploader("새로 생긴 CSV 업로드(여러 개 가능)", type=["csv"],
                                      accept_multiple_files=True, key="tr_newfiles")
        n_sigma = st.slider("이상탐지 기준(σ)", 1.0, 5.0, 3.0, 0.5)
        if new_files:
            for uf in new_files:
                txt_new = T._decode_raw_bytes(uf.read())
                try:
                    df_new = T.load_csv_text(txt_new, usecols=columns)
                except Exception as e:
                    st.error(f"{uf.name}: 읽기 실패 ({e})"); continue
                st.markdown(f"**{uf.name}**")
                report = []
                for it in columns:
                    if it not in df_new.columns:
                        continue
                    hist_col = f"{it}_평균"
                    if hist_col not in summary.columns:
                        continue
                    hist_mean = summary[hist_col].mean()
                    hist_std = summary[f"{it}_표준편차"].mean() if f"{it}_표준편차" in summary.columns else np.nan
                    if not hist_std or np.isnan(hist_std) or hist_std == 0:
                        continue
                    new_mean = df_new[it].mean()
                    z = abs(new_mean - hist_mean) / hist_std
                    flag = "🔴 이상" if z > n_sigma else "🟢 정상"
                    report.append((it, hist_mean, new_mean, z, flag))
                if report:
                    rep_df = pd.DataFrame(report, columns=["항목", "기존 평균", "새 파일 평균", "Z-score", "판정"])
                    st.dataframe(rep_df, use_container_width=True)

    # ---------------- 탭5: 신뢰성 분석(TTF·RUL) ----------------
    with tab5:
        st.subheader("고장이력(TTF) + 잔여수명(RUL) 계산")
        items5 = st.multiselect("분석할 항목", columns, default=columns[:min(3, len(columns))], key="tr_rel_items")
        stat5 = st.selectbox("RUL 계산 기준 통계", ["동작구간 중앙값", "동작구간 피크평균", "평균"], key="tr_rel_stat")

        st.markdown("**항목별 스펙 한계(LSL/USL)**")
        spec = {}
        for it in items5:
            c1, c2 = st.columns(2)
            lsl_in = c1.text_input(f"{it} LSL", value="", key=f"lsl_{it}")
            usl_in = c2.text_input(f"{it} USL", value="", key=f"usl_{it}")
            lsl = float(lsl_in) if lsl_in.strip() else None
            usl = float(usl_in) if usl_in.strip() else None
            spec[it] = (lsl, usl)

        if st.button("① 고장이력(TTF) + RUL 계산", type="primary"):
            lines = ["**[고장이력(TTF)]**"]
            ttf_map, rul_map = {}, {}
            for it in items5:
                lsl, usl = spec.get(it, (None, None))
                maxcol, mincol = f"{it}_최대", f"{it}_최소"
                if lsl is None and usl is None:
                    lines.append(f"- {it}: LSL/USL 미입력 (스킵)")
                elif maxcol not in summary.columns or mincol not in summary.columns:
                    lines.append(f"- {it}: 통계 없음")
                else:
                    res = T.detect_ttf(hours, summary[maxcol].to_numpy(), summary[mincol].to_numpy(), lsl, usl)
                    if res is None:
                        lines.append(f"- {it}: 스펙 이탈 없음")
                    else:
                        ttf_map[it] = res
                        lines.append(f"- {it}: {res['h']:.2f}h 지점 최초 이탈 (값 {res['value']:.4f}) → "
                                      f"{res['kind']} (이후 지속비율 {res['persist']*100:.0f}%)")

            lines.append(""); lines.append(f"**[열화모델 / RUL] (기준 통계: {stat5})**")
            for it in items5:
                lsl, usl = spec.get(it, (None, None))
                col = f"{it}_{stat5}"
                note = ""
                if col not in summary.columns:
                    col = f"{it}_평균"; note = " (동작구간 통계 없음 → 전체 평균 대체)"
                if col not in summary.columns:
                    lines.append(f"- {it}: 데이터 없음"); continue
                y = summary[col].to_numpy()
                ok = ~np.isnan(y)
                if ok.sum() < 2:
                    lines.append(f"- {it}: 데이터 부족"); continue
                model = T.best_model(hours[ok], y[ok])
                if model is None:
                    lines.append(f"- {it}: 모델 적합 실패"); continue
                h_now = float(hours[ok].max())
                preds = []
                for lim, name in [(usl, "USL"), (lsl, "LSL")]:
                    if lim is None:
                        continue
                    cross = T.predict_cross(model, h_now, lim)
                    if cross is not None:
                        preds.append((name, cross, cross - h_now))
                rul_map[it] = {"model": model, "preds": preds}
                base = f"- {it}: {model['kind']}모델 채택(R²={model['r2']:.3f}){note}"
                if preds:
                    for name, cross, rul in preds:
                        base += f", {name} 도달예상 {cross:.1f}h(RUL≈{rul:.1f}h)"
                else:
                    base += ", 스펙 도달 예측 불가(추세 미미 또는 이미 안정)"
                lines.append(base)

            st.markdown("\n\n".join(lines))
            st.session_state["tr_rel_cache"] = {"items": items5, "ttf_map": ttf_map, "rul_map": rul_map}

        cache = st.session_state.get("tr_rel_cache")
        if cache and cache["items"]:
            plot_item = st.selectbox("그래프로 볼 항목", cache["items"], key="tr_rel_plot_item")
            col = f"{plot_item}_{stat5}"
            if col not in summary.columns:
                col = f"{plot_item}_평균"
            if col in summary.columns:
                y = summary[col].to_numpy()
                fig5 = go.Figure()
                fig5.add_trace(go.Scatter(x=hours, y=y, mode="lines+markers", name=plot_item))
                model_info = cache["rul_map"].get(plot_item)
                if model_info and model_info["preds"]:
                    for name, cross, rul in model_info["preds"]:
                        fig5.add_vline(x=cross, line_dash="dash",
                                        annotation_text=f"{name} 도달예상 {cross:.1f}h")
                fig5.update_layout(xaxis_title="누적 작동시간(h)", yaxis_title=col, height=450)
                st.plotly_chart(fig5, use_container_width=True)
