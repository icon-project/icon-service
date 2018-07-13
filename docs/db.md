SCORE Database 구조 명세서
=========================

이 문서에서는 iconservice가 KeyValue 기반 Database 상에 어떠한 데이터를 저장하는지 그리고 그 데이터가 어떠한 형식으로 저장되어 있는지에 대해 기술한다.

# 문서 이력

| 일시 | 작성자 | 비고 |
|:---:|:-----:|:-----|
| 2018.07.12 | 조치원 | 초기 작성 |

# 개요

* 현 시점에서 KeyValue 기반 DB는 LevelDB 오픈소스를 사용하고 있다.
* LevelDB 상의 모든 데이터는 bytes 형식의 key와 bytes 형식의 value로 저장되어 있다.
* loopchain에서는 Block, Transaction, TransactionResult 저장을 위한 별도의 KeyValue DB를 사용하고 있으며 이 부분은 이 문서에서는 언급하지 않는다.
* 현 시점(iconservice-0.9.3)에서는 SCORE별로 별도의 DB를 사용하고 있으나 추후 버전부터는 하나의 DB로 통합될 예정이다.

# 설명

iconservice에서 DB에 저장하는 데이터의 종류는 크게 3가지로 나눌 수 있다.

* icx 계좌 정보: loopchain 망의 기반 통화 icx의 계좌들에 대한 잔고 및 상태 관리
* SCORE 상태 정보: 각 SCORE들이 관리하는 상태 데이터
* 기타 데이터
    * SCORE 배포 정보
    * GENESIS 및 FEE_TREASURY 계좌 주소
    * 기타 iconservice 동작에 필요한 데이터
    
## 데이터 형식 별 DB 저장 방법

| 데이터 형식 | 크기(bytes) | 설명 |
|:-----------|:-----------|:-----|
| Address | 21 | body(20) + prefix(1)<br>prefix: EOA(0), CONTRACT(1) |
| int | 가변 | 해당 수를 저장할 수 있는 최초 bytes을 구한 후 big endian 형식으로 encoding한 후 저장 |
| string | 가변 |utf-8 인코딩 방식으로 저장 |
| bytes | 가변 | 원본 그대로 저장 |

## icx 계좌 정보

ICON의 기반 통화인 icx의 계좌 정보는 다음의 형식으로 저장된다.

```
| key(20)     | value(36)                                               |
| address(20) | version(1) | type(1) | flags(1) | reserved(1) | icx(32) |
```

| 이름 | 데이터 형식 | 크기(byte) | 설명 |
|:----|:----------:|:----------:|-----|
| key | Address | 20 | icx 계좌의 주소 |
| version | int | 1 | 데이터 구조의 버전 |
| type | int | 1 | 계좌의 종류를 나타내는 정수값<br>EOA(0), GENESIS(1), TREASURY(2), CONTRACT(3) |
| flag | int | 1 | 계좌의 속성을 나타내는 bitwise 플래그값<br>C_REP(1), LOCKED(2) |
| reserved | int | 1 | 나중 사용을 위한 예약 영역 |
| icx | big endian int | 32 | 해당 계좌에 보관되어 있는 icx 코인양 |

## SCORE가 관리하는 상태 데이터

* SCORE들이 내부적으로 관리하는 상태 데이터
* icx_sendTransaction JSON-RPC 요청을 통해 수신된 transaction을 통해서만 상태가 변경될 수 있다.

### 기본 데이터 형식 별 DB value 저장 방식

| 데이터 형식 | 크기(bytes) | 설명 |
|:-----------|:-----------|:-----|
| Address | 21 | body(20) + prefix(1)<br>prefix: EOA(0), CONTRACT(1) |
| int | 가변 | 정수를 저장할 수 있는 최소 필요 byte 길이를 구한 후 big endian 형식으로 저장 |
| string | 가변 |utf-8 인코딩 형식으로 저장 |
| bytes | 가변 | 원본 그대로 저장 |

### Container 별 내부 item key 생성 방식

sep = '|' 문자 (0x7c)

#### DictDB

```
db_key = sha3_256(score_address + sep + type(0x00) + sep + var_key + sep + dict_key)
```

#### ArrayDB

```
db_key = sha3_256(score_address + sep + type(0x01) + sep + var_key + sep + index)
```

#### VarDB

```
db_key = sha3_256(score_address + sep + type(0x02) + sep + var_key)
```

### SCORE DB 통합 전 (iconservice-0.9.4 이전)

SCORE마다 물리적으로 분리된 KeyValueDB를 할당 받는다.
곧 Deprecated 될 예정

### SCORE DB 통합 후 (iconservice-0.9.4 이후)

* icx 계좌 정보, SCORE가 관리하는 상태 데이터, 기타 데이터 모두 하나의 KeyValueDB에 포함된다.
* 각 SCORE로 부터 입력받은 key가 충돌하는 경우를 방지하기 위해 해당 key는 SCORE 주소 + key 데이터의 해쉬값으로 변환된 후에 실제 DB에 저장된다.

#### SCORE 상태 데이터 Key 생성 방법

```
db_key = sha3_256(score_address + sep + score_key)
```

| 이름 | 형식 | 크기(byte) | 설명 |
|:----|:----:|:---------:|:-----|
| db_key | bytes | 32 | 실제 KeyValueDB에 저장되는 SCORE 상태 데이터의 key 값 |
| score_address | bytes | 20 | SCORE 주소 |
| sep | bytes | 1 | '&#x7c;' 문자 (0x7c) |
| score_key | bytes | > 0 | SCORE 코드 내에서 상태 DB에 넘겨주는 key 값 |

# 참고 자료

* [LevelDB github](https://github.com/google/leveldb)
* [plyvel github](https://github.com/wbolster/plyvel)