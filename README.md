# FinTrack Web 🏦

> **전국 은행 상품 통합 비교 서비스**
> 
> 개발자: **황원철** (yalkongs)

## 🌟 개요
**FinTrack Web**은 금융감독원(FSS)의 실시간 공시 데이터를 기반으로 전국의 모든 은행(시중은행, 지방은행, 인터넷은행)의 예적금 및 대출 상품을 한눈에 비교할 수 있는 프리미엄 웹 애플리케이션입니다.

## ✨ 주요 기능
- **통합 검색**: 예금, 적금, 신용대출, 주택담보대출 카테고리별 실시간 데이터 조회.
- **최적 상품 추천 (BEST)**: 금리 조건이 가장 유리한 상품을 자동으로 하이라이트.
- **상세 보기 모달**: 가입 방법, 만기 이자 계산 방식, 우대 조건 등 상세 정보 제공.
- **우대 금리 유형화**: '급여이체', '첫 거래' 등 우대 조건을 태그 형태로 시각화.
- **강력한 정렬**: 은행명, 상품명, 금리별 실시간 정렬 기능.
- **로컬 데이터 축적**: SQLite3를 사용하여 데이터를 로컬에 축적하여 실행 속도 최적화.

## 🛠 기술 스택
- **Backend**: Python 3, Flask, SQLite3
- **Frontend**: HTML5, CSS3 (Glassmorphism), Vanilla JavaScript
- **API**: 금융감독원 금융상품통합비교공시 API (Mock Mode 지원)

## 🚀 시작하기

### 1. 요구 사항 설치
```bash
pip install -r requirements.txt
```

### 2. 실행
```bash
python app.py
```
서버 실행 후 브라우저에서 `http://localhost:5001`에 접속하세요.

### 3. 데이터 갱신
화면의 **[지금 갱신하기]** 버튼을 누르면 실시간 외부 데이터를 로컬 DB에 동기화합니다.

## 📂 프로젝트 구조
- `app.py`: Flask 웹 서버 및 API 엔들포인트
- `database.py`: SQLite 데이터베이스 스키마 및 쿼리 관리
- `api_client.py`: 금융감독원 API 통신 및 Mock 데이터 생성 로직
- `templates/index.html`: 프리미엄 웹 인터페이스 (Frontend)

---
© 2026 Developed by 황원철.
