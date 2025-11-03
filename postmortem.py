import logging

import pytest
from pytest import CollectReport, StashKey

_phase_report_key = StashKey[dict[str, CollectReport]]()
_pm_logger = logging.getLogger("post-mortem")


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    """
    Make the report for a step available in the item's stash, so that
    fixtures can read the result in their teardown phase.
    Heavily inspired by: https://docs.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
    Implements the runtest_makereport-hook: https://docs.pytest.org/en/latest/reference/reference.html#std-hook-pytest_runtest_makereport

    :param item: The item the report is generated for.
    :param call: CallInfo for this phase
    :return: The report re received from the previous hook.
    """
    rep = yield

    # store test results for each phase of a call, which can
    # be "setup", "call", "teardown"
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep
    return rep


@pytest.fixture(autouse=True)
def pm_system(request: pytest.FixtureRequest, strategy, record_property):
    """
    Retrieves post-mortem diagnosis information from the strategy and emits the information to the log with level
    WARNING and also adds the information to the `junit.xml`.

    The strategy must implement a strategy.postmotem_info().
    It is up to the strategy to decide which information to collect depending on the DUTs status and the connections
    available (e.g. serial or ssh).
    """
    yield

    report = request.node.stash[_phase_report_key]
    if "call" in report and report["call"].failed:
        post_mortem_info: dict[str, list[str]] = strategy.postmortem_info()
        record_property("postmortem", post_mortem_info)
        for key, value in post_mortem_info.items():
            _pm_logger.warning(f"POST-MORTEM INFO: {key}")
            for line in value:
                _pm_logger.warning(f"| {line}")
