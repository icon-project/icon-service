from iconservice import *


class SampleArrayDB(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._array_db = ArrayDB('array_db', db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_values(self) -> list:
        ret = []
        for item in self._array_db:
            ret.append(item)
        return ret

    @external
    def set_values(self, i: int) -> None:
        self._array_db.put(i)
