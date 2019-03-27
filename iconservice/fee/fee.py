from ..base.msgpack_util import MsgPackConverter, TypeTag


class Fee(object):
    """
    SCORE Fee Information
    """
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
        data: list = MsgPackConverter.loads(buf)

        fee = Fee()
        fee.ratio = MsgPackConverter.decode(TypeTag.INT, data[0])
        fee.head_id = data[1]
        fee.tail_id = data[2]
        fee.available_head_id_of_virtual_step = data[3]
        fee.available_head_id_of_deposit = data[4]

        return fee

    def to_bytes(self) -> bytes:
        """Converts Fee object into bytes.

        :return: Fee in bytes
        """
        data: list = [MsgPackConverter.encode(self.ratio), self.head_id, self.tail_id,
                      self.available_head_id_of_virtual_step, self.available_head_id_of_deposit]
        return MsgPackConverter.dumps(data)

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
