
# -*- coding: utf-8 -*-
"""
reliability_calc.py
가속시험 통합계산기 - 계산 로직 모듈
① 온도가속(Arrhenius), ② 온습도가속(Peck), ③ 열피로가속(Coffin-Manson/Norris-Landzberg),
④ Weibull 시험시간비, ⑤ 수명데이터 분석(Weibull MLE)
"""
import math
import numpy as np

K_BOLTZMANN = 8.617333262e-5  # eV/K

def to_kelvin(temp_c: float) -> float:
    return temp_c + 273.15

# ---------------------------------------------------------------------------
# ① 온도가속 (Arrhenius)
# ---------------------------------------------------------------------------
def arrhenius_af(ea_ev: float, t_use_c: float, t_test_c: float) -> float:
    """가속계수 AF = exp( Ea/k * (1/Tuse - 1/Ttest) )"""
    tu = to_kelvin(t_use_c)
    tt = to_kelvin(t_test_c)
    return math.exp((ea_ev / K_BOLTZMANN) * (1.0 / tu - 1.0 / tt))

def arrhenius_test_time(field_hours: float, ea_ev: float, t_use_c: float, t_test_c: float) -> float:
    af = arrhenius_af(ea_ev, t_use_c, t_test_c)
    return field_hours / af

# ---------------------------------------------------------------------------
# ② 온습도가속 (Peck)
# ---------------------------------------------------------------------------
def peck_af(ea_ev: float, n: float, t_use_c: float, t_test_c: float,
            rh_use: float, rh_test: float) -> float:
    """AF = (RHtest/RHuse)^n * exp( Ea/k * (1/Tuse - 1/Ttest) )"""
    tu = to_kelvin(t_use_c)
    tt = to_kelvin(t_test_c)
    af_temp = math.exp((ea_ev / K_BOLTZMANN) * (1.0 / tu - 1.0 / tt))
    af_rh = (rh_test / rh_use) ** n
    return af_temp * af_rh

def peck_test_time(field_hours: float, ea_ev: float, n: float,
                    t_use_c: float, t_test_c: float, rh_use: float, rh_test: float) -> float:
    af = peck_af(ea_ev, n, t_use_c, t_test_c, rh_use, rh_test)
    return field_hours / af

# ---------------------------------------------------------------------------
# ③ 열피로가속 (Coffin-Manson / Norris-Landzberg)
# ---------------------------------------------------------------------------
def coffin_manson_af(dt_use: float, dt_test: float, m: float) -> float:
    """AF = (ΔT_test/ΔT_use)^m"""
    return (dt_test / dt_use) ** m

def norris_landzberg_af(dt_use: float, dt_test: float, m: float,
                         f_use_hz: float, f_test_hz: float,
                         ea_ev: float, t_max_use_c: float, t_max_test_c: float) -> float:
    """AF = (ΔTtest/ΔTuse)^m * (f_use/f_test)^(1/3) * exp( Ea/k*(1/Tmax_use - 1/Tmax_test) )"""
    tu = to_kelvin(t_max_use_c)
    tt = to_kelvin(t_max_test_c)
    term_dt = (dt_test / dt_use) ** m
    term_f = (f_use_hz / f_test_hz) ** (1.0 / 3.0)
    term_ea = math.exp((ea_ev / K_BOLTZMANN) * (1.0 / tu - 1.0 / tt))
    return term_dt * term_f * term_ea

def thermal_cycle_test_time(field_cycles: float, af: float) -> float:
    return field_cycles / af

# ---------------------------------------------------------------------------
# ④ Weibull 시험시간비 (신뢰수준/신뢰도 기반 시험시간 산출, 무고장시험)
# ---------------------------------------------------------------------------
def weibull_test_ratio(reliability: float, confidence: float, beta: float, n_samples: int) -> float:
    """
    무고장시험에서 요구 신뢰도 R, 신뢰수준 C를 만족하기 위한
    시험시간/목표수명 비율(test time ratio)을 계산.
    r=0(무고장) 가정, 카이제곱 근사 대신 표준식 사용:
        ratio = [ -ln(C) / (n * -ln(R)) ] ^ (1/beta)  ... (근사, 무고장시험 표준식)
    보다 일반적인 식: n * (t/t_goal)^beta = -ln(C)/(-ln(R))  형태를 사용.
    """
    if not (0 < reliability < 1) or not (0 < confidence < 1):
        raise ValueError("신뢰도와 신뢰수준은 0~1 사이여야 합니다.")
    numer = -math.log(confidence)
    denom = n_samples * (-math.log(reliability))
    ratio = (numer / denom) ** (1.0 / beta)
    return ratio

def weibull_required_test_time(target_life: float, reliability: float, confidence: float,
                                beta: float, n_samples: int) -> float:
    ratio = weibull_test_ratio(reliability, confidence, beta, n_samples)
    return target_life * ratio

# ---------------------------------------------------------------------------
# ⑤ 수명데이터 분석 (Weibull MLE, 완전데이터 기준 + 우측중도절단 지원)
# ---------------------------------------------------------------------------
def weibull_mle(times: np.ndarray, censored: np.ndarray = None, max_iter: int = 200, tol: float = 1e-8):
    """
    2모수 Weibull MLE (Newton-Raphson).
    times: 고장/중단 시간 배열
    censored: 같은 길이의 bool 배열. True면 우측중도절단(suspension), False면 고장(failure)
    반환: (beta_hat, eta_hat)
    """
    times = np.asarray(times, dtype=float)
    if censored is None:
        censored = np.zeros_like(times, dtype=bool)
    else:
        censored = np.asarray(censored, dtype=bool)

    failed = ~censored
    if failed.sum() < 2:
        raise ValueError("MLE 추정을 위해서는 최소 2개 이상의 고장 데이터가 필요합니다.")

    # 초기값: 관측 실패 데이터의 로그평균/표준편차 기반
    log_t = np.log(times[failed])
    beta0 = 1.2 / (np.std(log_t) + 1e-9)
    beta = max(beta0, 0.3)

    def d_loglik_dbeta(beta):
        t_b = times ** beta
        s1 = np.sum(t_b * np.log(times))
        s2 = np.sum(t_b)
        n_f = failed.sum()
        term1 = n_f / beta
        term2 = np.sum(np.log(times[failed]))
        term3 = n_f * s1 / s2
        return term1 + term2 - term3

    def d2_loglik_dbeta2(beta, h=1e-5):
        return (d_loglik_dbeta(beta + h) - d_loglik_dbeta(beta - h)) / (2 * h)

    for _ in range(max_iter):
        f = d_loglik_dbeta(beta)
        fp = d2_loglik_dbeta2(beta)
        if abs(fp) < 1e-12:
            break
        step = f / fp
        new_beta = beta - step
        if new_beta <= 0:
            new_beta = beta / 2
        if abs(new_beta - beta) < tol:
            beta = new_beta
            break
        beta = new_beta

    eta = (np.sum(times ** beta) / failed.sum()) ** (1.0 / beta)
    return beta, eta

def weibull_mttf(beta: float, eta: float) -> float:
    from math import gamma
    return eta * gamma(1.0 + 1.0 / beta)

def weibull_bxx(beta: float, eta: float, x_percent: float) -> float:
    """B_xx life: 누적고장률 xx%에 도달하는 시간"""
    p = x_percent / 100.0
    return eta * (-math.log(1.0 - p)) ** (1.0 / beta)

def weibull_reliability(t: float, beta: float, eta: float) -> float:
    return math.exp(-((t / eta) ** beta))

def weibull_cdf(t: float, beta: float, eta: float) -> float:
    return 1.0 - weibull_reliability(t, beta, eta)

# ---------------------------------------------------------------------------
# 참고 DB (대표적으로 자주 쓰이는 항목들 - 실무 참고용 예시 데이터)
# ---------------------------------------------------------------------------
EA_DB = [
    ("Capacitor, Aluminum Electrolytic", 0.4, 0.6),
    ("Capacitor, Mylar", 0.3, 0.5),
    ("Capacitor, Paper", 0.4, 0.6),
    ("Capacitor, Polycarbonate", 0.3, 0.5),
    ("Capacitor, Polyester", 0.3, 0.5),
    ("Capacitor, Tantalum", 0.3, 0.5),
    ("Capacitor, Ceramic (MLCC)", 0.8, 1.2),
    ("Resistor, Carbon Composition", 0.3, 0.5),
    ("Resistor, Film", 0.3, 0.5),
    ("Resistor, Wirewound", 0.4, 0.6),
    ("Diode, Silicon", 0.3, 0.7),
    ("Diode, Zener", 0.5, 0.8),
    ("Transistor, Bipolar (BJT)", 0.6, 0.9),
    ("Transistor, MOSFET", 0.3, 0.6),
    ("IC, CMOS Logic", 0.6, 0.8),
    ("IC, Bipolar Logic", 0.5, 0.7),
    ("IC, Memory (EEPROM)", 0.6, 1.0),
    ("Connector, Contact Corrosion", 0.4, 0.6),
    ("Connector, Fretting Corrosion", 0.3, 0.5),
    ("Solder Joint, Corrosion", 0.5, 0.7),
    ("Relay, Contact Wear", 0.4, 0.7),
    ("Switch, Mechanical", 0.3, 0.5),
    ("Battery, Li-ion Capacity Fade", 0.4, 0.6),
    ("LED, Luminous Degradation", 0.3, 0.6),
    ("Motor, Bearing Lubricant", 0.5, 0.8),
    ("Motor, Winding Insulation", 0.8, 1.4),
    ("Wire Insulation, PVC", 0.6, 1.0),
    ("Wire Insulation, XLPE", 0.7, 1.2),
    ("Plastic Housing, UV/Thermal Aging", 0.5, 0.9),
    ("Rubber Seal, Compression Set", 0.5, 0.9),
    ("Adhesive, Bond Strength Degradation", 0.4, 0.8),
    ("PCB, Delamination", 0.6, 1.0),
    ("Sensor, Drift", 0.4, 0.7),
    ("Fuse, Element Fatigue", 0.4, 0.6),
    ("Optocoupler, CTR Degradation", 0.5, 0.8),
    ("Crystal Oscillator, Frequency Drift", 0.3, 0.5),
    ("EMC Filter, Core Loss", 0.4, 0.6),
    ("Thermistor, NTC Drift", 0.3, 0.5),
    ("Varistor, MOV Degradation", 0.5, 0.8),
    ("Fan, Bearing Wear", 0.5, 0.8),
    ("Cable, Shield Corrosion", 0.4, 0.6),
]

M_EXPONENT_GUIDE = [
    ("Solder Joint (Coffin-Manson, 일반)", 1.9, 2.6,
     "SnPb/SAC 솔더 조인트 열피로 파괴 표준 문헌값 범위"),
    ("Ceramic Package (Large CTE mismatch)", 3.0, 4.0,
     "세라믹-보드 간 CTE 미스매치가 큰 경우 m값 증가"),
    ("Wire Bond Fatigue", 4.0, 6.0,
     "와이어본드 열피로 파괴 (IPC-9701 등 참고)"),
    ("Norris-Landzberg 일반 전자부품", 2.0, 2.65,
     "Norris-Landzberg 모델 표준 계수 (JEDEC JESD22-A104 참고)"),
]

WEIBULL_REF_DB = [
    ("Ball bearings", 1.3, "구름 베어링 - 마모/피로 파괴 초기"),
    ("Electric motors (bearing wear-out)", 1.3, "전동기 베어링 마모 마모고장기"),
    ("Solder joint fatigue (SAC305)", 2.0, "SAC305 솔더 조인트 열피로"),
    ("Solder joint fatigue (SnPb)", 2.3, "SnPb 솔더 조인트 열피로"),
    ("Capacitor, Aluminum Electrolytic (wear-out)", 3.0, "전해커패시터 전해액 건조 마모고장"),
    ("MLCC (dielectric breakdown)", 2.0, "적층세라믹콘덴서 절연파괴"),
    ("LED (lumen degradation)", 2.5, "LED 광속 저하"),
    ("Relay contacts (wear)", 1.5, "릴레이 접점 마모"),
    ("Connector (fretting corrosion)", 1.8, "커넥터 프레팅 부식"),
    ("Hard disk drive (mechanical wear-out)", 2.0, "HDD 기계적 마모고장"),
    ("Fan bearing (lubricant depletion)", 2.5, "팬 베어링 윤활유 고갈"),
    ("Gear tooth fatigue", 2.5, "기어 이 피로파괴"),
    ("Spring fatigue", 2.2, "스프링 피로파괴"),
    ("Electronic component (infant mortality)", 0.5, "초기고장기 전자부품 (DFR 특성)"),
    ("Electronic component (random failure)", 1.0, "우발고장기 (지수분포에 근사)"),
    ("Mechanical wear-out (general)", 3.0, "일반 기계부품 마모고장"),
    ("Battery capacity fade (Li-ion)", 2.0, "리튬이온 배터리 용량저하"),
    ("Semiconductor (TDDB)", 1.5, "반도체 시간종속절연파괴"),
    ("Semiconductor (Electromigration)", 2.0, "반도체 일렉트로마이그레이션"),
    ("Rubber seal (compression set)", 1.8, "고무 씰 압축영구줄음"),
]
