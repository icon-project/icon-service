ICON Smart Contract - SCORE
==================================

SCORE (Smart Contract on Reliable Environment) is a smart contract running on ICON network. A contract is a software that resides at a specific address on the blockchain and executed on ICON nodes. They are building blocks for DApp (Decentralized App). SCORE defines and exports interfaces, so that other SCORE can invoke its functions. The code is written in python, and is uploaded as compressed binary data on the blockchain.

- Deployed SCORE can be updated. SCORE address remains the same after update. 
- SCORE code size is limited to about 64 KB (actually bounded by the maximum stepLimit value during its deploy transaction) after compression.
- SCORE must follow sandbox policy - file system access or network API calls are prohibited.

Token & Crowdsale
--------------

This document will explain how to write SCOREs with T-Bears framework.
Let's start by creating a simple token contract. You can create an empty project using `init` command. Suppose your project name is 'sample_token' and the main class name is 'SampleToken'.

```
$ tbears init sample_token SampleToken
```

Above command will create a project folder, `sample_token`, and generate `__init__.py`, `sample_token.py`, and `package.json` files in the folder.  `sample_token.py` has the main class declaration whose name is `SampleToken`. You need to implement `SampleToken` class. 

IRC-2 standard defines the common behavior of tokens running on ICON. IRC-2 compliant token must implement following methods. The specification is here, [IRC-2](https://github.com/icon-project/IIPs/blob/master/IIPS/iip-2.md). 

```python
@external(readonly=True)
def name(self) -> str:
    
@external(readonly=True)
def symbol(self) -> str:

@external(readonly=True)
def decimals(self) -> int:
    
@external(readonly=True)
def totalSupply(self) -> int:

@external(readonly=True)
def balanceOf(self, _owner: Address) -> int:
    
@external
def transfer(self, _to: Address, _value: int, _data: bytes=None):
```

Below is a complete token implementation. You can copy and paste it to fill your `sample_token.py`. Note that `TokenFallbackInterface` is declared in the beginning to interact with `SampleCrowdsale` contract defined later. (In fact, `tbears samples` command will generate the two sample projects, `standard_token` and `standard_crowdsale`, with the complete source code provided. However, we used `init` command here to illustrate how to create a new project.)

When you deploy the contract, `on_install` method is called. You can pass the amount of initial tokens to the parameter `initialSupply`, and, in this example, 100% of initial tokens go to the contract owner. 

```python
from iconservice import *

TAG = 'SampleToken'


# An interface of ICON Token Standard, IRC-2
class TokenStandard(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def symbol(self) -> str:
        pass

    @abstractmethod
    def decimals(self) -> int:
        pass

    @abstractmethod
    def totalSupply(self) -> int:
        pass

    @abstractmethod
    def balanceOf(self, _owner: Address) -> int:
        pass

    @abstractmethod
    def transfer(self, _to: Address, _value: int, _data: bytes = None):
        pass


# An interface of tokenFallback.
# Receiving SCORE that has implemented this interface can handle
# the receiving or further routine.
class TokenFallbackInterface(InterfaceScore):
    @interface
    def tokenFallback(self, _from: Address, _value: int, _data: bytes):
        pass


class SampleToken(IconScoreBase, TokenStandard):

    _BALANCES = 'balances'
    _TOTAL_SUPPLY = 'total_supply'
    _DECIMALS = 'decimals'

    @eventlog(indexed=3)
    def Transfer(self, _from: Address, _to: Address, _value: int, _data: bytes):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._total_supply = VarDB(self._TOTAL_SUPPLY, db, value_type=int)
        self._decimals = VarDB(self._DECIMALS, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)

    def on_install(self, _initialSupply: int, _decimals: int) -> None:
        super().on_install()

        if _initialSupply < 0:
            revert("Initial supply cannot be less than zero")

        if _decimals < 0:
            revert("Decimals cannot be less than zero")

        total_supply = _initialSupply * 10 ** _decimals
        Logger.debug(f'on_install: total_supply={total_supply}', TAG)

        self._total_supply.set(total_supply)
        self._decimals.set(_decimals)
        self._balances[self.msg.sender] = total_supply

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def name(self) -> str:
        return "SampleToken"

    @external(readonly=True)
    def symbol(self) -> str:
        return "ST"

    @external(readonly=True)
    def decimals(self) -> int:
        return self._decimals.get()

    @external(readonly=True)
    def totalSupply(self) -> int:
        return self._total_supply.get()

    @external(readonly=True)
    def balanceOf(self, _owner: Address) -> int:
        return self._balances[_owner]

    @external
    def transfer(self, _to: Address, _value: int, _data: bytes = None):
        if _data is None:
            _data = b'None'
        self._transfer(self.msg.sender, _to, _value, _data)

    def _transfer(self, _from: Address, _to: Address, _value: int, _data: bytes):

        # Checks the sending value and balance.
        if _value < 0:
            revert("Transferring value cannot be less than zero")
        if self._balances[_from] < _value:
            revert("Out of balance")

        self._balances[_from] = self._balances[_from] - _value
        self._balances[_to] = self._balances[_to] + _value

        if _to.is_contract:
            # If the recipient is SCORE,
            #   then calls `tokenFallback` to hand over control.
            recipient_score = self.create_interface_score(_to, TokenFallbackInterface)
            recipient_score.tokenFallback(_from, _value, _data)

        # Emits an event log `Transfer`
        self.Transfer(_from, _to, _value, _data)
        Logger.debug(f'Transfer({_from}, {_to}, {_value}, {_data})', TAG)


```

Now, we are going to write a crowdsale contract using above token. Let's create a new project for the crowdsale contract. 

```
$ tbears init sample_crowdsale SampleCrowdsale
```

Our crowdsale contract will do the following.

- Exchange ratio to ICX is 1:1. Crowdsale target, token contract address, and its duration are set when the contract is first deployed.
- `total_joiner_count` function returns the number of contributors, and `check_goal_reached` function tests if the crowdsale target has been met.
- After the crowdsale finished, `safe_withdrawal` function transfers the fund to the beneficiary, contract owner in this example, if the sales target has been met. If sales target failed, each contributors can withdraw their contributions back.

Again, complete source is given below. Note that crowdsale duration is given in number of blocks, because SCORE logic must be deterministic across nodes, thus it must not rely on clock time.

```python
from iconservice import *

TAG = 'SampleCrowdsale'


# An interface of token to give a reward to anyone who contributes
class TokenInterface(InterfaceScore):
    @interface
    def transfer(self, _to: Address, _value: int, _data: bytes=None):
        pass


class SampleCrowdsale(IconScoreBase):

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

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

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

    def on_install(self, _fundingGoalInIcx: int, _tokenScore: Address, _durationInBlocks: int) -> None:
        """
        Called when this SCORE first deployed.

        :param _fundingGoalInIcx: The funding goal of this crowdsale, in ICX
        :param _tokenScore: SCORE address of token that will be used for the rewards
        :param _durationInBlocks: the sale duration is given in number of blocks
        """
        super().on_install()

        Logger.debug(f'on_install: fundingGoalInIcx={_fundingGoalInIcx}', TAG)
        Logger.debug(f'on_install: tokenScore={_tokenScore}', TAG)
        Logger.debug(f'on_install: durationInBlocks={_durationInBlocks}', TAG)

        if _fundingGoalInIcx < 0:
            revert("Funding goal cannot be less than zero")

        if _durationInBlocks < 0:
            revert("Duration cannot be less than zero")

        # The exchange ratio to ICX is 1:1
        icx_cost_of_each_token = 1

        self._addr_beneficiary.set(self.msg.sender)
        self._addr_token_score.set(_tokenScore)
        self._funding_goal.set(_fundingGoalInIcx)
        self._dead_line.set(self.block.height + _durationInBlocks)
        price = int(icx_cost_of_each_token)
        self._price.set(price)

        self._funding_goal_reached.set(False)
        self._crowdsale_closed.set(True)  # Crowdsale closed by default

    def on_update(self) -> None:
        super().on_update()

    @external
    def tokenFallback(self, _from: Address, _value: int, _data: bytes):
        """
        Implements `tokenFallback` in order for the SCORE
        to receive initial tokens to reward to the contributors
        """

        # Checks if the caller is a Token SCORE address that this SCORE is interested in.
        if self.msg.sender != self._addr_token_score.get():
            revert("Unknown token address")

        # Depositing tokens can only be done by owner
        if _from != self.owner:
            revert("Invalid sender")

        if _value < 0:
            revert("Depositing value cannot be less than zero")

        # start Crowdsale hereafter
        self._crowdsale_closed.set(False)
        Logger.debug(f'tokenFallback: token supply = "{_value}"', TAG)

    @payable
    def fallback(self):
        """
        Called when anyone sends funds to the SCORE.
        This SCORE regards it as a contribution.
        """
        if self._crowdsale_closed.get():
            revert('Crowdsale is closed.')

        # Accepts the contribution
        amount = self.msg.value
        self._balances[self.msg.sender] = self._balances[self.msg.sender] + amount
        self._amount_raised.set(self._amount_raised.get() + amount)
        value = int(amount / self._price.get())
        data = b'called from Crowdsale'

        # Gives tokens to the contributor as a reward
        token_score = self.create_interface_score(self._addr_token_score.get(), TokenInterface)
        token_score.transfer(self.msg.sender, value, data)

        if self.msg.sender not in self._joiner_list:
            self._joiner_list.put(self.msg.sender)

        self.FundTransfer(self.msg.sender, amount, True)
        Logger.debug(f'FundTransfer({self.msg.sender}, {amount}, True)', TAG)

    @external(readonly=True)
    def totalJoinerCount(self) -> int:
        """
        Returns the number of contributors.

        :return: the number of contributors
        """
        return len(self._joiner_list)

    def _after_dead_line(self) -> bool:
        # Checks if it has been reached to the deadline block
        Logger.debug(f'after_dead_line: block.height = {self.block.height}', TAG)
        Logger.debug(f'after_dead_line: dead_line()  = {self._dead_line.get()}', TAG)
        return self.block.height >= self._dead_line.get()

    @external
    def checkGoalReached(self):
        """
        Checks if the goal has been reached and ends the campaign.
        """
        if self._after_dead_line():
            if self._amount_raised.get() >= self._funding_goal.get():
                self._funding_goal_reached.set(True)
                self.GoalReached(self._addr_beneficiary.get(), self._amount_raised.get())
                Logger.debug(f'Goal reached!', TAG)
            self._crowdsale_closed.set(True)

    @external
    def safeWithdrawal(self):
        """
        Withdraws the funds.

        If the funding goal has been reached, sends the entire amount to the beneficiary.
        If the goal was not reached, each contributor can withdraw the amount they contributed.
        """
        if self._after_dead_line():
            # each contributor can withdraw the amount they contributed if the goal was not reached
            if not self._funding_goal_reached.get():
                amount = self._balances[self.msg.sender]
                self._balances[self.msg.sender] = 0
                if amount > 0:
                    if self.icx.send(self.msg.sender, amount):
                        self.FundTransfer(self.msg.sender, amount, False)
                        Logger.debug(f'FundTransfer({self.msg.sender}, {amount}, False)', TAG)
                    else:
                        self._balances[self.msg.sender] = amount

            # The sales target has been met. Owner can withdraw the contribution.
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

Type hinting is highly recommended for the input parameters and return value. When querying SCORE's APIs, API specification is generated based on its type hints. If type hints are not given, only function names will return.

Example)
```python
@external(readonly=True)
def func1(arg1: int, arg2: str) -> int:
    return 100
```

Possible data types for function parameters are `int`, `str`, `bytes`, `bool`, `Address`.
`List` and `Dict` type parameters are not supported yet.

Returning types can be `int`, `str`, `bytes`, `bool`, `Address`, `List`, `Dict`.

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
If the `key` does not exist, these classes return 0 when `value_type` is `int`, return "" when `str`, return `None` when the `value_type` is `Address` or `bytes`.
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
Example 1) One-depth dict (test\_dict1['key']):
```python
test_dict1 = DictDB('test_dict1', db, value_type=int)
test_dict1['key'] = 1 ## set
print(test_dict1['key']) ## get 1

print(test_dict1['nonexistence_key']) # prints 0 (key does not exist and value_type=int)
```

Example 2) Two-depth dict (test\_dict2\['key1']\['key2']):
```python
test_dict2 = DictDB('test_dict2', db, value_type=str, depth=2)
test_dict2['key1']['key2'] = 'a' ## set
print(test_dict2['key1']['key2']) ## get 'a'

print(test_dict2['key1']['nonexistent_key']) # prints "" (key does not exist and value_type=str)
```

If the depth is more than 2, dict[key] returns new DictDB.
Attempting to set a value to the wrong depth in the DictDB will raise an exception.    

Example 3)
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

Functions decorated with `@external` can be called from outside the contract. These functions are registered on the exportable API list.
Any attempt to call a non-external function from outside the contract will fail.
If a function is decorated with 'readonly' parameters, i.e., `@external(readonly=True)`, the function will have read-only access to the state DB. This is similar to view keyword in Solidity.
If the read-only external function is also decorated with `@payable`, the function call will fail.
Duplicate declaration of `@external` will raise IconScoreException on import time.

#### payable decorator (@payable)
Only functions with `@payable` decorator are permitted to transfer icx coins.
Transferring 0 icx is acceptable.
If msg.value (icx) is passed to non-payable function, the call will fail.

#### eventlog decorator (@eventlog)
Functions with `@eventlog` decorator will include logs in its TxResult as 'eventlogs'.
It is recommended to declare a function without implementation body. Even if the function has a body, it does not be executed.
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
InterfaceScore is an interface class used to invoke other SCORE's function.
This interface should be used instead of legacy 'call' function.
Usage syntax is as follows.

```python
class TokenInterface(InterfaceScore):
    @interface
    def transfer(self, addr_to: Address, value: int) -> bool: pass
```
If other SCORE has the function that has the same signature as defined here with `@interface` decorator,
then that function can be invoked via InterfaceScore class object.
Like `@eventlog` decorator, it is recommended to declare a function without implementation body.
If there is a function body, it will be simply ignored.

Example)
You need to get an InterfaceScore object by using IconScoreBase's built-in function `create_interface_score('score address', 'interface class')`.
Using the object, you can invoke other SCORE's external function as if it is a local function call.

```python
token_score = self.create_interface_score(self._addr_token_score.get(), TokenInterface)
token_score.transfer(self.msg.sender, value)
```

Built-in functions
--------------
#### create\_interface\_score('score address', 'interface class') -> interface class instance
This function returns an object, through which you have an access to the designated SCORE's external functions.

#### revert(message: str) -> None
Developer can force a revert exception.

If the exception is thrown, all the changes in the state DB in current transaction will be rolled back.


Built-in properties
--------------

#### msg : Holds information of the account who called the SCORE.
* msg.sender :
Address of the account who called this function.
If other contact called this function, msg.sender points to the caller contract's address.
* msg.value :
Amount of icx that the sender attempts to transfer to the current SCORE.

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
Returns True if coin transfer succeeds.

* icx.send(addr\_to(address), amount(integer)) -> bool
Sends designated amount of icx coin to `addr_to`.
Basic behavior is same as transfer, the difference is that exception is caught inside the function.
Returns True when coin transfer succeeded, False when failed.

#### db : db instance used to access state DB.

#### address : SCORE address.

#### owner : Address of the account who deployed the contract.

#### now : Wrapping function of block.timestamp.
