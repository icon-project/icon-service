Syntax
======

Type hints
^^^^^^^^^^

Type hinting is highly recommended for the input parameters and return
value. When querying SCORE’s APIs, API specification is generated based
on its type hints. If type hints are not given, only function names will
return.

Example)

.. code:: python

   @external(readonly=True)
   def func1(arg1: int, arg2: str) -> int:
       return 100

Possible data types for function parameters are ``int``, ``str``,
``bytes``, ``bool``, ``Address``. ``List`` and ``Dict`` type parameters
are not supported yet.

Returning types can be ``int``, ``str``, ``bytes``, ``bool``,
``Address``, ``List``, ``Dict``.

Exception handling
^^^^^^^^^^^^^^^^^^

When you handle exceptions in your contract, it is recommended to use `revert` function rather than using an exception inherited from `IconServiceBaseException`.

IconScoreBase (The highest parent class)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every classes must inherit ``IconScoreBase``. Contracts not derived from
``IconScoreBase`` can not be deployed.

\__init_\_
^^^^^^^^^^

This is a python init function. This function is called when the
contract is loaded at each node.

Member variables can be declared here, however, Declaring member
variables which not managed by states is prohibited. Utilities of DB
such as VarDB, DictDB, ArrayDB can be declared here as a member variable
as follows.

Example)

.. code:: python

   self._total_supply = VarDB(self._TOTAL_SUPPLY, db, value_type=int)
   self._decimals = VarDB(self._DECIMALS, db, value_type=int)
   self._balances = DictDB(self._BALANCES, db, value_type=int)

Also, parent’s init function must be called as follows.

Example)

.. code:: python

   super().__init__(db)

on_install
^^^^^^^^^^

This function is called when the contract is deployed for the first
time, and will not be called again on contract update or deletion
afterward. This is the place where you initialize the state DB.

VarDB, DictDB, ArrayDB
^^^^^^^^^^^^^^^^^^^^^^

VarDB, DictDB, ArrayDB are utility classes wrapping the state DB. A
``key`` can be a number or characters, and ``value_type`` can be
``int``, ``str``, ``Address``, and ``bytes``. If the ``key`` does not
exist, these classes return 0 when ``value_type`` is ``int``, return ""
when ``str``, return ``None`` when the ``value_type`` is ``Address`` or
``bytes``. VarDB can be used to store simple key-value state, and DictDB
behaves more like python dict. DictDB does not maintain order, whereas
ArrayDB, which supports length and iterator, maintains order.

VarDB(‘key’, ‘target db’, ‘return type’)
''''''''''''''''''''''''''''''''''''''''

Example) Setting ``theloop`` for the key ``name`` on the state DB:

.. code:: python

   VarDB('name', db, value_type=str).set('theloop')

Example) Getting value by the key ``name``:

.. code:: python

   name = VarDB('name', db, value_type=str).get()
   print(name) ## 'theloop'

DictDB(‘key’, ‘target db’, ‘return type’, ‘dict depth (default is 1)’)
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Example 1) One-depth dict (test_dict1[‘key’]):

.. code:: python

   test_dict1 = DictDB('test_dict1', db, value_type=int)
   test_dict1['key'] = 1 ## set
   print(test_dict1['key']) ## get 1

   print(test_dict1['nonexistence_key']) # prints 0 (key does not exist and value_type=int)

Example 2) Two-depth dict (test_dict2[‘key1’][‘key2’]):

.. code:: python

   test_dict2 = DictDB('test_dict2', db, value_type=str, depth=2)
   test_dict2['key1']['key2'] = 'a' ## set
   print(test_dict2['key1']['key2']) ## get 'a'

   print(test_dict2['key1']['nonexistent_key']) # prints "" (key does not exist and value_type=str)

If the depth is more than 2, dict[key] returns new DictDB. Attempting to
set a value to the wrong depth in the DictDB will raise an exception.

Example 3)

.. code:: python

   test_dict3 = DictDB('test_dict3', db, value_type=int, depth=3)
   test_dict3['key1']['key2']['key3'] = 1 ## ok
   test_dict3['key1']['key2'] = 1 ## raise mismatch exception

   test_dict2 = test_dict3['key']['key2']
   test_dict2['key1'] = 1 ## ok

ArrayDB(‘key’, ‘target db’, ‘return type’)
''''''''''''''''''''''''''''''''''''''''''

ArrayDB supports one dimensional array only. ArrayDB supports put, get,
and pop. Does not support insert (adding elements in the middle of
array).

.. code:: python

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

external decorator (@external)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Functions decorated with ``@external`` can be called from outside the
contract. These functions are registered on the exportable API list. Any
attempt to call a non-external function from outside the contract will
fail. If a function is decorated with ‘readonly’ parameters, i.e.,
``@external(readonly=True)``, the function will have read-only access to
the state DB. This is similar to view keyword in Solidity. If the
read-only external function is also decorated with ``@payable``, the
function call will fail. Duplicate declaration of ``@external`` will
raise IconScoreException on import time.

payable decorator (@payable)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Only functions with ``@payable`` decorator are permitted to transfer icx
coins. Transferring 0 icx is acceptable. If msg.value (icx) is passed to
non-payable function, the call will fail.

eventlog decorator (@eventlog)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Functions with ``@eventlog`` decorator will include logs in its TxResult
as ‘eventlogs’. It is recommended to declare a function without
implementation body. Even if the function has a body, it does not be
executed. When declaring a function, type hinting is a must. Without
type hinting, transaction will fail. The default value for the parameter
can be set.

If ``indexed`` parameter is set in the decorator, designated number of
parameters in the order of declaration will be indexed and included in
the Bloom filter. At most 3 parameters can be indexed, And index can’t
exceed the number of parameters(will raise an error). Indexed parameters
and non-indexed parameters are separately stored in TxResult.

Example)

.. code:: python

   # Declaration
   @eventlog
   def FundTransfer1(self, _backer: Address, _amount: int, _isContribution: bool): pass

   @eventlog(indexed=1) # The first param (backer) will be indexed
   def FundTransfer2(self, _backer: Address, _amount: int, _isContribution: bool): pass

   # Execution
   self.FundTransfer1(self.msg.sender, amount, True)
   self.FundTransfer2(self.msg.sender, amount, True)

Possible data types for function parameters are primitive types (int,
str, bytes, bool, Address). Array, Dictionary and None type parameter is
not supported.

fallback
^^^^^^^^

fallback function can not be decorated with ``@external``. (i.e.,
fallback function is not allowed to be called by external contract or
user.) This fallback function is executed whenever the contract receives
plain icx coins without data. If the fallback function is not decorated
with ``@payable``, the icx coin transfers to the contract will fail.

InterfaceScore
^^^^^^^^^^^^^^

InterfaceScore is an interface class used to invoke other SCORE’s
function. This interface should be used instead of legacy ‘call’
function. Usage syntax is as follows.

.. code:: python

   class TokenInterface(InterfaceScore):
       @interface
       def transfer(self, addr_to: Address, value: int) -> bool: pass

If other SCORE has the function that has the same signature as defined
here with ``@interface`` decorator, then that function can be invoked
via InterfaceScore class object. Like ``@eventlog`` decorator, it is
recommended to declare a function without implementation body. If there
is a function body, it will be simply ignored.

Example) You need to get an InterfaceScore object by using
IconScoreBase’s built-in function
``create_interface_score('score address', 'interface class')``. Using
the object, you can invoke other SCORE’s external function as if it is a
local function call.

.. code:: python

   token_score = self.create_interface_score(self._addr_token_score.get(), TokenInterface)
   token_score.transfer(self.msg.sender, value)
