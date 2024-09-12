import re

import labgrid.protocol


class SystemdRun:
    """
    Wrapper around `systemd-run` to run a command in the background.
    This wrapper is intended to be used as context manager:

    > with SystemdRun(command="sleep 30", shell=shell):
    >     pass

    The output of the command is not collected.
    Neither is the exit code.

    This is a workaround until something like https://github.com/labgrid-project/labgrid/pull/835 is merged.
    """

    _re_run = re.compile(r"^Running as unit: (run-\w+\.service);")

    def __init__(self, command: str, shell: labgrid.protocol.ConsoleProtocol):
        """
        Run `command` in a transient unit using `systemd-run`.
        """
        self._command = command
        self._shell = shell
        self._unit = None

    def __enter__(self) -> None:
        stdout = self._shell.run_check(f"systemd-run {self._command}")
        match = SystemdRun._re_run.match("".join(stdout))
        if not match:
            raise ValueError(f"systemd-run returned not parseable output: {stdout}")
        self._unit = match[1]

    def __exit__(self, _type, _value, _traceback):
        self._shell.run(f"systemctl stop {self._unit}")
