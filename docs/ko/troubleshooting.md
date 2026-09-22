# 트러블슈팅

**[English](../troubleshooting.md)** | 한국어

> 영어 문서가 기준입니다. 내용이 다르면 [영어 원문](../troubleshooting.md)을 따릅니다. 엔티티 이름과 속성 키는 Home Assistant 화면에 보이는 영어 그대로 적었습니다.

라벨이 인쇄되지 않을 때, 통합구성요소는 대개 그 이유를 이미 기록해 두었습니다. 이 문서는 보는 순서입니다: 먼저 마지막 BLE 세션의 분석을 담고 있는 센서들, 다음으로 그 센서가 볼 수 없는 경우들, 마지막으로 이슈에 첨부할 것.

## 어디를 볼까

프린터의 기기 페이지를 엽니다 (**설정 → 기기 및 서비스 → Niimbot → 프린터**). *진단* 아래에 다음 순서로 읽을 엔티티 네 개가 있습니다:

| 엔티티 | 알려주는 것 |
|---|---|
| **Last Failure** (마지막 실패) | BLE 세션이 마지막으로 **실패한** 시각. *속성*에 그 세션의 분석이 있습니다 — `operation`, `failed_stage`, `likely_cause`, `error`, 무선(`via`, `rssi`, `paths`), 단계별 소요 시간. 다음 실패까지 유지되므로, 어젯밤 실패한 인쇄를 오늘 아침 폴링이 성공한 뒤에도 읽을 수 있습니다. 연결조차 못 한 상태 폴링은 여기 기록되지 **않습니다**: 작업 사이에는 프린터가 보통 꺼져 있거나 절전 중이기 때문입니다. |
| **Last Error** (마지막 오류) | 마지막으로 실패한 인쇄에서 프린터가 직접 보고한 오류 코드(`CoverOpen`, `LackPaper`, `LowBattery`, …). 속성은 위와 같은 분석입니다. 프린터가 응답하기 전에 실패한 인쇄(예: `connect`)는 대신 예외 이름(`ConnectFailed`)이 표시됩니다. |
| **Print Duration** (인쇄 시간) | **가장 최근** 인쇄에 걸린 초. 성공/실패 무관. *속성*은 그 인쇄의 분석이며, 작업이 끝날 때 붙습니다 (진행 중 — `is_printing: true` — 에는 경과 시간만 있습니다). 디버깅하려는 인쇄가 마지막 인쇄일 때 사용하세요. |
| **Error Count** (오류 횟수) | 통합구성요소가 (다시) 로드된 뒤 실패한 세션 수. 프린터가 절전 중이라 연결 못 한 폴링은 세지 않습니다. 실패한 인쇄, 연결 후 실패한 폴링, 연결 못 한 `niimbot.refresh_info`는 셉니다. 아무것도 인쇄하지 않는데 올라간다면 링크가 열린 뒤 폴링이 실패하고 있다는 뜻입니다 — 숫자를 해석하기 전에 Last Failure의 `failed_stage`부터 읽으세요. |

속성 보기: 엔티티 클릭 → ⋮ → **속성**, 또는 **개발자 도구 → 상태**에서 엔티티 검색. 템플릿에서는 `{{ state_attr('sensor.b21_123456_ddee03_last_failure', 'likely_cause') }}` (ID는 프린터가 광고하는 이름 + MAC 마지막 6자리 hex).

Home Assistant는 Print Duration의 속성을 상태 변경마다 기록하므로, 그 센서의 기록에는 마지막 실패뿐 아니라 모든 인쇄의 분석이 있습니다. Last Failure와 Error Count는 재시작/리로드 시 비어서 시작합니다. 그 이전의 실패는 기록에서 찾으세요.

도움이 되는 엔티티가 둘 더 있지만, 있는 그대로 읽으세요:

- **Connection** (바이너리) — BLE 링크가 열려 있는 동안 켜집니다. **연결 유지**가 꺼져 있으면 폴링이나 인쇄 중에만, 켜져 있으면 작업 사이에도 링크가 유지되므로 *켜짐*이 곧 작업 중이라는 뜻은 아닙니다.
- **Print Progress** (인쇄 진행률) — 작업 중 프린터 자체의 페이지/피드 진행률. 작업이 죽은 지점에서 멈춥니다. 실패한 인쇄는 100 %에 도달하지 않습니다.

## 속성 읽기

속성은 다음 순서입니다. `failed_stage`는 BLE 통합구성요소들이 공유하는 이름이고, `failed_detail`은 프린터 고유의 단계 이름으로 둘이 다를 때만 있습니다.

| 속성 | 의미 |
|---|---|
| `operation` | `print`, `update`(예약된 상태 폴링), `refresh_info`(`niimbot.refresh_info` 액션), `settings`(자동 종료 / 연결음), `calibrate`, `cancel`, `reset`, `test_page`(버튼들). |
| `success` | 세션이 완료됐는지. |
| `error`, `failed_stage`, `failed_detail`, `likely_cause` | 실패 시에만: 정확한 메시지, 빠져나온 공유 단계, 그 단계의 프린터 고유 이름, 보통 무엇을 뜻하는지 한 문장. |
| `via`, `via_type`, `rssi`, `paths` | 링크가 지나간 무선(프록시 또는 로컬 어댑터), 그 무선이 마지막으로 본 프린터 신호, 지금 프린터가 보이는 연결 가능한 무선 수. `paths: 1`이면 대체할 무선이 없습니다. `connect` 실패 시 `via`는 시도한 무선입니다. |
| `advertised_via` | `via`와 다를 때만: 광고 신호가 가장 강했던 무선, 즉 Home Assistant가 먼저 시도하는 무선. 링크가 다른 곳으로 갔다면 페일오버입니다. |
| `connect_s`, `subscribe_s`, `prepare_s`, `info_s`, `transfer_s`, `finish_s`, `disconnect_s`, … | 단계별 소요 초, 실행 순서대로. 실행되지 않은 단계는 없습니다. `transfer_s`가 이미지 전송 자체이며 속도 조정 시 비교할 숫자입니다. |
| `reused_connection` | **연결 유지**가 켜져 있어 이미 열린 링크로 작업이 실행됐으면 `true` — 이 경우 `connect_s`가 없습니다. |
| `copies`, `density` | 인쇄에 요청된 값. |
| `cancelled` | `niimbot.cancel_print`나 프린터 자체 취소로 작업이 중단됐으면 `true`. 실패가 아닙니다. |
| `refresh_error` | 인쇄 후 상태 읽기(RFID / 하트비트)는 실패했지만 라벨은 이미 인쇄됨. 참고용. |

## 실패 읽기

Last Failure의 `failed_stage`부터 시작하세요: 세션이 어디까지 갔는지 공유 어휘로 말해줍니다. `failed_detail`은 같은 단계의 프린터 이름입니다. `likely_cause`는 단계, 오류 문구, 무선 상황을 종합한 해석이고, `error`는 정확한 메시지입니다.

### 프린터 오류 코드

프린터 자체가 작업을 거부하면 `error`는 `Printer error: <Code>`이고 `likely_cause`가 그것을 직접 설명합니다. `error`가 `Unsupported request 0x..`인 것은 다릅니다: 이 모델이나 펌웨어가 구현하지 않은 명령을 프린터가 NAK한 것입니다 (보통 캘리브레이션, 테스트 페이지 같은 버튼). 흔한 코드:

| 코드 | 의미 | 조치 |
|---|---|---|
| `CoverOpen` | 라벨 커버가 열림. | 닫고 다시 인쇄. |
| `LackPaper` / `PaperOutException` | 용지 없음, 또는 용지가 급지되지 않음. | 롤 다시 장착, 커버 닫기. |
| `LowBattery` / `BatteryException` | 인쇄하기엔 배터리 부족, 또는 배터리 이상. | 충전. |
| `WrongPaper` / `WrongRibbon` / `NoRibbon` / `UsedRibbon` | 소모품이 작업과 맞지 않거나 없음. | 롤 / 리본 확인; `label_type`이 용지와 맞는지 확인. |
| `Overheat` / `TemperatureLow` | 헤드가 온도 범위를 벗어남. | 기다렸다가 재시도. |
| `PrinterBusy` | 다른 작업이 실행 중 (흔히 휴대폰 앱). | 앱을 닫거나 대기. |
| `ReceiveDataTimeout` | 프린터가 이미지 데이터를 너무 오래 기다림 — 혼잡한 프록시. | `wait_between_print_lines`를 올리세요; 아래 `transfer` 참고. |

### `connect`

링크가 열리지 않았습니다.
- *`operation: update`라면 프린터의 정상 상태입니다.* 대부분 모델은 작업 사이에 꺼지거나 절전하므로, 그때 실행된 폴링은 여기서 실패합니다. Last Failure에 기록되지 않고 세지도 않습니다. **인쇄**가 같은 식으로 실패할 때만 더 들여다보세요.
- *확인:* `rssi`와 `paths`. `error`에 *slot* = 프록시의 연결 슬롯이 모두 사용 중. *settle* = 프린터가 링크를 받았다가 확립되기 전에 끊음.
- *조치:* 프린터를 켜세요. 약한 `rssi`(약 −85 dBm 이하): 프린터를 옮기거나 근처에 프록시 추가 — `paths: 1`이면 대체 무선도 없습니다. *slot*: 프록시당 BLE 기기를 줄이거나 프록시 추가.

### `session` (`failed_detail: subscribe`)

연결됐지만 프린터가 알림(notification)을 받지 않아 어떤 명령에도 응답할 수 없었습니다.
- *확인:* 매번 반복되나요?
- *조치:* 한 번: 무시, 다음 작업은 대개 성공. 매번: 프록시가 오래된 GATT 캐시를 제공하고 있을 수 있음 — 프록시 재시작.

### `session` (`failed_detail: prepare`)

연결됐지만 이미지 데이터를 보내기 전 작업 준비에서 실패했습니다: 모델을 읽지 못했거나 `label_type`이 모델이 지원하지 않는 값입니다.
- *확인:* `error`. *not supported for printer model* = 요청한 `label_type`(또는 클라우드 카탈로그에서 가져온 값)이 모델 목록 밖.
- *조치:* [devices.md](../devices.md)에서 모델의 `label_type`을 골라 넘기거나 생략. 모델이 `UNKNOWN`으로 나왔다면 Protocol Version과 Print Area 센서 값과 함께 [이슈를 열어주세요](https://github.com/eigger/hass-niimbot/issues).

### `session` (`failed_detail: info` / `settings` / `calibrate` / `cancel` / `reset` / `test_page`)

연결됐지만 프린터가 상태 읽기에 응답하지 않았거나, 설정 또는 버튼 명령을 거부했습니다.
- *확인:* `operation`이 어느 것인지 알려줍니다. *Unsupported request* = 모델이 그 명령을 구현하지 않음.
- *조치:* 상태 읽기(`info`)는 보통 일시적입니다. 한 모델에서 매번 실패하는 버튼이나 설정은 기능 지원 누락 — 모델명과 함께 이슈로 올릴 가치가 있습니다.

### `transfer`

이미지를 보내는 중 실패했습니다. 링크 품질을 가리키는 유일한 단계입니다.
- *확인:* `rssi`, `via`, `transfer_s`, 매번 같은 지점에서 죽는지. 프린터 쪽의 `ReceiveDataTimeout`은 같은 문제를 반대편에서 본 것입니다.
- *조치:* 한 번: 프린터나 사용된 프록시(`via`)를 옮기거나 하나 추가. `wait_between_print_lines`를 올리고(예: `0.02`) `print_line_batch_size`를 낮추세요(예: `8`) — [인쇄 속도 높이기](../../README.md#increasing-print-speed) 참고. 어떤 설정에서도 매번 같은 지점이라면: 속성과 함께 [이슈를 열어주세요](https://github.com/eigger/hass-niimbot/issues).

### `finish`

라벨은 전송됐고, 그 뒤 상태 읽기(RFID 잔량, 하트비트)만 실패했습니다.
- *조치:* 그 자체로는 무해 — 라벨이 나왔는지 확인하세요. 소모품 센서만 다음 폴링까지 한 작업 뒤처질 수 있습니다. **다음** 작업이 `PrinterBusy`로 거부되면 프린터가 이전 작업을 닫지 않은 것입니다: 전원을 껐다 켜세요.

### 빠른 확인

- **`rssi`가 낮은데 `paths`가 2 이상** — 다른 무선이 더 나을 수 있습니다. Home Assistant는 광고 신호가 가장 강한 쪽으로 연결하므로 대안은 실패 후에만 쓰입니다. `via`로 어느 것이 사용됐는지 확인하세요.
- **프록시를 추가한 직후 모든 것이 `connect`에서 실패** — 프록시는 `esp32_ble_tracker`와 `bluetooth_proxy` 양쪽 모두 `active: true`여야 합니다 ([README](../../README.md#important-notice) 참고). 패시브 프록시는 프린터를 보기만 하고 연결은 못 합니다.
- **휴대폰 앱이 열린 상태에서 인쇄 시 `error: ConnectFailed`** — 대부분 모델은 클라이언트 하나만 받습니다. 앱을 닫으세요.
- **`reused_connection: true` 다음에 `transfer` 실패** — 오래 유휴 상태로 열어둔 링크는 일부 프록시에서 stale 해질 수 있습니다. **연결 유지**를 끄고 비교해 보세요.
- **아무것도 인쇄하지 않는데 Error Count가 올라감** — 연결 후 실패한 폴링(`failed_stage: session`, `failed_detail: info`) — 보통 프록시 문제, 위 참고. 또는 자동화의 `refresh_info` 액션이 프린터가 꺼진 동안 실행되고 있음 (폴링과 달리 이것은 *셉니다*).

## 속성으로는 볼 수 없는 것

세션이 실패하지 않았거나 — 아예 일어나지 않았기 때문에 — 실패 센서에 절대 도달하지 않는 문제가 세 종류 있습니다.

**인쇄는 성공했는데 라벨이 잘못됨.** `success: true`인데 라벨이 비었거나, 잘렸거나, 뒤집혔거나, 배율이 틀림. 이미지는 프린터에 도달했고, 렌더링이나 모델의 인쇄 폭이 어긋난 것입니다. **Last Label Made**(전송된 것)를 보세요: 그게 틀리면 페이로드를 고치세요 — **개발자 도구 → 액션**에서 `preview: true`로 재현. 이미지는 맞는데 인쇄가 배율/위치가 틀리면 모델의 `printheadPixels`가 추정값일 수 있습니다 — 로그에 모델당 한 번 *uses an estimated printheadPixels value* 경고가 납니다. 보이는 결과를 이슈로 알려주세요.

**BLE 통신 전에 액션 자체가 오류.** 렌더링되지 않는 페이로드, 모델 범위 밖의 `density`나 `label_type`(*is not supported for this printer*), 어떤 무선도 지금 보지 못하는 프린터(*could not find printer with address …*): 액션은 그 메시지로 즉시 실패하며 세션 센서에는 아무것도 기록되지 않습니다. 액션 추적이나 UI에 표시된 오류를 확인하세요.

**세션이 시도되지 않음.** 어떤 무선도 프린터를 보지 못하면 상태 폴링은 캐시된 값을 반환하고 경고만 로그에 남깁니다. 센서는 마지막 값을 유지하고 **Connection**은 꺼진 채입니다. 프린터를 켜고 스캔 간격 하나를 기다리거나 `niimbot.refresh_info`를 호출하세요.

## 간헐적 실패

가끔만 실패하는 인쇄가 바로 Last Failure가 속성을 유지하는 이유입니다: 이미 나중 성공을 보여주는 Print Duration이 아니라 거기를 보세요. 실패 시점의 `failed_stage`와 `rssi`가 중요합니다. 실패가 한 `via`에 몰려 있으면 그 프록시가 문제이고, 매번 `paths`가 1이었다면 두 번째 무선이 대안이 됐을 것입니다.

## 이슈에 첨부할 것

1. **Last Failure** 속성 (개발자 도구 → 상태 → 엔티티 → 속성 블록 복사). 실패가 마지막 인쇄가 아니라면 그 시각 전후 기록에서 **Print Duration** 속성도.
2. 프린터 모델과 **Protocol Version** / **Print Area** 센서 값.
3. 실패가 `connect`나 `transfer`라면 프린터가 사용하는 무선 (`via` — 프록시 모델과 ESPHome 버전, 또는 어댑터).
4. 라벨이 잘못 나온 경우: **Last Label Made** 이미지와 인쇄물 사진.

디버그 로깅은 거의 필요 없습니다. 요청받으면 `logger:` 아래 `custom_components.niimbot: debug`를 추가하고 한 번 재현하세요.
