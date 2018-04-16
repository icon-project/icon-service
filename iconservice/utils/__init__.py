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
"""Utilities

Functions and classes in this module don't have any external dependencies.
"""

import re


def call_method(self,
                instance: object,
                method_name: str,
                params: dict=None) -> object:
    """Call a method of an instance in a generic way.

    :param icon_score:
    :param method_name:
    :param params:
    """
    method = getattr(instance, method_name)
    if not isinstance(method, callable):
        raise ValueError('Invalid method name')

    if params:
        return method(**params)
    else:
        return method()


def is_lowercase_hex_string(value: str) -> bool:
    """Check whether value is hexadecimal format or not

    :param value: text
    :return: True(lowercase hexadecimal) otherwise False
    """

    try:
        result = re.match('[0-9a-f]+', value)
        return len(result.group(0)) == len(value)
    except Exception:
        pass

    return False
