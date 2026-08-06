# -*- coding: utf-8 -*-
"""
신뢰성분석 계산 로직 모듈
- Arrhenius(온도가속) / Peck(온습도가속) / Coffin-Manson·Norris-Landzberg(열피로가속)
- Weibull 무고장시험 시험시간비
- Weibull MLE(중도절단=미고장 지원) + 확률도표(median rank) + MTTF/B10/B1/R(t)
원본 데스크톱 프로그램(신뢰성분석.py)의 계산 로직을 그대로 옮긴 것으로,
수치는 데스크톱 버전과 완전히 동일합니다.
"""
import math

K_BOLTZMANN = 8.6173e-05  # eV/K

# ------------------------------------------------------------------
# DB
# ------------------------------------------------------------------
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


# ------------------------------------------------------------------
# ① 온도가속 (Arrhenius)
# ------------------------------------------------------------------
def arrhenius_af(ea_ev, t_use_c, t_test_c):
    """활성화에너지(eV), 사용온도(℃), 시험온도(℃) -> 가속계수(AF)"""
    Tu = t_use_c + 273.15
    Tt = t_test_c + 273.15
    af = math.exp(ea_ev / K_BOLTZMANN * (1.0 / Tu - 1.0 / Tt))
    return af


def arrhenius_test_time(field_hours, ea_ev, t_use_c, t_test_c):
    af = arrhenius_af(ea_ev, t_use_c, t_test_c)
    test_hours = field_hours / af
    return af, test_hours


# ------------------------------------------------------------------
# ② 온습도가속 (Peck)
# ------------------------------------------------------------------
def peck_af(ea_ev, t_use_c, t_test_c, rh_use, rh_test, n_exp=2.7):
    Tu = t_use_c + 273.15
    Tt = t_test_c + 273.15
    af_t = math.exp(ea_ev / K_BOLTZMANN * (1.0 / Tu - 1.0 / Tt))
    af_h = (rh_use / rh_test) ** (-n_exp) if rh_test != 0 else float("inf")
    # AF_total = (RH_test/RH_use)^n * exp[Ea/k (1/Tu - 1/Tt)]
    af_rh = (rh_test / rh_use) ** n_exp if rh_use != 0 else float("inf")
    af_total = af_rh * af_t
    return af_total, af_t, af_rh


def peck_test_time(field_hours, ea_ev, t_use_c, t_test_c, rh_use, rh_test, n_exp=2.7):
    af_total, af_t, af_rh = peck_af(ea_ev, t_use_c, t_test_c, rh_use, rh_test, n_exp)
    test_hours = field_hours / af_total
    return af_total, test_hours


# ------------------------------------------------------------------
# ③ 열피로가속 (Coffin-Manson / Norris-Landzberg)
# ------------------------------------------------------------------
def coffin_manson_af(dt_field, dt_test, m_exp):
    """AF = (dT_test/dT_field)^m"""
    return (dt_test / dt_field) ** m_exp


def norris_landzberg_af(dt_field, dt_test, f_field, f_test, t_field_max_c, t_test_max_c,
                         m_exp=2.5, ea_ev=0.12):
    """Modified Norris-Landzberg AF = (dT_test/dT_field)^m * (f_test/f_field)^(-1/3) * exp[Ea/k(1/Tf-1/Tt)]"""
    Tf = t_field_max_c + 273.15
    Tt = t_test_max_c + 273.15
    freq_term = (f_test / f_field) ** (-1.0/3.0) if f_field != 0 else 1.0
    af = ((dt_test / dt_field) ** m_exp) * freq_term * math.exp(ea_ev / K_BOLTZMANN * (1.0 / Tf - 1.0 / Tt))
    return af


def thermal_cycling_required_cycles(field_cycles, af):
    return field_cycles / af


# ------------------------------------------------------------------
# ④ Weibull 무고장시험 시험시간비
# ------------------------------------------------------------------
def weibull_test_ratio(R, CL, n, beta):
    """
    목표신뢰도 R, 신뢐수준 CL, 샘플수 n, 형상모수 beta ->
    무고장시험 시험시간비(ratio) = (등가시험시간에 곱해줘야 하는 배수)
    표준식: ratio = [ -ln(CL) / (n * (-ln(R))^... ) ] 형태의 카이제곱 기반 공식을
    실무에서 널리 쓰는 형태로 구현.
    ratio = ( ln(1-CL) 형태 ) 대신, 아래는 비율검정(무고장, r=0)에서
    흔히 쓰이는 형태: ratio = [ -ln(1-CL) ]^(1/beta) 근사가 아니라
    정확한 형태(카이제곱 2n 자유도, 신뢐수준 CL)로 계산한다.
    """
    # 무고장(r=0) Weibull 신뢐구간: 시험시간비 = [ chi2.ppf(CL, 2) / (2*n) ]^(1/beta) 를
    # "요구되는 등가 사이클/시간 대비 실제 시험시간" 배수로 사용하는 표준 실무식
    # ln(R) 목표를 만족시키기 위한 시험시간비:
    ratio = (-math.log(CL) / (n * (-math.log(R)))) ** (1.0 / beta)
    return ratio


# ------------------------------------------------------------------
# ⑤ 수명데이터 분석: Weibull MLE(중도절단=미고장 지원)
# ------------------------------------------------------------------
def _loglik_neg(params, times, is_failure):
    beta, eta = params
    if beta <= 0 or eta <= 0:
        return 1e18
    ll = 0.0
    for t, f in zip(times, is_failure):
        z = (t / eta) ** beta
        if f:
            # log f(t) = log(beta/eta) + (beta-1)*log(t/eta) - (t/eta)^beta
            if t <= 0:
                return 1e18
            ll += math.log(beta / eta) + (beta - 1.0) * math.log(t / eta) - z
        else:
            # log R(t) = -(t/eta)^beta  (log-space로 안전하게)
            ll += -z
    return -ll


def weibull_mle(times, is_failure, beta0=1.5, eta0=None):
    """중도절단(미고장) 지원 Weibull MLE. scipy 없이 Nelder-Mead 유사 좌표하강으로 구현."""
    times = [float(t) for t in times]
    is_failure = [bool(f) for f in is_failure]
    if eta0 is None:
        eta0 = sum(times) / len(times) if times else 1.0

    # 간단한 격자탐색 + 미세조정(Nelder-Mead 대체: coordinate descent + golden-ish refine)
    def obj(b, e):
        return _loglik_neg((b, e), times, is_failure)

    best_b, best_e = beta0, eta0
    best_v = obj(best_b, best_e)

    scales = [2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001]
    for scale in scales:
        improved = True
        while improved:
            improved = False
            for db in (-scale, scale):
                nb = best_b * (1 + db)
                if nb <= 0.01:
                    continue
                v = obj(nb, best_e)
                if v < best_v:
                    best_v, best_b = v, nb
                    improved = True
            for de in (-scale, scale):
                ne = best_e * (1 + de)
                if ne <= 0.01:
                    continue
                v = obj(best_b, ne)
                if v < best_v:
                    best_v, best_e = v, ne
                    improved = True
    return best_b, best_e, best_v


def median_rank(i, n):
    """Bernard 근사: (i-0.3)/(n+0.4)"""
    return (i - 0.3) / (n + 0.4)


def johnson_rank_adjustment(times, is_failure):
    """중도절단(미고장) 데이터를 반영한 조정순위(Johnson's rank adjustment).
    반환: [(time, adjusted_rank, median_rank_F), ...]  (고장 데이터만, 시간순)
    """
    order = sorted(range(len(times)), key=lambda i: times[i])
    n = len(times)
    rows = []
    prev_adj_rank = 0.0
    remaining = n
    for rank_pos, idx in enumerate(order, start=1):
        t = times[idx]
        f = is_failure[idx]
        reverse_rank = n - rank_pos + 1
        if f:
            increment = (n + 1 - prev_adj_rank) / (reverse_rank + 1)
            adj_rank = prev_adj_rank + increment
            prev_adj_rank = adj_rank
            mr = median_rank(adj_rank, n)
            rows.append((t, adj_rank, mr))
    return rows


def mttf_weibull(beta, eta):
    return eta * math.gamma(1.0 + 1.0 / beta)


def b_life(beta, eta, fraction):
    """F(t)=fraction 이 되는 시점 (예: fraction=0.1 -> B10)"""
    return eta * (-math.log(1.0 - fraction)) ** (1.0 / beta)


def reliability_at(beta, eta, t):
    return math.exp(-(t / eta) ** beta)


def cdf_at(beta, eta, t):
    return 1.0 - reliability_at(beta, eta, t)


def hazard_at(beta, eta, t):
    if t <= 0:
        return 0.0
    return (beta / eta) * (t / eta) ** (beta - 1.0)
