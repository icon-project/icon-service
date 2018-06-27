0 Overview
============
rabbitmq을 이용하여 loopchain과 iconservice를 연동한다.

1 rabbitmq 설치
============

* 설치가이드 주소 : https://www.rabbitmq.com/download.html
* mac기준 brew설치후 install rabbitmq로 간단 설치 가능
* mac기준 설치경로는 /usr/local/sbin 에 설치가 된다.
* .bash_profile, .profile에 환경변수로 지정해두면 추후에 원할한 파일실행이 가능

2 rabbitmq 실행
============

* 설치경로의 rabbitmq-server를 실행

3 rabbitmq 재실행
============
```bash
# mac기준
# cd /usr/local/sbin
rabbitmqctl stop_app
rabbitmqctl reset
rabbitmqctl start_app
```

4 loopchain, iconservice 실행 튜토리얼
============

* loopchain, iconservice모두 rabbitmq서버가 실행이 되고 있어야 한다.

### 1 python 가상환경 세팅
```bash
mkdir tutorial
cd tutorial
virtualenv venv
source venv/bin/activate
```
### 2 package 설치
```bash
pip install earlgrey #rabbitmq 패키지
pip install loopchain
pip install iconservice
```

### 3 loopchain 실행
``` bash
# terminal1
loop rs -d -o loop_rs_conf.json

# terminal2
loop peer -d -o loop_peer_conf1.json
```

### 4 iconservice 실행
``` bash
# terminal3
iconservice start -c icon_conf1.json
```

### 5 curl 실행
tbears 연동
