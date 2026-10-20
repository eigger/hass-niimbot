# Niimbot 페이로드

[English](payload.md) | **한국어** · [README](../README.ko.md)

## 공통 payload 안내

공통 문법, 요소, 폰트, 색상, 회전, 디더링은 [imagespec 페이로드 안내](https://github.com/eigger/imagespec/blob/main/docs/payload.ko.md)를 확인하세요. Niimbot은 설치된 `imagespec[datamatrix]` 렌더러를 사용합니다.

## 이 통합에서 payload 사용

`niimbot.print` 액션은 `data.payload`의 요소 목록을 받습니다. 설정된 프린터의 이미지 엔티티 또는 기기를 대상으로 선택하세요. 로딩된 프린터가 하나면 대상 생략 시 자동 선택하며, 여러 대면 대상을 명시해야 합니다. 미리보기와 실제 인쇄는 같은 production `render_image` 함수를 사용합니다. 전체 API는 기존 [액션 (영어)](actions.md), [예제 (영어)](../examples/README.md)를 확인하세요.

Home Assistant가 액션 템플릿을 먼저 처리하고 imagespec에는 처리된 값이 전달됩니다. 페이로드 요소 내부에 별도 Jinja 엔진은 제공하지 않습니다. 폰트는 파일명 기준으로 통합의 `fonts/` 폴더, `/config/www/fonts/` 순으로 찾으며 기본값은 동봉된 `ppb.ttf`입니다. 이력 요소에는 실제 HA recorder 이력 공급자를 전달합니다. 로컬·원격 이미지 및 선택 바코드 의존성은 설치된 imagespec 안내를 따릅니다. 최소 예제는 네트워크, 외부 파일, 선택 기능을 검증하지 않습니다.

## 최소 동작 예제

전체 [미리보기 액션](../examples/payload/minimal.yaml)을 개발자 도구 → 액션에 열고 `image.niimbot_label`을 본인 프린터의 이미지 엔티티로 바꾸세요. 예제는 240 × 96 px 캔버스와 `preview: true`를 지정하므로 기기로 전송하지 않고 미리보기만 만듭니다. 미리보기를 확인한 후 크기에 맞는 롤을 장착하고 `preview: false`로 바꾸면 인쇄합니다. 먼저 프린터를 깨우고 NIIMBOT 휴대폰 앱을 종료하세요.

계약 검사는 실제 HA entry와 액션을 로딩하고 HA가 YAML을 처리한 뒤 production 경로로 렌더링합니다. 기기 명령은 보내지 않으며 픽셀 비교는 실물 인쇄 품질 검증을 대신하지 않습니다.

## 기기 출력 설정

Niimbot은 흑백(`#000000`, `#ffffff`)으로 렌더링하며 기본 배경은 흰색입니다. 전체 이미지 디더링은 꺼져 있고 지원되는 사진·차트 요소는 자체 디더링을 지정할 수 있습니다. 회전은 `rotate_mode="image"`로, 90°/270°에서 출력 폭과 높이가 바뀝니다. 최소 예제는 0°로 240 × 96 px를 출력하며 203 DPI에서 약 30 × 12 mm입니다. 회전된 D110 방식은 기존 [기존 예제 목록](../examples/README.md)의 D110 예제를 참고하세요.

액션에서 지정한 width/height/rotate가 클라우드 라벨 크기보다 우선합니다. 생략하면 온라인 조회 활성화 및 성공 시 조회값을 사용하고, 그렇지 않으면 기존 400 × 240 px, 0° 기본값을 사용합니다. 이 값은 모든 롤에 맞지 않습니다. [라벨 크기 안내 (영어)](label-sizing.md)에서 실제 DPI, 헤드 폭, 롤 크기를 선택하세요. 인쇄 농도와 용지 종류는 인쇄 시 확인된 모델에 맞게 검증됩니다.

## 지원 기능과 제한

텍스트, 도형, 이미지, 지원 바코드·Data Matrix, recorder 이력 요소는 imagespec이 제공하며 설치된 extras와 폰트·파일 조건을 따릅니다. 이 통합은 범용 컬러 인쇄나 폰트 다운로드 서비스를 추가하지 않습니다. BLE 전송 완료만으로 배율, 여백, 펌웨어 동작을 검증할 수 없습니다. 모델별 명령과 추정 인쇄 폭이 다를 수 있으므로 크기를 정할 때 [기기 참조 (영어)](devices.md)와 기존 예제를 보존해 확인하세요.

로컬 계약 검증은 주변 프린터 없이 설정한 HA entry와 동봉 폰트를 사용합니다. 실제 recorder 이력, 원격 이미지, 프록시 펌웨어, 실물 출력, 모든 선택 요소는 해당 데이터·기기로 별도 확인해야 합니다.

## 문제 해결

페이로드 오류나 출력 이상은 재시도 전에 액션 오류와 미리보기를 확인하세요. [기기별 문제 해결](troubleshooting.ko.md)과 기존 [Issues](https://github.com/eigger/hass-niimbot/issues)를 이용하세요. 로그·미리보기 공개 전에 주소, 개인 라벨 내용, 인증 정보를 제거하세요.
