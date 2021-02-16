# -*- coding: utf-8 -*-

from typing import Optional

from ..base.address import Address
from ..base.exception import InvalidBalanceException
from ..utils import bytes_to_hex


class BalanceVerifier(object):
    """Check for balance integrity
    """

    def __init__(self):
        self._tx_hash: Optional[bytes] = None
        self._issue = 0
        self._balance = 0

    def open(self, tx_hash: bytes):
        self._tx_hash = tx_hash
        self.reset()

    def issue(self, value: int):
        assert value >= 0
        self._issue += value

    def burn(self, value: int):
        assert value >= 0
        self._issue -= value

    def deposit(self, _address: Address, value: int):
        assert value >= 0
        self._balance += value

    def withdraw(self, _address: Address, value: int):
        assert value >= 0
        self._balance -= value

    def reset(self):
        """Reset the values of issue and balance to 0

        This is called when invoking a tx gets started or a tx is failed
        """
        self._issue = 0
        self._balance = 0

    def verify(self):
        if self._balance != self._issue:
            raise InvalidBalanceException(
                f"Invalid asset integrity: "
                f"tx_hash={bytes_to_hex(self._tx_hash)} "
                f"issue={self._issue} "
                f"balance={self._balance}"
            )

    def close(self):
        pass
