# ICON SCORE 개발 도구(tbears) TUTORIAL

## 문서 이력

| 일시 | 버전 | 작성자 | 비고 |
|:-----|:----|:-----:|:-----|
| 2018.07.06 | 0.9.3 | 김인원 | 설정 파일 내용 변경 |
| 2018.06.12 | 0.9.2 | 조치원 | Markdown 형식으로 변경 |
| 2018.06.11 | 0.9.1 | 조치원 | 에러 코드표 추가, icx_getTransactionResult 내용 수정 |
| 2018.06.01 | 0.9.0 | 조치원 | JSON-RPC API v3 ChangeLog 추가 |

## ICON SCORE 개발 환경

### Overview

현 시점에서 ICON SCORE 개발 및 실행을 위해서는 다음의 환경이 요구된다.

* OS: MacOS, Linux
    * 현재 Windows는 미지원
* Python
    * 버전: python 3.6 이상
    * IDE: Pycharm 권장    

### LevelDB

ICON SCORE에서는 SCORE의 상태들을 저장하기 위해 levelDB 오픈소스를 사용한다.
ICON SCORE 개발 환경을 구축하기 위해서는 levelDB 개발 라이브러리의 사전 설치가 반드시 필요하다.<br/>
[LevelDB GitHub](https://github.com/google/leveldb)

#### ex) MacOS에서의 설치 방법

```bash
$ brew install leveldb
```

## Getting started

```bash
# 작업 디렉토리 생성
$ mkdir work
$ cd work

# python 개발 환경 구축
$ virtualenv -p python3 .
$ source bin/activate

# ICON SCORE 개발 도구 설치
(work) $ pip install iconservice-x.x.x-py3-none-any.whl
(work) $ pip install tbears-x.x.x-py3-none-any.whl

# sample용 SCORE 프로젝트 2개 생성 (sample_crowd_sale, sample_token)
(work) $ tbears samples

# sample SCORE 프로젝트들이 정상적으로 생성되었는지 확인
(work) $ ls sample*
sample_crowd_sale:
__init__.py  package.json  sample_crowd_sale.py

sample_token:
__init__.py  package.json  __pycache__  sample_token.py

# sample_token SCORE 설치 및 JSON-RPC 서버 구동
(work) $ tbears run sample_token

# sample_crowd_sale SCORE 설치
(work) $ tbears run sample_crowd_sale

# SampleToken 코드의 동작을 테스트하는 스크립트 실행
# curl을 이용한 jsonrpc 통신
# ICON JSON-RPC API v3 프로토콜을 이용하여 sample SCORE 서비스 동작 여부 확인 가능
(work) $ ./run.sh
...
06-01 23:06:43 INFO {"jsonrpc": "2.0", "result": "0x3635c9adc5de9ffffe", "id": 50889}
06-01 23:06:43 INFO 127.0.0.1 - - [01/Jun/2018 23:06:43] "POST /api/v3 HTTP/1.1" 200 -
{"jsonrpc": "2.0", "result": "0x3635c9adc5de9ffffe", "id": 50889}

# 여기서부터는 자신의 SCORE 프로젝트를 생성하고 실행하는 방법 설명

# abc 토큰 개발을 위한 프로젝트 초기 생성
(work) $ tbears init <main python file name> <score class name>
ex)
(work) $ tbears init abc ABCToken

# abc 토큰 개발을 위한 프로젝트 생성 확인
(work) $ ls abc
abc.py  __init__.py  package.json

# JSON-RPC 서버 구동 및 abc 토큰 로딩
# DB 초기화되지 않음
(work) $ tbears run abc

# JSON-RPC 서버 종료
(work) $ tbears stop

# JSON-RPC 서버 종료 및 dbRoot, scoreRoot 디렉토리 제거
(work) $ tbears clear

# tbears 도움말
(work) $ tbears help
```

## tbears 사용 방법

### tbears 설정 파일

tbears의 작업 디렉토리 내 tbears.json 파일을 로딩한다.

#### 파일 내용

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

#### 설명

| 항목명 | 데이터 형식 | 설명 |
|:------|:-----------|:-----|
| global | dict | tbears에서 전역적으로 사용하는 설정 |
| global.from | string | tbears에서 JSON-RPC 서버로 메시지를 전송할 때 사용하는 from 주소 |
| global.port | int | JSON-RPC 서버의 포트 번호 |
| global.scoreRoot | string | SCORE가 설치될 루트 디렉토리 |
| global.dbRoot | string | 상태 기록을 위한 DB 파일이 생성되는 루트 디렉토리 |
| global.accounts | list | 초기 코인을 가지고 있는 계좌 정보 목록<br>(index 0) genesis: 초기 코인을 가지고 있는 계좌 정보<br>(index 1) fee_treasury: transaction 처리 수수료를 수집하는 계좌 정보<br>(index 2~): 임의의 계좌 정보 |
| log | dict | tbears 로깅 설정 |
| log.level | string | 로그 메시지 표시 수준 정의<br/>"debug", "info", "warning", "error" |
| log.filePath | string | 로그 파일 경로 |
| log.outputType | string | “console”: tbears를 실행한 콘솔창에 로그 표시<br/>“file”: 지정된 파일 경로에 로그 기록<br/>“console\|file”: 콘솔과 파일에 동시 기록 |
| deploy | dict | SCORE 배포 시, 사용하는 설정 |
| deploy.uri | string | 요청을 보낼 uri |
| deploy.stepLimit | string | -(optional) |
| deploy.nonce | string | -(optional) |

### score 배포 설정 파일 형식 (tbears config 파일과 별도로 존재)
```json
{
    "socreAddress": "cx0123456789abcdef0123456789abcdef01234567",
    "params": {
        "user_param1": "0x123",
        "user_param2": "hello"
    }
}

```

| 항목명 | 데이터 형식 | 설명 |
|:------|:-----------|:-----|
| scoreAddress | string | (optional) SCORE 업데이트 시 사용 (update 할 SCORE의 주소).<br/>최초 배포 시에는 사용 안함. |
| params | dict | on_install() 혹은 on_update()의 인자로 전달할 값들의 정보 |

### tbears samples

tbears에서 제공하는 SCORE 샘플 프로젝트 2개를 생성한다.
ICON SCORE 개발 시 참고 자료용으로 제공된다.

#### 사용 방법

```bash
(work) $ tbears samples
(work) $ ls sample*
sample_crowd_sale:
__init__.py  package.json  sample_crowd_sale.py

sample_token:
__init__.py  package.json  __pycache__  sample_token.py
```

### tbears init \<project> \<class>

처음 ICON SCORE를 개발할 때 해당 SCORE 프로젝트 디렉토리 및 필수 파일들을 생성한다.

#### 사용 방법
```bash
(work) $ tbears init abc ABCToken
(work) $ ls abc
abc.py  __init__.py  package.json
```

#### 설명

| 항목 | 설명 |
|:------|:-----|
| \<project> | 이름의 SCORE 프로젝트 디렉토리 생성 |
| tbears.json | tbears의 기본 설정파일 생성 |
| \<project>/\_\_init\_\_.py | SCORE 프로젝트 디렉토리가 python 패키지 형식으로 인식되도록 한다. |
| \<project>/package.json | SCORE의 메타 데이터 |
| \<project>/\<project>.py | SCORE의 메인 파일. 내부에 ABCToken class가 정의되어 있다. |

### tbears run \<project\> \[--install or --update] \[config param path]

JSON-RPC 서버를 시작하고 project 디렉토리 내에 있는 SCORE를 설치하여 해당 SCORE 서비스가 실행될 수 있는 환경을 구성한다.

#### 사용 방법

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

#### 설명

--install 이나 --update 옵션이 생략되는 경우 reload 형식으로 동작한다.

| 옵션 | 속성 | 설명 |
|:------|:-----|:-----|
| project | required | SCORE 코드를 포함하는 디렉토리 경로명 |
| --install | optional | SCORE를 설치한다. on_install()이 호출되며 인자에 값을 전달할 경우에 사용 |
| --update | optional | SCORE를 업데이트한다. on_update()가 호출된다.<br/>(--update 옵션은 현재 미구현으로 차기 버전에서 지원 예정) |
| config param path | optional | on\_install() 혹은 on_update()에 파라미터로 입력되는 데이터 내용을 담은 파일의 경로. 해당 파일의 내용은 json 형식을 따라야 한다. |
| --install, --update가 생략된 경우 | - | 해당 SCORE가 이미 설치된 상태라면 SCORE reload를 수행한다.<br/>SCORE를 설치하는 경우라면 파라미터 값 없이 on_install()이 호출된다. |

### tbears stop

JSON-RPC 서버를 종료한다. DB 내용은 유지된다.

#### 사용 방법

```bash
(work) $ tbears stop
```

### tbears clear

JSON-RPC 서버 종료 및 현재 사용 중인 DB를 제거한다.

#### 사용 방법

```bash
(work) $ tbears clear
```

## 개발 지원 도구들

SCORE 개발하는데 도움이 되는 각종 유틸리티들에 대해 소개하고 사용 방법을 설명한다.

### Logger

콘솔 혹은 파일 형식으로 로그를 기록할 수 있는 기능을 제공하는 패키지

#### 함수 형식

```python
@staticmethod
def debug(msg: str, tag: str)
```

#### 사용 방법

```python
from iconservice.logger import Logger

TAG = 'ABCToken'

Logger.debug('debug log', TAG)
Logger.info('info log', TAG)
Logger.warning('warning log', TAG)
Logger.error('error log', TAG)
```

## ICON SCORE 개발 시 유의 사항

* tbears는 현 시점에서 loopchain 엔진을 포함하고 있지 않기 때문에 일부 SCORE 개발과 관련없는 JSON-RPC API 들은 동작하지 않을 수 있다.
    * tbears에서 지원하는 JSON-RPC API:
        * icx_getBalance, icx_getTotalSupply, icx_getBalance, icx_call, icx_sendTransaction, icx_getTransactionResult
* 이후 tbears 버전에서는 사용 방법이나 SCORE 개발 방법이 일부 변경될 수 있다.
* 개발의 편의성을 위해서 tbears에서 제공하는 JSON-RPC 서버는 transaction 내에 포함된  전자 서명을 검증하지 않는다.
