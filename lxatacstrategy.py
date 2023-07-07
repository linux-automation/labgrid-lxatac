import enum

import attr

from labgrid.factory import target_factory
from labgrid.step import step
from labgrid.strategy import Strategy, StrategyError


class Status(enum.Enum):
    unknown = 0
    off = 1
    bootstrap = 2
    barebox = 3
    shell = 4


@target_factory.reg_driver
@attr.s(eq=False)
class LXATACStrategy(Strategy):
    """
    LXATACStrategy - Strategy to bootstrap the LAG LXATAC's rootfs and switch to barebox and shell.
    """
    bindings = {
        "dfu_mode": "DigitalOutputProtocol",
        "httpprovider": {"HTTPProviderDriver", None},
        "power": "PowerProtocol",
        "console": "ConsoleProtocol",
        "dfu": "DFUDriver",
        "fastboot": "AndroidFastbootDriver",
        "barebox": "BareboxDriver",
        "shell": "ShellDriver",
        "network": "NetworkService",
    }

    status = attr.ib(default=Status.unknown)
    mmc_bootstrapped = attr.ib(default=False)

    def __attrs_post_init__(self):
        super().__attrs_post_init__()

    @property
    def target_hostname(self):
        fqdn = self.network.address
        hostname, _ = fqdn.split(".", maxsplit=1)
        return hostname

    def bootstrap(self):
        self.dfu_mode.set(True)
        self.power.cycle()

        self.target.activate(self.dfu)

        # download tf-a to "FSBL"
        tfa_img = self.target.env.config.get_image_path("tfa")
        self.dfu.download(1, tfa_img)

        # download emmc-boot-image to "Partition3"
        mmc_boot_fip_img = self.target.env.config.get_image_path("mmc_boot_fip")
        self.dfu.download(3, mmc_boot_fip_img)
        self.dfu.detach(0)

        self.target.deactivate(self.dfu)

        self.target.activate(self.barebox)
        self.target.activate(self.fastboot)

        # write eMMC user partition
        mmc_img = self.target.env.config.get_image_path("mmc")
        self.fastboot.flash("mmc", mmc_img)

        # write eMMC boot partition
        mmc_boot_img = self.target.env.config.get_image_path("mmc_boot")
        self.fastboot.flash("bbu-mmc", mmc_boot_img)

        self.target.deactivate(self.fastboot)

        # mark system0 good / mark system1 bad
        self.barebox.run_check("state.bootstate.system0.remaining_attempts=3")
        self.barebox.run_check("state.bootstate.system0.priority=1")
        self.barebox.run_check("state.bootstate.system1.remaining_attempts=0")
        self.barebox.run_check("state.bootstate.system1.priority=0")
        self.barebox.run_check("state -s")

        self.target.deactivate(self.barebox)

        self.mmc_bootstrapped = True

    @step(args=["status"])
    def transition(self, status, *, step):
        if not isinstance(status, Status):
            status = Status[status]

        if status == Status.unknown:
            raise StrategyError(f"can not transition to {status}")

        elif status == self.status:
            step.skip("nothing to do")
            return

        elif status == Status.off:
            self.target.deactivate(self.barebox)
            self.target.deactivate(self.shell)
            self.target.deactivate(self.fastboot)

            if self.httpprovider:
                self.target.activate(self.httpprovider)

            self.target.activate(self.power)
            self.power.off()

            # assure the board is not jumpered for dfu mode
            self.target.activate(self.dfu_mode)
            self.dfu_mode.set(False)

            self.target.activate(self.console)

        elif status == Status.bootstrap:
            self.transition(Status.off)

            if not self.mmc_bootstrapped:
                self.bootstrap()

            self.dfu_mode.set(False)

        elif status == Status.barebox:
            self.transition(Status.bootstrap)
            # cycle power
            self.power.cycle()
            # interrupt barebox
            self.target.activate(self.barebox)
            self.barebox.run_check("global linux.bootargs.loglevel=loglevel=6")

        elif status == Status.shell:
            # transition to barebox
            self.transition(Status.barebox)
            self.barebox.boot("")
            self.barebox.await_boot()
            self.target.activate(self.shell)

            self.shell.run("systemctl is-system-running --wait", timeout=90)

        else:
            raise StrategyError(f"no transition found from {self.status} to {status}")

        self.status = status

    @step(args=["status"])
    def force(self, status):
        if not isinstance(status, Status):
            status = Status[status]

        if self.httpprovider:
            self.target.activate(self.httpprovider)

        self.target.activate(self.power)
        self.target.activate(self.console)

        if status == Status.barebox:
            self.target.activate(self.barebox)
        elif status == Status.shell:
            self.target.activate(self.shell)
        elif status == Status.bootstrap:
            pass
        else:
            raise StrategyError(f"can not force state {status}")

        self.mmc_bootstrapped = True
        self.status = status
