간단한 토큰을 만들어봅니다.
==================================

스펙은 1000개의 초기 발행량을 가진 토큰이며 처음 생성한 사람에게 전체 발행량을 발급합니다.<br/>
그리고 토큰을 전달하는 transfer 함수를 제공합니다.<br/>

```python
@score
class SampleToken(IconScoreBase):

    _BALANCES = 'balances'
    _TOTAL_SUPPLY = 'total_supply'

    def __init__(self, db: IconServiceDatabase, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._total_supply = VariableForDB(self._TOTAL_SUPPLY, db, variable_type=int)
        self._balances = ContainerForDB(self._BALANCES, db, limit_depth=1, value_type=int)

    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)

        init_supply = 1000
        decimal = 18
        total_supply = init_supply * 10 ** decimal

        self._total_supply.set(total_supply)
        self._balances[self.msg.sender] = total_supply

    @external(readonly=True)
    def total_supply(self) -> int:
        return int(self._total_supply.get())

    @external(readonly=True)
    def balance_of(self, addr_from: Address) -> int:
        var = self._balances[addr_from]
        if var is None:
            var = 0
        return var

    def _transfer(self, _addr_from: Address, _addr_to: Address, _value: int) -> bool:

        if self.balance_of(_addr_from) < _value:
            raise IconServiceBaseException(f"{_addr_from}'s balance < {_value}")

        self._balances[_addr_from] = self.balance_of(_addr_from) - _value
        self._balances[_addr_to] = _value
        return True

    @external()
    def transfer(self, addr_to: Address, value: int) -> bool:
        return self._transfer(self.msg.sender, addr_to, value)

    @payable
    def fallback(self) -> None:
        pass
```

문법설명
--------------
계약서 작성시 매개 변수 타입, 리턴 타입에 대한 명시를 해줄 것을 권장합니다.<br/>
해당 값으로 자동 템플릿이 생성될 예정입니다.<br/>
예시)
```python
def func1(arg1: int, arg2: str) -> object:
    pass
```

#### 예외
계약서를 작성하면서 예외 핸들링을 한다면,<br/>
IconServiceBaseException 예외를 상속받아서 구현하길 권장합니다.<br/>

#### score 데코레이터(@score)
다음 파이썬 코드가 메인 컨트랙트 클래스라는 것을 지정합니다.<br/>
score가 붙은 클래스는 상속이 불가합니다.<br/>

#### 최상단 부모 클래스(IconScoreBase)
모든 DApp 관련 클래스를 만들 때는 IconScoreBase 클래스를 상속받아서 사용합니다.<br/>
해당 클래스를 상속받지 않으면 계약서는 배포가 불가합니다.<br/>

#### __init__
해당 함수는 파이썬 자체의 초기화 함수이다. 이는 각각의 peer에서 각각의 SCORE에 해당 계약서가 로드 되었을때 호출되는 함수입니다.<br/>
초기화 시에 해당 계약서에서 사용할 멤버 변수를 선언합니다.<br/>
아래와 같이 부모 클래스의 초기화를 호출할 것을 권장합니다.<br/>
예시)
``` python
super().__init__()
```

#### genesis_init
해당 계약서가 최초 배포가 되었을 때 상태 DB에 write할 내용을 구현합니다.<br/>
관련 함수의 call은 최초 배포할 때 1회만 호출되며, 향후 update, delete 시에는 호출되지 않습니다.<br/>

#### VariableForDB, ContainerForDB
해당 클래스는 상태 DB에 관련한 값을 좀더 편리하게 사용하게 하는 유틸리티 클래스입니다.<br/>
키 값은 숫자, 문자 모두 가능하며, 반환될 type은 integer(정수), str(문자), Address(주소 객체)만 가능합니다. <br/>

##### VariableForDB('DB에 접근할 key', '접근할 db', '반환될 type')으로 사용됩니다.<br/>
예시) 상태 DB에 'name' 키로 'theloop'를 기입하고 싶다.<br/>
```python
VariableForDB('name', db, variable_type=str).set('theloop')
```
아까 기록한 'name' 키에 대한 값을 읽어오고 싶다.<br/>
```python
name = VariableForDB('name', db, variable_type=str).get()
print(name) ##'theloop'
```

##### ContainerForDB('DB에 접근할 key' '접근할 db', '컨테이너의 키에 대한 뎁스', '반환될 type')으로 사용가능합니다.<br/>
예시1) 상태 DB에 파이썬 dict의 형식을 사용하고 싶다. test_dict1['key'] <br/>
```python
test_dict1 = ContainerForDB('test_dict1', db, limit_depth=1, value_type=int)
test_dict1['key'] = 1 ## set
print(test_dict1['key']) ## get 1
```

예시2) test_dict2['key1']['key2']<br/>
```python
test_dict2 = ContainerForDB('test_dict2', db, limit_depth=2, value_type=str)
test_dict2['key1']['key2'] = 'a' ## set
print(test_dict2['key1']['key2']) ## get 'a'
```

#### external 데코레이터(@external)
이 데코레이터가 붙은 함수들만 외부에서 호출이 가능합니다.<br/>
즉 외부에서 호출 가능한 API에는 이 데코레이터가 붙은 함수들만 등록됩니다.<br/>
external 데코레이터가 없는 함수를 호출하면 해당 call은 실패합니다.<br/>
external(readonly=True) 라면 이 함수는 읽기전용 db만 접근 가능합니다. Solidity의 view 키워드 의미와 같습니다. <br/>
만약 payable이 없는 함수인데 msg.value 값이 있다면 해당 call은 실패합니다.<br/>
만약 payable이 있는 상태이나 external(readonly=True) 라면 해당 call은 실패합니다.<br/>

#### payable 데코레이터(@payable)
이 데코레이터가 붙은 함수들만 icx 코인 거래가 가능합니다.<br/>
0이 들어와도 문제가 없습니다. <br/>

#### fallback
만약 잘못된 함수를 call 한다고 하면 해당 fallback 함수가 호출됩니다.<br/>
데이터 없이 순수한 icx코인만 해당 계약서에 이체가 되었다면 해당 fallback 함수가 호출됩니다.<br/>
fallback 함수는 external을 사용할 수 없습니다.(외부 계약서 및, 유저가 호출 불가)<br/>
만약 icx가 이체가 되었는데, payable을 붙이지 않은 기본 fallback 함수가 호출되었다면<br/>
payable 규칙에 의거하여 해당 이체는 실패합니다.<br/>
