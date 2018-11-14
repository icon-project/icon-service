import threading
import random
import time
import unittest

from iconservice.database.db import ContextDatabase, IconScoreDatabase
from iconservice.iconscore.icon_container_db import ArrayDB
from iconservice.iconscore.icon_score_context import ContextContainer, IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
from tests import create_address
from tests.mock_db import MockKeyValueDatabase


class TestIconContainerDB(unittest.TestCase):

    def setUp(self):
        self.db = self.create_db()
        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.DIRECT)

        ContextContainer._push_context(self._context)
        pass

    def tearDown(self):
        ContextContainer._clear_context()
        self.db = None
        pass

    @staticmethod
    def create_db():
        mock_db = MockKeyValueDatabase.create_db()
        context_db = ContextDatabase(mock_db)
        return IconScoreDatabase(create_address(), context_db)

    def test_array_db(self):
        for i in range(1, 10):
            t = threading.Thread(target=self._thread_func, args=(i, self.db))
            t.start()

    def _thread_func(self, index, db):
        time.sleep(random.random())
        array = ArrayDB(str(index), db, value_type=int)

        for i in range(0, index):
            array.put(i)

        ret = sum(array)
        expect_ret = sum([i for i in range(0, index)])

        print(ret, expect_ret)
        self.assertEqual(ret, expect_ret)
