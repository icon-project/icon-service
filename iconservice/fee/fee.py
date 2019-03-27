from struct import Struct

from ..icon_constant import DEFAULT_BYTE_SIZE


class Fee(object):
    """
    SCORE Fee Information

    [Fee Structure for level db]
    - big endian, 1 + DEFAULT_BYTE_SIZE * 4 bytes

    [In Detail]
    | ratio(1)
    | head_id(DEFAULT_BYTE_SIZE)
    | tail_id(DEFAULT_BYTE_SIZE)
    | available_head_id_of_virtual_step (DEFAULT_BYTE_SIZE)
    | available_head_id_of_deposit (DEFAULT_BYTE_SIZE)
    """

    _struct = Struct(f'>B{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s')

    def __init__(self, ratio: int = 0, head_id: bytes = None, tail_id: bytes = None,
                 available_head_id_of_virtual_step: bytes = None, available_head_id_of_deposit: bytes = None):
        self.ratio = ratio
        self.head_id = head_id
        self.tail_id = tail_id
        self.available_head_id_of_virtual_step = available_head_id_of_virtual_step
        self.available_head_id_of_deposit = available_head_id_of_deposit

    @staticmethod
    def from_bytes(buf: bytes):
        """Converts Fee in bytes into Fee Object.

        :param buf: Fee in bytes
        :return: Fee Object
        """
        ratio, head_id, tail_id, available_head_id_of_virtual_step, available_head_id_of_deposit \
            = Fee._struct.unpack(buf)

        fee = Fee()
        fee.ratio = ratio
        fee.head_id = head_id
        fee.tail_id = tail_id
        fee.available_head_id_of_virtual_step = available_head_id_of_virtual_step
        fee.available_head_id_of_deposit = available_head_id_of_deposit

        return fee

    def to_bytes(self) -> bytes:
        """Converts Fee object into bytes.

        :return: Fee in bytes
        """
        return self._struct.pack(self.ratio, self.head_id, self.tail_id,
                                 self.available_head_id_of_virtual_step, self.available_head_id_of_deposit)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (Fee)
        """
        return isinstance(other, Fee) \
               and self.ratio == other.ratio \
               and self.head_id == other.head_id \
               and self.tail_id == other.tail_id \
               and self.available_head_id_of_virtual_step == other.available_head_id_of_virtual_step \
               and self.available_head_id_of_deposit == other.available_head_id_of_deposit

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (Fee)
        """
        return not self.__eq__(other)
