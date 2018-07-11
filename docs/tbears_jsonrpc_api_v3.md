ICON SCORE 개발 도구(tbears) 용 JSON-RPC API v3
=========================================

IconServiceEngine과 관련된 JSON-RPC API를 설명한다.

| 일시 | 작성자 | 비고 |
|:-----|:-----:|:----|
| 2018.07.11 | 이용우 | icx_getTransactionResult에 to, eventLogs, logsBloom 속성 추가 |
| 2018.06.29 | 박지윤 | 일부 API 오류 수정 |
| 2018.06.12 | 조치원 | 일부 표 오류 수정 |
| 2018.06.08 | 조치원 | 에러 코드표 추가, icx_getTransactionResult 내용 수정 |
| 2018.05.18 | 조치원 | JSON-RPC API v3 ChangeLog 추가 |
| 2018.05.17 | 박은수 | API 작성 규칙 추가, 문서 고도화 |
| 2018.05.15 | 조치원 | 최초 작성 |

# API 작성 규칙
* [JSON-RPC 2.0 표준안](http://www.jsonrpc.org/specification)을 따른다.

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "$STRING1",
    "id": $INT,
    "params": {
        "$KEY1": "$VALUE1",
        "$KEY2": {
            "method": "$STRING2",
            "params": {
                "$KEY3": "$VALUE3"
            }
        }
    }
}

// Response - 성공
{
    "jsonrpc": "2.0",
    "id": $INT,
    "result": "$STRING"
    // or
    "result": {
      "$KEY1": "$VALUE1",
      "$KEY2": "$VALUE2"
    }
}

// Response - 실패
{
    "jsonrpc": "2.0",
    "id": $INT1,
    "error": {
        "code": $INT2,
        "message": "$STRING"
    }
}
```
* "KEY"의 작명은 camel case를 따른다.

# VALUE 형식

기본적으로 모든 JSON-RPC 메시지 내의 VALUE는 문자열 형식으로 되어 있다.<br/>
많이 사용하는 "VALUE 형식"은 다음과 같다.

| VALUE 형식 | 설명 | 예 |
|:----------|:----|:----|
| <a id="T_ADDR_EOA">T_ADDR_EOA</a> | "hx" + 40 digit HEX 문자열 | hxbe258ceb872e08851f1f59694dac2558708ece11 |
| <a id="T_ADDR_SCORE">T_ADDR_SCORE</a> | "cx" + 40 digit HEX 문자열 | cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32 |
| <a id="T_HASH">T_HASH</a> | "0x" + 64 digit HEX 문자열 | 0xc71303ef8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238 |
| <a id="T_INT">T_INT</a> | "0x" + lowercase HEX 문자열 | 0xa |
| <a id="T_BIN_DATA">T_BIN_DATA</a> | "0x" + lowercase HEX 문자열<br>문자열의 길이가 짝수여야 한다 | 0x34b2 |
| <a id="T_SIG">T_SIG</a> | base64 encoded 문자열 | VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA= |
| <a id="T_DATA_TYPE">T_DATA_TYPE</a> | call: SCORE에서 제공하는 함수 호출<br/>deploy: SCORE 설치 및 업데이트 | - |

# JSON-RPC 에러 코드

ICON JSON-RPC API Response에서 사용되는 기본적인 에러 코드 및 설명.<br/>
아래 표의 메시지는 에러 코드에 대응하는 기본 메시지이며 구현에 따라 다른 메시지가 사용될 수 있다.

## 에러 코드표

| 에러 코드 | 메시지 | 설명 |
|:---------|:------|:-----|
| -32700 | Parse error | Invalid JSON was received by the server. An error occurred on the server while parsing the JSON text. |
| -32600 | Invalid Request | The JSON sent is not a valid Request object. |
| -32601 | Method not found | The method does not exist / is not available. |
| -32602 | Invalid params | Invalid method parameter(s). |
| -32603 | Internal error | Internal JSON-RPC error. |
| -32000 | Server error | IconServiceEngine 내부에서 발생하는 오류 |
| -32100 | Score error | Score 내부에서 발생하는 오류 |

## JSON-RPC Error Response
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32601,
        "message": "Method not found (transfer)"
    }
}
```

# JSON-RPC API v3 ChangeLog

* JSON-RPC 2.0 표준에 맞지 않는 부분 수정
    * 성공 response: result
    * 실패 response: error
* SCORE의 JSON-PRC Response 생성 시 loopchain에서 response_code 등의 부가적인 항목을 추가하지 않도록 한다.
    * v2: "result": {"response_code": "0x0", "response": "0x12345"}
    * v3: "result": "0x12345"
* v2 API에서 일부 동일한 의미의 key 명이 다르게 표현되는 부분 수정
    * v2: icx_getBlockByHeight: "time_stamp"
    * v2: icx_sendTransaction: "timestamp"
    * v3: "timestamp"
* v2 API에서 일부 VALUE 형식 일관성이 맞지 않는 부분 수정
    * timestamp
        * v2: icx_sendTransaction: "timestamp": "1234567890"
        * v2: icx_getBlockByHeight: "timestamp": 1234567890
        * v3: "timestamp": "0x499602d2"
    * hash
        * v2: icx_getBlockByHash: "hash": "af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc"
        * v3: "hash": "0xaf5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc"
* key 작명 시 camel case 방식을 따른다.
    * v2: "data_type"
    * v3: "dataType"
* icx_sendTransaction 메시지에서 tx_hash 항목을 삭제한다.

# JSON-RPC Methods

* [icx_call](#icx_call)
* [icx_getBalance](#icx_getbalance)
* [icx_getScoreApi](#icx_getscoreapi)
* [icx_getTotalSupply](#icx_gettotalsupply)
* [icx_getTransactionResult](#icx_gettransactionresult)
* [icx_sendTransaction](#icx_sendtransaction)

## icx_call

* SCORE 내의 External 함수를 호출한다.
* 상태 전이는 발생하지 않는다. 단순 조회 기능

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:-----------|:-----|
|from|[T_ADDR_EOA](#T_ADDR_EOA)|메시지를 보내는 주체의 주소|
|to|[T_ADDR_SCORE](#T_ADDR_SCORE)|transaction에 포함된 메시지콜 데이터를 처리할 SCORE 주소|
|dataType|[T_DATA_TYPE](#T_DATA_TYPE)|data 종류 명시. "call"만 가능|
|data| - |SCORE 구현에 따른 함수명 및 함수 Parameter|
|data.method | 문자열 | 해당 SCORE 내의 함수 |
|data.params | T_DICT | SCORE 함수로 전달되는 파라미터 값 |

### Returns

SCORE 함수 실행 결과

### Example

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_call",
    "id": 1234,
    "params": {
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11", // TX 송신자 주소
        "to": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32",   // SCORE 주소
        "dataType": "call", // 메시지콜
        "data": {           // 메시지콜 데이터
            "method": "get_balance", // SCORE External 함수
            "params": {
                "address": "hx1f9a3310f60a03934b917509c86442db703cbd52" // "get_balance" 함수의 파라미터
            }
        }
    }
}

// Response - 성공
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": "0x2961fff8ca4a62327800000"
}

// Response - 실패1
{
    "jsonrpc": "2.0",
    "id": 1234,
    "error": {
        "code": -32601,
        "message": "Method not found"
    }
}

// Response - 실패2
{
    "jsonrpc": "2.0",
    "id": 1234,
    "error": {
        "code": -32602,
        "message": "Invalid params"
    }
}
```

## icx_getBalance

* 지정된 계좌 주소 또는 SCORE의 코인 수를 조회한다.
* 상태 전이는 발생하지 않는다.

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:-----------|:-----|
| address | [T_ADDR_EOA](#T_ADDR_EOA) or [T_ADDR_SCORE](#T_ADDR_SCORE) | 조회할 주소 |

### Returns

코인 수

### Example

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_getBalance",
    "id": 1234,
    "params": {
        "address": "hxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32"
    }
}

// Response - 성공
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": "0xde0b6b3a7640000"
}

// Response - 실패
{
    "jsonrpc": "2.0",
    "id": 1234,
    "error": {
        "code": -32602,
        "message": "Invalid address"
    }
}
```

## icx_getScoreApi

* 스코어의 API 함수 (external, payable, fallback, on_install, on_update, eventlog) 정보(배열) 반환

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:-----------|:-----|
| address | [T_ADDR_SCORE](#T_ADDR_SCORE) | 조회할 SCORE 주소 |

### Returns

* 함수 정보에 대한 필드
    - type : function, fallback, on_install, on_update, eventlog
    - name : 함수 이름
    - inputs : 파라미터 정보(배열)
        + name : 파라미터 이름
        + type : 파라미터 타입 (int, str, bytes, bool, Address)
        + indexed : eventlog의 경우에 다음 정보가 표기
    - outputs : 리턴 값 정보
        + type : 리턴 값 타입 (int, str, bytes, bool, Address)
    - readonly : external(readonly=True)
    - payable : payable

### Example

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_getScoreApi",
    "id": 1234,
    "params": {
        "address": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32"  // SCORE 주소
    }
}

// Response - 성공
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": [...]
}

// Response - 실패
// icx_call 실패와 동일
```

## icx_getTotalSupply

* 현재 발급된 코인의 총 수를 조회한다.
* 상태 전이는 발생하지 않는다.

### Parameters
없음

### Returns
총 코인 수

### Example

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_getTotalSupply",
    "id": 1234
}

// Response - 성공
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": "0x2961fff8ca4a62327800000"
}
```

## icx_getTransactionResult

* txHash로 transaction 처리 결과를 조회한다.

### Parameters

| KEY | VALUE 형식 | 설명 |
|:----|:----------|:----- |
| txHash | [T_HASH](#T_HASH) | 조회할 TX hash |

### Returns

| KEY | VALUE 형식 | 설명 |
|:----|:----------|:-----|
| status | [T_INT](#T_INT) | 1 (success), 0 (failure) |
| to | [T_ADDR_EOA](#T_ADDR_EOA) or<br/> [T_ADDR_SCORE](#T_ADDR_SCORE) | transaction 의 수신 address |
| failure | T_DICT | status가 0(failure)인 경우에만 존재. code(str), message(str) 속성 포함 |
| txHash | [T_HASH](#T_HASH) | transaction hash |
| txIndex | [T_INT](#T_INT) | transaction index in a block |
| blockHeight | [T_INT](#T_INT) | transaction이 포함된 block의 height |
| blockHash | [T_HASH](#T_HASH) | transaction이 포함된 block의 hash |
| cumulativeStepUsed | [T_INT](#T_INT) | 블록 내에서 해당 transaction을 수행하기까지 소비된 step의 누적량 |
| stepUsed | [T_INT](#T_INT) | 해당 transaction을 수행하는데 소비된 step 양 |
| scoreAddress | [T_ADDR_SCORE](#T_ADDR_SCORE) | 해당 transaction이 SCORE을 생성했을 경우 해당 SCORE 주소 (optional) |
| eventLogs | [T_ARRAY](#T_ARRAY) | 해당 transaction의 실행 중에 발생한 EventLog의 목록 |
| logsBloom | [T_BIN_DATA](#T_BIN_DATA) | 발생한 EventLog의 Data중 인덱싱된 Data의 Bloom Filter 값 |

### Example

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_getTransactionResult",
    "id": 1234,
    "params": {
        "txHash": "0xb903239f8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238"
    }
}

// Response - 성공 한 tx에 대한 결과
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": {
        "status": "0x1",
        "to": "cx0000000000000000000000000000000000000000",
        "txHash": "0xb903239f8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238",
        "txIndex": "0x1",
        "blockHeight": "0x1234",
        "blockHash": "0xc71303ef8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238",
        "cumulativeStepUsed": "0x1234",
        "stepUsed": "0x1234",
        "stepPrice": "0x5678",
        "scoreAddress": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32",
        "eventLogs":[
            {
                "scoreAddress":"cx4d6f646441a3f9c9b91019c9b98e3c342cceb114",
                "indexed":[
                    "Transfer(Address,Address,int)",
                    "hx4873b94352c8c1f3b2f09aaeccea31ce9e90bd31",
                    "hx0000000000000000000000000000000000000000",
                    "0x8ac7230489e80000"
                ],
                "data":[]
            }
        ],
        "logsBloom":"0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000002000000000021000000000000000000000000000000000000000000000000003000000000031400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000"
    }
}

// Response - 실패 한 tx에 대한 결과
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": {
        "status": "0x0",
        "failure": {
            "code": "0x7d00",
            "message": "Out of balance"
        },
        "to": "hx5bfdb090f43a808005ffc27c25b213145e80b7cd",
        "txHash": "0xb903239f8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238",
        "txIndex": "0x1",
        "blockHeight": "0x1234",
        "blockHash": "0xc71303ef8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238",
        "cumulativeStepUsed": "0x1234",
        "stepUsed": "0x1234",
        "stepPrice": "0x5678"
    }
}

// Response - 실패 (잘못된 txHash에 대한 요청)
{
    "jsonrpc": "2.0",
    "id": 1234,
    "error": {
        "code": -32602,
        "message": "Invalid txHash"
    }
}
```

## icx_sendTransaction

* from 주소에서 to 주소로 지정된 금액의 코인을 이체한다.
* 새로운 SCORE를 install한다.
* to 주소가 가리키는 SCORE를 update 한다.
* to 주소가 가리키는 SCORE의 함수를 호출한다.
* 상태 전이가 발생한다.

### Parameters

| KEY | VALUE 형식 | 속성 | 설명 |
|:----|:----------|:----:|:-----|
| version | [T_INT](#T_INT) | required | 프로토콜 버전 ("0x3" for V3) |
| from | [T_ADDR_EOA](#T_ADDR_EOA) | required | transaction을 생성한 주체의 주소 |
| to | [T_ADDR_EOA](#T_ADDR_EOA) or<br/> [T_ADDR_SCORE](#T_ADDR_SCORE) | optional | 코인을 받거나 EOA 주소 혹은 transaction을 수행할 SCORE 주소 |
| value | [T_INT](#T_INT) | optional | to 주소로 이체할 ICX 코인양, 생략할 경우 0으로 간주 |
| stepLimit |[T_INT](#T_INT) | required | transaction을 수행하는데 소비되는 최대 step 허용치 |
| timestamp | [T_INT](#T_INT) | required | transaction을 전송할 때의 timestamp (단위: microsecond) |
| nonce | [T_INT](#T_INT) | optional | transaction hash 출동 방지를 위한 임의의 정수 |
| signature | [T_SIG](#T_SIG) | required | transaction의 전자 서명 데이터 |
| dataType | [T_DATA_TYPE](#T_DATA_TYPE) | optional | data 항목의 종류를 알려주는 값 (call, deploy) |
| data | N/A | optional | transaction의 목적에 따라 다양한 형식의 데이터가 포함됨 |
| data.method | 문자열 | optional | 해당 SCORE 내의 함수 (call) |
| data.contentType | 문자열 | optional | content의 mime-type (deploy) |
| data.content | [T_BIN_DATA](#T_BIN_DATA) | optional | 이진 데이터 (deploy) |
| data.params | T_DICT | optional | SCORE 함수로 전달되는 파라미터 값 |

### Returns

* 성공: transaction hash ([T_HASH](#T_HASH))
* 실패: 오류 코드 및 오류 메시지

### Example

* 단순 코인 이체

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 1234,
    "params": {
        "version": "0x3",
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "to": "hx5bfdb090f43a808005ffc27c25b213145e80b7cd",
        "value": "0xde0b6b3a7640000",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="
    }
}
```

* SCORE 함수 호출

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 1234,
    "params": {
        "version": "0x3",
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "to": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32",
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "call",
        "data": {
            "method": "transfer",
            "params": {
                "to": "hxab2d8215eab14bc6bdd8bfb2c8151257032ecd8b",
                "value": "0x1"
            }
        }
    }
}
```

* SCORE 설치

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 1234,
    "params": {
        "version": "0x3",
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "to": "cx0000000000000000000000000000000000000000", // SCORE 주소가 0이면 SCORE install 의미
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "deploy",
        "data": {
            "contentType": "application/zip",
            "content": "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e...", // SCORE 압축 데이터
            "params": {  // on_install() 함수로 전달되는 파라미터
                "name": "ABCToken",
                "symbol": "abc",
                "decimals": "0x12"
            }
        }
    }
}
```

* SCORE 업데이트

```json
// Request
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 1234,
    "params": {
        "version": "0x3",
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "to": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32", // 업데이트할 SCORE 주소
        "stepLimit": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "dataType": "deploy",
        "data": {
            "contentType": "application/zip",
            "content": "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e...", // SCORE 압축 데이터
            "params": {  // on_update() 함수로 전달되는 파라미터
                "amount": "0x1234"
            }
        }
    }
}
```

* Response

```json
// Response - 성공
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": "0x4bf74e6aeeb43bde5dc8d5b62537a33ac8eb7605ebbdb51b015c1881b45b3aed" // transaction hash
}

// Response - 실패
{
    "jsonrpc": "2.0",
    "id": 1234,
    "error": {
        "code": -32600,
        "message": "Invalid signature"
    }
}

// Response - 실패
{
    "jsonrpc": "2.0",
    "id": 1234,
    "error": {
        "code": -32601,
        "message": "Method not found"
    }
}
```

## 참고 자료

* [jsonrpc specification](http://www.jsonrpc.org/specification)
* [Ethereum JSON RPC API](https://github.com/ethereum/wiki/wiki/JSON-RPC)
* [ICON JSON RPC API v2](https://github.com/icon-project/icx_JSON_RPC)
