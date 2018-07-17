# ChangeLog

## 0.9.4 - 2018-07-17

### iconservice

* Implement configuration file
* Add governance SCORE
* Implement SCORE update feature
* Implement SCORE audit feature (incomplete)
* Fix a bug on calling SCORE function which needs no parameters

### etc

* To unify SCORE DBs is under development

### iconservice

## 0.9.3 - 2018-07-10

### iconservice

* Transation fee model applied (Default mode: off)
* Version field added in icx_sendTransaction (See icx_sendTransaction API reference)
* Additional fields in TransactionResult (See icx_getTransactionResult API reference)
* Supports both protocol v2 and v3

### etc

* Split RestServer as a separate package from loopchain

## 0.9.2 - 2018-06-29

* loopchain is integrated with iconservice
* EventLog format changed
* InterfaceScore added
  - Other Score's external function can be called via Interface
* IconScore Coin API modified
  - self.send, self.transfer -> self.icx.send, self.icx.transfer
* JSON-RPC API v3 updated
  - Every protocol now has a version field.
  - Block information query API added
  - Transaction information query API added 

## 0.9.1 - 2018-06-11

### SCORE

* @interface decorator added

### iconservice and tbears
* icx_sendTransaction method's return message changed
    - Error returns if the transaction is invalid.
* icx_getTransactionResult method added
    - Current version stores the transaction result in a memory.
    - When tbears server process exits, transaction result is lost.
    - In next version, transaction result will be stored in a persistent store.
* tbears run command parameters added (--install, --update)
* JSON-RPC message validation added
    - Will be continuously improved. 

### Documents

* tbears_jsonrpc_api_v3.md
    - Error code table added.
    - icx_getTransactionResult - description added for 'failure' key in response message.
* dapp_guid.md
    - Description added for built-in propertiess and functions. 
    
### Warnings    
    
* In next version, data format stored in LevelDB can be changed.
* If LevelDB data format changes, no backward compatibility is guarantees. 

## 0.9.0 - 2018-06-01

* IconScoreBase.genesis_init() changes to on_install(), on_update().
* SCORE can be implemented in multiple files.
* Logging feature added for SCORE developmenet.
* ICON JSON-RPC API v3 applied. (ref. tbears_jsonrpc_api_v3.md)
* Connect to tbears json rpc server from external IP address.
* "WARNING: Do not use the development server in a production" warning message removed.
* tbears development tool tutorial added.
* Use jsonpickle package. 

## 0.8.1 - 2018-05-25

* Multiple SCOREs can be executed.
* SCORE can be implemented in multiple files.
* When installing SCORE, previous DB state is kept. 
* DB related classes support bytes format data.
* @score decorator removed.
* @external() changed to @external
* 'tbears samples' command creates two sample scores. (sampleCrowdSale, tokentest)
* __init__.py is generated on project creation. (See tokentest/__init__.py)
* README.md content and file encoiding changed. (cp949 -> utf-8)

## 0.8.0 - 2018-05-11

* Only single SCORE can be executed.
* SCORE should be implemented in a single file.
* When installing SCORE, DB state is cleared.
