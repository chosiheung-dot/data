
# -*- coding: utf-8 -*-
"""
trend_calc.py
원본 데스크톱 프로그램(내구시험 추세 분석기 v13, app.py/tkinter)의 계산 로직을
웹(Streamlit) 환경에 맞게 옮긴 모듈.

원본과 다른 부분(웹 환경 제약 때문에 반드시 바뀌는 것):
- "폴더 선택" -> "여러 CSV 파일 업로드" (브라우저는 로컬 폴더를 실시간으로 감시할 수 없음)
- 파일시스템 경로 대신 (파일명, bytes) 쌍을 다룸
- 디스크 캐시(pickle) 대신 세션 캐시(st.session_state)를 사용 (app.py에서 처리)

계산 로직(누적 작동시간 산출, 통계, 노이즈필터, 추세적합, TTF/RUL 판정 등)은
원본과 동일한 알고리즘을 그대로 옮겼다.
"""
import os
import re
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

FOCUS_ITEMS = ["Cmd1", "FB1", "Spd1", "Cur1", "Cmd2", "FB2", "Spd2", "Cur2",
               "Cmd3", "FB3", "Spd3", "Cur3", "Pvtg"]
DT = 0.1  # 1행당 초 (샘플링 간격)

ACTIVE_RATIO_DEFAULT = 0.2  # 동작구간 판정 비율(전역 median 최대값 대비)


# ============================== 노이즈/제외 ==============================
def apply_noise_filter(series, mode, win=15):
    s = pd.Series(series).astype(float)
    if mode == "이동중앙값":
        return s.rolling(win, center=True, min_periods=1).median().to_numpy()
    if mode == "이동평균":
        return s.rolling(win, center=True, min_periods=1).mean().to_numpy()
    if mode == "3시그마제거":
        m, sd = s.mean(), s.std()
        if sd == 0 or np.isnan(sd):
            return s.to_numpy()
        mask = (s - m).abs() > 3 * sd
        s2 = s.copy()
        s2[mask] = np.nan
        return s2.interpolate(limit_direction="both").to_numpy()
    return s.to_numpy()


def apply_exclude(y, lo, hi):
    """제외 범위: lo~hi 사이 값을 NaN으로 만들어 화면에서 숨김(데이터 보존)."""
    if lo is None and hi is None:
        return y
    y = np.asarray(y, dtype=float).copy()
    lo2 = -np.inf if lo is None else lo
    hi2 = np.inf if hi is None else hi
    mask = (y >= lo2) & (y <= hi2)
    y[mask] = np.nan
    return y


# ============================== 파일명/헤더 ==============================
def parse_timestamp(fname):
    """파일명 패턴 '카운터-YYMMDD-HHMMSS.csv' 에서 실제 날짜/시각을 추출."""
    name = os.path.splitext(os.path.basename(fname))[0]
    parts = name.split("-")
    if len(parts) >= 3:
        date_s, time_s = parts[-2], parts[-1]
        if len(date_s) == 6 and len(time_s) == 6 and date_s.isdigit() and time_s.isdigit():
            try:
                return datetime.strptime(date_s + time_s, "%y%m%d%H%M%S")
            except Exception:
                pass
    return None


def _decode_raw(raw_bytes):
    """인코딩 자동판별(utf-8-sig/cp949/euc-kr/utf-8)해서 텍스트로 반환."""
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return raw_bytes.decode(enc)
        except Exception:
            continue
    return raw_bytes.decode("utf-8", errors="ignore")


def _is_header_like(line):
    toks = [t.strip() for t in line.split(",")]
    if len(toks) < 5:
        return False
    alpha = sum(1 for t in toks if re.search("[A-Za-z]", t))
    return alpha >= len(toks) * 0.6


def find_header_line(lines, expect_row=7):
    """항목명(헤더) 줄의 인덱스를 찾는다. 8행(index=7)을 우선 확인 후 자동탐지로 보정."""
    if expect_row < len(lines) and _is_header_like(lines[expect_row]):
        return expect_row
    hdr = expect_row if expect_row < len(lines) else 0
    for i, l in enumerate(lines[:40]):
        if _is_header_like(l):
            hdr = i
    return hdr


def get_header_items(raw_bytes, expect_row=7):
    """raw data 파일의 헤더 줄(기본 8행)을 읽어 '항목(컬럼) 이름 목록'을 반환한다."""
    lines = _decode_raw(raw_bytes).splitlines()
    if not lines:
        return []
    hdr = find_header_line(lines, expect_row=expect_row)
    if hdr >= len(lines):
        return []
    cols = [c.strip() for c in lines[hdr].split(",")]
    cols = [c for c in cols if c]
    if cols and re.search("time|시간", cols[0], re.I):
        cols = cols[1:]
    return cols


def load_csv(raw_bytes, usecols=None):
    """헤더 줄 자동탐지(8행 우선) + footer 자동 제거 + 인코딩 자동."""
    txt = _decode_raw(raw_bytes)
    lines = txt.splitlines()
    hdr = find_header_line(lines)

    def _read(engine):
        kwargs = dict(skiprows=hdr, engine=engine, on_bad_lines="skip")
        if usecols is not None:
            header_line = lines[hdr] if hdr < len(lines) else ""
            header_cols = [c.strip() for c in header_line.split(",")]
            keep = [c for c in usecols if c in header_cols]
            if keep:
                kwargs["usecols"] = keep
        return pd.read_csv(io.StringIO(txt), **kwargs)

    try:
        df = _read("c")
    except Exception:
        df = _read("python")

    df.columns = [str(c).strip() for c in df.columns]
    first = df.columns[0]
    df = df[~df[first].astype(str).str.contains("Time", na=False, case=False)]
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(how="all").reset_index(drop=True)


# ============================== 요약 통계 ==============================
def _summary_worker(args):
    hr, raw_bytes, focus_items = args
    try:
        df = load_csv(raw_bytes, usecols=focus_items)
    except Exception:
        return hr, {}, set(), 0
    cols_found = set(df.columns)
    nrows = len(df)
    rec = {}
    for it in focus_items:
        if it in df.columns:
            s = df[it].dropna()
            if len(s) == 0:
                continue
            m, sd = s.mean(), s.std()
            rec[f"{it}_평균"] = m
            rec[f"{it}_최대"] = s.max()
            rec[f"{it}_최소"] = s.min()
            rec[f"{it}_표준편차"] = sd
            rec[f"{it}_이상"] = int(((s - m).abs() > 3 * sd).sum()) if sd and sd > 0 else 0
    return hr, rec, cols_found, nrows


def _runs_above(mask):
    runs = []
    n = len(mask)
    i = 0
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def _active_median_peak(values, threshold):
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) == 0 or threshold is None or threshold <= 0:
        return np.nan, np.nan
    mask = np.abs(v) > threshold
    if not mask.any():
        return np.nan, np.nan
    med = float(np.median(v[mask]))
    peaks = [float(np.max(np.abs(v[a:b]))) for a, b in _runs_above(mask)]
    peak_avg = float(np.mean(peaks)) if peaks else np.nan
    return med, peak_avg


def _active_stats_worker(args):
    hr, raw_bytes, items, threshold_map = args
    try:
        df = load_csv(raw_bytes, usecols=items)
    except Exception:
        return hr, {}
    rec = {}
    for it in items:
        thr = threshold_map.get(it)
        if it in df.columns and thr:
            med, pk = _active_median_peak(df[it].to_numpy(), thr)
            rec[f"{it}_동작구간 중앙값"] = med
            rec[f"{it}_동작구간 피크평균"] = pk
    return hr, rec


def scan_files(uploaded):
    """uploaded: [(filename, bytes), ...] -> 시간순 정렬 후 {seq: (filename, bytes)}"""
    items = list(uploaded)

    def sort_key(item):
        fname, _ = item
        ts = parse_timestamp(fname)
        if ts is not None:
            return (0, ts, fname)
        return (1, fname)

    items.sort(key=sort_key)
    return {i: it for i, it in enumerate(items)}


def build_summary(files, focus_items, active_ratio=ACTIVE_RATIO_DEFAULT, progress_cb=None):
    """files: {seq: (filename, bytes)}
    반환: summary(DataFrame), file_ranges({seq:(start_h,end_h)}), columns(list), active_thresholds(dict)
    """
    rows = {}
    cols_found = set()
    nrows_map = {}
    to_compute = [(hr, raw, focus_items) for hr, (fname, raw) in files.items()]

    total = len(files)
    done = 0
    if to_compute:
        max_workers = min(16, (os.cpu_count() or 4) * 2)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_summary_worker, item): item for item in to_compute}
            for fut in as_completed(futs):
                hr, raw, _ = futs[fut]
                try:
                    hr2, rec, cols, nrows = fut.result()
                except Exception:
                    rec, cols, nrows = {}, set(), 0
                rows[hr] = rec
                cols_found |= cols
                nrows_map[hr] = nrows
                done += 1
                if progress_cb:
                    progress_cb(done, total)

    file_ranges = {}
    cum = 0.0
    for hr in sorted(files.keys()):
        dur_h = nrows_map.get(hr, 0) * DT / 3600.0
        start = cum
        cum += dur_h
        file_ranges[hr] = (start, cum)

    summary = pd.DataFrame(rows).T.sort_index()
    summary["누적작동시간(h)"] = [file_ranges.get(hr, (0, 0))[1] for hr in summary.index]
    columns = [c for c in focus_items if c in cols_found]

    # 신뢰성 분석용 동작구간 통계(Stage B)
    threshold_map = {}
    for it in columns:
        col = f"{it}_최대"
        if col in summary.columns:
            mx = summary[col].abs()
            mx = mx[np.isfinite(mx)]
            if len(mx) > 0:
                thr = float(np.median(mx)) * active_ratio
                if thr > 0:
                    threshold_map[it] = thr

    rows2 = {}
    to_compute2 = [(hr, files[hr][1], list(threshold_map.keys()), threshold_map)
                   for hr in files.keys()] if threshold_map else []
    if to_compute2:
        max_workers = min(16, (os.cpu_count() or 4) * 2)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_active_stats_worker, item): item for item in to_compute2}
            for fut in as_completed(futs):
                hr, raw, _, _ = futs[fut]
                try:
                    hr2, rec2 = fut.result()
                except Exception:
                    rec2 = {}
                rows2[hr] = rec2

    if rows2:
        df2 = pd.DataFrame(rows2).T
        for c in df2.columns:
            summary[c] = df2[c].reindex(summary.index)

    return summary, file_ranges, columns, threshold_map


def find_seq_by_cumhour(file_ranges, target_h):
    """target_h(누적 작동시간)에 해당하는 파일 seq를 찾는다."""
    if not file_ranges:
        return None
    items = sorted(file_ranges.items(), key=lambda kv: kv[1][0])
    for seq, (s, e) in items:
        if s - 1e-9 <= target_h <= e + 1e-9:
            return seq, s, e
    best = min(items, key=lambda kv: min(abs(kv[1][0] - target_h), abs(kv[1][1] - target_h)))
    return best[0], best[1][0], best[1][1]


# ============================== 추세 적합/예측 ==============================
def fit_linear(h, y):
    a, b = np.polyfit(h, y, 1)
    pred = a * h + b
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"kind": "선형", "params": (a, b), "r2": r2,
            "f": lambda x, a=a, b=b: a * x + b}


def fit_exp(h, y):
    """y = A * exp(B*h). y<=0 포함이면 적용 불가(None 반환)."""
    if np.any(y <= 0):
        return None
    logy = np.log(y)
    B, logA = np.polyfit(h, logy, 1)
    A = np.exp(logA)
    pred = A * np.exp(B * h)
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"kind": "지수", "params": (A, B), "r2": r2,
            "f": lambda x, A=A, B=B: A * np.exp(B * x)}


def best_model(h, y):
    """선형/지수 모델을 적합해 R²가 더 좋은 쪽을 채택."""
    h = np.asarray(h, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = ~np.isnan(y)
    h, y = h[ok], y[ok]
    if len(h) < 2:
        return None
    cands = [fit_linear(h, y)]
    exp_m = fit_exp(h, y)
    if exp_m is not None:
        cands.append(exp_m)
    cands.sort(key=lambda m: m["r2"], reverse=True)
    return cands[0]


def predict_cross(model, h_now, limit):
    """model 추세를 h_now 이후로 연장해 limit(USL/LSL)에 도달하는 시점을 계산."""
    if model is None or limit is None:
        return None
    span = max(h_now, 1.0)
    grid = np.linspace(h_now, h_now + span * 5, 20000)
    vals = model["f"](grid)
    now_val = model["f"](np.array([h_now]))[0]
    if now_val <= limit:
        cross_mask = vals >= limit
    else:
        cross_mask = vals <= limit
    idx = np.argmax(cross_mask) if cross_mask.any() else -1
    if idx <= 0:
        return None
    return float(grid[idx])


def detect_ttf(hours, ymax, ymin, lsl, usl, persist_ratio=0.7):
    """항목 1개에 대해 스펙(LSL/USL) 최초 이탈 시점을 찾고 영구/일시적 여부를 구분."""
    hours = np.asarray(hours, dtype=float)
    ymax = np.asarray(ymax, dtype=float)
    ymin = np.asarray(ymin, dtype=float)
    breach = np.zeros(len(hours), dtype=bool)
    if usl is not None:
        breach |= (ymax > usl)
    if lsl is not None:
        breach |= (ymin < lsl)
    if not breach.any():
        return None
    first = int(np.argmax(breach))
    after = breach[first:]
    persist = float(np.mean(after)) if len(after) else 0.0
    kind = "영구(고장 추정)" if persist >= persist_ratio else "일시적(노이즈 추정)"
    peak_val = ymax[first] if (usl is not None and ymax[first] > usl) else ymin[first]
    return {"h": float(hours[first]), "value": float(peak_val), "kind": kind, "persist": persist}
