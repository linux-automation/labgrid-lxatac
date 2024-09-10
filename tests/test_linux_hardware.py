import json


def test_linux_i2c_bus_0_eeprom(shell):
    """
    Test if the config EEPROM on i2cbus-0 can be read.
    """

    # the first 4 bytes of the EEPROM will always contain the magic for the TLV data stored in there
    magic = shell.run_check("dd if=/sys/bus/i2c/devices/0-0050/eeprom bs=1 count=4 status=none | base64")[0]
    assert magic == "xolcIQ=="


def test_linux_i2c_bus_1_usbhub(shell):
    """
    Test if a driver for the USB hub on i2cbus-1 has been loaded.
    """

    name = shell.run_check("cat /sys/bus/i2c/devices/i2c-1/1-002c/name")[0]
    assert name == "usb2514b"


def test_linux_i2c_bus_2_eeprom(shell):
    """
    Test if the config EEPROM on i2cbus-2 can be read.
    """

    # the first 4 bytes of the EEPROM will always contain the magic for the TLV data stored in there
    magic = shell.run_check("dd if=/sys/bus/i2c/devices/2-0050/eeprom bs=1 count=4 status=none | base64")[0]
    assert magic == "vCiN/g=="


def test_linux_i2c_bus_2_pmic(shell):
    """
    Test if a driver for the PMIC on i2cbus-2 has been loaded.
    """
    name = shell.run_check("cat /sys/bus/i2c/devices/i2c-2/2-0033/name")[0]
    assert name == "stpmic1"


def test_linux_spi_bus(shell):
    """Test if the spi subsystem exists"""
    shell.run_check("test -d /sys/bus/spi")
    shell.run_check("test -d /sys/class/drm/card0-SPI-1/")


def test_linux_mmc_bus(shell):
    """Test if the mmc subsystem exists"""
    shell.run_check("test -d /sys/bus/mmc")
    shell.run_check(r"test -d /sys/bus/mmc/devices/mmc1\:0001")


def test_linux_nvmem_bus(shell):
    """Test if the nvmem subsystem exists"""
    shell.run_check("test -d /sys/bus/nvmem")
    shell.run_check("test -d /sys/bus/nvmem/devices/?-00502")
    shell.run_check("test -d /sys/bus/nvmem/devices/?-00501")


def test_sensors(shell):
    stdout = shell.run_check("sensors -j")
    data = json.loads("".join(stdout))

    assert "cpu_thermal-virtual-0" in data
    assert 10 <= data["cpu_thermal-virtual-0"]["temp1"]["temp1_input"] <= 70
