from unittest.mock import Mock

import pytest

from iconservice import ZERO_SCORE_ADDRESS, Address
from iconservice.icon_constant import Revision
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_event_log import EventLogEmitter
from iconservice.icx.issue.engine import Engine as IssueEngine
from tests import create_address


@pytest.fixture(scope="function", params=[revision.value for revision in Revision])
def context(request):
    context = Mock(spec=IconScoreContext)
    context.revision = request.param
    return context


@pytest.fixture(scope="function")
def issue_engine(monkeypatch):
    issue_engine: 'IssueEngine' = IssueEngine()
    monkeypatch.setattr(IssueEngine, "_burn", Mock())
    yield issue_engine
    monkeypatch.undo()


@pytest.fixture(scope="function", autouse=True)
def event_log_emitter(monkeypatch):
    monkeypatch.setattr(EventLogEmitter, "emit_event_log", Mock())
    yield
    monkeypatch.undo()


class TestIssueEngine:

    def test_burn_event_log_should_be_fixed_after_revision_9(self, context, issue_engine):
        address: 'Address' = create_address()
        amount: int = 10
        expected_score_address: 'Address' = ZERO_SCORE_ADDRESS
        expected_signature: str = "ICXBurned(int)" \
            if context.revision >= Revision.FIX_BURN_EVENT_SIGNATURE.value else "ICXBurned"
        expected_arguments: list = [amount]
        expected_indexed_args_count: int = 0

        issue_engine.burn(context, address, amount)

        issue_engine._burn.assert_called_with(context, address, amount)
        EventLogEmitter.emit_event_log.assert_called_with(context,
                                                          score_address=expected_score_address,
                                                          event_signature=expected_signature,
                                                          arguments=expected_arguments,
                                                          indexed_args_count=expected_indexed_args_count)
