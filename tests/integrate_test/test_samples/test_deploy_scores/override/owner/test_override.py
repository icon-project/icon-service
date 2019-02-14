from iconservice import *


class TestOverride(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def test_func(self) -> int:
        return 0

    def __call(self):
        pass

