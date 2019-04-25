from iconservice import *


class GetApi(IconScoreBase):

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value(self, value1: int) -> int:
        return value1

    @external
    def set_value(self, value1: int):
        pass

    @payable
    def fallback(self, num1: int) -> int:
        print("fallback!!")