Governance SCORE API
====================

Governance SCORE가 제공하는 API를 설명한다.

| 일시 | 작성자 | 비고 |
|:----|:-----:|:----|
| 2018.06.21 | 조치원 | 초기 작성 |

# VALUE 형식

기본적으로 모든 JSON-RPC 메시지 내의 VALUE는 문자열 형식으로 되어 있다.<br>
많이 사용하는 "VALUE 형식"은 다음과 같다.

| VALUE 형식 | 설명 | 예 |
|:----------|:-----|:---|
| <a id="T_ADDR_EOA">T_ADDR_EOA</a> | "hx" + 40 digit HEX 문자열 | hxbe258ceb872e08851f1f59694dac2558708ece11 |
| <a id="T_ADDR_SCORE">T_ADDR_SCORE</a> | "cx" + 40 digit HEX 문자열 | cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32 |
| <a id="T_HASH">T_HASH</a> | "0x" + 64 digit HEX 문자열 | 0xc71303ef8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238 |
| <a id="T_INT">T_INT</a> | "0x" + lowercase HEX 문자열 | 0xa |
| <a id="T_BIN_DATA">T_BIN_DATA</a> | "0x" + lowercase HEX 문자열<br>문자열의 길이가 짝수여야 한다 | 0x34b2 |
| <a id="T_SIG">T_SIG</a> | base64 encoded 문자열 | VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA= |
| <a id="T_DATA_TYPE">T_DATA_TYPE</a> | install: SCORE 설치<br>update: 기존 SCORE 업데이트<br>call: SCORE에서 제공하는 함수 호출 | - |

# Overview

* 블록 체인 망을 운영하는데 필요한 각종 항목을 관리하는 Built-in SCORE를 의미한다.
* 주소: cx0000000000000000000000000000000000000001

# Query Methods

상태 변경 없이 조회만 가능한 Method

## getScoreStatus

* SCORE의 상태를 조회한다.
* 현재 SCORE의 동작 상태와 차기 SCORE의 심사 상태를 알 수 있다.

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:-----------|-----|
| address | [T_ADDR_SCORE](#T_ADDR_SCORE) | 조회할 SCORE 주소 |

### Examples

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": 0,
    "method": "icx_call",
    "params": {
        "from": "hx...", // optional
        "to": "cx0000000000000000000000000000000000000001",
        "dataType": "call",
        "data": {
            "method": "getScoreStatus",
            "params": {
                "address": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32"
            }
        }
    }
}
```

#### Response: SCORE install case

```json
// Response - 설치 요청, 심사 중
{
    "jsonrpc": "2.0",
    "id": 0,
    "result": {
        "next": {
            "status": "pending", // "rejected"
            "deployTxHash": "0x..." // deploy txHash
        }
    }
}

// Response - 심사 완료: accepted
{
    "jsonrpc": "2.0",
    "id": 0,
    "result": {
        "current": {
            "status": "active",
            "deployTxHash": "0x...",
            "auditTxHash": "0x..."
        }
    }
}

// Response - 심사 완료: rejected
{
    "jsonrpc": "2.0",
    "id": 0,
    "result": {
        "next": {
            "status": "rejected",
            "deployTxHash": "0x...",
            "auditTxHash": "0x..."
        }
    }
}
```

#### Response: SCORE update case

```json
// Response - update 요청, 심사 중
{
    "jsonrpc": "2.0",
    "id": 0,
    "result": {
        "current": {
            "status": "active", // or "inactive"
            "deployTxHash": "0x...",
            "auditTxHash": "0x..."
        },
        "next": {
            "status": "pending",
            "deployTxHash": "0x..."
        }
    }
}

// Response - update 요청, 심사 완료: rejected
{
    "jsonrpc": "2.0",
    "id": 0,
    "result": {
        "current": {
            "status": "active", // or "inactive"
            "deployTxHash": "0x...",
            "auditTxHash": "0x..."
        },
        "next": {
            "status": "rejected",
            "deployTxHash": "0x...",
            "auditTxHash": "0x..."
        }
    }
}
```

#### Response: error case

```json
{
    "jsonrpc": "2.0",
    "id": 0,
    "error": {
        "code": -32062,
        "message": "SCORE not found"
    }
}
```

# Invokde Methods

상태를 변경하는 Method

## acceptScore

* SCORE 등록 요청을 수락한다.
* SCORE 등록을 심사할 수 있는 권한을 가진 주소들만이 호출 가능하다.
* SCORE는 승인이 완료된 블록의 다음 블록부터 사용이 가능하다.

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:-----------|-----|
| txHash | [T_HASH](#T_HASH) | SCORE 설치 혹은 업데이트를 요청한 transaction의 hash 값 |

### Examples

#### Request

```json
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 1234,
    "params": {
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "to": "cx0000000000000000000000000000000000000001",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "call",
        "data": {
            "method": "acceptScore",
            "params": {
                "txHash": "0xb903239f8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238"
            }
        }
    }
}
```

## rejectScore

* SCORE 등록 요청을 거절한다.
* SCORE 등록을 심사할 수 있는 권한을 가진 주소들만이 호출 가능하다.

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:-----------|-----|
| txHash | [T_HASH](#T_HASH) | SCORE 설치 혹은 업데이트를 요청한 transaction의 hash 값 |
| reason | T_TEXT | SCORE 등록을 거절한 이유 |

### Examples

### Request

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 1234,
    "params": {
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "to": "cx0000000000000000000000000000000000000001",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "call",
        "data": {
            "method": "rejectScore",
            "params": {
                "txHash": "0xb903239f8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238",
                "reason": "SCORE cannot use network api"
            }
        }
    }
}
```

## revokeAuditor

* SCORE 등록을 심사할 수 있는 권한을 가진 주소 목록에서 해당 주소를 제거한다.
* Auditor 주소의 키가 유출되는 경우 대비

### Paramters

없음

### Examples

#### Request

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 1234,
    "params": {
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "to": "cx0000000000000000000000000000000000000001",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "call",
        "data": {
            "method": "revokeAuditor"
        }
    }
}
```
