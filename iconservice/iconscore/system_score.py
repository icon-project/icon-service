# -*- coding: utf-8 -*-

# Copyright 2020 ICON Foundation
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
"""SystemScore module
"""

from inspect import currentframe
from typing import TYPE_CHECKING, List

from iconcommons.logger import Logger
from typing_extensions import TypedDict

from .icon_score_base import IconScoreBase, interface, external, payable, eventlog, revert
from .icon_score_base2 import InterfaceScore
from ..base.address import Address
from ..base.exception import *
from ..icon_constant import ISCORE_EXCHANGE_RATE, Revision
from ..utils import to_camel_case

if TYPE_CHECKING:
    from ..database.db import IconScoreDatabase
    from ..iconscore.icon_score_context import IconScoreContext
    from ..iiss.storage import RewardRate


class Delegation(TypedDict):
    address: Address
    value: int


class SystemScore(IconScoreBase):
    @eventlog
    def IScoreClaimed(self, iscore: int, icx: int):
        pass

    @eventlog(indexed=1)
    def IScoreClaimedV2(self, address: Address, iscore: int, icx: int):
        pass

    @eventlog
    def PRepRegistered(self, address: Address):
        pass

    @eventlog
    def PRepUnregistered(self, address: Address):
        pass

    @eventlog
    def PRepSet(self, address: Address):
        pass

    @eventlog(indexed=1)
    def ICXBurnedV2(self, address: Address, amount: int, totalSupply: int):
        pass

    def __init__(self, db: 'IconScoreDatabase') -> None:
        super().__init__(db)

    def on_install(self, **kwargs) -> None:
        super().on_install()

    def on_update(self, **kwargs) -> None:
        super().on_update()

    @external
    def setStake(self, value: int = 0) -> None:
        self._context.engine.iiss.invoke(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getStake(self, address: Address) -> dict:
        return self._context.engine.iiss.query(*self._get_params(locals_params=locals()))

    @external
    def setDelegation(self, delegations: List[Delegation] = None) -> None:
        self._context.engine.iiss.invoke(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getDelegation(self, address: Address) -> dict:
        return self._context.engine.iiss.query(*self._get_params(locals_params=locals()))

    @external
    def claimIScore(self) -> None:
        self._context.engine.iiss.invoke(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def queryIScore(self, address: Address) -> dict:
        return self._context.engine.iiss.query(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def estimateUnstakeLockPeriod(self) -> dict:
        return self._context.engine.iiss.query(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getIISSInfo(self) -> dict:
        return _handle_get_iiss_info(self._context)

    @payable
    @external
    def registerPRep(self, name: str, country: str, city: str, email: str, website: str,
                     details: str, p2pEndpoint: str, nodeAddress: "Address" = None):
        self._context.engine.prep.invoke(*self._get_params(locals_params=locals()))

    @external
    def unregisterPRep(self):
        self._context.engine.prep.invoke(*self._get_params(locals_params=locals()))

    @external
    def setPRep(self, name: str = None, country: str = None, city: str = None, email: str = None,
                website: str = None, details: str = None, p2pEndpoint: str = None, nodeAddress: "Address" = None):
        self._context.engine.prep.invoke(*self._get_params(locals_params=locals()))

    @external
    def setGovernanceVariables(self, irep: int):
        self._context.engine.prep.invoke(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getPRep(self, address: Address) -> dict:
        return self._context.engine.prep.query(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getPReps(self, startRanking: int = None, endRanking: int = None) -> list:
        return self._context.engine.prep.query(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getMainPReps(self) -> dict:
        return self._context.engine.prep.query(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getSubPReps(self) -> dict:
        return self._context.engine.prep.query(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getPRepTerm(self) -> dict:
        return self._context.engine.prep.query(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getInactivePReps(self) -> dict:
        return self._context.engine.prep.query(*self._get_params(locals_params=locals()))

    @external(readonly=True)
    def getScoreDepositInfo(self, address: Address) -> dict:
        # TODO check with dbtools
        # if str(from_) not in _AUTHORIZED_ACCOUNTS:
        #     raise AccessDeniedException("No permission")

        context = self._context
        deposit_info = context.engine.fee.get_deposit_info(
            context, address, context.block.height
        )
        return None if deposit_info is None else deposit_info.to_dict(to_camel_case)

    @payable
    @external
    def burn(self):
        context = self._context
        if context.revision < Revision.BURN_V2_ENABLED.value:
            revert("burn is not enabled")

        context.engine.issue.burn(context, self.msg.sender, self.msg.value)

    def _get_params(self, locals_params: dict) -> tuple:
        method = currentframe().f_back.f_code.co_name
        params: dict = self._del_self_in_params(locals_params)
        return self._context, method, params

    def _del_self_in_params(self, kw_args: dict) -> dict:
        params = dict(kw_args)
        del params["self"]

        return params


class InterfaceSystemScore(InterfaceScore):
    @interface
    def setStake(self, value: int) -> None: pass

    @interface
    def getStake(self, address: Address) -> dict: pass

    @interface
    def estimateUnstakeLockPeriod(self) -> dict: pass

    @interface
    def setDelegation(self, delegations: List[Delegation] = None): pass

    @interface
    def getDelegation(self, address: Address) -> dict: pass

    @interface
    def claimIScore(self): pass

    @interface
    def queryIScore(self, address: Address) -> dict: pass

    @interface
    def getIISSInfo(self) -> dict: pass

    @interface
    def getPRep(self, address: Address) -> dict: pass

    @interface
    def getPReps(self, startRanking: int, endRanking: int) -> list: pass

    @interface
    def getMainPReps(self) -> dict: pass

    @interface
    def getSubPReps(self) -> dict: pass

    @interface
    def getPRepTerm(self) -> dict: pass

    @interface
    def getInactivePReps(self) -> dict: pass

    @interface
    def getScoreDepositInfo(self, address: Address) -> dict: pass

    @interface
    def burn(self): pass


def _create_rc_result(context: "IconScoreContext", start_block: int, end_block: int) -> dict:
    rc_result = dict()
    if start_block < 0 or end_block < 0:
        return rc_result

    iscore, request_block_height, rc_state_hash = \
        context.storage.rc.get_calc_response_from_rc()
    if iscore == -1:
        return rc_result

    if request_block_height != end_block:
        Logger.warning(
            tag="ISE",
            msg=f"Response block height is not matched to the request: "
            f"response block height:{request_block_height} "
            f"request block height:{end_block}",
        )
        return rc_result

    rc_result["iscore"] = iscore
    rc_result["estimatedICX"] = iscore // ISCORE_EXCHANGE_RATE
    rc_result["startBlockHeight"] = start_block
    rc_result["endBlockHeight"] = end_block
    rc_result["stateHash"] = rc_state_hash

    return rc_result


def _handle_get_iiss_info(context: "IconScoreContext") -> dict:
    term = context.engine.prep.term
    reward_rate: "RewardRate" = context.storage.iiss.get_reward_rate(context)

    response = {
        "blockHeight": context.block.height,
        "variable": {
            "irep": term.irep if term else 0,
            "rrep": reward_rate.reward_prep
        },
    }

    calc_start_block, calc_end_block = context.storage.meta.get_last_calc_info(context)

    next_calculation: int = calc_end_block
    if calc_start_block < 0 or context.block.height != next_calculation:
        next_calculation: Optional[
            int
        ] = context.storage.iiss.get_end_block_height_of_calc(context)
        if next_calculation is None:
            next_calculation = -1
    response["nextCalculation"] = next_calculation + 1

    term_start_block, term_end_block = context.storage.meta.get_last_term_info(context)

    if term_end_block < 0 or context.block.height != term_end_block:
        term_end_block: int = term.end_block_height if term else -1
    response["nextPRepTerm"] = term_end_block + 1

    response["rcResult"] = _create_rc_result(context, calc_start_block, calc_end_block)

    return response
