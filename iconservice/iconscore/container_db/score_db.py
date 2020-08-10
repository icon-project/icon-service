from typing import Optional, TYPE_CHECKING, List
from ...database.score_db.utils import KeyElement, DICT_DB_ID

if TYPE_CHECKING:
    from ...base.address import Address
    from ...database.db import IconScoreDatabase, IconScoreSubDatabase


class ScoreDatabase:
    def __init__(self, db: 'IconScoreDatabase'):
        self._db: 'IconScoreDatabase' = db

    @property
    def address(self) -> 'Address':
        return self._db.address

    def get(self, key: bytes) -> Optional[bytes]:

        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """

        keys: List['KeyElement'] = self._make_key_elements(key=key)
        return self._db.get(keys=keys)

    def put(self, key: bytes, value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        keys: List['KeyElement'] = self._make_key_elements(key=key)
        self._db.put(keys=keys, value=value)

    def delete(self, key: bytes):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        key: List['KeyElement'] = self._make_key_elements(key=key)
        self._db.delete(key)

    def get_sub_db(self, prefix: bytes) -> 'ScoreSubDatabase':
        keys: List['KeyElement'] = self._make_key_elements(key=prefix)
        db: 'IconScoreSubDatabase' = self._db.get_sub_db(keys=keys)
        return ScoreSubDatabase(db=db)

    @classmethod
    def _make_key_elements(cls, key: bytes) -> List['KeyElement']:
        return [KeyElement(keys=[key], container_id=DICT_DB_ID)]


class ScoreSubDatabase:
    def __init__(self, db: 'IconScoreSubDatabase'):
        self._db: 'IconScoreSubDatabase' = db

    @property
    def address(self) -> 'Address':
        return self._db.address

    def get(self, key: bytes) -> Optional[bytes]:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        keys: List['KeyElement'] = self._make_key_elements(key=key)
        return self._db.get(keys=keys)

    def put(self, key: bytes, value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        keys: List['KeyElement'] = self._make_key_elements(key=key)
        self._db.put(keys=keys, value=value)

    def delete(self, key: bytes):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        keys: List['KeyElement'] = self._make_key_elements(key=key)
        self._db.delete(keys=keys)

    def get_sub_db(
            self,
            prefix: bytes,
    ) -> 'ScoreSubDatabase':

        keys: List['KeyElement'] = self._make_key_elements(key=prefix)
        db: 'IconScoreSubDatabase' = self._db.get_sub_db(keys=keys)
        return ScoreSubDatabase(db=db)

    @classmethod
    def _make_key_elements(cls, key: bytes) -> List['KeyElement']:
        return [KeyElement(keys=[key], container_id=DICT_DB_ID)]
