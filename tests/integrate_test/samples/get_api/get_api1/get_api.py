from iconservice import *
from .base import BaseScore


class Person(TypedDict):
    name: str
    age: int
    wallet: Address


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
    def get_value(self, value1: int) -> int:
        return value1

    @payable
    def fallback(self) -> None:
        print("fallback!!")

    @external(readonly=True)
    def get_person(self) -> Person:
        return {
            "name": "hello",
            "age": 15,
            "wallet": SYSTEM_SCORE_ADDRESS
        }
