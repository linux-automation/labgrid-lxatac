import glob
import subprocess
import time


class SMBus:
    """Fake Python SMBus implementation using i2set as backend."""

    def __init__(self, usbpath: str):
        """
        Create an SMBus based on the usb-path of the target device.

        Arguments:
            usbpath (str): USB Path of the i2c-tiny-usb device to use. e.g. "1-1.2:1.0"
        """
        candidates = glob.glob(f"/sys/bus/usb/drivers/i2c-tiny-usb/{usbpath}/i2c-*")
        for candidate in candidates:
            self._bus = candidate.split("-")[-1]
            break
        else:
            raise FileNotFoundError("Could not find i2c-adapter with given name.")

    def write_byte_data(self, addr, reg, val):
        """Writes a register on an I2C device on this bus."""
        subprocess.check_call(["/usr/sbin/i2cset", "-y", str(self._bus), str(addr), str(reg), str(val), "b"])


def byte_n(val, n):
    return (val >> (8 * n)) & 0xFF


def symmetric_conn_dict(*conn_list):
    conn_dict = dict()

    for a, b, pin in conn_list:
        if a not in conn_dict:
            conn_dict[a] = dict()

        if b not in conn_dict:
            conn_dict[b] = dict()

        conn_dict[a][b] = pin
        conn_dict[b][a] = pin

    return conn_dict


class RelaisMatrix:
    _instance = None

    @classmethod
    def get_instance(cls, name):
        """Returns a single instance of RelaisMatrix"""
        if not cls._instance:
            cls._instance = RelaisMatrix(name)
        return cls._instance

    CONNECTIONS = symmetric_conn_dict(
        ("USB1_IN", "USB1_OUT", "D4"),
        ("USB2_IN", "USB2_OUT", "D6"),
        ("USB3_IN", "USB3_OUT", "D25"),
        ("USB1_IN", "BUS1", "D5"),
        ("USB2_IN", "BUS1", "D7"),
        ("USB3_IN", "BUS1", "D31"),
        ("OUT0", "BUS1", "D17"),
        ("OUT1", "BUS1", "D16"),
        ("UART_VCC", "BUS1", "D18"),
        ("IOBUS_VCC", "BUS1", "D29"),
        ("PWR_IN", "BUS1", "D28"),
        ("PWR_OUT", "BUS2", "D19"),
        ("BUS1", "VOLT", "D21"),
        ("BUS2", "VOLT", "D22"),
        ("BUS1", "CURR", "D23"),
        ("BUS2", "CURR", "D24"),
        ("SHUNT_10R", "CURR", "D1"),
        ("SHUNT_15R", "CURR", "D2"),
        ("SHUNT_68R", "CURR", "D3"),
        ("SHUNT_78R", "CURR", "D12"),
        ("SHUNT_130R", "CURR", "D13"),
        ("AUX1", "BUS1", "D11"),
        ("AUX1", "BUS2", "D10"),
        ("AUX2", "BUS1", "D20"),
        ("AUX3", "BUS1", "D8"),
        ("AUX4", "BUS1", "D9"),
        ("5V_0R", "5V", "!D30"),
        ("5V_1K", "5V", "D30"),
        ("5V_0R", "-5V", "!D30"),
        ("5V_1K", "-5V", "D30"),
        ("5V", "BUS1", "D14"),
        ("-5V", "BUS1", "D15"),
    )

    NON_LEAVES = {"BUS1", "BUS2", "CURR", "5V", "-5V"}

    # Make sure buses are not driven from two sources at the same time.
    MUTUALLY_EXCLUSIVE = (
        # TODO: Check which connections are mutually exclusive and add them here!
    )

    PORT_EXPANDER_ADDR = (0b0100000, 0b0100001, 0b0100010, 0b0100011, 0b0100100)

    PCA9554D_OUT_REG = 1
    PCA9554D_CFG_REG = 3

    def __init__(self, name, verbose=False):
        self.active_bitmask = 0

        self.verbose = verbose
        self.i2c = SMBus(name)

        for addr in self.PORT_EXPANDER_ADDR:
            # Configure all pins as outputs with low level
            self.i2c.write_byte_data(addr, self.PCA9554D_OUT_REG, 0)
            self.i2c.write_byte_data(addr, self.PCA9554D_CFG_REG, 0)

    def _set_bitmask(self, bm):
        changes = bm ^ self.active_bitmask

        if changes == 0:
            return

        for i, addr in enumerate(self.PORT_EXPANDER_ADDR):
            if not byte_n(changes, i):
                continue

            self.i2c.write_byte_data(addr, self.PCA9554D_OUT_REG, byte_n(bm, i))

        time.sleep(0.1)

        self.active_bitmask = bm

    def set_led(self, idx, status=True):
        # The LEDs are located after the 32bit occupied by the switches
        # in the bitmask.
        # The LEDs are active low.
        bitmask_idx = idx + 32
        status = 0 if status else 1

        final_bitmask = self.active_bitmask & ~(1 << bitmask_idx)
        final_bitmask |= status << bitmask_idx

        self._set_bitmask(final_bitmask)

    def clear_led(self, idx):
        self.set_led(idx, False)

    def set_switches(self, switches):
        # The switches are located in the first 32bit of the port expander
        # bitmask. The remaining bits are used for LEDs that should not
        # be affected by the break-then-make cycle.
        switches_off_bitmask = self.active_bitmask & (~0xFFFF_FFFF)
        final_bitmask = switches_off_bitmask

        for sw in switches:
            num = int(sw.lstrip("!D"))

            if sw.startswith("!D"):
                final_bitmask &= ~(1 << num)
            elif sw.startswith("D"):
                final_bitmask |= 1 << num
            else:
                raise ValueError(f"Unknown switch {sw}")

        # Don't need to perform a break-before-make cycle if the
        # desired final status is already configured
        if final_bitmask == self.active_bitmask:
            if self.verbose:
                print("SwitchMatrix: leaving switches as-is")
            return

        if self.verbose:
            print("SwitchMatrix: Break all connections")

        self._set_bitmask(switches_off_bitmask)

        if self.verbose:
            print("SwitchMatrix: Set connections:", ", ".join(sorted(switches)))

        self._set_bitmask(final_bitmask)

    def connect(self, spec="", ignore_exclusive=False):
        """
        Takes a connection spec like "PWR_OUT -> BUS2 -> CURR -> SHUNT_10R, USB1_IN -> USB1_OUT"
        and turns on all required switches to establish the connections.
        Does some basic sanity checks but you can still blow up the DUT with short circuits
        or by applying large AUX voltages if you want to.
        """

        paths = tuple(tuple(p.strip() for p in c.split("->")) for c in spec.split(","))

        switches = set()

        for path in paths:
            if path == ("",):
                continue

            unknown_nodes = set(path) - set(self.CONNECTIONS)
            if unknown_nodes:
                raise ValueError("Unknown path elements: " + ", ".join(sorted(unknown_nodes)))

            duplicate_nodes = set(a for a, b in zip(sorted(path)[:-1], sorted(path)[1:]) if a == b)

            if duplicate_nodes:
                raise ValueError("Duplicate path elements: " + ", ".join(sorted(duplicate_nodes)))

            if path[0] in self.NON_LEAVES:
                raise ValueError(f"First path element {path[0]} must be a leave")

            if path[-1] in self.NON_LEAVES:
                raise ValueError(f"Last path element {path[-1]} must be a leave")

            if any(p not in self.NON_LEAVES for p in path[1:-1]):
                raise ValueError(f"All in-between path elements ({' -> '.join(path[1:-1])}) must be non-leaves")

            prev_node = path[0]

            for prev_node, node in zip(path[:-1], path[1:]):
                if node not in self.CONNECTIONS[prev_node]:
                    raise ValueError(f"There is not possible connection between {prev_node} and {node}")

                sw = self.CONNECTIONS[prev_node][node]

                switches.add(sw)

        if not ignore_exclusive:
            for ex in self.MUTUALLY_EXCLUSIVE:
                isct = ex.intersection(switches)

                if len(isct) > 1:
                    raise ValueError("Outputs should not be active at the same time: " + ", ".join(isct))

        self.set_switches(switches)


def handle_init(name):
    RelaisMatrix.get_instance(name)


def handle_link(linkspec):
    RelaisMatrix.get_instance(None).connect(linkspec)


methods = {
    "init": handle_init,
    "link": handle_link,
}
