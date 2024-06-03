import time

import pytest
import requests


def put_endpoint(fqdn, endpoint, data):
    """PUT data to given endpoint on target."""
    r = requests.put(f"http://{fqdn}/{endpoint}", data=data)
    r.raise_for_status()
    return r


def get_endpoint(fqdn, endpoint):
    """GET given endpoint on target."""
    r = requests.get(f"http://{fqdn}/{endpoint}")
    r.raise_for_status()
    return r


def get_json_endpoint(fqdn, endpoint):
    """GET JSON response from given endpoint on target."""
    return get_endpoint(fqdn, endpoint).json()


def test_tacd_http_temperature(strategy, online):
    """Test tacd temperature endpoint."""
    res = get_json_endpoint(strategy.network.address, "v1/tac/temperatures/soc")

    # TODO: we could check res["ts"] by comparing it to our local time,
    # but that seems prone to false positive errors
    assert 0 < res["value"] < 70


def test_tacd_http_adc(strategy, online):
    """Test tacd ADC endpoints."""

    CHANNELS = (
        (0.0, 5.0, "v1/dut/feedback/current"),
        (-5.0, 50.0, "v1/dut/feedback/voltage"),
        (0.0, 0.7, "v1/usb/host/total/feedback/current"),
        (0.0, 0.5, "v1/usb/host/port1/feedback/current"),
        (0.0, 0.5, "v1/usb/host/port2/feedback/current"),
        (0.0, 0.5, "v1/usb/host/port3/feedback/current"),
        (-5.0, 5.0, "v1/output/out_0/feedback/voltage"),
        (-5.0, 5.0, "v1/output/out_1/feedback/voltage"),
        (0, 0.4, "v1/iobus/feedback/current"),
        (0, 14, "v1/iobus/feedback/voltage"),
    )

    for low, high, endpoint in CHANNELS:
        res = get_json_endpoint(strategy.network.address, endpoint)

        # TODO: we could check res["ts"] again
        assert low <= res["value"] <= high


def test_tacd_http_locator(strategy, online):
    """Test tacd locator endpoint."""
    ENDPOINT = "v1/tac/display/locator"

    for state in [b"true", b"false"]:
        put_endpoint(strategy.network.address, ENDPOINT, state)
        res = get_endpoint(strategy.network.address, ENDPOINT)
        assert res.content == state


def test_tacd_http_iobus_fault(strategy, online):
    """Test tacd iobus fault endpoint."""
    get_endpoint(strategy.network.address, "v1/iobus/feedback/fault")


@pytest.mark.parametrize(
    "output",
    (
        (
            "v1/dut/powered",
            (b'"On"', b'"Off"', b'"OffFloating"'),
            (
                "v1/dut/feedback/voltage",
                "v1/dut/feedback/current",
            ),
        ),
        (
            "v1/iobus/powered",
            (b"true", b"false"),
            (
                "v1/iobus/feedback/voltage",
                "v1/iobus/feedback/current",
            ),
        ),
        ("v1/uart/rx/enabled", (b"true", b"false"), ()),
        ("v1/uart/tx/enabled", (b"true", b"false"), ()),
        ("v1/output/out_0/asserted", (b"true", b"false"), ("v1/output/out_0/feedback/voltage",)),
        ("v1/output/out_1/asserted", (b"true", b"false"), ("v1/output/out_1/feedback/voltage",)),
    ),
)
def test_tacd_http_switch_output(strategy, online, output):
    """Test tacd output switching."""

    control, states, feedback = output

    for state in states:
        put_endpoint(strategy.network.address, control, state)
        time.sleep(0.5)
        res = get_endpoint(strategy.network.address, control)
        assert res.content == state

        for fb in feedback:
            # TODO: do some validation on the feedback voltages/currents
            res = get_json_endpoint(strategy.network.address, fb)
