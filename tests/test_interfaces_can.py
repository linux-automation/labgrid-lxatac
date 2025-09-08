import json
import time

import helper
import pytest


def test_can_interface_can0(shell, check):
    """
    Test if can0_iobus is configured correctly.

    can0_iobus is used by the IOBus-server and is thus already configured and up.
    """

    output = shell.run_check("ip -j -detail l show dev can0_iobus")
    data = json.loads("\n".join(output))
    with check:
        assert len(data) == 1
    with check:
        assert data[0]["linkinfo"]["info_data"]["bittiming"]["bitrate"] == 101052
    with check:
        assert data[0]["linkinfo"]["info_data"]["bittiming"]["sjw"] == 5


def test_can_interface_can1(shell):
    """
    Test if can1 is configured correctly.

    can1 is unused in normal operation is thus not configured.
    """

    output = shell.run_check("ip -j l show dev can1")
    data = json.loads("\n".join(output))
    assert len(data) == 1


@pytest.fixture()
def can_configured(shell):
    """Setup can interface for use and clean up afterward."""
    shell.run_check("systemctl stop lxa-iobus")

    # setting both interfaces down, so we can reliably reset berr-counters
    shell.run_check("ip l set can0_iobus down")
    shell.run_check("ip l set can1 down")

    # Apply configuration for can1, can0_iobus is being configured by systemd-networkd
    shell.run_check("ip link set can1 type can tq 400 prop-seg 9 phase-seg1 9 phase-seg2 6 sjw 5")
    yield

    # setting both interfaces down, so we can reliably reset berr-counters
    shell.run_check("ip l set can0_iobus down")
    shell.run_check("ip l set can1 down")

    # bring system back to operational state
    shell.run_check("ip l set can0_iobus up")
    shell.run_check("systemctl start lxa-iobus")


def test_can_tools(shell):
    """Make sure canutils are present."""
    shell.run_check("which candump")
    shell.run_check("which cansend")


@pytest.mark.xfail(
    reason="We currently suspect the Socketcan MCAN driver to not reliably reset the berr-counter on if-down on 6.10. "
    "At least can0_iobus is usually in an error state, since there is no other (active) CAN-node on the bus until "
    "can1 is set up. "
    "Thus the test fails most of the time."
)
@pytest.mark.lg_feature("eet")
def test_can_traffic(shell, can_configured):
    """
    Test basic CAN transmission assuming IOBus-server is stopped and both can-interfaces are configured.

    Check if it is possible to transfer some data from one CAN interface to the other.
    Requires an external connection between both interfaces.
    """

    shell.run_check("ip l set can0_iobus up")
    shell.run_check("ip l set can1 up")

    dump_file = "/tmp/can-test"

    with helper.SystemdRun(f'bash -c "candump -n1 can1 > {dump_file}"', shell):
        shell.run_check("cansend can0_iobus 01a#11223344AABBCCDD")
        dump = shell.run_check(f"cat {dump_file}")
        assert "  can1  01A   [8]  11 22 33 44 AA BB CC DD" in dump


@pytest.mark.parametrize("can_interface", ("can0_iobus", "can1"))
def test_can_berr_reset(shell, can_configured, can_interface):
    """
    Resetting the berr_counters works as long as the other interface is down, see:
    https://lore.kernel.org/all/20250812-m_can-fix-state-handling-v1-0-b739e06c0a3b@pengutronix.de/

    This test makes sure that we can reset the berr-counters as long as the other interface is down.
    """

    # Bring up the berr-counter
    shell.run_check(f"ip link set {can_interface} up")
    shell.run_check(f"cansend {can_interface} 01a#11223344AABBCCDD")
    time.sleep(1)

    # After some time the interface should be passive. Let's check that:
    [if_state] = shell.run_check(f"ip -detail -json link show {can_interface}")
    [if_state] = json.loads(if_state)
    assert if_state["linkinfo"]["info_data"]["state"] == "ERROR-PASSIVE"
    assert if_state["linkinfo"]["info_data"]["berr_counter"]["tx"] == 128

    # Setting the interface down should reset the counter:
    shell.run_check(f"ip link set {can_interface} down")
    [if_state] = shell.run_check(f"ip -detail -json link show {can_interface}")
    [if_state] = json.loads(if_state)
    assert if_state["linkinfo"]["info_data"]["state"] == "STOPPED"
    assert if_state["linkinfo"]["info_data"]["berr_counter"]["tx"] == 0
    assert if_state["linkinfo"]["info_data"]["berr_counter"]["rx"] == 0
