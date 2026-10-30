# 적용한 공통 규칙

- 표준: https://github.com/eigger/hass-repo-standards/tree/v1.1.5
- 참조 커밋 SHA: f56987f7f765a774c926fb8005fe5df68bb32451
- Standards release: v1.1.5
- Resolved standards SHA: f56987f7f765a774c926fb8005fe5df68bb32451
- 검토일: 2026-10-20; 이전 기준 `0490b2ad8378364b487746ea18fca7a0e1d22edc`에서 공식 Hassfest source 검증 호환 경로 채택
- profile: integration / ha; 실제 domain `niimbot`, 기본 브랜치 `master`
- 시작 커밋: `96b6482f419c3f77efd83c627cfefaacd6f22733` (PR #130 병합 후); 통합 버전 `4.2.3`
- 지원 최소 HA `2025.1.0` / Python `3.13` 유지; current HA `2026.10.2` / Python `3.14`
- 구현: implement; 독립 리뷰·검증: review; 최종 통합·PR: root
- 실제 검증 및 남은 작업: [HACS 설치·배지·카테고리 후속 검토](ADOPTION_CHECKLIST.md#hacs-설치배지카테고리-후속-검토)
- 중앙 현황: 이번 시작·단계 기록을 로컬 중앙 checkout의 niimbot 행에 반영; 원격 반영은 별도 상태로 보고

## 공식 Hassfest source 검증 호환 경로

현재 참조는 사용자가 명시적으로 요청한 [중앙 PR #10](https://github.com/eigger/hass-repo-standards/pull/10)의 squash 병합 후 main full SHA `648dad941a118c80325f44c7a13cb5b5b9c1c788`입니다. 앞서 검토한 PR commit `4d436cb2fc57be557cbbf4a20702249694a5d0c7`와 workflow/scripts/actions/templates/docs의 내용이 같음을 확인하고 병합 SHA로 고정했습니다. 중앙 PR은 병합되었으며 대상 [PR #131](https://github.com/eigger/hass-niimbot/pull/131)은 아직 열려 있습니다. `@main`으로 참조 정책을 변경하지 않았습니다.

PR #131의 `f63adccf314c349634f2cfd05da658d5d1e6830f`에서 HACS는10검사를 통과했지만 공식 published Hassfest 이미지가 `categories` 키 자체를 거부해 [Validate39420628025](https://github.com/eigger/hass-niimbot/actions/runs/39420628025)가 실패했습니다. 올바른 프린터 분류를 삭제하거나 검사를 생략하지 않고, Validate caller에만 `hassfest-core-ref: ec18d8b25d1ee39aa8b85a72a170e42bee33228c`를 지정했습니다. 이 공식 Core commit은 custom categories 스키마 지원과 검토된 taxonomy를 포함합니다. 중앙 source 경로는 고정 upstream URL/full SHA/실제 HEAD를 확인해 runner.temp에서 수정하지 않은 공식 Dockerfile을 빌드하고, 원래 caller checkout을 mount하여 전체 Hassfest를 실행합니다. fetch/build/검증 오류는 실패하며 빈 입력의 기존 공식 action 경로도 유지됩니다.

중앙 호환 패치는 구현·독립216개 unit tests와 정적 검사를 통과했습니다. 실제 local ARM64 build는 wheel 준비 정체로 약5분에 취소되어 완성 이미지·실제 Hassfest 성공을 확인하지 못했습니다. 대상 PR의 새 head에서 수행할 source build·전체 Hassfest와 다른 필수 CI 결과가 실제 완료되기 전에는 해결/PASS로 기록하지 않습니다. 통합 runtime·manifest 분류·지원 최소·의존성은 이 CI 수정에서 변경하지 않았습니다.

## HACS 설치·배지·카테고리 후속 범위

최신 중앙 렌더러로 양언어 README의 기존 설치 절에 저장소별 My Home Assistant HACS 배지 관리 블록을 추가했습니다. HACS가 먼저 설치되어 있어야 하며 배지는 저장소 화면을 열고 다운로드·재시작·통합 추가는 기존 절차를 따릅니다. Default 통계 배지는 공식 HACS 데이터의 `full_name`/`downloads` 동적 조회로 변경했습니다. 현재 확인된 리포 항목에 downloads가 없으므로 집계 확인 불가이며 0이나 활성 설치 수로 해석하지 않습니다. `docs/setup.md`의 과거 Custom repository 안내도 Default 목록 검색으로 맞췄습니다.

HA-02의 중앙 채택 정책으로 실제 Niimbot BLE 라벨 프린터 용도에 `computers_network.printers` 하나를 선택했습니다. 근거는 README 소개·지원 프린터 문서·실제 `niimbot.print` 액션과 중앙에 기록된 공식 Core taxonomy snapshot입니다. sensor/button 플랫폼이나 Bluetooth 의존성에서 별도 제품 용도를 추정하지 않아 보조 분류는 추가하지 않았습니다. 기존 integration_type 미선언은 그대로 유지하고 categories_review에는 null로 기록했습니다. 공식 HA 선택 필드/HACS 경고와 중앙 필수 정책을 구분하며 런타임·버전·의존성·지원 최소는 변경하지 않았습니다.

이번 clean 중앙 SHA로 inspect/plan을 실행했고 categories 차이를 자동 덮어쓰지 않는 conflict 및 기존 minimum-ha CI 보존 충돌을 검토했습니다. manifest 분류는 근거를 확인해 수동 보완하고, README는 같은 중앙 렌더러로 생성했습니다. 충돌 plan에 apply를 실행하거나 guard를 우회하지 않았습니다. 산출물은 `/private/tmp/niimbot-hacs-followup-20261020/`에 있습니다. CI는 기존 minimum/current matrix·주기·권한을 보존하며 검토 SHA만 갱신했습니다.

## 이전 2026-10-20 기준 채택 기록 (과거 범위)

아래는 PR #130 이전 채택의 영향과 검증 범위를 보존한 기록이며 이번 후속 작업 결과와 구분합니다.

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

## 2026-10-23 다운로드 배지 부분 갱신

- 배지·DOC-03/05와 Validate 형식 검사기만 중앙 [`b54ac48102d6e326c6929071fdc02ba8fade794e`](https://github.com/eigger/hass-repo-standards/tree/b54ac48102d6e326c6929071fdc02ba8fade794e)를 채택합니다. 이전 기준 SHA `648dad941a118c80325f44c7a13cb5b5b9c1c788`의 채택 이력·예외는 보존합니다. 모든 중앙 workflow/action pin과 standards-ref는 GOV-02의 단일 기준 SHA 계약에 맞춰 갱신합니다. 중앙 diff에서 공용 workflow/action 실행 파일은 이전 기준과 동일함을 확인했습니다.
- 대상 기본 브랜치 커밋: `d0c264dcd530faa0b962f9090b9dffeeaa7af709`. 주 에이전트 직접 구현·자체 리뷰(GOV-05의 배지/생성물 변경 범위), 검증은 [ADOPTION_CHECKLIST.md](ADOPTION_CHECKLIST.md#2026-10-23-downloads-배지-부분-검증)에 기록합니다.
- Downloads는 현재 릴리스 첨부 asset 다운로드 합계입니다. 사용자 지시에 따라 ZIP 배포를 도입하지 않으며 현재 HACS 소스 파일 설치는 이 수치에 집계되지 않습니다. 통합 코드·의존성·지원 최소·기존 설치 안내는 변경하지 않습니다.

## 2026-10-23 ZIP 릴리스 배포

- 기준 중앙 SHA: `0c1592977591ecba077a4666d699840062711201` ([중앙 PR15](https://github.com/eigger/hass-repo-standards/pull/15) 스쿼시 머지). 이전 `b54ac48102d6e326c6929071fdc02ba8fade794e` 채택 이력·예외를 보존하며 HACS-04·CI-11의 ZIP 배포 계약을 추가합니다.
- 대상 시작 SHA: `a54bb72d9b2ced6af4379d7e1939b582df226335`. hacs.json의 zip_release/filename과 중앙 release caller를 함께 적용합니다. archive 파일명은 `niimbot.zip`, ZIP 루트는 해당 통합 파일입니다.
- 중앙 workflow/action pin과 standards-ref는 단일 SHA로 정합화합니다. release:published에서 기존 해당 릴리스에 ZIP만 첨부하며 소스 버전·태그·릴리스 발행은 자동 변경하지 않습니다. 기존 asset 덮어쓰기를 거부합니다.
- 기존 지원 최소 HA `2025.1.0`와 통합 버전 `4.2.4` 및 의존성·구현은 보존합니다. 기존 태그의 hacs.json은 소급 수정하지 않으므로 다음 릴리스부터 ZIP 설치로 전환됩니다.
- immutable-releases 설정은 enabled=false/enforced_by_owner=false로 확인했습니다. 업로드 지연·실패 및 기존 asset 복구는 중앙 [릴리스 계약](https://github.com/eigger/hass-repo-standards/blob/0c1592977591ecba077a4666d699840062711201/docs/releases.md#zip-릴리스-첨부)을 따릅니다. 실제 새 릴리스 발행·설치·기기 검증은 이번 작업에 포함하지 않습니다.

## 2026-10-25 중앙 검사기 갱신

- 검토한 중앙 main: `1863343638014adb8a4001afc8fddc1a27dc500f` (git ls-remote 확인). 이전 기본 기준 `0c1592977591ecba077a4666d699840062711201`의 채택 이력은 위 기록을 보존합니다.
- 모든 중앙 workflow/action pin과 reusable workflow의 standards-ref를 같은 검토 SHA로 맞춥니다. HACS-04는 actions/*의 full SHA 고정을 유지하면서 SHA 값 차이를 허용합니다.
- 통합 코드·런타임 의존성·지원 최소·배포 버전은 이번 변경 대상이 아닙니다. 기존 채택 범위를 전체 완료로 바꾸지 않으며 실제 검증 결과와 남은 항목은 ADOPTION_CHECKLIST.md의 같은 날짜 기록을 참조합니다.


### 2026-10-25 Standards 파일·표시 이름 분리

- 기존 Validate의 중앙 검사 job을 `standards.yml`로 옮기고 workflow/job 표시 이름을 `Standards`로 줄였습니다. Validate의 HACS/Hassfest, 검사 항목·통과 기준·실행 단계·조건·권한은 유지합니다.
- 위치 인식과 중앙 명명 안내를 맞춘 검토 소스: `ca740d88b32fa5dcbc94c41fce2908450c76ed50` ([중앙 PR #24](https://github.com/eigger/hass-repo-standards/pull/24), 현재 이 PR의 의존 변경). 이전 기준 `1863343638014adb8a4001afc8fddc1a27dc500f`의 검증 이력은 앞 기록으로 보존합니다. 모든 중앙 pin·standards-ref는 같은 새 검토 소스로 맞춥니다.

## 2026-10-25 중앙 immutable release 참조 전환

- 사용자 요청에 따라 현재 중앙 참조를 immutable `v1.0.0` / resolved SHA `44349ee5621eea5d80e5c427f7a2435d2c2491bb`로 전환했습니다. 중앙 workflow/action caller는 exact release tag를, `standards-ref`는 resolved full SHA를 사용합니다.
- 범위는 중앙 참조·기록 정합화뿐입니다. 기존 지원 최소, 통합 버전, manifest, 런타임 요구사항, 구현, 테스트와 CI의 caller-owned 설정은 보존했습니다.
- 과거 SHA·검증·예외 기록은 역사적 증거로 보존합니다. 이번 변경은 generated reference-only 범위이므로 GOV-05 자체 검토이며 PR CI/병합은 대기 상태입니다.
