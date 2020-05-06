from iconservice import *
import os


class SampleScoreUsingImportOs(IconScoreBase):
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(
        self, value: "Address" = None, value1: Address = None, value2: int = None
    ) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def hello(self) -> int:
        return 0
