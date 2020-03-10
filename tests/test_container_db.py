import unittest

import time
import plyvel

from iconservice import VarDB, ArrayDB, DictDB, Address
from iconservice.database.db import KeyValueDatabase, ContextDatabase, IconScoreDatabase
from iconservice.icon_constant import IconScoreContextType
from iconservice.iconscore.icon_container_db import ContainerUtil
from iconservice.iconscore.icon_score_context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests import create_address, rmtree
from tests.mock_db import MockKeyValueDatabase

DB_PATH: str = ".mycom22_db"
VAR_DB: str = "test_var"
ARRAY_DB: str = "test_array"
DICT_DB1: str = "test_dict1"
DICT_DB2: str = "test_dict2"
SCORE_ADDR: 'Address' = create_address(1, b'0')

REVISION: int = 10
INDEX: int = 7

DISABLE = True

# RANGE_LIST = [10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000]
RANGE_LIST = [5000000]

SCORE_ADDR_BYTES = SCORE_ADDR.to_bytes()


@unittest.skipIf(condition=DISABLE, reason="DISABLE")
class TestPlyvelDB(unittest.TestCase):
    """
    Native PlyvelDB performance check
    """

    def _hash_key_bypass(self, key: bytes) -> bytes:
        return key

    def _hash_key_origin(self, key: bytes) -> bytes:
        data = [SCORE_ADDR.to_bytes()]
        data.append(b'0x10')
        data.append(key)
        return b'|'.join(data)

    def _hash_key_cache_bytes(self, key: bytes) -> bytes:
        data = [SCORE_ADDR_BYTES]
        data.append(b'0x10')
        data.append(key)
        return b'|'.join(data)

    def _hash_key_cache_bytes_and_remove_append(self, key: bytes) -> bytes:
        data = [SCORE_ADDR_BYTES, b'0x10', key]
        return b'|'.join(data)

    def _put(self, range_cnt: int, hash_func: callable):
        db = plyvel.DB(f"{DB_PATH}_{range_cnt}", create_if_missing=True)

        for i in range(range_cnt):
            key = f"{i}".encode()
            hashed_key = hash_func(key)
            db.put(hashed_key, SCORE_ADDR_BYTES)

    def _get(self, range_cnt: int, hash_func: callable):
        db = plyvel.DB(f"{DB_PATH}_{range_cnt}", create_if_missing=True)

        start = time.time()

        for i in range(range_cnt):
            key = f"{i}".encode()
            hashed_key = hash_func(key)
            db.get(hashed_key)

        print(f"_get[{hash_func.__name__} {range_cnt} :", time.time() - start)

    def test_put(self):
        for i in RANGE_LIST:
            rmtree(f"{DB_PATH}_{i}")

        for i in RANGE_LIST:
            self._put(i, self._hash_key_bypass)

    def test_get(self):
        for i in RANGE_LIST:
            self._get(i, self._hash_key_bypass)


@unittest.skipIf(condition=DISABLE, reason="DISABLE")
class TestPrebuildForContainerDB(unittest.TestCase):
    """
    Prebuild DB for ContainerDB get
    """

    def _create_plyvel_db(self, range_cnt: int):
        _db = KeyValueDatabase.from_path(f"{DB_PATH}{range_cnt}")
        context_db = ContextDatabase(_db)
        return IconScoreDatabase(SCORE_ADDR, context_db)

    def _create_new_db(self, range_cnt: int):
        self.db = self._create_plyvel_db(range_cnt)
        self._context = IconScoreContext(IconScoreContextType.DIRECT)
        self._context.current_address = self.db.address
        self._context.revision = REVISION
        ContextContainer._push_context(self._context)

        ## LOGIC

        var_db = VarDB(VAR_DB, self.db, value_type=int)
        array_db = ArrayDB(ARRAY_DB, self.db, value_type=Address)
        dict_db1 = DictDB(DICT_DB1, self.db, value_type=Address)
        dict_db2 = DictDB(DICT_DB2, self.db, value_type=int)

        index: int = 0
        for index in range(range_cnt):
            addr: 'Address' = create_address()
            array_db.put(addr)
            dict_db1[index] = addr
            dict_db2[addr] = index
        var_db.set(index)

        ContextContainer._pop_context()

    def test_create_db(self):
        for i in RANGE_LIST:
            rmtree(f"{DB_PATH}{i}")

        for i in RANGE_LIST:
            self._create_new_db(i)


def _create_plyvel_db(range_cnt: int):
    _db = KeyValueDatabase.from_path(f"{DB_PATH}{range_cnt}")
    context_db = ContextDatabase(_db)
    return IconScoreDatabase(SCORE_ADDR, context_db)


def _create_mock_db(range_cnt: int):
    mock_db = MockKeyValueDatabase.create_db()
    context_db = ContextDatabase(mock_db)
    return IconScoreDatabase(SCORE_ADDR, context_db)


# for profile
def _for_profile_function(range_cnt: int, _create_db_func: callable):
    db = _create_db_func(range_cnt)
    _context = IconScoreContext(IconScoreContextType.DIRECT)
    _context.current_address = db.address
    _context.revision = REVISION
    ContextContainer._push_context(_context)

    array_db = ArrayDB(ARRAY_DB, db, value_type=Address)

    for index in range(range_cnt):
        addr: 'Address' = create_address()
        array_db.put(addr)

    for i in range(range_cnt):
        a = array_db[i]

    ContextContainer._clear_context()


@unittest.skipIf(condition=DISABLE, reason="DISABLE")
class TestIconContainerDB(unittest.TestCase):
    def _setup(self, range_cnt: int, _create_db_func: callable):
        self.db = _create_db_func(range_cnt)
        self._context = IconScoreContext(IconScoreContextType.DIRECT)
        self._context.current_address = self.db.address
        self._context.revision = REVISION
        ContextContainer._push_context(self._context)

    def _tear_down(self):
        ContextContainer._clear_context()
        self.db = None
        # rmtree(f"{DB_PATH}{range_cnt}")

    def _var_db_perfomance(self,
                           range_cnt: int,
                           _create_db_func: callable):
        self._setup(range_cnt, _create_db_func)

        var_db = VarDB(VAR_DB, self.db, value_type=Address)
        var_db.set(0)

        start = time.time()

        # LOGIC
        for i in range(range_cnt):
            a = var_db.get()

        print(f"_var_db_perfomance [{_create_db_func.__name__} {range_cnt} :", time.time() - start)

        self._tear_down()

    def _array_db_perfomance(self,
                             range_cnt: int,
                             _create_db_func: callable):
        self._setup(range_cnt, _create_db_func)

        array_db = ArrayDB(ARRAY_DB, self.db, value_type=Address)
        for index in range(range_cnt):
            addr: 'Address' = create_address()
            array_db.put(addr)

        start = time.time()

        # LOGIC
        for i in range(range_cnt):
            a = array_db[i]

        print(f"_array_db_perfomance [{_create_db_func.__name__} {range_cnt} :", time.time() - start)

        self._tear_down()

    def _dict_db_perfomance(self,
                            range_cnt: int,
                            _create_db_func: callable):
        self._setup(range_cnt, _create_db_func)

        dict_db = DictDB(DICT_DB1, self.db, value_type=Address)
        for index in range(range_cnt):
            addr: 'Address' = create_address()
            dict_db[index] = addr
        start = time.time()

        # LOGIC
        for i in range(range_cnt):
            a = dict_db[i]

        print(f"_dict_db_perfomance [{_create_db_func.__name__} {range_cnt} :", time.time() - start)

        self._tear_down()

    def _complex_db_perfomance(self,
                               range_cnt: int,
                               _create_db_func: callable):
        self._setup(range_cnt, _create_db_func)

        array_db = ArrayDB(ARRAY_DB, self.db, value_type=Address)
        dict_db = DictDB(DICT_DB2, self.db, value_type=Address)

        for index in range(range_cnt):
            addr: 'Address' = create_address()
            array_db.put(addr)
            dict_db[addr] = index

        start = time.time()

        # LOGIC
        for i in range(range_cnt):
            a = dict_db[array_db[0]]

        print(f"_complex_db_perfomance [{_create_db_func.__name__} {range_cnt} :", time.time() - start)

        self._tear_down()

    def test_var_db_performance(self):
        for count in RANGE_LIST:
            self._var_db_perfomance(count, _create_mock_db)

    def test_array_db_performance(self):
        for count in RANGE_LIST:
            self._array_db_perfomance(count, _create_mock_db)

    def test_dict_db_performance(self):
        for count in RANGE_LIST:
            self._dict_db_perfomance(count, _create_mock_db)

    def test_complex_db_performance(self):
        for count in RANGE_LIST:
            self._complex_db_perfomance(count, _create_mock_db)

    def test_profile(self):
        from cProfile import Profile
        from pstats import Stats

        # LOGIC
        p = Profile()
        p.runcall(_for_profile_function, 100_000, _create_mock_db)

        stats = Stats(p)
        stats.print_stats()
