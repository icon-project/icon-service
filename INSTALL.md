# How to install ICON Service

## Envirnoment

* OS: Ubuntu or MacOS
    - Windows is not supported yet.
* Python: 3.6.5+
    - virtualenv is required.
    - Python 3.7 or higher is not supported.

## Prerequisites

Required libraries or services that are to be working with ICON Service

* [LevelDB](https://github.com/google/leveldb): Key/Value DB used for saving blockchain data
* [libsecp256k](https://github.com/bitcoin-core/secp256k1): ECDSA based signing/verification library
* [RabbitMQ](https://www.rabbitmq.com/)
  * The most popular open source message broker
  * Used for components such as loopchain, iconservice and iconrpcserver to communicate with each other.

## Packages

ICON node consists of 5 packages.

### iconcommons

Common utilities used in ICON Service and ICON RPC Server

github: https://github.com/icon-project/icon-commons

pypi: https://pypi.org/project/iconcommons/

* Logging utils
* Configuration file management

### iconservice

ICON Service component

github: https://github.com/icon-project/icon-service

pypi: https://pypi.org/project/iconservice/

ICON Service component plays the following roles:
* Base coin management
* SCORE LifeCycle management
* Transaction processing
* SCORE state management

### iconrpcserver

ICON RPC Server component

github: https://github.com/icon-project/icon-rpc-server

pypi: https://pypi.org/project/iconrpcserver/

* Server handling JSON-RPC request and response.
* JSON-RPC message syntax check
* Refer to the name of method in a JSON-RPC request and pass it to the appropriate component (loopchain or iconservice)

### earlgrey

Earlgrey is a python library which provides a convenient way to publish and consume messages between processes using RabbitMQ. It is abstracted to RPC pattern.

github: https://github.com/icon-project/earlgrey

pypi: https://pypi.org/project/earlgrey/

### loopchain

Blockchain engine for icon foundation

github: https://github.com/icon-project/loopchain

pypi: N/A

## Installation

Assuming that the above prerequisites have been already installed.

```bash
$ virtualenv venv             # Create a virtual environment.
$ source venv/bin/activate    # Enter the virtual enviroment.

# The processes below are executed under virtualenv environment.

# Install python packages being comprised of a ICON node.
(venv) $ pip install iconcommons
(venv) $ pip install iconservice
(venv) $ pip install iconrpcserver
(venv) $ pip install earlgrey
# loopchain package has not been published on pypi.org yet.
# Thus you need to build loopchain source code to create a python wheel package file.
# Refer to the loopchain github repository above
(venv) $ pip install loopchain-x.x.x-py3-none-any.whl

# Execute ICON Service
(venv) $ iconservice start -c ./iconservice_config.json
# Execute loopchain
(venv) $ loop peer -d -r ${RADIO_STATION_IP}:${RADIO_STATION_PORT} -o ./peer_conf.json
# Execute JSON-RPC Server
(venv) $ iconrpcserver start -c ./iconrpcserver_config.json
```

## Configuration File

### iconservice_config.json

Configuration file example of ICON Service

Once an  ICON node starts with a specific configuration, you MUST NOT change it, because changing a configuration can cause the data inconsistency among ICON nodes.

If you want to use a new configuration, stop all nodes, clear their old block data  and restart them with the new one.

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

### iconrpcserver_config.json

Configuration file example of ICON RPC Server

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
| log | dict | Refer to the description of iconservice_config.json |
| channel | string | channel name to interact with loopchain |
| amqpKey | string | used for a part of a queue name of RabbitMQ |
| amqpTarget | string | IP of RabbitMQ Server<br>ex) "127.0.0.1" |
| port | integer | PRC Server port |
| gunicornWorkerCount | integer | gunicorn worker count<br>default count  = 2 * cpu + 1 |