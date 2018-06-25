0 Overview
============
`icx_getTransactionResult` JSON RPC 스펙을 다음의 요구 사항들이 충족되도록 수정한다.

* 실패한 transaction에 대한 정보를 돌려주어야 한다.
* 이전 transaction에서 contract deploy가 일어났다면, 생성된 contract address 정보
* Score 실행 중에 소모된 step(gas) 값
* transaction 실행 중에 생성된 logs
* ...

1 기존 스펙
===========
### Params
* `tx_hash`: hash string from the result of `icx_sendTransaction`

##### Example of request
```json
{
    "jsonrpc" : "2.0",
    "method": "icx_getTransactionResult",
    "id": 2,
    "params": {
        "tx_hash": "e670ec64341771606e55d6b4ca35a1a6b75ee3d5145a99d05921026d1527331"
    }
}
```

### Response
* `response_code`: JSON RPC error code.
* `response`: Code or message. See the following explanation for code.

```python
    SUCCESS = 0
    EXCEPTION = 90
    NOT_INVOKED = 2 # means pending
    NOT_EXIST = 3 # possibly means failure
    SCORE_CONTAINER_EXCEPTION = 9100
```

##### Example of response
```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "response_code": 0,
        "response": {
            "code": 0
        }
    }
}
```

2 [참고] 이더리움 `eth_getTransactionReceipt`
============================================
* https://github.com/ethereum/wiki/wiki/JSON-RPC#eth_gettransactionreceipt
* 다음과 같은 정보를 response로 알려준다.
    * `transactionHash`: DATA, 32 Bytes - hash of the transaction.
    * `transactionIndex`: QUANTITY - integer of the transactions index position in the block.
    * `blockHash`: DATA, 32 Bytes - hash of the block where this transaction was in.
    * `blockNumber`: QUANTITY - block number where this transaction was in.
    * `cumulativeGasUsed`: QUANTITY - The total amount of gas used when this transaction was executed in the block.
    * `gasUsed`: QUANTITY - The amount of gas used by this specific transaction alone.
    * `contractAddress`: DATA, 20 Bytes - The contract address created, if the transaction was a contract creation, otherwise null.
    * `logs`: Array - Array of log objects, which this transaction generated.
    * `logsBloom`: DATA, 256 Bytes - Bloom filter for light clients to quickly retrieve related logs.
    * `status`: either 1 (success) or 0 (failure)


3 확장된 스펙 제안
=================
### Params
* Params는 이전과 동일 - `tx_hash`

### Response
#### On success
* `response`: 이전과 같은 포맷. 다만 실패한 transaction에 대해서 아래와 같이 명시적인 코드를 추가한다.
    * `FAILURE` = -1
* `blockNumber`: The block height number where this transaction was in.
* `contractAddress`: 'cx' + 40 digit hex string - The contract address created, if the transaction was a contract creation, otherwise null.
* `stepUsed`: The amount of step used by the transaction.

##### Example of response (on success)
```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "response": {
            "code": 0
        },
        "blockNumber": "0xb",
        "stepUsed": "0x4dc",
        "contractAddress": "cxb60e8dd61c5d32be8058bb8eb970870f07233155"
    }
}
```

##### Example of serialized results
```json
[{
    "txHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "blockHeight": 0,
    "to": "hx0000000000000000000000000000000000000000",
    "contractAddress": null,
    "stepUsed": 0,
    "status": 1
  }]
```

#### On error
* `code`: an error code
* `message`: a string providing a short description of the error


### Event Log
- 지원 하는 parameter type: 
  int, str, bytes, bool, Address
- indexed
  - 첫 item은 Event의 signature
  - 총 4개까지 지원
- data: parameter 제한 없음
   

예)
```json
{
    "eventLogs": [
        {
            "scoreAddress": "cxXXXXXXXXXXXXXXXXXXXX",
            "indexed": [
              "Transfer(Address,Address,int)", 
              "hxAAAAAAAAAAAAAAAAAAAA", 
              "hxBBBBBBBBBBBBBBBBBBBB" 
            ],
            "data": [
              "0x56bc75e2d63100000"
            ]
        },
        ...
    ]
}
```