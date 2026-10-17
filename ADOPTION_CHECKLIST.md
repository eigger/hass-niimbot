# 공통 규칙 적용 체크리스트

2026-10-18 최초 채택 작업의 검증 기록입니다. 로컬 변경을 검토하며 원격 기본 브랜치 반영·CI 성공과 구분합니다. [사용법과 판정 기준](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/checklist.md)을 읽고, 아래 규칙은 `STANDARDS.md`에 기록한 표준 커밋에서 확인합니다. 태그·릴리스 대신 `main`의 검토 커밋을 기준으로 하며, 연결한 사용법과 규칙은 같은 검토 SHA로 고정했습니다.

## 검토 대상

| 항목 | 값 |
|---|---|
| 통합 리포 / 실제 기본 브랜치 | eigger/hass-niimbot / master (`git ls-remote --symref origin HEAD`) |
| domain / 구현 경로 | niimbot / custom_components/niimbot |
| 검토 대상 통합 커밋 / 채택 PR | d5686890c76fbc74171484de13383537772a10f3 기반 구현 e4a1334 / [PR #126](https://github.com/eigger/hass-niimbot/pull/126) |
| 검토한 표준 전체 커밋 SHA | 7acd9cab6ac774e4695f2c962e3d88b5faa4620d (`git ls-remote` 확인) |
| 검토일 / 조율 담당 | 2026-10-18 / root(niimbot-20261018) |
| 구현 서브 에이전트 / 독립 리뷰·검증 서브 에이전트 | tests_ci / integration_docs; independent_review |
| 중앙 현황표 반영일 / 기록 | 2026-10-18 중앙 checkout 자기 행 갱신; 원격 미반영 |
| 변경 전 지원 최소 HA / 근거 파일(hacs.json·manifest·README) | hacs.json.homeassistant=2025.1.0; manifest/기존 README 추가 하한 없음 |
| 유지·변경할 지원 최소 / 변경 시 실제 비호환 근거·명시적 승인 | 2025.1.0 유지; domain/unique ID/통합 버전 유지 |
| current 테스트 HA / 호환 Python·플러그인 | HA2026.10.2 / Python3.14 / plugin0.13.373 (실제3.14.5; 기존0.13.366은 HA2026.9.3) |
| 최소 테스트 HA / 호환 Python·플러그인 | HA2025.1.0 / Python3.13 / plugin0.13.201 (실제3.13.14) |
| profile / 테스트 경로 | integration / ha; tests/components/niimbot/ |
| 이전 검토 기록 | 최초 채택; 기존 실제 HA fixture/entry 로딩 회귀 테스트 보존 |
| 채택 판정 | 로컬 구현·독립 검증 완료 / 전체 이관 진행 중: HA-12 예외, 원격 기본 브랜치·CI/validator·중앙 원격 반영 대기 |

상태: `TODO` = 미확인·미충족, `PASS` = 근거로 확인, `EXCEPTION` = 적용 대상의 기록된 예외, `N/A` = 적용 조건에 해당 없음. 최초 기록은 미확인으로 시작했고 아래 상태는 실제 근거로 갱신했습니다. `TODO`를 해당 없음으로 처리하지 않습니다. 묶은 규칙의 결과가 다르면 행을 나눕니다. 권장 항목은 별도로 표시했으며 미채택 이유를 기록합니다.

## 채택·구조·사용자 데이터

| 규칙 ID | 확인 항목 | 상태 | 근거 / 남은 작업 |
|---|---|---|---|
| GOV-01, GOV-02 | `STANDARDS.md`에 표준 SHA·profile·실제 기본 브랜치·예외 기록, workflow/action은 검토 SHA로 고정 | PASS | STANDARDS.md의 전체 SHA 및 ha profile; 공통 caller 모두 해당 SHA 고정. |
| GOV-03 | 새 표준 채택 변경의 영향·이관 방법과 명시적 채택 PR 확인. 규칙 자체를 변경하면 공통 CHANGELOG 기록 | TODO | 최초 채택 이관 영향은 아래 기록. [PR #126](https://github.com/eigger/hass-niimbot/pull/126) 생성, 브랜치 push. 기본 브랜치 미반영. |
| GOV-04 | 중앙 표에 작업 시작·단계 변경·종료 상태, 담당·적용 내용·검증/리뷰 근거·남은 작업 갱신, 타 리포 기록 보존 | TODO | 중앙 checkout niimbot 행 시작/구현/검증 마감 갱신 완료. 중앙 원격에는 미반영; 대상 PR 생성 및 원격 CI 검증 단계. |
| GOV-05 | 구현과 독립 리뷰·검증을 별도 서브 에이전트에게 위임, 지적 수정·재검증 및 결과 취합 | PASS | 구현 tests_ci/integration_docs; 별도 independent_review가 지적 반환→수정 후 두 독립 HA환경151PASS. 아래 최종 명령·버전·로그 참조. |
| HA-01, HA-13 | `custom_components/<domain>/`와 domain 일치, 필요한 모듈·공개 API·생명주기는 Core 대응 구조 | PASS | domain/const/manifest 일치; config flow·typed runtime_data·entity·platform·protocol 역할 유지, 실제 Core entry 생명주기 사용. |
| HA-02 | manifest 필드·정렬·동작 선언 확인, 공식 품질 등급 자가 표기 없음 | PASS | manifest domain/name 이후 정렬, config_flow/Bluetooth/dependencies/version4.2.2 기존 동작 선언 보존; quality_scale 자가등급 없음. |
| HA-03 (권장) | 공통 상수·설정·갱신·플랫폼 역할 및 프로토콜 경계에 맞게 모듈 구성 | PASS | const/config_flow/data/entity/platform 및 niimprint 분리 유지; 불필요 coordinator 파일/빈 모듈 생성 없음. |
| HA-04, HA-08 | UI 설정·중복·안정적 식별 및 기능별 options/reauth/reconfigure, entity 의미·registry 영향 확인 | PASS | 실제 user/Bluetooth flow, 중복 및 options/reload 검증; 기존 unique ID·device metadata 유지. 인증 기반 서비스가 아니므로 reauth 해당없음. |
| HA-01, HA-04, HA-08, REL-01, REL-03 | domain·unique ID·entry schema·상태/통계 계약 변경 시 migration 테스트와 사용자 조치 안내 | N/A | 이번 작업에서 domain·unique ID·entry schema·상태 통계 식별 계약 변경 없음; 연결 실패 unavailable 처리는 별도 회귀 검증. |
| HA-05, HA-06 | setup 실패 구분, unload/reload·부분 실패의 task/listener/연결 정리, async·timeout·취소 처리 | PASS | cloud entry background task 취소/gather; coordinator.shutdown·부분 setup platform cleanup 및 unload 성공 후 disconnect. PNG encode executor, shared HTTP session/10s timeout; 취소 전파. |
| HA-07 | 중복 polling·property I/O 방지, push 보존, unavailable/unknown·실패 후 복구 | PASS | BLE 갱신 실패 UpdateFailed, 이전 데이터 보존하면서 unavailable; cloud update는 상태 listener만 갱신하여 실패를 성공으로 덮지 않음. 복구 회귀 포함. |
| HA-11 | 번역·action/schema 일치 | PASS | strings.json/translations/en·ko/services.yaml 기존 실제 schema 일치 검토. |
| HA-12 | 로그/diagnostics/fixture 비식별화와 제공 시 redaction 테스트 | EXCEPTION | 자동 로그의 raw discovery/BLEData/report/locals/packet/HTTP 예외 제거 및 비노출 회귀 PASS. 로컬 진단 센서의 경로/오류 속성 유지 범위는 STANDARDS.md 예외 참조. |

## 실제 HA 테스트·호환성·의존성

| 규칙 ID | 확인 항목 | 상태 | 근거 / 남은 작업 |
|---|---|---|---|
| TEST-08 | `tests/components/<domain>/`에 구현과 대응하는 테스트·domain fixture 배치, discovery·CI 경로 일치 | PASS | tests/components/niimbot/ 패키지 및 fixture; pytest.ini/testpaths와 caller pytest-args 일치. 기존137함수 누락0. |
| TEST-02, TEST-03, DEP-07 | 실제 HA·호환 플러그인과 `hass`/`enable_custom_integrations` fixture 사용, HA core stub/복사본/`--no-deps`로 대체하지 않음 | PASS | 실제 hass/enable_custom_integrations/plugin 및 MockConfigEntry 사용. HA core sys.modules stub/--no-deps 없음. 독립 환경 실제 설치 및 entry/platform 테스트. |
| TEST-09 | 실제 loader·config entry manager로 setup/플랫폼 로딩, HA 상태·registry·service/action으로 결과 검증 | PASS | test_init.py의 config_entries.async_setup/unload/reload, entity registry/6platform 상태 및 실제 HA service 액션 검증. |
| TEST-01, TEST-06, TEST-07 | 구현 기능별 성공·실패·중복·migration·unload·복구 회귀 검증, 외부 통신 경계만 mock, skip 사유 | PASS | 기존137함수 보존+최종151case. 실제 HA manager flow·플랫폼·상태/액션·setup/unload/reload/options 및 cloud task취소·부분setup실패·unavailable복구/민감로그 회귀. 외부장치/API경계 mock; skip0. entry schema 변경없음. |
| TEST-04, HACS-01 | 변경 전 지원 최소·current·각 Python/플러그인 분리, 선언한 정확한 최소 검증, 상향 시 비호환 근거·명시적 승인 확인 | PASS | 지원최소2025.1.0 유지; exact HA2025.1.0/Python3.13.14/plugin0.13.201 독립151PASS. currentHA2026.10.2/Python3.14.5/plugin0.13.373 별도151PASS. 기존Python3.12설치제약 명시. |
| TEST-05, HA-10, DEP-02, DEP-05 | imagespec·blesession 등 최소/현재 라이브러리 별도 환경, 실제 HA 테스트·정확한 설치값·API 경계 검증 | PASS | 구현 4분리환경(각HA×current/minimum libs)151PASS·pipcheck; 독립 current+정확최소 설치값 검증. blesession0.9.0/imagespec[datamatrix]1.1.0가 현재 resolver/하한모두동일. |
| DEP-01, DEP-06 | Python runtime은 manifest requirements, HA domain은 dependencies/after_dependencies, 테스트·린트 requirements는 별도 | PASS | manifest 기존 blesession>=0.9.0/imagespec[datamatrix]>=1.1.0 보존; runtime/HA component/test/lint 요구사항 구분. |
| DEP-07, CI-06 | 실제 사용하는 HA 구성요소의 requirements·필수 재귀 의존성·선택 로딩 경로 설치, resolver·`pip check` 통과 | PASS | 중앙 installer의 manifest/test constraints 동시resolver 및 실제 설치HA bluetooth/bluetooth_adapters/recorder 재귀requirements; 구현4env/독립2env pipcheck PASS. |
| DEP-02, DEP-03, DEP-08 | 의존성 추가/변경의 버전·extras·marker·선언 위치·지원 플랫폼·라이선스 검토, 실제 HA 테스트와 문서 갱신 | N/A | 신규 runtime 의존성/버전/extras/marker 변경 없음. 테스트 플러그인 current 변경 검증은 TEST/CI 행에 별도 기록. |

독립 리뷰는 변경 전후 지원 최소와 current를 비교하고, 봇 PR이 과거 최소 requirements·constraints까지 갱신하거나 expected-ha-version·Python을 누락하지 않았는지 확인합니다. 최신 테스트 실패는 호환 수정 대상으로 처리합니다.

아래는 각 분리 환경의 실제 결과입니다. 최소 HA와 최소 라이브러리 검증을 혼동하지 않고, marker가 활성인 환경에서 대상 패키지 설치값을 확인합니다. 실행하지 않은 조합은 `TODO` 또는 근거가 있는 `EXCEPTION`으로 남깁니다.

| 검증 축 / 상태 | 통합 커밋 | Python / HA / 플러그인 실제 버전 | 대상 패키지 실제 버전·extras·marker | 명령·테스트 결과·pip check / CI run·job | skip·제외·미검증 범위 |
|---|---|---|---|---|---|
| current HA/current libs / PASS | d568689 기반 최종 로컬 tree | 3.14.5 / 2026.10.2 / 0.13.373 | blesession0.9.0 / imagespec[datamatrix]1.1.0 | 구현151passed5.52s / 독립151passed5.39s; pipcheck PASS | skip0; 실물/원격 미검증 |
| current HA/minimum libs / PASS | 같은 로컬 tree | 3.14.5 / 2026.10.2 / 0.13.373 | blesession==0.9.0 / imagespec[datamatrix]==1.1.0 | 구현 별도환경151passed5.58s; pipcheck PASS | skip0 |
| exact minimum HA/current libs / PASS | 같은 로컬 tree | 3.13.14 / 2025.1.0 / 0.13.201 | blesession0.9.0 / imagespec[datamatrix]1.1.0 | 구현 별도환경151passed6.16s; pipcheck PASS | skip0 |
| exact minimum HA/minimum libs / PASS | 같은 로컬 tree | 3.13.14 / 2025.1.0 / 0.13.201 | blesession==0.9.0 / imagespec[datamatrix]==1.1.0 | 구현151passed5.84s / 독립151passed5.76s; pipcheck PASS | skip0 |

## HACS·CI·의존성 업데이트

| 규칙 ID | 확인 항목 | 상태 | 근거 / 남은 작업 |
|---|---|---|---|
| HACS-01, HACS-02 | 루트 README/LICENSE/hacs.json, 검증한 최소 HA, 실제 배포 구조와 필요한 옵션 일치 | PASS | 루트 hacs.json/README/LICENSE, custom_components/niimbot 배포 유지; 최소2025.1.0/Python3.13 조건 명시. 불필요 패키징 필드 없음. |
| HACS-03, HACS-05 | Default 여부는 목록 근거로 확인, [로컬 brand/icon.png 또는 원격 brands 근거](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/hacs.md)와 HACS/Hassfest 실제 실행, ignore는 이유·해제 조건 기록 | TODO | HACS Custom 표기/원격 brands icon.png·logo.png 확인; HACS/Hassfest caller 설치, ignore없음. 이 변경 tree 원격 validator 미실행. |
| HACS-06 (권장) | description·topics·issue 경로·brands 및 사용하는 HACS 필드 지원 확인 | PASS | GitHub metadata description/topics/Issues/Discussions 및 원격 brands icon/logo 존재 확인. |
| CI-01, CI-02 | Validate/Python Tests 공통화, 확장 job 유지, PR·실제 기본 브랜치 push·dispatch 및 필요한 schedule | PASS | SHA-pinned tests.yml/validate.yml/update-dependencies.yml; master push/PR/dispatch, Validate 및 updater schedule. |
| CI-03, CI-05, CI-08 | 최소 권한·checkout 자격증명 비보존·timeout·concurrency, full SHA·갱신 관리, 비신뢰 입력·secrets 경계 | PASS | caller read-only, updater job write scoped; 중앙 full SHA 하위 checkout credential=false/timeout/concurrency; Dependabot 설정. |
| CI-04, CI-07, CI-12 | 실패를 숨기지 않는 실제 `ha` 필수 테스트, 버전별 환경·cache·Ruff 설정과 required checks 이름 확인 | PASS | ha profile current/minimum 별도 matrix 및 라이브러리 current/minimum; lint/test 독립실행·실패숨김없음. 실제 branch protection 없음 확인. 원격 job 성공은 미검증. |
| DEP-03, DEP-04, CI-09 | updater의 선택 package·연산자/extras/marker 보존, 안정 버전·major 정책, 실제 기본 브랜치·단일 bot branch·PR만 제안 | PASS | 선택 imagespec/blesession; pinned 공통 updater의 extras/연산자/marker·안정버전·major거절·실제defaultbranch·단일botbranch/PR 계약 독립검토. |
| CI-09, CI-10, DEP-08 | 변경 tree의 새 하한·실제 HA 검증 후 PR 동기화, 실패 시 중단·변경 없음 시 기존 PR 정리, 후속 required checks 충족 방식 확인 | PASS | 독립 updater PyPI dryrun exit0 Requirements are current/no change. 코드의 exact-new-minimum 검증·failureguard·변경없음PR정리 확인. CONTRIBUTING에 GITHUB_TOKEN 후속 Tests/Validate botbranch 수동dispatch 절차; 실제 write/PR동작 미실행. |

## README·Bluetooth·유지보수

| 규칙 ID | 확인 항목 | 상태 | 근거 / 남은 작업 |
|---|---|---|---|
| DOC-01, DOC-02, DOC-06 | 영어 README.md·한국어 README.ko.md·상호 링크·기존 내용 보존, 간결한 제목/소개/핵심지원/최소요구/빠른설치·설정/짧은예제/중요제한/문서목록, 상세옵션·긴YAML·참조·개발/실HA테스트·의존성/검증범위를 docs·examples 등으로 보존·분리하고 유효한 링크 제공, 실제 활성 Issues·Discussions 또는 대체 지원 경로·실제 LICENSE 링크 | PASS | README 영한/상호연결·요구사항·빠른설치·대표예제·제한·문서·지원·LICENSE; 기존 sizing표 docs/label-sizing.md 보존. CONTRIBUTING 실제 환경/설치/검증 명령. |
| DOC-03, DOC-04, DOC-05 | 제목 아래 관리 블록, flat-square·순서·실제 조건별 배지, CI 실제 기본 브랜치, 필수 동적 Usage·Analytics 참여 설치 의미·미집계/조회 실패와 0 설치 구분·이전 안내 보존 | PASS | 영한 managed badges 및 .hass-standards.json: HACS Custom/Release/HA minimum/Tests/Validate/License/Usage 순서, master/flat-square/domain niimbot. |
| HA-09, HA-10 | BLE 사용 시 HA Bluetooth API·라이브러리 공개 경계, 지원한 proxy 경로·재연결·취소·서비스 변경 검증 | PASS | 기존 HA Bluetooth manager/blesession 공개 경계 보존, 프로토콜 실패/재연결/취소 회귀 유지. 실물 proxy·펌웨어·HA UI는 미검증. |
| DOC-07 | blesession/proxy 통합 README의 핵심조건·상세문서 링크, 공통 Bluetooth 설정·추천기기·active 스캔/GATT 차이, 통합별 troubleshooting 또는 공통 링크+모델고유조건·실제진단·민감정보 제거 제보 안내 | PASS | README/setup/troubleshooting 영한: 중앙 Bluetooth 설정/추천기기, active GATT·스캔 차이, 깨우기/단일클라이언트/프린터·proxy조건 및 재현/비식별화 제보 안내. |
| DOC-07, HA-12 | 기기별 깨우기·인증·타 앱 연결·전송 제약, 실제 검증 경로와 미검증 범위, 공개 문제 로그 비식별화 | PASS | 이 행의 PASS는 공개 제보 안내 절차에 한정하며 로컬 센서 속성은 위 HA-12 예외 적용.  실물 재검증은 수행하지 않았다고 명시; 실제 진단은 session sensors 및 debug logger, 공개전 MAC/이름/네트워크/라벨/오류 비식별화 절차 안내. |
| HACS-04, REL-01, REL-02, REL-03, CI-11 | 통합 릴리스 시 같은 검증 commit/tag·manifest 버전·산출물·권한, 사용자 영향·지원 변경·제한 안내 | N/A | 이번 작업은 릴리스/태그/버전 변경 없음; CONTRIBUTING에 차후 release checklist 명시. 기존 정식4.2.2만 확인. |
| REL-04 | 이전/중단 시 README 상단 경로·유지보수 상태·재등록 여부, 자동 이전으로 오인하지 않는 안내 | N/A | 유지보수 중인 통합이며 이전/중단 작업 없음. |
| REL-05 (권장) | 의존성/HA API 변경과 기능 변경 분리, 표준 변경은 명시적 채택 PR로 반영 | PASS | 지원/domain/버전/런타임 하한 변경 없이 공통 기준 채택과 호환성 수정을 한 작업으로 기록. |

## 예외와 남은 작업

예외 원본은 `STANDARDS.md`입니다. 아래에 해당 위치를 연결하고, 예외가 실제 없음을 확인한 뒤에만 `없음`으로 바꿉니다.

| 규칙 ID | 예외 위치 / 이유 | 담당자 | 재검토 조건 |
|---|---|---|---|
| HA-12 | [STANDARDS.md](STANDARDS.md#예외와-검증-범위): 로컬 진단 센서의 경로·오류 계약 유지 | eigger | 공개 자동첨부/export 또는 redaction helper 도입 시 |

| 규칙 ID / TODO | 남은 작업 / issue·PR | 담당자 | 완료 근거 |
|---|---|---|---|
| GOV-03/04, HACS-05, CI-09/10 | PR #126의 CI/validator 확인·기본 브랜치 반영 및 중앙 원격 상태 갱신 | eigger | 해당 커밋과 원격 run 링크 확보 시 |

최종 검토 시 적용 대상 필수 `TODO`와 `EXCEPTION`, 이유가 있는 `N/A`, 권장 미채택을 구분해 적습니다. CI 성공만으로 실물 기기 검증을 주장하지 않습니다. 실물 검증을 수행했다면 모델·펌웨어·어댑터/proxy·연결 경로와 결과를 별도로 기록합니다.

중앙 보고는 [적용 현황표](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/adoption-status.md)의 자기 리포 행에 반영합니다. 리뷰 지적·수정·재검증 결과와 중앙 갱신 실패 사유가 있으면 남은 작업에도 기록합니다.

## 착수 시 확인한 외부 메타데이터

- `git ls-remote --symref origin HEAD`: master / d5686890c76fbc74171484de13383537772a10f3. 사용자 변경 없이 착수.
- `gh api repos/eigger/hass-niimbot`: Issues·Discussions 활성, default_branch=master.
- `gh api repos/eigger/hass-niimbot/releases/latest`: 정식 4.2.2, 2026-10-17 게시.
- `gh api repos/home-assistant/brands/contents/custom_integrations/niimbot`: icon.png·logo.png 존재.
- `gh api repos/eigger/hass-niimbot/branches/master/protection`: HTTP404 `Branch not protected`. 설정 변경 없음.
- 기존 blesession>=0.9.0·imagespec[datamatrix]>=1.1.0는 Python>=3.13 요구. Python3.12 설치 실패 후 최소 테스트를3.13으로 설정; HA 지원 하한 유지.
- 중앙 `.venv/bin/python scripts/check_repository.py`: 25 documents, 7 workflows, JSON/caller contracts PASS. 대상 원격 CI를 대신하지 않음.

## 이관 영향

평면 테스트를 domain 패키지로 옮기며 helper import와 discovery 경로를 함께 변경합니다.
직접 작성 CI와 updater를 검토 SHA의 reusable workflow로 교체합니다.
새 검사는 current·minimum-ha의 lint 및 Python/ha/current·minimum 테스트, Validate의 HACS·Hassfest입니다.
기존 required checks는 없음을 위 API로 확인했으며 원격 게시 후 실제 job 명칭·성공 여부 확인이 필요합니다.
기기 재등록이나 version/domain 변경은 없습니다. 릴리스는 별도 검토 대상입니다.

## 회귀 보존 확인

2026-10-18 주 에이전트가 `git ls-tree HEAD tests/`와 `git show HEAD:<path>`의 AST를
`tests/components/niimbot/test_*.py`와 비교했습니다. 기존 테스트 함수 137개 중 이름 누락 0개.
이 구조 검사는 실제 테스트 실행·검증 결과를 대신하지 않습니다.

## 최종 독립 검증 (2026-10-18)

- 대상: 시작 커밋 `d5686890c76fbc74171484de13383537772a10f3` 기반 구현 커밋 `e4a1334`, 이후 검증기록 문서 변경. PR #126. 기록을 고친 이후 통합/테스트 코드 변경 없음.
- 구현: tests_ci / integration_docs; 독립 리뷰: independent_review. setup/unload 부분 실패, HA2025.1의 OptionsFlowWithReload/AddConfigEntryEntitiesCallback 미지원, 테스트 BLEDevice/registry 버전 차이, 연결 실패 상태, 민감 디버그 로그 지적을 수정 후 재검증.
- 명령: 각 독립 venv의 `python -m pytest tests/components/niimbot/ -q --timeout 120`, `python -m pip check`; `python -m ruff check .`, `python -m ruff format --check .`; actionlint1.7.12; `git diff --check`.
- Ruff0.14.14 check/format 48files는 구현·독립 모두 PASS, actionlint1.7.12는 구현 담당 실행 PASS(독립 실행 아님). 배지 `python3 ../hass-repo-standards/scripts/sync_badges.py . --check` PASS. README/CONTRIBUTING/docs/examples 상대링크21문서 PASS.
- 구현 실행 로그: `/tmp/niimbot-impl-{current,min313,current-minlib,min313-currentlib}-tests.log`.
- 독립 실행 로그: `/tmp/niimbot-independent-current-pytest-final.log`, `/tmp/niimbot-independent-minimum313-pytest-final.log`.
- 독립 updater dry-run: 중앙 `actions/update-manifest/update.py`를 niimbot manifest와 packages imagespec/blesession으로 실행, exit0 `Requirements are current; no change`. 쓰기·PR 생성 미실행.
- 설정 flow는 발견·중복·options 저장을 실제 HA manager로 검증. 별도 GATT 인증 handshake 기능은 없으며 초기 poll 실패도 잠든 프린터를 허용해 unavailable로 로딩하는 기존 정책을 유지. 인증 계정/reauth 및 schema migration 변경 없음.
- 독립 리뷰 결과: 수정 후 새 필수 코드 결함 없음. HA-12 로컬 진단 속성 범위예외 유지. HACS/Hassfest 및 해당 tree 원격 CI·실물·중앙 원격 반영은 수행하지 않았으며 PASS로 간주하지 않음.

최종 기록도 independent_review가 확인했으며, HA-11/HA-12 상태 분리와 공개 제보 절차 범위 명시 지적을 반영했습니다.

## 원격 PR 검증 진행

- PR: [#126](https://github.com/eigger/hass-niimbot/pull/126), branch `codex/adopt-shared-standards` → `master`.
- 구현 커밋: `e4a1334`; 원격 Tests [39074283274](https://github.com/eigger/hass-niimbot/actions/runs/39074283274), Validate [39074283178](https://github.com/eigger/hass-niimbot/actions/runs/39074283178) 실행 시작.
- 최종 문서 커밋을 포함한 head의 실제 CI 결과를 별도로 확인합니다. 기본 브랜치 병합은 이 작업에 포함하지 않습니다.
