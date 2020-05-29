from collections import namedtuple
from typing import List, Tuple, Union

from tools.precommit_converter.converter.converter import Converter, NotMatchException
from tools.precommit_converter.utils import BytesKeyValue

ConvertedKeyValue = namedtuple("ConvertedKeyValue", ['tx_index', 'position', 'key', 'value'])


class ConvertEngine:
    def __init__(self):
        self._converters: List[Converter] = []
        for converter in Converter.__subclasses__():
            self._converters.append(converter())

    def convert(self, key_values: List['BytesKeyValue']) -> List[ConvertedKeyValue]:
        ret: List[ConvertedKeyValue] = []
        for i, bkv in enumerate(key_values):
            converted_key, converted_value = self._convert(bkv.key, bkv.value)
            ret.append(ConvertedKeyValue(bkv.tx_index, i, converted_key, converted_value))
        return ret

    def _convert(self, key: bytes, value: bytes) -> Tuple[Union[bytes, str], Union[bytes, str]]:
        for converter in self._converters:
            try:
                converted_key, converted_value = converter.convert(key, value)
                break
            except NotMatchException:
                continue
        else:
            converted_key, converted_value = f"Hex: {key.hex()} Bytes: {key}", f"Hex: {value.hex()} Bytes: {value}"
        return converted_key, converted_value
