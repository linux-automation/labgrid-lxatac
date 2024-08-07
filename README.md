Labgrid LXA TAC Test Suite
==========================

This repository contains the [lagrid](https://github.com/labgrid-project/labgrid)-based test suite for the LXA TAC.

This test suite serves two purposes:

- It is used to find regressions during development and to help us decide if a revision is fit for release.
- As an example how labgrid can be used to test an Embedded Linux device-under-test (DUT).

What's in this Repository
-------------------------

- `tests/`: Contains the actual `pytest` tests.
- `lxatacstrategy.py`: Is the labgrid strategy, that controls the state of the DUT.
- `conftest.py`: `pytest` configuration. Mostly the states of the strategy exported as `pytest` `fixtures`.
- `lxatac-vanilla.yaml`: Minimal labgrid environment to run most of the tests in this repository.
   This environment can be used as a starting point to run these tests yourself.
- `lxatac-vanilla-eet.yaml`: Extended labgrid environment that additionally uses an
   [Ethmux](https://www.linux-automation.com/en/products/ethernet-mux.html) and a custom test device to test even
   more features of the LXA TAC.
- `lxatac-ptx.yaml`: labgrid environment used to test the Pengutronix-internal flavor of `meta-lxatac`.
- `lxatac-eet.py` and `agents/lxatac-eet.py`: labgrid driver and agent for the custom test device.
- `contrib/`: Additional configuration for the custom test device.

How to run these tests
----------------------

To run these tests yourself, you will need the following:

- A functioning labgrid remote infrastructure.
- A labgrid setup providing the minimum resources needed (see below).
  This can, of course, be an LXA TAC.
- An LXA TAC as DUT.
- Artifacts from a [meta-lxatac](https://github.com/linux-automation/meta-lxatac/) build.

The minimum resources needed to control an LXA TAC DUT are:

- **Power Switch**: Used to switch the 12 V to the DUT on/off.
  Used to control the power state of the DUT.
- **Serial Port**: Connected to the *debug serial* power on the DUT.
  Used to have a shell in Bootloader and Linux.
- **DFUDevice** and **AndroidFastboot**: Connected to the USB-C (device) port of the DUT.
  Used to load the initial bootloader to RAM and to download the initial contents of the eMMC.
- **Digital Output** (PIO): Connected to the `boot1`-signal on the baseboard.
  Used to force the DUT into serial download mode on power on.
  (See [meta-lxatac README](https://github.com/linux-automation/meta-lxatac/?tab=readme-ov-file#bring-the-device-into-usb-boot-mode)
  for details.)
- **HTTPProvider**: An HTTP-Server that can be used by labgrid to serve images to the DUT.
  Used to test streaming updates using RAUC.

The labgrid environments provided here are the ones used during development and thus contain settings specific to our
lab.
However, the `lxatac-vanialla.yml` is a good starting point to configure your own environment.
Make sure to adapt the following settings to your setup:

- `RemotePlace`: Use the name of the labgrid place containing the minimum resources (without the `HTTPProvider`).
- `NetworkService`: Use the hostname of the DUT as it can be used on your exporters and test-runners.
- `RemoteHTTPProvider`: Use the settings of your own HTTP server.
- `images`: Make sure to point these paths to the actual build artifacts.

Afterwards you can `lock` the labgrid place and run the tests:

```shell
labgrid-client -c lxatac-vanilla.yaml lock
pytest -vv --lg-env=lxatac-vanialla.yaml --lg-colored-steps --lg-log tests/
```