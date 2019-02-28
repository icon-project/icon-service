from iconservice import *


class MemberVariableScore(IconScoreBase):
    """Score class to check whether that consensus failure by undefined member variable is fixed
    """

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._name = '__init__'

    def on_install(self) -> None:
        super().on_install()
        # self._name member variable should be defined in __init__().
        self._name = 'on_install'

    def on_update(self) -> None:
        super().on_update()
        self._name = 'on_update'

    @external(readonly=True)
    def getName(self) -> str:
        # An exception is expected in the case when on_install() was not called.
        return self._name
