0 Overview
============
rabbitmq을 이용하여 loopchain과 iconservice를 연동한다.

1 rabbitmq 설치
============

* 설치가이드 주소 : https://www.rabbitmq.com/download.html

* mac기준 brew설치후 install rabbitmq로 간단 설치 가능

* $ sudo find / -name rabbitmq-server실행해서 결과로 찾은 PATH 를 아래와 같이 추가한다.
ex) $ export PATH=$PATH:/usr/local/Cellar/rabbitmq/3.7.4/sbin

* 설치 오류 발생시 $ brew install automake

2 rabbitmq 실행
============

* rabbitmq 서비스 실행
```bash
brew services start rabbitmq
rabbitmqctl list_queues
```

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

4 rabbitmq 서비스 종료
============

```bash
brew services stop rabbitmq
```

5 loopchain, iconservice 실행 튜토리얼 (1pc)
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
pip install tbears
```

### 3 loopchain 실행
* 4개의 peer이상 사용하기를 권장
``` bash
# terminal1
# -d 디버그, -o 설정파일
loop rs -d -o ./conf/loop_rs_conf.json

# terminal2
# -d 디버그, -r target radio station -o 설정파일
loop peer -d -r 127.0.0.1:7102 -o ./conf/loop_peer_conf1.json
```

### 4 iconservice 실행
* loopchain peer와 1:1 매칭
``` bash
# terminal3
-c 설정파일
iconservice start -c ./conf/icon_conf1.json
```

### 5 샘플코드 생성
```bash
tbears samples
```

### 6 배포
``` bash
tbears deploy sample_token -k ./icon_keys/icon_keystore
키체인 암호 : qwer1234%
```

