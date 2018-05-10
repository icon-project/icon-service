import collections
from typing import TypeVar, Optional, Any, Union, Tuple, TYPE_CHECKING
from ..base.address import Address
from ..base.exception import ContainerDBException
from collections import Iterator

K = TypeVar('K', int, str, Address)
V = TypeVar('V', int, str, Address, bytes, bool)

if TYPE_CHECKING:
    from ..database.db import IconScoreDatabase


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
        elif isinstance(key, Address):
            str_key = str(key)
        else:
            raise ContainerDBException(f"can't encode key: {key}")
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
            raise ContainerDBException(f"can't encode value: {value}")
        return byte_value

    @staticmethod
    def decode_object(value: bytes, value_type: type) -> Optional[Union[K, V]]:
        if value is None:
            return return_default_value(value_type)

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

    @staticmethod
    def put_to_db(db: 'IconScoreDatabase', db_key: str, container: iter) -> None:
        sub_db = db.get_sub_db(ContainerUtil.encode_key(db_key))
        if isinstance(container, dict):
            ContainerUtil.__put_to_db_internal(sub_db, container.items())
        elif isinstance(container, (list, set, tuple)):
            ContainerUtil.__put_to_db_internal(sub_db, enumerate(container))

    @staticmethod
    def get_from_db(db: 'IconScoreDatabase', db_key: str, *args, value_type: type) -> Optional[K]:
        sub_db = db.get_sub_db(ContainerUtil.encode_key(db_key))
        *args, last_arg = args
        for arg in args:
            sub_db = sub_db.get_sub_db(ContainerUtil.encode_key(arg))

        byte_key = sub_db.get(ContainerUtil.encode_key(last_arg))
        if byte_key is None:
            return return_default_value(value_type)
        return ContainerUtil.decode_object(byte_key, value_type)

    @staticmethod
    def __put_to_db_internal(db: 'IconScoreDatabase', iters: iter) -> None:
        for key, value in iters:
            sub_db = db.get_sub_db(ContainerUtil.encode_key(key))
            if isinstance(value, dict):
                ContainerUtil.__put_to_db_internal(sub_db, value.items())
            elif isinstance(value, (list, set, tuple)):
                ContainerUtil.__put_to_db_internal(sub_db, enumerate(value))
            else:
                db_key = ContainerUtil.encode_key(key)
                db_value = ContainerUtil.encode_value(value)
                db.put(db_key, db_value)


class DictDB(object):

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type, depth: int=1) -> None:
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

        return ContainerUtil.decode_object(sub_db.get(ContainerUtil.encode_key(last_key)), self.__value_type)

    def __check_tuple_keys(self, keys: Any) -> Tuple[K, ...]:

        if keys is None:
            keys = tuple()
        elif not isinstance(keys, collections.Iterable):
            keys = tuple([keys])

        for key in keys:
            if not isinstance(key, (int, str, Address)):
                raise ContainerDBException(f"can't cast args {type(key)} : {key}")

        if not len(keys) == self.__depth:
            raise ContainerDBException('depth over')

        return keys


class ArrayDB(Iterator):
    __SIZE = 'size'

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type) -> None:
        self.__db = db.get_sub_db(ContainerUtil.encode_key(var_key))
        self.__size = self.__get_size()
        self.__index = 0
        self.__value_type = value_type

    def put(self, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        self.__db.put(ContainerUtil.encode_key(self.__size), byte_value)
        self.__size += 1
        self.__set_size()

    def pop(self) -> None:
        self.__size -= 1
        self.__set_size()

    def get(self, index: int=0) -> V:
        if index >= self.__size:
            raise ContainerDBException(f'ArrayDB out of range')

        return ContainerUtil.decode_object(self.__db.get(ContainerUtil.encode_key(index)), self.__value_type)

    def __iter__(self):
        self.__index = 0
        return self

    def __next__(self) -> V:
        if self.__index < self.__size:
            index = self.__index
            self.__index += 1
            return self.get(index)
        else:
            raise StopIteration

    def __len__(self):
        return self.__size

    def __get_size(self) -> int:
        size = 0
        db_list_size = ContainerUtil.decode_object(self.__db.get(ContainerUtil.encode_key(ArrayDB.__SIZE)), int)
        if db_list_size:
            size = db_list_size

        return size

    def __set_size(self) -> None:
        sub_db = self.__db
        byte_value = ContainerUtil.encode_value(self.__size)
        sub_db.put(ContainerUtil.encode_key(ArrayDB.__SIZE), byte_value)

    def __setitem__(self, index: int, value: V) -> None:
        if index >= self.__size:
            raise ContainerDBException(f'ArrayDB out of range')

        sub_db = self.__db
        byte_value = ContainerUtil.encode_value(value)
        sub_db.put(ContainerUtil.encode_key(index), byte_value)

    def __getitem__(self, index: int) -> V:
        if isinstance(index, int):
            if index < 0:
                index += len(self)
            if index < 0 or index >= len(self):
                return return_default_value(self.__value_type)
                # raise ContainerDBException(f'ArrayDB out of range, {index}')

            sub_db = self.__db
            return ContainerUtil.decode_object(sub_db.get(ContainerUtil.encode_key(index)), self.__value_type)

    def __contains__(self, item: V):
        for e in self:
            if e == item:
                return True
        return False


class VarDB(object):

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type) -> None:
        self.__db = db
        self.__var_byte_key = ContainerUtil.encode_key(var_key)
        self.__value_type = value_type

    def set(self, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        self.__db.put(self.__var_byte_key, byte_value)

    def get(self) -> Optional[V]:
        return ContainerUtil.decode_object(self.__db.get(self.__var_byte_key), self.__value_type)


def return_default_value(value_type: type) -> Any:
    if value_type == int:
        return 0
    elif value_type == str:
        return ""
    return None
