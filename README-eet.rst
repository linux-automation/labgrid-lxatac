LXA TAC External Electronic Testing Equipment
=============================================

The ``eet`` is an external signal multiplexing device - initially designed for end-of-line tests of the LXA TAC.
In these tests it is used to provide analog signals to the TAC's DUT-facing interfaces.

For this document we assume that you are using a ``lxatac-S10-R01-V01-C00``.

Modifications
-------------

* Use the I2C-to-USB control option.
* Power the eet with 12V via the ``12V-in`` barrel jack.
* ``12V-in`` soldered to ``AUX3``.
* ``5V`` (from I2C-adapter) soldered to ``AUX 1``
* External short between ``Curr+`` and ``Curr-``.
* ``Volt+`` and ``Volt-`` can be open or connected to a high impedance volt-meter.
  But be aware that this port will be used to short ``BUS1`` and ``BUS2`` in some tests.

Connections between eet and LXA TAC
-----------------------------------

* 3x USB-Host port to ``USB in``.
* At least one USB device (e.g. mass storage) connected to one of the ``USB out``.
* UART ``3.3V`` and ``GND`` from LXA TAC and ``eet`` connected.
* ``OUT0`` and ``OUT1`` connected.
* IOBus connected with a 9-Pin D-Sub cable.
* DUT Power connected.

Labgrid Setup
-------------

We are using a test-suite-local driver for the EET.
Make sure to add an ``RemoteLxatacEETResource`` to your environment configuration:

.. code-block:: none

      RemoteLxatacEETResource:
        host: lxatac-00013
        usbpath: 1-1.2:1.0

``usbpath`` can be obtained on the exporter where the ``eet`` is connected to.
Watch out for ``/sys/bus/usb/drivers/i2c-tiny-usb/{usbpath}/``.