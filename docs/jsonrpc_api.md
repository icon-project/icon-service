# IconScore 개발 도구 (tbears)용 JSONRPC API

* IconServiceEngine과 관련된 jsonrpc api를 설명한다.
* [jsonrpc 2.0 표준안](http://www.jsonrpc.org/specification)을 따른다.

## 공통 항목

* JSONRPC API에서 공통적으로 사용되는 항목들을 설명한다.

### 항목별 설명

* from
    - 메시지를 보내는 주체의 주소
    - 데이터 형식: 주소
* to
    - 코인을 받은 주소
    - transaction에 포함된 메시지콜 데이터를 처리할 Score 주소
    - 데이터 형식: 주소
* value
    - 이체할 코인 수
    - 단위: loop (1 icx == 10^18 loop)
    - 데이터 형식: 정수를 나타내는 16진수 문자열
* step
    - transaction을 처리하기 위한 최대 step 수
    - transac
    - Ethereum의 gas와 동일
* timestamp
    - 단위: microsecond
    - 데이터 형식: 정수
* nonce
    - transaction hash를 생성하는데 사용되는 임의의 정수
    - 데이터 형식: 정수
    - Optional
* signature
    - transaction 전자 서명 데이터
    - 데이터 형식: 전자 서명
* data_type
    - data 항목에 들어가는 내용의 종류를 명시
    - 데이터 형식: 문자열
    - 종류
        - install: Score 설치
        - update: 기존 Score 업데이트
        - call: Score에서 제공하는 함수 호출
* data
    - data_type의 값에 따라 다른 내용을 포함한다.
    - icx_sendTransaction 설명 참고

### 데이터 표현 형식

기본적으로 모든 jsonrpc 메시지 내의 값들은 문자열 형식으로 되어 있다.

* 주소
    - EOA: 'hx' + 40 digit hex string
    - Score: 'cx' + 40 digit hex string
* 정수
    - Format: 0x + lowercase hex string
* 이진 데이터
    - 0x + lowercase hex string
    - hexa string의 길이가 짝수여야 한다.
* signature
    - base64

## icx_call

* Score 내의 External 함수를 호출한다.
* to 주소가 가리키는 Score의 함수를 호출한다.
* 상태 전이 없음, 단순 조회 기능

### Request

```json
{
    "jsonrpc": "2.0",
    "method": "icx_call",
    "id": 1234,
    "params": {
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11", // 메시지 송신자 주소
        "to": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32",   // Score Address
        "data_type": "call", // 메시지콜
        "data": {            // 메시지콜 데이터
            "method": "get_balance", // 토큰 잔고 조회
            "params": {
                "address": "hx1f9a3310f60a03934b917509c86442db703cbd52" // 토큰 잔고를 조회할 계좌 주소
            }
        }
    }
}
```

### Response

#### 성공

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": "0x2961fff8ca4a62327800000"
}
```

#### 실패

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "error": {
        "code": -32601,
        "message": "Method not found"
    }
}
```

```json
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

* 지정된 계좌 주소의 코인 수를 조회한다.
* 상태 전이는 발생하지 않는다.

### Request

#### 성공

```json
{
    "jsonrpc": "2.0",
    "method": "icx_getBalance",
    "id": 10,
    "params": {
        "address": "hxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32"
    }
} 
```

#### 실패

```json
{
    "jsonrpc": "2.0",
    "id": 10,
    "error": {
        "code": -32602,
        "message": "Invalid address"
    }
}
```

### Response

```json
{
    "jsonrpc": "2.0",
    "id": 10,
    "result": "0xde0b6b3a7640000"
}
```

## icx_getTotalSupply

* 현재 발급된 코인의 총 수를 조회한다.
* 상태 전이는 발생하지 않는다.

### Request

```json
{
    "jsonrpc": "2.0",
    "method": "icx_getTotalSupply",
    "id": 0
}
```

### Response

```json
{
    "jsonrpc": "2.0",
    "id": 1234,
    "result": "0x2961fff8ca4a62327800000"
}
```

## icx_getTransactionResult

* tx_hash로 transaction 처리 결과를 조회한다.

### Request

```json
{
    "jsonrpc": "2.0",
    "method": "icx_getTransactionResult",
    "id": 578,
    "params": {
        "tx_hash": "0xb903239f8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238"
    }
}
```

### Response

```json
{
    "jsonrpc": "2.0",
    "id": 578,
    "result": {
        "status": "0x1",
        "tx_hash": "0xb903239f8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238",
        "tx_index": "0x1",
        "block_height": "0x1234",
        "block_hash": "0xc71303ef8543d04b5dc1ba6579132b143087c68db1b2168786408fcbce568238",
        "cumulative_step_used": "0x1234",
        "step_used": "0x1234",
        "contract_address": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32"
    }
}
```

## icx_sendTransaction

* from 주소에서 to 주소로 지정된 금액의 코인을 이체한다.
* to 주소가 가리키는 Score의 함수를 호출한다.
* 상태 전이가 발생한다.

### Request

```json
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 9876,
    "params": {
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "step": "0x12345",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "data_type": "install",
        "data": {
            "content_type": "application/zip", // content 내용에 대한 mime-type
            "content": "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e..." // IconScore 압축 데이터
        }
    }
}
```

```json
{
    "jsonrpc": "2.0", // jsonrpc 버전
    "method": "icx_sendTransaction", // jsonrpc 메소드명
    "id": 9876, // jsonrpc message id
    "params": {
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11", // transaction 생성 주체의 주소
        "to": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32", // transaction의 메시지콜을 처리할 Score 주소
        "step": "0x12345", // Ethereum의 gas 개념
        "timestamp": "0x563a6cf330136", // transaction 생성 시간. 단위: microsecond
        "nonce": "0x1", // 임의의 정수
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "data_type": "update", // Score 업데이트
        "data": {
            "content_type": "application/zip", // content의 mime-type
            "content": "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e..." // IconScore 압축 데이터
        }
    }
}
```

```json
{
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "id": 9876,
    "params": {
        "from": "hxbe258ceb872e08851f1f59694dac2558708ece11",
        "to": "cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32",
        "value": "0xde0b6b3a7640000",
        "timestamp": "0x563a6cf330136",
        "nonce": "0x1",
        "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
        "data_type": "call",
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

### Response

#### 성공

```json
{
    "jsonrpc": "2.0",
    "id": 9876,
    "result": "0x4bf74e6aeeb43bde5dc8d5b62537a33ac8eb7605ebbdb51b015c1881b45b3aed"
}
```

#### 실패

```json
{
    "jsonrpc": "2.0",
    "id": 9876,
    "error": {
        "code": -32600,
        "message": "Invalid signature"
    }
}
```

```json
{
    "jsonrpc": "2.0",
    "id": 9876,
    "error": {
        "code": -32601,
        "message": "Method not found"
    }
}
```

## 참고 자료

* [jsonrpc specification](http://www.jsonrpc.org/specification)
* [Ethereum JSON RPC API](https://github.com/ethereum/wiki/wiki/JSON-RPC)
* [Icon JSON RPC API](https://github.com/icon-project/icx_JSON_RPC)