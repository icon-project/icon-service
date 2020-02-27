from functools import wraps

import pytest

from iconservice.database.db import KeyValueDatabase, ContextDatabase
from iconservice.icon_constant import IconScoreContextType, IconNetworkValueType
from iconservice.icon_network.container import Container as INVContainer
from iconservice.icon_network.data.value import (
    RevisionCode,
    ScoreBlackList,
    StepPrice,
    StepCosts,
    MaxStepLimits,
    ServiceConfig,
    ImportWhiteList
)
from iconservice.utils import ContextStorage, ContextEngine
from tests.mock_db import MockKeyValueDatabase


def patch_several(*decorate_args):
    def start_patches(*args):
        for patcher in args:
            patcher.start()

    def stop_patches(*args):
        for patcher in args:
            patcher.stop()

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_patches(*decorate_args)
            ret = func(*args, **kwargs)
            stop_patches(*decorate_args)
            return ret

        return wrapper

    return decorate


def generate_inv_container(is_migrated: bool, revision: int = 0):
    is_migrated: bool = False
    service_config: int = 0
    step_costs = {
        'default': 1_000_000,
        'contractCall': 15_000,
        'contractCreate': 200_000,
        'contractUpdate': 80_000,
        'contractDestruct': -70_000,
        'contractSet': 30_000,
        'get': 0,
        'set': 200,
        'replace': 50,
        'delete': -150,
        'input': 200,
        'eventLog': 100,
        'apiCall': 0
    }
    max_step_limits: dict = {
        IconScoreContextType.INVOKE: 2_500_000_000,
        IconScoreContextType.QUERY: 50_000_000
    }
    step_price: int = 0
    score_black_list: list = []
    import_white_list = {"iconservice": ['*']}
    system_value = INVContainer(is_migrated=False)
    system_value._cache = {
        IconNetworkValueType.REVISION_CODE: RevisionCode(revision),
        IconNetworkValueType.SCORE_BLACK_LIST: ScoreBlackList(score_black_list),
        IconNetworkValueType.STEP_PRICE: StepPrice(step_price),
        IconNetworkValueType.STEP_COSTS: StepCosts(step_costs),
        IconNetworkValueType.MAX_STEP_LIMITS: MaxStepLimits(max_step_limits),
        IconNetworkValueType.SERVICE_CONFIG: ServiceConfig(service_config),
        IconNetworkValueType.IMPORT_WHITE_LIST: ImportWhiteList(import_white_list)
    }
    return system_value


@pytest.fixture(scope="function")
def context_db():
    mocked_kv_db: 'KeyValueDatabase' = MockKeyValueDatabase.create_db()
    return ContextDatabase(mocked_kv_db)


@pytest.fixture(scope="session", autouse=True)
def set_default_context_storage_and_engine():
    # Only work on python3 upper
    temp_storage, temp_engine = ContextStorage.__new__.__defaults__, ContextEngine.__new__.__defaults__
    ContextStorage.__new__.__defaults__ = (None,) * len(ContextStorage._fields)
    ContextEngine.__new__.__defaults__ = (None,) * len(ContextEngine._fields)
    yield
    ContextStorage.__new__.__defaults__, ContextEngine.__new__.__defaults__ = temp_storage, temp_engine
