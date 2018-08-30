from iconservice import *
from .base import BaseScore


class GetApi(BaseScore):

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
    def get_value1(self, value1: int) -> int:
        return value1

    @external(readonly=True)
    def get_value2(self, value2: int) -> int:
        return value2

    @payable
    def fallback(self) -> None:
        print("fallback!!")
