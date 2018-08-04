간단한 토큰을 만들어봅니다.
==================================

개요
--------------
```
$ tbears init {project_name} {class_name}
```
위의 명령을 수행하면 {project_name} 폴더가 생기며,
해당 폴더 안에 \_\_init\_\_.py, {project_name}.py, package.json 파일이 자동 생성됩니다.<br/>
{project_name}.py 파일에는 {class_name}으로 메인 클래스가 선언되어 있습니다.<br/>


<br/>
1000개의 초기 발행량을 가지며 처음 생성한 사람에게 전체 발행량을 발급하는 간단한 토큰 예제입니다.<br/>
아울러 토큰을 전달하는 transfer 함수를 제공합니다.<br/>

```python
class SampleToken(IconScoreBase):

    __BALANCES = 'balances'
    __TOTAL_SUPPLY = 'total_supply'

    @eventlog(indexed=3)
    def Transfer(self, addr_from: Address, addr_to: Address, value: int): pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self.__total_supply = VarDB(self.__TOTAL_SUPPLY, db, value_type=int)
        self.__balances = DictDB(self.__BALANCES, db, value_type=int)

    def on_install(self, init_supply: int = 1000, decimal: int = 18) -> None:
        super().on_install()

        total_supply = init_supply * 10 ** decimal

        self.__total_supply.set(total_supply)
        self.__balances[self.msg.sender] = total_supply

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def total_supply(self) -> int:
        return self.__total_supply.get()

    @external(readonly=True)
    def balance_of(self, addr_from: Address) -> int:
        return self.__balances[addr_from]

    def __transfer(self, _addr_from: Address, _addr_to: Address, _value: int) -> bool:

        if self.balance_of(_addr_from) < _value:
            self.revert(f"{_addr_from}'s balance < {_value}")

        self.__balances[_addr_from] = self.__balances[_addr_from] - _value
        self.__balances[_addr_to] = self.__balances[_addr_to] + _value

        self.Transfer(_addr_from, _addr_to, _value)
        return True

    @external
    def transfer(self, addr_to: Address, value: int) -> bool:
        return self.__transfer(self.msg.sender, addr_to, value)

    def fallback(self) -> None:
        pass

```

<br/>
위의 샘플 토큰을 가지고 크라우드 세일을 하는 예제입니다.<br/>
icx와의 교환 비율은 1:1이며 1분 후에 크라우드 세일이 종료됩니다.<br/>
크라우드 펀딩에 참가한 총 인원을 구하는 함수(total_joiner_count)와 크라우드 세일 마감함수(check_goal_reached)<br/>
그리고 크라우드 세일 성공 및 실패 시에 icx를 환급받는 함수(safe_withdrawal)를 제공합니다.<br/>

```python
class SampleTokenInterface(InterfaceScore):
    @interface
    def transfer(self, addr_to: Address, value: int) -> bool: pass


class SampleCrowdSale(IconScoreBase):
    __ADDR_BENEFICIARY = 'addr_beneficiary'
    __FUNDING_GOAL = 'funding_goal'
    __AMOUNT_RAISE = 'amount_raise'
    __DEAD_LINE = 'dead_line'
    __PRICE = 'price'
    __BALANCES = 'balances'
    __ADDR_TOKEN_SCORE = 'addr_token_score'
    __FUNDING_GOAL_REACHED = 'funding_goal_reached'
    __CROWD_SALE_CLOSED = 'crowd_sale_closed'
    __JOINER_LIST = 'joiner_list'

    @eventlog(indexed=3)
    def FundTransfer(self, backer: Address, amount: int, is_contribution: bool):
        pass

    @eventlog(indexed=2)
    def GoalReached(self, recipient: Address, total_amount_raised: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

        self.__addr_beneficiary = VarDB(self.__ADDR_BENEFICIARY, db, value_type=Address)
        self.__addr_token_score = VarDB(self.__ADDR_TOKEN_SCORE, db, value_type=Address)
        self.__funding_goal = VarDB(self.__FUNDING_GOAL, db, value_type=int)
        self.__amount_raise = VarDB(self.__AMOUNT_RAISE, db, value_type=int)
        self.__dead_line = VarDB(self.__DEAD_LINE, db, value_type=int)
        self.__price = VarDB(self.__PRICE, db, value_type=int)
        self.__balances = DictDB(self.__BALANCES, db, value_type=int)
        self.__joiner_list = ArrayDB(self.__JOINER_LIST, db, value_type=Address)
        self.__funding_goal_reached = VarDB(self.__FUNDING_GOAL_REACHED, db, value_type=bool)
        self.__crowd_sale_closed = VarDB(self.__CROWD_SALE_CLOSED, db, value_type=bool)

        self.__sample_token_score = self.create_interface_score(self.__addr_token_score.get(), SampleTokenInterface)

    def on_install(self, funding_goal_in_icx: int = 100, duration_in_minutes: int = 1,
                   icx_cost_of_each_token: int = 1) -> None:
        super().on_install()

        one_icx = 1 * 10 ** 18
        one_minute_to_sec = 1 * 60
        one_second_to_microsec = 1 * 10 ** 6
        now_seconds = self.now()

        # genesis params
        if_successful_send_to = self.msg.sender
        addr_token_score = Address.from_string('cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf')

        self.__addr_beneficiary.set(if_successful_send_to)
        self.__addr_token_score.set(addr_token_score)
        self.__funding_goal.set(funding_goal_in_icx * one_icx)
        self.__dead_line.set(now_seconds + duration_in_minutes * one_minute_to_sec * one_second_to_microsec)
        price = int(icx_cost_of_each_token * one_icx)
        self.__price.set(price)

        self.__sample_token_score = self.create_interface_score(self.__addr_token_score.get(), SampleTokenInterface)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def total_joiner_count(self):
        return len(self.__joiner_list)

    @payable
    def fallback(self) -> None:
        if self.__crowd_sale_closed.get():
            self.revert('crowd sale is closed')

        amount = self.msg.value
        self.__balances[self.msg.sender] = self.__balances[self.msg.sender] + amount
        self.__amount_raise.set(self.__amount_raise.get() + amount)
        value = int(amount / self.__price.get())

        self.__sample_token_score.transfer(self.msg.sender, value)

        if self.msg.sender not in self.__joiner_list:
            self.__joiner_list.put(self.msg.sender)

        self.FundTransfer(self.msg.sender, amount, True)

    @external
    def check_goal_reached(self):
        if not self.__after_dead_line():
            self.revert('before deadline')

        if self.__amount_raise.get() >= self.__funding_goal.get():
            self.__funding_goal_reached.set(True)
            self.GoalReached(self.__addr_beneficiary.get(), self.__amount_raise.get())
        self.__crowd_sale_closed.set(True)

    def __after_dead_line(self):
        return self.now() >= self.__dead_line.get()

    @external
    def safe_withdrawal(self):
        if not self.__after_dead_line():
            self.revert('before deadline')

        if not self.__funding_goal_reached.get():
            amount = self.__balances[self.msg.sender]
            self.__balances[self.msg.sender] = 0
            if amount > 0:
                if self.icx.send(self.msg.sender, amount):
                    self.FundTransfer(self.msg.sender, amount, False)
                else:
                    self.__balances[self.msg.sender] = amount

        if self.__funding_goal_reached.get() and self.__addr_beneficiary.get() == self.msg.sender:
            if self.icx.send(self.__addr_beneficiary.get(), self.__amount_raise.get()):
                self.FundTransfer(self.__addr_beneficiary.get(), self.__amount_raise.get(),
                                  False)
            else:
                self.__funding_goal_reached.set(False)

```


문법 설명
--------------
계약서 작성시 매개 변수 타입, 리턴 타입에 대한 명시(타입 힌트)를 해줄 것을 권장합니다.<br/>
계약서에서 제공하는 외부 API에 대한 정보를 계약서에 명시된 타입 힌트를 이용하여 만들게 됩니다.<br/>
만약 타입 힌트가 적혀있지 않다면 해당 API 정보에 함수명에 대한 내용만 자동 기입됩니다.<br/>

예시)
```python
@external
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
아울러 아래와 같이 부모 클래스의 초기화 함수를 반드시 호출해야 합니다.<br/>

예시)
``` python
super().__init__(db)
```

#### on_install
계약서가 최초 배포되었을 때 상태 DB에 기록할 내용을 구현합니다.<br/>
이 함수의 호출은 최초 배포할 때 1회만 호출되며, 향후 계약서의 업데이트, 삭제 시에는 호출되지 않습니다.<br/>

#### VarDB, DictDB, ArrayDB
상태 DB에 읽고 쓰는 작업을 좀 더 편리하게 하기 위한 유틸리티 클래스입니다.<br/>
키는 숫자, 문자 모두 가능하며, 반환될 value_type은 integer(정수), str(문자), Address(주소 객체), 그리고 bytes가 가능합니다. <br/>
존재하지 않는 키로 값을 얻으려 하면, value_type이 int일 때 0, str일 때 ""을 반환하며, Address 객체 및 bytes일 때는 None을 반환합니다.<br/>
VarDB는 단순 키-값 형식의 상태를 저장할 때 사용할 수 있으며, DictDB는 파이썬의 dict와 비슷하게 동작할 수 있게 구현되었습니다. <br/>
참고로 DictDB는 순서 보장이 되지 않습니다. <br/>
Length와 iterator를 지원하는 ArrayDB는 순서 보장을 합니다. <br/>

##### VarDB('DB에 접근할 key', '접근할 db', '반환될 type')<br/>
예시) 상태 DB에 'name' 키로 'theloop' 값을 기록할 때:<br/>
```python
VarDB('name', db, value_type=str).set('theloop')
```
'name' 키에 대해 기록한 값을 읽어올 때:<br/>
```python
name = VarDB('name', db, value_type=str).get()
print(name) ##'theloop'
```

##### DictDB('DB에 접근할 key', '접근할 db', '반환될 type', '컨테이너의 키에 대한 뎁스(기본값 1)')<br/>
예시1) 상태 DB에 파이썬 dict의 형식을 사용할 때 (test_dict1['key'] 형식): <br/>
```python
test_dict1 = DictDB('test_dict1', db, value_type=int)
test_dict1['key'] = 1 ## set
print(test_dict1['key']) ## get 1

print(test_dict1['nonexistence_key']) # 0 출력(존재하지 않는 키에 접근, value_type=int)
```

예시2) 이차원 배열 형식 (test_dict2['key1']['key2']):<br/>
```python
test_dict2 = DictDB('test_dict2', db, value_type=str, depth=2)
test_dict2['key1']['key2'] = 'a' ## set
print(test_dict2['key1']['key2']) ## get 'a'

print(test_dict2['key1']['nonexistence_key']) # "" 출력(존재하지 않는 키에 접근, value_type=str)
```

depth가 2 이상인 경우에 dict[key]로 접근시 value_type이 아니라 DictDB가 새로 만들어져 나옵니다.<br/>
만약 설정한 depth와 다르게 하여 값을 세팅하려 하면 예외가 발생합니다.<br/>

예시3)<br/>
```python
test_dict3 = DictDB('test_dict2', db, value_type=str, depth=3)
test_dict3['key1']['key2']['key3'] = 1  # ok
test_dict3['key1']['key2'] = 1  # raise mismatch exception

test_dict2 = test_dict3['key']['key2']
test_dict2['key1'] = 1  # ok
```

##### ArrayDB('DB에 접근할 key', '접근할 db', '반환될 type')<br/>
1차원 Array만 지원합니다.<br/>
put, get, pop을 지원하며, 중간 삽입(insert)은 지원하지 않습니다.<br/>

```python
test_array = ArrayDB('test_array', db, value_type=str)
test_array.put(0)
test_array.put(1)
test_array.put(2)
test_array[0] = 0 # ok
# test_array[100] = 1 # error
len(test_array) # ok
for e in test_array: # ok
    print(e)
print(test_array[-1]) # ok
print(test_array[-100]) # error
```

#### external 데코레이터 (@external)
이 데코레이터가 붙은 함수들만 외부에서 호출이 가능합니다.<br/>
즉 외부에서 호출 가능한 API 목록에는 이 데코레이터가 붙은 함수들만 등록됩니다.<br/>
external 데코레이터가 없는 함수를 호출하면 해당 call은 실패합니다.<br/>
external(readonly=True)라고 선언된 함수는 읽기전용 db에만 접근 가능합니다. Solidity의 view 키워드 의미와 같습니다. <br/>
만약 payable이 있는 상태이나 external(readonly=True)라고 선언되었다면 해당 call은 실패합니다.<br/>
external 데코레이터가 중복으로 선언되어 있다면 import 타임에 IconScoreException이 발생합니다.<br/>

#### payable 데코레이터 (@payable)
이 데코레이터가 붙은 함수들만 icx 코인 거래가 가능합니다.<br/>
0이 들어와도 문제가 없습니다. <br/>
만약 payable이 없는 함수인데 msg.value (icx) 값이 있다면 해당 call은 실패합니다.<br/>

#### eventlog 데코레이터 (@eventlog)
이 데코레이터가 붙은 함수는 TxResult에 'eventlogs'의 내용으로 로그가 기록됩니다.<br/>
해당 함수 선언은 구현 부가 없는 함수 작성을 권장하며, 설사 구현 부가 있더라도 해당 내용은 동작하지 않습니다.<br/>
함수 선언 시 매개 변수의 Type Hint는 필수입니다. Type Hint가 없다면 트랜잭션은 성공하지 못합니다.<br/>
함수 선언 시에 데코레이터의 매개 변수에 `indexed` 값을 설정하면 해당 수 만큼의 변수(선언된 순서 순)가 인덱싱이 되어 블룸 필터(Bloom filter)에 적용이 됩니다.<br/>

예시)<br/>
```python
# 선언부
@eventlog
def FundTransfer1(self, backer: Address, amount: int, is_contribution: bool): pass

@eventlog(indexed=1) # 변수 1개(backer)만 인덱싱 됨
def FundTransfer2(self, backer: Address, amount: int, is_contribution: bool): pass

# 실행부
self.FundTransfer1(self.msg.sender, amount, True)
self.FundTransfer2(self.msg.sender, amount, True)
```
매개 변수는 기본 타입(int, str, bytes, bool, Address)만 지원하며, array 타입은 지원하지 않습니다.<br/>
인덱싱이 되지 않는 매개 변수는 TxResult에 인덱싱 된 매개 변수와 별도로 분리되어 저장됩니다.<br/>
매개 변수의 인덱싱은 최대 3까지 가능합니다.<br/>

#### fallback
fallback 함수에는 external 데코레이터를 사용할 수 없습니다. (즉 외부 계약서 및 유저가 호출 불가)<br/>
만약 계약서에서 데이터 필드가 없는 순수한 icx 코인만 해당 계약서에 이체되었다면 이 fallback 함수가 호출됩니다.<br/>
만약 icx 코인이 이체되었는데, payable을 붙이지 않은 기본 fallback 함수가 호출되었다면<br/>
payable 규칙에 의거하여 해당 이체는 실패합니다.<br/>

#### InterfaceScore
다른 스코어의 함수를 호출하는 인터페이스로, 기존에 제공하던 call 함수 대신 사용할 수 있습니다.<br/>
사용 형식은 다음과 같습니다.<br/>

```python
class SampleTokenInterface(InterfaceScore):
    @interface
    def transfer(self, addr_to: Address, value: int) -> bool: pass
```
다른 스코어에 interface 데코레이터가 붙은 함수처럼 정의된 함수가 있다면 그 함수를 호출할 수 있습니다.<br/>
eventlog 데코레이터와 마찬가지로 구현부가 없는 함수 작성을 권장하며, 설사 구현부가 있더라도 해당 내용은 동작하지 않습니다.<br/>

예시)<br/>
IconScoreBase 내장함수 create_interface_score(스코어 주소, 인터페이스로 사용할 클래스)를 사용하여,
InterfaceScore 객체를 가져옵니다.<br/>
해당 객체를 사용하여 다른 스코어의 외부 함수를 일반 함수 콜처럼 호출할 수 있습니다.<br/>

```python
sample_token_score = self.create_interface_score(self.__addr_token_score.get(), SampleTokenInterface)
sample_token_score.transfer(self.msg.sender, value)
```

내장 함수 설명
--------------
#### create_interface_score(addr_to(주소), interface_cls(인터페이스 클래스)) -> interface_cls 객체
이 함수를 통하여 다른 스코어(addr_to)의 external 함수에 접근 가능한 객체를 얻습니다.

#### [legacy] call(addr_to(주소), func_name,  kw_dict(함수의 params)) -> 콜 함수의 반환 값
InterfaceScore가 도입되기 전에 다른 스코어의 함수를 호출하기 위해 제공했던 함수입니다.

#### revert(message: str) -> None
개발자가 강제로 revert 예외를 발생시킬 수 있습니다.<br/>
해당 예외가 발생하면 그동안 실행하면서 변경되었던 상태 DB 값은 롤백됩니다.<br/>

내장 프로퍼티 설명
--------------

#### msg : 스코어를 부른 계정의 정보가 담겨있습니다.
* msg.sender :
현재 이 스코어의 함수를 호출한 계정의 주소입니다. <br/>
만약 해당 스코어에서 다른 스코어의 함수를 접근하면 호출한 스코어의 주소 값을 가리킵니다.<br/>
* msg.value :
현재 이 스코어의 함수를 호출한 계정에서 전송하려는 icx 값입니다. <br/>

#### tx : 해당 트랜잭션의 정보입니다.
* tx.origin : 트랜잭션을 만든 계정
* tx.index : 트랜잭션 인덱스
* tx.hash : 트랜잭션 해쉬 값
* tx.timestamp : 트랜잭션이 생성된 시각
* tx.nonce : (옵션) 임의의 값

#### block : 해당 트랜잭션을 담고있는 블럭의 정보입니다.
* block.height : 블럭의 높이 값
* block.hash : 블럭의 해쉬 값
* block.timestamp : 블럭이 생성된 시각

#### icx : icx 코인을 전송하기 위한 객체입니다.
* icx.transfer(addr_to(주소), amount(정수값)) -> bool<br/>
addr_to 주소로 amount만큼 icx 코인을 전송합니다.<br/>
만약 로직 실행 중에 예외가 발생하면 해당 예외를 처리하지 않고 상위로 올려줍니다.<br/>
성공하면 반환 값은 True입니다.<br/>

* icx.send(addr_to(주소), amount(정수값)) -> bool<br/>
addr_to 주소로 amount만큼 icx 코인을 전송합니다.<br/>
기본 동작은 transfer와 동일하나, 예외를 이 함수 안에서 처리합니다.<br/>
전송을 성공하면 True, 실패하면 False가 반환됩니다.<br/>

#### db : 상태 DB를 접근하는 db 객체입니다.

#### address : 스코어의 주소 값입니다.

#### owner : 해당 스코어를 배포한 계정의 주소입니다.

#### now : block.timestamp의 wrapping 함수입니다.
