import re


def test_pstore_fs(shell):
    """
    Test if the pstore filesystem exists.
    """

    shell.run_check("test -d /sys/fs/pstore")


def test_kernel_messages(shell, check):
    """
    Test if the kernel only logs messages that we expect.

    This test will ignore some harmless messages that can happen during normal operation.
    """

    expected = {
        "cacheinfo: Unable to detect cache hierarchy for CPU 0",
        "spi_stm32 44009000.spi: failed to request tx dma channel",
        "spi_stm32 44009000.spi: failed to request rx dma channel",
        "clk: failed to reparent ethck_k to pll4_p: -22",
        "dwc2 49000000.usb-otg: supply vusb_d not found, using dummy regulator",
        "dwc2 49000000.usb-otg: supply vusb_a not found, using dummy regulator",
        "check access for rdinit=/init failed: -2, ignoring",
        "stm32-dwmac 5800a000.ethernet switch: Adding VLAN ID 0 is not supported",
    }

    allowed = {
        # The following messages can happen during other tests and are harmless
        "sd 0:0:0:0: [sda] No Caching mode page found",
        "sd 0:0:0:0: [sda] Assuming drive cache: write through",
    }

    messages = shell.run_check("dmesg -l warn -l err -l crit -l alert -l emerg -k")
    messages = set(re.sub(r"^\[\s*\d+\.\d+\] ", "", m) for m in messages)

    assert messages - allowed == expected
