import traceback

import pytest

@pytest.fixture(scope='function')
def barebox(strategy, target):
    try:
        strategy.transition('barebox')
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into barebox failed: {e}", returncode=3)

    return target.get_driver('BareboxDriver')


@pytest.fixture(scope='function')
def shell(strategy, target):
    try:
        strategy.transition('shell')
    except Exception as e:
        traceback.print_exc()
        pytest.exit(f"Transition into shell failed: {e}", returncode=3)

    return target.get_driver('ShellDriver')


@pytest.fixture
def default_bootstate(strategy):
    """Set default state values as setup/teardown"""
    strategy.transition("barebox")
    strategy.barebox.run_check('bootchooser -a default -p default')

    yield

    strategy.transition("barebox")
    strategy.barebox.run_check('bootchooser -a default -p default')


@pytest.fixture
def set_bootstate(strategy, default_bootstate):
    """Sets the given bootchooser parameters."""
    def _set_bootstate(system0_prio, system0_attempts, system1_prio, system1_attempts):
        strategy.transition('barebox')
        barebox = strategy.barebox

        barebox.run_check(f'state.bootstate.system0.priority={system0_prio}')
        barebox.run_check(f'state.bootstate.system0.remaining_attempts={system0_attempts}')

        barebox.run_check(f'state.bootstate.system1.priority={system1_prio}')
        barebox.run_check(f'state.bootstate.system1.remaining_attempts={system1_attempts}')

        barebox.run_check('state -s')

    yield _set_bootstate


@pytest.fixture
def get_rauc_bundle_url(strategy, env, shell):
    """Makes the RAUC bundle target-accessible at the returned URL."""
    bundle = env.config.get_image_path('rauc_bundle')

    def _get_rauc_bundle_url():
        if strategy.httpprovider is None:
            pytest.skip("no HTTPProvider configured")
            return

        staged = strategy.httpprovider.stage(bundle)

        # ping default_gateway
        network_available = shell.poll_until_success('ping -c1 _gateway', timeout=60.0)
        assert network_available, 'no successful gateway ping within 60s'

        return staged

    yield _get_rauc_bundle_url
