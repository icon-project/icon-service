# ChangeLog

## 0.9.4 - 2018-07-17

### iconservice

* 설정 파일 구현
* Governance SCORE 통합
* SCORE update 기능 추가
* SCORE audit 기능 추가 (미완성)
* 새로운 transaction dataType 값 추가 (message)
* 수수료 계산 시 새로운 step 규칙 적용

### SCORE

* __init__() 메소드 매개 변수 변경
    * __init__(self, db: IconScoreDatabase)
    * 기존 SCORE 수정 필요

### tbears

* 전자 서명 방식 변경
* tbears command 및 설정 파일 형식 변경 (tbears_tutorial.md 참고)

### 기타

* SCORE DB 통합 작업 진행 중

## 0.9.3 - 2018-07-10

### iconservice

* 수수료 차감 기능 구현 (기본 설정: off)
* icx_sendTransaction에 version 필드 추가 (icx_sendTransaction API 문서 참조)
* TransactionResult에 새로운 항목 추가 (icx_getTransactionResult API 문서 참조)
* 프로토콜 v2, v3 동시 지원

### 기타

* loopchain에서 RestServer를 별도의 패키지로 분리

## 0.9.2 - 2018-06-29

* loopchain + iconservice 연동
* EventLog 형식 변경
* InterfaceScore 추가
  - 외부 스코어의 external function 호출시 Interface로 호출하도록 추가
* IconScore Coin API 변경
  - self.send, self.transfer -> self.icx.send, self.icx.transfer
* JSON-RPC API v3 업데이트
  - 모든 프로토콜에 version 필드 추가
  - 블록정보 조회 API 추가
  - 트랜젝션 정보 조회 API 추가

## 0.9.1 - 2018-06-11

### SCORE

* @interface decorator 추가

### iconservice and tbears

* icx_sendTransaction 메소드 응답 형식 수정
    - 유효하지 않은 transaction이 수신되면 에러 응답을 하도록 수정됨
* icx_getTransactionResult 메소드 추가
    - 현재 transaction 처리 결과는 메모리에 저장됨
    - tbears server 프로세스가 종료되면 transaction 처리 결과는 사라짐
    - 차기 버전에서는 transaction result를 영구 저장소에 저장할 예정
* tbears run command parameter 추가 (--install, --update)
* JSON-RPC 메시지 유효성 검사 기능 구현
    - 지속적으로 업데이트 예정

### Documents

* tbears_jsonrpc_api_v3.md
    - 에러 코드표 추가
    - icx_getTransactionResult에서 failure 항목 설명 추가
* dapp_guid.md
    - property, func 내용 추가
    
### 주의 사항    

* 이후 버전에서 LevelDB에 저장되는 데이터 형식이 변경될 수 있음
* LevelDB에 저장되는 데이터 형식 변경 시 이전 데이터와의 호환성이 깨질 수 있음

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
