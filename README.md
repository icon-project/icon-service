# ICON Service

ICON Service manage state of ICON node including ICX, SCOREs using LevelDB.

Before processing transactions, ICON Service check for syntax errors, balances, etc. 

## Installation

This chapter will explain how to install icon service engine on your system. 

### Requirements

ICON SCORE development and execution requires following environments.

* OS: MacOS, Linux
    * Windows are not supported yet.
* Python
    * Version: python 3.6+
    * IDE: Pycharm is recommended.

**Libraries**

| name        | description                                                  | github                                                       |
| ----------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| LevelDB     | ICON SCORE uses levelDB to store its states.                 | [LevelDB GitHub](https://github.com/google/leveldb)          |
| libsecp256k | ICON SCORE uses secp256k to sign and validate a digital signature. | [secp256k GitHub](https://github.com/bitcoin-core/secp256k1) |

### Setup on MacOS

```bash
#install levelDB
$ brew install leveldb

# Create a working directory
$ mkdir work
$ cd work

# setup the python virtualenv development environment
$ virtualenv -p python3 venv
$ source venv/bin/activate

# Install the ICON SCORE dev tools
(venv) $ pip install iconservice
```

### Setup on Linux

```bash
# Install levelDB
$ sudo apt-get install libleveldb1 libleveldb-dev
# Install libSecp256k
$ sudo apt-get install libsecp256k1-dev

# Create a working directory
$ mkdir work
$ cd work

# Setup the python virtualenv development environment
$ virtualenv -p python3 venv
$ source venv/bin/activate

# Install the ICON SCORE dev tools
(venv) $ pip install iconservice
```

## Building source code

First, clone this project. Then go to the project folder and create a user environment and run build script.

```bash
$ virtualenv -p python3 venv  # Create a virtual environment.
$ source venv/bin/activate    # Enter the virtual environment.
(venv)$ ./build.sh            # run build script
(venv)$ ls dist/              # check result wheel file
iconservice-x.x.x-py3-none-any.whl
```

## Reference
- [ICON JSON-RPC API v3](https://github.com/icon-project/icon-rpc-server/blob/master/docs/icon-json-rpc-v3.md)
- [earlgrey](https://github.com/icon-project/earlgrey)
- [ICON Commons](https://github.com/icon-project/icon-commons)
- [ICON RPC Server](https://github.com/icon-project/icon-rpc-server)

## License

This project follows the Apache 2.0 License. Please refer to [LICENSE](https://www.apache.org/licenses/LICENSE-2.0) for details.
