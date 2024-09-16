import time

import pytest


@pytest.mark.lg_feature("eet")
def test_interface_usb_io(strategy, env, target, shell):
    """Test USB device by writing a small file onto the device and reading it again"""
    usb_storage = env.config.get_target_option(target.name, "usb_storage")

    # Connect USB-Stick to DUT
    strategy.eet.link("USB1_IN -> USB1_OUT")

    # Create tmp file
    shell.run_check("dd if=/dev/random of=/tmp/test_file bs=1M count=15")
    [checksum1] = shell.run_check("md5sum /tmp/test_file")

    # Write tmp file onto usb device
    shell.run_check(f"dd if=/tmp/test_file of={usb_storage} bs=1M count=15")

    # Disconnect and connect the USB stick to make sure all buffers have been flushed.
    strategy.eet.link("")
    time.sleep(1)
    strategy.eet.link("USB1_IN -> USB1_OUT")
    time.sleep(5)

    # Read tmp file from usb device
    shell.run_check(f"dd if={usb_storage} of=/tmp/test_file bs=1M count=15")

    # Compare checksums
    [checksum2] = shell.run_check("md5sum /tmp/test_file")

    assert checksum1 == checksum2, f"checksum are different: {checksum1} != {checksum2}"
