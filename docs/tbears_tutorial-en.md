# ICON SCORE development tool (tbears) TUTORIAL

## Change history 

| Date | Version | Author | Description |
|:-----|:----|:-----:|:-----|
| 2018.07.10 | 0.9.3 | Chiwon Cho | earlgrey package description added. |
| 2018.07.06 | 0.9.3 | Inwon Kim | Configuration file updated. |
| 2018.06.12 | 0.9.2 | Chiwon Cho | Tutorial moved from doc to markdown. |
| 2018.06.11 | 0.9.1 | CHiwon Cho | Error codes added. icx_getTransactionResult description updated. |
| 2018.06.01 | 0.9.0 | Chiwon Cho | JSON-RPC API v3 ChangeLog added. |

## ICON SCORE development environment

### Overview

ICON SCORE development and execution requires following environments. 

* OS: MacOS or Linux
    * Windows are not supported yet.
* Python
    * Version: python 3.6+
    * IDE: Pycharm is recommended.    

### LevelDB

ICON SCORE uses open-source levelDB to store SCORE states.
Hence, levelDB dev libraries must be pre-installed.<br/>
[LevelDB GitHub](https://github.com/google/leveldb)

#### ex) installing on MacOS

```bash
$ brew install leveldb
```

## Getting started

```bash
# Create a working directory
$ mkdir work
$ cd work

# Setup the python virtualenv development environment
$ virtualenv -p python3 .
$ source bin/activate

# Install the ICON SCORE dev tools
(work) $ pip install earlgrey-x.x.x-py3-none-any.whl
(work) $ pip install iconservice-x.x.x-py3-none-any.whl
(work) $ pip install tbears-x.x.x-py3-none-any.whl

# Create 2 sample SCORE projects (sample_crowd_sale, sample_token)
(work) $ tbears samples

# Sample SCORE projects should have following files.
(work) $ ls sample*
sample_crowd_sale:
__init__.py  package.json  sample_crowd_sale.py

sample_token:
__init__.py  package.json  sample_token.py

# Install sample_token SCORE and run JSON-RPC server.
(work) $ tbears run sample_token

# Install sample_crowd_sale SCORE.
(work) $ tbears run sample_crowd_sale

# Test SampleToken using test script, run.sh.
# Test script uses curl to make a jsonrpc request.
# The script tests ICON JSON-RPC API v3 protocol against the sample SCORE service.
(work) $ ./run.sh
...
06-01 23:06:43 INFO {"jsonrpc": "2.0", "result": "0x3635c9adc5de9ffffe", "id": 50889}
06-01 23:06:43 INFO 127.0.0.1 - - [01/Jun/2018 23:06:43] "POST /api/v3 HTTP/1.1" 200 -
{"jsonrpc": "2.0", "result": "0x3635c9adc5de9ffffe", "id": 50889}

# Create a new SCORE project.
# Create a project for 'abc' token using init command.
(work) $ tbears init <main python file name> <score class name>
ex)
(work) $ tbears init abc ABCToken

# Project files for abc token are create.
(work) $ ls abc
abc.py  __init__.py  package.json

# Run JSON-RPC server and load abc token.
# DB is not initialized.
(work) $ tbears run abc

# Stop JSON-RPC server. 
(work) $ tbears stop

# Stop JSON-RPC server and remove dbRoot, scoreRoot folders.
(work) $ tbears clear

# tbears help shows help message.
(work) $ tbears help
```

## tbears tutorial

### tbears configuration file

Load tbears.json file in the tbears working directory. 

#### File content

```json
{
    "global": {
        "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "port": 9000,
        "scoreRoot": "./.score",
        "dbRoot": "./.db",
        "genesisData": {
            "accounts": [
                {
                    "name": "genesis",
                    "address": "hx0000000000000000000000000000000000000000",
                    "balance": "0x2961fff8ca4a62327800000"
                },
                {
                    "name": "fee_treasury",
                    "address": "hx1000000000000000000000000000000000000000",
                    "balance": "0x0"
                }
            ]
        }
    },
    "log": {
        "colorLog": true,
        "level": "debug",
        "filePath": "./tbears.log",
        "outputType": "console|file"
    },
    "deploy": {
        "uri": "http://localhost:9000/api/v3",
        "stepLimit": "0x12345",
        "nonce": "0x123"
    }
}
```

#### Description

| Field | Data type | Description |
|:------|:-----------|:-----|
| global | dict | tbears global configuration. |
| global.from | string | from address that tbears uses when it sends messages to JSON-RPC server. |
| global.port | int | JSON-RPC server port number. |
| global.scoreRoot | string | Root directory that SCORE will be installed. |
| global.dbRoot | string | Root directory that state DB file will be created. |
| global.accounts | list | List of accounts that holds initial coins. <br>(index 0) genesis: account that holds initial coins.<br>(index 1) fee_treasury: account that collects transaction fees.<br>(index 2~): random accounts. |
| log | dict | tbears logging setting |
| log.level | string | log level. <br/>"debug", "info", "warning", "error" |
| log.filePath | string | log file path. |
| log.outputType | string | “console”: log outputs to the console that tbears is running.<br/>“file”: log outputs to the file path.<br/>“console\|file”: log outputs to both console and file. |
| deploy | dict | Configurations for SCORE deployment. |
| deploy.uri | string | uri that the deploy request is sent to |
| deploy.stepLimit | string | -(optional) |
| deploy.nonce | string | -(optional) |

### SCORE deploy configuration file format (a separate file from tbears config)
```json
{
    "socreAddress": "cx0123456789abcdef0123456789abcdef01234567",
    "params": {
        "user_param1": "0x123",
        "user_param2": "hello"
    }
}

```

| Field | Data type | Description |
|:------|:-----------|:-----|
| scoreAddress | string | (optional) Used when update SCORE (The address of the SCORE being updated).<br/>Not used when initial deploy. |
| params | dict | Parameters to be passed to on_install() or on_update() |

### tbears samples

tbears comes with 2 sample SCOREs as a reference. "tbears sample" command will create the sample projects. 

#### Usage 

```bash
(work) $ tbears samples
(work) $ ls sample*
sample_crowd_sale:
__init__.py  package.json  sample_crowd_sale.py

sample_token:
__init__.py  package.json  sample_token.py
```

### tbears init \<project> \<class>

init command creates a new SCORE project. It creates project folder and required files.

#### Usage
```bash
(work) $ tbears init abc ABCToken
(work) $ ls abc
abc.py  __init__.py  package.json
```

#### File description

| Item | Description |
|:------|:-----|
| \<project> | SCORE project name. Project folder is create with the same name. |
| tbears.json | tbears default configuration file will be created on the working directory. |
| \<project>/\_\_init\_\_.py | \_\_init\_\_.py file to make the project folder recognized as a python package. |
| \<project>/package.json | SCORE metadata. |
| \<project>/\<project>.py | SCORE main file. ABCToken class is defined. |

### tbears run \<project\> \[--install or --update] \[config param path]

Starts  JSON-RPC server, and installs the SCORE in the project folder. SCORE is ready to execute.  

#### Usage

```bash
(work) $ tbears run abc
...
06-20 18:12:36 INFO {"jsonrpc": "2.0", "result": "0xab7cfcd238d0a871ffe1c8d2e0114b014a0eb71182d9ee4f0b19d46bf6f7c44a", "id": 111}
...

# issue icx_getTransactionResult with the result (txHash)
# need to modify value of txHash in issue_rpc.sh
(work) $ ./issue_rpc.sh gettxres
...
06-22 18:15:15 INFO {"jsonrpc": "2.0", "result": {"txHash": "0xab7cfcd238d0a871ffe1c8d2e0114b014a0eb71182d9ee4f0b19d46bf6f7c44a", "blockHeight": "0x9", "to": null, "scoreAddress": "cx6bd390bd855f086e3e9d525b46bfe24511431532", "stepUsed": "0x1770", "status": "0x1", "failure": null, "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}, "id": 112}
...
```

```bash
(work) $ cat ./params.json
{
    "params": {
        "init_supply": "0x3e8",
        "decimal": "0x12"
    }
} 

(work) $ tbears run abc --install ./params.json
...
```

#### Description

If --install or --update is omitted, SCORE is reloaded. 

| Option | Required | Description |
|:------|:-----|:-----|
| project | required | Directory path that contains the SCORE code. |
| --install | optional | If this option is given, SCORE is installed. SCORE's on_install() function is called, and parameters can be passed to the function. |
| --update | optional | SCORE is updated. on_update() is called.<br/>(--update is not implemented yet. Will be supported in next version.) |
| config param path | optional | Path to a file containing the data that will be passed to on_install() or on_update() as parameters. Data should conform to json format. |
| if --install or --update omitted | - | If the SCORE is already installed, SCORE will be reloaded.<br/>If SCORE needs to be newly installed, on_install() is called without parameters. |

### tbears stop

Stops JSON-RPC server. DB remains the state.

#### Usage 

```bash
(work) $ tbears stop
```

### tbears clear

Stops JSON-RPC server and removes current DB.

#### Usage

```bash
(work) $ tbears clear
```

## Utilities

This chapter explains the utilities that will help SCORE development.

### Logger

Logger is a package writing outputs to log file or console.

#### Method

```python
@staticmethod
def debug(msg: str, tag: str)
```

#### Usage

```python
from iconservice.logger import Logger

TAG = 'ABCToken'

Logger.debug('debug log', TAG)
Logger.info('info log', TAG)
Logger.warning('warning log', TAG)
Logger.error('error log', TAG)
```

## Notes

* tbears currently does not have loopchain engine, so some JSON-RPC APIs which are not related to SCORE developement may not function. 
    * Below JSON-RPC APIs are supported in tbears:
        * icx_getBalance, icx_getTotalSupply, icx_getBalance, icx_call, icx_sendTransaction, icx_getTransactionResult
* In next versions, tbears commands or SCORE development methods may change in part. 
* For the development convinience, JSON-RPC server in tbears does not verify the transaction signature.
