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
import time

import pytest

from iconservice.icon_constant import ConfigKey
from iconservice.statics import Statics
from tests import create_address


class TestStatics:
    def test_statics_ip_overflow_attack(self):
        diff_reset_time = 1
        dos_check_count = 10
        dos_release_time = 2

        conf = {
            ConfigKey.DIFF_RESET_TIME: diff_reset_time,
            ConfigKey.DOS_CHECK_COUNT: dos_check_count,
            ConfigKey.DOS_RELEASE_TIME: dos_release_time,
        }
        statics = Statics(conf)

        ip: str = "192.168.0.1"
        for i in range(dos_check_count + 2):
            print(i)
            try:
                statics.update(ip=ip, params={"from": str(create_address())})
            except Exception as e:
                print(e)

        time.sleep(dos_release_time - 1)

        try:
            print(12)
            statics.update(ip=ip, params={"from": str(create_address())})
        except Exception as e:
            print(e)

        time.sleep(dos_release_time)

        # already release
        # have to no raise
        print(13)
        statics.update(ip=ip, params={"from": str(create_address())})
        print("release!")
