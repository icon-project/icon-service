from functools import wraps

import pytest

from iconservice.database.db import KeyValueDatabase, ContextDatabase
from iconservice.icon_constant import IconScoreContextType, IconNetworkValueType
from iconservice.inv.container import Container as INVContainer
from iconservice.inv.data.value import (
    RevisionCode,
    ScoreBlackList,
    StepPrice,
    StepCosts,
    MaxStepLimits,
    ServiceConfig,
    ImportWhiteList
)
from iconservice.iconscore.icon_score_step import StepType
from iconservice.utils import ContextStorage, ContextEngine
from tests.legacy_unittest.mock_db import MockKeyValueDatabase


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


# FIXME: Set valid step costs
def generate_inv_container(is_migrated: bool, revision: int = 0):
    is_migrated: bool = False
    service_config: int = 0
    step_costs = {
        'default': 0,
        'contractCall': 0,
        'contractCreate': 0,
        'contractUpdate': 0,
        'contractDestruct': 0,
        'contractSet': 0,
        'get': 0,
        'set': 0,
        'replace': 0,
        'delete': -150,
        'input': 0,
        'eventLog': 0,
        'apiCall': 0
    }
    step_costs = {StepType(key): val for key, val in step_costs.items()}
    max_step_limits: dict = {
        IconScoreContextType.INVOKE: 2_500_000_000,
        IconScoreContextType.QUERY: 50_000_000
    }
    step_price: int = 0
    score_black_list: list = []
    import_white_list = {"iconservice": ['*']}
    inv_container = INVContainer(is_migrated=False)
    inv_container._icon_network_values = {
        IconNetworkValueType.REVISION_CODE: RevisionCode(revision),
        IconNetworkValueType.SCORE_BLACK_LIST: ScoreBlackList(score_black_list),
        IconNetworkValueType.STEP_PRICE: StepPrice(step_price),
        IconNetworkValueType.STEP_COSTS: StepCosts(step_costs),
        IconNetworkValueType.MAX_STEP_LIMITS: MaxStepLimits(max_step_limits),
        IconNetworkValueType.SERVICE_CONFIG: ServiceConfig(service_config),
        IconNetworkValueType.IMPORT_WHITE_LIST: ImportWhiteList(import_white_list)
    }
    return inv_container


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
