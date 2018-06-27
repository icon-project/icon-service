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
(icon) $ ./build.sh build

# 패키지 파일 생성 확인
(icon) $ cd dist
(icon) $ ls 
iconservice-x.x.x-py3-none-any.whl
```

## Build script
```bash
build.sh [test|build|deploy]
```
* Options
  - test: test 실행
  - build: test 후 build 실행
  - build --ignore-test: build 실행
  - deploy: test, build 후 s3에 deploy
  - deploy --ignore-test: build 후 s3에 deploy
    \*\*deploy가 실행 되기 위해선 `AWS_ACCESS_KEY_ID`와 `AWS_SECRET_ACCESS_KEY`가 환경변수로 선언이 되어 있어야 한다

* Tbears
  - tbears의 build script 사용법도 동일
  - **dependencies**: iconservice의 의존을 충족 하여야 함
    - **default**: S3에 올라가 있는  `iconservice.whl`을 다운받아 설치하여 의존을 충족
    - **iconservice repository 지정**: 환경변수로 `ICONSERVICEPATH` 를 지정하면 whl 설치 없이 repository로 의존을 충족
    
      예)
        ```bash
        $ export ICONSERVICEPATH=../icon
        $ build.sh test
        ```



## CI/CD
* Jenkins Url: [https://jenkins.theloop.co.kr](https://jenkins.theloop.co.kr) (goldworm/@ucoin)
* Path: 
  - iconservice: ICON > ICON_iconservice
  - tbears: ICON > ICON_tbears
* Task
  - On branch `develop`: test
  - On branch `master`: test, package, deploy to S3

## 배포 URL
> http://tbears.icon.foundation.s3-website.ap-northeast-2.amazonaws.com


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
* [tbears tutorial](docs/tbears_tutorial.md)
* [(Deprecated) tbears tutorial - GoogleDocs](https://docs.google.com/document/d/1TTD_eR8-LlgVAYGo7knwJ7kCA6AZ9-YpiWyVrTtiPj4/edit?usp=sharing)
