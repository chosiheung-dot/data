# 신뢰성분석 & 추세분석기 (통합 웹앱)

원본 데스크톱(tkinter) 프로그램 2종을 Streamlit 웹앱으로 재구성했습니다.

## 구성 파일
- `app.py` : 메인 진입점 (사이드바에서 두 프로그램 중 선택)
- `reliability_app.py` / `reliability_calc.py` : ① 신뢰성분석(가속시험 통합계산기) - 5개 탭
  - ① 온도가속(Arrhenius) ② 온습도가속(Arrhenius-Peck) ③ 열피로가속(Coffin-Manson/Norris-Landzberg)
  - ④ Weibull 시험시간비 계산기(참고DB 69개) ⑤ 수명데이터분석(Weibull MLE, MTTF/B10/B1/R(t))
- `trend_app.py` / `trend_calc.py` : ② 추세분석기(Raw Data 분석) - 5개 탭
  - 전체 추세 / 정밀 분석 / 두 시간대 비교 / 새 파일 비교(폴더감시 대체) / 신뢰성 분석(TTF·RUL)

## 로컬 실행
```
pip install -r requirements.txt
streamlit run app.py
```
브라우저가 자동으로 열리며, 기본 주소는 http://localhost:8501 입니다.

## 데이터 입력 방식 (추세분석기)
원본 프로그램은 폴더를 선택하면 그 폴더 안의 모든 CSV를 자동으로 스캔합니다.
- **로컬에서 `streamlit run app.py`로 직접 실행 중**이면 사이드바에서
  "폴더 경로 입력(로컬 실행 시)"을 선택하고 CSV들이 들어있는 폴더 경로를 그대로 입력하면
  원본과 동일하게 폴더 안의 모든 CSV를 자동으로 읽습니다.
- **Streamlit Cloud 등 원격 서버에 배포한 경우**에는 서버가 사용자 PC의 폴더에 접근할 수 없으므로,
  "CSV 파일 업로드"를 선택해 파일들을 직접 업로드해야 합니다.

## 원본과 다른 점 (웹 환경 제약)
- 폴더 실시간 감시(자동 새 파일 감지) → "새 파일 비교" 탭에서 직접 업로드하여 비교하는 방식으로 대체
- 마우스 드래그 확대/축소 → Plotly 그래프의 확대(zoom)/이동(pan) 기능으로 대체
