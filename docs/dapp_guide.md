간단한 토큰을 만들어봅니다.
==================================

<br/>
1000개의 초기 발행량을 가지며 처음 생성한 사람에게 전체 발행량을 발급하는 간단한 토큰 예제입니다.<br/>
아울러 토큰을 전달하는 transfer 함수를 제공합니다.<br/>

```python
class SampleToken(IconScoreBase):

    _BALANCES = 'balances'
    _TOTAL_SUPPLY = 'total_supply'

    def __init__(self, db: IconScoreDatabase, addr_owner: Address) -> None:
        super().__init__(db, addr_owner)
        self._total_supply = VarDB(self._TOTAL_SUPPLY, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)

    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)

        init_supply = 1000
        decimal = 18
        total_supply = init_supply * 10 ** decimal

        self._total_supply.set(total_supply)
        self._balances[self.msg.sender] = total_supply

    @external(readonly=True)
    def total_supply(self) -> int:
        return self._total_supply.get()

    @external(readonly=True)
    def balance_of(self, addr_from: Address) -> int:
        return self._balances[addr_from]

    def _transfer(self, _addr_from: Address, _addr_to: Address, _value: int) -> bool:

        if self.balance_of(_addr_from) < _value:
            raise IconScoreBaseException(f"{_addr_from}'s balance < {_value}")

        self._balances[_addr_from] = self._balances[_addr_from] - _value
        self._balances[_addr_to] = self._balances[_addr_to] + _value
        return True

    @external
    def transfer(self, addr_to: Address, value: int) -> bool:
        return self._transfer(self.msg.sender, addr_to, value)

    def fallback(self) -> None:
        pass

```

<br/>
위의 샘플토큰을 가지고 크라우드 세일을 하는 예제입니다.<br/>
icx와 교환비율은 1:1이며 1분후에 크라우드 세일이 종료됩니다.<br/>
크라우드펀딩에 참가한 총 인원을 구하는 함수(total_joiner_count)와 크라우드세일 마감함수(check_goal_reached)<br/>
그리고 크라우드세일 성공 및 실패시에 icx를 환급받는(safe_withdrawal)을 제공합니다.<br/>

```python
class SampleCrowdSale(IconScoreBase):
    _ADDR_BENEFICIARY = 'addr_beneficiary'
    _FUNDING_GOAL = 'funding_goal'
    _AMOUNT_RAISE = 'amount_raise'
    _DEAD_LINE = 'dead_line'
    _PRICE = 'price'
    _BALANCES = 'balances'
    _ADDR_TOKEN_SCORE = 'addr_token_score'
    _FUNDING_GOAL_REACHED = 'funding_goal_reached'
    _CROWD_SALE_CLOSED = 'crowd_sale_closed'
    _JOINER_LIST = 'joiner_list'

    def __init__(self, db: IconScoreDatabase, owner: Address) -> None:
        super().__init__(db, owner)

        self._addr_beneficiary = VarDB(self._ADDR_BENEFICIARY, db, value_type=Address)
        self._addr_token_score = VarDB(self._ADDR_TOKEN_SCORE, db, value_type=Address)
        self._funding_goal = VarDB(self._FUNDING_GOAL, db, value_type=int)
        self._amount_raise = VarDB(self._AMOUNT_RAISE, db, value_type=int)
        self._dead_line = VarDB(self._DEAD_LINE, db, value_type=int)
        self._price = VarDB(self._PRICE, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)
        self._joiner_list = ArrayDB(self._JOINER_LIST, db, value_type=Address)
        self._funding_goal_reached = VarDB(self._FUNDING_GOAL_REACHED, db, value_type=bool)
        self._crowd_sale_closed = VarDB(self._CROWD_SALE_CLOSED, db, value_type=bool)

    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)

        one_icx = 1 * 10 ** 18
        one_minute_to_sec = 1 * 60
        one_second_to_microsec = 1 * 10 ** 6
        now_seconds = self.now()

        # genesis params
        if_successful_send_to = self.msg.sender
        addr_token_score = Address.from_string('cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf')

        funding_goal_in_icx = 100
        duration_in_minutes = 1
        icx_cost_of_each_token = 1

        self._addr_beneficiary.set(if_successful_send_to)
        self._addr_token_score.set(addr_token_score)
        self._funding_goal.set(funding_goal_in_icx * one_icx)
        self._dead_line.set(now_seconds + duration_in_minutes * one_minute_to_sec * one_second_to_microsec)
        price = int(icx_cost_of_each_token * one_icx)
        self._price.set(price)

    @external(readonly=True)
    def total_joiner_count(self):
        return len(self._joiner_list)

    @payable
    def fallback(self) -> None:
        if self._crowd_sale_closed.get():
            raise IconScoreBaseException('crowd sale is closed')

        amount = self.msg.value
        self._balances[self.msg.sender] = self._balances[self.msg.sender] + amount
        self._amount_raise.set(self._amount_raise.get() + amount)
        value = int(amount / self._price.get())
        self.call(self._addr_token_score.get(), 'transfer', {'addr_to': self.msg.sender, 'value': value})

        if self.msg.sender not in self._joiner_list:
            self._joiner_list.put(self.msg.sender)

        # event FundTransfer(msg.sender, amount, True)

    @external
    def check_goal_reached(self):
        if not self.__after_dead_line():
            raise IconScoreBaseException('before deadline')

        if self._amount_raise.get() >= self._funding_goal.get():
            self._funding_goal_reached.set(True)
            # event GoalReached(beneficiary, amountRaised)
        self._crowd_sale_closed.set(True)

    def __after_dead_line(self):
        return self.now() >= self._dead_line.get()

    @external
    def safe_withdrawal(self):
        if not self.__after_dead_line():
            raise IconScoreBaseException('before deadline')

        if not self._funding_goal_reached.get():
            amount = self._balances[self.msg.sender]
            if amount > 0:
                if self.send(self.msg.sender, amount):
                    # event FundTransfer(msg.sender, amount, False)
                    pass
                else:
                    self._balances[self.msg.sender] = amount

        if self._funding_goal_reached.get() and self._addr_beneficiary.get() == self.msg.sender:
            if self.send(self._addr_beneficiary.get(), self._amount_raise.get()):
                # event FundTransfer(beneficiary, amountRaised, False)
                pass
            else:
                self._funding_goal_reached.set(False)
                
```


문법 설명
--------------
계약서 작성시 매개 변수 타입, 리턴 타입에 대한 명시를 해줄 것을 권장합니다.<br/>
계약서 정보를 자동으로 만들어 줄때 API에 대한 내용을 계약서에 명시된 타입힌트를 이용하여 제작을 진행합니다.<br/>
만약 타입힌트가 적혀있지 않다면 해당 계약서 정보에 함수명에 대한 내용만 자동 기입됩니다.<br/>

예시)
```python
@external()
def func1(arg1: int, arg2: str) -> object:
    pass
```

#### 예외 처리
계약서를 작성하면서 예외를 처리하고 싶다면,<br/>
IconServiceBaseException 예외를 상속받아서 구현하길 권장합니다.<br/>

#### 최상단 부모 클래스 (IconScoreBase)
모든 DApp 관련 클래스를 만들 때는 IconScoreBase 클래스를 상속받아서 사용합니다.<br/>
이 클래스를 상속받지 않은 계약서는 배포할 수 없습니다.<br/>

#### \_\_init\_\_
파이썬 자체의 초기화 함수입니다. 이는 각각의 노드에서 해당 계약서가 로드될 때 호출되는 함수입니다.<br/>
초기화 시에 해당 계약서에서 사용할 멤버 변수를 선언합니다.<br/>
아울러 아래와 같이 부모 클래스의 초기화 함수를 호출할 것을 권장합니다.<br/>
예시)
``` python
super().__init__()
```

#### genesis_init
계약서가 최초 배포되었을 때 상태 DB에 기록할 내용을 구현합니다.<br/>
이 함수의 호출은 최초 배포할 때 1회만 호출되며, 향후 계약서의 업데이트, 삭제 시에는 호출되지 않습니다.<br/>

#### VarDB, DictDB, ArrayDB
상태 DB에 읽고 쓰는 작업을 좀 더 편리하게 하기 위한 유틸리티 클래스입니다.<br/>
키는 숫자, 문자 모두 가능하며, 반환될 value_type은 integer(정수), str(문자), Address(주소 객체), 그리고 bytes가 가능합니다. <br/>
존재하지 않는 키로 값을 얻으려 하면, value_type이 int일 때 0, str일 때 ""을 반환하며, Address 객체 및 bytes일 때는 None을 반환합니다.</br>
VarDB는 단순 키-값 형식의 상태를 저장할 때 사용할 수 있으며, DictDB는 파이썬의 dict와 비슷하게 동작할 수 있게 구현되었습니다. <br/>
참고로 DictDB는 순서 보장이 되지 않습니다. <br/>
Length와 iterator를 지원하는 ArrayDB는 순서 보장을 합니다. <br/>

##### VarDB('DB에 접근할 key', '접근할 db', '반환될 type')으로 사용됩니다.<br/>
예시) 상태 DB에 'name' 키로 'theloop' 값을 기록할 때:<br/>
```python
VarDB('name', db, value_type=str).set('theloop')
```
'name' 키에 대해 기록한 값을 읽어올 때:<br/>
```python
name = VarDB('name', db, value_type=str).get()
print(name) ##'theloop'
```

##### DictDB('DB에 접근할 key', '접근할 db', '반환될 type', '컨테이너의 키에 대한 뎁스(기본값 1)')으로 사용가능합니다.<br/>
예시1) 상태 DB에 파이썬 dict의 형식을 사용할 때 (test_dict1['key'] 형식): <br/>
```python
test_dict1 = DictDB('test_dict1', db, value_type=int)
test_dict1['key'] = 1 ## set
print(test_dict1['key']) ## get 1

print(test_dict1['nonexistence_key']) # 0출력(존재하지 않는 키에 접근, value_type=int)
```

예시2) 이차원 배열 형식 (test_dict2['key1']['key2']):<br/>
```python
test_dict2 = DictDB('test_dict2', db, value_type=str, depth=2)
test_dict2['key1']['key2'] = 'a' ## set
print(test_dict2['key1']['key2']) ## get 'a'

print(test_dict2['key1']['nonexistence_key']) # "" 출력(존재하지 않는 키에 접근, value_type=str)
```

##### ArrayDB('DB에 접근할 key', '접근할 db', '반환될 type')으로 사용됩니다.<br/>
1차원 Array만 지원합니다.<br/>
put, get, pop을 지원하며, 중간삽입(insert)는 지원하지 않습니다.<br/>

```python
test_array = ArrayDB('test_array', db, value_type=str)
test_array.put(0)
test_array.put(1)
test_array.put(2)
test_array[0] = 0 # ok
# test_array[100] = 1 #error
len(test_array) # ok
for e in test_array: # ok
    print(e)
print(test_array[-1]) #ok
print(test_array[-100]) #error
```

#### external 데코레이터 (@external)
이 데코레이터가 붙은 함수들만 외부에서 호출이 가능합니다.<br/>
즉 외부에서 호출 가능한 API 목록에는 이 데코레이터가 붙은 함수들만 등록됩니다.<br/>
external 데코레이터가 없는 함수를 호출하면 해당 call은 실패합니다.<br/>
external(readonly=True)라고 선언된 함수는 읽기전용 db에만 접근 가능합니다. Solidity의 view 키워드 의미와 같습니다. <br/>
만약 payable이 없는 함수인데 msg.value 값이 있다면 해당 call은 실패합니다.<br/>
만약 payable이 있는 상태이나 external(readonly=True) 라면 해당 call은 실패합니다.<br/>

#### payable 데코레이터 (@payable)
이 데코레이터가 붙은 함수들만 icx 코인 거래가 가능합니다.<br/>
0이 들어와도 문제가 없습니다. <br/>
만약 payable이 없는 함수에 icx값이 들어있다면 해당 call은 실패합니다.

#### fallback
fallback 함수에는 external 데코레이터를 사용할 수 없습니다. (즉 외부 계약서 및 유저가 호출 불가)<br/>
만약 계약서에서 정의되지 않은 함수를 call하거나 데이터 필드가 없는 순수한 icx 코인만 해당 계약서에 <br/>
이체되었다면 이 fallback 함수가 호출됩니다.<br/>
만약 icx 코인이 이체되었는데, payable을 붙이지 않은 기본 fallback 함수가 호출되었다면<br/>
payable 규칙에 의거하여 해당 이체는 실패합니다.<br/>
