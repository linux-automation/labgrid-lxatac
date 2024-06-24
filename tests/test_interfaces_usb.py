def test_interface_usb_io(strategy, shell):
    """Test USB device by writing a small file onto the device and reading it again"""
    usbpath = shell.target.env.config.get_target_option(shell.target.name, "usbpath")

    if strategy.eet:
        strategy.eet.link("USB1_IN -> USB1_OUT")

    # Create tmp file
    shell.run_check("dd if=/dev/random of=/tmp/test_file bs=1M count=15")
    checksum1, _, returncode = shell.run("md5sum /tmp/test_file")
    assert returncode == 0
    assert len(checksum1) > 0

    # Get usb device file
    usb_device, _, returncode = shell.run(
        f"grep -rs '^DEVNAME=' /sys/bus/usb/devices/{usbpath} | cut -d= -f2 | grep sd[a-z]$"
    )
    assert len(usb_device) > 0
    assert returncode == 0

    # Write tmp file onto usb device
    stdout, stderr, returncode = shell.run(f"dd if=/tmp/test_file of=/dev/{usb_device} bs=1M count=15")
    assert returncode == 0
    assert len(stdout) > 0
    assert len(stderr) == 0, f"could not write onto '{usb_device}': {stderr}"

    # Read tmp file from usb device
    stdout, stderr, returncode = shell.run(f"dd if=/dev/{usb_device} of=/tmp/test_file bs=1M count=15")
    assert returncode == 0
    assert len(stdout) > 0
    assert len(stderr) == 0, f"could not read read '{usb_device}': {stderr}"

    # Compare checksums
    checksum2, _, returncode = shell.run("md5sum /tmp/test_file")
    assert returncode == 0
    assert len(checksum2) > 0
    assert checksum1 == checksum2, f"checksum are different: {checksum1} != {checksum2}"
