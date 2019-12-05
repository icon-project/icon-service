from iconservice import *


GLOBAL_DICT = {"a": 1, "b": [2, 3], "c": {"d": 4}}
GLOBAL_LIST = [1, {"a": 1}, ["c", 2]]
GLOBAL_TUPLE = ({"a": 1}, 2, ["c", 2])


class GlobalVariableScore(IconScoreBase):
    """Used to check if global score data is corrupted by calling score query api
    """

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def hello(self) -> str:
        return "hello"

    @external(readonly=True)
    def getGlobalDict(self) -> dict:
        return GLOBAL_DICT

    @external(readonly=True)
    def getGlobalList(self) -> list:
        return GLOBAL_LIST

    @external(readonly=True)
    def getGlobalTuple(self) -> list:
        """The mismatch of return value type hint is intended for test_integrate_global_variable_score unittest
        """
        return GLOBAL_TUPLE
