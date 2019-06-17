from iconservice import *


class SampleInterface(InterfaceScore):
    @interface
    def set_value(self, value: int) -> None: pass

    @interface
    def get_value(self) -> int: pass

    @interface
    def get_db(self) -> IconScoreDatabase: pass


class SampleLinkScore(IconScoreBase):
    _SCORE_ADDR = 'score_addr'

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)
        self._addr_score = VarDB(self._SCORE_ADDR, db, value_type=Address)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=False)
    def add_score_func(self, score_addr: Address) -> None:
        self._addr_score.set(score_addr)

    @external(readonly=True)
    def get_value(self) -> int:
        test_interface = self.create_interface_score(self._addr_score.get(), SampleInterface)
        return test_interface.get_value()

    @external
    def set_value(self, value: int):
        test_interface = self.create_interface_score(self._addr_score.get(), SampleInterface)
        test_interface.set_value(value)
        self.Changed(value)

    def _get_other_score_db(self):
        interface_score = self.create_interface_score(self._addr_score.get(), SampleInterface)
        return interface_score.get_db()

    @external(readonly=True)
    def get_other_score_db_bool(self) -> bool:
        self._get_other_score_db()
        return True

    @external(readonly=True)
    def get_other_score_db_int(self) -> int:
        self._get_other_score_db()
        return 1

    @external(readonly=True)
    def get_other_score_db_str(self) -> str:
        self._get_other_score_db()
        return "string"

    @external(readonly=True)
    def get_other_score_db_bytes(self) -> bytes:
        self._get_other_score_db()
        return b'bytestring'

    @external(readonly=True)
    def get_other_score_db_address(self) -> Address:
        self._get_other_score_db()
        return Address.from_string(f"hx{'0'*40}")

    @external
    def try_get_other_score_db(self):
        self._get_other_score_db()
