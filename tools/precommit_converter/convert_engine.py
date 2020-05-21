from typing import Any

from tools.precommit_converter.converter import Converter


class NotMatchException(Exception):
    pass


class StaticConverterController:
    def __init__(self):
        self._mapper = {}

    def register(self, key: bytes, value_converter: callable):
        self._mapper[key] = value_converter

    def convert(self, key: bytes, value: bytes):
        try:
            return self._mapper[key](key, value)
        except KeyError:
            raise NotMatchException()


class FlexibleConverterController:
    def __init__(self):
        self._detector_converter_pairs = []

    def register(self, key_detector: callable, value_converter: callable):
        self._detector_converter_pairs.append((key_detector, value_converter))

    def convert(self, key: bytes, value: bytes) -> Any:
        for detector, converter in self._detector_converter_pairs:
            if detector(key) is True:
                return converter(key, value)
        else:
            raise NotMatchException()


class ConvertEngine:
    def __init__(self):
        self._static_key_converter = StaticConverterController()
        self._flexible_key_converter = FlexibleConverterController()
        for method_ in Converter.__subclasses__():
            for key, converter in method_.get_static_key_convert_methods():
                self._static_key_converter.register(key, converter)

            for key_detector, converter in method_.get_flexible_key_convert_methods():
                self._flexible_key_converter.register(key_detector, converter)

    def convert(self, key: bytes, value: bytes):
        # Todo: check the minimum requirements
        try:
            converted_key, converted_value = self._static_key_converter.convert(key, value)
        except NotMatchException:
            try:
                converted_key, converted_value = self._flexible_key_converter.convert(key, value)
            except NotMatchException:
                # print("Converter not found")
                converted_key, converted_value = key, value
        return converted_key, converted_value
