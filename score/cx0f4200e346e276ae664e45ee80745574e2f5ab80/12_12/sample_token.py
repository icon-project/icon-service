# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

from iconservice.base.exception import IconScoreBaseException
from iconservice.base.address import Address
from iconservice.iconscore.icon_score_base import IconScoreBase, external, score
from iconservice.database.db import InternalScoreDatabase
from iconservice.iconscore.icon_container_db import DictDB, VarDB


@score
class SampleToken(IconScoreBase):

    _BALANCES = 'balances'
    _TOTAL_SUPPLY = 'total_supply'

    def __init__(self, db: InternalScoreDatabase, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._total_supply = VarDB(self._TOTAL_SUPPLY, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)

    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)

        init_supply = 1000
        decimal = 18
        total_supply = init_supply * 10 ** decimal

        self._total_supply.set(total_supply)
        self._balances[self.address] = total_supply

    @external(readonly=True)
    def total_supply(self) -> int:
        return self._total_supply.get()

    @external(readonly=True)
    def balance_of(self, addr_from: Address) -> int:
        var = self._balances[addr_from]
        if var is None:
            var = 0
        return var

    def _transfer(self, _addr_from: Address, _addr_to: Address, _value: int) -> bool:

        if self.balance_of(_addr_from) < _value:
            raise IconScoreBaseException(f"{_addr_from}'s balance < {_value}")

        self._balances[_addr_from] = self.balance_of(_addr_from) - _value
        self._balances[_addr_to] = _value
        return True

    @external()
    def transfer(self, addr_to: Address, value: int) -> bool:
        return self._transfer(self.msg.sender, addr_to, value)

    def fallback(self) -> None:
        pass
