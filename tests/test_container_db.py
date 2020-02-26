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

    def _hash_key(self, key: bytes) -> bytes:
        """All key is hashed and stored
        to StateDB to avoid key conflicts among SCOREs

        :params key: key passed by SCORE
        :return: key bytes
        """

        data = [SCORE_ADDR_BYTES]
        data.append(b'0x10')
        data.append(key)

        return b'|'.join(data)

    def _put(self, range_cnt: int):
        db = plyvel.DB(f"{DB_PATH}_{range_cnt}", create_if_missing=True)

        for i in range(range_cnt):
            key = f"{i}".encode()
            hashed_key = self._hash_key(key)
            hashed_key = self._hash_key(key)
            # hashed_key = key
            db.put(hashed_key, SCORE_ADDR_BYTES)

    def _get(self, range_cnt: int):
        db = plyvel.DB(f"{DB_PATH}_{range_cnt}", create_if_missing=True)

        start = time.time()

        for i in range(range_cnt):
            key = f"{i}".encode()
            hashed_key = self._hash_key(key)
            hashed_key = self._hash_key(key)
            # hashed_key = key
            db.get(hashed_key)

        print(f"_get {range_cnt} :", time.time() - start)

    def test_put(self):
        for i in RANGE_LIST:
            rmtree(f"{DB_PATH}_{i}")

        for i in RANGE_LIST:
            self._put(i)

    def test_get(self):
        for i in RANGE_LIST:
            self._get(i)


@unittest.skipIf(condition=DISABLE, reason="DISABLE")
class TestPrebuildForContainerDB(unittest.TestCase):

    """
    Prebuild DB for ContainerDB get
    """

    def _create_db(self, range_cnt: int):
        _db = KeyValueDatabase.from_path(f"{DB_PATH}{range_cnt}")
        context_db = ContextDatabase(_db)
        return IconScoreDatabase(SCORE_ADDR, context_db)

    def _create_new_db(self, range_cnt: int):
        self.db = self._create_db(range_cnt)
        self._context = IconScoreContext(IconScoreContextType.DIRECT)
        self._context.current_address = self.db.address
        self._context.revision = REVISION
        ContextContainer._push_context(self._context)

        ## LOGIC

        var_db = VarDB(VAR_DB, self.db, value_type=int)
        array_db = ArrayDB(ARRAY_DB, self.db, value_type=Address)
        dict_db1 = DictDB(DICT_DB1, self.db, value_type=Address)
        dict_db2 = DictDB(DICT_DB2, self.db, value_type=int)

        for i in range(range_cnt):
            addr: 'Address' = create_address()
            array_db.put(addr)
            dict_db1[i] = addr
            dict_db2[addr] = i
        var_db.set(i)

        ContextContainer._pop_context()

    def test_create_db(self):
        for i in RANGE_LIST:
            rmtree(f"{DB_PATH}{i}")

        for i in RANGE_LIST:
            self._create_new_db(i)


def _create_db(range_cnt: int):
    _db = KeyValueDatabase.from_path(f"{DB_PATH}{range_cnt}")
    context_db = ContextDatabase(_db)
    return IconScoreDatabase(SCORE_ADDR, context_db)


# for profile
def _for_profile_function(range_cnt: int):
    db = _create_db(range_cnt)
    _context = IconScoreContext(IconScoreContextType.DIRECT)
    _context.current_address = db.address
    _context.revision = REVISION
    ContextContainer._push_context(_context)

    array_db = ArrayDB(ARRAY_DB, db, value_type=Address)
    for i in range(range_cnt):
        a = array_db[i]

    ContextContainer._clear_context()


@unittest.skipIf(condition=DISABLE, reason="DISABLE")
class TestIconContainerDB(unittest.TestCase):
    def _setup(self, range_cnt: int):
        self.db = _create_db(range_cnt)
        self._context = IconScoreContext(IconScoreContextType.DIRECT)
        self._context.current_address = self.db.address
        self._context.revision = REVISION
        ContextContainer._push_context(self._context)

    def _tear_down(self):
        ContextContainer._clear_context()
        self.db = None
        # rmtree(f"{DB_PATH}{range_cnt}")

    def _test1(self, range_cnt: int):
        self._setup(range_cnt)

        array_db = ArrayDB(ARRAY_DB, self.db, value_type=Address)
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = array_db[i]

        print(f"_test1 {range_cnt} :", time.time() - start)

        self._tear_down()

    def _test2(self, range_cnt: int):
        self._setup(range_cnt)

        dict_db1 = DictDB(DICT_DB1, self.db, value_type=Address)
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = dict_db1[i]

        print(f"_test2 {range_cnt} :", time.time() - start)

        self._tear_down()

    def _test3(self, range_cnt: int):
        self._setup(range_cnt)

        array_db = ArrayDB(ARRAY_DB, self.db, value_type=Address)
        dict_db2 = DictDB(DICT_DB2, self.db, value_type=int)
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = dict_db2[array_db[0]]

        print(f"_test3 {range_cnt} :", time.time() - start)

        self._tear_down()

    def _test4(self, range_cnt: int):
        self._setup(range_cnt)

        var_db = VarDB(VAR_DB, self.db, value_type=Address)
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = var_db.get()

        print(f"_test4 {range_cnt} :", time.time() - start)

        self._tear_down()

    def _test5(self, range_cnt: int):
        self._setup(range_cnt)

        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = self.db.get(ContainerUtil.encode_key(VAR_DB))

        print(f"_test5 {range_cnt} :", time.time() - start)

        self._tear_down()

    def _test6(self, range_cnt: int):
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            ContainerUtil.encode_key(VAR_DB)

        print(f"_test6 {range_cnt} :", time.time() - start)

    def _test7(self, range_cnt: int):
        self._setup(range_cnt)

        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = self.db._context_db.get(self._context,
                                        b'\x01\xf1\xbf6o\x19\n\xac\xaa\x83\xba\xd2d\x1e\xe1\x06\xe9\x04\x10\x96\xe4|test_var')

        print(f"_test7 {range_cnt} :", time.time() - start)

        self._tear_down()

    def _test8(self, range_cnt: int):
        self._setup(range_cnt)

        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = self.db._hash_key(ContainerUtil.encode_key(VAR_DB))

        print(f"_test8 {range_cnt} :", time.time() - start)

        self._tear_down()

    def _test9(self, range_cnt: int):
        address: 'Address' = create_address()
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = address.to_bytes()

        print(f"_test9 {range_cnt} :", time.time() - start)

    def _test10(self, range_cnt: int):
        address: 'Address' = create_address()
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = b'|'.join([address.to_bytes(), address.to_bytes(), address.to_bytes(), address.to_bytes()])

        print(f"_test10 {range_cnt} :", time.time() - start)

    def _test11(self, range_cnt: int):
        address: 'Address' = create_address()
        data = [address.to_bytes(), address.to_bytes(), address.to_bytes(), address.to_bytes()]
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = b'|'.join(data)

        print(f"_test12 {range_cnt} :", time.time() - start)

    def _test12(self, range_cnt: int):
        address: 'Address' = create_address()
        data = [address.to_bytes(), address.to_bytes(), address.to_bytes(), address.to_bytes()]
        start = time.time()

        # LOGIC

        for i in range(range_cnt):
            a = address.to_bytes() + b'|' + address.to_bytes() + b'|' + address.to_bytes() + b'|' + address.to_bytes()

        print(f"_test12 {range_cnt} :", time.time() - start)

    def test_performance(self):
        for i in RANGE_LIST:
            self._test4(range_cnt=i)

    def test_profile(self):
        from cProfile import Profile
        from pstats import Stats

        # LOGIC
        p = Profile()
        p.runcall(_for_profile_function, 100_000)

        stats = Stats(p)
        stats.print_stats()
