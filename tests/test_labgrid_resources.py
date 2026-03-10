import ast
import re
import time

import pytest
from helper import SystemdRun


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
def test_labgrid_resources_simple(shell, strategy, local_coordinator, check):
    exporter = strategy.target_hostname
    expected_resources = (
        (
            f"{exporter}/dut_power/NetworkPowerPort",
            (
                (("params", "host"), f"http://{exporter}/v1/dut/powered/compat"),
                (("params", "index"), "0"),
                (("params", "model"), "rest"),
            ),
        ),
        (
            f"{exporter}/http/RemoteHTTPProvider",
            (
                (("params", "external"), f"http://{exporter}/srv/"),
                (("params", "host"), exporter),
                (("params", "internal"), "/srv/www/"),
            ),
        ),
        (
            f"{exporter}/lxatac-usb-power-p1/NetworkUSBPowerPort",
            (
                (("params", "busnum"), 1),
                (("params", "devnum"), 2),
                (("params", "host"), exporter),
                (("params", "index"), 1),
                (("params", "path"), "1-1"),
                (("params", "model_id"), 9492),
                (("params", "vendor_id"), 1060),
            ),
        ),
        (
            f"{exporter}/lxatac-usb-power-p2/NetworkUSBPowerPort",
            (
                (("params", "busnum"), 1),
                (("params", "devnum"), 2),
                (("params", "host"), exporter),
                (("params", "index"), 2),
                (("params", "path"), "1-1"),
                (("params", "model_id"), 9492),
                (("params", "vendor_id"), 1060),
            ),
        ),
        (
            f"{exporter}/lxatac-usb-power-p3/NetworkUSBPowerPort",
            (
                (("params", "busnum"), 1),
                (("params", "devnum"), 2),
                (("params", "host"), exporter),
                (("params", "index"), 3),
                (("params", "path"), "1-1"),
                (("params", "model_id"), 9492),
                (("params", "vendor_id"), 1060),
            ),
        ),
        (
            f"{exporter}/out_0/HttpDigitalOutput",
            ((("params", "url"), f"http://{exporter}/v1/output/out_0/asserted"),),
        ),
        (
            f"{exporter}/out_1/HttpDigitalOutput",
            ((("params", "url"), f"http://{exporter}/v1/output/out_1/asserted"),),
        ),
        (
            f"{exporter}/serial/NetworkSerialPort",
            (
                (("params", "host"), exporter),
                (("params", "extra", "path"), "/dev/ttySTM1"),
            ),
        ),
        (
            f"{exporter}/tftp/RemoteTFTPProvider",
            (
                (("params", "external"), "/"),
                (("params", "host"), exporter),
                (("params", "internal"), "/srv/tftp/"),
            ),
        ),
    )
    for _ in range(60 // 15):
        resources = set(shell.run_check("LG_COORDINATOR=localhost labgrid-client resources"))
        if resources.issuperset(set(x[0] for x in expected_resources)):
            # We have found all resources in expected_resources (and possibly even more).
            break
        time.sleep(15)
    else:
        pytest.fail("Failed to get resources, even after trying for 1 minute")

    def get_nested(data, path):
        for key in path:
            if isinstance(data, dict):
                data = data[key]
            else:
                return None
        return data

    for expected_resource in expected_resources:
        if not expected_resource[1]:
            # No need to get details from the exporter if no tests are given
            continue

        # get currently running config
        details = shell.run_check(f"LG_COORDINATOR=localhost labgrid-client -vv resources {expected_resource[0]}")
        details = "".join(d for d in details if d.startswith("      "))
        details = ast.literal_eval(details)

        # Perform tests
        for expected_config in expected_resource[1]:
            with check:
                assert get_nested(details, expected_config[0]) == expected_config[1]


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
