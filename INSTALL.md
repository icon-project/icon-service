# How to install ICON node

This document explains how to setup a private loopchain network.

## Environment

* OS: Ubuntu or MacOS
    - Windows is not supported yet.
* Python: 3.6.5+
    - virtualenv is required.
    - Python 3.7 or higher is not supported.

## Packages

ICON node consists of the following 5 packages.

### iconcommons

Common utilities used in ICON Service and ICON RPC Server

* Logging utils
* Configuration file management

github: https://github.com/icon-project/icon-commons  
pypi: https://pypi.org/project/iconcommons/

### iconservice

ICON Service component plays the following roles:
* Base coin management
* SCORE lifecycle management
* Transaction processing
* SCORE state management

github: https://github.com/icon-project/icon-service  
pypi: https://pypi.org/project/iconservice/

### iconrpcserver

ICON RPC Server component

* A server that handles JSON-RPC request and response.
* JSON-RPC message syntax check
* Pass a JSON-RPC request to the appropriate components (loopchain or iconservice) according to its method name.

github: https://github.com/icon-project/icon-rpc-server  
pypi: https://pypi.org/project/iconrpcserver/

### earlgrey

Earlgrey is a python library which provides a convenient way to publish and consume messages between processes using RabbitMQ.
It abstracts the implementation complexity of the RPC pattern.  

github: https://github.com/icon-project/earlgrey  
pypi: https://pypi.org/project/earlgrey/

### loopchain

Blockchain engine for ICON Foundation

github: https://github.com/icon-project/loopchain  
pypi: N/A

## Installation

### Install third party tools

automake, pkg-config, libtool, leveldb, rabbitmq, openssl

### Setup RabbitMQ

* Increase the maximum number of file descriptors.

```bash
$ ulimit -S -n {value: int}
```

* Add the above command to the `rabbitmq-env.conf` file to run the command each time rabbitmq starts.
* You may find this file here (/usr/local/etc/rabbitmq/rabbitmq-env.conf).
* Recommended value is 2048 or more.
* You may need to adjust this value depending on your infrastructure environment.

* Start rabbitmq

```bash
# MacOS
$ brew services start rabbitmq
$ rabbitmqctl list_queues
```

```bash
# Ubuntu
$ sudo service rabbitmq-server start
$ sudo rabbitmqctl list_queues
```

* Enable rabbitmq web management

```bash
$ rabbitmq-plugins enable rabbitmq_management
```

### Setup virtualenv

* Check your python version

```bash
$ python3 -V
Python 3.6.7
```

* Create an isolated environment and activate it

```bash
$ virtualenv -p python3 ./venv
$ source ./venv/bin/activate
(venv) $
```

* Check python version in the virtualenv

```bash
(venv) $ python -V
Python 3.6.7
```

### Install ICON packages

#### Stable version

It is possible to install packages from pypi.org.
```bash
(venv) $ pip install earlgrey
(venv) $ pip install iconcommons
(venv) $ pip install iconservice
(venv) $ pip install iconrpcserver
```

#### Development version

Packages under development can be unstable.

If you have generated SSH key for GitHub, you can install the packages with the commands below.
```bash
(venv) $ pip install git+ssh://git@github.com/icon-project/earlgrey.git
(venv) $ pip install git+ssh://git@github.com/icon-project/icon-commons.git
(venv) $ pip install git+ssh://git@github.com/icon-project/icon-service.git
(venv) $ pip install git+ssh://git@github.com/icon-project/icon-rpc-server.git
```

Alternatively, you can install with the following commands.
```bash
(venv) $ pip install git+https://github.com/icon-project/earlgrey.git
(venv) $ pip install git+https://github.com/icon-project/icon-commons.git
(venv) $ pip install git+https://github.com/icon-project/icon-service.git
(venv) $ pip install git+https://github.com/icon-project/icon-rpc-server.git
```

### Install loopchain from source

```bash
# Get loopchain source code from github.
(venv) $ git clone https://github.com/icon-project/loopchain.git
(venv) $ cd loopchain

# Generate gRPC code
(venv) $ ./generate_code.sh

(venv) $ mkdir -p resources/my_pki
(venv) $ cd resources/my_pki

# Generate a private key
(venv) $ openssl ecparam -genkey -name secp256k1 | openssl ec -aes-256-cbc -out my_private.pem
# Generate a public key
(venv) $ openssl ec -in my_private.pem -pubout -out my_public.pem
# Store the password of my_private.pem in the env variable
(venv) $ export PW_icon_dex={ENTER_MY_PASSWORD}
(venv) $ cd ../..
```

### Write channel_manage_data.json for private loopchain network

* It is required to allow only permissioned nodes to join the network.
* Radiostation must have this file.
* Peer does not need this.
* It's quite simple.

Format

```json
{
  "[CHANNEL_NAME]": {
    "score_package": "score/icx",
    "peers": [
      {
        "peer_target": "[PEER_IP]:[PEER_PORT]"
      },
      ...
    ]
  },
  ...
}
```

Example for local test

```json
{
  "icon_dex": {
    "score_package": "score/icx",
    "peers": [
      {
        "peer_target": "[local_ip]:7100"
      },
      {
        "peer_target": "[local_ip]:7200"
      },
      {
        "peer_target": "[local_ip]:7300"
      },
      {
        "peer_target": "[local_ip]:7400"
      }
    ]
  }
}
```

### Write genesis.json

Genesis block contents

```json
{
  "transaction_data": {
    "nid": "0xa",
    "accounts": [
      {
        "name": "god",
        "address": "hxebf3a409845cd09dcb5af31ed5be5e34e2af9433",
        "balance": "0x2961fff8ca4a62327800000"
      },
      {
        "name": "treasury",
        "address": "hx1000000000000000000000000000000000000000",
        "balance": "0x0"
      }
    ],
    "message": "Any messages you want to record"
  }
}
```

## Execution

### Run loopchain as a RadioStation

* Radiostation uses TCP ports 7102 and 9002 by default.
* Make sure for every peer not to open ports that radiostation has already used.

```bash
(venv) $ ./loopchain.py rs
```

### Run loopchain as a Peer

* A peer consists of iconservice, loopchain and iconrpcserver components.
* Each component publishes and consumes messages via RabbitMQ.

```bash
(venv) $ iconservice start -c ./iconservice_config.json
(venv) $ ./loopchain.py peer -r {RADIOSTATION_IP:PORT} -o conf/{PEER_CONFIG}.json
(venv) $ iconrpcserver start -c ./iconrpcserver_config.json
```

### Stop

Refer to the shell script below.

```bash
#!/bin/bash
  
function stop_loopchain()
{
    OS=$(uname)
    if [ $OS == "Linux" ]; then
        kill $(ps aux | grep 'loop rs\|loop peer\|loopchain rest-rs\|loopchain channel' | grep -v grep | awk '{print $2}')
    else
        pgrep loop | xargs kill
    fi
}

# Stop loopchain on RadioStation and Peer
stop_loopchain

# Stop ICON Service
iconservice stop -c ./conf/iconservice_config.json

# Stop ICON RPC Server
iconrpcserver stop -c ./conf/iconrpcserver_config.json
```

### Clean Up (delete log / delete DB)

```bash
# Remove logs and storages of radiostation and ICON Service (scoreRootPath, stateDbRootPath)
# Each path can be found in configuration files.

(venv) $ rm -rf log/
(venv) $ rm -rf .storage_test/
(venv) $ rm -rf .storage/
```

### Example: Execute 1 RadioStation and 4 Peers on localhost

* Be careful about TCP server port collision among processes.
    - Peer, ICON RPC Server and RadioStation
* Each peer SHOULD use distinct paths to avoid overwriting data of other peers.
    - Data storage paths: scoreRootPath, stateDbRootPath, DEFAULT_STORAGE_PATH
    - Key files: public_path and private_path of each peer
    - Log files
* We assume that channel_data.json and genesis.json have been already created in the working directory.
* To make configuration files for each peer, refer to [Configuration Files](#configuration-files) section below.

```bash
# Enter the loopchain source directory.
(venv) $ cd loopchain

(venv) $ ls *.json
channel_manage_data.json  genesis.json

# Run a radiostation.
(venv) $ ./loopchain.py rs

# Run loopchain peer0.
(venv) $ iconservice start -c ./conf/iconservice_0_config.json
(venv) $ ./loopchain.py peer -r 127.0.0.1:7102 -o ./conf/test_0_conf.json
(venv) $ iconrpcserver start -c ./conf/iconrpcserver_0_config.json

# Run loopchain peer1.
(venv) $ iconservice start -c ./conf/iconservice_1_config.json
(venv) $ ./loopchain.py peer -r 127.0.0.1:7102 -o conf/test_1_conf.json
(venv) $ iconrpcserver start -c ./conf/iconrpcserver_1_config.json

# Run loopchain peer2.
(venv) $ iconservice start -c ./conf/iconservice_2_config.json
(venv) $ ./loopchain.py peer -r 127.0.0.1:7102 -o conf/test_2_conf.json
(venv) $ iconrpcserver start -c ./conf/iconrpcserver_2_config.json

# Run loopchain peer3.
(venv) $ iconservice start -c ./conf/iconservice_3_config.json
(venv) $ ./loopchain.py peer -r 127.0.0.1:7102 -o conf/test_3_conf.json
(venv) $ iconrpcserver start -c ./conf/iconrpcserver_3_config.json

# Call JSON-RPC method (icx_getTotalSupply) to check whether peer0 works.
(venv) $ curl -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0", "method":"icx_getTotalSupply", "id":1}' 'http://127.0.0.1:9000/api/v3'
{"jsonrpc": "2.0", "result": "0x296f3c1a8737310c8800000", "id": 1}
```

Example: bash script for a peer execution
```bash
#!/bin/bash -x
  
set -e

if [ $# -ne 2 ]; then
    printf "[Usage] $0 <start or stop> <Peer Number>\nex) $0 start 0\nex) $0 stop 0\n"
    exit 1
fi

# Replace "test" with your password.
export PW_icon_dex="test"

COMMAND=$1
I=$2

echo "#### [ $I ] ####"
IS_CONF_FILE="./conf/is_conf_$I.json"
PEER_CONF_FILE="./conf/peer_conf_$I.json"
IRPC_CONF_FILE="./conf/irpc_conf_$I.json"

iconservice $COMMAND -c "$IS_CONF_FILE"
sleep 2

iconrpcserver $COMMAND -c "$IRPC_CONF_FILE"
sleep 2

if [ $COMMAND == "start" ]; then
    ./loopchain.py peer -d -r 127.0.0.1:7102 -o "$PEER_CONF_FILE"
fi
```

## Configuration Files

### RadioStation

Configuration file example of RadioStation.

```json
{
  "CHANNEL_MANAGE_DATA_PATH" : "channel_manage_data.json",
  "ENABLE_CHANNEL_AUTH": true,
  "CHANNEL_OPTION" : {
    "loopchain_default": {
      "store_valid_transaction_only": true,
      "send_tx_type": 2,
      "load_cert": false,
      "consensus_cert_use": false,
      "tx_cert_use": false,
      "tx_hash_version": 1,
      "genesis_tx_hash_version": 0,
      "key_load_type": 0,
      "public_path": "./resources/test_pkis/test_0_public.der",
      "private_path": "./resources/test_pkis/test_0_private.der",
      "private_password": "test"
    }
  }
}
```

### Peer

Configuration file example of Peer.

```json
{
  "LOOPCHAIN_DEFAULT_CHANNEL": "icon_dex",
  "CHANNEL_OPTION" : {
    "icon_dex": {
      "store_valid_transaction_only": true,
      "send_tx_type": 2,
      "load_cert": false,
      "consensus_cert_use": false,
      "tx_cert_use": false,
      "tx_hash_version": 1,
      "genesis_tx_hash_version": 0,
      "key_load_type": 0,
      "public_path": "./resources/my_pki/my_public.pem",
      "private_path": "./resources/my_pki/my_private.pem",
      "genesis_data_path": "./genesis.json"
    }
  },
  "USE_EXTERNAL_SCORE": true,
  "USE_EXTERNAL_REST": true,
  "PORT_PEER": 7100,
  "AMQP_KEY": "7100",
  "DEFAULT_STORAGE_PATH": ".storage/",
  "ALLOW_MAKE_EMPTY_BLOCK": false,
  "SUBSCRIBE_USE_HTTPS": true,
  "LOOPCHAIN_LOG_LEVEL": "INFO"
}
```

### ICON Service

Configuration file example of ICON Service.

Once an ICON node starts with a specific configuration, you MUST NOT change it, because changing a configuration can cause the data inconsistency among ICON nodes.

If you want to use a new configuration, stop all nodes, clear their old block data and restart them with the new one.

```json
{
    "log": {
        "colorLog": false,
        "level": "info",
        "filePath": "./log/iconservice.log",
        "outputType": "console|file",
        "rotate": {
            "type": "period|bytes",
            "period": "daily",
            "interval": 1,
            "backupCount": 10,
            "maxBytes": 50000000
        }
    },
    "scoreRootPath": ".score",
    "stateDbRootPath": ".statedb",
    "channel": "icon_dex",
    "amqpKey": "7100",
    "amqpTarget": "127.0.0.1",
    "builtinScoreOwner": "hx4b096790c3a1804c9828939839a901d5078020a7",
    "service": {
        "fee": false,
        "audit": false,
        "deployerWhiteList": false,
        "scorePackageValidator": false
    }
}
```

| Field | Type | Description |
|:------|------|:------------|
| log | dict | logging configuration |
| log.logger | string | logger name |
| log.colorLog | boolean | Enable or Disable colorLog |
| log.level | string | "debug", "info" , "warning", "error" |
| log.filePath | string | log file path<br>* The exception logs are managed separately in the "exc" folder for that path<br>* If filePath is set to "/logs/iconservice.log", exception logs are saved in "/logs/exc/iconservice.log" |
| log.outputType | string | target where log messages are printed<br>"console", "file", "console\|file" |
| log.rotate | string | "period": rotate by period<br>"bytes": rotate by maxBytes<br>"period\|bytes": log rotate to both period and bytes. |
| log.rotate.period | string | "daily", "weekly", "hourly", "minutely" |
| log.rotate.interval | integer | ex) (period: "hourly", interval: 24) == (period: "daily") |
| log.rotate.maxBytes | integer | log rotation happens when log file reaches to the specific size<br>ex) 1048576 |
| log.rotate.backupCount | integer | limit the number of backup log files |
| scoreRootPath | string | root directory where SCORE will be installed |
| scoreDbRootPath | string | root directory where state DB will be located |
| channel | string | channel name to interact with loopchain |
| amqpKey | string | used for a part of a queue name of RabbitMQ |
| amqpTarget | string | IP of RabbitMQ Server<br>ex) "127.0.0.1" |
| builtinScoreOwner | address | owner address of built-in SCOREs |
| service | dict | enable or disable several features of ICON Service |
| service.fee | boolean | enable or disable to charge transaction fee |
| service.audit | boolean | when enabled, audit process is required to deploy a SCORE |
| service.deployerWhiteList | boolean | when enabled, the only addresses in deployer whitelist can deploy a SCORE |
| service.scorePackageValidator | boolean | when enabled, SCORE can only import limited packages that scorePackageValidator allows |

### ICON RPC Server

Configuration file example of ICON RPC Server.

```json
{
    "log": {
        "colorLog": true,
        "level": "info",
        "filePath": "./log/iconrpcservice.log",
        "outputType": "console|file",
        "rotate": {
            "type": "period|bytes",
            "period": "daily",
            "interval": 1,
            "backupCount": 10,
            "maxBytes": 52428800
        }
    },
    "channel": "icon_dex",
    "port": 9000,
    "amqpTarget": "127.0.0.1",
    "amqpKey": "7100",
    "gunicornWorkerCount": 1,
    "subscribeUseHttps": true
}
```

| Field | Type | Description |
|:------|------|:------------|
| log | dict | Refer to the [Configuration Files > ICON Service](#icon-service) section |
| channel | string | channel name to interact with loopchain |
| amqpKey | string | used for a part of a queue name in RabbitMQ |
| amqpTarget | string | IP of RabbitMQ Server<br>ex) "127.0.0.1" |
| port | integer | TCP port for JSON-RPC Server |
| gunicornWorkerCount | integer | gunicorn worker count<br>default count = 2 * CPU Cores + 1 |
