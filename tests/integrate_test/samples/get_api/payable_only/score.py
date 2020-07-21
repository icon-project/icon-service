from iconservice import *


class PayableOnlyScore(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value(self, value: int) -> int:
        return value

    @external
    @payable
    def set_value(self, value: int):
        pass

    @payable
    def bet(self):
        """function whose invalid decorator combination is invalid
        """
        pass

    @payable
    def fallback(self) -> None:
        pass

    def inner_func(self) -> int:
        return 0
