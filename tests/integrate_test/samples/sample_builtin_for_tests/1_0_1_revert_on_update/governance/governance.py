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
        self._migrate_v1_0_1()
        self._version.set('1.0.1')

    def _migrate_v1_0_1(self):
        # Migrate and Remove all icon network variables
        revert("Migration failure")

    @external(readonly=True)
    def getVersion(self) -> str:
        return self._version.get()
