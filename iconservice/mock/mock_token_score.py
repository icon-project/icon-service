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


from ..base.address import Address, AddressPrefix
from ..iconscore.icon_score_context import IconScoreContext


class MockTokenScore(object):
    """IconScore for token test 
    """

    def __init__(self):
        pass

    def transfer(self,
                 context: IconScoreContext,
                 to: Address,
                 value: int) -> bool:

        _from = context.tx.origin
        from_amount = int.from_bytes(context.db.get(_from.body), 'big')
        to_amount = int.from_bytes(context.db.get(to.body), 'big')

        from_amount -= value
        to_amount += value

        context.db.put(_from.body, from_amount.to_bytes(32, 'big'))
        context.db.put(to.body, to_amount.to_bytes(32, 'big'))

        return True

    def balance_of(self,
                   context: IconScoreContext,
                   address: Address) -> int:
        amount = int.from_bytes(context.db.get(address.body), 'big')
        return amount
