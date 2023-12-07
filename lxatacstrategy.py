import enum
import json

import attr

from labgrid.factory import target_factory
from labgrid.step import step
from labgrid.strategy import Strategy, StrategyError

# Possible state transitions:
#
#            +---------------------------------------------------------+
#            v                                                         |
#            +--------+------------+----------+  +---------------------+
#            v        v            v          |  v                     |
# unknown -> off -1-> bootstrap -> barebox -> shell -> network --------+
#                                                      | |             |
#                                                      2 +-> system0 --+
#                                                      v               |
#                                                      rauc_installed -+
#                                                      |               |
#                                                      +---> system1 --+
# 1) Via bootstrap() but only once
# 2) Via rauc_install() but only once

class Status(enum.Enum):
    unknown = 0
    off = 1
    bootstrap = 2
    barebox = 3
    shell = 4
    network = 5
    system0 = 6
    rauc_installed = 7
    system1 = 8


@target_factory.reg_driver
@attr.s(eq=False)
class LXATACStrategy(Strategy):
    """
    LXATACStrategy - Strategy to bootstrap the LAG LXATAC's rootfs and switch to barebox and shell.
    """
    bindings = {
        "dfu_mode": "DigitalOutputProtocol",
        "httpprovider": "HTTPProviderDriver",
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
    rauc_installed = attr.ib(default=False)

    def __attrs_post_init__(self):
        super().__attrs_post_init__()

    @property
    def target_hostname(self):
        fqdn = self.network.address
        hostname, _ = fqdn.split(".", maxsplit=1)
        return hostname

    def bootstrap(self):
        self.transition(Status.off)

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
        self.target.deactivate(self.barebox)

        self.dfu_mode.set(False)

        self.mmc_bootstrapped = True

    def rauc_install(self):
        self.transition(Status.system0)

        self.target.activate(self.httpprovider)

        bundle = self.target.env.config.get_image_path('rauc_bundle')
        bundle_url = self.httpprovider.stage(bundle)

        self.shell.run_check(f'rauc-enable-cert devel.cert.pem')
        self.shell.run_check(f'rauc install {bundle_url}', timeout=600)

        self.target.deactivate(self.httpprovider)

        self.rauc_installed = True

    def set_bootstate(self, system0_prio, system0_attempts, system1_prio, system1_attempts):
        self.transition(Status.barebox)

        self.barebox.run_check(f'state.bootstate.system0.priority={system0_prio}')
        self.barebox.run_check(f'state.bootstate.system0.remaining_attempts={system0_attempts}')

        self.barebox.run_check(f'state.bootstate.system1.priority={system1_prio}')
        self.barebox.run_check(f'state.bootstate.system1.remaining_attempts={system1_attempts}')

        self.barebox.run_check('state -s')

    def get_booted_slot(self):
        self.transition(Status.network)

        stdout = self.shell.run_check('rauc status --output-format=json', timeout=60)
        rauc_status = json.loads(stdout[0])

        assert 'booted' in rauc_status, 'No "booted" key in rauc status json found'

        return rauc_status['booted']

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
            if self.status in [Status.shell, Status.network, Status.system0, Status.system1]:
                # Cleanly shut down the labgrid exporter to help the
                # coordinator clean up stale resources.
                self.shell.run("systemctl stop labgrid-exporter", timeout=90)

            self.target.deactivate(self.barebox)
            self.target.deactivate(self.shell)
            self.target.deactivate(self.fastboot)

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

        elif status == Status.barebox:
            self.transition(Status.bootstrap)

            # cycle power
            self.power.cycle()
            # interrupt barebox
            self.target.activate(self.barebox)
            self.barebox.run_check("global linux.bootargs.loglevel=loglevel=6")

        elif status == Status.shell:
            # No need to reboot just because we checked for network connectivity
            # or the slot we are running on.
            if self.status not in [Status.network, Status.system0, Status.system1]:
                # transition to barebox
                self.transition(Status.barebox)

                self.barebox.boot("")
                self.barebox.await_boot()

                self.target.activate(self.shell)

            self.shell.run("systemctl is-system-running --wait", timeout=90)

        elif status == Status.network:
            # No need to reboot just because we checked which slot we are running on.
            if self.status not in [Status.system0, Status.system1]:
                self.transition(Status.shell)

            self.shell.poll_until_success('ping -c1 _gateway', timeout=60.0)

        elif status == Status.system0:
            self.transition(Status.network)

            if self.get_booted_slot() != 'system0':
                self.set_bootstate(20, 1, 10, 1)
                self.transition(Status.network)

                assert self.get_booted_slot() == 'system0'

        elif status == Status.rauc_installed:
            self.transition(Status.network)

            if not self.rauc_installed:
                self.rauc_install()

        elif status == Status.system1:
            self.transition(Status.rauc_installed)

            if self.get_booted_slot() != 'system1':
                self.set_bootstate(10, 1, 20, 1)
                self.transition(Status.network)

                assert self.get_booted_slot() == 'system1'

        else:
            raise StrategyError(f"no transition found from {self.status} to {status}")

        self.status = status

    @step(args=["status"])
    def force(self, status):
        if not isinstance(status, Status):
            status = Status[status]

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
