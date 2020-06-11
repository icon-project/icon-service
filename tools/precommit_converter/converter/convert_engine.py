from typing import List, Tuple, Union

from tools.precommit_converter.converter.converter import Converter, NotMatchException
from tools.precommit_converter.data.key_value import KeyValue


class ConvertEngine:
    def __init__(self):
        self._converters: List[Converter] = []
        for converter in Converter.__subclasses__():
            self._converters.append(converter())

    def set_converted_key_values(self, key_values: List['KeyValue']):
        for kv in key_values:
            kv.set_converted_key_value(*self._convert(kv.bytes_key, kv.bytes_value))

    def _convert(self, key: bytes, value: bytes) -> Tuple[Union[bytes, str], Union[bytes, str]]:
        for converter in self._converters:
            try:
                converted_key, converted_value = converter.convert(key, value)
                break
            except NotMatchException:
                continue
        else:
            converted_key, converted_value = f"Hex: 0x{key.hex()}", f"Hex: 0x{value.hex()}"
        return converted_key, converted_value
