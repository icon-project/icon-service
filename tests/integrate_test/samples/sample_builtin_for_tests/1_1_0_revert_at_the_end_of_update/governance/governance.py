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

from iconservice import *
from iconservice.iconscore.system import *


TAG = 'Governance'
DEBUG = False

CURRENT = 'current'
NEXT = 'next'
STATUS = 'status'
DEPLOY_TX_HASH = 'deployTxHash'
AUDIT_TX_HASH = 'auditTxHash'
DEPOSIT_INFO = 'depositInfo'
VALID_STATUS_KEYS = [STATUS, DEPLOY_TX_HASH, AUDIT_TX_HASH]

STATUS_PENDING = 'pending'
STATUS_ACTIVE = 'active'
STATUS_INACTIVE = 'inactive'
STATUS_REJECTED = 'rejected'

STEP_TYPE_DEFAULT = 'default'
STEP_TYPE_CONTRACT_CALL = 'contractCall'
STEP_TYPE_CONTRACT_CREATE = 'contractCreate'
STEP_TYPE_CONTRACT_UPDATE = 'contractUpdate'
STEP_TYPE_CONTRACT_DESTRUCT = 'contractDestruct'
STEP_TYPE_CONTRACT_SET = 'contractSet'
STEP_TYPE_GET = 'get'
STEP_TYPE_SET = 'set'
STEP_TYPE_REPLACE = 'replace'
STEP_TYPE_DELETE = 'delete'
STEP_TYPE_INPUT = 'input'
STEP_TYPE_EVENT_LOG = 'eventLog'
STEP_TYPE_API_CALL = 'apiCall'
INITIAL_STEP_COST_KEYS = [STEP_TYPE_DEFAULT,
                          STEP_TYPE_CONTRACT_CALL, STEP_TYPE_CONTRACT_CREATE, STEP_TYPE_CONTRACT_UPDATE,
                          STEP_TYPE_CONTRACT_DESTRUCT, STEP_TYPE_CONTRACT_SET,
                          STEP_TYPE_GET, STEP_TYPE_SET, STEP_TYPE_REPLACE, STEP_TYPE_DELETE, STEP_TYPE_INPUT,
                          STEP_TYPE_EVENT_LOG, STEP_TYPE_API_CALL]

CONTEXT_TYPE_INVOKE = 'invoke'
CONTEXT_TYPE_QUERY = 'query'

ZERO_TX_HASH = bytes(32)


class Governance(IconSystemScoreBase):
    """Governance Score for testing failure case during migration (that is on_update)"""
    _SCORE_STATUS = 'score_status'  # legacy
    _AUDITOR_LIST = 'auditor_list'
    _DEPLOYER_LIST = 'deployer_list'
    _VERSION = 'version'
    _SERVICE_CONFIG = 'service_config'
    _AUDIT_STATUS = 'audit_status'
    _REJECT_STATUS = 'reject_status'

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._auditor_list = ArrayDB(self._AUDITOR_LIST, db, value_type=Address)
        self._audit_status = DictDB(self._AUDIT_STATUS, db, value_type=bytes)
        self._reject_status = DictDB(self._REJECT_STATUS, db, value_type=bytes)

        self._version = VarDB(self._VERSION, db, value_type=str)

    def on_install(self) -> None:
        """DB initialization on score install
        """
        pass

    def on_update(self) -> None:
        super().on_update()
        self._migrate_v1_1_0()
        self._version.set('1.1.0')

    def _migrate_v1_1_0(self):
        # Migrate and Remove all icon network variables
        service_config = VarDB("service_config", self.db, value_type=int)

        step_types = ArrayDB('step_types', self.db, value_type=str)
        step_costs = DictDB('step_costs', self.db, value_type=int)
        step_price = VarDB('step_price', self.db, value_type=int)
        max_step_limits = DictDB('max_step_limits', self.db, value_type=int)

        revision_code = VarDB('revision_code', self.db, value_type=int)
        revision_name = VarDB('revision_name', self.db, value_type=str)

        import_white_list = DictDB('import_white_list', self.db, value_type=str)
        import_white_list_keys = ArrayDB('import_white_list_keys', self.db, value_type=str)
        score_black_list = ArrayDB('score_black_list', self.db, value_type=Address)

        deployer_list = ArrayDB('deployer_list', self.db, value_type=Address)

        # Convert DictDB to dict, ArrayDB to list
        pure_max_step_limits = {
            CONTEXT_TYPE_INVOKE: max_step_limits[CONTEXT_TYPE_INVOKE],
            CONTEXT_TYPE_QUERY: max_step_limits[CONTEXT_TYPE_QUERY]
        }
        pure_step_costs = {key: step_costs[key] for key in step_types}
        pure_import_white_list = {key: import_white_list[key].split(',') for key in import_white_list_keys}
        pure_score_black_list = list(score_black_list)

        # Migrates
        system_values = {
            IconNetworkValueType.SERVICE_CONFIG: service_config.get(),
            IconNetworkValueType.STEP_PRICE: step_price.get(),
            IconNetworkValueType.STEP_COSTS: pure_step_costs,
            IconNetworkValueType.MAX_STEP_LIMITS: pure_max_step_limits,
            IconNetworkValueType.REVISION_CODE: revision_code.get(),
            IconNetworkValueType.REVISION_NAME: revision_name.get(),
            IconNetworkValueType.IMPORT_WHITE_LIST: pure_import_white_list,
            IconNetworkValueType.SCORE_BLACK_LIST: pure_score_black_list
        }
        self.migrate_icon_network_value(system_values)

        # Remove all icon network variables
        service_config.remove()
        revision_code.remove()
        revision_name.remove()
        step_price.remove()
        max_step_limits.remove(CONTEXT_TYPE_QUERY)
        max_step_limits.remove(CONTEXT_TYPE_INVOKE)

        def _remove_array(array: ArrayDB):
            while True:
                ret = array.pop()
                if ret is None:
                    break

        for type_ in step_types:
            step_costs.remove(type_)
        _remove_array(step_types)

        for key in import_white_list_keys:
            import_white_list.remove(key)
        _remove_array(import_white_list_keys)
        _remove_array(score_black_list)
        _remove_array(deployer_list)

        revert("Migration failure")

    @external(readonly=True)
    def getVersion(self) -> str:
        return self._version.get()
