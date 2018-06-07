# ICON Service Engine

## Overview

* loopchain과 SCORE 구동 엔진 간의 의존성 제거
* 코인 잔고 관리
* Multi SCORE support
* TX 처리 수수료 처리를 위한 STEP 소비량 계산
* SCORE 개발용 기반 클래스 및 데이터 클래스 제공
* 전월세 수수료 모델 적용
* SCORE 설치 절차 정립 (설치 요청 + 승인)

## How to build

IconService PIP 패키지 생성 방법

```bash
# ICON 디렉토리로 이동
$ cd icon

# virtualenv 환경으로 진입
$ source bin/source

# pip packaging 스크립트 실행
(icon) $ ./build.sh

# 패키지 파일 생성 확인
(icon) $ cd dist
(icon) $ ls 
iconservice-x.x.x-py3-none-any.whl
```

## CI/CD
* Jenkins Url: [https://jenkins.theloop.co.kr](https://jenkins.theloop.co.kr) (goldworm/@ucoin)
* Path: ICON > ICON_iconservice
* Task
  - On branch `develop`: test
  - On branch `master`: test, package, deploy to S3


## Directories

* docs: 문서
* iconservice: IconService 소스 코드
* message_queue: MQ 패키지 코드
* tests: 테스트 코드
* tools: curl을 사용하는 tbears 테스트용 bash script

## Documents

* [ChangeLog](docs/CHANGELOG.md)
* [IconService 설계 문서](docs/class.md)
* [Dapp 작성 가이드 문서](docs/dapp_guide.md)
* [ICON JSON-RPC API v3](docs/tbears_jsonrpc_api_v3.md)
* [icx_getTransactionResult JSON API 확장](docs/improve-get-transaction-result.md)
* [tbears tutorial - GoogleDocs](https://docs.google.com/document/d/1TTD_eR8-LlgVAYGo7knwJ7kCA6AZ9-YpiWyVrTtiPj4/edit?usp=sharing)
