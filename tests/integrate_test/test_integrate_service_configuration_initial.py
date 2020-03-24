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

"""IconScoreEngine testcase
"""

from iconcommons import IconConfig

from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey, IconScoreContextType
from iconservice.icon_constant import IconServiceFlag
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateServiceConfigurationInitial(TestIntegrateBase):
    def setUp(self):
        self._block_height = 0
        self._prev_block_hash = None
        self.config = IconConfig("", default_icon_config)
        self.config.load()

        self.config.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin.address)})
        self.config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: False,
                                                     ConfigKey.SERVICE_FEE: False,
                                                     ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: False,
                                                     ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}})
        self.config.update_conf({ConfigKey.SCORE_ROOT_PATH: self._score_root_path,
                                 ConfigKey.STATE_DB_ROOT_PATH: self._state_db_root_path})

    def test_service_configuration_fee_setting(self):
        self.config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_FEE: True}})
        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(self.config)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        self.assertEqual(context.icon_service_flag, IconServiceFlag.FEE)

    def test_service_configuration_audit_setting(self):
        self.config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}})
        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(self.config)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        self.assertEqual(context.icon_service_flag, IconServiceFlag.AUDIT)

    def test_service_configuration_deployer_white_list_setting(self):
        self.config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: True}})
        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(self.config)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        self.assertEqual(context.icon_service_flag, IconServiceFlag.DEPLOYER_WHITE_LIST)

    def test_service_configuration_score_package_validiator_setting(self):
        self.config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: True}})
        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(self.config)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        self.assertEqual(context.icon_service_flag, IconServiceFlag.SCORE_PACKAGE_VALIDATOR)

    def test_service_configuration_multiple_setting(self):
        multiple_config = {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True,
                                               ConfigKey.SERVICE_FEE: True,
                                               ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: True,
                                               ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: True}}
        self.config.update_conf(multiple_config)
        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(self.config)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        expected_flag = IconServiceFlag.FEE | IconServiceFlag.AUDIT | \
                        IconServiceFlag.SCORE_PACKAGE_VALIDATOR | IconServiceFlag.DEPLOYER_WHITE_LIST
        self.assertEqual(context.icon_service_flag, expected_flag)

    def test_service_configuration_when_rc_monitor_setting_is_true(self):
        self.config.update_conf({ConfigKey.ICON_RC_MONITOR: True})
        self.icon_service_engine = IconServiceEngine()

        self.icon_service_engine.open(self.config)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        rc_open_command: list = context.engine.iiss._reward_calc_proxy._reward_calc.args
        assert '-monitor' in rc_open_command

    def test_service_configuration_when_rc_monitor_setting_is_false(self):
        self.config.update_conf({ConfigKey.ICON_RC_MONITOR: False})
        self.icon_service_engine = IconServiceEngine()

        self.icon_service_engine.open(self.config)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        rc_open_command: list = context.engine.iiss._reward_calc_proxy._reward_calc.args
        assert '-monitor' not in rc_open_command

    def test_service_configuration_default_rc_monitor_setting(self):
        self.icon_service_engine = IconServiceEngine()

        self.icon_service_engine.open(self.config)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        rc_open_command: list = context.engine.iiss._reward_calc_proxy._reward_calc.args
        assert '-monitor' in rc_open_command
