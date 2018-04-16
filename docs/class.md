# IconService 설계 문서

작성자: 조치원
작성일: 2018.03.20(화)

## Overview

## Architecture

### Communication between components

* loopchain을 구성하는 각 Component들과의 통신 부분 구현
* loopchain engine과의 결합성을 줄일 것

#### IconService

* Icon 관련 서비스의 메인이 되는 클래스
* 별도의 프로세스로 동작하며 loopchain과는 IPC 통신
* 다른 언어로 개발될 수 있다.

#### Connector

* loopchain과의 통신 처리
  * grpc
  * MQ + jsonrpc
* 통신 방법이 변경되더라도 Connector만 변경하면 되도록 구현 필요

### Icx Coin Management

* icx 코인 이체
* icx 잔고 조회
* 다른 IconScore부터의 메시지콜 요청 지원

#### IcxEngine

* icx 코인 이체 및 조회 관리
* icx_score에서 사용하던 객체 재활용

### Multiple IconScore Management

* IconService에서 실행되는 IconScore들의 LifeCycle 관리

#### IconScore

* Icon Smart Contract
* 각 Icon Score마다 고유의 주소를 가짐

#### IconScoreFactory

* 새로운 IconScore를 동적으로 생성할 수 있는 Icon Score
* loopchain이 재기동될 때 자신이 생성한 Icon Score들도 함께 생성해야 한다.
* One Code Multi Instance Score 지원을 위해 필요

#### IconScoreContext

IconScore 내에서 사용 가능한 정보나 함수 지원

* block: block information
  * block.coinbase
  * block.number
  * block.timestamp
* msg
  * msg.sender
  * msg.value
  * msg.gas_left()
* tx
  * tx.gasprice
  * tx.origin

#### IconScoreInstaller

* IconScore 코드를 지정된 파일 경로에 설치
* mime-type에 따라 다양한 설치자 존재 가능 (zip, url 등등)
* IconScore 구성 파일들에 대한 무결정 확인 (sha3_256 사용)

#### IconScoreLoader

* 파일 시스템에 저장되어 있는 IconScore를 로딩
* 로딩된 IconScore 객체를 IconScoreEngine에 등록
* IconScoreEngine과의 의존성이 없어야 한다.

#### IconScoreEngine

* IconScore들의 생명주기 관리 (등록, 업데이트, 제거)
* 주소로 구분되는 IconScore의 함수 호출
* IconScoreLoader와의 의존성이 없어야 한다.

### IconScore State Management

* IconScore의 상태를 저장하기 위해 Key:Value 기반의 Database가 사용된다.
* 각 IconScore는 하나의 상태 DB를 가진다.
* Block이 합의되어 BlockChain에 저장되기 전에는 해당 Block의 transaction으로 변경된 상태는 메모리에 저장된다. (Precommit)

#### MemoryDatabase

* 상태가 변경되었지만 합의가 완료되지 않아 영구 저장소(파일)에 기록될 수 없는 데이터를 저장
* IconScore 개발자는 자신이 사용하는 Database 객체가 MemoryDatabase인지 FileDatabase인지 알 수 없도록 추상화한다.

#### FileDatabase

* plyvel 패키지를 이용하여 levedb 데이터를 조회하거나 기록할 때 사용

#### ReadOnlyDatabase

* 정보 조회 목적으로만 사용하는 Database
* 정보 변경 메소드 수행 시 예외 발생

### Gas Calculation

* IconScore를 실행하면서 발생하는 수수료를 계산한다.
* Client vs 서비스 제공자 간 수수료 부담 비율을 고려하여 IconScore 실행 수수료를 지불 처리한다.

### GasPriceTable

### Gas

### 기타

#### Logging

* 오류 원인 분석을 지원하기 위한 로그 정보 기록