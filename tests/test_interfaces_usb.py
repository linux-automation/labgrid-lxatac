def test_interface_usb_io(strategy, shell):
    """Test USB device by writing a small file onto the device and reading it again"""
    usbpath = shell.target.env.config.get_target_option(shell.target.name, "usbpath")

    if strategy.eet:
        strategy.eet.link("USB1_IN -> USB1_OUT")

    # Create tmp file
    shell.run_check("dd if=/dev/random of=/tmp/test_file bs=1M count=15")
    checksum1 = shell.run_check("md5sum /tmp/test_file")[0]

    # Get usb device file
    usb_device = shell.run_check(f"grep -rs '^DEVNAME=' /sys/bus/usb/devices/{usbpath} | cut -d= -f2 | grep sd[a-z]$")
    assert len(usb_device) > 0

    # Write tmp file onto usb device
    shell.run_check(f"dd if=/tmp/test_file of=/dev/{usb_device} bs=1M count=15")

    # Read tmp file from usb device
    shell.run_check(f"dd if=/dev/{usb_device} of=/tmp/test_file bs=1M count=15")

    # Compare checksums
    checksum2 = shell.run_check("md5sum /tmp/test_file")[0]

    assert checksum1 == checksum2, f"checksum are different: {checksum1} != {checksum2}"
