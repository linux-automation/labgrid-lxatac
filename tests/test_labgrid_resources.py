import logging
import re
import time

import pytest
from helper import SystemdRun
from labgrid.resource.remote import RemotePlaceManager


@pytest.fixture
def local_coordinator(shell):
    """
    Set up the DUT in a way, that it has a labgrid-coordinator running locally and
    the coordinator is used by the labgrid-exporter.
    Afterward make sure the configuration change is undone.
    """
    with SystemdRun(command="labgrid-coordinator -l localhost:20408", shell=shell):
        shell.run_check("echo LABGRID_COORDINATOR_IP=localhost > /etc/labgrid/environment.local")
        shell.run_check("echo LABGRID_COORDINATOR_PORT=20408 >> /etc/labgrid/environment.local")
        shell.run_check("mkdir /etc/systemd/system/labgrid-exporter.service.d/")
        shell.run_check("echo [Service] > /etc/systemd/system/labgrid-exporter.service.d/local.conf")
        shell.run_check(
            "echo EnvironmentFile=/etc/labgrid/environment.local >> "
            "/etc/systemd/system/labgrid-exporter.service.d/local.conf"
        )
        shell.run_check("systemctl daemon-reload")
        shell.run_check("systemctl restart labgrid-exporter")
        yield
        shell.run_check("rm -r /etc/systemd/system/labgrid-exporter.service.d")
        shell.run_check("systemctl daemon-reload")
        shell.run_check("systemctl restart labgrid-exporter")


@pytest.mark.slow
def test_labgrid_resources_simple(strategy, shell, check):
    """Test non-managed resources."""

    def retry_loop(logger):
        rpm = RemotePlaceManager.get()
        exporter = strategy.target_hostname

        for _ in range(300 // 15):
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

            logger.info("(Still) waiting for labgrid resources to appear...")
            time.sleep(15)

        pytest.fail("Failed to get resources, even after trying for 5 minutes")

    logger = logging.getLogger("test_labgrid_resources_simple")
    serial_port_params, power_port_params, _out_0, _out_1 = retry_loop(logger)

    with check:
        assert serial_port_params["extra"]["path"].startswith("/dev/ttySTM")
    with check:
        assert power_port_params["model"] == "rest"


@pytest.mark.slow
def test_labgrid_resources_usb(shell, eet, strategy, local_coordinator):
    """
    Test if a USB device connected to one of the usb-ports is exported correctly.
    """
    if eet:
        eet.link("USB1_IN -> USB1_OUT, USB2_IN -> USB2_OUT, USB3_IN -> USB3_OUT")

    exporter = strategy.target_hostname
    resource_re = re.compile(exporter + r"\/lxatac-usb-ports-p.*\/.*")
    for _ in range(60 // 15):
        resources = shell.run_check("LG_COORDINATOR=localhost labgrid-client resources")
        for resource in resources:
            match = resource_re.match(resource)
            if match:
                break
        else:
            time.sleep(15)
            continue
        break
    else:
        pytest.fail("Failed to get resources, even after trying for 1 minute")
