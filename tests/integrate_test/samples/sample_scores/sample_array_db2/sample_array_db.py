from iconservice import *


class SampleArrayDB(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._array_db = ArrayDB('array_db', db, value_type=Address)

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
    def add_value(self) -> None:
        address: Address = Address.from_string(f"hx{'0'*40}")
        self._array_db.put(address)

    @external(readonly=True)
    def check(self, address: Address) -> bool:
        return address in self._array_db
