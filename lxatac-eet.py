import os.path

import attr
from labgrid import step, target_factory
from labgrid.driver import Driver
from labgrid.resource.common import NetworkResource, Resource
from labgrid.util.agentwrapper import AgentWrapper


@target_factory.reg_resource
@attr.s(eq=False)
class LxatacEETResource(Resource):
    """This resource describes a LXA-TAC external electrical testing device connected via USB/I2C.

    Args:
        usbpath (str): Name of the i2c-tiny-usb device as found in /sys/class/i2c-adapter/i2c-*/name"""

    usbpath = attr.ib(validator=attr.validators.instance_of(str))


@target_factory.reg_resource
@attr.s(eq=False)
class RemoteLxatacEETResource(NetworkResource):
    """This resource describes a LXA-TAC external electrical testing device connected via USB/I2C.

    Args:
        host (str): hostname of the exporter
        usbpath (str): Name of the i2c-tiny-usb device as found in /sys/class/i2c-adapter/i2c-*/name"""

    host = attr.ib(validator=attr.validators.instance_of(str))
    usbpath = attr.ib(validator=attr.validators.instance_of(str))


@target_factory.reg_driver
@attr.s(eq=False)
class LxatacEETDriver(Driver):
    bindings = {
        "eet": {"LxatacEETResource", "RemoteLxatacEETResource"},
    }

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        self.wrapper = None

    def on_activate(self):
        host = self.eet.host if isinstance(self.eet, RemoteLxatacEETResource) else None
        self.wrapper = AgentWrapper(host)
        self.proxy = self.wrapper.load(
            "lxatac-eet", path=os.path.join(os.path.dirname(os.path.realpath(__file__)), "agents")
        )
        self.proxy.init(self.eet.usbpath)

    def on_deactivate(self):
        self.proxy.link("")
        self.wrapper.close()
        self.wrapper = None
        self.proxy = None

    @Driver.check_active
    @step(args=["linkspec"])
    def link(self, linkspec):
        self.proxy.link(linkspec)
