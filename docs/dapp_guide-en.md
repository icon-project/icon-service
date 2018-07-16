ICON DApp Guide
==================================

Overview
--------------

This document explains how to create a DApp program under the ICON Score framework.
Let's start by creating a simple token contract.

```
$ tbears init sample_token SampleToken
```

Above command will create `sample_token` folder,
and generate `__init__.py`, `sample_token.py`, `package.json` files in the folder.
`sample_token.py` has a main class declaration whose name is `SampleToken`.
`__init__.py` has auto-generated statements for dynamic import.
If folder structure changes, make sure you adjust the import statements.

This exmaple generates 1,000 initial tokens, and 100% of tokens go to the contract owner.
Transfer function is given to transfer tokens to other accounts.

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

Now, we are going to write a crowd sale contract using above token.
Exchange ratio to icx is 1:1, and the crowd sale duration is 1 minute.
`total_joiner_count` function returns the number of contributors,
and `check_goal_reached` function tests if the crowd sale target has been met.
After the crowd sale finished, `safe_withdrawal` function transfers the fund to the beneficiery,
contract owner in this example, if the sales target has been met.
However, if sales target failed, this function refunds to the contributors.

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
                self.FundTransfer(self.__addr_beneficiary.get(), self.__amount_raise.get(), False)
            else:
                self.__funding_goal_reached.set(False)

```


Syntax 
--------------
Type hinting is highly recommended for the input parameters and return value.
When querying Score's APIs, API specification is generated based on its type hints.
If type hints are not given, only function names will be returned.

Example)
```python
@external
def func1(arg1: int, arg2: str) -> object:
    pass
```

#### Exception handling
When you handle exceptions in your contract, it is recommended to inherit IconServiceBaseException.

#### IconScoreBase (The highest parent class)
Every DApp classes must inherit IconScoreBase. Contracts not derived from IconScoreBase can not be deployed.

#### \_\_init\_\_
This is a python init function. This function is called when the contract is loaded at each node.
Member variables should be declared here.
Also, parent's init function must be called as follows.

Example)
``` python
super().__init__(db)
```

#### on\_install
This function is called once when the conract is deployed for the first time, and will not be called again on contract update or deletion afterward.
This is the place where you initialize the state DB.

#### VarDB, DictDB, ArrayDB
VarDB, DictDB, ArrayDB are utility classes wrapping the state DB.
A key can be a number or characters, and value\_type can be int, str, Address, and bytes.
If the key does not exist, these classes return 0 when value\_type is int, return "" when str, return None when the value\_type is Address or bytes.
VarDB can be used to store simple key-value state, and DictDB behaves more like python dict.
DictDB does not maintain order, whereas ArrayDB, which supports length and iterator, maintains order.

##### VarDB('key', 'target db', 'return type')
Example) Setting 'theloop' for the key 'name' on the state DB:
```python
VarDB('name', db, value_type=str).set('theloop')
```
Example) Getting value by the key 'name':
```python
name = VarDB('name', db, value_type=str).get()
print(name) ## 'theloop'
```

##### DictDB('key', 'target db', 'return type', 'dict depth (default is 1)')
Example1) One-depth dict (test\_dict1['key']):
```python
test_dict1 = DictDB('test_dict1', db, value_type=int)
test_dict1['key'] = 1 ## set
print(test_dict1['key']) ## get 1

print(test_dict1['nonexistence_key']) # prints 0 (key does not exist and value_type=int)
```

Example2) Two-depth dict (test\_dict2\['key1']\['key2']):
```python
test_dict2 = DictDB('test_dict2', db, value_type=str, depth=2)
test_dict2['key1']['key2'] = 'a' ## set
print(test_dict2['key1']['key2']) ## get 'a'

print(test_dict2['key1']['nonexistent_key']) # prints "" (key does not exist and value_type=str)
```

If the depth is more than 2, dict[key] returns new DictDB.
Attempting to set a value to the wrong depth in the DictDB will raise an exception.    

Example3)
```python
test_dict3 = DictDB('test_dict3', db, value_type=int, depth=3)
test_dict3['key1']['key2']['key3'] = 1 ## ok
test_dict3['key1']['key2'] = 1 ## raise mismatch exception

test_dict2 = test_dict3['key']['key2']
test_dict2['key1'] = 1 ## ok
```

##### ArrayDB('key', 'target db', 'return type')
ArrayDB supports one dimensional array only.
ArrayDB supports put, get, and pop. Does not support insert (adding elements in the middle of array).

```python
test_array = ArrayDB('test_array', db, value_type=int)
test_array.put(0)
test_array.put(1)
test_array.put(2)
test_array.put(3)
print(len(test_array)) ## prints 4
print(test_array.pop()) ## prints 3
test_array[0] = 0 ## ok
# test_array[100] = 1 ## error
for e in test_array: ## ok
    print(e)
print(test_array[-1]) ## ok
# print(test_array[-100]) ## error
```

#### external decorator (@external)

Functions decorated with `@external` can be called from outside the contract.
These functions are registered on the exportable API list.
Any attempt to call a non-external function from outside the contract will fail.
If a function is decorated with readonly parameters, i.e., `@external(readonly=True)`,
the function will have read-only access to the state DB. This is similar to view keyward in Solidity.
If the read-only external function is also decorated with `@payable`, the function call will fail.
Duplicate declaration of `@external` will raise IconScoreException on import time.

#### payable decorator (@payable)
Only functions with `@payable` decorator are permitted to transfer icx coins.
Transfering 0 icx is accceptable. 
If msg.value (icx) is passed to non-payable function, the call will fail.

#### eventlog decorator (@eventlog)
Functions with `@eventlog` decorator will include logs in its TxResult as 'eventlogs'.
It is recommended to declare a function without implementation body. 
Even if the function has a body, it does not be executed.
When declaring a function, type hinting is a must. Without type hinting, transaction will fail.
If `indexed` parameter is set in the decorator, designated number of parameters in the order of declaration
will be indexed and included in the Bloom filter.  At most 3 parameters can be indexed.
Indexed parameters and non-indexed parameters are separately stored in TxResult.

Example)
```python
# Declaration
@eventlog
def FundTransfer1(self, backer: Address, amount: int, is_contribution: bool): pass

@eventlog(indexed=1) # The first param (backer) will be indexed
def FundTransfer2(self, backer: Address, amount: int, is_contribution: bool): pass

# Execution
self.FundTransfer1(self.msg.sender, amount, True)
self.FundTransfer2(self.msg.sender, amount, True)
```
Possible data types for function parameters are primitive types (int, str, bytes, bool, Address).
Array type parameter is not supported.

#### fallback
fallback function can not be decorated with `@external`. (i.e., fallback function is not allowed to be called by external contract or user.)
This fallback function is executed whenever the contract receives plain icx coins without data.
If the fallback function is not decorated with `@payable`, the icx coin transfers to the contract will fail.

#### InterfaceScore
InterfaceScore is an interface class used to invoke other Score's function.
This interface should be used instead of legacy 'call' function.
Usage syntax is as follows.

```python
class SampleTokenInterface(InterfaceScore):
    @interface
    def transfer(self, addr_to: Address, value: int) -> bool: pass
```
If other Score has the function that has the same signature as defined here with `@interface` decorator,
then that function can be invoked via InterfaceScore class object.
Like `@eventlog` decorator, it is recommended to declare a function without implementation body.
If there is a function body, it will be simply ignored.

Example)
You need to get an InterfaceScore object by using IconScoreBase's built-in function `create_interface_score('score address', 'interface class')`.
Using the object, you can invoke other Score's external function as if it is a local function call.

```python
sample_token_score = self.create_interface_score(self.__addr_token_score.get(), SampleTokenInterface)
sample_token_score.transfer(self.msg.sender, value)
```

Built-in fucntions
--------------
#### create\_interface\_score('score address', 'interface class') -> interface class instance
This function returns an object, through which you have an access to the designated Score's external functions.

#### revert(message: str) -> None
Developer can force a revert exception.

If the exception is thrown, all the changes in the state DB in current transaction will be rolled back.


Built-in properties
--------------

#### msg : Holds information of the account who called the Score.
* msg.sender :
Address of the account who called this funciton.
If other contact called this function, msg.sender points to the caller contract's address.
* msg.value :
Amount of icx that the sender attempts to transfer to the current Score.

#### tx : Transaction info.
* tx.origin : The account who created the transaction.
* tx.index : Transaction index.
* tx.hash : Transaction hash.
* tx.timestamp : Transaction creation time.
* tx.nonce : (optional) random value. 

#### block : Block info that contains current transaction.
* block.height : Block height.
* block.hash : Block hash.
* block.timestamp : Block creation time.

#### icx : An object used to transfer icx coin.
* icx.transfer(addr\_to(address), amount(integer)) -> bool
Transfers designated amount of icx coin to addr\_to.
If exception occurs during execution, the exception will be escalated.
Returns True if coin transer succeeds.

* icx.send(addr\_to(address), amount(integer)) -> bool
Sends designated amount of icx coin to addr\_to.
Basic behavior is same as transfer, the difference is that exception is caught inside the function.
Returns True when coin transfer succeeded, False when failed.

#### db : db instance used to access state DB.

#### address : Score address.

#### owner : Address of the account who deployed the contract.

#### now : Wrapping function of block.timestamp.
