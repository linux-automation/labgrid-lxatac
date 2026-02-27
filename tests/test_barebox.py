import re


def test_barebox_messages(barebox):
    """
    Test if the kernel only logs messages that we expect.

    This test will ignore some harmless messages that can happen during normal operation.
    """

    expected = set()

    allowed = set()

    messages = barebox.run_check("dmesg -p notice")
    messages = set(re.sub(r"^\[\s*\d+\.\d+\] ", "", m) for m in messages)

    assert messages - allowed == expected
