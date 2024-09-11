import json

import pytest


def test_can_interface_can0(shell):
    """
    Test if can0_iobus is configured correctly.

    can0_iobus is used by the IOBus-server and is thus already configured and up.
    """

    output = shell.run_check("ip -j -detail l show dev can0_iobus")
    data = json.loads("\n".join(output))
    assert len(data) == 1
    assert data[0]["linkinfo"]["info_data"]["bittiming"]["bitrate"] == 101052
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
    shell.run_check("ip l set can0_iobus down")
    shell.run_check("ip l set can1 down")
    shell.run_check("ip link set can1 type can tq 400 prop-seg 9 phase-seg1 9 phase-seg2 6 sjw 5")
    shell.run_check("ip l set can0_iobus up")
    shell.run_check("ip l set can1 up")
    yield
    shell.run_check("ip l set can1 down")
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

    dump_file = "/tmp/can-test"

    shell.run_check(f"candump -n1 can1 > {dump_file} &")
    shell.run_check("cansend can0_iobus 01a#11223344AABBCCDD")

    dump = shell.run_check(f"cat {dump_file}")
    assert "  can1  01A   [8]  11 22 33 44 AA BB CC DD" in dump
