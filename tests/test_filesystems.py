import json

KILO = 1_000
MEGA = 1_000 * KILO
GIGA = 1_000 * MEGA


def test_partition_sizes(shell, check):
    stdout = shell.run_check("lsblk -b --json /dev/mmcblk1")
    json_info = json.loads("".join(stdout))

    [mmcblk1] = json_info["blockdevices"]
    part_sizes = {child["name"]: child["size"] for child in mmcblk1["children"]}

    with check:
        assert part_sizes["mmcblk1p1"] in range(2_000 * MEGA, 2_500 * MEGA)
    with check:
        assert part_sizes["mmcblk1p2"] in range(2_000 * MEGA, 2_500 * MEGA)
    with check:
        assert part_sizes["mmcblk1p3"] in range(8 * GIGA, 16 * GIGA)


def test_filesystem_sizes(shell, check):
    # / should have some spare space available
    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /")
    [fs_info] = json.loads("".join(stdout))["filesystems"]
    with check:
        assert fs_info["size"] in range(1_900 * MEGA, 2_500 * MEGA)
    with check:
        assert fs_info["used"] / fs_info["size"] < 0.6

    # /srv should be mostly empty
    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /srv")
    [fs_info] = json.loads("".join(stdout))["filesystems"]
    with check:
        assert fs_info["size"] in range(8 * GIGA, 16 * GIGA)
    with check:
        assert fs_info["used"] / fs_info["size"] < 0.1

    # /run, /tmp, /var/volatile should be mostly empty
    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /run")
    [fs_info] = json.loads("".join(stdout))["filesystems"]
    with check:
        assert fs_info["used"] / fs_info["size"] < 0.2

    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /tmp")
    [fs_info] = json.loads("".join(stdout))["filesystems"]
    with check:
        assert fs_info["used"] / fs_info["size"] < 0.2

    stdout = shell.run_check("findmnt -b --json -o SIZE,USED /var/volatile")
    [fs_info] = json.loads("".join(stdout))["filesystems"]
    with check:
        assert fs_info["used"] / fs_info["size"] < 0.2
