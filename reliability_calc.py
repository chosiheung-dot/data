# -*- coding: utf-8 -*-
"""
reliability_calc.py
원본 데스크톱 프로그램(신뢰성분석.py, tkinter)의 계산 로직과 DB를 그대로 이식.
- 탭① 온도가속(Arrhenius)
- 탭② 온습도가속(Arrhenius-Peck)
- 탭③ 열피로가속(Thermal Cycling) - Coffin-Manson / Modified Norris-Landzberg
- 탭④ Weibull 시험시간비 계산기 + 참고 DB
- 탭⑤ 수명데이터 분석 - Weibull MLE -> MTTF/B10/B1/R(t) + 확률도표
"""
import math

K_BOLTZMANN = 8.6173e-05  # eV/K

# ============================================================
# DB : 활성화에너지 (Ea)
# ============================================================
EA_DB = [
    ('Capacitor, Aluminum Electrolytic', '0.81', 'EPRI NP-6408', 'Capacity Tol. 기준'),
    ('Capacitor, Mylar', '0.86', 'EPRI NP-6408', 'Capacity Tol. 기준'),
    ('Capacitor, Paper', '0.9', 'EPRI NP-6408', 'Capacity Tol. 기준'),
    ('Capacitor, Polycarbonate', '0.8', 'EPRI NP-6408', 'Capacity Tol. 기준'),
    ('Capacitor, Polyester', '0.86', 'EPRI NP-6408', 'Capacity Tol. 기준'),
    ('Capacitor, Tantalum', '1.27', 'EPRI NP-6408', 'Capacity Tol. 기준'),
    ('Capacitors, chlorinated diphenyl 0.5% azobenzene', '2', 'EPRI NP-1558', ''),
    ('Capacitors, chlorinated diphenyl kraft paper', '0.86', 'EPRI NP-1558', ''),
    ('Capacitors, chlorinated diphenyl kraft paper with 0.5% azobenzene', '1.5', 'EPRI NP-1558', ''),
    ('Capacitors, chlorinated diphenyl kraft paper with 5% azobenzene', '1.93', 'EPRI NP-1558', ''),
    ('Capacitors, chlorinated diphenyl. 0.5% anthraquinone', '1.53', 'EPRI NP-1558', ''),
    ('Capacitors, chlorinated diphenyl. No stabilizers', '1.17', 'EPRI NP-1558', ''),
    ('Capacitors, dielectric, tubular paper', '2.42', 'EPRI NP-1558', ''),
    ('Capacitors, metalized paper', '1.32', 'EPRI NP-1558', ''),
    ('Capacitors, titanium-titanium dioxide, thin film(@25℃-100℃)', '0.09', 'EPRI NP-1558', ''),
    ('Coils, Class A', '1.08', 'EPRI NP-6408', 'Elect Str.기준'),
    ('Diode', '1.13', 'EPRI NP-6408', 'Fail Rate(MTBF) 기준'),
    ('Diode, others', '1.13-2.77', 'EPRI NP-1558', ''),
    ('Diode, Si(-1960)', '1.14', 'EPRI NP-1558', ''),
    ('Diode, Si-general', '1.13-2.77', 'EPRI NP-1558', ''),
    ('Diode, Silicon, 1N673 & 1N696', '1.8', 'EPRI NP-1558', ''),
    ('Diode, varactors', '2.31-2.38', 'EPRI NP-1558', ''),
    ('Diodes, silicon, p-n-p-n', '1.41', 'EPRI NP-1558', ''),
    ('Diodes, silicon, varactors', '2.31-2.38', 'EPRI NP-1558', ''),
    ('Fuse, Ceramic', '3.91', 'EPRI NP-6408', 'Mech Creep 기준'),
    ('Fuse, Glass', '3.91', 'EPRI NP-6408', 'Mech Creep 기준'),
    ('IC', '1', 'EPRI NP-6408', 'Fail Rate(MTBF) 기준'),
    ('IC(Surface charge accumulation)', '1.0-1.05', 'David J. Klinger, et al.', 'AT&T Reliability Manual, Van Nostrand Reinhold, 1990'),
    ('IC(Charge injection)', '1.3', 'David J. Klinger, et al.', 'AT&T Reliability Manual, Van Nostrand Reinhold, 1990'),
    ('IC(Electromigration)', '0.5-1.2', 'David J. Klinger, et al.', 'AT&T Reliability Manual, Van Nostrand Reinhold, 1990'),
    ('IC(Corrosion)', '0.3-0.6', 'David J. Klinger, et al.', 'AT&T Reliability Manual, Van Nostrand Reinhold, 1990'),
    ('IC(Intermetallic growth)', '1.0-1.05', 'David J. Klinger, et al.', 'AT&T Reliability Manual, Van Nostrand Reinhold, 1990'),
    ('IC(Aluminum penetration into silicon)', '1.4-1.6', 'David J. Klinger, et al.', 'AT&T Reliability Manual, Van Nostrand Reinhold, 1990'),
    ('IC(SiO2중의 Na이온의 드리프트)', '1.0-1.4', '마쓰다 전기', '반도체디바이스의 신뢰성기술, 일과기련, 1988'),
    ('IC(Si-SiO2 계면의 슬로 트래핑)', '1', '마쓰다 전기', '반도체디바이스의 신뢰성기술, 일과기련, 1988'),
    ('IC(반전층의 생성)', '0.8-1.0', '마쓰다 전기', '반도체디바이스의 신뢰성기술, 일과기련, 1988'),
    ('IC(채널 효과)', '0.5', '마쓰다 전기', '반도체디바이스의 신뢰성기술, 일과기련, 1988'),
    ('IC(수분에 의한 이온 이동 가속)', '0.8', '마쓰다 전기', '반도체디바이스의 신뢰성기술, 일과기련, 1988'),
    ('IC(Al Corrosion)', '0.6-0.9', '마쓰다 전기', '반도체디바이스의 신뢰성기술, 일과기련, 1988'),
    ('IC(산화막의 파괴)', '0.6', '마쓰다 전기', '반도체디바이스의 신뢰성기술, 일과기련, 1988'),
    ('IC(금속간 화합물 성장)', '0.5-0.7', '마쓰다 전기', '반도체디바이스의 신뢰성기술, 일과기련, 1988'),
    ('IC(Gate Oxide Defect)', '0.7-0.5', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Intermetallic Defect)', '0.3', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Poly to Metal Defect)', '0.3', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Silicon Junction Defect)', '0.5-0.3', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Masking(Poly, Diff.. etc.) Defect)', '0.8', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Metallization Defect)', '0.5', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Electromigration)', '1.0-0.5', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Contamination(Surface and Bulk))', '1', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ("IC(Charge Loss(EPROM's))", '0.6', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Assembly(Bond, Die Att. etc.))', '0.5', 'INTEL', 'Components Quality and Reliability, 1991/92'),
    ('IC(Surface charges Inversion, Accumulation)', '1', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Oxide Pinholes)', '1', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Dielectric Breakdown(TDDB))', '0.3', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Charge Loss)', '0.8', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Electromigration, Large grain Al, glassivated)', '1', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Electromigration, Small grain Al)', '0.5', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Cu-Al/Cu-Si-Al sputtered)', '0.7', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Corrosion)', '0.6-0.7', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Intermetallic Growth)', '1', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Metal Scratches)', '0.5-0.7', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Silicon Defects)', '0.5', 'Motolola', 'Reliability & Quality, 1993'),
    ('IC(Mechanical wireshorts)', '0.3-0.4', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Diffusion and Bulk Defects)', '0.3-0.4', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Oxide Defects)', '0.3-0.4', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Top to Bottom Metal Short)', '0.5', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Electromigration)', '0.55', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Charge Trapping)', '0.06', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Electrolytic Corrosion)', '0.8-1.0', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Au-Al Intermetallics)', '0.8-2.0', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Au-Al Bond Degradation)', '1.0-2.2', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Ionic Contamination)', '1.02', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Alloy Pitting)', '1.77', 'Signetics', 'Reliability Handbook, 1992'),
    ('IC(Al electromigration)', '0.6-1.2', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Al stress migration)', '0.7-0.9', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Au-Al alloy growth)', '0.85-1.1', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Al corrosion)', '0.6-1.2', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Oxide breakdown)', '0.6-1.2', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Ion movement acceleration due to moisture)', '0.3-0.35', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Na ion drift in SiO2)', '0.8', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Slow trapping of Si-SiO2 Interface)', '1.0-1.4', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Inversion layer formation)', '1', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('IC(Na ion drift in SiO2)', '0.8-1.0', 'Toshiba', 'Semiconductor Reliability Handbook(Integrated Circuit), 1992'),
    ('Microcircuits, CMOS 4007 freak pop.', '0.9', 'EPRI NP-1558', ''),
    ('Microcircuits, CMOS 4008 main pop.', '1.3', 'EPRI NP-1558', ''),
    ('Microcircuits, CMOS type CD 4011A', '1.4', 'EPRI NP-1558', ''),
    ('Microcircuits, CMOS type CD 4013A', '1.1', 'EPRI NP-1558', ''),
    ('Microcircuits, CMOS type CD 4024A', '1', 'EPRI NP-1558', ''),
    ('Optical Coupler', '1', 'EPRI NP-6408', 'Fail Rate(Non-op) 기준'),
    ('SCR', '1', 'EPRI NP-5024', ''),
    ('semiconductor devices, silicon', '0.9-1.4', 'EPRI NP-1558', ''),
    ('Silicon Controled Rectifier', '1', 'EPRI NP-6408', 'Fail Rate(MTBF) 기준'),
    ('Transistor Si planar4A-2(1963)', '1.5', 'EPRI NP-1558', 'Constant Stress'),
    ('Transistor Si planar4A-2(1967)', '1.18', 'EPRI NP-1558', ''),
    ('Transistor Si planar4A-2(1968)', '1.29', 'EPRI NP-1558', 'Step Stress'),
    ('Transistor, bipolar, p-n-p-n', '1.65', 'EPRI NP-1558', ''),
    ('Transistor, Ge gettered', '1.24', 'EPRI NP-1558', ''),
    ('Transistor, Ge MADT, 2N501(1958)', '1.07', 'EPRI NP-1558', 'MADT=Micro Alloy Diffused Transistor'),
    ('Transistor, Ge MADT, 2N501(1959)', '1.07', 'EPRI NP-1558', ''),
    ('Transistor, Ge MAT, 2N393(1959, 1960)', '1', 'EPRI NP-1558', 'MAT=Micro Alloy Transistor'),
    ('Transistor, Ge mesa, 2N559(1958)', '1.17', 'EPRI NP-1558', ''),
    ('Transistor, Ge mesa, 2N559(1959)', '0.95', 'EPRI NP-1558', ''),
    ('Transistor, Ge mesa, 2N559(1960)', '1.14', 'EPRI NP-1558', ''),
    ('Transistor, Ge mesa, AF106(1969)', '1', 'EPRI NP-1558', ''),
    ('Transistor, Ge ungettered', '0.88', 'EPRI NP-1558', ''),
    ('Transistor, modern submarine cable', '1.4', 'EPRI NP-1558', ''),
    ('Transistor, Power, MSC 1330', '0.81', 'EPRI NP-1558', ''),
    ('Transistor, Si mesa, 2N1051(1960)', '1.12', 'EPRI NP-1558', ''),
    ('Transistor, Si mesa, 2N269(1961)', '0.58', 'EPRI NP-1558', ''),
    ('Transistor, Si mesa, 2N560(1959)', '1.12', 'EPRI NP-1558', ''),
    ('Transistor, Si mesa, 2N560(1960)', '1.5', 'EPRI NP-1558', ''),
    ('Transistor, Si, p-n-p-n', '1.65', 'EPRI NP-1558', ''),
    ('Transistor, Silicon, (all) at wear-out', '1.46', 'EPRI NP-1558', ''),
    ('Transistor, Silicon, (all) before wear-out', '1.12', 'EPRI NP-1558', 'with surface inversion failures'),
    ('Transistor, silicon, bipolar', '1.02', 'EPRI NP-1558', 'with Au-Al bond failures'),
    ('Transistor, silicon, bipolar', '1.02-1.04', 'EPRI NP-1558', ''),
    ('Transistor, silicon, bipolar', '1.77', 'EPRI NP-1558', 'with metal penetration into Si.'),
    ('Transistor, silicone mesa, 2N560', '2.16', 'EPRI NP-1558', ''),
    ('Transistor, Vycor gettered germanium, 2N559', '1.02', 'EPRI NP-1558', ''),
    ('Transistors', '1.02', 'EPRI NP-6408', 'Fail Rate(MTBF) 기준'),
    ('Transistors', '0.66', 'EPRI NP-1558', ''),
    ('Transistors, 2N559, vacuum baked', '0.89', 'EPRI NP-1558', ''),
    ('Transistors, CMOS', '1.18', 'EPRI NP-1558', ''),
    ('Transistors, diffused-germanium', '0.87', 'EPRI NP-1558', 'Constant stress tests with moisture getter'),
    ('Transistors, diffused-germanium', '1.24', 'EPRI NP-1558', 'Step-stress tests without moisture getter'),
    ('Transistors, Ge alloy, LT 123(1958)', '1.25', 'EPRI NP-1558', ''),
    ('Transistors, Ge alloyed, OC 1972(1964)', '1.26', 'EPRI NP-1558', ''),
    ('Transistors, Ge alloyed, OC 1972(1966)', '1.08', 'EPRI NP-1558', ''),
    ('Transistors, germanium', '0.17', 'EPRI NP-1558', ''),
    ('Transistors, germanium, @60℃', '0.99-1.26', 'EPRI NP-1558', ''),
    ('Transistors, germanium, gettered with vycor or molecular sieve', '1.24', 'EPRI NP-1558', ''),
    ('Transistors, germanium, ungettered', '0.88', 'EPRI NP-1558', ''),
    ('Transistors, MOS', '1.1 or 1.2', 'EPRI NP-1558', ''),
    ('Transistors, Si main pop.(1960)', '1.02', 'EPRI NP-1558', ''),
    ('Transistors, Si planar, BFY 33(1969)', '1.12', 'EPRI NP-1558', ''),
    ('Transistors, silicon, typical', '0.96', 'EPRI NP-1558', 't10 lifeline'),
    ('Transistors, silicon, typical', '1.11', 'EPRI NP-1558', 't50 lifeline'),
    ('Transistors, submarine-cable', '1.3', 'EPRI NP-1558', '0.025% failure'),
    ('Transistors, submarine-cable', '1.24', 'EPRI NP-1558', '50% failure'),
    ('OLED 소자', '0.3', '정보디스플레이공학(책)', ''),
    ('전자제품', '0.3~0.7', '기업에서 관행적 적용', ''),
    ('전자부품', '0.2~1.2', '기업에서 관행적 적용', ''),
    ('LCD', '0.6', '기업에서 관행적 적용', ''),
    ('노트북', '0.5', '기업에서 관행적 적용', ''),
    ('TV', '0.55', '기업에서 관행적 적용', ''),
    ('PDP module', '0.49', '기업에서 관행적 적용', ''),
    ('OLED module', '0.4', '기업에서 관행적 적용', ''),
    ('Battery Management System', '0.45', '기업에서 관행적 적용', ''),
    ('VCR', '0.39', '기업에서 관행적 적용', ''),
    ('노트북', '0.46', '기업에서 관행적 적용', ''),
    ('대표치(시스템 또는 모듈)', '0.5', '기업에서 관행적 적용', ''),
    ('Natural Rubber', '0.8', '한국화학융합시험연구원', ''),
    ('NBR', '0.93', '한국화학융합시험연구원', ''),
    ('H-NBR', '0.3', '한국화학융합시험연구원', ''),
    ('EPDM', '0.7-0.86', '한국화학융합시험연구원', ''),
    ('자동차용 전장품(대표치)', '0.8', 'GMW 3172', '가속시험설계시 사용하고, 시험결과로 부터 재산출'),
    ('OLED 소자(시험설계/Spec 개발적용)', '0.3', '정보디스플레이공학(책)', ''),
    ('전자제품(시험설계/Spec 개발적용)', '0.3~0.7', '', ''),
    ('전자부품(시험설계/Spec 개발적용)', '0.2~1.2', '', ''),
    ('LCD(시험설계/Spec 개발적용)', '0.6', '', ''),
    ('노트북(시험설계/Spec 개발적용)', '0.5', '', ''),
    ('TV(시험설계/Spec 개발적용)', '0.55', '', ''),
    ('PDP module(시험설계/Spec 개발적용)', '0.49', '', ''),
    ('OLED module(시험설계/Spec 개발적용)', '0.4', '', ''),
    ('Battery Management System(시험설계/Spec 개발적용)', '0.45', '', ''),
    ('VCR(시험설계/Spec 개발적용)', '0.39', '', ''),
    ('노트북(시험설계/Spec 개발적용)2', '0.46', '', ''),
    ('대표치(시스템 또는 모듈)(시험설계/Spec 개발적용)', '0.5', '한국자동차연구원 추천', ''),
    ('H.Livingston (2002)', '3', '', ''),
    ('Brizout, et.al (1992)', '2.66', '', ''),
    ('Philps (@HAST)', '4.6', '', ''),
    ('SEMATECH', '2.7', '', ''),
    ('대표치(아레니우스 특성 지수)', '3', '', ''),
    ('정류자 다이오드(Voltage)', '2.43', 'H.Livingston (2002)', ''),
    ('레이저 다이오드(Voltage)', '2.8', '', ''),
    ('NR(고무소재)', '0.74~0.84', '한국화학융합시험연구원', ''),
    ('EPDM(고무소재)', '0.77~0.89', '한국화학융합시험연구원', ''),
    ('Oxide(Failure Mechanism)', '0.8', 'ADI Reliability Handbook', ''),
    ('Contamination(Failure Mechanism)', '1.4', 'ADI Reliability Handbook', ''),
    ('Silicon Junction Defects(Failure Mechanism)', '0.8', 'ADI Reliability Handbook', ''),
    ('Defect of oxide film', '0.3 eV to 1.1 eV', 'Failure Mechanism of Semiconductor Devices @panasonic', ''),
    ('Drift of ionicity (Na ions in oxide film)', '0.3 eV to 1.8 eV', 'Failure Mechanism of Semiconductor Devices @panasonic', ''),
    ('Slow trap', '0.8 eV to 1.2 eV', 'Failure Mechanism of Semiconductor Devices @panasonic', ''),
    ('Electromigration disconnection', 'for Al wire: 0.5 eV to 0.7 eV', 'Failure Mechanism of Semiconductor Devices @panasonic', ''),
    ('Electromigration disconnection(Cu wire)', 'for Cu wire: 0.8 eV to 1.0 eV', 'Failure Mechanism of Semiconductor Devices @panasonic', ''),
    ('Metal(Al) corrosion', '0.7 eV to 0.9 eV', 'Failure Mechanism of Semiconductor Devices @panasonic', ''),
    ('Growth of compound between metals(Au-Al)', '1.0 eV to 1.3 eV', 'Failure Mechanism of Semiconductor Devices @panasonic', ''),
    ('통상적인 전자소자의 활성화에너지(GM)', '0.3 eV to 1.2 eV', '', ''),
    ('전장품의 활성화에너지(시험설계 시 Spec 개발 적용)', '0.8 eV', '', ''),
    ('서하이 자동차의 활성화에너지(시험설계 시 SPEC 개발, VW참고)', '0.45 eV', '', ''),

]

# ============================================================
# DB : Weibull Beta/Eta 참고값
# ============================================================
WEIBULL_DB = [
    ('Components', 'Ball bearings', 0.7, 1.3, 3.5, 14000.0, 40000.0, 250000.0),
    ('Components', 'Roller bearings', 0.7, 1.3, 3.5, 9000.0, 50000.0, 125000.0),
    ('Components', 'Sleeve bearing', 0.7, 1.0, 3.0, 10000.0, 50000.0, 143000.0),
    ('Components', 'Belts, drive', 0.5, 1.2, 2.8, 9000.0, 30000.0, 91000.0),
    ('Components', 'Bellows, hydraulic', 0.5, 1.3, 3.0, 14000.0, 50000.0, 100000.0),
    ('Components', 'Bolts', 0.5, 3.0, 10.0, 125000.0, 300000.0, 100000000.0),
    ('Components', 'Clutches, friction', 0.5, 1.4, 3.0, 67000.0, 100000.0, 500000.0),
    ('Components', 'Clutches, magnetic', 0.8, 1.0, 1.6, 100000.0, 150000.0, 333000.0),
    ('Components', 'Couplings', 0.8, 2.0, 6.0, 25000.0, 75000.0, 333000.0),
    ('Components', 'Couplings, gear', 0.8, 2.5, 4.0, 25000.0, 75000.0, 1250000.0),
    ('Components', 'Cylinders, hydraulic', 1.0, 2.0, 3.8, 9000000.0, 900000.0, 200000000.0),
    ('Components', 'Diaphragm, metal', 0.5, 3.0, 6.0, 50000.0, 65000.0, 500000.0),
    ('Components', 'Diaphragm, rubber', 0.5, 1.1, 1.4, 50000.0, 60000.0, 300000.0),
    ('Components', 'Gaskets, hydraulics', 0.5, 1.1, 1.4, 700000.0, 75000.0, 3300000.0),
    ('Components', 'Filter, oil', 0.5, 1.1, 1.4, 20000.0, 25000.0, 125000.0),
    ('Components', 'Gears', 0.5, 2.0, 6.0, 33000.0, 75000.0, 500000.0),
    ('Components', 'Impellers, pumps', 0.5, 2.5, 6.0, 125000.0, 150000.0, 1400000.0),
    ('Components', 'Joints, mechanical', 0.5, 1.2, 6.0, 1400000.0, 150000.0, 10000000.0),
    ('Components', 'Knife edges, fulcrum', 0.5, 1.0, 6.0, 1700000.0, 2000000.0, 16700000.0),
    ('Components', 'Liner, recip. comp. cyl.', 0.5, 1.8, 3.0, 20000.0, 50000.0, 300000.0),
    ('Components', 'Nuts', 0.5, 1.1, 1.4, 14000.0, 50000.0, 500000.0),
    ('Components', '"O"-rings, elastomeric', 0.5, 1.1, 1.4, 5000.0, 20000.0, 33000.0),
    ('Components', 'Packings, recip. comp. rod', 0.5, 1.1, 1.4, 5000.0, 20000.0, 33000.0),
    ('Components', 'Pins', 0.5, 1.4, 5.0, 17000.0, 50000.0, 170000.0),
    ('Components', 'Pivots', 0.5, 1.4, 5.0, 300000.0, 400000.0, 1400000.0),
    ('Components', 'Pistons, engines', 0.5, 1.4, 3.0, 20000.0, 75000.0, 170000.0),
    ('Components', 'Pumps, lubricators', 0.5, 1.1, 1.4, 13000.0, 50000.0, 125000.0),
    ('Components', 'Seals, mechanical', 0.8, 1.4, 4.0, 3000.0, 25000.0, 50000.0),
    ('Components', 'Shafts, cent. pumps', 0.8, 1.2, 3.0, 50000.0, 50000.0, 300000.0),
    ('Components', 'Springs', 0.5, 1.1, 3.0, 14000.0, 25000.0, 5000000.0),
    ('Components', 'Vibration mounts', 0.5, 1.1, 2.2, 17000.0, 50000.0, 200000.0),
    ('Components', 'Wear rings, cent. pumps', 0.5, 1.1, 4.0, 10000.0, 50000.0, 90000.0),
    ('Components', 'Valves, recip comp.', 0.5, 1.4, 4.0, 3000.0, 40000.0, 80000.0),
    ('Machinery Equipment', 'Circuit breakers', 0.5, 1.5, 3.0, 67000.0, 100000.0, 1400000.0),
    ('Machinery Equipment', 'Compressors, centrifugal', 0.5, 1.9, 3.0, 20000.0, 60000.0, 120000.0),
    ('Machinery Equipment', 'Compressor blades', 0.5, 2.5, 3.0, 400000.0, 800000.0, 1500000.0),
    ('Machinery Equipment', 'Compressor vanes', 0.5, 3.0, 4.0, 500000.0, 1000000.0, 2000000.0),
    ('Machinery Equipment', 'Diaphgram couplings', 0.5, 2.0, 4.0, 125000.0, 300000.0, 600000.0),
    ('Machinery Equipment', 'Gas turb. comp. blades/vanes', 1.2, 2.5, 6.6, 10000.0, 250000.0, 300000.0),
    ('Machinery Equipment', 'Gas turb. blades/vanes', 0.9, 1.6, 2.7, 10000.0, 125000.0, 160000.0),
    ('Machinery Equipment', 'Motors, AC', 0.5, 1.2, 3.0, 1000.0, 100000.0, 200000.0),
    ('Machinery Equipment', 'Motors, DC', 0.5, 1.2, 3.0, 100.0, 50000.0, 100000.0),
    ('Machinery Equipment', 'Pumps, centrifugal', 0.5, 1.2, 3.0, 1000.0, 35000.0, 125000.0),
    ('Machinery Equipment', 'Steam turbines', 0.5, 1.7, 3.0, 11000.0, 65000.0, 170000.0),
    ('Machinery Equipment', 'Steam turbine blades', 0.5, 2.5, 3.0, 400000.0, 800000.0, 1500000.0),
    ('Machinery Equipment', 'Steam turbine vanes', 0.5, 3.0, 3.0, 500000.0, 900000.0, 1800000.0),
    ('Machinery Equipment', 'Transformers', 0.5, 1.1, 3.0, 14000.0, 200000.0, 14200000.0),
    ('Instrumentation', 'Controllers, pneumatic', 0.5, 1.1, 2.0, 1000.0, 25000.0, 1000000.0),
    ('Instrumentation', 'Controllers, solid state', 0.5, 0.7, 1.1, 20000.0, 100000.0, 200000.0),
    ('Instrumentation', 'Control valves', 0.5, 1.0, 2.0, 14000.0, 100000.0, 333000.0),
    ('Instrumentation', 'Motorized valves', 0.5, 1.1, 3.0, 17000.0, 25000.0, 1000000.0),
    ('Instrumentation', 'Solenoid valves', 0.5, 1.1, 3.0, 50000.0, 75000.0, 1000000.0),
    ('Instrumentation', 'Transducers', 0.5, 1.0, 3.0, 11000.0, 20000.0, 90000.0),
    ('Instrumentation', 'Transmitters', 0.5, 1.0, 2.0, 100000.0, 150000.0, 1100000.0),
    ('Instrumentation', 'Temperature indicators', 0.5, 1.0, 2.0, 140000.0, 150000.0, 3300000.0),
    ('Instrumentation', 'Pressure indicators', 0.5, 1.2, 3.0, 110000.0, 125000.0, 3300000.0),
    ('Instrumentation', 'Flow instrumentation', 0.5, 1.0, 3.0, 100000.0, 125000.0, 10000000.0),
    ('Instrumentation', 'Level instrumentation', 0.5, 1.0, 3.0, 14000.0, 25000.0, 500000.0),
    ('Instrumentation', 'Electro-mechanical parts', 0.5, 1.0, 3.0, 13000.0, 25000.0, 1000000.0),
    ('Static Equipment', 'Boilers, condensers', 0.5, 1.2, 3.0, 11000.0, 50000.0, 3300000.0),
    ('Static Equipment', 'Pressure vessels', 0.5, 1.5, 6.0, 1250000.0, 2000000.0, 33000000.0),
    ('Static Equipment', 'Filters, strainers', 0.5, 1.0, 3.0, 5000000.0, 5000000.0, 200000000.0),
    ('Static Equipment', 'Check valves', 0.5, 1.0, 3.0, 100000.0, 100000.0, 1250000.0),
    ('Static Equipment', 'Relief valves', 0.5, 1.0, 3.0, 100000.0, 100000.0, 1000000.0),
    ('Service Liquids', 'Coolants', 0.5, 1.1, 2.0, 11000.0, 15000.0, 33000.0),
    ('Service Liquids', 'Lubricants, screw compr.', 0.5, 1.1, 3.0, 11000.0, 15000.0, 40000.0),
    ('Service Liquids', 'Lube oils, mineral', 0.5, 1.1, 3.0, 3000.0, 10000.0, 25000.0),
    ('Service Liquids', 'Lube oils, synthetic', 0.5, 1.1, 3.0, 33000.0, 50000.0, 250000.0),
    ('Service Liquids', 'Greases', 0.5, 1.1, 3.0, 7000.0, 10000.0, 33000.0),

]

# ============================================================
# DB : Coffin-Manson m지수 선정 가이드
# ============================================================
M_GUIDE_DB = [
    ("무연솔더 적용 부품 Lead-free Solder(Sn97Ag3Cu0.5)", 2.65,
     "PCB 및 솔더링을 포함한 센서, 제어기류 (예: 무연솔더 적용 센서류)"),
    ("플라스틱 균열(Plastic Crack), 박리(Delamination)", 4.2,
     "솔더링이 적용되지 않은 점용접(Spot Welding) 센서, 퓨징(Fusing) 접합 부품, 플라스틱 몰딩/하우징 부품 "
     "(예: CKP센서, 모터/기어 액추에이터, Sol. 밸브류 등)"),
    ("금속간 결합부의 균열(Crack) - ΔT=100℃ 이하", 5.0,
     "Al, Steel 등 금속 소재 접합 구조 부품 (예: GDI 펌프, 디젤 고압펌프 등)"),
    ("금속간 결합부의 균열(Crack) - ΔT=200℃ 이상", 4.0,
     "Al, Steel 등 금속 소재 접합 구조 부품 중 ΔTservice≥200℃ 이상으로 필드온도 불확실한 부품(보수적 적용) "
     "(예: 배기 매니폴드 등)"),
]

MODEL_GUIDE_TEXT = """[ 언제 어떤 모델을 써야 하나요? ]

(1) Coffin-Manson (단순 모델)
   - 반영 요소 : DeltaT(온도변화폭) 크기만 반영
   - 적합 대상 : 플라스틱 하우징 균열/박리, 금속 접합부 균열 등 (Dwell 영향이 상대적으로 작은 구조)
   - dwell time, ramp rate 데이터가 없거나 불확실할 때도 사용

(2) Modified Norris-Landzberg (정밀 모델)
   - 반영 요소 : DeltaT + 고온유지시간(Dwell) + 승온속도(Ramp) + 절대온도(Arrhenius항)
   - 적합 대상 : 솔더 접합부(BGA/QFN 등 PCB 실장부품)의 저사이클 피로
   - 계수(n=2.65, m=0.136, Ea/k=2185)는 Pb-free 솔더 접합 문헌 기준 근사값이므로,
     다른 재질/구조에는 신뢰도가 낮을 수 있습니다.

* 판정 기준은 원칙적으로 '사이클 수' 입니다. 소요시간(분/시간/일)은 시험 스케줄링 참고용입니다.
* 시험온도는 부품 정격범위, 유리전이온도(Tg), 솔더 융점을 넘지 않아야 하며,
  유지시간은 DUT 내부/접합부 온도가 실제로 안정화되는 시간(통상 10~15분 이상) 이상이어야 합니다."""

# ============================================================
# 계산 함수
# ============================================================
def celsius_to_kelvin(c):
    return c + 273.15


def arrhenius_af(Tu_c, Ta_c, E):
    Tu = celsius_to_kelvin(Tu_c)
    Ta = celsius_to_kelvin(Ta_c)
    return math.exp((E / K_BOLTZMANN) * (1.0 / Tu - 1.0 / Ta))


def peck_af(Tu_c, Hu, Ta_c, Ha, E, n):
    Tu = celsius_to_kelvin(Tu_c)
    Ta = celsius_to_kelvin(Ta_c)
    return math.exp((E / K_BOLTZMANN) * (1.0 / Tu - 1.0 / Ta)) * ((Hu / Ha) ** (-n))


def equiv_time_single(t_field, af):
    """필드조건 시간(t_field)을 시험조건 시간으로 등가환산 (t_test = t_field / AF)"""
    return t_field / af


def weibull_test_time_ratio(R, CL, n_sample, beta):
    """시험시간비 = [ (-ln CL) / (n * -ln R) ] ^ (1/beta) """
    numer = -math.log(CL)
    denom = n_sample * (-math.log(R))
    return (numer / denom) ** (1.0 / beta)


def coffin_manson_af(dT_field, dT_test, m):
    return (dT_test / dT_field) ** m


def norris_landzberg_af(dT_field, dT_test, dwell_field, dwell_test,
                          ramp_test, Tmax_field_c, Tmax_test_c):
    Tmax_field_k = celsius_to_kelvin(Tmax_field_c)
    Tmax_test_k = celsius_to_kelvin(Tmax_test_c)
    term1 = (dT_test / dT_field) ** 2.65
    term2 = (dwell_test / dwell_field) ** 0.136
    term3 = 1.22 * (ramp_test ** -0.0757)
    term4 = math.exp(2185.0 * (1.0 / Tmax_field_k - 1.0 / Tmax_test_k))
    return term1 * term2 * term3 * term4


def profile_cycle_time_min(low_dwell, ramp_up, high_dwell, ramp_down):
    return low_dwell + ramp_up + high_dwell + ramp_down


# ============================================================
# 수명데이터 분석 (Weibull MLE, 확률도표, 파생지표)
# ============================================================
def _safe_ratio_pow(t, eta, beta):
    """ (t/eta)**beta 를 로그공간에서 계산해 오버플로우를 방지 """
    if t <= 0:
        return 0.0
    log_val = beta * (math.log(t) - math.log(eta))
    if log_val > 700:
        return math.inf
    return math.exp(log_val)


def _weibull_negloglik(params, times, is_failure):
    """음의 로그우도함수 (고장/미고장 데이터 모두 반영). params=(log_beta, log_eta)"""
    log_beta, log_eta = params
    beta = math.exp(log_beta)
    eta = math.exp(log_eta)
    ll = 0.0
    for t, f in zip(times, is_failure):
        r = _safe_ratio_pow(t, eta, beta)
        if f:
            if r == math.inf:
                return 1e12
            ll += math.log(beta / eta) + (beta - 1) * (math.log(t) - math.log(eta)) - r
        else:
            ll += -1e6 if r == math.inf else -r
    return -ll


def _nelder_mead(f, x0, max_iter=2000, tol=1e-10):
    """scipy 없이 사용하는 간단한 2변수 Nelder-Mead 구현"""
    n = len(x0)
    step = 0.5
    simplex = [list(x0)]
    for i in range(n):
        p = list(x0)
        p[i] += step
        simplex.append(p)
    fvals = [f(p) for p in simplex]

    for _ in range(max_iter):
        order = sorted(range(len(simplex)), key=lambda i: fvals[i])
        simplex = [simplex[i] for i in order]
        fvals = [fvals[i] for i in order]
        if abs(fvals[-1] - fvals[0]) < tol:
            break
        centroid = [sum(s[j] for s in simplex[:-1]) / n for j in range(n)]
        worst = simplex[-1]
        xr = [centroid[j] + 1.0 * (centroid[j] - worst[j]) for j in range(n)]
        fr = f(xr)
        if fr < fvals[0]:
            xe = [centroid[j] + 2.0 * (centroid[j] - worst[j]) for j in range(n)]
            fe = f(xe)
            simplex[-1], fvals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < fvals[-2]:
            simplex[-1], fvals[-1] = xr, fr
        else:
            xc = [centroid[j] + 0.5 * (worst[j] - centroid[j]) for j in range(n)]
            fc = f(xc)
            if fc < fvals[-1]:
                simplex[-1], fvals[-1] = xc, fc
            else:
                best_pt = simplex[0]
                for i in range(1, len(simplex)):
                    simplex[i] = [best_pt[j] + 0.5 * (simplex[i][j] - best_pt[j]) for j in range(n)]
                    fvals[i] = f(simplex[i])
    order = sorted(range(len(simplex)), key=lambda i: fvals[i])
    return simplex[order[0]], fvals[order[0]]


def fit_weibull_mle(times, is_failure):
    """중도절단(미고장) 데이터를 지원하는 Weibull MLE 적합.
    반환: (beta, eta) 또는 데이터 부족 시 None
    """
    fail_times = [t for t, f in zip(times, is_failure) if f]
    if len(fail_times) < 2:
        return None
    log_t_mid = math.log(sorted(fail_times)[len(fail_times) // 2])

    best = None
    for beta0 in (0.5, 1.0, 2.0, 3.0, 5.0):
        x0 = [math.log(beta0), log_t_mid]
        res = _nelder_mead(lambda p: _weibull_negloglik(p, times, is_failure), x0)
        if best is None or res[1] < best[1]:
            best = res
    log_beta, log_eta = best[0]
    return math.exp(log_beta), math.exp(log_eta)


def weibull_median_rank(order, n):
    """Bernard 근사 median rank : (i-0.3)/(n+0.4)"""
    return (order - 0.3) / (n + 0.4)


def weibull_rank_adjustment(times, is_failure):
    """미고장(중도절단) 데이터를 반영한 조정순위법(Johnson's Rank Adjustment).
    반환: [(고장시간, median_rank), ...]  (고장 데이터만, 시간 오름차순)
    """
    order_data = sorted(zip(times, is_failure), key=lambda x: x[0])
    n = len(order_data)
    results = []
    prev_adj_rank = 0.0
    remaining = n
    for t, is_f in order_data:
        if is_f:
            increment = (n + 1 - prev_adj_rank) / (remaining + 1)
            prev_adj_rank = prev_adj_rank + increment
            results.append((t, weibull_median_rank(prev_adj_rank, n)))
        remaining -= 1
    return results


def weibull_mttf(beta, eta):
    """평균수명 MTTF = eta * Gamma(1 + 1/beta)"""
    return eta * math.gamma(1 + 1.0 / beta)


def weibull_bpercentile(beta, eta, p_percent):
    """B(p) 수명 : F(t)=p% 가 되는 시점"""
    p = p_percent / 100.0
    return eta * (-math.log(1 - p)) ** (1.0 / beta)


def weibull_reliability(t, beta, eta):
    """신뢰도 R(t) = exp[-(t/eta)^beta]"""
    r = _safe_ratio_pow(t, eta, beta)
    return 0.0 if r == math.inf else math.exp(-r)


def weibull_failure_rate(t, beta, eta):
    """고장률함수 h(t) = (beta/eta) * (t/eta)^(beta-1)"""
    if t <= 0:
        t = 1e-9
    return (beta / eta) * (t / eta) ** (beta - 1)
