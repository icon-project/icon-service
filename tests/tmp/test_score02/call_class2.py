from iconservice import *
from .call_class1 import CallClass1


class CallClass2(CallClass1):
    def on_install(self, params) -> None:
        pass

    def on_update(self, params) -> None:
        pass

    def __init__(self, db: IconScoreDatabase, owner: Address):
        super().__init__(db, owner)

    def func1(self):
        pass
