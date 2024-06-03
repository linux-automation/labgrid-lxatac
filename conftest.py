import traceback

import pytest


@pytest.fixture(scope="function")
def barebox(strategy, target):
    try:
        strategy.transition("barebox")
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into barebox failed: {e}", returncode=3)

    return target.get_driver("BareboxDriver")


@pytest.fixture(scope="function")
def shell(strategy, target):
    try:
        strategy.transition("shell")
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into shell failed: {e}", returncode=3)

    return target.get_driver("ShellDriver")


@pytest.fixture(scope="function")
def online(strategy, target):
    try:
        strategy.transition("network")
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into online state failed: {e}", returncode=3)


@pytest.fixture(scope="function")
def system0_shell(strategy, target):
    try:
        strategy.transition("system0")
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into system0 shell failed: {e}", returncode=3)

    return target.get_driver("ShellDriver")


@pytest.fixture(scope="function")
def system1_shell(strategy, target):
    try:
        strategy.transition("system1")
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into system1 shell failed: {e}", returncode=3)

    return target.get_driver("ShellDriver")
