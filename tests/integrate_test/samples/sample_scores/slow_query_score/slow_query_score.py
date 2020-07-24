# -*- coding: utf-8 -*-

"""
Example

Problem with Health Check : query thread issue
"""

from iconservice import *
TAG = 'SlowQueryScore'


class SlowQueryScore(IconScoreBase):
    """ Slow Query Score """

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, db: IconScoreDatabase):
        super().__init__(db)

    def on_install(self):
        super().on_install()

    def on_update(self):
        super().on_update()

    @external(readonly=True)
    def slow_query(self) -> int:
        for i in range(300000):
            sha3_256(b'')
        return 1
