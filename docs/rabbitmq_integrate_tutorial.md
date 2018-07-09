Overview
============
loopchain과 iconservice를 연동해서 SCORE를 등록 및 실행하는 방법을 설명한다.

rabbitmq 설치
============

설치가이드 주소 : https://www.rabbitmq.com/download.html

## MacOS

* mac기준 brew설치후 install rabbitmq로 간단 설치 가능
* $ sudo find / -name rabbitmq-server실행해서 결과로 찾은 PATH 를 아래와 같이 추가한다.
ex) $ export PATH=$PATH:/usr/local/Cellar/rabbitmq/3.7.4/sbin

* 설치 오류 발생시 $ brew install automake

```bash
brew services start rabbitmq
rabbitmqctl list_queues
```

## Ubuntu

```bash
sudo apt install rabbitmq-server
```

loopchain, iconservice 실행
============

* rabbitmq서버가 실행되고 있어야 한다.
* 아래 서비스 실행 순서를 준수해야 한다.
    - radiostation, iconservice, loopchain, restserver 순서로 실행 필요

## 라이브러리 및 실행 환경 설정

```bash
$ mkdir work
$ cd work
$ cp ~/Downloads/line_test.tar.gz
$ tar xzvf line_test.tar.gz

$ cd line_test
$ virtualenv -p python3 venv
$ source venv/bin/activate

$ pip install ./lib/earlgrey-x.x.x-py3-none-any.whl
$ pip install ./lib/iconservice-x.x.x-py3-none-any.whl
$ pip install ./lib/tbears-x.x.x-py3-none-any.whl
$ pip install ./lib/loopchain-x.x.x-py3-none-any.whl
$ pip install ./lib/rest-x.x.x-py3-none-any.whl
```

## radiostation 서비스 실행

```bash
# -d 디버그, -o 설정파일
$ loop rs -d -o ./conf/loop_rs_conf.json
```

## iconservice 서비스 실행

```bash
$ iconservice start -c ./conf/icon_conf1.json
```

## loopchain 서비스 실행

```bash
# -d 디버그, -r target radio station -o 설정파일
$ loop peer -d -r 127.0.0.1:7102 -o ./conf/loop_peer_conf1.json
```

## restserver 서비스 실행

```bash
$ rest start -o ./conf/rest_config.json
```

## tbears samples 코드 생성

```bash
$ tbears samples
```

## 새 SCORE 등록하기

``` bash
# 키체인 암호 : qwer1234%
$ tbears deploy sample_token -k ./icon_keys/key1
```
