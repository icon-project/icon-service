# ChangeLog

## 0.9.1 - 2018-06-08

### SCORE

* @interface decorator 추가

### tbears

* icx_sendTransaction 메소드 응답 형식 수정
* icx_getTransactionResult 메소드 추가
* run command parameter 추가 (--install, --update)
* JSON-RPC 프로토콜 상에서 null값을 가지는 key에 대한 예외 처리

### Documents

* tbears_jsonrpc_api_v3.md
    - 에러 코드표 추가
* dapp_guid.md
    - property, func 내용 추가

## 0.9.0 - 2018-06-01

* IconScoreBase.genesis_init()를 on_install(), on_update()로 변경
* SCORE 개발 시 복수 개의 파일로 개발 가능
* SCORE 개발용 로깅 기능 추가
* ICON JSON-RPC API v3 적용 (tbears_jsonrpc_api_v3.md 참고)
* 외부 IP로 tbears json rpc server에 접속 가능
* "WARNING: Do not use the development server in a production" 경고 메시지 제거
* tbears 개발 도구 사용 튜토리얼 문서 추가
* jsonpickle 패키지 사용 가능

## 0.8.1 - 2018-05-25

* 복수 SCORE 실행 가능
* 복수 파일로 SCORE 개발 가능
* SCORE 설치 시 DB 상태 유지
* DB 관련 클래스에서 bytes 형식 데이터 지원
* @score decorator 제거
* @external() -> @external 로 변경
* tbears samples 실행하면 sample score 2개 생성 (sampleCrowdSale, tokentest)
* project 생성 시 __init__.py 파일 추가 (tokentest/__init__.py 참조)
* README.md 내용 및 파일 인코딩 변경(cp949 -> utf-8)

## 0.8.0 - 2018-05-11

* 한 개의 SCORE만 실행 가능
* 한 파일로만 SCORE 개발 가능
* SCORE 설치 시 DB 상태 초기화
