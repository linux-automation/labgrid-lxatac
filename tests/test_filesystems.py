import json

import pytest

KILO = 1_000
MEGA = 1_000 * KILO
GIGA = 1_000 * MEGA


def filesystem_sizes(shell):
    # / should have some spare space available
    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /")
    fs_info = json.loads("".join(stdout))["filesystems"][0]
    assert fs_info["size"] in range(1_900 * MEGA, 2_500 * MEGA)
    assert fs_info["used"] / fs_info["size"] < 0.6

    # /srv should be mostly empty
    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /srv")
    fs_info = json.loads("".join(stdout))["filesystems"][0]
    assert fs_info["size"] in range(8 * GIGA, 16 * GIGA)
    assert fs_info["used"] / fs_info["size"] < 0.1

    # /run, /tmp, /var/volatile should be mostly empty
    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /run")
    fs_info = json.loads("".join(stdout))["filesystems"][0]
    assert fs_info["used"] / fs_info["size"] < 0.2

    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /tmp")
    fs_info = json.loads("".join(stdout))["filesystems"][0]
    assert fs_info["used"] / fs_info["size"] < 0.2

    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /var/volatile")
    fs_info = json.loads("".join(stdout))["filesystems"][0]
    assert fs_info["used"] / fs_info["size"] < 0.2


def test_partition_sizes(shell):
    stdout = shell.run_check("lsblk -b --json /dev/mmcblk1")
    json_info = json.loads("".join(stdout))

    part_sizes = {child["name"]: child["size"] for child in json_info["blockdevices"][0]["children"]}

    assert part_sizes["mmcblk1p1"] in range(2_000 * MEGA, 2_500 * MEGA)
    assert part_sizes["mmcblk1p2"] in range(2_000 * MEGA, 2_500 * MEGA)
    assert part_sizes["mmcblk1p3"] in range(8 * GIGA, 16 * GIGA)


@pytest.mark.xfail(
    reason="There is a known bug, in which directories are created in `/srv` during the first boot. "
    "If this happens `/srv` will not be mounted with the correct partition on consecutive boots in this slot. "
    "Since we have r/w root-partition most of the system behaves as expected. "
    "But changes to /srv are lost on update. "
    "This behavior needs to be fixed - but is currently expected to fail."
)
@pytest.mark.slow
def test_system0_filesystem_sizes(system0_shell):
    filesystem_sizes(system0_shell)


@pytest.mark.slow
def test_system1_filesystem_sizes(system1_shell):
    filesystem_sizes(system1_shell)
