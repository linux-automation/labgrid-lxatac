import time

import pytest
from labgrid.resource.remote import RemotePlaceManager
from labgrid.remote.common import ResourceMatch
from labgrid.util import Timeout

def test_labgrid_resources_simple(strategy, shell):
    """Test non-managed resources."""

    def retry_loop():
        rpm = RemotePlaceManager.get()
        exporter = strategy.target_hostname

        for _ in range(300):
            time.sleep(1)
            rpm.poll()

            try:
                resources = rpm.session.resources[exporter]
                serial_port = resources["serial"]["RawSerialPort"]
                power_port = resources["dut_power"]["NetworkPowerPort"]

                if not serial_port.avail:
                    continue

                if not power_port.avail:
                    continue

                return (serial_port.params, power_port.params)

            except Exception as e:
                pass

        pytest.fail("Failed to get resources, even after trying for 5 minutes")

    serial_port_params, power_port_params = retry_loop()

    assert serial_port_params["extra"]["path"].startswith("/dev/ttySTM")
    assert power_port_params["model"] == "rest"

    # The GPIOs are claimed by the tacd and should be controlled via it.
    # We need a driver for that
    #for gpio_idx in (0, 1):
    #    gpio = resources[f"gpio{gpio_idx}"]["SysfsGPIO"].asdict()
    #    assert gpio["avail"]


def test_labgrid_resources_usb(strategy, shell):
    """Test ManagedResources (udev)."""

    def retry_loop():
        rpm = RemotePlaceManager.get()
        exporter = strategy.target_hostname
        match = ResourceMatch.fromstr(f"{exporter}/lxatac-usb-ports-p*/*")

        for _ in range(300):
            time.sleep(1)
            rpm.poll()

            try:
                usb_resources = []

                groups = rpm.session.resources[exporter]
                for group_name, group in sorted(groups.items()):
                    for resource_name, resource in sorted(group.items()):
                        if match.ismatch((exporter, group_name, resource.cls, resource_name)) and resource.avail:
                            usb_resources.append(resource)

                if len(usb_resources) > 0:
                    return usb_resources

            except Exception as e:
                pass

        pytest.fail("Failed to get resources, even after trying for 5 minutes")

    usb_resources = retry_loop()

    # make sure at least one USB resource is available
    assert usb_resources != []
