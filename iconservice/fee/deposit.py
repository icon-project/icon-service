import typing
from struct import Struct

from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER
from ..base.address import Address, ICON_EOA_ADDRESS_BYTES_SIZE, ICON_CONTRACT_ADDRESS_BYTES_SIZE

if typing.TYPE_CHECKING:
    from ..base.address import Address


class Deposit(object):
    """
    Deposit Information having both pack and unpack function

    [Deposit Structure for level db]
    - big endian, ICON_CONTRACT_ADDRESS_BYTES_SIZE + ICON_EOA_ADDRESS_BYTES_SIZE + DEFAULT_BYTE_SIZE * 8 bytes

    [In Detail]
    | score_address(ICON_CONTRACT_ADDRESS_BYTES_SIZE)
    | sender(ICON_EOA_ADDRESS_BYTES_SIZE)
    | deposit_amount(DEFAULT_BYTE_SIZE)
    | deposit_used(DEFAULT_BYTE_SIZE)
    | created(DEFAULT_BYTE_SIZE)
    | expires(DEFAULT_BYTE_SIZE)
    | virtual_step_issued(DEFAULT_BYTE_SIZE)
    | virtual_step_used(DEFAULT_BYTE_SIZE)
    | prev_id(DEFAULT_BYTE_SIZE)
    | next_id(DEFAULT_BYTE_SIZE)
    """
    _struct = Struct(f'>{ICON_CONTRACT_ADDRESS_BYTES_SIZE}s'
                     f'{ICON_EOA_ADDRESS_BYTES_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s'
                     f'{DEFAULT_BYTE_SIZE}s')

    def __init__(self, deposit_id: bytes = None, score_address: 'Address' = None, sender: 'Address' = None,
                 deposit_amount: int = 0, deposit_used: int = 0, created: int = 0, expires: int = 0,
                 virtual_step_issued: int = 0, virtual_step_used: int = 0, prev_id: bytes = None, next_id: bytes = None):
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
        """Creates Deposit object from bytes data

        :param buf: deposit info in bytes
        :return: deposit object
        """
        score_address, sender, deposit_amount, deposit_used, created, expires, virtual_step_issued, virtual_step_used, \
        prev_id, next_id = Deposit._struct.unpack(buf)

        deposit = Deposit()
        deposit.score_address = Address.from_bytes(score_address)
        deposit.sender = Address.from_bytes(sender)
        deposit.deposit_amount = int.from_bytes(deposit_amount, DATA_BYTE_ORDER)
        deposit.deposit_used = int.from_bytes(deposit_used, DATA_BYTE_ORDER)
        deposit.created = int.from_bytes(created, DATA_BYTE_ORDER)
        deposit.expires = int.from_bytes(expires, DATA_BYTE_ORDER)
        deposit.virtual_step_issued = int.from_bytes(virtual_step_issued, DATA_BYTE_ORDER)
        deposit.virtual_step_used = int.from_bytes(virtual_step_used, DATA_BYTE_ORDER)
        deposit.prev_id = prev_id
        deposit.next_id = next_id

        return deposit

    def to_bytes(self) -> bytes:
        """Converts Deposit object into bytes

        :return: deposit info in bytes
        """
        return self._struct.pack(self.score_address.to_bytes(), self.sender.to_bytes(),
                                 self.deposit_amount.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER),
                                 self.deposit_used.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER),
                                 self.created.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER),
                                 self.expires.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER),
                                 self.virtual_step_issued.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER),
                                 self.virtual_step_used.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER), self.prev_id, self.next_id)

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
