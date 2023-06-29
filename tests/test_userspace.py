import json
import re

from labgrid.driver import ExecutionError


def test_system_running(shell):
    try:
        shell.poll_until_success('systemctl is-system-running', timeout=120.0, sleepduration=10.0)
    except ExecutionError:
        # gather information about failed units
        shell.run("systemctl list-units --failed --no-legend --plain --no-pager")
        raise


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


def test_srv_mount(shell):
    mount = '\n'.join(shell.run_check("mount"))
    srv_mounted = re.compile(
        r'^/dev/mmcblk\S* on /srv type ext4', re.MULTILINE
    )

    assert srv_mounted.search(mount) is not None


def test_chrony(shell):
    """Test that chronyd is running and synchronized."""
    [chronyc] = shell.run_check("chronyc -c tracking")
    chronyc_csv = chronyc.split(",")

    # make sure stratum > 0 is used
    int(chronyc_csv[2]) > 0


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

    [ip] = shell.run_check("ip -d -j link show tac-bridge")
    [ip_json] = json.loads(ip)

    # link attributes are in expected state
    assert ip_json["linkinfo"]["info_data"]["stp_state"] == 0
    assert ip_json["linkinfo"]["info_data"]["mcast_snooping"] == 0
