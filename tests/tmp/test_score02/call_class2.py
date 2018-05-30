from iconservice import *
from .call_class1 import CallClass1
from print_func.print_func import func_test
from test_func.test_func import test1_func


class CallClass2(CallClass1):
    def on_install(self, params) -> None:
        pass

    def on_update(self, params) -> None:
        pass

    def __init__(self, db: IconScoreDatabase, owner: Address):
        # super().__init__(db, owner)
        pass

    def func1(self):
        pass

    def print_test(self):
        func_test()
        test1_func()

