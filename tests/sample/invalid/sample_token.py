from iconservice import *


class SampleToken(object):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    @external(readonly=True)
    def hello(self) -> str:
        print(f'Hello, world!')
        return "Hello"
