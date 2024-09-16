import json
import traceback

import pytest


@pytest.fixture(scope="function")
def barebox(strategy):
    try:
        strategy.transition("barebox")
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into barebox failed: {e}", returncode=3)

    return strategy.barebox


@pytest.fixture(scope="function")
def shell(strategy):
    try:
        strategy.transition("shell")
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into shell failed: {e}", returncode=3)

    return strategy.shell


@pytest.fixture
def default_bootstate(strategy):
    """Set default state values as setup/teardown"""
    strategy.transition("barebox")
    strategy.barebox.run_check("bootchooser -a default -p default")

    yield

    strategy.transition("barebox")
    strategy.barebox.run_check("bootchooser -a default -p default")


@pytest.fixture
def booted_slot(shell):
    """Returns booted slot."""

    def _booted_slot():
        [stdout] = shell.run_check("rauc status --output-format=json", timeout=60)
        rauc_status = json.loads(stdout)

        assert "booted" in rauc_status, 'No "booted" key in rauc status json found'

        return rauc_status["booted"]

    yield _booted_slot


@pytest.fixture
def set_bootstate_in_bootloader(strategy, default_bootstate):
    """Sets the given bootchooser parameters."""

    def _set_bootstate(system0_prio, system0_attempts, system1_prio, system1_attempts):
        strategy.transition("barebox")
        barebox = strategy.barebox

        barebox.run_check(f"state.bootstate.system0.priority={system0_prio}")
        barebox.run_check(f"state.bootstate.system0.remaining_attempts={system0_attempts}")

        barebox.run_check(f"state.bootstate.system1.priority={system1_prio}")
        barebox.run_check(f"state.bootstate.system1.remaining_attempts={system1_attempts}")

        barebox.run_check("state -s")

    yield _set_bootstate


@pytest.fixture
def rauc_bundle(target, strategy, env, shell):
    """Makes the RAUC bundle target-accessible at the returned location."""
    bundle = env.config.get_image_path("rauc_bundle")

    def _rauc_bundle():
        target.activate(strategy.httpprovider)
        return strategy.httpprovider.stage(bundle)

    yield _rauc_bundle


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: These tests run especially slow.")
