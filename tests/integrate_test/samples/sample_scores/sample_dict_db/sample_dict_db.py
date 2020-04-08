# -*- coding: utf-8 -*-

"""
Example

Problem with DictDB : cannot iterate
https://forum.icon.community/t/problem-with-dictdb-cannot-iterate/484
"""

from iconservice import *
TAG = 'IterableDictDB'


class IterableDictDB(IconScoreBase):
    """ IterableDictDB SCORE Base implementation """

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._dict = DictDB('DICT', db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external
    def create_item(self, key: str, value: int) -> None:
        self._dict[key] = value

    @external(readonly=True)
    def get_items(self) -> list:
        items = []
        for item in self._dict:
            items.append(item)
        return items
