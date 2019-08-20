from iconservice import *


class SampleScore(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._table = DictDB('value', db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external
    def func(self):
        for i in range(100):
            self._table[i] = 10 ** 20

        for i in range(100):
            self._table.remove(i)
