# 🚌 셔틀버스 ETA 예측 시스템 (ShuttleRun)

## 👥 팀소개

* **팀원**:

  * **안재민** : 팀장
  * **언도윤** : 팀원
  * **지현구** : 팀원

## ✅ 프로젝트 개요

* **팀명**: 13조
* **인원**: 3명
* **운영 시간**: 10:30 ~ 20:40 (21:00 버스는 학교 → 죽전역까지)

---

## 🌟 기능

1. **셔틀 동안 시간 예측 (ETA)**

   * 교내 출발 시간표 + 거리/속도 기반 예측 알고리즘
   * 평균 속도 기능 간이 목록 또는 Google Directions API 활용

2. **시각화 제공**

   * `"예상 도착 시간: 7분"`, `"80%"` 등 텍스트 및 그래프 표시
   * 지도상 현재 예산 위치 표시 (Leaflet Marker)

3. **사용자 인터페이스**

   * 시간 기능에 필요한 간단한 UI
   * 웹 브라우저 기본 구조

---

## 🛠️ 기술 스택 및 역할 분담

| 역할    | 이름 | 기술                               | 비고              |
| ----- | -- | -------------------------------- | --------------- |
| 프론트엔드 | 재민 | HTML, CSS, JS, Leaflet, Chart.js | 지도 시각화, 동안률 그래프 |
| 백어드   | 도윤 | Python, Flask                    | ETA 계산, API 서버  |
| 문서/관리 | 현구 | GitHub, 문서화, 전체코드                   | 기획서, README 관리  |

---

## 🧐 주요 기술 요소

* **📍 지도 시각화**: OpenStreetMap + Leaflet.js
* **🧮 ETA 예측**: 평균 거리/속도 기반 예측 또는 Directions API
* **🌐 API 서버**: Flask 기능 /eta 역할
* **📊 시각화**: Chart.js or HTML Progress Bar
* **📂 교내 시간표 DB**: CSV 또는 JSON 바로 활용

---

## ⏱️ 개발 순위

1. ✅ **교내 출발 시간표 .json 파일로 변환**
2. ✅ **죽전역 ↔ 학교 거리 기준 평균 속도 계산**

   * 간단 버전: 시간별 평균 속도 CSV 기록
   * 심화 버전: Directions API 또는 거리-시간 검색
3. ✅ **Flask + Leaflet 연동**
4. ✅ **프론트엔드에서 Flask API 호출 및 ETA 표시**

---

## 🔗 활용 오픈소스

| 이름                      | 기능                       | 링크                                                              |
| ----------------------- | ------------------------ | --------------------------------------------------------------- |
| Flask-Leaflet Demo      | Flask + Leaflet 연동 구조 참고 | [GitHub](https://github.com/adwhit/flask-leaflet-demo)          |

---

## 📁 파일 구조

```
ShuttleRun/
├── backend/
│   ├── app.py                 ← Flask 실행 코드
│   └── requirements.txt       ← Flask, requests 등 의종성
│
├── frontend/
│   ├── index.html             ← Leaflet 로딩 HTML
│   ├── style.css              ← 기본 스타일
│   └── script.js              ← JS 코드 (API 호출 등)
│
├── docs/
│   └── 기획서.md              ← 역할 분단 및 환동 과정 정리
│
├── .gitignore                 ← __pycache__, .env 등 제외
├── README.md                  ← 전체 설명서
└── LICENSE                    ← MIT 등 선택
```

