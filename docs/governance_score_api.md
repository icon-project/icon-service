Governance SCORE API
====================

Describes APIs that Governance SCORE provides.

| Date | Author | Changes |
|:---- |:-----: |:--------|
| 2018.07.16 | Yongwoo Lee | Added getStepCosts, setStepCost, StepCostChanged |
| 2018.07.13 | Jaechang Namgoong | Added setStepPrice, StepPriceChanged |
| 2018.07.09 | Jaechang Namgoong | Added getStepPrice |
| 2018.07.03 | Jaechang Namgoong | Added Eventlog (Accepted, Rejected) |
| 2018.06.22 | Chiwon Cho | Added AddAuditor, RemoveAuditor |
| 2018.06.21 | Chiwon Cho | Initial version |

# Value Type

기본적으로 모든 JSON-RPC 메시지 내의 VALUE는 문자열 형식으로 되어 있다.
많이 사용하는 "VALUE 형식"은 다음과 같다.

| Value Type | Description | Example |
|:---------- |:------------|:--------|
| <a id="T_ADDR_EOA">T_ADDR_EOA</a> | "hx" + 40 digit HEX 문자열 | hxbe258ceb872e08851f1f59694dac2558708ece11 |
| <a id="T_ADDR_SCORE">T_ADDR_SCORE</a> | "cx" + 40 digit HEX 문자열 | cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32 |
| <a id="T_HASH">T_HASH</a> | "0x" + 64 digit HEX 문자열 | 0xc71303ef8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238 |
| <a id="T_INT">T_INT</a> | "0x" + lowercase HEX 문자열 | 0xa |
| <a id="T_BIN_DATA">T_BIN_DATA</a> | "0x" + lowercase HEX 문자열<br>문자열의 길이가 짝수여야 한다 | 0x34b2 |
| <a id="T_SIG">T_SIG</a> | base64 encoded 문자열 | VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA= |

# Overview

* 블록 체인 망을 운영하는데 필요한 각종 항목을 관리하는 Built-in SCORE를 의미한다.
* 주소: cx0000000000000000000000000000000000000001

# Methods List

* Query methods
    * [getScoreStatus](#getscorestatus)
    * [getStepPrice](#getstepprice)
    * [getStepCosts](#getstepcosts)
* Invoke methods
    * [acceptScore](#acceptscore)
    * [rejectScore](#rejectscore)
    * [addAuditor](#addauditor)
    * [removeAuditor](#removeauditor)
    * [setStepPrice](#setstepprice)
    * [setStepCost](#setstepcost)
* Eventlog
    * [Accepted](#accepted)
    * [Rejected](#rejected)
    * [StepPriceChanged](#steppricechanged)
    * [StepCostChanged](#stepcostchanged)


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
    "id": 1234,
    "method": "icx_call",
    "params": {
        "from": "hxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32", // optional
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
    "id": 1234,
    "result": {
        "next": {
            "status": "pending",
            "deployTxHash": "0xe0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b27"
        }
    }
}
```

```json
// Response - 심사 완료: accepted
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": {
        "current": {
            "status": "active",
            "deployTxHash": "0xe0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b27",
            "auditTxHash": "0x644dd57fbb65b49a49bcaf5e7685e01d53dc321f1cfb7dbbf8f4306265745292"
        }
    }
}
```

```json
// Response - 심사 완료: rejected
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": {
        "next": {
            "status": "rejected",
            "deployTxHash": "0xe0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b27",
            "auditTxHash": "0x644dd57fbb65b49a49bcaf5e7685e01d53dc321f1cfb7dbbf8f4306265745292"
        }
    }
}
```

#### Response: SCORE update case

```json
// Response - update 요청, 심사 중
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": {
        "current": {
            "status": "active", // or "inactive"
            "deployTxHash": "0xe0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b207",
            "auditTxHash": "0x644dd57fbb65b49a49bcaf5e7685e01d53dc321f1cfb7dbbf8f4306265745292"
        },
        "next": {
            "status": "pending",
            "deployTxHash": "0xe0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b207"
        }
    }
}
```

```json
// Response - update 요청, 심사 완료: rejected
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": {
        "current": {
            "status": "active", // or "inactive"
            "deployTxHash": "0xe0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b27",
            "auditTxHash": "0x644dd57fbb65b49a49bcaf5e7685e01d53dc321f1cfb7dbbf8f4306265745292"
        },
        "next": {
            "status": "rejected",
            "deployTxHash": "0xe0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b27",
            "auditTxHash": "0x644dd57fbb65b49a49bcaf5e7685e01d53dc321f1cfb7dbbf8f4306265745292"
        }
    }
}
```

#### Response: error case

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "error": {
        "code": -32062,
        "message": "SCORE not found"
    }
}
```

## getStepPrice

* Returns the current step price in loop.

### Parameters

None

### Returns

`T_INT` - integer of the current step price in loop (1 ICX == 10^18 loop).

### Examples

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "method": "icx_call",
    "params": {
        "from": "hxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32", // optional
        "to": "cx0000000000000000000000000000000000000001",
        "dataType": "call",
        "data": {
            "method": "getStepPrice",
            "params": {}
        }
    }
}
```

#### Response

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": "0xe8d4a51000" // 1000000000000
}
```

## getStepCosts

* Returns a table of the step costs for the specific action in SOCRE

### Parameters

None

### Returns

`T_DICT` - a dict:  keys - camel-cased action strings, values - step costs in integer

### Examples

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "method": "icx_call",
    "params": {
        "from": "hxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32", // optional
        "to": "cx0000000000000000000000000000000000000001",
        "dataType": "call",
        "data": {
            "method": "getStepCosts",
            "params": {}
        }
    }
}
```

#### Response

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": {
        "default": "0xfa0",
        "contractCall": "0x5dc",
        "contractCreate": "0x4e20",
        "contractUpdate": "0x1f40",
        "contractDestruct": "-0x1b58",
        "contractSet": "0x3e8",
        "set": "0x14",
        "replace": "0x5",
        "delete": "-0xf",
        "input": "0x14",
        "eventLog": "0xa"
    }
}
```


# Invoke Methods

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
    "id": 1234,
    "method": "icx_sendTransaction",
    "params": {
        "version": "0x3",
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

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "method": "icx_sendTransaction",
    "params": {
        "version": "0x3",
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

## addAuditor

* SCORE 등록 심사 권한을 가진 주소 목록에 새로운 주소를 추가한다.
* 해당 목록에 등록된 주소만이 acceptScore와 rejectScore를 호출할 수 있다.
* SCORE Owner만 호출할 수 있다.

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:-----------|-----|
| address | [T_ADDR_EOA](#T_ADDR_EOA) | SCORE 등록 심사 권한을 가진 주소 목록에 추가한 새로운 EOA 주소 |

### Examples

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "method": "icx_sendTransaction",
    "params": {
        "version": "0x3",
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11", // owner address
        "to": "cx0000000000000000000000000000000000000001",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "call",
        "data": {
            "method": "addAuditor",
            "params": {
                "address": "hx2d54d5ca2a1dffbcfc3fb2c86cc07cb826f6b931"
            }
        }
    }
}
```

## removeAuditor

* SCORE 등록 심사 권한을 가진 주소 목록에서 기존 주소를 제거한다.
* 해당 목록에서 제거된 주소는 더이상 SCORE 등록 심사를 할 수 없다.
* SCORE Owner 혹은 목록에 있는 Auditor 본인이 자신을 제거할 수 있다.

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:-----------|-----|
| address | [T_ADDR_EOA](#T_ADDR_EOA) | SCORE 등록 심사 권한을 가진 주소 목록에 있는 EOA 주소 |

### Examples

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "method": "icx_sendTransaction",
    "params": {
        "version": "0x3",
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11", // owner address
        "to": "cx0000000000000000000000000000000000000001",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "call",
        "data": {
            "method": "removeAuditor",
            "params": {
                "address": "hx2d54d5ca2a1dffbcfc3fb2c86cc07cb826f6b931"
            }
        }
    }
}
```

## setStepPrice

* Sets the current step price in loop.
* Only the owner can call this function.

### Parameters

| Key | Value Type | Description |
|:----|:-----------|-----|
| stepPrice | [T_INT](#T_INT) | step price in loop (1 ICX == 10^18 loop) |

### Examples

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "method": "icx_sendTransaction",
    "params": {
        "version": "0x3",
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11", // owner address
        "to": "cx0000000000000000000000000000000000000001",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "call",
        "data": {
            "method": "setStepPrice",
            "params": {
                "stepPrice": "0xe8d4a51000" // 1000000000000
            }
        }
    }
}
```

## setStepCost

* Sets the step costs for the specific action in SOCRE.
* Only the owner can call this function.

### Parameters

| Key | Value Type | Description |
|:----|:-----------|-----|
| stepType | [T_STRING](#T_STRING) | action type |
| cost | [T_INT](#T_INT) | step cost for the type |

### Examples

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "method": "icx_sendTransaction",
    "params": {
        "version": "0x3",
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11", // owner address
        "to": "cx0000000000000000000000000000000000000001",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "call",
        "data": {
            "method": "setStepCost",
            "params": {
                "stepType": "contractDestruct",
                "cost": "-0x1b58" // -7000
            }
        }
    }
}
```

# Eventlog

## Accepted

Must trigger on any successful acceptScore transaction.

```python
@eventlog(indexed=1)
def Accepted(self, tx_hash: str):
    pass
```

## Rejected

Must trigger on any successful rejectScore transaction.

```python
@eventlog(indexed=1)
def Rejected(self, tx_hash: str):
    pass
```

## StepPriceChanged

Must trigger on any successful setStepPrice transaction.

```python
@eventlog(indexed=1)
def StepPriceChanged(self, step_price: int):
    pass
```

## StepCostChanged

Must trigger on any successful setStepCost transaction.

```python
@eventlog(indexed=1)
def StepPriceChanged(self, step_type: str, cost: int):
    pass
```
