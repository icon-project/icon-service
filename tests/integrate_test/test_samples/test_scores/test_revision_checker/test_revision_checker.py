from iconservice import *


class TestRevisionChecker(IconScoreBase):

    @eventlog(indexed=1)
    def RevisionChecked(self, revision: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external
    def checkRevision(self) -> None:
        self.RevisionChecked(self._context.revision)
