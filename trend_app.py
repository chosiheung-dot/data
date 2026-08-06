# -*- coding: utf-8 -*-
"""
trend_app.py
내구시험 추세 분석기 (Trend Analyzer) - Streamlit 웹앱

원본 데스크톱 프로그램(app.py, tkinter+customtkinter, v13)의 5개 탭을
최대한 그대로 옮겼다. 다만 웹(브라우저)이라는 환경 특성상 아래 1가지는
동작 방식이 달라질 수 밖에 없다는 점을 먼저 밝혀둔다.

  ⚠ "폴더 감시" 탭(원본 탭④): 원본은 사용자 PC의 폴더를 백그라운드 스레드로
     계속 감시해 새 파일이 생기면 즉시 팝업으로 알려준다. 브라우저 기반 웹
     서비스는 사용자의 로컬 폴더를 감시할 수 없고, 24시간 서버를 계속
     띄워두는 것도 무료 배포 환경에서는 불가능하다. 그래서 이 탭은
     "새로 생긴 CSV들을 다시 업로드해서 그 자리에서 비교/이상탐지" 하는
     방식(수동 새로고침)으로 대체했다. 판정 로직(평균±Nσ 이상탐지)은 원본과 동일.

나머지 4개 탭(전체 추세 / 정밀 분석 / 두 시간대 비교 / 신뢰성 분석(TTF·RUL))은
원본과 동일한 계산 로직(trend_calc.py)을 그대로 사용하며, 그래프는 원본의
마우스 휠줌/드래그를 웹에서 동등하게 쓸 수 있는 Plotly 인터랙티브 그래프로 구현했다.
"""
import io
import time
import hashlib

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import trend_calc as T

LINE_COLORS = ["#3B82F6", "#22D3EE", "#34D399", "#F59E0B", "#F472B6", "#A78BFA", "#FB7185", "#FBBF24"]


# ============================== 공용 헬퍼 ==============================
def _files_signature(files):
    return hashlib.md5("|".join(f"{n}:{len(b)}" for n, b in files).encode()).hexdigest()


def _fig_png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    return buf.getvalue()


def _pdf_header(pdf, title, lines):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.05, 0.96, title, fontsize=18, weight="bold", va="top")
    ax.text(0.05, 0.90, time.strftime("생성일시 %Y-%m-%d %H:%M"), fontsize=10, color="#555")
    y = 0.84
    for ln in lines:
        ax.text(0.05, y, ln, fontsize=11, va="top")
        y -= 0.032
    pdf.savefig(fig)
    plt.close(fig)


def _download_row(key_prefix, png_bytes=None, pdf_bytes=None, xlsx_bytes=None, base_name="chart"):
    cols = st.columns(3)
    if png_bytes is not None:
        cols[0].download_button("⬇ 이미지(PNG)", data=png_bytes, file_name=f"{base_name}.png",
                                 mime="image/png", key=key_prefix + "_png")
    if pdf_bytes is not None:
        cols[1].download_button("⬇ PDF 리포트", data=pdf_bytes, file_name=f"{base_name}.pdf",
                                 mime="application/pdf", key=key_prefix + "_pdf")
    if xlsx_bytes is not None:
        cols[2].download_button("⬇ 엑셀", data=xlsx_bytes, file_name=f"{base_name}.xlsx",
                                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 key=key_prefix + "_xlsx")


# ============================== 데이터 로드(업로드) ==============================
def _load_area():
    st.markdown("#### 📁 Raw Data 업로드")
    st.caption("원본 프로그램의 '폴더 선택'을 대신합니다. 같은 세트의 CSV 파일들을 한 번에 여러 개 선택해서 업로드하세요. "
               "파일명이 `카운터-YYMMDD-HHMMSS.csv` 형식이면 실제 저장 시각 순으로 정렬해서 분석하고, "
               "아니면 업로드한 순서를 그대로 사용합니다.")
    uploaded = st.file_uploader("CSV 파일 (여러 개 선택)", type=["csv", "CSV"], accept_multiple_files=True,
                                 key="tr_upload")
    load_clicked = st.button("📥 분석 시작(불러오기)", key="tr_load_btn", type="primary")

    if load_clicked:
        if not uploaded:
            st.warning("CSV 파일을 먼저 선택하세요.")
        else:
            files_raw = [(f.name, f.getvalue()) for f in uploaded]
            sig = _files_signature(files_raw)
            with st.spinner("파일을 분석하는 중..."):
                scanned = T.scan_files(files_raw)
                sample_raw = scanned[min(scanned.keys())][1]
                raw_items = T.get_header_items(sample_raw) or list(T.FOCUS_ITEMS)
                summary, file_ranges, columns, thr_map = T.build_summary(scanned, raw_items,
                                                                          active_ratio=T.ACTIVE_RATIO_DEFAULT)
            st.session_state["tr_sig"] = sig
            st.session_state["tr_files"] = scanned
            st.session_state["tr_raw_items"] = raw_items
            st.session_state["tr_summary"] = summary
            st.session_state["tr_file_ranges"] = file_ranges
            st.session_state["tr_columns"] = columns
            st.session_state["tr_thresholds"] = thr_map
            st.session_state["tr_active_ratio"] = T.ACTIVE_RATIO_DEFAULT
            st.session_state["tr_mon_known"] = set(scanned.keys())
            st.success(f"{len(scanned)}개 파일 로드 완료")

    if st.session_state.get("tr_summary") is not None:
        total_h = st.session_state["tr_summary"]["누적작동시간(h)"].max()
        st.info(f"● {len(st.session_state['tr_files'])}개 파일 로드됨 · 누적 작동시간 총 {total_h:.1f}h · "
                f"항목 {len(st.session_state['tr_columns'])}개")
        return True
    return False


def _ready():
    return st.session_state.get("tr_summary") is not None


# ============================== 탭1: 전체 추세 ==============================
def _tab_trend():
    if not _ready():
        st.warning("먼저 위에서 CSV를 업로드하고 [분석 시작]을 눌러주세요.")
        return
    summary = st.session_state["tr_summary"]
    raw_items = st.session_state["tr_raw_items"]

    left, right = st.columns([1, 2])
    with left:
        items = st.multiselect("항목 선택", raw_items,
                                default=[c for c in raw_items if "cur" in c.lower()][:3] or raw_items[:1],
                                key="tr1_items")
        stat = st.selectbox("통계", ["동작구간 중앙값", "동작구간 피크평균", "평균", "최대", "최소", "표준편차"],
                             key="tr1_stat")
        st.caption("(대기/정지구간이 섞인 전류 등은 '동작구간 중앙값' 권장)")
        nf = st.selectbox("노이즈 처리", ["없음", "이동중앙값", "이동평균", "3시그마제거"], key="tr1_nf")
        c1, c2 = st.columns(2)
        lo = c1.number_input("제외범위 min", value=None, key="tr1_lo", format="%.4f")
        hi = c2.number_input("제외범위 max", value=None, key="tr1_hi", format="%.4f")
        reg = st.checkbox("추세선·회귀", key="tr1_reg")
        thr = st.number_input("임계값(수명예측, 선택)", value=None, key="tr1_thr", format="%.4f")
        draw = st.button("📊 그래프 그리기", key="tr1_draw", type="primary")

    with right:
        if draw or st.session_state.get("tr1_drawn"):
            st.session_state["tr1_drawn"] = True
            if not items:
                st.info("항목을 1개 이상 선택하세요.")
                return
            hours = summary["누적작동시간(h)"].to_numpy()
            fig = go.Figure()
            infos = []
            for i, it in enumerate(items):
                col = f"{it}_{stat}"
                if col not in summary.columns:
                    continue
                y = T.apply_exclude(T.apply_noise_filter(summary[col].to_numpy(), nf), lo, hi)
                c = LINE_COLORS[i % len(LINE_COLORS)]
                fnames = [st.session_state["tr_files"][s][0] for s in summary.index]
                fig.add_trace(go.Scatter(x=hours, y=y, mode="lines+markers", name=it,
                                          line=dict(color=c), marker=dict(size=5),
                                          hovertext=fnames, hovertemplate="%{x:.2f}h<br>%{y:.4f}<br>%{hovertext}"))
                if reg:
                    yv = summary[col].to_numpy()
                    ok = ~np.isnan(yv)
                    if ok.sum() >= 2:
                        hv, yv2 = hours[ok], yv[ok]
                        a, b = np.polyfit(hv, yv2, 1)
                        r2 = np.corrcoef(hv, yv2)[0, 1] ** 2
                        fig.add_trace(go.Scatter(x=hv, y=a * hv + b, mode="lines", name=f"{it} 추세선",
                                                  line=dict(color=c, dash="dash")))
                        t = f"{it}: {a:+.5f}/h, R²={r2:.3f}"
                        if thr is not None and a != 0:
                            cross = (thr - b) / a
                            if cross > hv.max():
                                t += f", 임계도달≈{cross:.1f}h"
                        infos.append(t)
            fig.update_layout(xaxis_title="누적 작동시간 (h)", yaxis_title=stat, height=480,
                               legend=dict(orientation="h"), margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True, key="tr1_chart")
            if infos:
                st.markdown("**추세 정보**")
                for t in infos:
                    st.write("- " + t)

            # 다운로드용 matplotlib 재생성
            mfig, ax = plt.subplots(figsize=(11, 6))
            for i, it in enumerate(items):
                col = f"{it}_{stat}"
                if col in summary.columns:
                    y = T.apply_exclude(T.apply_noise_filter(summary[col].to_numpy(), nf), lo, hi)
                    ax.plot(hours, y, marker="o", ms=3, label=it, color=LINE_COLORS[i % len(LINE_COLORS)])
            ax.set_xlabel("누적 작동시간(h)"); ax.set_ylabel(stat); ax.grid(alpha=0.3); ax.legend(fontsize=8)
            ax.set_title(f"항목별 {stat} 추세")
            png = _fig_png_bytes(mfig)

            pdf_buf = io.BytesIO()
            with PdfPages(pdf_buf) as pdf:
                lines = ["[전체 추세 분석 리포트]",
                         f"분석 누적 작동시간 범위: {hours.min():.2f}h ~ {hours.max():.2f}h",
                         f"분석 항목: {', '.join(items)}", f"통계 기준: {stat}", ""] + infos
                _pdf_header(pdf, "내구시험 추세 분석 리포트", lines)
                pdf.savefig(mfig)
            plt.close(mfig)

            xbuf = io.BytesIO()
            with pd.ExcelWriter(xbuf, engine="openpyxl") as xw:
                summary.to_excel(xw, sheet_name="전체통계")
            _download_row("tr1_dl", png_bytes=png, pdf_bytes=pdf_buf.getvalue(), xlsx_bytes=xbuf.getvalue(),
                           base_name="전체추세")


# ============================== 탭2: 정밀 분석 ==============================
def _tab_detail():
    if not _ready():
        st.warning("먼저 위에서 CSV를 업로드하고 [분석 시작]을 눌러주세요.")
        return
    raw_items = st.session_state["tr_raw_items"]
    file_ranges = st.session_state["tr_file_ranges"]
    files = st.session_state["tr_files"]

    left, right = st.columns([1, 2])
    with left:
        target_h = st.number_input("누적 작동시간(h) 입력", value=0.0, step=0.5, key="tr2_hour")
        items = st.multiselect("항목 선택", raw_items, default=raw_items[:2], key="tr2_items")
        nf = st.selectbox("노이즈 처리", ["없음", "이동중앙값", "이동평균", "3시그마제거"], key="tr2_nf")
        c1, c2 = st.columns(2)
        lo = c1.number_input("제외범위 min", value=None, key="tr2_lo", format="%.4f")
        hi = c2.number_input("제외범위 max", value=None, key="tr2_hi", format="%.4f")
        twin = st.checkbox("단위 다르면 보조축으로 겹쳐보기", value=True, key="tr2_twin")
        load = st.button("🔍 불러오기", key="tr2_load", type="primary")

    with right:
        if load or st.session_state.get("tr2_loaded"):
            found = T.find_seq_by_cumhour(file_ranges, target_h)
            if found is None:
                st.warning("해당하는 파일을 찾지 못했습니다.")
                return
            seq, s, e = found
            fname, raw = files[seq]
            df = T.load_csv(raw)
            st.session_state["tr2_loaded"] = True
            note = "" if (s - 1e-6 <= target_h <= e + 1e-6) else " (범위 밖이라 가장 가까운 파일로 대체됨)"
            st.success(f"입력 {target_h}h → 매칭 파일: {s:.2f}h~{e:.2f}h 구간 (파일: {fname}){note}")

            x = np.arange(len(df)) * T.DT
            scales = {}
            for it in items:
                if it in df.columns:
                    med = np.nanmedian(np.abs(df[it].to_numpy()))
                    scales[it] = med if np.isfinite(med) else 0
            big = max(scales.values()) if scales else 0

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            for i, it in enumerate(items):
                if it not in df.columns:
                    continue
                y = T.apply_exclude(T.apply_noise_filter(df[it].to_numpy(), nf), lo, hi)
                c = LINE_COLORS[i % len(LINE_COLORS)]
                use2 = twin and big > 0 and scales.get(it, 0) > 0 and (big / max(scales[it], 1e-9)) >= 10
                fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=it, line=dict(color=c, width=1)),
                              secondary_y=use2)
            fig.update_layout(height=500, xaxis_title="파일 내 경과 시간(초)",
                               title=f"누적 {s:.2f}h~{e:.2f}h 구간 원본 파형 ({len(df):,}점)",
                               dragmode="pan", legend=dict(orientation="h"), margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True, key="tr2_chart",
                             config={"scrollZoom": True})
            st.caption("💡 마우스 휠=확대/축소, 드래그=이동(pan). 원본 프로그램의 휠줌/드래그와 동일한 조작입니다.")

            rows = []
            for it in items:
                if it in df.columns:
                    s2 = df[it].dropna()
                    rows.append([it, s2.mean(), s2.max(), s2.min(), s2.std()])
            if rows:
                st.dataframe(pd.DataFrame(rows, columns=["항목", "평균", "최대", "최소", "표준편차"]),
                             use_container_width=True)

            mfig, ax = plt.subplots(figsize=(11, 6))
            for i, it in enumerate(items):
                if it in df.columns:
                    y = T.apply_exclude(T.apply_noise_filter(df[it].to_numpy(), nf), lo, hi)
                    ax.plot(x, y, lw=0.7, label=it, color=LINE_COLORS[i % len(LINE_COLORS)])
            ax.set_title(f"{s:.2f}h~{e:.2f}h 원본 파형"); ax.set_xlabel("파일 내 경과 시간(초)")
            ax.grid(alpha=0.3); ax.legend(fontsize=8)
            png = _fig_png_bytes(mfig)
            pdf_buf = io.BytesIO()
            with PdfPages(pdf_buf) as pdf:
                lines = ["[정밀 분석 리포트]", f"입력한 누적 작동시간: {target_h}h",
                         f"매칭된 실제 구간: {s:.2f}h ~ {e:.2f}h", f"파일: {fname}",
                         f"샘플 수: {len(df):,} (1행=0.1초)", f"노이즈 필터: {nf}",
                         f"항목: {', '.join(items)}", "", "[항목별 통계]"]
                for it in items:
                    if it in df.columns:
                        s2 = df[it].dropna()
                        lines.append(f" - {it}: 평균 {s2.mean():.4f}, 최대 {s2.max():.4f}, "
                                     f"최소 {s2.min():.4f}, 표준편차 {s2.std():.4f}")
                _pdf_header(pdf, f"정밀 분석 리포트 ({s:.2f}h~{e:.2f}h)", lines)
                pdf.savefig(mfig)
            plt.close(mfig)
            _download_row("tr2_dl", png_bytes=png, pdf_bytes=pdf_buf.getvalue(), base_name="정밀분석")


# ============================== 탭3: 두 시간대 비교 ==============================
def _tab_compare():
    if not _ready():
        st.warning("먼저 위에서 CSV를 업로드하고 [분석 시작]을 눌러주세요.")
        return
    raw_items = st.session_state["tr_raw_items"]
    file_ranges = st.session_state["tr_file_ranges"]
    files = st.session_state["tr_files"]

    left, right = st.columns([1, 2])
    with left:
        c1, c2 = st.columns(2)
        a = c1.number_input("A 누적 작동시간(h)", value=0.0, step=0.5, key="tr3_a")
        b = c2.number_input("B 누적 작동시간(h)", value=0.0, step=0.5, key="tr3_b")
        items = st.multiselect("항목 선택", raw_items, default=raw_items[:2], key="tr3_items")
        mode = st.selectbox("보기 방식", ["겹쳐서", "위아래로"], key="tr3_mode")
        nf = st.selectbox("노이즈 처리", ["없음", "이동중앙값", "이동평균", "3시그마제거"], key="tr3_nf")
        c3, c4 = st.columns(2)
        lo = c3.number_input("제외범위 min", value=None, key="tr3_lo", format="%.4f")
        hi = c4.number_input("제외범위 max", value=None, key="tr3_hi", format="%.4f")
        cmpbtn = st.button("🆚 비교하기", key="tr3_cmp", type="primary")

    with right:
        if cmpbtn or st.session_state.get("tr3_done"):
            fa = T.find_seq_by_cumhour(file_ranges, a)
            fb = T.find_seq_by_cumhour(file_ranges, b)
            if fa is None or fb is None:
                st.warning("A 또는 B에 해당하는 파일을 찾지 못했습니다.")
                return
            st.session_state["tr3_done"] = True
            seq_a, sa, ea = fa
            seq_b, sb, eb = fb
            fname_a, raw_a = files[seq_a]
            fname_b, raw_b = files[seq_b]
            dfa = T.load_csv(raw_a)
            dfb = T.load_csv(raw_b)
            label_a = f"{sa:.2f}~{ea:.2f}h(A)"; label_b = f"{sb:.2f}~{eb:.2f}h(B)"
            st.success(f"A 입력 {a}h → {sa:.2f}~{ea:.2f}h ({fname_a})  \n"
                       f"B 입력 {b}h → {sb:.2f}~{eb:.2f}h ({fname_b})")

            if mode == "위아래로":
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=[label_a, label_b])
                for row, df in [(1, dfa), (2, dfb)]:
                    for i, it in enumerate(items):
                        if it not in df.columns:
                            continue
                        y = T.apply_exclude(T.apply_noise_filter(df[it].to_numpy(), nf), lo, hi)
                        fig.add_trace(go.Scatter(x=np.arange(len(df)) * T.DT, y=y, mode="lines", name=it,
                                                  line=dict(color=LINE_COLORS[i % len(LINE_COLORS)], width=1),
                                                  showlegend=(row == 1)), row=row, col=1)
                fig.update_layout(height=560, margin=dict(t=50))
            else:
                fig = go.Figure()
                for i, it in enumerate(items):
                    c = LINE_COLORS[i % len(LINE_COLORS)]
                    if it in dfa.columns:
                        y = T.apply_exclude(T.apply_noise_filter(dfa[it].to_numpy(), nf), lo, hi)
                        fig.add_trace(go.Scatter(x=np.arange(len(dfa)) * T.DT, y=y, mode="lines",
                                                  name=f"{it} A({label_a})", line=dict(color=c)))
                    if it in dfb.columns:
                        y = T.apply_exclude(T.apply_noise_filter(dfb[it].to_numpy(), nf), lo, hi)
                        fig.add_trace(go.Scatter(x=np.arange(len(dfb)) * T.DT, y=y, mode="lines",
                                                  name=f"{it} B({label_b})", line=dict(color=c, dash="dash")))
                fig.update_layout(height=500, title=f"A {label_a}(실선) vs B {label_b}(점선)",
                                   xaxis_title="파일 내 경과 시간(초)", margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True, key="tr3_chart")

            rows = []
            for it in items:
                if it in dfa.columns and it in dfb.columns:
                    ma, mb = dfa[it].mean(), dfb[it].mean()
                    diff = mb - ma
                    pct = (diff / ma * 100) if ma != 0 else 0
                    rows.append([it, ma, mb, diff, pct])
            if rows:
                st.dataframe(pd.DataFrame(rows, columns=["항목", "A 평균", "B 평균", "차이", "차이(%)"]),
                             use_container_width=True)

            pdf_buf = io.BytesIO()
            mfig, ax = plt.subplots(figsize=(11, 6))
            for i, it in enumerate(items):
                c = LINE_COLORS[i % len(LINE_COLORS)]
                if it in dfa.columns:
                    y = T.apply_exclude(T.apply_noise_filter(dfa[it].to_numpy(), nf), lo, hi)
                    ax.plot(np.arange(len(dfa)) * T.DT, y, lw=0.6, color=c, label=f"{it} A({label_a})")
                if it in dfb.columns:
                    y = T.apply_exclude(T.apply_noise_filter(dfb[it].to_numpy(), nf), lo, hi)
                    ax.plot(np.arange(len(dfb)) * T.DT, y, lw=0.6, color=c, ls="--", label=f"{it} B({label_b})")
            ax.set_title(f"A {label_a}(실선) vs B {label_b}(점선)"); ax.set_xlabel("파일 내 경과 시간(초)")
            ax.grid(alpha=0.3); ax.legend(fontsize=8)
            with PdfPages(pdf_buf) as pdf:
                lines = ["[두 시간대 비교 리포트]", f"입력 A: {a}h -> 매칭 {label_a} / 입력 B: {b}h -> 매칭 {label_b}",
                         f"노이즈 필터: {nf}", f"항목: {', '.join(items)}", "", "[통계 비교]"]
                for r in rows:
                    lines.append(f" - {r[0]}: A {r[1]:.4f} -> B {r[2]:.4f} (차이 {r[3]:+.4f}, {r[4]:+.1f}%)")
                _pdf_header(pdf, f"두 시간대 비교 리포트 ({label_a} vs {label_b})", lines)
                pdf.savefig(mfig)
            plt.close(mfig)
            png = None
            _download_row("tr3_dl", pdf_bytes=pdf_buf.getvalue(), base_name="두시간대비교")


# ============================== 탭4: 새 파일 비교(폴더 감시 대체) ==============================
def _tab_monitor():
    st.warning("⚠ 원본 프로그램의 '폴더 감시'(실시간 백그라운드 감시)는 브라우저 특성상 그대로 재현할 수 없습니다. "
               "대신 아래처럼 **새로 쌓인 CSV들을 다시 업로드해서 그 자리에서 비교**하는 방식으로 대체했습니다. "
               "이상탐지 판정 기준(평균 ± Nσ)은 원본과 동일합니다.")
    if not _ready():
        st.info("먼저 위에서 기존 CSV를 업로드하고 [분석 시작]을 눌러주세요.")
        return

    sigma = st.number_input("이상 임계 (Nσ)", value=3.0, step=0.5, key="tr4_sigma")
    new_uploaded = st.file_uploader("새로 생긴 CSV 파일들 업로드", type=["csv", "CSV"], accept_multiple_files=True,
                                     key="tr4_upload")
    check = st.button("🔎 새 파일 확인 / 이상탐지", key="tr4_check", type="primary")

    if check:
        if not new_uploaded:
            st.warning("새로 업로드할 CSV를 선택하세요.")
            return
        existing_names = {fname for fname, _ in st.session_state["tr_files"].values()}
        raw_items = st.session_state["tr_raw_items"]
        mon_items = [it for it in raw_items if "cur" in it.lower()] or list(raw_items)
        logs = []
        for f in new_uploaded:
            if f.name in existing_names:
                logs.append(f"[{time.strftime('%H:%M:%S')}] {f.name} : 이미 로드된 파일 (건너뜀)")
                continue
            raw = f.getvalue()
            try:
                df = T.load_csv(raw)
            except Exception as e:
                logs.append(f"[{time.strftime('%H:%M:%S')}] {f.name} : 읽기 실패 ({e})")
                continue
            dur_h = len(df) * T.DT / 3600.0
            msgs = []
            for it in mon_items:
                if it in df.columns:
                    s = df[it].dropna()
                    if len(s) > 0:
                        m, sd = s.mean(), s.std()
                        cnt = int(((s - m).abs() > sigma * sd).sum()) if sd > 0 else 0
                        if cnt > 0:
                            msgs.append(f"{it}:{cnt}건")
            txt = f"[{time.strftime('%H:%M:%S')}] 신규 파일 감지({f.name}, 약 {dur_h:.2f}h 분량)"
            if msgs:
                txt += " / ⚠ 이상 " + ", ".join(msgs)
            logs.append(txt)
        st.session_state.setdefault("tr4_log", [])
        st.session_state["tr4_log"] = logs + st.session_state["tr4_log"]

    if st.session_state.get("tr4_log"):
        st.text_area("감지 로그", value="\n".join(st.session_state["tr4_log"]), height=240, key="tr4_logbox")
        st.caption("이상이 감지된 파일은 '전체 추세/정밀 분석' 탭에서 CSV를 다시 함께 업로드해 분석에 포함시키세요.")


# ============================== 탭5: 신뢰성 분석 (TTF·RUL) ==============================
def _tab_reliability():
    if not _ready():
        st.warning("먼저 위에서 CSV를 업로드하고 [분석 시작]을 눌러주세요.")
        return
    raw_items = st.session_state["tr_raw_items"]
    summary = st.session_state["tr_summary"]

    left, right = st.columns([1, 2])
    with left:
        items = st.multiselect("항목 선택", raw_items, default=raw_items[:2], key="tr5_items")
        ratio = st.number_input("동작구간 판정 비율 (기본 0.2)", value=st.session_state.get("tr_active_ratio", 0.2),
                                 min_value=0.01, max_value=1.0, step=0.05, key="tr5_ratio")
        st.caption("항목별 '파일 최댓값들의 median × 이 비율'을 넘는 샘플만 '동작 중'으로 봄")
        if st.button("비율 적용(재계산)", key="tr5_apply_ratio"):
            with st.spinner("동작구간 재계산 중..."):
                summary2, file_ranges2, columns2, thr_map2 = T.build_summary(
                    st.session_state["tr_files"], raw_items, active_ratio=ratio)
            st.session_state["tr_summary"] = summary2
            st.session_state["tr_file_ranges"] = file_ranges2
            st.session_state["tr_columns"] = columns2
            st.session_state["tr_thresholds"] = thr_map2
            st.session_state["tr_active_ratio"] = ratio
            summary = summary2
            thr = thr_map2
            if thr:
                st.info("자동 산정된 동작임계값:\n" + "\n".join(f"- {k}: {v:.4f}" for k, v in thr.items()))
            else:
                st.info("동작임계값을 산정할 수 있는 항목이 없습니다.")

        stat = st.selectbox("RUL 계산 기준 통계", ["동작구간 중앙값", "동작구간 피크평균", "평균"], key="tr5_stat")

        st.markdown("**항목별 스펙 한계(LSL/USL)**")
        spec_df = pd.DataFrame({"항목": items, "LSL": [None] * len(items), "USL": [None] * len(items)})
        spec_edit = st.data_editor(spec_df, key="tr5_spec", num_rows="fixed", use_container_width=True,
                                    hide_index=True)
        compute = st.button("① 고장이력(TTF) + RUL 계산", key="tr5_compute", type="primary")

    with right:
        if compute or st.session_state.get("tr5_done"):
            if not items:
                st.info("항목을 1개 이상 선택하세요.")
                return
            st.session_state["tr5_done"] = True
            hours = summary["누적작동시간(h)"].to_numpy()
            spec_map = {}
            for _, row in spec_edit.iterrows():
                spec_map[row["항목"]] = (row["LSL"], row["USL"])

            lines = ["[고장이력(TTF)]"]
            ttf_map, rul_map = {}, {}
            for it in items:
                lsl, usl = spec_map.get(it, (None, None))
                lsl = None if pd.isna(lsl) else lsl
                usl = None if pd.isna(usl) else usl
                maxcol, mincol = f"{it}_최대", f"{it}_최소"
                if lsl is None and usl is None:
                    lines.append(f" - {it}: LSL/USL 미입력 (스킵)")
                elif maxcol not in summary.columns or mincol not in summary.columns:
                    lines.append(f" - {it}: 통계 없음")
                else:
                    res = T.detect_ttf(hours, summary[maxcol].to_numpy(), summary[mincol].to_numpy(), lsl, usl)
                    if res is None:
                        lines.append(f" - {it}: 스펙 이탈 없음")
                    else:
                        ttf_map[it] = res
                        lines.append(f" - {it}: {res['h']:.2f}h 지점 최초 이탈 (값 {res['value']:.4f}) -> "
                                     f"{res['kind']} (이후 지속비율 {res['persist']*100:.0f}%)")

            lines.append("")
            lines.append(f"[열화모델 / RUL] (기준 통계: {stat})")
            for it in items:
                lsl, usl = spec_map.get(it, (None, None))
                lsl = None if pd.isna(lsl) else lsl
                usl = None if pd.isna(usl) else usl
                col = f"{it}_{stat}"
                use_note = ""
                if col not in summary.columns:
                    col = f"{it}_평균"
                    use_note = " (동작구간 통계 없음 -> 전체 평균 대체)"
                if col not in summary.columns:
                    lines.append(f" - {it}: 데이터 없음"); continue
                y = summary[col].to_numpy()
                ok = ~np.isnan(y)
                if ok.sum() < 2:
                    lines.append(f" - {it}: 데이터 부족"); continue
                model = T.best_model(hours[ok], y[ok])
                if model is None:
                    lines.append(f" - {it}: 모델 적합 실패"); continue
                h_now = float(hours[ok].max())
                preds = []
                for lim, name in [(usl, "USL"), (lsl, "LSL")]:
                    if lim is None:
                        continue
                    cross = T.predict_cross(model, h_now, lim)
                    if cross is not None:
                        preds.append((name, cross, cross - h_now))
                rul_map[it] = {"model": model, "preds": preds}
                base = f" - {it}: {model['kind']}모델 채택(R²={model['r2']:.3f}){use_note}"
                if preds:
                    for name, cross, rul in preds:
                        base += f", {name} 도달예상 {cross:.1f}h(RUL≈{rul:.1f}h)"
                else:
                    base += ", 스펙 도달 예측 불가(추세 미미 또는 이미 안정)"
                lines.append(base)

            st.session_state["tr5_cache"] = {"items": items, "hours": hours, "stat": stat,
                                              "ttf_map": ttf_map, "rul_map": rul_map, "spec_map": spec_map,
                                              "lines": lines}
            st.code("\n".join(lines))

            plot_item = st.selectbox("그래프로 볼 항목", items, key="tr5_plotitem")
            _rel_draw(plot_item)


def _rel_draw(it):
    cache = st.session_state.get("tr5_cache")
    if not cache or it not in cache["items"]:
        return
    summary = st.session_state["tr_summary"]
    hours = cache["hours"]; stat = cache["stat"]
    col = f"{it}_{stat}"
    if col not in summary.columns:
        col = f"{it}_평균"
    y = summary[col].to_numpy()
    ok = ~np.isnan(y)
    lsl, usl = cache["spec_map"].get(it, (None, None))
    lsl = None if pd.isna(lsl) else lsl
    usl = None if pd.isna(usl) else usl

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours[ok], y=y[ok], mode="markers", name=f"{it} 실측({stat})",
                              marker=dict(color=LINE_COLORS[0], size=7)))
    info = cache["rul_map"].get(it)
    if info is not None:
        model = info["model"]
        h_now = float(hours[ok].max()) if ok.any() else 0.0
        span = max(h_now, 1.0)
        grid = np.linspace(float(hours[ok].min()) if ok.any() else 0.0, h_now + span * 0.5, 300)
        fig.add_trace(go.Scatter(x=grid, y=model["f"](grid), mode="lines", name=f"{model['kind']}모델 예측",
                                  line=dict(color=LINE_COLORS[3], dash="dash")))
        for name, cross, rul in info["preds"]:
            if cross <= grid.max():
                fig.add_vline(x=cross, line=dict(color="#F87171", dash="dot"),
                               annotation_text=f"{name} 도달 {cross:.1f}h")
    if usl is not None:
        fig.add_hline(y=usl, line=dict(color="#F87171", dash="dot"), annotation_text=f"USL={usl}")
    if lsl is not None:
        fig.add_hline(y=lsl, line=dict(color="#F87171", dash="dot"), annotation_text=f"LSL={lsl}")
    fig.update_layout(height=480, xaxis_title="누적 작동시간(h)", yaxis_title=it,
                       title=f"{it} 열화 모델 & 잔여수명(RUL) 예측", margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True, key=f"tr5_chart_{it}")

    pdf_buf = io.BytesIO()
    mfig, ax = plt.subplots(figsize=(11, 6))
    ax.scatter(hours[ok], y[ok], s=14, color=LINE_COLORS[0], label=f"{it} 실측({stat})")
    if info is not None:
        model = info["model"]
        h_now = float(hours[ok].max()) if ok.any() else 0.0
        span = max(h_now, 1.0)
        grid = np.linspace(float(hours[ok].min()) if ok.any() else 0.0, h_now + span * 0.5, 300)
        ax.plot(grid, model["f"](grid), color=LINE_COLORS[3], ls="--", lw=1.6, label=f"{model['kind']}모델 예측")
        for name, cross, rul in info["preds"]:
            if cross <= grid.max():
                ax.axvline(cross, color="#F87171", ls=":", lw=1.2)
    if usl is not None:
        ax.axhline(usl, color="#F87171", ls=":", lw=1.0, label=f"USL={usl}")
    if lsl is not None:
        ax.axhline(lsl, color="#F87171", ls=":", lw=1.0, label=f"LSL={lsl}")
    ax.set_xlabel("누적 작동시간(h)"); ax.set_ylabel(it); ax.set_title(f"{it} 열화 모델 & RUL 예측")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    with PdfPages(pdf_buf) as pdf:
        _pdf_header(pdf, "신뢰성 분석 리포트 (스펙한계·고장이력·RUL)", cache["lines"])
        pdf.savefig(mfig)
    plt.close(mfig)
    _download_row(f"tr5_dl_{it}", pdf_bytes=pdf_buf.getvalue(), base_name=f"신뢰성분석_{it}")


# ============================== 메인 ==============================
def render():
    st.markdown("## 내구시험 추세 분석기 (Raw Data 분석)")
    _load_area()
    st.divider()
    tabs = st.tabs(["전체 추세", "정밀 분석", "두 시간대 비교", "새 파일 비교(폴더감시 대체)", "신뢰성 분석(TTF·RUL)"])
    with tabs[0]:
        _tab_trend()
    with tabs[1]:
        _tab_detail()
    with tabs[2]:
        _tab_compare()
    with tabs[3]:
        _tab_monitor()
    with tabs[4]:
        _tab_reliability()
