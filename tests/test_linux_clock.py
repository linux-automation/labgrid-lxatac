from datetime import datetime
from time import monotonic

import pytest


def strptime(s):
    fmts = [
        # 'Fri Jan  1 05:12:45 UTC 2016'
        "%a %b  %d %X UTC %Y",
        # 'Thu Jan  1 05:13:44 1970  .087782 seconds'
        "%a %b  %d %X %Y  .%f seconds",
        # 'Thu Jan  1 05:13:44 1970  0.087782 seconds'
        "%a %b  %d %X %Y  0.%f seconds",
        # '1970-01-01 00:13:32+00:00'
        "%Y-%m-%d %H:%M:%S+00:00",
        # '1970-01-01 00:13:32.135780+00:00'
        "%Y-%m-%d %H:%M:%S.%f+00:00",
    ]

    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"time data '{s}' does not match known formats")


def get_date_fmt(shell):
    "Check if the installed date support %6N"
    stdout, _, rc = shell.run("date -u +%6N")
    assert rc == 0
    if "N" in stdout[0]:
        return "'%Y-%m-%d %H:%M:%S+00:00'"
    else:
        return "'%Y-%m-%d %H:%M:%S.%6N+00:00'"


def test_clock_system(shell):
    """
    This test checks the system clock frequency by running `date` with `sleep`
    and measures the elapsed time against the host time.
    """

    def run_cmd(sleep):
        host_start_time = monotonic()

        stdout, _, rc = shell.run(
            f"date -u +{date_fmt}; sleep {sleep}; date -u +{date_fmt}", timeout=float(sleep) + 5.0
        )

        assert rc == 0

        date0_str = stdout[0]
        date1_str = stdout[1]

        date0 = strptime(date0_str)
        date1 = strptime(date1_str)

        assert date0 <= date1

        return (monotonic() - host_start_time), (date1 - date0).total_seconds()

    date_fmt = get_date_fmt(shell)

    # get connection offset
    connection_offset, _ = run_cmd(0)

    # run test
    ref_offset, meas_offset = run_cmd(30)

    assert meas_offset / (ref_offset - connection_offset) == pytest.approx(1.0, abs=1e-2)
