import time

import pytest
from labgrid.resource.remote import RemotePlaceManager
from labgrid.remote.common import ResourceMatch
from labgrid.util import Timeout


def get_exporter_resources(exporter):
    """Retrieves all resources from the specified exporter."""
    rpm = RemotePlaceManager.get()
    rpm.poll()

    # wait for at least one export
    timeout = Timeout(30.0)
    while exporter not in rpm.session.resources:
        if timeout.expired:
            pytest.fail(f"No exports from {exporter} within {timeout.timeout} seconds")

        time.sleep(1)
        rpm.poll()

    time.sleep(10)
    rpm.poll()

    return rpm.session.resources[exporter]


def test_labgrid_resources_simple(strategy, shell):
    """Test non-managed resources."""
    resources = get_exporter_resources(strategy.target_hostname)

    serial_port = resources["serial"]["RawSerialPort"].asdict()
    assert serial_port["avail"]
    assert serial_port["params"]["extra"]["path"].startswith("/dev/ttySTM")

    power_port = resources["dut_power"]["NetworkPowerPort"].asdict()
    assert power_port["avail"]
    assert power_port["params"]["model"] == "rest"

    # The GPIOs are claimed by the tacd and should be controlled via it.
    # We need a driver for that
    #for gpio_idx in (0, 1):
    #    gpio = resources[f"gpio{gpio_idx}"]["SysfsGPIO"].asdict()
    #    assert gpio["avail"]


def test_labgrid_resources_usb(strategy, shell):
    """Test ManagedResources (udev)."""
    exporter = strategy.target_hostname
    groups = get_exporter_resources(exporter)
    match = ResourceMatch.fromstr(f"{exporter}/lxatac-usb-ports-p*/*")

    usb_resources = []

    for group_name, group in sorted(groups.items()):
        for resource_name, resource in sorted(group.items()):
            if match.ismatch((exporter, group_name, resource.cls, resource_name)):
                usb_resources.append(resource)

    # make sure at least one USB resource is available
    assert any(res.asdict()["avail"] for res in usb_resources)
