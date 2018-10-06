from iconservice import *


class TestEventLogScore(IconScoreBase):
    @eventlog(indexed=2)
    def NormalEventLog(self, value1: str, value2: str, value3: str):
        pass

    @eventlog(indexed=2)
    def NormalEventLogWithDefault(self, value1: str, value2: str="default2", value3: str="default3"):
        pass

    @eventlog
    def EventLogTestingBytesString(self, string: str, bytes: bytes):
        pass

    @eventlog
    def EventLogWithNoneDefault(self, integer: int=None, string: str=None, boolean: bool=None, address: Address=None, bytes: bytes=None):
        pass

    @eventlog
    def EventLogWithOutParams(self):
        pass

    @eventlog(indexed=1)
    def EventLogHavingBody(self, value: str):
        self.set_value(value)

    @eventlog
    def EventLogForCheckingParamsType(self, integer: int, string: str, boolean: bool, bytes: bytes, address: Address):
        pass

    @eventlog(indexed=-1)
    def EventLogIndexUnderZero(self, value: str):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=str)

    def on_install(self, value: str="default") -> None:
        super().on_install()
        self.set_value(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value(self) -> str:
        return self._value.get()

    @external
    def set_value(self, value: str):
        self._value.set(value)

    @external(readonly=True)
    def call_even_log_in_read_only_method(self) -> str:
        self.NormalEventLog("1", "2", "3")
        return "test"

    @external
    def call_valid_event_log(self, value1: str, value2: str, value3: str):
        self.NormalEventLog(value1, value2, value3)

    @external
    def call_valid_event_log_with_none(self):
        self.NormalEventLog(None, None, None)

    @external
    def call_valid_event_log_keyword(self, value1: str, value2: str, value3: str):
        self.NormalEventLog(value1, value2=value2, value3=value3)

    @external
    def call_valid_event_log_with_default(self, value1: str):
        self.NormalEventLogWithDefault(value1)

    @external
    def call_event_log_default_is_none(self, test_type: str):
        integer = 0x00
        string = "test"
        boolean = True
        bytes = b'0'
        address = Address.from_string("cx0000000000000000000000000000000000000000")
        if test_type == "integer":
            self.EventLogWithNoneDefault(string=string, boolean=boolean, bytes=bytes, address=address)
        elif test_type == "string":
            self.EventLogWithNoneDefault(integer=integer, boolean=boolean, bytes=bytes, address=address)
        elif test_type == "boolean":
            self.EventLogWithNoneDefault(integer=integer, string=string, bytes=bytes, address=address)
        elif test_type == "bytes":
            self.EventLogWithNoneDefault(integer=integer, string=string, boolean=boolean, address=address)
        elif test_type == "address":
            self.EventLogWithNoneDefault(integer=integer, string=string, boolean=boolean, bytes=bytes)

    @external
    def call_event_log_params_are_not_defined(self):
        self.EventLogWithOutParams()

    @external
    def call_event_log_having_body(self):
        self.EventLogHavingBody("call event log having body")

    @external
    def call_event_log_raising_error(self):
        self._value.set("set data before event log raise error")
        # raise error as input less params
        self.NormalEventLog("1", "2")

    @external
    def call_event_log_index_under_zero(self):
        self.EventLogIndexUnderZero("test")

    @external
    def call_event_log_input_less_number_of_params(self):
        self.NormalEventLog("1", "2")

    @external
    def call_event_log_input_exceed_number_of_params(self):
        self.NormalEventLog("1", "2", "3", "4")

    @external
    def call_event_log_input_exceed_number_of_params2(self):
        self.NormalEventLog("1", "2", "3", "4", "5")

    @external
    def call_event_log_input_empty_bytes_and_string_data(self):
        self.EventLogTestingBytesString(string="", bytes=b'')

    @external
    def call_event_log_for_checking_params_type(self, test_type: str, input_params_type: str):
        integer = 0x00
        string = ""
        boolean = True
        bytes = b'0'
        address = Address.from_string("cx0000000000000000000000000000000000000000")
        none = None

        if test_type == "integer":
            integer = locals()[input_params_type]
        elif test_type == "string":
            string = locals()[input_params_type]
        elif test_type == "boolean":
            boolean = locals()[input_params_type]
        elif test_type == "bytes":
            bytes = locals()[input_params_type]
        elif test_type == "address":
            address = locals()[input_params_type]
        self.EventLogForCheckingParamsType(integer, string, boolean, bytes, address)
