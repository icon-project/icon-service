import collections
from typing import TypeVar, Optional, Any, Union, Tuple
from ..base.address import Address
from ..base.exception import IconScoreBaseException
from ..database.db import IconScoreDatabase

K = TypeVar('K', int, str, Address)
V = TypeVar('V', int, str, Address, bytes, bool)


class ContainerUtil(object):
    @staticmethod
    def encode_key(key: K) -> bytes:
        prefix = '|'
        fmt = '{}{}'

        key_str = ContainerUtil.__encode_key(key)
        return fmt.format(key_str, prefix).encode()

    @staticmethod
    def encode_value(value: V) -> bytes:
        return ContainerUtil.__encode_value(value).encode()

    @staticmethod
    def __encode_key(key: K) -> str:
        if isinstance(key, int):
            str_key = hex(key)
        elif isinstance(key, str):
            str_key = key
        else:
            raise IconScoreBaseException(f"can't encode key: {key}")
        return str_key

    @staticmethod
    def __encode_value(value: V) -> str:
        if isinstance(value, int):
            byte_value = hex(value)
        elif isinstance(value, str):
            byte_value = value
        elif isinstance(value, Address):
            byte_value = str(value)
        elif isinstance(value, bool):
            byte_value = hex(int(value))
        elif isinstance(value, bytes):
            byte_value = value
        else:
            raise IconScoreBaseException(f"can't encode value: {value}")
        return byte_value

    @staticmethod
    def decode_object(value: bytes, value_type: type) -> Optional[Union[K, V]]:
        obj_value = None
        if value_type == int:
            obj_value = int(value.decode(), 16)
        elif value_type == str:
            obj_value = value.decode()
        elif value_type == Address:
            str_value = value.decode()
            obj_value = Address.from_string(str_value)
        if value_type == bool:
            obj_value = bool(int(value.decode(), 16))
        elif value_type == bytes:
            obj_value = value
        return obj_value

    @staticmethod
    def remove_prefix_from_iters(iter_items: iter) -> iter:
        return ((ContainerUtil.__remove_prefix_from_key(key), value) for key, value in iter_items)

    @staticmethod
    def __remove_prefix_from_key(key_from_bytes: bytes) -> bytes:
        return key_from_bytes[:-1]


class ContainerDBBase(object):

    @staticmethod
    def put_to_db(db: IconScoreDatabase, db_key: str, container: iter) -> None:
        sub_db = db.get_sub_db(ContainerUtil.encode_key(db_key))
        if isinstance(container, dict):
            ContainerDBBase.__put_to_db_internal(sub_db, container.items())
        elif isinstance(container, (list, set, tuple)):
            ContainerDBBase.__put_to_db_internal(sub_db, enumerate(container))

    @staticmethod
    def get_from_db(db: IconScoreDatabase, db_key: str, *args, value_type: type) -> Optional[K]:
        sub_db = db.get_sub_db(ContainerUtil.encode_key(db_key))
        *args, last_arg = args
        for arg in args:
            sub_db = sub_db.get_sub_db(ContainerUtil.encode_key(arg))

        byte_key = sub_db.get(ContainerUtil.encode_key(last_arg))
        if byte_key is None:
            return None
        return ContainerUtil.decode_object(byte_key, value_type)

    @staticmethod
    def __put_to_db_internal(db: IconScoreDatabase, iters: iter) -> None:
        for key, value in iters:
            sub_db = db.get_sub_db(ContainerUtil.encode_key(key))
            if isinstance(value, dict):
                ContainerDBBase.__put_to_db_internal(sub_db, value.items())
            elif isinstance(value, (list, set, tuple)):
                ContainerDBBase.__put_to_db_internal(sub_db, enumerate(value))
            else:
                db_key = ContainerUtil.encode_key(key)
                db_value = ContainerUtil.encode_value(value)
                db.put(db_key, db_value)


class DictDB(object):

    def __init__(self, var_key: str, db: IconScoreDatabase, value_type: type, depth: int=1) -> None:
        self.__db = db.get_sub_db(ContainerUtil.encode_key(var_key))
        self.__value_type = value_type
        self.__depth = depth

    def __setitem__(self, keys: Any, value: V) -> None:
        keys = self.__check_tuple_keys(keys)

        *keys, last_key = keys
        sub_db = self.__db
        for key in keys:
            sub_db = sub_db.get_sub_db(ContainerUtil.encode_key(key))

        byte_value = ContainerUtil.encode_value(value)
        sub_db.put(ContainerUtil.encode_key(last_key), byte_value)

    def __getitem__(self, keys: Any) -> V:
        keys = self.__check_tuple_keys(keys)

        *keys, last_key = keys
        sub_db = self.__db
        for key in keys:
            sub_db = sub_db.get_sub_db(ContainerUtil.encode_key(key))
        return self.__decode_object(sub_db.get(ContainerUtil.encode_key(last_key)))

    def len(self, keys: Any=None) -> int:
        keys = self.__check_tuple_keys(keys, is_strict_depth=False)
        sub_db = self.__find_sub_db_from_keys(self.__db, keys)
        return len([item for item in sub_db.iterator()])

    def iter(self, keys: Any=None) -> iter:
        keys = self.__check_tuple_keys(keys, is_strict_depth=False)
        sub_db = self.__find_sub_db_from_keys(self.__db, keys)
        return ContainerUtil.remove_prefix_from_iters(sub_db.iterator())

    def __check_tuple_keys(self, keys: Any, is_strict_depth: bool=True) -> Tuple[K, ...]:

        if keys is None:
            keys = tuple()
        elif not isinstance(keys, collections.Iterable):
            keys = tuple([keys])

        for key in keys:
            if not isinstance(key, (int, str, Address)):
                raise IconScoreBaseException(f"can't cast args {type(key)} : {key}")

        if is_strict_depth:
            if not len(keys) == self.__depth:
                raise IconScoreBaseException('depth over')
        else:
            if len(keys) >= self.__depth:
                raise IconScoreBaseException('depth over')
        return keys

    def __decode_object(self, value: bytes) -> Optional[V]:
        if value is None:
            return None
        return ContainerUtil.decode_object(value, self.__value_type)

    @staticmethod
    def __find_sub_db_from_keys(db: IconScoreDatabase, keys: Tuple[K, ...]) -> IconScoreDatabase:
        sub_db = db
        for key in keys:
            sub_db = sub_db.get_sub_db(ContainerUtil.encode_key(key))
        return sub_db


class VarDB(object):

    def __init__(self, var_key: str, db: IconScoreDatabase, value_type: type) -> None:
        self.__db = db
        self.__var_byte_key = ContainerUtil.encode_key(var_key)
        self.__value_type = value_type

    def set(self, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        self.__db.put(self.__var_byte_key, byte_value)

    def get(self) -> Optional[V]:
        return self.__decode_object(self.__db.get(self.__var_byte_key))

    def __decode_object(self, value: bytes) -> Optional[V]:
        if value is None:
            return None
        return ContainerUtil.decode_object(value, self.__value_type)
