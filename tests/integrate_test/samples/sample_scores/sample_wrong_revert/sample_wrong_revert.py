from iconservice import *


class SampleWrongRevert(IconScoreBase):
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value1 = VarDB('value1', db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value1(self) -> int:
        return self._value1.get()

    @external(readonly=False)
    def set_value1(self, value: int) -> None:
        revert("hello world", 33000)
        self._value1.set(value)

    @external(readonly=False)
    def call_revert_with_invalid_code(self):
        revert(message='call_revert_with_invalid_code', code='code')

    @external(readonly=False)
    def call_revert_with_none_message(self):
        revert(message=None, code=33000)

    @external(readonly=False)
    def call_revert_with_none_message_and_none_code(self):
        revert(message=None, code=None)

    @external(readonly=False)
    def call_exception(self):
        raise KeyError('Intended exception')

    @payable
    def fallback(self) -> None:
        print("fallback!!")
