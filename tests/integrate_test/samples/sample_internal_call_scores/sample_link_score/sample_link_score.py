from iconservice import *


class SampleInterface(InterfaceScore):
    @interface
    def set_value(self, value: int) -> None: pass

    @interface
    def get_value(self) -> int: pass

    @interface
    def get_db(self) -> IconScoreDatabase: pass

    @interface
    def fallback_via_internal_call(self) -> None: pass

    @interface
    def fallback_via_not_payable_internal_call(self) -> None: pass


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
    def get_data_from_other_score(self) -> bool:
        db = self._get_other_score_db()
        db.get(b'dummy_key')
        return True

    @external
    def put_data_to_other_score_db(self):
        db = self._get_other_score_db()
        db.put(b'dummy_key', b'dummy_value')

    @external(readonly=False)
    def transfer_icx_to_other_score(self, value: int) -> None:
        test_interface = self.create_interface_score(self._addr_score.get(), SampleInterface)
        test_interface.value = value
        test_interface.fallback_via_internal_call()

    @external(readonly=False)
    def transfer_icx_to_other_score_fail(self, value: int) -> None:
        test_interface = self.create_interface_score(self._addr_score.get(), SampleInterface)
        test_interface.value = value
        test_interface.fallback_via_not_payable_internal_call()

    @external(readonly=False)
    @payable
    def transfer_all_icx_to_other_score(self) -> None:
        amount: int = self.icx.get_balance(self.address)
        self.call(self._addr_score.get(), 'fallback_via_internal_call', {}, amount)

    @payable
    def fallback(self) -> None:
        pass
