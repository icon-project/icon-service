from collections import namedtuple
from typing import List, Tuple, Union

from tools.precommit_converter.converter import Converter, NotMatchException

ConvertedKeyValues = namedtuple("ConvertedKeyValues", ['position', 'key', 'value'])


class ConvertEngine:
    def __init__(self):
        self._converters: List[Converter] = []
        for converter in Converter.__subclasses__():
            self._converters.append(converter())

    def convert(self, key_values: list) -> List[ConvertedKeyValues]:
        ret: List[ConvertedKeyValues] = []
        for i, (key, value) in enumerate(key_values):
            converted_key, converted_value = self._convert(key, value)
            ret.append(ConvertedKeyValues(i, converted_key, converted_value))
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
