import pytest
import yaml


def run_stressor(shell, args):
    output = shell.run_check(f"stress-ng --yaml /tmp/stress-ng.yaml --timeout 10s --metrics {args}")
    print(output)
    data = shell.run_check("cat /tmp/stress-ng.yaml")
    data = yaml.load("\n".join(data), Loader=yaml.SafeLoader)
    return data


# run a single test
def test_stress_matrix(shell):
    data = run_stressor(shell, "--matrix 0")
    metrics = data["metrics"][0]
    assert metrics["stressor"] == "matrix"
    assert metrics["bogo-ops-per-second-usr-sys-time"] == pytest.approx(128, rel=0.1)  # ±10%


# run multiple similar tests
@pytest.mark.parametrize(
    "stressor, expected",
    (
        ("zero", pytest.approx(170496, rel=0.1)),  # ±10%
        ("yield", pytest.approx(109129, rel=0.1)),  # ±10%
        ("switch", pytest.approx(25591, rel=0.2)),  # ±20%
        ("shm", pytest.approx(61, rel=0.1)),  # ±10%
        ("remap", pytest.approx(4.8, rel=0.1)),  # ±10%
        ("qsort", pytest.approx(0.98, rel=0.1)),  # ±10%
        ("bsearch", pytest.approx(16.3, rel=0.1)),  # ±10%
        ("atomic", pytest.approx(62, rel=0.1)),  # ±10%
    ),
)
def test_stress(shell, stressor, expected):
    args = "--shm-bytes 1M" if stressor == "shm" else ""

    data = run_stressor(shell, f"--{stressor} 0 {args}")
    metrics = data["metrics"][0]

    assert metrics["stressor"] == stressor
    assert metrics["bogo-ops-per-second-usr-sys-time"] == expected
