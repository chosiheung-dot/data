# -*- coding: utf-8 -*-
"""
trend_calc.py
내구시험 추세 분석기(Trend Analyzer) - 계산 로직 모듈
원본 데스크톱 프로그램(tkinter, app.py v13)의 계산 함수를 그대로 이식.
- 원본과의 유일한 차이: 폴더를 tkinter filedialog로 여는 대신,
  ① 서버에서 직접 접근 가능한 "폴더 경로 문자열"을 입력받거나(로컬 실행 시)
  ② 웹 업로드된 파일들(bytes)을 받는 두 가지 입력 방식을 모두 지원한다.
  (그 외 헤더탐지/누적작동시간/동작구간 통계/추세적합/TTF·RUL 계산 로직은 원본과 동일)
"""
import os, re, glob, io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd

FOCUS_ITEMS = ["Cmd1", "FB1", "Spd1", "Cur1", "Cmd2", "FB2", "Spd2", "Cur2",
               "Cmd3", "FB3", "Spd3", "Cur3", "Pvtg"]
DT = 0.1  # 1행당 초 (샘플링 간격)
ACTIVE_RATIO_DEFAULT = 0.2
SUMMARY_VER = 2


# =============================== 파일 판독 ===============================
def decode_raw(path):
    """경로(str)를 읽어 인코딩 자동판별(utf-8-sig/cp949/euc-kr/utf-8) 텍스트로 반환."""
    raw = open(path, "rb").read()
    return _decode_raw_bytes(raw)


def _decode_raw_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def parse_timestamp(fname):
    """파일명 패턴 '카운터-YYMMDD-HHMMSS.csv' 에서 실제 날짜/시각 추출. 실패 시 None."""
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
    """raw data 텍스트의 헤더 줄(기본 8행)을 읽어 항목(컬럼) 이름 목록을 반환."""
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


def load_csv_text(txt, usecols=None):
    """헤더 줄 자동탐지(8행 우선) + footer 자동 제거 + 숫자 변환."""
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


# =============================== 파일 스캔(폴더 경로 or 업로드) ===============================
def scan_folder(folder_path):
    """서버에서 접근 가능한 폴더 경로를 스캔해 '실제 저장 시각' 기준으로 정렬한
    {seq: path} 딕셔너리를 반환한다. (원본 _scan_files와 동일 로직)"""
    paths = glob.glob(os.path.join(folder_path, "*.csv")) + glob.glob(os.path.join(folder_path, "*.CSV"))
    paths = sorted(set(paths))

    def sort_key(p):
        ts = parse_timestamp(p)
        if ts is not None:
            return (0, ts, p)
        return (1, os.path.getmtime(p), p)

    paths.sort(key=sort_key)
    return {i: p for i, p in enumerate(paths)}, {i: decode_raw(p) for i, p in enumerate(paths)}


def scan_uploaded(files_info):
    """files_info: [(filename, raw_bytes), ...] 업로드된 파일들을 '파일명 속 타임스탬프'
    기준으로 정렬(원본과 동일), 텍스트로 디코딩해 {seq: name}, {seq: text} 반환."""
    items = [(name, _decode_raw_bytes(raw)) for name, raw in files_info]

    def sort_key(item):
        name, _ = item
        ts = parse_timestamp(name)
        return (0, ts) if ts else (1, name)

    items.sort(key=sort_key)
    names = {i: it[0] for i, it in enumerate(items)}
    texts = {i: it[1] for i, it in enumerate(items)}
    return names, texts


# =============================== 요약 통계 빌드 ===============================
def _summary_worker(args):
    hr, txt, focus_items = args
    try:
        df = load_csv_text(txt, usecols=focus_items)
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
            rec[f"{it}_평균"] = m; rec[f"{it}_최대"] = s.max()
            rec[f"{it}_최소"] = s.min(); rec[f"{it}_표준편차"] = sd
            rec[f"{it}_이상"] = int(((s - m).abs() > 3 * sd).sum()) if sd and sd > 0 else 0
    return hr, rec, cols_found, nrows


def _runs_above(mask):
    runs = []
    n = len(mask); i = 0
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            runs.append((i, j)); i = j
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
    hr, txt, items, threshold_map = args
    rec = {}
    if not items:
        return hr, rec
    try:
        df = load_csv_text(txt, usecols=items)
    except Exception:
        return hr, rec
    for it in items:
        thr = threshold_map.get(it)
        if it in df.columns and thr:
            med, pk = _active_median_peak(df[it].to_numpy(), thr)
            rec[f"{it}_동작구간 중앙값"] = med
            rec[f"{it}_동작구간 피크평균"] = pk
    return hr, rec


def build_summary(seqs_texts, focus_items, active_ratio=ACTIVE_RATIO_DEFAULT, progress_cb=None):
    """seqs_texts: {seq(int, 시간순): raw_text(str)}.
    반환: (summary DataFrame, columns_found(list), active_thresholds(dict))
    원본 _build_summary()와 동일 로직(캐시만 제외, 매 실행 새로 계산)."""
    rows = {}; cols_found = set(); nrows_map = {}
    items_to_compute = [(hr, txt, focus_items) for hr, txt in seqs_texts.items()]
    total = len(items_to_compute); done = 0
    if progress_cb: progress_cb(done, total)

    max_workers = min(32, (os.cpu_count() or 4) * 4)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_summary_worker, item): item for item in items_to_compute}
        for fut in as_completed(futs):
            hr, _, _ = futs[fut]
            try:
                hr2, rec, cols, nrows = fut.result()
            except Exception:
                rec, cols, nrows = {}, set(), 0
            rows[hr] = rec; cols_found |= cols; nrows_map[hr] = nrows
            done += 1
            if progress_cb: progress_cb(done, total)

    # ★ 누적 작동시간(h): seq 순서대로 각 파일의 실제 지속시간(행개수*0.1초)만 누적합산
    file_ranges = {}
    cum = 0.0
    for hr in sorted(seqs_texts.keys()):
        dur_h = nrows_map.get(hr, 0) * DT / 3600.0
        start = cum; cum += dur_h
        file_ranges[hr] = (start, cum)

    summary = pd.DataFrame(rows).T.sort_index()
    summary["누적작동시간(h)"] = [file_ranges.get(hr, (0, 0))[1] for hr in summary.index]
    columns = [c for c in focus_items if c in cols_found]

    # 동작구간 통계(Stage B): 전체 파일 최댓값들의 median * ratio 를 임계값으로 사용
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
    to_compute2 = [(hr, txt, list(threshold_map.keys()), threshold_map) for hr, txt in seqs_texts.items()]
    if to_compute2 and threshold_map:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_active_stats_worker, item): item for item in to_compute2}
            for fut in as_completed(futs):
                hr, _, _, _ = futs[fut]
                try:
                    hr2, rec2 = fut.result()
                except Exception:
                    rec2 = {}
                rows2[hr] = rec2

    if rows2:
        active_df = pd.DataFrame(rows2).T
        for c in active_df.columns:
            summary[c] = active_df[c]

    return summary, columns, threshold_map, file_ranges


# =============================== 노이즈필터 / 제외범위 ===============================
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


# =============================== 추세적합 / TTF / RUL ===============================
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
    """model 추세를 h_now 이후로 연장해 limit(USL/LSL)에 도달하는 시점을 계산.
    관찰기간의 5배를 넘는 예측은 신뢰도가 낮다고 보고 컷(None)."""
    if model is None or limit is None:
        return None
    span = max(h_now, 1.0)
    grid = np.linspace(h_now, h_now + span * 5, 20000)
    vals = model["f"](grid)
    if limit >= 0:
        cross_mask = vals >= limit if model["params"][0] >= 0 else vals <= limit
    else:
        cross_mask = vals <= limit if model["params"][0] <= 0 else vals >= limit
    # 값이 limit 방향으로 접근하는 경우를 일반화: 초기값과 limit의 대소관계로 판단
    y0 = model["f"](np.array([h_now]))[0]
    if y0 < limit:
        cross_mask = vals >= limit
    else:
        cross_mask = vals <= limit
    idx = int(np.argmax(cross_mask)) if cross_mask.any() else -1
    if idx <= 0:
        return None
    return float(grid[idx])


def detect_ttf(hours, ymax, ymin, lsl, usl, persist_ratio=0.7):
    """항목 1개에 대해 스펙(LSL/USL) 최초 이탈 시점을 찾고, 이후 지속 여부로
    '영구(고장 추정)' / '일시적(노이즈 추정)'을 구분."""
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
