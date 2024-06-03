"""Basic rauc tests"""


# TODO: we should test if this image can install a recent stable bundle and
# if a recent stable bundle can install this bundle.
# That would need some strategy involvement, maybe even having a new
# "stable bundle booted" state so we do not accidentially test the stable
# bundle instead of the new one.


def test_rauc_version(shell):
    """
    Test basic availability working of rauc binary by obtaining version
    information
    """
    stdout = shell.run_check("rauc --version")
    assert "rauc" in "\n".join(stdout)


# TODO: decide how to pass a bundle URL
# def test_rauc_info_json(shell, get_rauc_bundle_url):
#    """Test rauc info output in JSON"""
#    bundle_url = get_rauc_bundle_url()
#    result = shell.run_check(f'rauc info {bundle_url} --output-format=json > /tmp/rauc.json')
#
#    result = shell.run_check('cat /tmp/rauc.json')
#    result = json.loads('\n'.join(result))
#    assert 'Linux Automation GmbH - LXA TAC' in result['compatible']
#    assert any('rootfs' in image for image in result['images'])


def test_system0_rauc_status(system0_shell):
    """
    Test basic slot status readout for system0.
    """
    system0_shell.run_check("rauc status", timeout=60)


def test_bootchooser_boot_system0_and_mark_bad(system0_shell, strategy):
    """
    Test if booting by priority works, mark system bad and test fallback.
    """

    slot = strategy.get_booted_slot()
    assert slot == "system0"

    # make sure there _is_ another slot
    strategy.transition("rauc_installed")

    # mark system0 bad
    system0_shell.run_check("rauc status mark-good other")
    system0_shell.run_check("rauc status mark-bad booted")

    # transition: shell -> off -> shell
    strategy.transition("off")
    strategy.transition("shell")

    slot = strategy.get_booted_slot()

    assert slot == "system1"

    # mark system0 good again, we were just pretending after all
    system0_shell.run_check("rauc status mark-good other")
    system0_shell.run_check("rauc status mark-active other")


def test_system1_rauc_status(system1_shell):
    """
    Test basic slot status readout for system1.
    """
    system1_shell.run_check("rauc status", timeout=60)


def test_bootchooser_boot_system1_and_mark_bad(system1_shell, strategy):
    """
    Test if booting by priority works, mark system bad and test fallback.
    """

    slot = strategy.get_booted_slot()
    assert slot == "system1"

    # mark system1 bad
    # TODO: why do we need all of these?
    system1_shell.run_check("rauc status mark-bad booted")
    system1_shell.run_check("rauc status mark-good other")
    system1_shell.run_check("rauc status mark-active other")

    # transition: shell -> off -> shell
    strategy.transition("off")
    strategy.transition("shell")

    slot = strategy.get_booted_slot()
    assert slot == "system0"

    # mark system1 good again, we were just pretending after all
    system1_shell.run_check("rauc status mark-good other")
    system1_shell.run_check("rauc status mark-active other")
