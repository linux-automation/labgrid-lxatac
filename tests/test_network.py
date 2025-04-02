import hashlib
import json
from time import sleep

import helper
import pytest
import requests


@pytest.fixture(scope="function")
def prepare_network(strategy, shell):
    """
    To test the TAC's network, we use ourselves as an endpoint by using an Ethmux.
    For that, we create a new namespace where we put the DUT port in and which
    will communicate with the uplink port through the Ethmux.

    This way we can check that both network ports are working as expected.
    And it also allows us to test local services like TFTP and HTTP server against
    ourselves without the need for an external test setup on the labgrid exporter.
    """
    strategy.ethmux.set(False)  # Connect Upstream Ethernet-port to DUT Ethernet-port
    shell.run_check("systemctl stop tacd")
    shell.run_check("systemctl stop NetworkManager")
    shell.run_check("ip link delete tac-bridge")
    shell.run_check("ip netns add dut-namespace")
    shell.run_check("ip link set dut netns dut-namespace")
    shell.run_check("ip netns exec dut-namespace ip link set dev dut up")
    shell.run_check("ip netns exec dut-namespace ip addr add 10.11.12.1/24 dev dut")
    shell.run_check("ip link set dev uplink up")
    shell.run_check("ip addr add 10.11.12.2/24 dev uplink")
    yield
    shell.run_check("ip addr del 10.11.12.2/24 dev uplink")
    shell.run_check("ip netns exec dut-namespace ip link set dut netns 1")
    shell.run_check("ip netns del dut-namespace")
    shell.run_check("systemctl start NetworkManager")
    shell.run_check("systemctl start tacd")
    strategy.ethmux.set(True)  # Reconnect Upstream Ethernet-port to Lab Network
    strategy.wait_online()


@pytest.mark.lg_feature("ethmux")
def test_network_tftp(prepare_network, shell, log_duration):
    """Test tftp functionality"""

    try:
        # Create test file in tftp directory and grant access to it
        shell.run_check("touch /srv/tftp/test_file && chmod o+w /srv/tftp/test_file")

        # Create test file that will be uploaded
        shell.run_check("dd if=/dev/random of=./test_file bs=1M count=15")

        # Generate checksum
        checksum1 = shell.run_check("md5sum ./test_file")
        assert len(checksum1) > 0

        # Upload file to tftp server
        with log_duration("tftp put"):
            shell.run_check("ip netns exec dut-namespace tftp -p -r ./test_file 10.11.12.2", timeout=35)

        # Download file from tftp server
        with log_duration("tftp get"):
            shell.run_check("ip netns exec dut-namespace tftp -g -r test_file 10.11.12.2", timeout=35)

        # Generate checksum
        checksum2 = shell.run_check("md5sum ./test_file")
        assert len(checksum2) > 0

        # Compare checksums
        assert checksum1 == checksum2, f"checksum are different: {checksum1} != {checksum2}"

    finally:
        # Clean up
        shell.run("rm /srv/tftp/test_file ./test_file")


@pytest.mark.slow
@pytest.mark.lg_feature("ethmux")
@pytest.mark.parametrize(
    "bandwidth, expected",
    ((10, pytest.approx(9, rel=0.1)), (100, pytest.approx(90, rel=0.1)), (1000, pytest.approx(350, rel=0.1))),
)
def test_network_performance(prepare_network, shell, record_property, bandwidth, expected):
    """Test network performance via iperf3"""

    try:
        # Set bandwidth on both interfaces
        shell.run_check(f"ethtool -s uplink speed {bandwidth}")
        shell.run_check(f"ip netns exec dut-namespace ethtool -s dut speed {bandwidth}")

        # Await setup time
        sleep(5)

        # Start iperf server in network namespace
        port = 5151
        with helper.SystemdRun(f"ip netns exec dut-namespace iperf3 -s -1 -p {port}", shell):
            # Run iperf client client in default network namespace
            stdout = shell.run_check(f"iperf3 -J -c 10.11.12.1 -p {port}")

            results = json.loads("".join(stdout), strict=False)

            mbps_received = results["end"]["sum_received"]["bits_per_second"] / 1e6
            record_property(f"actual-bandwidth-{bandwidth}", mbps_received)
            assert mbps_received == expected

    finally:
        # Reset bandwidth configuration
        shell.run("ethtool -s uplink speed 1000")
        shell.run("ip netns exec dut-namespace ethtool -s dut speed 1000")


def test_network_interfaces(shell):
    """Test whether all expected network interfaces are present"""

    found_interfaces = set()
    stdout = shell.run_check("ip --json link show")
    interfaces = json.loads("".join(stdout))

    expected_interfaces = {
        "lo",
        "can0_iobus",
        "can1",
        "switch",
        "dut",
        "uplink",
        "tac-bridge",
    }

    for interface in interfaces:
        found_interfaces.add(interface["ifname"])

    assert expected_interfaces == found_interfaces


@pytest.mark.lg_feature("ptx-flavor")
def test_network_nfs_io(env, target, shell, check):
    """Test nfs share io"""
    ptx_works = set(env.config.get_target_option(target.name, "ptx-works-available"))

    readable = set()
    writeable = set()
    missing = set()
    # Iterate over all available shares and check whether io operation is possible
    for ptx_work in ptx_works:
        # Check if an automount unit has been created
        _, _, rc = shell.run(f"findmnt --json {ptx_work} -t autofs")
        if rc != 0:
            missing.add(ptx_work)

        # Make sure the directories contain something
        dir_contents, _, rc = shell.run(f"ls -1 {ptx_work}", timeout=60)
        # Timeout of the automount-units are a generous 30s.
        # Let's use a much longer timeout for our commands to catch all problems on the DUT.
        if len(dir_contents) > 0 and rc == 0:
            readable.add(ptx_work)

        # Check if the share is mounted readonly
        stdout, _, rc = shell.run(f"findmnt --json {ptx_work} -t nfs4")
        # Ignore if we do not find the mountpoint here, since one of the other tests very likely found the problem.
        if rc == 0:
            [fs_info] = json.loads("\n".join(stdout))["filesystems"]
            if "rw" in fs_info["options"].split(","):
                writeable.add(ptx_work)

    with check:
        assert missing == set(), "These ptx-works do not have corresponding automount-units"
    with check:
        assert ptx_works == readable, "Mounts are not readable"
    with check:
        assert writeable == set(), "Mounts are writeable but should not be"


def test_network_http_io(strategy, shell):
    """Test http server file io"""

    try:
        # Create test file
        shell.run_check("dd if=/dev/random of=/srv/www/test_file bs=1M count=15")
        [output] = shell.run_check("md5sum /srv/www/test_file")
        assert len(output) > 0

        # Cut out hash from output
        checksum1 = output.split(" ")[0]

        # Download test file
        r = requests.get(f"http://{strategy.network.address}/srv/test_file")
        assert r.status_code == 200

        checksum2 = hashlib.md5(r.content).hexdigest()

        assert checksum1 == checksum2, f"checksums are different: {checksum1} != {checksum2}"

    finally:
        # Delete test file
        shell.run("rm /srv/www/test_file")
