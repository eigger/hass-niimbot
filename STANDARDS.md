# 적용한 공통 규칙

- 표준: https://github.com/eigger/hass-repo-standards/tree/7acd9cab6ac774e4695f2c962e3d88b5faa4620d
- 참조 커밋 SHA: `7acd9cab6ac774e4695f2c962e3d88b5faa4620d`
- 검토일: 2026-10-18 (최초 채택, 로컬 작업)
- profile: integration / ha
- 적용 점검표: [ADOPTION_CHECKLIST.md](ADOPTION_CHECKLIST.md)
- 중앙 현황표: https://github.com/eigger/hass-repo-standards/blob/main/docs/adoption-status.md
- 조율: root(niimbot-20261018); 구현: tests_ci / integration_docs; 독립 리뷰·검증: independent_review
- 중앙 현황: 2026-10-18 중앙 checkout의 niimbot 행 갱신, 원격 미반영
- 실제 기본 브랜치: master
- 시작 커밋: `d5686890c76fbc74171484de13383537772a10f3`
- 테스트 경로: `tests/components/niimbot/`
- 변경 전/후 지원 최소 HA: `2025.1.0` (`hacs.json`); 변경 없음
- 통합 버전: `4.2.2`; domain 및 기존 registry 식별 계약 유지
- current 검증: Python3.14.5 / HA2026.10.2 / plugin0.13.373, 독립151PASS
- 최소 HA 검증: Python3.13.14 / HA2025.1.0 / plugin0.13.201, 독립151PASS
- 라이브러리: blesession0.9.0 / imagespec[datamatrix]1.1.0, HA별 current/minimum 분리4환경 각151PASS
- 세부 설치값·명령·결과: 적용 점검표 참조

## 예외와 검증 범위

| 규칙 ID | 이유와 범위 | 담당자 | 재검토 조건 |
|---|---|---|---|
| HA-12 | 자동 로그의 식별자/원문 덤프는 제거했지만, 기존 로컬 진단 센서의 via/advertised_via 경로와 error/refresh_error 원문은 장애 경로 비교·기존 사용자 계약을 위해 보존. 공개 제출 전 수동 비식별화 필요. diagnostics 다운로드/자동 공개 기능 없음. | eigger | diagnostics export·공개 이슈 자동첨부·공통 redaction helper 도입 또는 진단 속성 계약 변경 시 |

이 범위예외는 독립 리뷰 `independent_review`가 원문 규칙과 비교해 확인했습니다.
원격 push·PR·릴리스는 실행하지 않았습니다. HACS/Hassfest와 실제 원격 CI·updater 실행은 미검증이며
실물 프린터·Bluetooth proxy·HA UI 검증은 로컬 pytest 성공과 별도입니다.
전체 채택 상태는 원격 반영/검증 전까지 `진행 중`으로 유지합니다.
