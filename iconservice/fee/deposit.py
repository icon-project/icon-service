from typing import Optional

from ..base.address import Address
from ..base.msgpack_util import MsgPackConverter, TypeTag


class Deposit(object):
    """
    Deposit Information having both pack and unpack function
    """
    def __init__(self, deposit_id: bytes = None, score_address: 'Address' = None, sender: 'Address' = None,
                 deposit_amount: int = 0, deposit_used: int = 0, created: int = 0, expires: int = 0,
                 virtual_step_issued: int = 0, virtual_step_used: int = 0, prev_id: bytes = None,
                 next_id: bytes = None):
        # deposit id, should be tx hash of deposit transaction
        self.id = deposit_id
        # target SCORE address
        self.score_address = score_address
        # sender address
        self.sender = sender
        # deposit amount of ICXs in loop
        self.deposit_amount = deposit_amount
        # used amount of deposited ICXs in loop
        self.deposit_used = deposit_used
        # created time in block
        self.created = created
        # expires time in block
        self.expires = expires
        # issued amount of virtual STEPs
        self.virtual_step_issued = virtual_step_issued
        # used amount of virtual STEPs
        self.virtual_step_used = virtual_step_used
        # previous id of this deposit
        self.prev_id = prev_id
        # next id of this deposit
        self.next_id = next_id

    @staticmethod
    def from_bytes(buf: bytes):
        """Creates Deposit object from bytes data.

        :param buf: deposit info in bytes
        :return: deposit object
        """
        data: list = MsgPackConverter.loads(buf)

        deposit = Deposit()
        deposit.score_address = Address.from_bytes(data[0])
        deposit.sender = Address.from_bytes(data[1])
        deposit.deposit_amount = MsgPackConverter.decode(TypeTag.INT, data[2])
        deposit.deposit_used = MsgPackConverter.decode(TypeTag.INT, data[3])
        deposit.created = MsgPackConverter.decode(TypeTag.INT, data[4])
        deposit.expires = MsgPackConverter.decode(TypeTag.INT, data[5])
        deposit.virtual_step_issued = MsgPackConverter.decode(TypeTag.INT, data[6])
        deposit.virtual_step_used = MsgPackConverter.decode(TypeTag.INT, data[7])
        deposit.prev_id = data[8]
        deposit.next_id = data[9]

        return deposit

    def to_bytes(self) -> bytes:
        """Converts Deposit object into bytes.

        :return: deposit info in bytes
        """
        data: list = [self.score_address.to_bytes(),
                      self.sender.to_bytes(),
                      MsgPackConverter.encode(self.deposit_amount),
                      MsgPackConverter.encode(self.deposit_used),
                      MsgPackConverter.encode(self.created),
                      MsgPackConverter.encode(self.expires),
                      MsgPackConverter.encode(self.virtual_step_issued),
                      MsgPackConverter.encode(self.virtual_step_used),
                      self.prev_id,
                      self.next_id]

        return MsgPackConverter.dumps(data)

    def to_dict(self, casing: Optional = None) -> dict:
        """Returns properties as dict.

        :param casing: a kind of functions to convert one casing notation to another
        :return: deposit info in dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            # Excludes properties which have `None` value
            if value is None:
                continue

            new_key = casing(key) if casing else key
            new_dict[new_key] = value

        return new_dict

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (Deposit)
        """
        return isinstance(other, Deposit) \
               and self.score_address == other.score_address \
               and self.sender == other.sender \
               and self.deposit_amount == other.deposit_amount \
               and self.deposit_used == other.deposit_used \
               and self.created == other.created \
               and self.expires == other.expires \
               and self.virtual_step_issued == other.virtual_step_issued \
               and self.virtual_step_used == other.virtual_step_used \
               and self.prev_id == other.prev_id \
               and self.next_id == other.next_id

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (Deposit)
        """
        return not self.__eq__(other)
