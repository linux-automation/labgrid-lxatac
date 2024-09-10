import json

import pytest

KILO = 1_000
MEGA = 1_000 * KILO
GIGA = 1_000 * MEGA


def filesystem_sizes(shell):
    # These tests are not RAUC tests per se, but we want to run them for both
    # slots and jamming them in between the RAUC tests using e.g., dependencies
    # did not work to well / was even messier than just placing them here.

    # $ df -B1
    # Filesystem      1B-blocks      Used Available Use% Mounted on
    # /dev/root      1052303360 832401408 145055744  86% /
    # ...
    df = shell.run_check("df -B1")

    # [{"Filesystem": "/dev/root", "1B-blocks": ...}, {"Filesystem": ...
    df = list(dict(zip(df[0].split(), line.split())) for line in df[1:])

    # {'/': {'Filesystem': '/dev/root', ...
    df = dict((e["Mounted"], e) for e in df)

    # / should have some spare space available
    assert int(df["/"]["1B-blocks"]) in range(1_900 * MEGA, 2_500 * MEGA)
    assert int(df["/"]["Used"]) / int(df["/"]["1B-blocks"]) < 0.6

    # /srv should be mostly empty
    assert int(df["/srv"]["1B-blocks"]) in range(8 * GIGA, 16 * GIGA)
    assert int(df["/srv"]["Used"]) / int(df["/srv"]["1B-blocks"]) < 0.1

    # /run, /tmp, /var/volatile should be mostly empty
    assert int(df["/run"]["Used"]) / int(df["/run"]["1B-blocks"]) < 0.2
    assert int(df["/tmp"]["Used"]) / int(df["/tmp"]["1B-blocks"]) < 0.2
    assert int(df["/var/volatile"]["Used"]) / int(df["/var/volatile"]["1B-blocks"]) < 0.2


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
