def test_linux_i2c_bus(shell):
    """Test if the i2c subsystem exists"""
    shell.run_check("test -d /sys/bus/i2c")


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
    shell.run_check("test -d /sys/bus/nvmem/devices/0-00501")
    shell.run_check("test -d /sys/bus/nvmem/devices/2-00502")
