Let's create a simple token.
==================================

Overview
--------------
```
$ tbears init {project_name} {class_name}
```
Above command will create {project_name} folder,
and generate \_\_init\_\_.py, {project_name}.py, package.json files in the folder.<br/>
{project_name}.py has a main class declaration whose name is {class_name}.<br/>
\_\_init\_\_.py has auto-generated statements for dynamic import.
If folder structure changes, make sure you adjust the import statements.<br/>


<br/>
This exmaple generates 1,000 initial tokens, and 100% of tokens go to the contract owner.<br/>  
Transfer function is given to transfer tokens to other account.<br/>

```python
class SampleToken(IconScoreBase):

    __BALANCES = 'balances'
    __TOTAL_SUPPLY = 'total_supply'

    @eventlog(indexed=3)
    def Transfer(self, addr_from: Address, addr_to: Address, value: int): pass

    def __init__(self, db: IconScoreDatabase, addr_owner: Address) -> None:
        super().__init__(db, addr_owner)
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
Now, we are going to write a crowd sale contract using above token.<br/>
Exchange ratio to icx is 1:1, and the crowd sale duration is 1 minute.<br/>
total_joiner_count function returns the number of contributors, and check_goal_reached function tests if the crowd sale target has been met.<br/>
After the crowd sale finished, safe_withdrawal function transfers the fund 
to the beneficiery, contract owner in this example, if the sales target has been met. 
However, if sales target failed, this function refunds to the contributors.<br/>

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

    def __init__(self, db: IconScoreDatabase, owner: Address) -> None:
        super().__init__(db, owner)

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


Syntax 
--------------
Type hinting is highly recommended for the input parameters and return value.<br/>
When querying Score's APIs, API specification is generated based on its type hints.<br/>
If type hints are not given, only function names will be return.<br/> 

Example)
```python
@external
def func1(arg1: int, arg2: str) -> object:
    pass
```

#### Exception handling

When you handle exceptions in your contract, 
it is recommended to inherit IconServiceBaseException.<br/> 

#### The highest parent class (IconScoreBase)
Every DApp classes must inherit IconScoreBase. Contracts not derived from IconScoreBase can not be deployed.<br/>

#### \_\_init\_\_
This is a python init function. This function is called when the contract is loaded at each node.<br/>
Member variables should be declared here.<br/>
Also, parent's init function must be called as follows.<br/>   

Example)
``` python
super().__init__(db, owner)
```

#### on_install
This function is called once when the conract is deployed for the first time, and will not be called again on contract update or deletion afterward.<br/>
This is the place where you initialize state DB.<br/> 

#### VarDB, DictDB, ArrayDB
VarDB, DictDB, ArrayDB are utility classes wrapping state DB.<br/> 
A key can be number or characters, and value_type can be int, str, Address, and bytes. <br/>
If the key does not exist, these classes return 0 when value_type is int, return "" when str, return None when the value_type is Address or bytes.<br/>
VarDB can be used to store simple key-value state, whereas DictDB behaves more like python dict. <br/> 
DictDB does not maintain order. 
ArrayDB, which supports length and iterator, maintains order. <br/>

##### VarDB('key', 'target db', 'return type')<br/>
Example) Setting 'theloop' for the key 'name' on the state DB:<br/>
```python
VarDB('name', db, value_type=str).set('theloop')
```
Getting value by the key 'name':<br/>
```python
name = VarDB('name', db, value_type=str).get()
print(name) ##'theloop'
```

##### DictDB('key', 'target db', 'return type', 'dict depth (default is 1)')<br/>
Example1) One-depth dict (test_dict1['key']): <br/>
```python
test_dict1 = DictDB('test_dict1', db, value_type=int)
test_dict1['key'] = 1 ## set
print(test_dict1['key']) ## get 1

print(test_dict1['nonexistence_key']) # prins 0 (key does not exist and value_type=int)
```

Example2) Two-depth dict (test_dict2['key1']['key2']):<br/>
```python
test_dict2 = DictDB('test_dict2', db, value_type=str, depth=2)
test_dict2['key1']['key2'] = 'a' ## set
print(test_dict2['key1']['key2']) ## get 'a'

print(test_dict2['key1']['nonexistent_key']) # prints "" (key does not exist and value_type=str)
```

If the depth is more than 2, dict[key] returns new DictDB.<br/>
Attempting to set a value to the wrong depth in the DictDB will raise an exception.    

Example3)<br/>
```python
test_dict3 = DictDB('test_dict3', db, value_type=int, depth=3)
test_dict3['key1']['key2']['key3'] = 1  # ok
test_dict3['key1']['key2'] = 1  # raise mismatch exception

test_dict2 = test_dict3['key']['key2']
test_dict2['key1'] = 1  # ok
```

##### ArrayDB('key', 'target db', 'return type')<br/>
ArrayDB supports one demensional array only.<br/>
ArrayDB supports put, get, and pop. Does not support insert (adding elements in the middle of array).<br/>

```python
test_array = ArrayDB('test_array', db, value_type=int)
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

#### external decorator (@external)

Functions decorated with @external can be called from outside the contract. 
These functions are registered on the exportable API list.<br/>
Any attempt to call a non-external function from outside the contract will fail.<br/>
If a function is decorated with readonly parameters, i.e., @external(readonly=True), 
the function will have read-only access to the state DB. This is similar to view keyward in Solidity.<br/>
If the read-only external function is also decorated with @payable, the function call will fail.<br/>
Duplicate declaration of @external will raise IconScoreException on import time.<br/>

#### payable decorator (@payable)
Only functions with @payable decorator are permitted to transfer icx coins.<br/>
Transfering 0 icx is accceptable. 
If msg.value (icx) is passed to non-payable function, the call will fail.<br/>

#### eventlog decorator (@eventlog)
Functions with @eventlog decorator will include logs in its TxResult as 'eventlogs'. <br/>
It is recommended to declare a function without implementation body. 
Even if the function has a body, it does not execute. <br/>
When declaring a function, type hinting is a must. Without type hinting, transaction will fail. <br/>
If 'indexed' parameter is set in the decorator, designated number of parameters in the order of declaration will be indexed and included in the Bloom filter. At most 3 parameters can be indexed. 
Indexed parameters and non-indexed parameters are separately stored in TxResult.<br/>

Example)<br/>
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
Array type parameter is not supported.<br/>

#### fallback
fallback function can not be decorated with @external. (i.e., fallback function is not allowed to be called by external contract or user.)<br/>
This fallback function is executed whenever the contract receives plain icx coins without data.<br/>
If the fallback function is not decorated with @payable, then the transaction will fail because it can not modify state DB.<br/>  

#### InterfaceScore
InterfaceScore is an interface class used to invoke other Score's function. 
This interface should be used instead of legacy 'call' function.<br/>
Usage syntax is as follows.<br/>

```python
class SampleTokenInterface(InterfaceScore):
    @interface
    def transfer(self, addr_to: Address, value: int) -> bool: pass
```
If other Score has the function that has the same signature as defined here with @interface decorator, 
then that function can be invoked via InterfaceScore class object.<br/>
Like @eventlog decorator, it is recommended to declare a function without implementation body. 
If there is a function body, it will be simply ignored. <br/>   

Example)<br/>
Getting InterfaceScore object using IconScoreBase's built-in function create_interface_score('score address', 'interface class'). <br/>
Using the object, you can invoke other Score's external function as if it is a local function call.<br/> 

```python
sample_token_score = self.create_interface_score(self.__addr_token_score.get(), SampleTokenInterface)
sample_token_score.transfer(self.msg.sender, value)
```

Built-in fucntions
--------------
#### create_interface_score(addr_to(address), interface_cls(interface class)) -> interface_cls instance
This function returns an object, through which you have an access to the designated Score's (address_to) external functions.

#### [legacy] call(addr_to(address), func_name, kw_dict(function params)) -> calling function's return value
Legacy method used to call other Score's function. This has been relaced by InterfaceScore. 

#### revert(message: str) -> None
Developer can force a revert exception.<br/>
If the exception is thrown, all the changes in the state DB in current transaction will be rolled back.<br/>  


Built-in properties
--------------

#### msg : Holds information of the account who called the Score.
* msg.sender :
Address of the account who called this funciton. <br/>
If other contact called this function, msg.sender points to the caller contract's address. <br/>  
* msg.value :
Amount of icx that the sender attempts to transfer to the current Score.<br/>  

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
* icx.transfer(addr_to(address), amount(integer)) -> bool<br/>
Transfers designated amount of icx coin to addr_to.<br/>
If exception occurs during execution, the exception will be escalated.<br/>
Returns True if coin transer succeeds.<br/>

* icx.send(addr_to(address), amount(integer)) -> bool<br/>
Sends designated amount of icx coin to addr_to.<br/>
Basic behavior is same as transfer, the difference is that exception is caught inside the function.<br/>
Returns True when coin transfer succeeded, False when failed.<br/>

#### db : db instance used to access state DB.

#### address : Score address.

#### owner : Address of the account who deployed the contract.

#### now : Wrapping function of block.timestamp.
