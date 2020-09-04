# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import TYPE_CHECKING

from .icx_account import Account
from .storage import AccountPartFlag
from ..base.ComponentBase import EngineBase
from ..base.address import Address
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from .coin_part import CoinPart
    from .stake_part import StakePart
    from .delegation_part import DelegationPart


class Engine(EngineBase):
    """Manages the balances of icon accounts

    The basic unit of icx coin is loop. (1 icx == 1e18 loop)
    _context property is inherited from ContextGetter
    """

    def get_balance(self,
                    context: 'IconScoreContext',
                    address: 'Address') -> int:
        """Get the balance of address

        :param context:
        :param address: account address
        :return: the balance of address in loop (1 icx  == 1e18 loop)
        """

        # If the address is not present, its balance is 0.
        # Unit: loop (1 icx == 1e18 loop)
        account: 'Account' = context.storage.icx.get_account(context, address)
        return account.balance

    def charge_fee(self,
                   context: 'IconScoreContext',
                   from_: 'Address',
                   fee: int):
        """Charge a fee for a tx
        It MUST NOT raise any exceptions

        :param context:
        :param from_:
        :param fee:
        :return:
        """
        self._transfer(context, from_, context.storage.icx.fee_treasury, fee)

    def transfer(self,
                 context: 'IconScoreContext',
                 from_: 'Address',
                 to: 'Address',
                 amount: int) -> bool:
        if amount < 0:
            raise InvalidParamsException('Amount is less than zero')

        return self._transfer(context, from_, to, amount)

    def _transfer(self,
                  context: 'IconScoreContext',
                  from_: 'Address',
                  to: 'Address',
                  amount: int) -> bool:
        """Transfer the amount of icx to the account indicated by _to address

        :param context:
        :param from_: icx sender
        :param to: icx receiver
        :param amount: the amount of coin in loop to transfer
        :return True
        """
        if from_ != to and amount > 0:
            # get account info from state db.
            from_account = context.storage.icx.get_account(context, from_)
            to_account = context.storage.icx.get_account(context, to)

            from_account.withdraw(amount)
            to_account.deposit(amount)

            # write newly updated state into state db.
            context.storage.icx.put_account(context, from_account)
            context.storage.icx.put_account(context, to_account)

        return True

    @classmethod
    def get_account_raw_data(
            cls,
            context: 'IconScoreContext',
            address: 'Address',
            account_filter: 'AccountPartFlag'
    ) -> dict:
        """Get the balance of address

        :param context:
        :param address: account address
        :param account_filter:
        :return: raw data of account in stateDB
        """

        ret = {}
        if AccountPartFlag.COIN in account_filter:
            part: 'CoinPart' = context.storage.icx.get_part(
                context=context,
                flag=AccountPartFlag.COIN,
                address=address
            )
            ret["coin"] = {
                "type": part.type.value,
                "typeStr": str(part.type),
                "flag": part.flags.value,
                "flagStr": str(part.flags),
                "balance": part.balance
            }
        if AccountPartFlag.STAKE in account_filter:
            part: 'StakePart' = context.storage.icx.get_part(
                context=context,
                flag=AccountPartFlag.STAKE,
                address=address
            )
            ret["stake"] = {
                "stake": part.stake,
                "unstake": part.unstake,
                "unstakeBlockHeight": part.unstake_block_height,
                "unstakesInfo": part.unstakes_info,
            }
        if AccountPartFlag.DELEGATION in account_filter:
            part: 'DelegationPart' = context.storage.icx.get_part(
                context=context,
                flag=AccountPartFlag.DELEGATION,
                address=address
            )
            ret["delegation"] = {
                "totalDelegated": part.delegated_amount,
                "delegations": [
                    {"address": delegation[0], "value": delegation[1]}
                    for delegation in part.delegations
                ],
            }
        return ret
