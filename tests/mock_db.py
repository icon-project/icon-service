from iconservice.database.db import KeyValueDatabase
from iconservice.database.db import ContextDatabase, IconScoreDatabase
from iconservice.base.address import AddressPrefix
from typing import Optional
from tests import create_address


class MockPlyvelDatabase(KeyValueDatabase):
    """Plyvel database wrapper
    """

    @staticmethod
    def make_db() -> dict:
        return dict()

    def __init__(self, db: dict) -> None:
        self._db = db

    def get(self, key: bytes) -> Optional[bytes]:
        if key not in self._db:
            return None
        return self._db[key]

    def put(self, key: bytes, value: bytes) -> None:
        self._db[key] = value

    def delete(self, key: bytes) -> None:
        del self._db[key]

    def close(self) -> None:
        if self._db:
            self._db.close()
            self._db = None

    def get_sub_db(self, key: bytes):
        return MockPlyvelDatabase(self.make_db())

    def write_batch(self, states: dict) -> None:
        pass


def create_mock_icon_score_db():
    mock_db = MockPlyvelDatabase(MockPlyvelDatabase.make_db())
    address = create_address(AddressPrefix.EOA, b'test_db')
    context_db = ContextDatabase(mock_db)
    return IconScoreDatabase(address, context_db)
