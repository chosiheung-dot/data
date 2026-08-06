# -*- coding: utf-8 -*-
"""
추세 분석기(Trend Analyzer) 계산 로직 모듈
- CSV 자동헤더탐지 로더 / 노이즈필터 / 누적작동시간 / 추세적합(선형·지수) / TTF·RUL 판정
원본 데스크톱 프로그램(app.py)의 계산 로직을 그대로 옮긴 것입니다.
"""
import os, re, io
from datetime import datetime
import numpy as np
import pandas as pd

DT = 0.1  # 1행당 초 (샘플링 간격)


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


def _decode_raw_bytes(raw):
    """인코딩 자동판별(utf-8-sig/cp949/euc-kr/utf-8)해서 텍스트로 반환."""
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def decode_raw(path):
    raw = open(path, "rb").read()
    return _decode_raw_bytes(raw)


def _is_header_like(line):
    toks = [t.strip() for t in line.split(",")]
    if len(toks) < 5:
        return False
    alpha = sum(1 for t in toks if re.search("[A-Za-z]", t))
    return alpha >= len(toks) * 0.6


def find_header_line(lines, expect_row=7):
    if expect_row < len(lines) and _is_header_like(lines[expect_row]):
        return expect_row
    hdr = expect_row if expect_row < len(lines) else 0
    for i, l in enumerate(lines[:40]):
        if _is_header_like(l):
            hdr = i
    return hdr


def get_header_items(text, expect_row=7):
    """raw data 텍스트(파일 전체 문자열)의 헤더 줄을 읽어 항목(컬럼) 이름 목록을 반환."""
    lines = text.splitlines()
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


def load_csv_text(text, usecols=None):
    """헤더 줄 자동탐지 + footer 자동 제거. text는 파일 전체 문자열."""
    lines = text.splitlines()
    hdr = find_header_line(lines)

    def _read(engine):
        kwargs = dict(skiprows=hdr, engine=engine, on_bad_lines="skip")
        if usecols is not None:
            header_line = lines[hdr] if hdr < len(lines) else ""
            header_cols = [c.strip() for c in header_line.split(",")]
            keep = [c for c in usecols if c in header_cols]
            if keep:
                kwargs["usecols"] = keep
        return pd.read_csv(io.StringIO(text), **kwargs)

    try:
        df = _read("c")
    except Exception:
        df = _read("python")

    df.columns = [str(c).strip() for c in df.columns]
    if len(df.columns) == 0:
        return df
    first = df.columns[0]
    df = df[~df[first].astype(str).str.contains("Time", na=False, case=False)]
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(how="all").reset_index(drop=True)


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
        s2 = s.copy(); s2[mask] = np.nan
        return s2.interpolate(limit_direction="both").to_numpy()
    return s.to_numpy()


def apply_exclude(y, lo, hi):
    if lo is None and hi is None:
        return y
    y = np.asarray(y, dtype=float).copy()
    lo2 = -np.inf if lo is None else lo
    hi2 = np.inf if hi is None else hi
    mask = (y >= lo2) & (y <= hi2)
    y[mask] = np.nan
    return y


def summarize_file(text, focus_items):
    """파일 1개(텍스트) -> 항목별 통계 dict, 실제 존재 컬럼 set, 행개수(=누적작동시간 계산용)."""
    try:
        df = load_csv_text(text, usecols=focus_items)
    except Exception:
        return {}, set(), 0
    cols_found = set(df.columns)
    nrows = len(df)
    rec = {}
    for it in focus_items:
        if it in df.columns:
            s = df[it].dropna()
            if len(s) == 0:
                continue
            m, sd = s.mean(), s.std()
            rec[f"{it}_평균"] = m; rec[f"{it}_최대"] = s.max()
            rec[f"{it}_최소"] = s.min(); rec[f"{it}_표준편차"] = sd
            rec[f"{it}_이상"] = int(((s - m).abs() > 3 * sd).sum()) if sd and sd > 0 else 0
    return rec, cols_found, nrows


def cumulative_hours(nrows_list):
    """파일별 행개수 리스트 -> (각 파일까지의) 누적 작동시간(h) 리스트. 1행=0.1초 기준."""
    hours = []
    acc = 0.0
    for n in nrows_list:
        acc += n * DT / 3600.0
        hours.append(acc)
    return hours


ACTIVE_RATIO_DEFAULT = 0.2


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


def _fit_linear(h, y):
    a, b = np.polyfit(h, y, 1)
    pred = a * h + b
    ss_res = np.sum((y - pred) ** 2); ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"kind": "선형", "params": (a, b), "r2": r2, "f": lambda x, a=a, b=b: a * x + b}


def _fit_exp(h, y):
    if np.any(y <= 0):
        return None
    logy = np.log(y)
    B, logA = np.polyfit(h, logy, 1)
    A = np.exp(logA)
    pred = A * np.exp(B * h)
    ss_res = np.sum((y - pred) ** 2); ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"kind": "지수", "params": (A, B), "r2": r2, "f": lambda x, A=A, B=B: A * np.exp(B * x)}


def best_model(h, y):
    h = np.asarray(h, dtype=float); y = np.asarray(y, dtype=float)
    ok = ~np.isnan(y)
    h, y = h[ok], y[ok]
    if len(h) < 2:
        return None
    cands = [_fit_linear(h, y)]
    exp_m = _fit_exp(h, y)
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
    """스펙(LSL/USL) 최초 이탈 시점 + 영구/일시적 판정."""
    hours = np.asarray(hours, dtype=float)
    ymax = np.asarray(ymax, dtype=float); ymin = np.asarray(ymin, dtype=float)
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
