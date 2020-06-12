from typing import Optional, List


class KeyValue:
    def __init__(self, tx_indexes: Optional[List[int]], bytes_key: bytes, bytes_value: Optional[bytes]):
        self.tx_indexes: Optional[List[int]] = tx_indexes
        self.bytes_key: bytes = bytes_key
        # Some data could be None (e.g. delete SCORE data)
        self.bytes_value: Optional[bytes] = bytes_value

        self.converted_key: Optional[str] = None
        self.converted_value: Optional[str] = None

    @property
    def hex_key(self):
        return "0x" + self.bytes_key.hex()

    @property
    def hex_value(self):
        return "0x" + self.bytes_value.hex()

    def set_converted_key_value(self, converted_key: str, converted_value: str):
        self.converted_key, self.converted_value = converted_key, converted_value
