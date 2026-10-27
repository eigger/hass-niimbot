# 공식 Hassfest source 검증 CI 후속

- 일자: 2026-10-20. 대상: [PR #131](https://github.com/eigger/hass-niimbot/pull/131)의 기존 head `f63adccf314c349634f2cfd05da658d5d1e6830f` 기반 CI/기록 변경.
- 중앙 기준: [중앙 PR #10](https://github.com/eigger/hass-repo-standards/pull/10)의 squash 병합 main full SHA `648dad941a118c80325f44c7a13cb5b5b9c1c788`; 앞서 검토한 PR commit `4d436cb2fc57be557cbbf4a20702249694a5d0c7`에서 병합 SHA로 동기화.
- 중앙 PR의 squash 병합을 먼저 진행하라는 사용자 명시적 요청에 따라 중앙 PR10은 병합 완료했습니다. target PR131은 열린 상태로 새 head의 실제 CI를 기다립니다. 앞서 검토한 PR commit과 workflow/scripts/actions/templates/docs 차이 없음을 확인했으며 고정 SHA 정책을 유지합니다.

| 항목 | 현재 상태 | 이번 근거 / 남은 일 |
|---|---|---|
| 원격 기존 검증 | HACS PASS / Hassfest FAIL | f63adcc의 [Validate39420628025](https://github.com/eigger/hass-niimbot/actions/runs/39420628025): HACS10검사(categories 포함) 및 중앙 관리 영역 검사는 통과했지만 published Hassfest가 `categories` 키 자체를 거부. 선택한 프린터 분류 오류가 아니며 실패를 완료/PASS로 바꾸지 않음. |
| CI 호환 경로 | 적용·실행 대기 | Validate caller에만 `hassfest-core-ref: ec18d8b25d1ee39aa8b85a72a170e42bee33228c` 추가. 올바른 categories/최소 HA/의존성을 보존하고 공식 source Dockerfile/entrypoint/전체 validator를 실행하도록 중앙 PR 경로 선택. 오류 억제·manifest 전처리 없음. |
| 공용 참조 | PASS (정적) | Tests/current·minimum/Update dependencies/Validate/check-standards와 STANDARDS의 fullSHA를648dad9로 동기화. 기존 matrix·주기·권한 유지. |
| 중앙 패치 검증 | PASS (도구 단위·정적) | 중앙 구현·독립216unit tests 각각79.194s/76.676s; 새7개에서 ref/HEAD/collision/fetch/build/run 실패와 caller mount 보존 검증. Ruff92files·actionlint·중앙37documents7workflows PASS. 이 결과는 실제 source 이미지 실행 성공을 대신하지 않음. |
| 실제 로컬 image build | 미완료·취소 | 정확한 Core HEAD 확인 및 수정 없는 upstream Dockerfile로 ARM64 build. base/CI tools 설치·115package resolve 후 wheel 준비 정체, 약5분에 취소(exit130). host exact wheel GET200이지만 Docker/uv 정체 원인은 확정하지 않음. 완성 이미지·실제 Hassfest 실행 PASS 없음. |
| 새 PR head 원격 CI | TODO | push 후 target PR131에서 source fetch/build/전체 Hassfest와 HACS/중앙검사/Tests를 실행해 동일 head 근거 기록. 이 단계 전 기존 실패 해결로 주장하지 않음. |
| GOV 도구·정적 | PASS (검사) / 계획 충돌 보존 | 게시 중앙 commit으로 inspect/source-ci-plan 실행. 기존 custom CI3파일은 preserve conflict, 설정 JSON의 canonical 정리 operation1개. 기존 계획을 강제로 apply하지 않고 필요한 CI 참조·옵션만 수동 병합. 새 checker가 해당 선택 input을 허용함을 실제 검사. |
| runtime·지원 | 변경 없음 | 이번 추가 수정은 CI/개발문서/기록만; manifest/runtime/HA최소2025.1.0/의존성/분류/통합버전4.2.3 유지. 기존 HA 로컬644case 결과는 아래 역사 기록이며 이번 source build 검증으로 재사용하지 않음. |

실제 명령: 게시 중앙 checkout의 `python scripts/check_integration.py . --check`, `python scripts/sync_badges.py . --check`, `python scripts/check_repository.py`, actionlint1.7.12 `.github/workflows/*.yml`, `git diff --check` PASS. 기존 로컬 HA 환경에 패키지를 추가·교체하지 않았습니다. 새 필수 검증은 target PR131의 실제 CI에서 수행하며 결과 전에는 미완료입니다.

앞선 중앙 PR commit4d436cb 기준의 `source-ci-inventory.json`/`source-ci-plan.json` 및 로컬 build/unit 로그는 `/private/tmp/niimbot-hacs-followup-20261020/`에 보존합니다. 중앙 main648dad9 병합 후 해당 clean checkout으로 중앙 통합 검사·배지·repository 검사와 actionlint/diff 검사를 재실행해 통과했습니다. target6bb5401의 병합 전 SHA 기반 source CI는 새 head 실행으로 대체되므로 그 결과를 병합 SHA 검증으로 재사용하지 않습니다. 대상 기본브랜치 반영·새 head의 실제 source build/Hassfest 검증은 아직 미완료입니다.

---

## 아래는 앞선 HACS 설치·배지·카테고리 적용의 검증 기록입니다

# HACS 설치·배지·카테고리 후속 검토

- 일자: 2026-10-20. 대상: PR #130 병합 후 `master`의 `96b6482f419c3f77efd83c627cfefaacd6f22733` 기반 로컬 tree.
- 중앙 기준: `0490b2ad8378364b487746ea18fca7a0e1d22edc`, 이전 `0bfb572cbe49b92b3dbc559382c00bd0eb2cbd44`.
- 범위: 양언어 HACS 설치 배지·Default 다운로드 배지·설치 설명, 실제 제품 분류 메타데이터, 공용 SHA 동기화. runtime/통합 버전4.2.3/의존성/HA 최소2025.1.0/Python 최소3.13/기존 CI matrix 유지.

| 항목 | 상태 | 이번 근거 / 제한 |
|---|---|---|
| GOV-01/02, CI | PASS (정적) | STANDARDS 기준 SHA 및 공용 workflow/action/standards-ref 일치, current/minimum HA·library matrix/권한/주기 보존. |
| DOC-03/05 | PASS (정적) | 중앙 렌더러의 HACS Downloads 동적 badge로 교체; 공식 data.json에서 full_name 선택. HTTP200과 리포 항목848680333 존재를 확인했으나 downloads 필드는 현재 없음. 0·활성 설치 수·전체 릴리스 합계로 주장하지 않으며 표시 성공은 미확인. |
| DOC-06 설치 | PASS (정적) | 기존 영한 설치 절·본문을 보존하고 installation 관리 블록 추가. 실제 owner=eigger/repository=hass-niimbot. Default는 category 파라미터 생략, HACS 사전 설치·사용자 다운로드/재시작 절차 명시. docs/setup.md의 오래된 custom repository 안내 수정. 실제 HA 브라우저 링크 클릭은 미검증. |
| HA-02 categories | PASS (선택·정적) | 실제 제품 Niimbot BLE 라벨 프린터와 niimbot.print 용도로 computers_network.printers1개 선택. 공식 Core taxonomy snapshot ec18d8b...의 값. 센서·Bluetooth를 별도 제품 카테고리로 추정하지 않음. 기존 integration_type 미선언 유지, categories_review null 및 판단 근거 기록. HACS 누락 경고와 중앙 필수 정책을 구분. |
| GOV 도구 | 검토·수동 병합 | clean 중앙 checkout의 inspect 및 initial-plan 실제 실행. categories 자동 변경 금지/기존 CI 보존 conflict를 확인 후 manifest를 근거에 따라 수동 보완. README는 check_integration.py --write-readmes 중앙 렌더러 사용. reviewed-plan은 operation0이지만 CI/설정4개의 dirty guard conflict를 계속 보고. apply 미실행, guard 우회·자동적용 성공 주장 없음. |
| TEST / DOC-08 | PASS (로컬 실행) | 실제 최소/current HA에서 기존 entry·flow·platform·registry·reload/unload/부분 실패 회귀18case 및 mandatory payload1case를 각각 실행. 기존 package 교체·기기 명령 없음. 아래 실행 증거 참조. |
| GOV-05 독립 검토 | PASS | implement 구현과 review 독립 검증 분리; 독립 코드/번역/분류 의미·근거·배지 query 검토 및 양 HA 전체644case 통과, 필수 지적 없음. |
| HACS/Hassfest/원격 CI | TODO | 이번 PR head 커밋의 원격 결과 확인 필요. PR #130 병합96b6482의 Tests39413126318/Validate39413126356 성공은 이번 변경 검증으로 재사용하지 않음. |
| 예외·기기·배포 | 기존 범위 유지 | STANDARDS의 HA-12 기존 로컬 진단 속성 범위 유지. 신규 예외·실물 인쇄·프록시 firmware·태그/릴리스 작업 없음. |

## 후속 실제 실행 증거

| 구현 환경 | Python / HA / plugin | 실제 imagespec / blesession | 실행 결과 |
|---|---|---|---|
| current | 3.14.5 / 2026.10.2 / 0.13.373 | 1.1.0[datamatrix] / 0.9.0 | 실제 HA18PASS0.51s, payload1PASS0.19s, pip check PASS |
| exact minimum | 3.13.14 / 2025.1.0 / 0.13.201 | 1.1.0[datamatrix] / 0.9.0 | 실제 HA18PASS0.50s, payload1PASS0.20s, pip check PASS |
| 독립 current | 3.14.5 / 2026.10.2 / 0.13.373 | 1.1.0[datamatrix] / 0.9.0 | 전체644PASS9.08s, payload1PASS0.18s, pip check PASS |
| 독립 exact minimum | 3.13.14 / 2025.1.0 / 0.13.201 | 1.1.0[datamatrix] / 0.9.0 | 전체644PASS8.78s, payload1PASS0.16s, pip check PASS |

- 기존 분리 venv `/private/tmp/niimbot-implementation-20261020-{current,minimum}`의 이미 resolve된 패키지로 실행; payload 검증 후 패키지 덮어 설치 없음.
- HA 명령: `<env>/bin/python -m pytest tests/components/niimbot/test_init.py tests/components/niimbot/test_config_flow.py -q --timeout 120`. 실제 manifest loader·entry setup·6플랫폼·registry·flow·reload/unload 및 부분setup 실패 처리 검증, skip0.
- payload 명령: `PAYLOAD_REPOSITORY="$PWD" PAYLOAD_DOMAIN=niimbot PYTHONPATH=<reviewed-central>/scripts <env>/bin/python -m pytest -p hass_standards_payload tests/components/niimbot/test_payload_examples.py -q --timeout 120`. 실제 HA/등록 액션/production render_image와 설치된 public imagespec 출력·크기·palette 비교1case, skip0.
- 중앙 `check_integration.py . --check`, `sync_badges.py . --check`, actionlint1.7.12 `.github/workflows/*.yml`, `git diff --check` PASS. `check_repository.py`는 중앙37documents7workflows PASS이며 대상 통합 원격 CI/하드웨어 성공을 대신하지 않음.
- 도구 입력/계획 및 로그: `/private/tmp/niimbot-hacs-followup-20261020/{inventory,input,initial-plan,reviewed-plan}.json`, `{current,minimum}-{payload,ha,pip-check}.log`.
- 구현 담당은 문서·metadata scope에 맞춰 위18case+payload를 실행했고 독립 담당은 같은 tree의 전체644case 회귀를 양 환경에서 별도 재실행했습니다. 독립 명령은 payload 성공 후 `<env>/bin/python -m pytest tests/components/niimbot/ -q --timeout 120 --ignore=tests/components/niimbot/test_payload_examples.py`; skip0. 독립 로그 `/private/tmp/niimbot-review-hacs-followup-{current,minimum}-{payload,regression}.log`. 독립 Ruff0.17.1 check/format81files·중앙 검사·배지·actionlint·diffcheck도 PASS. PR Tests의 전체 HA×library matrix는 별도 확인합니다. 아래의 이전 실행은 역사 기록입니다.

## 후속 남은 작업

PR 생성·동일 head의 Tests/Validate 및 독립 최종 리뷰를 기록합니다. 기본 브랜치 반영·해당 커밋 검증 후 중앙 현황의 완료 여부를 갱신하며 중앙 로컬 편집을 원격 반영으로 간주하지 않습니다.

---

# 2026-10-20 재검토

이번 검토 대상은 `a61795fbbf101650965be10a81b722bb6d1c2925` 기반 로컬 변경이며 중앙 기준은 `0bfb572cbe49b92b3dbc559382c00bd0eb2cbd44`입니다. 과거 PASS는 아래 역사 기록으로 보존하며 이번 검증과 구분합니다.

| 규칙 / 범위 | 이번 상태 | 근거·제한 |
|---|---|---|
| GOV-01/02 | PASS | STANDARDS 새 기준·이전 기준·영향 기록, 공용 CI full SHA/standards-ref 일치. |
| GOV-04/05 | 진행 중 | implement 구현 / review 독립 검증 / root 통합. PR·동일 커밋 원격 CI·중앙 원격 현황 반영은 최종 기록 예정. |
| GOV 관리 도구 | 검토·수동 병합 | inspect/initial-plan/reviewed-plan 실제 실행. 기존 CI 보존 및 dirty guard 충돌로 apply 미실행, 자동 적용 성공 주장 없음. 최종 operation 0이나 unresolved guard 4개이며 원인은 STANDARDS 기록. |
| HACS-03/05, DOC-03/04/05 | PASS (정적·목록) | HACS 공식 목록 pinned commit에서 Default 확인, 양언어 배지/설치 안내 반영. 최소 HA2025.1.0 유지. 이 변경 커밋의 HACS/Hassfest는 PR 원격 CI 확인 전 TODO. |
| DOC-01/02/06, DOC-07 | PASS (정적) | 중앙 렌더러 관리 영역/기존 본문 보존; 언어별 blesession 사용자 문서 및 로컬 고정 구조·이전 한국어 URL 보존. 실물 경로 새 검증 없음. |
| DOC-08 | PASS (로컬 실행) | 전체 YAML preview 액션1개, 실제 HA entry/서비스/production render_image 및 _make_context 사용. 기기 전송 없음. current/exact-minimum 실행 근거는 아래 갱신. |
| HA-11 | PASS (정적) | 기존 배포 en 번역을 strings 원본과 일치시켜 Core 참조 해결; 한국어 키·placeholder 보존. |
| TEST-08/09, CI-01/04/07/12 | PASS (로컬 실행) | 중앙 root/domain 관리 fixture, 각 실제 플랫폼 registry/state/unload assertion 및 기존 회귀 보존. exact minimum/current HA와 각 library 조합 보존. |
| CI-09/10 | 정적 확인 | updater 주기/범위/권한과 검증 command 보존; 새 공용 SHA가 필수 payload 계약 후 일반 회귀의 관리 scaffold만 제외. 실제 bot PR 쓰기 미실행. |
| HA-12 | 기존 EXCEPTION | STANDARDS의 기존 로컬 진단 속성 운용 범위예외 유지. 신규 예외 없음. |
| REL | N/A | 버전4.2.3/domain/support 변경 및 태그/릴리스 없음. |

## 이번 실제 검증 증거

대상은 위 시작 커밋 기반 최종 로컬 tree이며 코드·YAML·fixture는 검증 이후 변경하지 않았습니다. 문서/검증 기록의 후속 편집은 기능 결과와 구분합니다.

| 환경 / 담당 | 실제 Python / HA / plugin | 실제 libraries | 결과 |
|---|---|---|---|
| fresh current / implement | 3.14.5 / 2026.10.2 / 0.13.373 | imagespec[datamatrix]1.1.0, blesession0.9.0, pyStrich0.20 | payload1PASS; regression644PASS; pip check PASS |
| fresh exact minimum / implement | 3.13.14 / 2025.1.0 / 0.13.201 | imagespec[datamatrix]==1.1.0, blesession==0.9.0, pyStrich0.10 | payload1PASS; regression644PASS8.42s; pip check PASS |
| independent current / review | 3.14.5 / 2026.10.2 / 0.13.373 | imagespec[datamatrix]1.1.0, blesession0.9.0 | payload1PASS0.16s; regression644PASS12.17s; pip check PASS |
| independent exact minimum / review | 3.13.14 / 2025.1.0 / 0.13.201 | imagespec[datamatrix]==1.1.0, blesession==0.9.0 | payload1PASS0.15s; regression644PASS11.15s; pip check PASS |

- fresh 환경은 각각 별도 venv에서 검토 SHA의 `actions/python-environment/install.py`로 실제 HA component requirements까지 동시 resolve했습니다. current는 resolver 선택, minimum은 manifest의 정확한 하한 모드입니다. 검증 후 패키지 덮어 설치는 하지 않았습니다. 각 HA의 current/minimum library 교차4조합은 PR Tests에서 별도로 검증하며 위2조합 결과를 미실행4조합 PASS로 확장하지 않습니다.
- payload 명령: `PAYLOAD_REPOSITORY="$PWD" PAYLOAD_DOMAIN=niimbot PYTHONPATH=<reviewed-central>/scripts <env>/bin/python -m pytest -p hass_standards_payload tests/components/niimbot/test_payload_examples.py -q --timeout 120`. 예제 `examples/payload/minimal.yaml`1개가 실제 실행되어 production 렌더러/public imagespec 출력·240×96 크기·흑백 palette 일치 확인. 기기 명령 없음.
- payload 성공 후 회귀 명령: `<env>/bin/python -m pytest tests/components/niimbot/ -q --timeout 120 --ignore=tests/components/niimbot/test_payload_examples.py`. 기존637case+추가7case=644case, skip0. 일반 수집도 중앙 모듈을 최상위 import하지 않으며 독립 plugin 없이 정상 회귀 실행.
- 구현·독립 양쪽 Ruff0.17.1 `check .` 및 `format --check .`81files, 중앙 `check_integration.py . --check`, `git diff --check` PASS. 독립 actionlint1.7.12 PASS; root의 중앙 `check_repository.py`37documents7workflows PASS는 중앙 도구 자체 검증입니다.
- initial plan에서 잘못 지정한 number 플랫폼/독립 coordinator scaffold는 실제 구현을 확인하여 입력에서 제거했습니다. 실제6플랫폼(sensor/image/binary_sensor/select/switch/button)과 인라인 coordinator 구현을 보존하고 가짜 기능을 만들지 않았습니다.
- 최초 새 button test는 disabled-by-default maintenance button을 활성 상태로 가정해 양 환경에서 실패했습니다. 실제 registry disabled 상태를 확인하는 의미 있는 assertion으로 수정 후 위 전체644case를 독립 재실행하여 통과했습니다. current adapter의 ServiceCall signature 차이도 실제 minimum/current에 맞춰 수정 후 재검증했습니다.
- 로컬 구현 로그: `/private/tmp/niimbot-adopt-20261020/{current-install,minimum-install,fresh-current-payload,fresh-minimum-payload,fresh-current-regression,fresh-minimum-regression}.log`; 독립 로그: `/private/tmp/niimbot-review-20261020-{current,minimum}-{payload,regression-final}.log`.
- 독립 리뷰 지적: 커스텀 통합 명시 보존, trailing whitespace/formatter 수정, disabled button 검증 정정 완료. 최종 기능 지적 없음. 이번 변경 커밋의 원격 HACS/Hassfest/CI와 실물 출력은 아직 미검증입니다.

## 이번 남은 작업

- PR 생성 후 같은 head 커밋의 Tests/Validate(HACS·Hassfest·Central template compliance) 성공 확인.
- 기본 브랜치 반영 및 해당 커밋 검증 후 중앙 현황 완료 처리. 중앙 로컬 편집은 원격 반영으로 간주하지 않음.
- 이번 작업은 실물 프린터/proxy 출력 검증, updater의 실제 의존성 변경/봇 PR 생성, release/tag를 포함하지 않음.

---

## 2026-10-18 최초 채택 기록 (과거 증거)

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
| 채택 판정 | 로컬 구현·독립 검증 완료 / 전체 이관 진행 중: HA-12 예외, 기본 브랜치·중앙 원격 반영 대기; PR ae3c4ea Tests/Validate PASS |

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
| HACS-03, HACS-05 | Default 여부는 목록 근거로 확인, [로컬 brand/icon.png 또는 원격 brands 근거](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/hacs.md)와 HACS/Hassfest 실제 실행, ignore는 이유·해제 조건 기록 | PASS | HACS Custom 표기/원격 brands icon.png·logo.png 확인; HACS/Hassfest caller 설치, ignore없음. ae3c4ea의 Validate39074311918 HACS9개/brands·Hassfest Invalid integrations0 독립 PASS. |
| HACS-06 (권장) | description·topics·issue 경로·brands 및 사용하는 HACS 필드 지원 확인 | PASS | GitHub metadata description/topics/Issues/Discussions 및 원격 brands icon/logo 존재 확인. |
| CI-01, CI-02 | Validate/Python Tests 공통화, 확장 job 유지, PR·실제 기본 브랜치 push·dispatch 및 필요한 schedule | PASS | SHA-pinned tests.yml/validate.yml/update-dependencies.yml; master push/PR/dispatch, Validate 및 updater schedule. |
| CI-03, CI-05, CI-08 | 최소 권한·checkout 자격증명 비보존·timeout·concurrency, full SHA·갱신 관리, 비신뢰 입력·secrets 경계 | PASS | caller read-only, updater job write scoped; 중앙 full SHA 하위 checkout credential=false/timeout/concurrency; Dependabot 설정. |
| CI-04, CI-07, CI-12 | 실패를 숨기지 않는 실제 `ha` 필수 테스트, 버전별 환경·cache·Ruff 설정과 required checks 이름 확인 | PASS | ha profile current/minimum 별도 matrix 및 라이브러리 current/minimum; lint/test 독립실행·실패숨김없음. 실제 branch protection 없음 확인. ae3c4ea의 Tests39074311974 전체6job 성공 독립 확인. |
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
- 독립 리뷰 결과: 수정 후 새 필수 코드 결함 없음. HA-12 로컬 진단 속성 범위예외 유지. 원격 CI는 아래 ae3c4ea 증거로 별도 갱신. 실물·중앙 원격 반영은 수행하지 않음.

최종 기록도 independent_review가 확인했으며, HA-11/HA-12 상태 분리와 공개 제보 절차 범위 명시 지적을 반영했습니다.

## 원격 PR 검증 진행

- PR: [#126](https://github.com/eigger/hass-niimbot/pull/126), branch `codex/adopt-shared-standards` → `master`.
- 구현 커밋: `e4a1334`; 초기 Tests39074283274/Validate39074283178는 후속 커밋 검증으로 대체하여 취소(실패 아님).
- 최종 문서 커밋을 포함한 head의 실제 CI 결과를 별도로 확인합니다. 기본 브랜치 병합은 이 작업에 포함하지 않습니다.

### PR 원격 CI 성공 증거

- 검증 커밋: `ae3c4ea45e1d4f699bebf7fe7519115bf2b16a76`; 주 에이전트와 independent_review가 실제 job 로그를 확인.
- [Tests39074311974](https://github.com/eigger/hass-niimbot/actions/runs/39074311974): HA×library4조합 각각151passed, skip0; 두 lint job 성공; 각 환경 pip check PASS.
- current Python3.14.8 / HA2026.10.2 / plugin0.13.373: current libs151passed6.35s, minimum libs151passed7.70s.
- minimum Python3.13.16 / HA2025.1.0 / plugin0.13.201: current libs151passed9.25s, minimum libs151passed8.28s.
- 양 HA의 current/minimum 모두 실제 blesession0.9.0 / imagespec[datamatrix]1.1.0.
- [Validate39074311918](https://github.com/eigger/hass-niimbot/actions/runs/39074311918): HACS9개 검사(brands포함) PASS, Hassfest Invalid integrations0 PASS.
- 원격 버전은 위 로컬 Python3.14.5/3.13.14와 구분합니다. 로그는 `/tmp/niimbot-independent-remote-{current-current,current-minimum,minimum-current,minimum-minimum}.log`.
- 이 결과는 ae3c4ea의 증거입니다. 이 기록을 추가한 후속 문서 커밋도 PR의 Checks에서 별도로 확인합니다. 미병합 상태이며 기본 브랜치 완료로 기록하지 않습니다.

## 2026-10-23 Downloads 배지 부분 검증

- 기준: 중앙 `b54ac48102d6e326c6929071fdc02ba8fade794e`의 DOC-03/05·배지 생성기와 Validate 형식 검사기만 부분 채택. 대상 시작 SHA `d0c264dcd530faa0b962f9090b9dffeeaa7af709`. 기존 전체 채택 결과·예외는 유지하며 이번 변경으로 전체 재채택 완료를 주장하지 않습니다.
- 계획/자체 리뷰: 양언어 관리 블록을 같은 중앙 렌더러로 생성, 잘못된 HACS 데이터 조회 배지를 Downloads로 교체, 집계 의미와 소스 파일 설치 제외를 양언어로 명시. GOV-02에 따라 중앙 호출 pin과 standards-ref를 같은 SHA로 맞춥니다. 이전 기준과 새 기준의 공용 workflow/action 파일은 동일하며 실행 설정·지원 최소·ZIP 배포 설정을 보존합니다.
- 검증 명령·결과와 최종 head SHA·원격 CI 링크는 이 PR 본문에 기록합니다. 문서·배지·형식 검사기 pin만 변경하므로 로컬 HA 환경을 재구축하지 않으며 실제 기기·HA UI·사용자 다운로드 집계는 미검증입니다.
- 실행 결과: WSL Ubuntu Python 3.14.4/PyYAML 6.0.3/packaging 26.0에서 중앙 `scripts/sync_badges.py <repo> --check`, `scripts/check_integration.py <repo>` 및 actionlint 1.7.12의 전체 caller workflow 검사 PASS. Windows Git의 `git diff --check` PASS. 양언어 배지 외 기존 본문은 집계 설명의 정정·추가만 허용하고 보존했습니다.
- 초기 검사 실패 기록: 단일 기준 SHA 계약에 맞지 않는 검사기 pin만의 갱신은 GOV-02에서 거부되어 모든 중앙 pin을 동일 SHA로 정합화했습니다. Windows 중앙 템플릿 CRLF 비교는 실패하여 LF 중앙 snapshot의 Linux 검사로 재검증했습니다. WSL Git은 Windows worktree gitdir 경로를 해석하지 못해 diff 검사를 실패했고 동일 변경의 Windows Git 검사로 대체했습니다. 실패를 PASS로 소급하지 않습니다.

## 2026-10-23 ZIP 릴리스 적용 검증

- 기준 `0c1592977591ecba077a4666d699840062711201` / 대상 시작 `a54bb72d9b2ced6af4379d7e1939b582df226335`. HACS-04/CI-11 부분 갱신이며 기존 전체 채택 이력·예외는 유지합니다.
- 계획: hacs.json에 zip_release:true, filename:niimbot.zip을 추가하고 중앙 release.yml을 같은 SHA로 생성합니다. 기존 caller는 중앙 pin/standards-ref만 변경합니다. 지원 최소·통합 버전·의존성·구현·README 본문을 보존합니다.
- 검증: 중앙 생성기/정적 검사·actionlint·실제 packager로 추적된 통합 파일의 ZIP 루트·manifest/번역/brand 등 런타임 자료 포함과 저장소 메타데이터 제외를 확인합니다. CLI 검증 명령·실제 버전·최종 head SHA·ZIP 결과·독립 리뷰·원격 CI 링크는 이 PR 본문에서 한 번 기록합니다.
- 중앙 실행 로직은 독립 zip_release_review 리뷰에서 지적 수정 후 추가 지적 없음. 대상 caller/메타데이터/ZIP도 별도 독립 리뷰합니다. 로컬 HA 환경 재구축·새 릴리스 발행·asset 업로드·기기 설치는 수행하지 않으며 미실행을 PASS로 기록하지 않습니다. immutable-releases는 enabled:false로 확인했습니다.


## 2026-10-25 중앙 검사기 부분 갱신 검증

- 검토한 중앙 SHA: `1863343638014adb8a4001afc8fddc1a27dc500f`; 적용 시작 커밋: `0af28aafa29914cc61a9a117a3d29d006a18348b`.
- 범위: 중앙 pin·standards-ref·검토 기준 기록 정합화. HA 구현·요구 버전은 유지합니다.
- 로컬: Python 3.14.5 / PyYAML 6.0.3, `python scripts/check_integration.py <target>` (검토한 중앙 source에서 실행): PASS.
- actionlint: PASS. PR CI·독립 리뷰 결과는 PR 링크와 check 결과를 확인합니다. 이 로컬 결과만으로 전체 채택 완료를 주장하지 않습니다.
- 독립 리뷰: 별도 review_checker_rollout 담당자가 19개 리포의 workflow 69개·기존 job 100개를 구조 비교했습니다. 새 CI 회귀 지적 없음. 기존 job ID·입력·권한·지원 최소와 통합 코드 보존 및 새 standards job의 중앙 템플릿 일치 확인. 실행 변경 없는 이 기록 추가 전 작업 트리를 검토했습니다.


### 2026-10-25 Standards workflow 분리 검증

- 분리 시작 커밋: `7be3764d983c177a625255b8810409392c66e356`; 검토 중앙 소스 `ca740d88b32fa5dcbc94c41fce2908450c76ed50` (중앙 PR #24). Validate는 HACS/Hassfest job을 그대로 유지하며 중앙 job만 standards.yml로 이동하고 표시 이름을 Standards로 변경합니다.
- 독립 리뷰: root 구현의 19개 리포에 대해 별도 fix_scale_atflee_ci 담당자가 Validate job 19개와 이동 job 19개의 YAML 정의를 비교했습니다. 파일 이동·표시 이름 외 실제 검사 단계·이벤트·권한·timeout·입력 변경 없음. 중앙 위치 인식 변경은 root가 별도 독립 리뷰했습니다.
- 로컬: 새 중앙 검사기·actionlint·diff 검사 PASS. 중앙 전체232개·관련38개 회귀 테스트와 양 배치19개 동등성 검사 PASS. 모든 대상 기본 브랜치의 branch protection·rulesets 조회에서 필수 검사 이름 설정이 없어 이름 변경으로 인한 대기 충돌 없음. 원격 CI는 이 PR의 최신 head에서 확인합니다.
- 검사 기준을 추가하거나 완화하지 않았으며 기존 inline 배치도 같은 기준으로 지원합니다. 실제 runtime·지원 최소·의존성은 이 파일 분리에서 변경하지 않습니다.

## 2026-10-25 중앙 immutable release 참조 전환

- 요청/범위: 사용자 요청으로 `hass-niimbot`의 중앙 workflow/action 참조를 `v1.0.0`으로, `standards-ref`를 `44349ee5621eea5d80e5c427f7a2435d2c2491bb`으로 전환. manifest·hacs·requirements·통합 코드·테스트·지원 최소 및 caller-owned CI 설정은 변경하지 않음.
- 기준 대상: 기본 브랜치 base `19134bcc151a8bd3cfa91138be347b23660eefff`. 중앙 release는 `manage_integration.py verify-release`로 published/non-prerelease/immutable 및 peeled SHA 일치를 원격 확인.
- 실제 검증: Python 3.14 중앙 `check_integration.py` 변경 전/후, changed workflow actionlint, `git diff --check`, reference-only 범위 assert를 실행. 이번 refs-only 변경에서는 HA/device 테스트를 재실행하지 않았고 PR CI/병합은 대기.
- 리뷰: 중앙 generated reference-only 결과로 GOV-05 자체 검토; 별도 교차 검토는 조율자가 수행 예정. 기존 실패·미검증은 PASS로 재분류하지 않음.
