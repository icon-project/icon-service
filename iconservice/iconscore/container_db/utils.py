from typing import Optional, Any, Union, TYPE_CHECKING

from ...base.address import Address
from ...base.exception import InvalidParamsException
from ...database.score_db.utils import K, V
from ...utils import int_to_bytes, bytes_to_int

if TYPE_CHECKING:
    from ...database.db import IconScoreDatabase, IconScoreSubDatabase
    from . import ContainerDBBase


class Utils:
    @classmethod
    def get_container_id(cls, container: 'ContainerDBBase') -> bytes:
        return container.get_container_id()

    @classmethod
    def encode_key(cls, key: K) -> bytes:
        """Create a key passed to DB

        :param key:
        :return:
        """
        if key is None:
            raise InvalidParamsException('key is None')

        if isinstance(key, int):
            bytes_key = int_to_bytes(key)
        elif isinstance(key, str):
            bytes_key = key.encode('utf-8')
        elif isinstance(key, Address):
            bytes_key = key.to_bytes()
        elif isinstance(key, bytes):
            bytes_key = key
        else:
            raise InvalidParamsException(f'Unsupported key type: {type(key)}')
        return bytes_key

    @classmethod
    def encode_value(cls, value: V) -> bytes:
        if isinstance(value, int):
            byte_value = int_to_bytes(value)
        elif isinstance(value, str):
            byte_value = value.encode('utf-8')
        elif isinstance(value, Address):
            byte_value = value.to_bytes()
        elif isinstance(value, bool):
            byte_value = int_to_bytes(int(value))
        elif isinstance(value, bytes):
            byte_value = value
        else:
            raise InvalidParamsException(f'Unsupported value type: {type(value)}')
        return byte_value

    @classmethod
    def decode_object(cls, value: bytes, value_type: type) -> Optional[Union[K, V]]:
        if value is None:
            return cls.get_default_value(value_type)

        obj_value = None
        if value_type == int:
            obj_value = bytes_to_int(value)
        elif value_type == str:
            obj_value = value.decode()
        elif value_type == Address:
            obj_value = Address.from_bytes(value)
        if value_type == bool:
            obj_value = bool(bytes_to_int(value))
        elif value_type == bytes:
            obj_value = value
        return obj_value

    @classmethod
    def get_default_value(cls, value_type: type) -> Any:
        if value_type == int:
            return 0
        elif value_type == str:
            return ""
        elif value_type == bool:
            return False
        return None

    @classmethod
    def remove_prefix_from_iters(cls, iter_items: iter) -> iter:
        return ((cls.__remove_prefix_from_key(key), value) for key, value in iter_items)

    @classmethod
    def __remove_prefix_from_key(cls, key_from_bytes: bytes) -> bytes:
        return key_from_bytes[:-1]

    @classmethod
    def put_to_db(
            cls,
            db: 'IconScoreDatabase',
            db_key: str,
            container: iter
    ):
        """
        Only V1 supported.

        TODO V2 support.

        :param db:
        :param db_key:
        :param container:
        :return:
        """
        sub_db = db.get_sub_db(cls.encode_key(db_key))
        if isinstance(container, dict):
            cls.__put_to_db_internal(sub_db, container.items())
        elif isinstance(container, (list, set, tuple)):
            cls.__put_to_db_internal(sub_db, enumerate(container))

    @classmethod
    def get_from_db(
            cls,
            db: 'IconScoreDatabase',
            db_key: str,
            *args,
            value_type: type
    ) -> Optional[K]:
        """
        Only V1 supported.

        TODO V2 support.

        :param db:
        :param db_key:
        :param args:
        :param value_type:
        :return:
        """

        sub_db = db.get_sub_db(cls.encode_key(db_key))
        *args, last_arg = args
        for arg in args:
            sub_db = sub_db.get_sub_db(cls.encode_key(arg))

        byte_key = sub_db.get(cls.encode_key(last_arg))
        if byte_key is None:
            return cls.get_default_value(value_type)
        return cls.decode_object(byte_key, value_type)

    @classmethod
    def __put_to_db_internal(
            cls,
            db: Union['IconScoreDatabase', 'IconScoreSubDatabase'],
            iters: iter
    ):
        """
        Only V1 supported.

        TODO V2 support.

        :param db:
        :param iters:
        :return:
        """

        for key, value in iters:
            sub_db = db.get_sub_db(cls.encode_key(key))
            if isinstance(value, dict):
                cls.__put_to_db_internal(sub_db, value.items())
            elif isinstance(value, (list, set, tuple)):
                cls.__put_to_db_internal(sub_db, enumerate(value))
            else:
                db_key = cls.encode_key(key)
                db_value = cls.encode_value(value)
                db.put(db_key, db_value)
