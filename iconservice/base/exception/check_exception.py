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

import traceback
from functools import wraps

from base_exception import *


# 예외 검사 간편하게 할 수 있는 함수인데..
# 사용할지 안할지는 지켜본다.
def check_exception(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ScoreBaseException:
            log_call_stack = traceback.format_stack()
            log_exec = traceback.format_exc()
            # TODO replace log function
            print(f'call_stack\n', *log_call_stack, log_exec)
        except IcxException:
            log_call_stack = traceback.format_stack()
            log_exec = traceback.format_exc()
            # TODO replace log function
            print(f'call_stack\n', *log_call_stack, log_exec)
        except IconServiceBaseException:
            log_call_stack = traceback.format_stack()
            log_exec = traceback.format_exc()
            # TODO replace log function
            print(f'call_stack\n', *log_call_stack, log_exec)
        except Exception:
            raise
        finally:
            pass
    return _wrapper
