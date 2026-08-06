# 신뢐성분석 & 추세분석기 (통합 웹앱)

## 로컬 실행
```
pip install -r requirements.txt
streamlit run app.py
```
브라우저가 자동으로 열리며, 기본 주소는 http://localhost:8501 입니다.

## 구성 파일
- `app.py` : Streamlit UI (사이드바에서 '신뢐성 분석' / '추세 분석기' 전환)
- `reliability_calc.py` : Arrhenius/Peck/Coffin-Manson/Norris-Landzberg, Weibull 시험시간비, Weibull MLE(중도절단=미고장 지원) 등 계산 로직
- `trend_calc.py` : CSV 자동헤더탐지, 노이즈필터, 누적작동시간, 추세적합(선형/지수), TTF 판정 로직

## 무료로 링크 하나 만들어 공유하기 (Streamlit Community Cloud)
1. https://github.com 에서 계정 생성 (이미 있으면 스킵)
2. 새 저장소(Repository) 생성 → 이 폴더의 4개 파일(app.py, reliability_calc.py, trend_calc.py, requirements.txt)을 업로드
3. https://share.streamlit.io 접속 → GitHub 계정 연동 → 방금 만든 저장소 선택 → Deploy 클릭
4. 몇 분 후 `https://xxx.streamlit.app` 형태의 링크가 생성됨 → 이 링크를 그대로 공유하면 브라우저만으로 접속 가능

※ 무료 플랜은 앱이 기본적으로 공개(public) 상태입니다. 외부 공개에 문제가 없다는 전제로 만들어졌습니다.
