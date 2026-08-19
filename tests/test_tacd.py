import contextlib
import json
import time
from collections.abc import Callable, Generator
from typing import Any

import labgrid.driver
import paho.mqtt.client as mqtt
import pytest
import requests
from labgrid.util import Timeout


def test_tacd_http_temperature(strategy, shell):
    """Test tacd temperature endpoint."""
    r = requests.get(f"http://{strategy.network.address}/v1/tac/temperatures/soc")
    temperature = r.json()["value"]
    assert r.status_code == 200
    assert 0 < temperature < 70

    stdout = shell.run_check("sensors -j")
    data = json.loads("".join(stdout))

    # We have seen two variants of the name. Make sure both work.
    if "cpu_thermal-virtual-0" in data:
        data["cpu_thermal_0-virtual-0"] = data["cpu_thermal-virtual-0"]

    assert "cpu_thermal_0-virtual-0" in data

    assert data["cpu_thermal_0-virtual-0"]["temp1"]["temp1_input"] == pytest.approx(temperature, abs=3)


@pytest.mark.parametrize(
    "low, high, endpoint",
    (
        (-0.01, 5.0, "v1/dut/feedback/current"),
        (-5.0, 50.0, "v1/dut/feedback/voltage"),
        (-0.01, 0.7, "v1/usb/host/total/feedback/current"),
        (-0.01, 0.5, "v1/usb/host/port1/feedback/current"),
        (-0.01, 0.5, "v1/usb/host/port2/feedback/current"),
        (-0.01, 0.5, "v1/usb/host/port3/feedback/current"),
        (-5.0, 5.0, "v1/output/out_0/feedback/voltage"),
        (-5.0, 5.0, "v1/output/out_1/feedback/voltage"),
        (-0.01, 0.4, "v1/iobus/feedback/current"),
        (-0.01, 14, "v1/iobus/feedback/voltage"),
    ),
)
def test_tacd_http_adc(strategy, shell, low, high, endpoint):
    """Test tacd ADC endpoints."""
    r = requests.get(f"http://{strategy.network.address}/{endpoint}")
    assert r.status_code == 200
    assert low <= r.json()["value"] <= high


@pytest.mark.parametrize(
    "state",
    (b"true", b"false"),
)
def test_tacd_http_locator(strategy, shell, state):
    """Test tacd locator endpoint."""
    endpoint = "v1/tac/display/locator"

    r = requests.put(f"http://{strategy.network.address}/{endpoint}", data=state)
    assert r.status_code == 204

    r = requests.get(f"http://{strategy.network.address}/{endpoint}")
    assert r.status_code == 200
    assert r.content == state


def test_tacd_http_iobus_fault(strategy, shell):
    """Test tacd iobus fault endpoint."""
    r = requests.get(f"http://{strategy.network.address}/v1/iobus/feedback/fault")
    assert r.status_code == 200
    assert r.text in ("true", "false")


@pytest.mark.parametrize(
    "control, states",
    (
        ("v1/dut/powered", (b'"On"', b'"Off"', b'"OffFloating"')),
        ("v1/iobus/powered", (b"true", b"false")),
        ("v1/uart/rx/enabled", (b"true", b"false")),
        ("v1/uart/tx/enabled", (b"true", b"false")),
        ("v1/output/out_0/asserted", (b"true", b"false")),
        ("v1/output/out_1/asserted", (b"true", b"false")),
    ),
)
def test_tacd_http_switch_output(strategy, shell, control, states):
    """Test tacd output switching."""
    for state in states:
        r = requests.put(f"http://{strategy.network.address}/{control}", data=state)
        assert r.status_code == 204

        time.sleep(0.5)

        r = requests.get(f"http://{strategy.network.address}/{control}")
        assert r.status_code == 200
        assert r.content == state


@pytest.mark.lg_feature("eet")
@pytest.mark.parametrize(
    "endpoint, link, bounds, precondition",
    (
        (
            "v1/output/out_0/feedback/voltage",
            "5V_1K -> -5V -> BUS1 -> OUT0",
            (-5.5, -4.0),
            ("v1/output/out_0/asserted", b"false"),
        ),
        (
            "v1/output/out_0/feedback/voltage",
            "5V_1K -> 5V -> BUS1 -> OUT0",
            (4.0, 5.5),
            ("v1/output/out_0/asserted", b"false"),
        ),
        (
            "v1/output/out_1/feedback/voltage",
            "5V_1K -> -5V -> BUS1 -> OUT1",
            (-5.5, -4.0),
            ("v1/output/out_1/asserted", b"false"),
        ),
        (
            "v1/output/out_1/feedback/voltage",
            "5V_1K -> 5V -> BUS1 -> OUT1",
            (4.0, 5.5),
            ("v1/output/out_1/asserted", b"false"),
        ),
        (
            "v1/output/out_0/feedback/voltage",
            "AUX1 -> BUS1 -> OUT0",
            (3.0, 3.6),
            ("v1/output/out_0/asserted", b"false"),
        ),
        (
            "v1/output/out_1/feedback/voltage",
            "AUX1 -> BUS1 -> OUT1",
            (3.0, 3.6),
            ("v1/output/out_1/asserted", b"false"),
        ),
        (
            "v1/usb/host/port1/feedback/current",
            "USB1_IN -> BUS1 -> CURR -> SHUNT_78R",
            (0.045, 0.065),
            None,
        ),
        (
            "v1/usb/host/port1/feedback/current",
            "USB1_IN -> BUS1 -> CURR -> SHUNT_15R",
            (0.29, 0.33),
            None,
        ),
        (
            "v1/usb/host/port1/feedback/current",
            "USB1_IN -> BUS1 -> CURR -> SHUNT_10R, USB1_IN -> BUS1 -> CURR -> SHUNT_15R",
            (0.46, 0.5),
            None,
        ),
        (
            "v1/usb/host/port2/feedback/current",
            "USB2_IN -> BUS1 -> CURR -> SHUNT_78R",
            (0.045, 0.065),
            None,
        ),
        (
            "v1/usb/host/port2/feedback/current",
            "USB2_IN -> BUS1 -> CURR -> SHUNT_15R",
            (0.29, 0.33),
            None,
        ),
        (
            "v1/usb/host/port2/feedback/current",
            "USB2_IN -> BUS1 -> CURR -> SHUNT_10R, USB2_IN -> BUS1 -> CURR -> SHUNT_15R",
            (0.46, 0.5),
            None,
        ),
        (
            "v1/usb/host/port3/feedback/current",
            "USB3_IN -> BUS1 -> CURR -> SHUNT_78R",
            (0.045, 0.065),
            None,
        ),
        (
            "v1/usb/host/port3/feedback/current",
            "USB3_IN -> BUS1 -> CURR -> SHUNT_15R",
            (0.29, 0.33),
            None,
        ),
        (
            "v1/usb/host/port3/feedback/current",
            "USB3_IN -> BUS1 -> CURR -> SHUNT_10R, USB3_IN -> BUS1 -> CURR -> SHUNT_15R",
            (0.46, 0.5),
            None,
        ),
        (
            "v1/dut/feedback/voltage",
            "AUX3 -> BUS1 -> PWR_IN",
            (11.5, 12.5),
            ("v1/dut/powered", b'"On"'),
        ),
        (
            "v1/dut/feedback/current",
            "AUX3 -> BUS1 -> PWR_IN",
            (-0.05, 0.05),
            ("v1/dut/powered", b'"On"'),
        ),
        (
            "v1/dut/feedback/current",
            "AUX3 -> BUS1 -> PWR_IN, PWR_OUT -> BUS2 -> CURR -> SHUNT_78R",
            (0.14, 0.16),
            ("v1/dut/powered", b'"On"'),
        ),
        (
            "v1/dut/feedback/current",
            "AUX3 -> BUS1 -> PWR_IN, PWR_OUT -> BUS2 -> CURR -> SHUNT_15R",
            (0.70, 0.85),
            ("v1/dut/powered", b'"On"'),
        ),
        (
            "v1/dut/feedback/current",
            "AUX3 -> BUS1 -> PWR_IN, PWR_OUT -> BUS2 -> CURR -> SHUNT_10R",
            (1.1, 1.2),
            ("v1/dut/powered", b'"On"'),
        ),
    ),
)
def test_tacd_eet_analog(strategy, shell, eet, record_property, endpoint, link, bounds, precondition):
    """Test if analog measurements work with values not equal to zero."""
    if precondition:
        r = requests.put(f"http://{strategy.network.address}/{precondition[0]}", data=precondition[1])
        assert r.status_code == 204

    eet.link(link)  # connect supply to output
    time.sleep(0.5)  # give the analog world a moment to settle

    r = requests.get(f"http://{strategy.network.address}/{endpoint}")
    assert r.status_code == 200
    record_property(f"{endpoint} @ {link}", r.json()["value"])
    assert bounds[0] <= r.json()["value"] <= bounds[1]


@pytest.mark.lg_feature("eet")
def test_tacd_uart_3v3(strategy, shell, eet, record_property):
    """
    Test if the 3.3V supply from the DUT UART power is enabled as expected.

    These 3.3V are not managed by tacd, but are statically enabled in the devicetree.
    With this test, we just make sure this is still the case.
    """
    eet.link(
        "UART_VCC -> BUS1 -> VOLT, PWR_OUT -> BUS2 -> VOLT"
    )  # Connect the 3.3V supply from the DUT UART to PWR_OUT, so we can measure it using the DUT power switch
    time.sleep(0.5)
    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/voltage")
    assert r.status_code == 200
    record_property("3V3-Supply", r.json()["value"])
    assert 3.0 < r.json()["value"] < 3.6


@pytest.mark.lg_feature("eet")
def test_tacd_dut_power_switchable(strategy, shell, eet, record_property, check):
    """
    Test if the tacd can switch the DUT power and if measurements are correct.
    """
    eet.link(
        "AUX3 -> BUS1 -> PWR_IN, PWR_OUT -> BUS2 -> CURR -> SHUNT_15R"
    )  # Connect PWRin to 12V. Load PWRout with 15R
    r = requests.put(f"http://{strategy.network.address}/v1/dut/powered", data=b'"On"')  # activate DUT power switch
    assert r.status_code == 204
    time.sleep(0.5)  # Give measurements a moment to settle

    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/current")  # measure DUT current
    assert r.status_code == 200
    record_property("On -> Current", r.json()["value"])
    with check:
        assert 0.70 < r.json()["value"] < 0.85

    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/voltage")  # measure DUT voltage
    assert r.status_code == 200
    record_property("On -> Voltage", r.json()["value"])
    with check:
        assert 11 < r.json()["value"] < 13

    r = requests.put(f"http://{strategy.network.address}/v1/dut/powered", data=b'"Off"')  # deactivate DUT power switch
    assert r.status_code == 204
    time.sleep(0.2)  # Give measurements a moment to settle

    r = requests.get(
        f"http://{strategy.network.address}/v1/dut/feedback/current"
    )  # DUT current should be zero immediately
    assert r.status_code == 200
    record_property("Off -> Current", r.json()["value"])
    with check:
        assert -0.05 < r.json()["value"] < 0.05

    time.sleep(0.2)  # DUT voltage may take a few moments to get close to zero
    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/voltage")
    assert r.status_code == 200
    record_property("Off -> Voltage", r.json()["value"])
    assert -0.5 < r.json()["value"] < 0.5


@pytest.mark.lg_feature("eet")
def test_tacd_dut_power_off_floating(strategy, shell, eet, record_property, check):
    """
    Test if the tacd handles Off and OffFloating correctly.

    This is done by connecting a 5V source with a 1k internal resistance to the output of the power switch.
    During `OffFloting` the voltage must be higher as in `Off` since the additional load must be missing.

    The 5V are provided from the VBus of the test-systems USB and are known to be unstable.
    """

    # Switch power switch to off. The output is loaded with 10k
    r = requests.put(f"http://{strategy.network.address}/v1/dut/powered", data=b'"Off"')
    assert r.status_code == 204

    # Connect 5V via 1K Ohm to PWR_OUT
    eet.link("5V_1K -> 5V -> BUS1 -> VOLT, PWR_OUT -> BUS2 -> VOLT")
    time.sleep(0.5)  # Give measurements a moment to settle

    # measure DUT voltage
    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/voltage")
    assert r.status_code == 200
    off_voltage = r.json()["value"]
    record_property("Off -> Voltage", off_voltage)

    # USB supply voltage can be all over the place
    assert 3 < off_voltage < 5.5, "Off-voltage is not inside USB-Supply range"

    # Switch power switch to off without the load.
    r = requests.put(f"http://{strategy.network.address}/v1/dut/powered", data=b'"OffFloating"')
    assert r.status_code == 204
    time.sleep(0.5)  # Give measurements a moment to settle

    # measure DUT voltage
    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/voltage")
    assert r.status_code == 200
    floating_voltage = r.json()["value"]
    record_property("Floating -> Voltage", floating_voltage)

    # USB supply voltage can be all over the place
    with check:
        assert 3 < floating_voltage < 5.5, "OffFloating-voltage is not inside USB-supply range"

    # Make sure both measurements have the right relation
    with check:
        assert floating_voltage > off_voltage, "OffFloating-voltage is not higher than Off-voltage"

    # Voltage relation is given by the voltage divider of 1k and 10k
    assert off_voltage / floating_voltage == pytest.approx(10e3 / (10e3 + 1e3), rel=0.15)


@pytest.mark.lg_feature("eet")
def test_tacd_iobus_power_switchable(strategy, shell, eet, record_property, check):
    """
    Test if the tacd can switch the IOBus power and if measurements are correct.
    """
    eet.link("IOBUS_VCC -> BUS1 -> CURR -> SHUNT_68R")  # Load IOBUs VCC with 68R
    r = requests.put(
        f"http://{strategy.network.address}/v1/iobus/powered", data=b"true"
    )  # activate IOBus power supply
    assert r.status_code == 204
    time.sleep(0.5)  # Give measurements a moment to settle

    r = requests.get(f"http://{strategy.network.address}/v1/iobus/feedback/current")  # measure IOBUs current
    assert r.status_code == 200
    record_property("On -> Current", r.json()["value"])
    with check:
        assert 0.15 < r.json()["value"] < 0.18

    r = requests.get(f"http://{strategy.network.address}/v1/iobus/feedback/voltage")  # measure IOBus voltage
    assert r.status_code == 200
    record_property("On -> Voltage", r.json()["value"])
    with check:
        assert 10 < r.json()["value"] < 13

    r = requests.put(
        f"http://{strategy.network.address}/v1/iobus/powered", data=b"false"
    )  # deactivate IObus power supply
    assert r.status_code == 204
    time.sleep(0.5)  # Give measurements a moment to settle

    r = requests.get(
        f"http://{strategy.network.address}/v1/iobus/feedback/current"
    )  # IOBus current should be zero immediately
    assert r.status_code == 200
    record_property("Off -> Current", r.json()["value"])
    with check:
        assert -0.05 < r.json()["value"] < 0.05

    time.sleep(2)
    r = requests.get(f"http://{strategy.network.address}/v1/iobus/feedback/voltage")
    assert r.status_code == 200
    record_property("Off -> Voltage", r.json()["value"])
    assert -0.5 < r.json()["value"] < 0.5


@pytest.fixture(scope="function")
def tacd_configured(strategy, shell: labgrid.driver.ShellDriver):
    """
    Make sure the tacd is in a configured mode and restore the previous state after the test has run.
    """

    r = requests.get(f"http://{strategy.network.address}/v1/tac/setup_mode")
    assert r.status_code == 200

    if r.text == "false":
        # We are already set up. Nothing to do.
        yield
        return

    # Create backup of the state file. This may fail if no state file was written yet.
    # The tacd only writes the state file when a persistent topic is actively changed.
    # So if everything is still at the defaults, there will be no file.
    # Silently ignore the error in this case.
    shell.run("cp /srv/tacd/state.json /srv/tacd/state.json.bkp")

    # Leave setup mode (this is possible via the API, while the inverse is not)
    r = requests.put(f"http://{strategy.network.address}/v1/tac/setup_mode", data=b"false")
    assert r.status_code == 204

    yield

    # Delete the state file and replace it with the backed up one (if one was created above).
    shell.run_check("systemctl stop tacd")
    shell.run_check("rm /srv/tacd/state.json")
    shell.run("mv /srv/tacd/state.json.bkp /srv/tacd/state.json")
    shell.run_check("systemctl start tacd")


def test_tacd_ssh_pubkeys_not_writeable_http(shell, strategy, tacd_configured):
    """
    Make sure we can not get or set the authorized_keys using the HTTP API in the tacd.

    @relation(CYSEC-4, scope=function)
    """
    # Make sure setup mode is disabled
    r = requests.get(f"http://{strategy.network.address}/v1/tac/setup_mode")
    assert r.status_code == 200
    assert r.text == "false"

    # We should not be able to retrieve SSH keys outside of setup mode
    r = requests.get(f"http://{strategy.network.address}/v1/tac/ssh/authorized_keys")
    assert r.status_code == 403
    assert r.text == "This file may only be read in setup mode"

    magic_string = "NO_SSH_KEY"
    # Make sure the authorized_keys isn't accidentally already set to our magic string
    with contextlib.suppress(labgrid.driver.shelldriver.ExecutionError):
        assert shell.get_bytes("/root/.ssh/authorized_keys").decode() != magic_string

    # We should not be able to PUT SSH keys outside of setup mode
    r = requests.put(f"http://{strategy.network.address}/v1/tac/ssh/authorized_keys", data=magic_string)
    assert r.status_code == 403
    assert r.text == "This file may only be written in setup mode"

    # Make sure the authorized_keys has not been written even if the HTTP status message tells otherwise
    with contextlib.suppress(labgrid.driver.shelldriver.ExecutionError):
        assert shell.get_bytes("/root/.ssh/authorized_keys").decode() != magic_string


@pytest.fixture(scope="function")
def ws_mqtt(strategy) -> Generator[tuple[mqtt.Client, dict[Any, Any], Callable[..., str]], Any, None]:
    """
    Sets up a threaded paho-mqtt client that is connected to the websocket-mqtt endpoint of the tacd.

    Since paho-mqtt is event-driven by design and this does not go very well with linear tests this fixture also
    provides a wrapper around  paho-mqtt that allows a test to retrieve the last value of each topic.
    """
    last_values = dict()

    def _on_message(client, userdata, msg):
        last_values[msg.topic] = msg.payload.decode()

    def get_value(topic: str) -> str:
        t = Timeout(timeout=1.0)
        while not t.expired:
            if topic in last_values:
                return last_values.pop(topic)
            time.sleep(0.1)
        else:
            raise TimeoutError("Topic not found until timeout")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
    client.on_message = _on_message
    client.ws_set_options(path="/v1/mqtt")
    client.connect(f"{strategy.network.address}", 80)
    client.loop_start()
    connect_timeout = Timeout(timeout=5.0)
    while not connect_timeout.expired:
        if client.is_connected():
            break
        time.sleep(0.1)
    else:
        raise ConnectionError("Could not connect to tacd mqtt-ws in time!")
    yield client, last_values, get_value
    client.disconnect()


def test_tacd_ssh_pubkeys_not_writeable_ws(shell, tacd_configured, ws_mqtt):
    """
    Make sure we can not set the authorized_keys using the Websocket in the tacd.

    @relation(CYSEC-4, scope=function)
    """
    client, last_values, get_value = ws_mqtt

    # Make sure setup mode is disabled
    client.subscribe("/v1/tac/setup_mode")
    assert get_value("/v1/tac/setup_mode") == "false"

    magic_string = "NO_SSH_KEY"
    # Make sure the authorized_keys isn't accidentally already set to our magic string
    with contextlib.suppress(labgrid.driver.shelldriver.ExecutionError):
        assert shell.get_bytes("/root/.ssh/authorized_keys").decode() != magic_string

    # We should not be able to PUT SSH keys outside of setup mode
    client.publish("/v1/tac/ssh/authorized_keys", magic_string, qos=0, retain=True)

    # Make sure the authorized_keys has not been written even if the HTTP status message tells otherwise
    with contextlib.suppress(labgrid.driver.shelldriver.ExecutionError):
        assert shell.get_bytes("/root/.ssh/authorized_keys").decode() != magic_string


def test_tacd_no_setup_mode_http(shell, strategy, tacd_configured):
    """
    Make sure we can not enter setup mode via the HTTP API.

    @relation(CYSEC-5, scope=function)
    """

    # Make sure setup mode is disabled
    r = requests.get(f"http://{strategy.network.address}/v1/tac/setup_mode")
    assert r.status_code == 200
    assert r.text == "false"

    # Try to activate config mode
    r = requests.put(f"http://{strategy.network.address}/v1/tac/setup_mode", data="true")
    assert r.status_code == 204

    # Make sure setup mode is still disabled
    r = requests.get(f"http://{strategy.network.address}/v1/tac/setup_mode")
    assert r.status_code == 200
    assert r.text == "false"


def test_tacd_no_setup_mode_ws(shell, strategy, tacd_configured, ws_mqtt):
    """
    Make sure we can not enter setup mode via the Websocket API.

    @relation(CYSEC-5, scope=function)
    """
    client, last_values, get_value = ws_mqtt

    # Make sure setup mode is disabled
    r = requests.get(f"http://{strategy.network.address}/v1/tac/setup_mode")
    assert r.status_code == 200
    assert r.text == "false"

    # Try to activate config mode
    client.publish("/v1/tac/setup_mode", "true", qos=0, retain=True)

    # Make sure setup mode is still disabled
    r = requests.get(f"http://{strategy.network.address}/v1/tac/setup_mode")
    assert r.status_code == 200
    assert r.text == "false"
