from iconservice import *


class SampleScoreCallReflex(IconScoreBase):
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external
    def invoke(self, index: int) -> None:
        print(f"index:{index}")
        self.call(self.msg.sender, "invoke", {"index": index + 1})

    @external(readonly=True)
    def query(self, index: int) -> int:
        return self.call(self.msg.sender, "query", {"index": index + 1})
