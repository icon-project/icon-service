Event Log의 Indexing과 Bloom Filter
==

## Overview
Score에서 Event Log의 적용 방법 및 Indexing Rule, TransactionResult에 포함되는 형식, Bloom Filter의 Filter search 방법에 대한 기술이다



## SCORE에서 Event Log의 적용

- `@eventlog`의 데코레이터로 Event의 선언이 가능함

- 데코레이터의 `indexed` 값 설정으로 인덱싱 하는 매개변수의 수(max=3)를 정한다

- 매개변수는 type hint를 꼭 명시하여야 한다

- 매개변수로 지원하는 자료형은 다음과 같다
  > `bool`, `int`, `str`, `bytes`, `Address`

- 선언된 매개변수 타입과 맞지 않는 매개변수 값으로 이벤트를 호출할 경우 type mismatch 에러를 발생
  > e.g. None 셋팅

예)

```python
@eventlog(indexed=2)
def Transfer(self, from_: Address, to_: Address, amount: int):
    pass
```



## Indexing

- Event의 Signature는 Indexing의 가장 첫 item이다  (`함수명(매개변수타입,...)`) 
  예) `Transfer(Address,Address,int)`
- `@eventlog`의 데코레이터의 `indexed`에 설정된 수(max=3) 만큼 매개변수가(선언된 순서 순) 인덱싱이 된다.
- 인덱싱에는 변수의 선언된 순서를 포함한다. 같은 값에 선언된 위치가 다르면 인덱싱 값도 다르다.
- 인덱싱 매개 변수는 EventLog의 indexed 필드에 array 형태로 저장이 된다



### Indexing Rule (Bloom filter hash function)

- `raw-data` = `매개변수순서(1byte)` + `data`

  -  bool, int, bytes: 원 값의 bytes를 `data`로 사용
  -  Address: body의 20 bytes를 `data`로 사용
  -  str: utf-8 인코딩을 한 bytes를 `data`로 사용
  -  None: `data`를 추가하지 않고 `매개변수순서(1byte)`로 `hash-data`를 만든다

- `hash-data` = sha3-256(`raw-data`)

- `chunk[0]` = `hash-data[0:2]` & 2047

- `chunk[1]` = `hash-data[2:4]` & 2047 

- `chunk[2]` = `hash-data[4:6]` & 2047

- bloom-data(2048bits) = setAt(`chunk[0]`) | setAt(`chunk[1]`) | setAt(`chunk[2]`) 



## Transaction Result에 포함되는 형식

한 Transaction 안에 다수의 Event log가 포함될 수 있어 Transaction Result에서는 Array형식으로 포함 된다

### Event log의 Fields
| KEY          | VALUE 형식                    | 설명                                                         |
| :----------- | :---------------------------- | :----------------------------------------------------------- |
| scoreAddress | [T_ADDR_SCORE](#T_ADDR_SCORE) | 해당 이벤트가 발생한  SCORE의 주소                           |
| indexed      | [T_ARRAY](#T_ARRAY)           | Event log의 인덱싱 데이터(Max length = 4)<br />- 첫번째 아이템에는 이벤트의 signatue가 저장된다 (필수)<br />- 두번때 아이템부터는 Indexed params가 저장된다.(SCORE에 선언된 type에 따름) |
| data         | [T_ARRAY](#T_ARRAY)           | Event log의 파라메터 저장 (SCORE에 선언된 type에 따름)       |

예)
다음과 같이 선언된 Event를 emit한 경우

```python
@eventlog(indexed=2)
def Transfer(self, from_: Address, to_: Address, amount: int):
    pass

...


self.Transfer(
    'hx4873b94352c8c1f3b2f09aaeccea31ce9e90bd31', 
    'hx0000000000000000000000000000000000000000', 
    10000000000000000000)
```

다음과 같은 결과를 볼 수 있다

```json
{
   "txHash":"2457e1b3275546b2101ded58e09e565e1cac45dc93c858a7c39a60f91b51d847",
   "blockHeight":"0x3",
   "txIndex":"0x0",
   "to":"cx0cb2bf4d130b28daebd9c058b28b9b4353bac523",
   "stepUsed":"0x203a",
   "eventLogs":[
      {
         "scoreAddress":"cx0cb2bf4d130b28daebd9c058b28b9b4353bac523",
         "indexed":[
             "Transfer(Address,Address,int)",
             "hx4873b94352c8c1f3b2f09aaeccea31ce9e90bd31",
             "hx0000000000000000000000000000000000000000",
          ],
         "data":[
            "0x8ac7230489e80000"
         ]
      }
   ],
   "logsBloom":"0x00000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000003000000000020400000000000000000000000000000000000000000000000000000000000001400000000000000000000000000000000000000000000000000000000000000220000000000000",
   "status":"0x1"
}
```

|  | indexed |   data  |
| :------ | :--- | :--- |
| 0 | **signature**: Transfer(Address,Address,int) | **amount**: 0x8ac7230489e80000 |
| 1 | **from_**: hx4873b94352c8c1f3b2f09aaeccea31ce9e90bd31 |      |
| 2 | **t_**: hx0000000000000000000000000000000000000000 |      |



## Bloom 
- 256 bytes의 raw bytes

- Event log들의 Indexing 결과의 bloom-data들을 `OR` 연산 

  


### Filter Search
- 검색하려는 이벤트 값을  [Indexing Rule](#indexing) 에 따라 bloom-data를 생성

- Bloom 값에 포함되는지 판단<br />
  예) <br />
  검색하려는 이벤트의 bloom-data = 0x10101010 , logsBloom = 0x30303030 

  then, 0x10101010 ⊂ 0x30303030
  


  - 포함: 해당하는 조건에 충족될 확률이 높음 -> 실제 Data 확인
  - 포함하지 않음: 해당하는 조건에 충족되지 않음


