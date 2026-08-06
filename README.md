# 가속시험 통합계산기 (신뢰성분석) — 웹앱

원본 tkinter 데스크톱 프로그램(`신뢰성분석.py`)을 Streamlit 웹앱으로 그대로 재현한 버전입니다.

## 구성 (5개 탭)
- ① 온도가속 (Arrhenius Model)
- ② 온습도가속 (Arrhenius-Peck Model)
- ③ 열피로가속 (Thermal Cycling) — Coffin-Manson / Modified Norris-Landzberg
- ④ Weibull 시험시간비 계산기 + 참고 DB
- ⑤ 수명데이터 분석 — 고장/미고장 데이터 → Weibull MLE → MTTF/B10/B1/R(t) + 확률도표

각 탭은 원본과 동일하게 **좌측(입력) / 우측(결과, 연한 파란 배경 박스)** 2단 구조이며,
"계산 실행 ▶"(파란 버튼) / "엑셀로 내보내기" 버튼, DB 검색(활성화에너지 190개 / Weibull 참고 69개 / m지수 가이드 4개),
⑤→④ β값 연동, ⓘ 설명 팝업까지 원본 기능을 포함합니다.

## 로컬 실행
```
pip install -r requirements.txt
streamlit run app.py
```
브라우저가 자동으로 열리며, 기본 주소는 http://localhost:8501 입니다.

## 구성 파일
- `app.py` : Streamlit UI (5개 탭)
- `reliability_calc.py` : 계산 로직 + DB 데이터 (원본 tkinter 프로그램의 계산부만 순수 함수로 분리)
- `requirements.txt` : 설치 패키지 목록
