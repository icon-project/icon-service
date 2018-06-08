from iconservice import *


class CallClass1(IconScoreBase):
    def on_install(self, params: dict) -> None:
        pass

    def on_update(self, params: dict) -> None:
        pass

    def __init__(self, db: IconScoreDatabase, owner: Address):
        super().__init__(db, owner)

    @external(readonly=True)
    def func1(self):
        pass

    @external
    def func2(self):
        pass

    @payable
    @external
    def func3(self):
        pass

    @payable
    @external
    def func4(self):
        pass

    @payable
    def func5(self):
        pass

    def func6(self):
        pass

    @payable
    def fallback(self):
        pass
