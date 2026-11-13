# kbo-fa-feed

2027 KBO FA 관련 기사·커뮤니티 글을 **5분마다** 자동으로 모아 보여 주는 페이지입니다.

- 수집: GitHub Actions가 `scripts/collect.py`를 5분마다 실행 (`.github/workflows/collect.yml`)
- 출처: 구글 뉴스·빙 뉴스 RSS(키 필요 없음), 디시인사이드 삼성 갤러리 제목 검색, 네이버 뉴스·카페·블로그(선택, API 키 필요)
- 결과: `docs/data/news.json` → `docs/index.html`이 보여 줌 (GitHub Pages)
- 선수 목록·검색어: `config.json`

새 글이 없으면 파일을 바꾸지 않아서 커밋도 생기지 않습니다. GitHub의 예약 실행은 붐빌 때 몇 분 늦어질 수 있어요.

## 처음 한 번 설정

1. **GitHub Pages 켜기**: 저장소 Settings → Pages → Source를 "Deploy from a branch", Branch를 `main` / `/docs`로 두고 Save.
   몇 분 뒤 `https://kortirpitz.github.io/kbo-fa-feed/` 에서 열립니다.
2. **Actions 켜기**: Actions 탭에서 워크플로 사용을 허용하고, "FA 소식 수집" → Run workflow로 한 번 실행해 보세요.
3. **(선택) 네이버 키**: https://developers.naver.com 에서 애플리케이션 등록(검색 API) → Client ID/Secret 발급 →
   저장소 Settings → Secrets and variables → Actions → New repository secret으로
   `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 두 개를 추가. 그다음 실행부터 네이버 카페·블로그 글도 들어옵니다.

## 수집하지 않는 것

- X(트위터)·인스타그램·스레드: 남의 공개 글을 검색하는 무료 API가 없음
- MLB파크·에펨코리아: robots.txt에서 검색엔진 외 자동 수집을 금지해 제외
- 루리웹: 검색 페이지 자동 수집을 금지해 제외
- 기사 본문: 제목·링크·짧은 소개문만 저장하고 원문은 링크로 연결
