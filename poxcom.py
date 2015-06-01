# poxcom.py

"""POX Serial Port stuff
- Daemon for managing TX with an external serial device
- Daemon for managing RX with an external serial device

(NOTE:  You'll need your own serial gizmo.)

This project uses an external serial device with a binary command format:

<address byte>, <size byte>, <1-8 data bytes>

The first byte is hard-coded to 2 for the device address.
The next byte is the number of bytes to follow (size of data).
The first byte in the data is a command code.
Arbitrary data may follow the command code.

The Serial TX daemon takes high-level commands from the app
and converts them to low-level binary commands for the external device.

The Serial RX daemon has a state machine to recognize incoming command
packets.  It can send high-level events back to the app based on the
commands it receives.  It also handles "heartbeat" commands from the
external device and enqueues appropriate response (bypassing the main app).
The heartbeat can let a user know if the serial link is good.

Heartbeat protocol:

If device sends 2,2,0,0 then the App must send 2,2,0,2
If device sends 2,2,0,1 then the App must send 2,2,0,3

"""

import threading
import Queue

import serial


POX_COM = "COM"


class ExtCmd(object):
    """
    Holds command data.
    """

    def __init__(self, cmd_id, data=None):
        """
        Initializes command data.
        :param cmd_id: Numeric ID for command
        :param data: Bytearray
        """
        self.cmd_id = cmd_id
        self.data = data

    def __str__(self):
        """
        Provides method for pretty-printing command data.
        :return: string
        """
        return str(self.cmd_id) + "," + str([hex(x) for x in self.data])


class RXFSM(object):
    """
    Implements byte-oriented state machine for recognizing
    serial commands with a binary format.
    """

    STATE_IDLE = 0
    STATE_ADDR = 1
    STATE_SIZE = 2
    STATE_DATA = 3

    def __init__(self):
        """
        Initializes state machine in idle state.
        """
        self.state = RXFSM.STATE_IDLE
        self.data = None
        self.cmd_id = None
        self.addr = 2  # hard-coded device address
        self.size = 0
        self.ct = 0

    def crank(self, b):
        """
        Executes one pass of state machine.
        :param b: Numeric byte (0-255)
        :return: ExtCmd object if command ready, None otherwise
        """
        result = None
        if self.state == RXFSM.STATE_IDLE:
            if b == self.addr:
                self.state = RXFSM.STATE_ADDR
            else:
                self.state = RXFSM.STATE_IDLE
        elif self.state == RXFSM.STATE_ADDR:
            if 1 <= b <= 8:
                self.size = b
                self.ct = 0
                self.state = RXFSM.STATE_SIZE
            else:
                self.state = RXFSM.STATE_IDLE
        elif self.state == RXFSM.STATE_SIZE:
            # check for valid command code (0-69, 128)
            if b <= 69 or b == 128:
                self.cmd_id = b
                self.data = None
                if self.size == 1:
                    self.state = RXFSM.STATE_IDLE
                    result = ExtCmd(self.cmd_id)
                else:
                    self.ct = 1
                    self.data = bytearray()
                    self.state = RXFSM.STATE_DATA
            else:
                self.state = RXFSM.STATE_IDLE
        elif self.state == RXFSM.STATE_DATA:
            # consume arbitrary data byte
            self.data.append(b)
            self.ct += 1
            if self.ct == self.size:
                self.state = RXFSM.STATE_IDLE
                result = ExtCmd(self.cmd_id, self.data)
        return result


class Com(object):
    """
    Implements all serial daemon operation.
    """
    def __init__(self):
        """
        Initializes all objects for serial communication.
        - RX state machine in idle state
        - Empty Queue for receiving commands
        - Serial port (not opened)
        - Blank objects for daemon threads
        - Blank reference for App queue
        """
        self.rxfsm = RXFSM()
        self.serial = serial.Serial()
        self._cmd_rx_queue = Queue.Queue()
        self._cmd_tx_queue = None
        self._rx_thread = None
        self._tx_thread = None

    def open(self, port, baudrate):
        """
        Attempts to open serial port.
        :param port: String name for a port (depends on OS)
        :param baudrate: A valid numeric baud rate: 9600, 19200, etc.
        :return: True if success, False otherwise
        """
        result = False
        try:
            self.serial.baudrate = baudrate
            self.serial.port = port
            self.serial.open()
            result = True
        except OSError:
            pass
        except serial.SerialException:
            pass
        return result

    def _start_rx(self):
        """
        Starts Serial RX daemon
        """
        self._rx_thread = threading.Thread(target=self.rx_loop)
        self._rx_thread.setDaemon(True)
        self._rx_thread.start()

    def _start_tx(self):
        """
        Starts Serial TX daemon
        """
        self._tx_thread = threading.Thread(target=self.tx_loop)
        self._tx_thread.setDaemon(True)
        self._tx_thread.start()

    def start(self, cmd_tx_queue):
        """
        Launches serial daemons if port is open.
        """
        if self.serial.isOpen():
            self._cmd_tx_queue = cmd_tx_queue
            self._start_rx()
            self._start_tx()

    def post_cmd(self, cmd, data):
        """
        Enqueues a command that will be converted
        into a serial command for the external device.
        """
        if self._tx_thread is not None:
            if self._tx_thread.is_alive():
                s = "{0} {1}".format(cmd, data)
                self._cmd_rx_queue.put(s)

    def _handle_serial_rx_cmd(self, cmd):
        """
        Converts command into appropriate action.
        - May enqueue event message for main app
        - May handle daemon-specific event (heartbeat)
        :param cmd: ExtCmd object with command data
        """
        if cmd.cmd_id == 0:
            # service the heartbeat
            # bypass the main app and post a command to self
            # that tells Serial TX daemon to ack the heartbeat
            if cmd.data[0] == 0:
                self.post_cmd("hbu", "")
            elif cmd.data[0] == 1:
                self.post_cmd("hbd", "")
        elif cmd.cmd_id == 128:
            # general message from external device
            if cmd.data[0] == 4:
                # inform app that device reset
                if self._cmd_tx_queue is not None:
                    s = "{0} {1}".format(POX_COM, "rst")
                    self._cmd_tx_queue.put(s)

    def rx_loop(self):
        """
        Implements Serial RX daemon loop.
        - Receives binary commands from serial device
        - Runs bytes through the RX state machine
        - Acts on decoded commands
        """
        while True:
            # wait for serial data (this blocks)
            x = None
            try:
                x = self.serial.read(1)
            except serial.SerialException:
                pass

            if x is not None:
                result = self.rxfsm.crank(ord(x[0]))
                if result is not None:
                    self._handle_serial_rx_cmd(result)

    def tx_loop(self):
        """
        Implements Serial TX daemon loop.
        - Receives high-level commands from main app
        - Decodes commands and spews bytes out serial port
        """
        while True:
            item = self._cmd_rx_queue.get()
            self._cmd_rx_queue.task_done()
            stokens = item.split()
            cmd = stokens[0]

            data = None
            if cmd == "hbu":
                data = b'\x02\x02\x00\x02'
            elif cmd == "hbd":
                data = b'\x02\x02\x00\x03'
            elif cmd == "rst":
                data = b'\x02\x01\x18'

            if data is not None:
                try:
                    self.serial.write(data)
                except serial.SerialException:
                    pass
