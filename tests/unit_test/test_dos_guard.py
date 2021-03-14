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

from iconservice.dosguard import DoSGuard
from tests import create_address


class TestDoSGuard:
    def test_dos_guard_overflow_attack(self):
        reset_time = 1
        threshold = 10
        ban_time = 2

        dos_guard = DoSGuard(reset_time, threshold, ban_time)

        _from: str = str(create_address())
        for i in range(threshold):
            print(i)
            dos_guard.run(_from=_from)

        with pytest.raises(Exception):
            print(10)
            dos_guard.run(_from=_from)

        time.sleep(ban_time + 1)

        # already release
        # have to no raise
        print(11)
        dos_guard.run(_from=_from)
