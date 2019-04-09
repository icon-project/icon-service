from ..utils.msgpack_for_db import MsgPackForDB


class Fee(object):
    """
    SCORE Fee Information Class
    implementing functions to serialize and deserialize.
    """

    def __init__(self, min_remaining_amount: int = 0, head_id: bytes = None, tail_id: bytes = None,
                 available_head_id_of_virtual_step: bytes = None, available_head_id_of_deposit: bytes = None,
                 expires_of_virtual_step: int = -1, expires_of_deposit: int = -1):
        # min remaining amount of deposit; it is boundary of processing the last transaction.
        self.min_remaining_amount = min_remaining_amount
        self.head_id = head_id
        self.tail_id = tail_id
        self.available_head_id_of_virtual_step = available_head_id_of_virtual_step
        self.available_head_id_of_deposit = available_head_id_of_deposit
        self.expires_of_virtual_step = expires_of_virtual_step
        self.expires_of_deposit = expires_of_deposit

    @staticmethod
    def from_bytes(buf: bytes):
        """Converts Fee in bytes into Fee Object.

        :param buf: Fee in bytes
        :return: Fee Object
        """
        data: list = MsgPackForDB.loads(buf)

        fee = Fee()
        fee.min_remaining_amount = data[0]
        fee.head_id = data[1]
        fee.tail_id = data[2]
        fee.available_head_id_of_virtual_step = data[3]
        fee.available_head_id_of_deposit = data[4]
        fee.expires_of_virtual_step = data[5]
        fee.expires_of_deposit = data[6]

        return fee

    def to_bytes(self) -> bytes:
        """Converts Fee object into bytes.

        :return: Fee in bytes
        """
        data: list = [self.min_remaining_amount, self.head_id, self.tail_id,
                      self.available_head_id_of_virtual_step, self.available_head_id_of_deposit,
                      self.expires_of_virtual_step, self.expires_of_deposit]
        return MsgPackForDB.dumps(data)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (Fee)
        """
        return isinstance(other, Fee) \
               and self.min_remaining_amount == other.min_remaining_amount \
               and self.head_id == other.head_id \
               and self.tail_id == other.tail_id \
               and self.available_head_id_of_virtual_step == other.available_head_id_of_virtual_step \
               and self.available_head_id_of_deposit == other.available_head_id_of_deposit \
               and self.expires_of_virtual_step == other.expires_of_virtual_step \
               and self.expires_of_deposit == other.expires_of_deposit

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (Fee)
        """
        return not self.__eq__(other)
