from iconservice import *


class TestScorePass(IconScoreBase):

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
    def get_value1(self) -> int:
        return 0

    @payable
    def fallback(self) -> None:
        print("fallback!!")
