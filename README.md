# 가속시험 통합계산기 (신뢰성분석) - 웹앱

원본 데스크톱 프로그램(tkinter)의 5개 탭 기능을 Streamlit 웹앱으로 재구성했습니다.
- ① 온도가속 (Arrhenius)
- ② 온습도가속 (Peck)
- ③ 열피로가속 (Coffin-Manson / Norris-Landzberg)
- ④ Weibull 시험시간비
- ⑤ 수명데이터 분석 (Weibull MLE)

## 이번 버전(v7) 변경사항
1. **추세분석기(내구시험 Raw Data 분석) 기능 제거** — 추세분석기는 EXE로 별도 배포하므로 웹에서는 신뢰성분석만 제공합니다.
2. 화면 상단 "원본 데스크톱 프로그램의 5개 탭을 그대로 재현했습니다" 안내 문구 삭제.
3. DB 검색 등 작은 팝업(popover)이 좁게 뜨던 문제를 해결 — 아래 항목 전부 `st.dialog`(큰 모달, width="large")로 통일:
   - ① 활성화에너지 DB 검색 / 왜 필요한가
   - ② 활성화에너지 DB 검색
   - ③ 모델 선택 가이드 / m지수 참고 가이드
   - ④ Weibull β·η 참고 DB / 왜 필요한가
   - ⑤ MTTF·B10·B1·R(t) 설명

## 파일 구성
- `app.py` : Streamlit 메인 앱 (5개 탭 UI + 모달)
- `reliability_calc.py` : 계산 로직(Arrhenius/Peck/Coffin-Manson/Norris-Landzberg/Weibull) + 참고 DB
- `requirements.txt` : 의존 패키지 목록

## 로컬 실행 방법
```
pip install -r requirements.txt
streamlit run app.py
```

## 업데이트 방법
1. 화면 UI, 탭 구성, 버튼 등을 바꾸고 싶으면 → `app.py` 수정
2. 계산식이나 DB(활성화에너지/Weibull β 참고값/m지수 가이드)를 바꾸고 싶으면 → `reliability_calc.py` 수정
3. 새 패키지가 필요하면 → `requirements.txt`에 추가
4. 수정한 파일을 GitHub 저장소(`chosiheung-dot/data`)에 업로드(Commit) → Streamlit Cloud가 자동으로 몇 분 내 재배포합니다.

## 참고
- `st.dialog`의 `width="large"` 옵션을 쓰기 위해 `requirements.txt`에서 `streamlit>=1.38`로 지정했습니다.
- DB 값(활성화에너지/Weibull β/m지수)은 실무에서 자주 참고되는 대표값 예시이며, 실제 설계/품질 기준에 따라 조정해서 사용하세요.
