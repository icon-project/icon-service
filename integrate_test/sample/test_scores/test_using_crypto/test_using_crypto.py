from iconservice import *


class TestUsingCrypto(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value(self, value: str) -> int:
        sha = self.crypto.sha3_256(value.encode())
        return sha.hexdigest()
