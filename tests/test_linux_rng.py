"""Run linux random number generator checks."""


def test_dev_random(shell):
    """Test if we can read /dev/random and not get timeout"""
    shell.run_check("timeout 5 dd if=/dev/random of=/dev/null bs=1 count=16")


def test_dev_urandom(shell):
    """Test if we can read /dev/urandom"""
    shell.run_check("timeout 5 dd if=/dev/urandom of=/dev/null bs=1 count=16")


def test_dev_hwrng(shell):
    """Test if we can read /dev/hwrng"""
    shell.run_check("timeout 5 dd if=/dev/hwrng of=/dev/null bs=1 count=16")


def test_hwrng_task(shell):
    """Test that hwrng kernel task is running"""
    shell.run_check("pgrep -P 2 -x hwrng")
