import json


def test_linux_i2c_bus_0_eeprom(shell):
    """
    Test if the config EEPROM on i2cbus-0 can be read.
    """

    # the first 4 bytes of the EEPROM will always contain the magic for the TLV data stored in there
    [magic] = shell.run_check("dd if=/sys/bus/i2c/devices/0-0050/eeprom bs=1 count=4 status=none | base64")
    assert magic == "xolcIQ=="


def test_linux_i2c_bus_1_eeprom(shell):
    """
    Test if the config EEPROM on i2cbus-1 can be read.
    """

    # the first 4 bytes of the EEPROM will always contain the magic for the TLV data stored in there
    [magic] = shell.run_check("dd if=/sys/bus/i2c/devices/1-0050/eeprom bs=1 count=4 status=none | base64")
    assert magic == "vCiN/g=="


def test_linux_i2c_bus_1_pmic(shell):
    """
    Test if a driver for the PMIC on i2cbus-1 has been loaded.
    """
    [name] = shell.run_check("cat /sys/bus/i2c/devices/1-0033/name")
    assert name == "stpmic1"


def test_linux_i2c_bus_2_usbhub(shell):
    """
    Test if a driver for the USB hub on i2cbus-2 has been loaded.
    """

    [name] = shell.run_check("cat /sys/bus/i2c/devices/2-002c/name")
    assert name == "usb2514b"


def test_linux_spi_0_adc(shell):
    """
    Test if the ADC on spi-0 works.
    """

    # The voltage on power board switch is very likely not zero.
    # So if we can ready anything else, SPI to the ADC very likely works.
    # (Also: the tacd tests using these measurements would very likely fail.)
    [digits] = shell.run_check(r"cat /sys/bus/spi/devices/spi0.0/iio\:device3/in_voltage_raw")
    assert int(digits) > 0


def test_linux_spi_1_lcd(shell):
    """
    Test if the framebuffer for the LCD on spi-1 exists.
    """

    # This is not a test of the SPI device itself, since we do not get any feedback from the display.
    # But this way, we at least know that the correct drm device has been probed.
    [name] = shell.run_check("cat /sys/bus/spi/devices/spi1.0/graphics/fb0/name")
    assert name == "panel-mipi-dbid"


def test_linux_spi_2_ethernet_switch(shell):
    """
    Test if the Ethernet switch on spi-2 works.
    """
    shell.run_check("test -d /sys/bus/spi/devices/spi2.0")

    # Statistics for the uplink interface are read from the Ethernet switch using spi0.
    # So a non-zero value will indicate that the device on the bus works.
    [rx_packets] = shell.run_check("ethtool -S uplink  | grep rx_packets")
    assert int(rx_packets.split(":")[-1]) > 0


def test_sensors(shell, record_property):
    stdout = shell.run_check("sensors -j")
    data = json.loads("".join(stdout))

    assert "cpu_thermal-virtual-0" in data
    record_property("cpu_thermal-virtual-0", data["cpu_thermal-virtual-0"]["temp1"]["temp1_input"])
    assert 10 <= data["cpu_thermal-virtual-0"]["temp1"]["temp1_input"] <= 70
