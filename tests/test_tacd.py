import json
import time

import pytest
import requests


def test_tacd_http_temperature(strategy, online, shell):
    """Test tacd temperature endpoint."""
    r = requests.get(f"http://{strategy.network.address}/v1/tac/temperatures/soc")
    temperature = r.json()["value"]
    assert r.status_code == 200
    assert 0 < temperature < 70

    stdout = shell.run_check("sensors -j")
    data = json.loads("".join(stdout))
    assert "cpu_thermal-virtual-0" in data

    assert abs(data["cpu_thermal-virtual-0"]["temp1"]["temp1_input"] - temperature) < 3


@pytest.mark.parametrize(
    "low, high, endpoint",
    (
        (-0.01, 5.0, "v1/dut/feedback/current"),
        (-5.0, 50.0, "v1/dut/feedback/voltage"),
        (-0.01, 0.7, "v1/usb/host/total/feedback/current"),
        (-0.001, 0.5, "v1/usb/host/port1/feedback/current"),
        (-0.01, 0.5, "v1/usb/host/port2/feedback/current"),
        (-0.001, 0.5, "v1/usb/host/port3/feedback/current"),
        (-5.0, 5.0, "v1/output/out_0/feedback/voltage"),
        (-5.0, 5.0, "v1/output/out_1/feedback/voltage"),
        (-0.01, 0.4, "v1/iobus/feedback/current"),
        (-0.01, 14, "v1/iobus/feedback/voltage"),
    ),
)
def test_tacd_http_adc(strategy, low, high, endpoint):
    """Test tacd ADC endpoints."""
    r = requests.get(f"http://{strategy.network.address}/{endpoint}")
    assert r.status_code == 200
    assert low <= r.json()["value"] <= high


@pytest.mark.parametrize(
    "state",
    (b"true", b"false"),
)
def test_tacd_http_locator(strategy, online, state):
    """Test tacd locator endpoint."""
    endpoint = "v1/tac/display/locator"

    r = requests.put(f"http://{strategy.network.address}/{endpoint}", data=state)
    assert r.status_code == 204

    r = requests.get(f"http://{strategy.network.address}/{endpoint}")
    assert r.status_code == 200
    assert r.content == state


def test_tacd_http_iobus_fault(strategy, online):
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
def test_tacd_http_switch_output(strategy, online, control, states):
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
def test_tacd_eet_analog(strategy, online, endpoint, link, bounds, precondition):
    """Test if analog measurements work with values not equal to zero."""
    if precondition:
        r = requests.put(f"http://{strategy.network.address}/{precondition[0]}", data=precondition[1])
        assert r.status_code == 204

    strategy.eet.link(link)  # connect supply to output
    time.sleep(0.2)  # give the analog world a moment to settle

    r = requests.get(f"http://{strategy.network.address}/{endpoint}")
    assert r.status_code == 200
    assert bounds[0] <= r.json()["value"] <= bounds[1]


@pytest.mark.lg_feature("eet")
def test_tacd_uart_3v3(strategy, online):
    """
    Test if the 3.3V supply from the DUT UART power is enabled as expected.

    These 3.3V are not managed by tacd, but are statically enabled in the devicetree.
    With this test, we just make sure this is still the case.
    """
    strategy.eet.link(
        "UART_VCC -> BUS1 -> VOLT, PWR_OUT -> BUS2 -> VOLT"
    )  # Connect the 3.3V supply from the DUT UART to PWR_OUT, so we can measure it using the DUT power switch
    time.sleep(0.5)
    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/voltage")
    assert r.status_code == 200
    assert 3.0 < r.json()["value"] < 3.6


@pytest.mark.lg_feature("eet")
def test_tacd_dut_power_switchable(strategy, online):
    """
    Test if the tacd can switch the DUT power and if measurements are correct.
    """
    strategy.eet.link(
        "AUX3 -> BUS1 -> PWR_IN, PWR_OUT -> BUS2 -> CURR -> SHUNT_15R"
    )  # Connect PWRin to 12V. Load PWRout with 15R
    r = requests.put(f"http://{strategy.network.address}/v1/dut/powered", data=b'"On"')  # activate DUT power switch
    assert r.status_code == 204
    time.sleep(0.1)  # Give measurements a moment to settle

    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/current")  # measure DUT current
    assert r.status_code == 200
    assert 0.70 < r.json()["value"] < 0.85

    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/voltage")  # measure DUT voltage
    assert r.status_code == 200
    assert 11 < r.json()["value"] < 13

    r = requests.put(f"http://{strategy.network.address}/v1/dut/powered", data=b'"Off"')  # deactivate DUT power switch
    assert r.status_code == 204
    time.sleep(0.2)  # Give measurements a moment to settle

    r = requests.get(
        f"http://{strategy.network.address}/v1/dut/feedback/current"
    )  # DUT current should be zero immediately
    assert r.status_code == 200
    assert -0.05 < r.json()["value"] < 0.05

    time.sleep(0.2)  # DUT voltage may take a few moments to get close to zero
    r = requests.get(f"http://{strategy.network.address}/v1/dut/feedback/voltage")
    assert r.status_code == 200
    assert -0.5 < r.json()["value"] < 0.5


@pytest.mark.lg_feature("eet")
def test_tacd_iobus_power_switchable(strategy, online):
    """
    Test if the tacd can switch the IOBus power and if measurements are correct.
    """
    strategy.eet.link("IOBUS_VCC -> BUS1 -> CURR -> SHUNT_68R")  # Load IOBUs VCC with 68R
    r = requests.put(
        f"http://{strategy.network.address}/v1/iobus/powered", data=b"true"
    )  # activate IOBus power supply
    assert r.status_code == 204
    time.sleep(0.5)  # Give measurements a moment to settle

    r = requests.get(f"http://{strategy.network.address}/v1/iobus/feedback/current")  # measure IOBUs current
    assert r.status_code == 200
    assert 0.15 < r.json()["value"] < 0.18

    r = requests.get(f"http://{strategy.network.address}/v1/iobus/feedback/voltage")  # measure IOBus voltage
    assert r.status_code == 200
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
    assert -0.05 < r.json()["value"] < 0.05

    time.sleep(2)
    r = requests.get(f"http://{strategy.network.address}/v1/iobus/feedback/voltage")
    assert r.status_code == 200
    assert -0.5 < r.json()["value"] < 0.5


# TODO: Add a test that checks if "OffFloating" works with the power switch
