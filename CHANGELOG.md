# ChangeLog

## 1.1.2.11 - 2018.12.10

* Revision: 3
* Replace thread local storage with generator in ArrayDB.
* Add parameter type check to revert function.


## 1.1.2 - 2018.10.15

* Revision: 2
* Fix import module loading error on ScorePackageValidator.


## 1.1.1 - 2018.10.08

* Prevent SCORE from using block.hash and block.prev_hash.


## 1.1.0 - 2018.10.08

* Fix icx.send() return value bug.
* Implemented call state reversion.
* Limit the number of SCORE internal circular calls (Maximum: 64)
* Limit the number of SCORE internal calls (Maximum: 1024)
* Fix a bug on SCORE zip file created on MacOS.
* Fix an exception which happens to IconServiceEngine._charge_transaction_fee() during invoking a block.
* Implemented ScorePackageValidator and import whitelist.
* Enable to change service configuration on runtime.
* Keep state db consistency with revision code provided by Governance SCORE icx.send() return value bug.
* Skip audit process for updating Governance SCORE.
* Add unittest and integration test codes for error test cases.
* Reuse cached invoke results.
* Provide json_dumps and json_loads APIs to a SCORE.


## 1.0.6.2 - 2018.09.20

* Fix an exception which happens to IconServiceEngine._charge_transaction_fee() during invoking a block.
* Fix a wrong message of "Out of Balance: balance(x) < value(y) + fee(y)" logging.


## 1.0.6.1 - 2018.09.18

* Fix invoke error on calling readonly external call in icx_sendTransaction.


## 1.0.6 - 2018.09.11

* Fix a bug that icx is not transferred on calling the method provided by other SCORE.
* Fix RabbitMQ connection check bug: connection close.
* Remove unused package: jsonschema.
* Remove debug assert code in icon_pre_validator.py.
* Update iconservice_cli log.
* Update pre-validator to reject a tx that has too long params compared to its stepLimit.


## 1.0.5 - 2018.09.04

* Fix occasional SCORE module loading failures on Linux systems such as Jenkins.
* Fix RabbitMQ initialize checking logic.


## 1.0.4 - 2018.08.28

* TypeConverter raises an exception for invalid parameters.
* When deployment is approved in audit mode, on_install or on_update is called in the deployer context(tx=None, msg=deployed msg).
* Disable transaction deploying SCORE with ICX value.
* Fix error on calling ise_getStatus.
* Provide a SCORE with a hash API.
