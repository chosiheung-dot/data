# 신뢰성분석 (가속시험 통합계산기) - Streamlit 웹앱

원본 데스크톱 프로그램(신뢰성분석.py, tkinter)의 화면 구조를 그대로 재현한 웹앱입니다.

## 화면 구성 (원본과 동일)
- 좌측: 입력값(그룹 박스) / 우측: 결과(연한 파란 박스) + 계산공식(회색 박스)
- 탭① 온도가속(Arrhenius)
- 탭② 온습도가속(Arrhenius-Peck)
- 탭③ 열피로가속(Thermal Cycling) - Coffin-Manson / Modified Norris-Landzberg
- 탭④ Weibull 시험시간비 계산기 + 참고 DB
- 탭⑤ 수명데이터 분석(Weibull MLE) + 확률도표 + β값 ④ 탭으로 전송

## 로컬 실행
```
pip install -r requirements.txt
streamlit run app.py
```
브라우저가 자동으로 열리며, 기본 주소는 http://localhost:8501 입니다.

## 구성 파일
- `app.py` : Streamlit UI (5개 탭)
- `reliability_calc.py` : 계산 로직 + DB(활성화에너지 190개, Weibull Beta/Eta 69개, m지수 가이드 4개)
- `requirements.txt` : 의존 패키지 목록

## 참고
- 추세 분석기(내구시험 추세 분석기)는 별도로 재작업 예정입니다.
