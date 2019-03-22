from struct import Struct
from ..icon_constant import DEFAULT_BYTE_SIZE


class Deposit(object):
    """Deposit Information"""

    # Deposit Structure for level db (big endian, 128 bytes)
    # score_address(4) | sender(4) | amount(32) | created(8) | expires(8)
    # | virtual_step_issued(32) | virtual_step_used(32) | prev_id(4) | next_id(4)
    _struct = Struct(f'>BBBx{DEFAULT_BYTE_SIZE}s')

    def __init__(self, deposit_id: bytes, score_address: 'Address', sender: 'Address', amount: int = 0,
                 created: int = 0, expires: int = 0, virtual_step_issued: int = 0, virtual_step_used: int = 0,
                 prev_id: bytes = None, next_id: bytes = None):
        # deposit id, should be tx hash of deposit transaction
        self.id = deposit_id
        # target SCORE address
        self.score_address = score_address
        # sender address
        self.sender = sender
        # amount of ICXs in loop
        self.amount = amount
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
        """Deposit object from bytes data

        :param buf: deposit info in bytes
        :return: deposit object
        """
        return Deposit

    @staticmethod
    def to_bytes(self) -> bytes:
        """Converts Deposit object into bytes

        :return: deposit info in bytes
        """
        return Deposit._struct.pack()

