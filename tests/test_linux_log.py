import re


def test_pstore_fs(shell):
    """
    Test if the pstore filesystem exists.
    """

    shell.run_check("test -d /sys/fs/pstore")


def test_kernel_messages(shell):
    """
    Test if the kernel only logs messages that we expect.

    This test will ignore some harmless messages that can happen during normal operation.
    """

    expected = {
        "clk: failed to reparent ethck_k to pll4_p: -22",
        "dwc2 49000000.usb-otg: supply vusb_d not found, using dummy regulator",
        "dwc2 49000000.usb-otg: supply vusb_a not found, using dummy regulator",
        "stm32-dwmac 5800a000.ethernet switch: Adding VLAN ID 0 is not supported",
        "stm32-dwmac 5800a000.ethernet: txpbl(2) is too low for TSO",
    }

    allowed = {
        # This message is present in the v26.07.1 stable release (kernel 7.1.6)
        # but not in the development branch (kernel 7.2.6).
        # TODO: Remove once the next stable release is published.
        "cacheinfo: Unable to detect cache hierarchy for CPU 0",
        # The following messages can happen during other tests and are harmless
        "sd 0:0:0:0: [sda] No Caching mode page found",
        "sd 0:0:0:0: [sda] Assuming drive cache: write through",
        # These messages are accepted
        "systemd[1]: systemd-journald-dev-log.socket: SO_PASSSEC failed: Operation not supported",
        "systemd[1]: systemd-journald.socket: SO_PASSSEC failed: Operation not supported",
        # These messages can happen, if USB devices get disconnected during other tests
        "usb usb1-port1: Cannot enable. Maybe the USB cable is bad?",
        "usb usb1-port1: cannot reset (err = -32)",
        "usb usb1-port2: Cannot enable. Maybe the USB cable is bad?",
        "usb usb1-port2: cannot reset (err = -32)",
        "usb usb1-port3: Cannot enable. Maybe the USB cable is bad?",
        "usb usb1-port3: cannot reset (err = -32)",
    }

    allowed_re = [
        # These messages can happen depending on the order tests and are harmless
        re.compile(
            r"^systemd-journald.+File \/var\/log\/journal.+ corrupted or uncleanly shut down, renaming and replacing.$"
        ),
    ]

    messages = shell.run_check("dmesg -l warn -l err -l crit -l alert -l emerg")
    messages = set(re.sub(r"^\[\s*\d+\.\d+\] ", "", m) for m in messages)

    messages = {m for m in messages if not any(r.match(m) for r in allowed_re)}

    assert messages - allowed == expected
