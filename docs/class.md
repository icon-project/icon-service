# IconService 설계 문서

## 문서 이력

| 일시 | 버전 | 작성자 | 비고 |
|:------|:-----|:---:|:--------|
| 2018.06.04 | 0.9.0 | 조치원 | 0.9.0 형식에 맞추어 문서 갱신 |
| 2018.03.20 | 0.0.0 | 조치원 | 최초 작성 |

## Overview

* loopchain과 SCORE 구동 엔진 간의 의존성 제거
* 코인 잔고 관리
* Multi SCORE support
* TX 처리 비용을 STEP 단위로 통일
* SCORE 개발 편의성 강화
* 전월세 수수료 모델 적용
* SCORE 설치 절차 정립 (설치 요청 + 승인)

## Architecture

### Communication between components

* loopchain을 구성하는 각 Component들과의 통신 부분 구현
* loopchain engine과의 결합성을 줄일 것

#### IconServiceEngine class

* ICON 관련 서비스의 메인이 되는 클래스
* 코인 관리와 SCORE 관리는 모두 이 클래스 내에서 수행된다.
* 통신 방법을 포함하여 loopchain과의 어떠한 의존성도 존재해서는 안된다.

#### IconScoreInnerService class

* loopchain과의 통신 처리 (MQ 방식)
* 통신 방법이 변경되더라도 이 부분만 변경되어야 한다.

### base package

* 패키지 내에서 공통적으로 사용되는 기반 클래스들 제공
* address, block, exception, message, transaction 등등

### database package

* LevelDB Wrapper
* DB에 기록 전 Cache 관리

### icx package

* 코인 이체
* 코인 잔고 조회
* 계좌 주소 객체 정의
* 계좌 데이터를 DB에 기록

#### IcxEngine class

* 코인 이체 및 조회 관리
* SCORE 에서는 이 객체를 통해 코인 이체 및 조회 가능

### iconscore package

* SCORE LifeCyle 관리 (설치, 로딩, 실행)
* SCORE 개발에 필요한 기반 클래스 및 데이터 클래스 제공
* SCORE 실행 시 필요한 정보를 담고 있는 Context 클래스
* SCORE 실행 단계별 STEP 소비량 계산

#### IconScoreBase class

* SCORE 를 만들기 위해서 반드시 상속받아야 하는 기반 클래스
* 각 SCORE 마다 고유의 주소를 가짐
* SCORE 구현을 위해 필요한 정보 객체와 API 제공

#### IconScoreFactory class (미구현)

* 새로운 SCORE 를 동적으로 생성할 수 있는 방법 제공
* IconServiceEngine 이 재기동될 때 자신이 생성한 SCORE 들도 함께 생성해야 한다.
* One Code Multi Instance SCORE 지원을 위해 필요

#### IconScoreContext class

IconScore 내에서 사용 가능한 정보나 함수 지원

* block: block information
    - block.hash
    - block.number
    - block.timestamp
* msg
    - msg.sender
    - msg.value
    - msg.step_left()
* tx
    - tx.origin
    - tx.timestamp
    - tx.nonce

#### IconScoreDeployer

* SCORE 설치 패키지를 지정된 파일 경로에 설치
    * $SCORE_ROOT/address_without_prefix/blockHeight_txIndex
* contentType에 따라 다양한 설치자 존재 가능 (zip, url 등등)

#### IconScoreLoader

* 파일 시스템에 저장되어 있는 SCORE를 메모리에 로딩
* IconScoreInfoMapper 클래스 내에서 사용된다.

#### IconScoreEngine

* iconscore 패키지 내 메인 클래스
* SCORE 들의 생명주기 관리 (설치, 업데이트, 실행 등)

#### IconScoreResult

* TransactionResult 정의 클래스

#### IconScoreStepCounter

* 각 항목별 STEP 소비량 계산

### database

* IconScore의 상태를 저장하기 위해 Key:Value 기반의 Database가 사용된다.
* 확정되기 전 블록에 저장되어 있는 tx에 의해 변경된 상태는 메모리에 저장된다. (Batch)
* 해당 블록이 확정되면 영구 저장소(LevelDB)에 기록한다.

#### PlyvelDatabase

* plyvel 패키지를 이용하여 LevelDB 데이터를 조회하거나 기록할 때 사용

#### ContextDatabase

* IconScoreContext를 파라메터로 입력 받는다.
* 현재 Context의 정보에 따라 상태 값을 Batch에 적을지 실제 LevelDB에 기록할지를 결정한다.

#### IconScoreDatabase

* SCORE에게 전달되는 DB 객체
* 내부에 ContextDatabase 객체를 포함한다.

### logger

#### Logger

* SCORE 및 IconServiceEngine 디버깅 로그 저장 기능 지원

### utils

* 일반 유틸리티 함수 및 클래스 정의
