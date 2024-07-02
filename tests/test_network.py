from http import client
from time import sleep
import subprocess
import json
import pytest


@pytest.fixture(scope="function")
def prepare_network(strategy, shell):
    """In order to test network, we use ourselves as an endpoint by using an Ethmux.
    For that, we create a new namespace where we put the DUT port in and which
    will communicate with the uplink port through the Ethmux."""
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


@pytest.mark.lg_feature("ethmux")
def test_network_tftp(prepare_network, shell):
    """Test tftp functionality"""

    fqdn = shell.target.get_resource("NetworkService").address

    # Create test file in tftp directory and grant access to it
    stdout, stderr, returncode = shell.run("touch /srv/tftp/test_file && chmod o+w /srv/tftp/test_file")
    assert returncode == 0

    # Create test file that will be uploaded
    stdout, stderr, returncode = shell.run("dd if=/dev/random of=./test_file bs=1M count=15")
    assert returncode == 0

    # Generate checksum
    checksum1, stderr, returncode = shell.run("md5sum ./test_file")
    assert returncode == 0
    assert len(checksum1) > 0

    # Upload file to tftp server
    stdout, stderr, returncode = shell.run("ip netns exec dut-namespace tftp -p -r ./test_file 10.11.12.2")
    assert returncode == 0

    # Download file from tftp server
    stdout, stderr, returncode = shell.run("ip netns exec dut-namespace tftp -g -r test_file 10.11.12.2")
    assert returncode == 0

    # Generate checksum
    checksum2, stderr, returncode = shell.run("md5sum ./test_file")
    assert returncode == 0
    assert len(checksum2) > 0

    # Compare checksums
    assert checksum1 == checksum2, f"checksum are different: {checksum1} != {checksum2}"

    # Clean up
    stdout, stderr, returncode = shell.run("rm /srv/tftp/test_file ./test_file")
    assert returncode == 0
