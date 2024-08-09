import logging

import labgrid
from labgrid.logging import StepLogger, basicConfig

"""
Reproducer: Test if /srv is empty
=================================

This script tries to reproduce a situation where /srv is not empty after the first reboot of the TAC.
Since this does not happen on every "fist boot", we need a few tries to reproduce this issue.

The reproducer works as follows:
* Bootstrap the TAC (TF-A, Barebox, Root-FS) using the strategy.
* Halt boot of the device in Barebox before the first boot of Linux.
* Boot Linux. On first boot we will restart after repairing the GPT.
* Interrupt boot in Barebox, again - before Linux starts the 2nd time.
* Use Barebox to mount the root-fs and check if /srv is actually empty.
  (This way we are sure that no component inside our Linux can tamper
  with /srv on 2nd boot before we do the check.)

If /srv is not empty: Stop the script and leave the device in this state.
"""

basicConfig(level=logging.CONSOLE)
labgrid.util.helper.processwrapper.enable_logging()
labgrid.consoleloggingreporter.ConsoleLoggingReporter.start(".")
StepLogger.start()
logger = logging.getLogger("main")

labgrid_env = labgrid.Environment("lxatac-vanilla-eet.yaml")
target = labgrid_env.get_target()
strategy = target.get_strategy()
barebox = strategy.barebox
shell = strategy.shell

retry = 1
while True:
    logger.info(f"Boot {retry}")
    logger.info("============")

    strategy.transition("barebox")
    logger.info("Reached Barebox")

    barebox.boot("")
    barebox.await_boot()
    logger.info("Barebox detected boot into Linux")

    target.deactivate(barebox)
    logger.info("Waiting for Barebox to reappear...")
    target.activate(barebox)
    logger.info("Captured Barebox")

    stdout = barebox.run_check("mount /dev/mmc1.0")
    if "mounted /dev/mmc1.0 on /mnt/mmc1.0" not in " ".join(stdout):
        logger.error("Failed to mount mmc1.0 in Barebox!")
        exit(1)

    stdout = barebox.run_check("ls -l /mnt/mmc1.0/var")
    if len(stdout) == 0:
        logger.error("/var is empty? Something is wrong. stopping.")
        exit(1)

    stdout = barebox.run_check("ls -l /mnt/mmc1.0/srv")
    if len(stdout) > 0:
        logger.error("/srv is not empty. Nice!")
        logger.error("Found the following directories: ")
        for line in stdout:
            logger.error(f"- {line}")
        exit(0)

    logger.info("/srv is empty.")

    strategy.transition("off")
    strategy.mmc_bootstrapped = False
    retry += 1
