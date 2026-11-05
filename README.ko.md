<!-- hass-standards:header:start -->
# Niimbot for Home Assistant

imagespec 레이아웃을 Niimbot Bluetooth 프린터로 전송해 라벨을 인쇄하는 Home Assistant 커스텀 통합입니다.

[English](README.md) | **한국어**

<!-- hass-standards:badges:start -->
[![Release](https://img.shields.io/github/v/release/eigger/hass-niimbot?style=flat)](https://github.com/eigger/hass-niimbot/releases)
[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5?style=flat)](#설치)
[![Home Assistant minimum](https://img.shields.io/badge/HA-%E2%89%A5%202025.1.0-41BDF5?style=flat)](hacs.json)
[![Tests](https://img.shields.io/github/actions/workflow/status/eigger/hass-niimbot/tests.yml?branch=master&style=flat&label=Tests)](https://github.com/eigger/hass-niimbot/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/eigger/hass-niimbot/validate.yml?branch=master&style=flat&label=Validate)](https://github.com/eigger/hass-niimbot/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/eigger/hass-niimbot?style=flat)](LICENSE)
[![Downloads](https://img.shields.io/github/downloads/eigger/hass-niimbot/latest/total?style=flat&color=41BDF5&label=Downloads)](https://github.com/eigger/hass-niimbot/releases)
<!-- hass-standards:badges:end -->
<!-- hass-standards:header:end -->

<img title="B1 / B1 Pro" src="docs/images/b1.jpg" width="280" alt="B1 / B1 Pro"> <img title="B21 Pro" src="docs/images/b21pro.jpg" width="280" alt="B21 Pro"> <img title="D110" src="docs/images/d110.jpg" width="280" alt="D110">

**사진 속 모델** · B1 / B1 Pro / B21 Pro / D110

## 요구사항

- **Home Assistant:** 2025.1.0 이상.
- **Python:** 기존 런타임 의존성 때문에 3.13 이상이 필요합니다. Python 3.12에서 실행하는 Home Assistant 2025.1은 호환 런타임을 사용하세요.
- **Bluetooth:** 연결 가능한 Home Assistant Bluetooth 어댑터 또는 활성 ESPHome Bluetooth 프록시.
- **기기:** 지원되는 Niimbot BLE 프린터.

## 설치

<!-- hass-standards:installation:start -->
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=eigger&repository=hass-niimbot)
<!-- hass-standards:installation:end -->

1. 위 배지를 클릭해 마켓플레이스에서 저장소를 엽니다.
2. 저장소를 직접 추가하려면 **설정 → 마켓플레이스 → 링크에서 추가**에서 <https://github.com/eigger/hass-niimbot>을 입력합니다. 안내가 표시되면 GitHub 계정을 연결합니다.
3. **설치**를 선택합니다. 재시작 안내가 표시되면 Home Assistant를 재시작합니다. 설치가 끝나면 [설정](#설정)으로 이동합니다.

## 설정

프린터 전원을 켜고 절전 상태에서 깨운 뒤 NIIMBOT 휴대폰 앱의 연결을 해제합니다. **설정 → 기기 및 서비스 → 통합 추가 → Niimbot**에서 발견된 프린터를 선택합니다.

[Bluetooth 프록시 설정](https://github.com/eigger/blesession/blob/main/docs/bluetooth.ko.md), [Niimbot 설정(영어)](docs/setup.md#bluetooth-connection), [문제 해결](docs/troubleshooting.ko.md)을 참고하세요.

## 빠른 시작

통합 옵션에서 **Fetch Label Info Online**을 켜고 **Cloud Label Info** 조회가 성공하면 장착된 라벨 크기를 자동으로 사용합니다. **개발자 도구 → 액션**에서 프린터를 대상으로 다음 예제를 실행합니다.

```yaml
action: niimbot.print
target:
  device_id: <your device>
data:
  payload:
    - type: text
      value: Hello World!
      x: 10
      y: 10
      size: 28
```

[페이로드 안내](docs/payload.ko.md), [예제 모음 (영어)](examples/README.md), [액션 매개변수 (영어)](docs/actions.md), [imagespec 요소 참조 (영어)](https://github.com/eigger/imagespec/blob/main/docs/elements.md)에서 인쇄·자동화 예제를 확인할 수 있습니다.

<a name="주요-제한사항"></a>

## 중요 제한사항

대표 확인 모델은 B1, B1 Pro, B2 Pro, B21 Pro, D110입니다. 다른 모델·펌웨어는 동작이 다를 수 있습니다. 모델별 DPI, 크기, 회전, 농도와 자동 크기 우선순위는 [라벨 크기 안내 (영어)](docs/label-sizing.md), 전체 모델·용지 종류는 [기기 참조 (영어)](docs/devices.md)를 확인하세요.

온라인 라벨 조회는 기본적으로 꺼져 있습니다. 켜면 라벨 제품 바코드만 NIIMBOT 카탈로그에 전송합니다. 조회가 실패하면 크기를 직접 지정하세요. 기존 `400×240` px 기본값은 모든 라벨에 맞지 않습니다. BLE 전송 성공이 실제 인쇄 품질 검증을 뜻하지는 않습니다.

<a name="문서와-지원"></a>

## 문서

- [문서 목록 (영어)](docs/README.md)
- [설정과 옵션 (영어)](docs/setup.md)
- [문제 해결](docs/troubleshooting.ko.md) ([English](docs/troubleshooting.md))
- [개발과 테스트 (영어)](CONTRIBUTING.md)

<!-- hass-standards:support:start -->
## 지원

- [Issues](https://github.com/eigger/hass-niimbot/issues): 버그를 신고하거나 기능을 요청하세요.
- [Discussions](https://github.com/eigger/hass-niimbot/discussions): 질문하고 사용 경험을 공유하세요.
<!-- hass-standards:support:end -->

<!-- hass-standards:related-projects:start -->
## 관련 프로젝트

- [imagespec](https://github.com/eigger/imagespec): 페이로드 렌더러와 요소 참조
- [niimblue](https://github.com/MultiMote/niimblue): Niimbot 프로토콜 구현
- [Stash](https://github.com/eigger/stash): Niimbot 인쇄를 지원하는 재고 관리 도구
<!-- hass-standards:related-projects:end -->

<!-- hass-standards:license:start -->
## 라이선스

[MIT License](LICENSE) 라이선스로 배포됩니다.
<!-- hass-standards:license:end -->
