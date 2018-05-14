from iconservice import *


class CallClass1(IconScoreBase):
    def genesis_init(self, *args, **kwargs) -> None:
        pass

    def __init__(self, db: IconScoreDatabase, owner: Address):
        super().__init__(db, owner)

    @external(readonly=True)
    def func1(self):
        pass

    @external
    def func2(self):
        pass

    @external(readonly=True)
    @payable
    def func3(self):
        pass

    @external
    @payable
    def func4(self):
        pass

    @payable
    def func5(self):
        pass

    def func6(self):
        pass

    # @external
    @payable
    def fallback(self):
        pass