# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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


class IcxIssueFormula(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        self._handler = {'prep': self.handle_icx_issue_formula_for_prep,
                         'eep': self.handle_icx_issue_formula_for_eep,
                         'dapp': self.handle_icx_issue_formula_for_dapp}

        self._prep_count = 23
        self._sub_prep_count = 100
        self._month = 12
        self._block_generation_amount_per_year = 1000

    def calculate(self, group, data):
        handler = self._handler[group]
        value = handler(data)
        return value

    @staticmethod
    def handle_icx_issue_formula_for_prep(data: dict) -> int:
        return 1

    @staticmethod
    def handle_icx_issue_formula_for_eep(data: dict) -> int:
        return 2

    @staticmethod
    def handle_icx_issue_formula_for_dapp(data: dict) -> int:
        return 3
