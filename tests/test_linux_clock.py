from datetime import datetime
from time import monotonic

import pytest


def test_clock_system(shell):
    """
    This test checks the system clock frequency by running `date` with `sleep`
    and measures the elapsed time against the host time.
    """

    def run_cmd(sleep):
        host_start_time = monotonic()

        date_fmt = "'%Y-%m-%d %H:%M:%S.%N'"
        stdout = shell.run_check(
            f"date -u +{date_fmt}; sleep {sleep}; date -u +{date_fmt}", timeout=float(sleep) + 5.0
        )

        # `date` on the DUT supports %N (nanoseconds), `datetime` can only parse %f (microseconds).
        # `date` adds zero-padding to all fields, so we can simply drop the last three digits of %N.
        date0 = datetime.strptime(stdout[0][:-3], "%Y-%m-%d %H:%M:%S.%f")
        date1 = datetime.strptime(stdout[1][:-3], "%Y-%m-%d %H:%M:%S.%f")

        assert date0 <= date1

        return (monotonic() - host_start_time), (date1 - date0).total_seconds()

    # get connection offset
    connection_offset, _ = run_cmd(0)

    # run test
    ref_offset, meas_offset = run_cmd(30)

    assert meas_offset / (ref_offset - connection_offset) == pytest.approx(1.0, abs=1e-2)
