from iconservice import *
from .basic_token import BasicToken


class StandardToken(BasicToken):
    """
    Implementation of the basic standard token.
    """
    __DBKEY_ALLOWED = 'allowed'

    @eventlog(indexed=2)
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
    def increase_approval(self, spender: Address, value: int) -> bool:
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
    def decrease_approval(self, spender: Address, value: int) -> bool:
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
    def transfer_from(self, from_addr: Address, to_addr: Address, value: int) -> bool:
        """
        Transfer tokens from one address to another

        :param from_addr: address The address which you want to send tokens from
        :param to_addr: address The address whitch you want to transfer to
        :param value: int the amount of tokens to be transferred
        :return:
        """
        if self.balanceOf(from_addr) < value:
            self.revert(f"User balance is not enough.")

        if self._allowed[from_addr][self.msg.sender] < value:
            self.revert("User doesn't have allowed value.")

        self._balances[from_addr] = self._balances[from_addr] - value
        self._balances[to_addr] = self._balances[to_addr] + value
        self._allowed[from_addr][self.msg.sender] = self._allowed[from_addr][self.msg.sender] - value

        self.Transfer(from_addr, to_addr, value, 'None')
        Logger.debug(f"transfer_from [after] from : {self.balanceOf(from_addr)}, to {self.balanceOf(to_addr)}, ",
                     f"allowed : {self.allowance(from_addr, self.msg.sender)}")

        return True
