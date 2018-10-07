from iconservice import *
from .basic_token import BasicToken

import os as iconservice

class StandardToken(BasicToken):
    """
    Implementation of the basic standard token.
    """
    __DBKEY_ALLOWED = 'allowed'

    @eventlog(indexed=3)
    def Approval(self, owner: Address, spender: Address, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._allowed = DictDB(self.__DBKEY_ALLOWED, db, value_type=int, depth=2)

    @external
    def approve(self, spender: Address, value: int) -> bool:
        """
        Approve the passed address to spend the specified amount of tokens on behalf of msg.sender

        :param spender:
        :param value:
        :return:
        """
        self._allowed[self.msg.sender][spender] = value

        self.Approval(self.msg.sender, spender, value)
        Logger.debug(f"approved {self.msg.sender},{spender} = {value}")
        return True

    @external(readonly=True)
    def allowance(self, owner: Address, spender: Address) -> int:
        return self._allowed[owner][spender]

    @external
    def increaseApproval(self, spender: Address, value: int) -> bool:
        """
        Increase the amount of tokens that an owner allowed to a spender

        :param spender:
        :param value:
        :return:
        """
        self._allowed[self.msg.sender][spender] = self._allowed[self.msg.sender][spender] + value

        self.Approval(self.msg.sender, spender, self._allowed[self.msg.sender][spender])
        Logger.debug(f"increase approval {self.msg.sender},{spender} += {value} "
                     f"=> {self._allowed[self.msg.sender][spender]}")
        return True

    @external
    def decreaseApproval(self, spender: Address, value: int) -> bool:
        """
        Decrease the amount of tokens that an owner allowed to a spender.

        :param spender:
        :param value:
        :return:
        """
        old_value = self._allowed[self.msg.sender][spender]
        self._allowed[self.msg.sender][spender] = max(0, old_value - value)

        self.Approval(self.msg.sender, spender, self._allowed[self.msg.sender][spender])
        Logger.debug(f"decrease approval {self.msg.sender},{spender} -= {value} "
                     f"=> {self._allowed[self.msg.sender][spender]}")
        return True

    @external
    def transferFrom(self, fromAddr: Address, toAddr: Address, value: int) -> bool:
        """
        Transfer tokens from one address to another

        :param fromAddr: address The address which you want to send tokens from
        :param toAddr: address The address whitch you want to transfer to
        :param value: int the amount of tokens to be transferred
        :return:
        """
        if self.balanceOf(fromAddr) < value:
            self.revert(f"User balance is not enough.")

        if self._allowed[fromAddr][self.msg.sender] < value:
            self.revert("User doesn't have allowed value.")

        self._balances[fromAddr] = self._balances[fromAddr] - value
        self._balances[toAddr] = self._balances[toAddr] + value
        self._allowed[fromAddr][self.msg.sender] = self._allowed[fromAddr][self.msg.sender] - value

        self.Transfer(fromAddr, toAddr, value, 'None')
        Logger.debug(f"transfer_from [after] from : {self.balanceOf(fromAddr)}, to {self.balanceOf(toAddr)}, ",
                     f"allowed : {self.allowance(fromAddr, self.msg.sender)}")

        return True
