# 🚌 셔틀버스 ETA 예측 시스템 (ShuttleRun)

## ✅ 프로젝트 개요

* **팀명**: 13조
* **팀원**: -**안재민** : 팀장  
-**엄도윤** : 팀원   
-**지현구** : 팀원  
* **운영 시간**: 10:30 \~ 20:40 (21:00 버스는 학교 → 죽전역까지)

### 🔍 문제

* **문제점**: 교내 출발 시간표만 존재 → 죽전역 출발 셔틀 동안 도착 시간 예측 불가
* **목표**: **죽전역 기준 셔틀 동안 도착 시간 예측** 및 시각화 제공

---

## 🌟 기능

1. **셔틀 동안 시간 예측 (ETA)**

   * 교내 출발 시간표 + 거리/속도 기반 예측 알고리즘
   * 평균 속도 기능 간이 목록 또는 Google Directions API 활용

2. **시각화 제공**

   * `"셔틀 동안까지 7분 남음"`, `"동안률 80%"` 등 텍스트 및 그래프 표시
   * 지도상 현재 예산 위치 표시 (Leaflet Marker)

3. **사용자 인터피스**

   * 시간 기능에 필요한 간개한 UI
   * 웹 브라우저 기본 구조

---

## 🛠️ 기술 스택 및 역할 분담

| 역할    | 이름 | 기술                               | 비고              |
| ----- | -- | -------------------------------- | --------------- |
| 프론트엔드 | 재민 | HTML, CSS, JS, Leaflet, Chart.js | 지도 시각화, 동안률 그래프 |
| 백어드   | 도윤 | Python, Flask                    | ETA 계산, API 서버  |
| 문서/관리 | 현구 | GitHub, 문서화                      | 기획서, README 관리  |

---

## 🧐 주요 기술 요소

* **📍 지도 시각화**: OpenStreetMap + Leaflet.js
* **🧮 ETA 예측**: 평균 거리/속도 기반 예측 또는 Directions API
* **🌐 API 서버**: Flask 기능 /eta 역할
* **📊 시각화**: Chart.js or HTML Progress Bar
* **📂 교내 시간표 DB**: CSV 또는 JSON 바로 활용

---

## ⏱️ 개발 용선순위

1. ✅ **교내 출발 시간표 CSV 형식으로 변환**
2. ✅ **죽전역 ↔ 학교 거리 기준 평균 속도 계산**

   * 간이 버전: 시간별 평균 속도 CSV 기록
   * 심험 버전: Directions API 또는 거리-시간 프로경 검색
3. ✅ **Flask + Leaflet 연동 예제 실행**
4. ✅ **프론트엔드에서 Flask API 호출 및 ETA 표시**

---

## 🔗 활용 가능 오픈소스

| 이름                      | 기능                       | 링크                                                              |
| ----------------------- | ------------------------ | --------------------------------------------------------------- |
| Flask-Leaflet Demo      | Flask + Leaflet 연동 구조 참고 | [GitHub](https://github.com/adwhit/flask-leaflet-demo)          |
| Flask-GoogleMaps        | Flask 내에서 Google Maps 활용 | [GitHub](https://github.com/flask-extensions/Flask-GoogleMaps)  |
| Leaflet Routing Machine | 경로 및 정류장 시각화             | [GitHub](https://github.com/perliedman/leaflet-routing-machine) |

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

