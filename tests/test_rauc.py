"""Basic rauc tests"""

import json

import pytest
from labgrid.driver import ExecutionError


def get_booted_slot(shell):
    """Returns booted slot."""
    stdout = shell.run_check('rauc status --output-format=json', timeout=60)
    rauc_status = json.loads(stdout[0])

    assert 'booted' in rauc_status, 'No "booted" key in rauc status json found'

    return rauc_status['booted']


def test_rauc_version(shell):
    """
    Test basic availability working of rauc binary by obtaining version
    information
    """
    stdout = shell.run_check('rauc --version')
    assert 'rauc' in '\n'.join(stdout)


def test_rauc_status(shell):
    """
    Test basic slot status readout.
    """
    shell.run_check('rauc status', timeout=60)


def test_rauc_info_json(shell, get_rauc_bundle_url):
    """Test rauc info output in JSON"""
    bundle_url = get_rauc_bundle_url()
    result = shell.run_check(f'rauc info {bundle_url} --output-format=json > /tmp/rauc.json')

    result = shell.run_check('cat /tmp/rauc.json')
    result = json.loads('\n'.join(result))
    assert 'lxatac' in result['compatible']
    assert any('rootfs' in image for image in result['images'])


@pytest.mark.dependency()
def test_rauc_install(strategy, get_rauc_bundle_url, set_bootstate):
    """
    Test if rauc install works.
    """
    set_bootstate(20, 1, 10, 1)
    strategy.transition('shell')
    shell = strategy.shell

    assert get_booted_slot(shell) == 'system0'

    bundle_url = get_rauc_bundle_url()
    shell.run_check(f'rauc install {bundle_url}', timeout=600)

    # transition: shell -> off -> shell
    strategy.transition('off')
    strategy.transition('shell')

    assert get_booted_slot(shell) == 'system1'

    try:
        shell.run_check("systemctl is-system-running")
    except ExecutionError:
        # gather information about failed units
        shell.run("systemctl list-units --failed --no-legend --plain --no-pager")
        raise


@pytest.mark.dependency(depends=['test_rauc_install'])
def test_bootchooser_boot_system0_and_mark_bad(strategy, set_bootstate):
    """
    Test if booting by priority works, mark system bad and test fallback.
    """
    set_bootstate(20, 1, 10, 1)
    strategy.transition('shell')
    shell = strategy.shell

    assert get_booted_slot(shell) == 'system0'

    # mark system0 bad
    shell.run_check('rauc status mark-bad')

    # transition: shell -> off -> shell
    strategy.transition('off')
    strategy.transition('shell')

    assert get_booted_slot(shell) == 'system1'


@pytest.mark.dependency(depends=['test_rauc_install'])
def test_bootchooser_boot_system1_and_mark_bad(strategy, set_bootstate):
    """
    Test if booting by priority works, mark system bad and test fallback.
    """
    set_bootstate(10, 1, 20, 1)
    strategy.transition('shell')
    shell = strategy.shell

    assert get_booted_slot(shell) == 'system1'

    # mark system1 bad
    shell.run_check('rauc status mark-bad')

    # transition: shell -> off -> shell
    strategy.transition('off')
    strategy.transition('shell')

    assert get_booted_slot(shell) == 'system0'
