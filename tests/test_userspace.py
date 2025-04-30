import csv
import json


def test_chrony(shell):
    """Test that chronyd is running and synchronized."""
    stdout = shell.run_check("chronyc -c tracking")
    csv_reader = csv.reader(stdout)

    for line in csv_reader:
        # make sure stratum > 0 is used
        assert int(line[2]) > 0


def test_switch_configuration(shell, check):
    """Test that the switch is configured correctly."""
    uplink_ifname = "uplink"

    [bridge] = shell.run_check("bridge -j link")
    bridge_json = json.loads(bridge)

    # interface exists
    assert any(b["ifname"] == uplink_ifname for b in bridge_json)

    # interface is in expected state
    for b in bridge_json:
        if b["ifname"] == uplink_ifname:
            assert b["state"] == "forwarding"

    [ip_link] = shell.run_check("ip -d -j link show tac-bridge")
    [ip_link_json] = json.loads(ip_link)

    # link attributes are in expected state
    with check:
        assert ip_link_json["linkinfo"]["info_data"]["stp_state"] == 0
    with check:
        assert ip_link_json["linkinfo"]["info_data"]["mcast_snooping"] == 0

    [ip_addr] = shell.run_check("ip -d -j addr show tac-bridge")
    [ip_addr_json] = json.loads(ip_addr)

    mac = ip_addr_json["address"]
    link_local_v6 = next(
        ai["local"] for ai in ip_addr_json["addr_info"] if ai["family"] == "inet6" and ai["scope"] == "link"
    )
    global_v6 = next(
        ai["local"] for ai in ip_addr_json["addr_info"] if ai["family"] == "inet6" and ai["scope"] == "global"
    )

    # Each TAC is assigned 16 MAC addresses and the tac-bridge should use
    # the one ending in '3'.
    with check:
        assert mac[-1] == "3"

    # Check if the configured v6 addresses are derived from the current MAC address.
    v6_tail = mac.split(":")
    v6_tail.insert(3, "fe")
    v6_tail.insert(3, "ff")
    v6_tail = list(int(a + b, 16) for a, b in zip(v6_tail[::2], v6_tail[1::2]))
    v6_tail[0] ^= 0x0200
    v6_tail = ":".join(f"{a:x}" for a in v6_tail)

    with check:
        assert link_local_v6.endswith(v6_tail)
    with check:
        assert global_v6.endswith(v6_tail)


def test_hostname(shell, check):
    """Test whether the serial number is contained in the hostname"""

    [serial_number] = shell.run_check("cat /sys/firmware/devicetree/base/chosen/baseboard-factory-data/serial-number")
    serial_number = serial_number.rstrip("\x00")  # Remove trailing \0
    serial_number = serial_number.split(".")[-1]  # Only the last part is used in the hostname

    [hostname] = shell.run_check("hostname")

    with check:
        assert serial_number in hostname

    [etc_hostname] = shell.run_check("cat /etc/hostname")

    with check:
        assert etc_hostname != "localhost"

    with check:
        assert serial_number in etc_hostname
