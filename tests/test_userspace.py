import json

import pytest
from labgrid.driver import ExecutionError


def system_running(shell):
    try:
        # the strategy already waits for this when transitioning to the shell state
        shell.run_check("systemctl is-system-running")
    except ExecutionError:
        # gather information about failed units
        shell.run("systemctl list-units --failed --no-legend --plain --no-pager")
        raise


@pytest.mark.slow
def test_system_running_0(system0_shell):
    system_running(system0_shell)


@pytest.mark.slow
def test_system_running_1(system1_shell):
    system_running(system1_shell)


def test_nfs_mounts(env, target, shell):
    """Test that the NFS mounts listed in the environment config are available."""
    ptx_works = env.config.get_target_option(target.name, "ptx-works-available")

    mount = shell.run_check("mount")
    mount = "\n".join(mount)

    for ptx_work in ptx_works:
        assert ptx_work in mount

        dir_contents = shell.run_check(f"ls -1 {ptx_work}")
        # make sure the directories contain something
        assert len(dir_contents) > 0


def test_chrony(shell):
    """Test that chronyd is running and synchronized."""
    [chronyc] = shell.run_check("chronyc -c tracking")
    chronyc_csv = chronyc.split(",")

    # make sure stratum > 0 is used
    assert int(chronyc_csv[2]) > 0


def test_switch_configuration(shell):
    """Test that the switch is configured correctly."""
    uplink_ifname = "uplink"

    [bridge] = shell.run_check("bridge -j link")
    bridge_json = json.loads(bridge)

    # interface exists
    any(b["ifname"] == uplink_ifname for b in bridge_json)

    # interface is in expected state
    for b in bridge_json:
        if b["ifname"] == uplink_ifname:
            assert b["state"] == "forwarding"

    [ip_link] = shell.run_check("ip -d -j link show tac-bridge")
    [ip_link_json] = json.loads(ip_link)

    # link attributes are in expected state
    assert ip_link_json["linkinfo"]["info_data"]["stp_state"] == 0
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
    assert mac[-1] == "3"

    # Check if the configured v6 addresses are derived from the current MAC address.
    v6_tail = mac.split(":")
    v6_tail.insert(3, "fe")
    v6_tail.insert(3, "ff")
    v6_tail = list(int(a + b, 16) for a, b in zip(v6_tail[::2], v6_tail[1::2]))
    v6_tail[0] ^= 0x0200
    v6_tail = ":".join(f"{a:x}" for a in v6_tail)

    assert link_local_v6.endswith(v6_tail)
    assert global_v6.endswith(v6_tail)
