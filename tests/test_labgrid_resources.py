import time

import pytest
from labgrid.remote.common import ResourceMatch
from labgrid.resource.remote import RemotePlaceManager

# TODO: These tests make use of the RemotePlaceManager(), that is not meant to be used for cases like these.
# It would probably be better to create a new labgrid remote place with a labgrid `target` and the expected
# resources on the fly.


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
                out_0 = resources["out_0"]["HttpDigitalOutput"]
                out_1 = resources["out_0"]["HttpDigitalOutput"]

                if not serial_port.avail:
                    continue

                if not power_port.avail:
                    continue

                if not out_0.avail:
                    continue

                if not out_1.avail:
                    continue

                return (serial_port.params, power_port.params, out_0.params, out_1.params)

            except Exception:
                pass

        pytest.fail("Failed to get resources, even after trying for 5 minutes")

    serial_port_params, power_port_params, _out_0, _out_1 = retry_loop()

    assert serial_port_params["extra"]["path"].startswith("/dev/ttySTM")
    assert power_port_params["model"] == "rest"


def test_labgrid_resources_usb(strategy, shell, eet):
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

            except Exception:
                pass

        pytest.fail("Failed to get resources, even after trying for 5 minutes")

    if eet:
        eet.link("USB1_IN -> USB1_OUT, USB2_IN -> USB2_OUT, USB3_IN -> USB3_OUT")
    usb_resources = retry_loop()

    # make sure at least one USB resource is available
    assert usb_resources != []
