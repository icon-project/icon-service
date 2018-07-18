ICON Smart Contract - SCORE
==================================

SCORE (Smart Contract on Reliable Environment) is a smart contract running on ICON network. A contract is a software that resides at a specific address on the blockchain and executed on ICON nodes. They are building blocks for DApp (Decentralized App). SCORE defines and exports interfaces, so that other SCORE can invoke its functions. The code is written in python, and to be uploaded as compressed binary data on the blockchain.

- Deployed SCORE can be updated. SCORE address remains the same after update. 
- SCORE code size is limited to 1MB after compression. (i.e., transaction size)
- SCORE must follow sandbox policy - file system access or network API calls are prohibited.

Simple Token & Crowd Sale
--------------

This document will explain how to write SCOREs with tbears framework.
Let's start by creating a simple token contract.

```
$ tbears init sample_token SampleToken
```

Above command will create `sample_token` folder, and generate `__init__.py`, `sample_token.py`, `package.json` files in the folder.  `sample_token.py` has a main class declaration whose name is `SampleToken`.  `__init__.py` has auto-generated statements for dynamic import. If folder structure changes, make sure you adjust the import statements.

When you deploy the contract, you can pass the amount of initial tokens to be issue to the parameter `initialSupply`, and in this example, 100% of initial tokens go to the contract owner. `transfer` function is given to transfer tokens to other accounts.

```python
class SampleToken(IconScoreBase, TokenStandard):

    _BALANCES = 'balances'
    _TOTAL_SUPPLY = 'total_supply'

    @eventlog(indexed=3)
    def Transfer(self, _from: Address, _to: Address, _value: int, _data: bytes):
        pass

    def __init__(self, db: IconScoreDatabase, _owner: Address) -> None:
        super().__init__(db, _owner)
        self._total_supply = VarDB(self._TOTAL_SUPPLY, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)

    def on_install(self, initialSupply: int, decimals: int) -> None:
        super().on_install()

        total_supply = initialSupply * 10 ** decimals
        Logger.debug(f'on_install: total_supply={total_supply}', TAG)

        self._total_supply.set(total_supply)
        self._balances[self.msg.sender] = total_supply

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def name(self) -> str:
        return "SampleToken"

    @external(readonly=True)
    def symbol(self) -> str:
        return "MST"

    @external(readonly=True)
    def decimals(self) -> int:
        return 18

    @external(readonly=True)
    def totalSupply(self) -> int:
        return self._total_supply.get()

    @external(readonly=True)
    def balanceOf(self, _owner: Address) -> int:
        return self._balances[_owner]

    @external
    def transfer(self, _to: Address, _value: int, _data: bytes=None):
        if _data is None:
            _data = b'None'
        self._transfer(self.msg.sender, _to, _value, _data)

    def _transfer(self, _from: Address, _to: Address, _value: int, _data: bytes):
        if self._balances[_from] < _value:
            self.revert("Out of balance")

        self._balances[_from] = self._balances[_from] - _value
        self._balances[_to] = self._balances[_to] + _value
        if _to.is_contract:
            crowdsale_score = self.create_interface_score(_to, CrowdSaleInterface)
            crowdsale_score.tokenFallback(_from, _value, _data)
        self.Transfer(_from, _to, _value, _data)
        Logger.debug(f'Transfer({_from}, {_to}, {_value}, {_data})', TAG)

```

Now, we are going to write a crowd sale contract using above token. Let's create a new project for the crowd sale contract. 

```
$ tbears init sample_crowdsale SampleCrowdSale
```

Exchange ratio to ICX is 1:1. Crowdsale target and its duration are set when the contract is first deployed.

`total_joiner_count` function returns the number of contributors, and `check_goal_reached` function tests if the crowdsale target has been met.

After the crowdsale finished, `safe_withdrawal` function transfers the fund to the beneficiery, contract owner in this example, if the sales target has been met. If sales target failed, each contributors can withdrow their contributions back.

```python
TAG = 'SampleCrowdSale'

class TokenInterface(InterfaceScore):
    @interface
    def transfer(self, _to: Address, _value: int, _data: bytes=None):
        pass

class SampleCrowdSale(IconScoreBase):
    _ADDR_BENEFICIARY = 'addr_beneficiary'
    _ADDR_TOKEN_SCORE = 'addr_token_score'
    _FUNDING_GOAL = 'funding_goal'
    _AMOUNT_RAISED = 'amount_raised'
    _DEAD_LINE = 'dead_line'
    _PRICE = 'price'
    _BALANCES = 'balances'
    _JOINER_LIST = 'joiner_list'
    _FUNDING_GOAL_REACHED = 'funding_goal_reached'
    _CROWDSALE_CLOSED = 'crowdsale_closed'

    @eventlog(indexed=3)
    def FundTransfer(self, backer: Address, amount: int, is_contribution: bool):
        pass

    @eventlog(indexed=2)
    def GoalReached(self, recipient: Address, total_amount_raised: int):
        pass

    def __init__(self, db: IconScoreDatabase, _owner: Address) -> None:
        super().__init__(db, _owner)

        self._addr_beneficiary = VarDB(self._ADDR_BENEFICIARY, db, value_type=Address)
        self._addr_token_score = VarDB(self._ADDR_TOKEN_SCORE, db, value_type=Address)
        self._funding_goal = VarDB(self._FUNDING_GOAL, db, value_type=int)
        self._amount_raised = VarDB(self._AMOUNT_RAISED, db, value_type=int)
        self._dead_line = VarDB(self._DEAD_LINE, db, value_type=int)
        self._price = VarDB(self._PRICE, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)
        self._joiner_list = ArrayDB(self._JOINER_LIST, db, value_type=Address)
        self._funding_goal_reached = VarDB(self._FUNDING_GOAL_REACHED, db, value_type=bool)
        self._crowdsale_closed = VarDB(self._CROWDSALE_CLOSED, db, value_type=bool)

    def on_install(self, fundingGoalInIcx: int, tokenScore: Address, durationInSeconds: int) -> None:
        super().on_install()

        Logger.debug(f'on_install: fundingGoalInIcx={fundingGoalInIcx}', TAG)
        Logger.debug(f'on_install: tokenScore={tokenScore}', TAG)
        Logger.debug(f'on_install: durationInSeconds={durationInSeconds}', TAG)

        one_second_in_microseconds = 1 * 10 ** 6
        now_seconds = self.now()
        icx_cost_of_each_token = 1

        self._addr_beneficiary.set(self.msg.sender)
        self._addr_token_score.set(tokenScore)
        self._funding_goal.set(fundingGoalInIcx)
        self._dead_line.set(now_seconds + durationInSeconds * one_second_in_microseconds)
        price = int(icx_cost_of_each_token)
        self._price.set(price)

        self._funding_goal_reached.set(False)
        self._crowdsale_closed.set(True)  # CrowdSale closed by default

    def on_update(self) -> None:
        super().on_update()

    @external
    def tokenFallback(self, _from: Address, _value: int, _data: bytes):
        if self.msg.sender == self._addr_token_score.get() \
                and _from == self.owner:
            # token supply to CrowdSale
            Logger.debug(f'tokenFallback: token supply = "{_value}"', TAG)
            if _value >= 0:
                self._crowdsale_closed.set(False)  # start CrowdSale hereafter
        else:
            # reject if this is an unrecognized token transfer
            Logger.debug(f'tokenFallback: REJECT transfer', TAG)
            self.revert('Unexpected token owner!')

    @payable
    def fallback(self):
        if self._crowdsale_closed.get():
            self.revert('CrowdSale is closed.')

        amount = self.msg.value
        self._balances[self.msg.sender] = self._balances[self.msg.sender] + amount
        self._amount_raised.set(self._amount_raised.get() + amount)
        value = int(amount / self._price.get())
        data = b'called from CrowdSale'
        token_score = self.create_interface_score(self._addr_token_score.get(), TokenInterface)
        token_score.transfer(self.msg.sender, value, data)

        if self.msg.sender not in self._joiner_list:
            self._joiner_list.put(self.msg.sender)

        self.FundTransfer(self.msg.sender, amount, True)
        Logger.debug(f'FundTransfer({self.msg.sender}, {amount}, True)', TAG)

    @external(readonly=True)
    def total_joiner_count(self) -> int:
        return len(self._joiner_list)

    def _after_dead_line(self) -> bool:
        Logger.debug(f'after_dead_line: now()       = {self.now()}', TAG)
        Logger.debug(f'after_dead_line: dead_line() = {self._dead_line.get()}', TAG)
        return self.now() >= self._dead_line.get()

    @external
    def check_goal_reached(self):
        if self._after_dead_line():
            if self._amount_raised.get() >= self._funding_goal.get():
                self._funding_goal_reached.set(True)
                self.GoalReached(self._addr_beneficiary.get(), self._amount_raised.get())
                Logger.debug(f'Goal reached!', TAG)
            self._crowdsale_closed.set(True)

    @external
    def safe_withdrawal(self):
        if self._after_dead_line():
            # each contributor can withdraw the amount they contributed 
            # if the goal was not reached
            if not self._funding_goal_reached.get():
                amount = self._balances[self.msg.sender]
                self._balances[self.msg.sender] = 0
                if amount > 0:
                    if self.icx.send(self.msg.sender, amount):
                        self.FundTransfer(self.msg.sender, amount, False)
                        Logger.debug(f'FundTransfer({self.msg.sender}, {amount}, False)', TAG)
                    else:
                        self._balances[self.msg.sender] = amount

            if self._funding_goal_reached.get() and self._addr_beneficiary.get() == self.msg.sender:
                if self.icx.send(self._addr_beneficiary.get(), self._amount_raised.get()):
                    self.FundTransfer(self._addr_beneficiary.get(), self._amount_raised.get(), False)
                    Logger.debug(f'FundTransfer({self._addr_beneficiary.get()},'
                                 f'{self._amount_raised.get()}, False)', TAG)
                else:
                    # if the transfer to beneficiary fails, unlock contributors balance
                    Logger.debug(f'Failed to send to beneficiary!', TAG)
                    self._funding_goal_reached.set(False)

```



Syntax 
--------------

#### Type hints

Type hinting is highly recommended for the input parameters and return value. When querying Score's APIs, API specification is generated based on its type hints. If type hints are not given, only function names will return.

Example)
```python
@external
def func1(arg1: int, arg2: str) -> object:
    pass
```

#### Exception handling
When you handle exceptions in your contract, it is recommended to inherit `IconServiceBaseException`.

#### IconScoreBase (The highest parent class)
Every classes must inherit `IconScoreBase`. Contracts not derived from `IconScoreBase` can not be deployed.

#### \_\_init\_\_
This is a python init function. This function is called when the contract is loaded at each node. Member variables should be declared here. 

Also, parent's init function must be called as follows.

Example)
``` python
super().__init__(db)
```

#### on\_install
This function is called when the contract is deployed for the first time, and will not be called again on contract update or deletion afterward.
This is the place where you initialize the state DB.

#### VarDB, DictDB, ArrayDB
VarDB, DictDB, ArrayDB are utility classes wrapping the state DB.
A `key` can be a number or characters, and `value_type` can be `int`, `str`, `Address`, and `bytes`.
If the `key` does not exist, these classes return 0 when `value_type` is `int`, return "" when `str`, return None when the `value_type` is `Address` or `bytes`.
VarDB can be used to store simple key-value state, and DictDB behaves more like python dict.
DictDB does not maintain order, whereas ArrayDB, which supports length and iterator, maintains order.

##### VarDB('key', 'target db', 'return type')
Example) Setting `theloop` for the key `name` on the state DB:
```python
VarDB('name', db, value_type=str).set('theloop')
```
Example) Getting value by the key `name`:
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
If other SCORE has the function that has the same signature as defined here with `@interface` decorator,
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
Transfers designated amount of icx coin to `addr_to`.
If exception occurs during execution, the exception will be escalated.
Returns True if coin transer succeeds.

* icx.send(addr\_to(address), amount(integer)) -> bool
Sends designated amount of icx coin to `addr_to`.
Basic behavior is same as transfer, the difference is that exception is caught inside the function.
Returns True when coin transfer succeeded, False when failed.

#### db : db instance used to access state DB.

#### address : Score address.

#### owner : Address of the account who deployed the contract.

#### now : Wrapping function of block.timestamp.
