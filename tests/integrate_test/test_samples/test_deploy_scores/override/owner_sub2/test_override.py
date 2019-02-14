from iconservice import *
from .base.base import TestBase


class TestOverride(TestBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)


