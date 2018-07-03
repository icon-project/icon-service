Event Log 의 Indexing과 Bloom Filter
==

## 문서 이력

| 일시 | 버전 | 작성자 | 비고 |
|:-----|:----|:-----:|:-----|
| 2018.07.02 | 0.0.1 | 이용우 | 신규 |
| 2018.07.03 | 0.0.2 | 이용우 | indexed 필드, str타입 indexing rule |

## Overview
Event Log의 적용, Indexing Rule, Bloom Filter의 Filter search 방법에 대한 기술이다

## Event Log 적용

- `@eventlog`의 데코레이터로 Event의 선언이 가능함

- 데코레이터의 `indexed` 값 설정으로 인덱싱 하는 매개변수의 수를 정한다

- 매개변수는 type hint를 꼭 명시하여야 한다

- 매개변수로 지원하는 자료형은 다음과 같다
  > `bool`, `int`, `str`, `bytes`, `Address`

- 선언된 매개변수 타입과 맞지 않는 매개변수 값으로 이벤트를 호출할 경우 type mismatch 에러를 발생
  > e.g. None 셋팅

예)

```python
@eventlog(indexed=2)
def Transfer(self, from_: Address, to_: Address, amout: int):
  pass
```


## Indexing

- Event의 Signature는 Indexing의 가장 첫 item이다  (`함수명(매개변수타입,...)`) 
  예) `Transfer(Address,Address,int)`
- `@eventlog`의 데코레이터의 `indexed`에 설정된 수 만큼 매개변수가(선언된 순서 순) 인덱싱이 된다.
- 인덱싱에는 변수의 선언된 순서를 포함한다. 같은 값에 선언된 위치가 다르면 인덱싱 값도 다르다.
- 인덱싱 매개 변수는 EventLog의 indexed 필드에 array형태로 저장이 된다


### Indexing Rule(Bloom filter hash function)
- `raw-data` = `매개변수순서(1byte)` + `data`

  -  bool, int, bytes: 원 값의 bytes를 `data`로 사용
  -  Address: body의 20 bytes를 `data`로 사용
  -  str: utf-8 인코딩을 한 bytes를 `data`로 사용

- `hash-data` = sha3-256(`raw-data`)

- `chunk[0]` = `hash-data[0:2]` & 2047

- `chunk[1]` = `hash-data[2:4]` & 2047 

- `chunk[2]` = `hash-data[4:6]`  & 2047

- bloom-data = set(`chunk[0]`) | set(`chunk[1]`) | set(`chunk[2]`) 


## Bloom 
- 256 bytes의 raw bytes
- Indexing 결과의 bloom-data들을 `OR` 연산 


### Filter Search
- filter를 하는 값을  [Indexing Rule](#Indexing Rule(Bloom filter hash function)) 에 따라 bloom-data를 생성
- Bloom 값에 포함되는지 판단
  - 포함: 해당하는 조건에 충족될 확률이 높음 > 실제 Data 확인
  - 포함하지않음: 해당하는 조건에 충족되지 않음


## Transaction Result에 포함되는 형태
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