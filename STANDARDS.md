# 적용한 공통 규칙

- 표준: https://github.com/eigger/hass-repo-standards/tree/0bfb572cbe49b92b3dbc559382c00bd0eb2cbd44
- 참조 커밋 SHA: `0bfb572cbe49b92b3dbc559382c00bd0eb2cbd44`
- 검토일: 2026-10-20; 이전 기준 `7acd9cab6ac774e4695f2c962e3d88b5faa4620d`에서 명시적 재채택
- profile: integration / ha; 실제 domain `niimbot`, 기본 브랜치 `master`
- 시작 커밋: `a61795fbbf101650965be10a81b722bb6d1c2925`; 통합 버전 `4.2.3`
- 지원 최소 HA `2025.1.0` / Python `3.13` 유지; current HA `2026.10.2` / Python `3.14`
- 구현: implement; 독립 리뷰·검증: review; 최종 통합·PR: root
- 실제 검증 및 남은 작업: [2026-10-20 재검토](ADOPTION_CHECKLIST.md#2026-10-20-재검토)
- 중앙 현황: 이번 시작·단계 기록을 로컬 중앙 checkout의 niimbot 행에 반영; 원격 반영은 별도 상태로 보고

## 이번 기준 변경의 영향

공통 README header/support/related-projects/license와 flat 배지를 중앙 렌더러로 맞추고 기존 본문·예제·고지를 보존했습니다. HACS Default는 [공식 목록의 확인 커밋](https://github.com/hacs/default/blob/a75c02e2cb94db482c5aaddcc83d0dad00cc20a0/integration)의 `eigger/hass-niimbot` 항목을 근거로 표시합니다. Default 등록은 HA Core 통합이라는 뜻이 아니며 커스텀 통합 배포 구조와 `hacs.json`의 지원 하한은 유지합니다.

공용 Tests/Validate/updater의 검토 SHA와 `standards-ref`를 동기화하고 Validate에 중앙 관리 영역 검사를 추가했습니다. updater 파일명은 `update_dependencies.yml`로 맞추며 기존 주기·권한·동작과 Tests의 정확한 최소 HA/current 및 라이브러리 matrix를 보존합니다. 기존 최소 환경은 Dependabot 제외를 유지합니다.

DOC-07의 언어별 사용자 원본 링크와 고정 문제 해결 구조, DOC-08의 언어별 문서·전체 미리보기 액션·실제 HA/production 렌더링 계약을 추가했습니다. 기존 한국어 URL의 문서는 이전 링크와 본문을 보존합니다. 실제 액션의 mapping schema는 기존 임의 데이터·대상·생략값을 그대로 허용하고 기존 렌더러·모델 검증을 유지합니다. English deployment 번역의 기존 문구를 strings 원본에 반영하여 미해결 Core 참조를 제거했습니다.

## 도구 계획과 수동 병합 범위

중앙 clean checkout과 동일한 full SHA로 `manage_integration.py inspect` 및 adopt `plan`을 실행했습니다. 첫 계획은 기존 최소 환경 CI·관리 경계 없는 README·루트 conftest 차이 등을 보존 충돌로 차단했습니다. 계획을 검토하여 실제 플랫폼·기존 테스트·최소 지원을 보존하는 수동 병합을 수행했습니다. 최종 재계획은 새 operation 0개지만 변경된 CI와 설정 4파일의 dirty guard 충돌을 계속 보고합니다. 중앙 생성 workflow는 실제 기존 minimum-ha matrix 및 확장 인자를 자동 병합하지 않습니다. 충돌 계획의 `apply`를 실행하거나 guard를 우회하지 않았으며 자동 적용/멱등성 성공을 주장하지 않습니다. 산출물은 `/private/tmp/niimbot-adopt-20261020/`에 보존했습니다. 이 도구의 계획 충돌과 최종 중앙 정적 검사/실제 HA 검증 결과를 구분합니다.

## 예외와 검증 범위

이전 채택의 HA-12 범위예외를 그대로 유지합니다. 로컬 진단 센서의 `via`/`advertised_via`와 원래 오류 상세는 운용·장애 경로 비교 계약을 위해 남기며 자동 공개·diagnostics export가 없습니다. 공개 전에 사용자가 비식별화해야 합니다. 담당자 eigger; diagnostics export·자동첨부·공통 redaction helper 또는 속성 계약 변경 시 재검토합니다. 새로운 예외나 기능·지원 하한 변경은 없습니다.

기기 명령, 실물 출력, 프록시·펌웨어 조합, 원격 이미지·실제 recorder 이력 및 모든 선택 요소를 새로 검증하지 않았습니다. 하단의 2026-10-18 수치와 원격 CI는 과거 증거이며 이번 변경의 PASS로 재사용하지 않습니다. 이번 PR과 같은 커밋의 원격 CI·기본 브랜치 반영 전까지 전체 채택 상태는 진행 중입니다.

## 2026-10-18 최초 채택 기록 (과거 증거)


- 표준: https://github.com/eigger/hass-repo-standards/tree/7acd9cab6ac774e4695f2c962e3d88b5faa4620d
- 과거 기준: `7acd9cab6ac774e4695f2c962e3d88b5faa4620d`
- 검토일: 2026-10-18 (최초 채택, PR #126)
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
PR: https://github.com/eigger/hass-niimbot/pull/126 (구현 커밋 e4a1334). 브랜치를 push하고 ae3c4ea의 Tests·Validate 전체 성공을 독립 확인했습니다.
HACS9개·Hassfest 및 HA4조합 각151passed를 점검표에 기록했습니다. updater 쓰기·릴리스는 실행하지 않았습니다.
실물 프린터·Bluetooth proxy·HA UI 검증은 로컬 pytest 성공과 별도입니다.
전체 채택 상태는 기본 브랜치 병합·해당 커밋 검증 전까지 `진행 중`으로 유지합니다.
