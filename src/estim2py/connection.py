import copy
from typing import Literal

import serial  # pyright: ignore[reportMissingModuleSource]
import time
import logging

from .exceptions import Estim2pyError, Estim2pyUnsupportedError
from .modes import Estim2pyMode
from .protocol import Estim2pyBias, Estim2pyProtocol, detect_protocol, get_protocol, split_status
from .status import Estim2pyStatus

logger = logging.getLogger(__name__)

type ChannelName = str
"""Type used to refer to channel names: A B C D."""

type ChannelVal = int
"""Type used to refer to a channel value: 0-100."""

#from serial.tools import list_ports

class Estim2pyConnection():
    """
    Connect to the Estim 2b box, and manage communication

    All method calls will return an Estim2pyStatus object.

    A note about the delay.  This needs to be at least 0.034, as that is the amount of time it takes to send 33 bytes over the serial wire.
    That doesn't necessarily give any time for the 2B to act.  0.10 (the default) is extremely safe. 
    
    args:
    device - the serial device to connect with.

    keywords:
    timeout - Serial timeout, sent straight to pyserial
    delay - enforced delay.  This gives the 2b enough time to act, and then respond. 
    do_flush - whether or not to flush input on status retrieval.   This is probably witchcraft and can be left as false.
    protocol - "auto" (default) asks the box for its status and picks the protocol from the reply.
    A protocol name ("2.106", "2.119B", "2.120B") or an Estim2pyProtocol skips the probe.

    The protocol in use is available as connection.protocol.
    """

    BAUD: int = 9600
    BYTESIZE: int = serial.EIGHTBITS
    PARITY: str = serial.PARITY_NONE
    STOPBITS: int = serial.STOPBITS_ONE

    MODE_MAX: int = 100

    TERMINATION_CHAR: Literal[b"\n"] = b"\n" 
    
    def __init__(self, device: str, timeout:float=2, delay:float=0.04, do_flush:bool=False,
                 protocol: str | Estim2pyProtocol = "auto") -> None:
        self.delay: float = delay
        self.do_flush: bool = do_flush
        self.serial: serial.Serial = serial.Serial(
            device,
            self.BAUD,
            timeout  = timeout,
            bytesize = self.BYTESIZE,
            parity   = self.PARITY,
            stopbits = self.STOPBITS)

        if isinstance(protocol, Estim2pyProtocol):
            self.protocol: Estim2pyProtocol = protocol
        elif protocol == "auto":
            self.protocol = self.__detect()
        else:
            self.protocol = get_protocol(protocol)
        logger.info(f"Using protocol {self.protocol.name}")

    def __del__(self):
        # I don't think there would be any more pending output, but lets be sure of that.
        if hasattr(self, 'serial') and hasattr(self.serial, "flush"):
            self.serial.flush()
            self.serial.close()
        
    def get_status(self):
        """Returns a Estim2pyStatus object"""

        # Through experimentation, it looks like the flush isn't needed.
        # Certainly not on a get_status call.
        # That handling needs to go into the lower level __send/__receive
        return self.__send("")

    def set_to_status(self, to_status: Estim2pyStatus) -> bool:
        """Change all settings to the input status. Returns a success boolean.

        The status may come from a box with different firmware: the mode is then set by name, and the
        bias by setting.  Settings this firmware does not have are skipped.

        On 2.106 firmware this will cowardly leave link alone and expect it off,
        until I figure out what is wrong with channel link there.
        
        args:
        to_status (Estim2pyStatus): target status.

        returns:
        True if all parameters were set, false if there was a mismatch.

        raises:
        ValueError if the status is in a mode this firmware does not have (e.g. flo on 2.106).
        """
        expected = copy.copy(to_status)
        expected.protocol = self.protocol.name

        if to_status.is_high_power():
            _ = self.high()
        elif to_status.is_dynamic_power():
            _ = self.dynamic()
        else:
            _ = self.low()

        if self.protocol.name == "2.106":
            logger.debug("Cowardly expecting linked to be 0 because of link bug.")
            expected.linked = 0
        elif to_status.is_linked():
            _ = self.link()
        else:
            _ = self.unlink()

        if Estim2pyMode.table(to_status.protocol) is Estim2pyMode.table(self.protocol.name):
            _ = self.set_mode(to_status.mode)
        else:
            name = Estim2pyMode.get_mode(to_status.mode, to_status.protocol).name
            logger.debug(f"Mode {to_status.mode} of firmware {to_status.protocol} is {name!r} here.")
            expected.mode = self.set_mode_by_name(name).mode

        bias = to_status.get_bias()
        if bias is not None and self.protocol.supports("bias"):
            expected.bias = self.set_bias(bias).bias
        if to_status.output_map is not None and self.protocol.supports("output_map"):
            _ = self.set_output_map(to_status.output_map)
        if to_status.warp is not None and self.protocol.supports("warp"):
            _ = self.set_warp(to_status.warp)
        if to_status.ramp is not None and self.protocol.supports("ramp"):
            _ = self.set_ramp(to_status.ramp)

        _ = self.set_channel('a', to_status.get_channel('a'))
        _ = self.set_channel('b', to_status.get_channel('b'))
        _ = self.set_channel('c', to_status.get_channel('c'))
        _ = self.set_channel('d', to_status.get_channel('d'))

        current_status = self.get_status()
        result = current_status == expected

        if not result:
            logger.warning(f"Estim2pyConnection.set_to_status() failed.\nCurrent: {current_status=}\nTarget : {expected}")
        
        return result
        
    def set_channel(self, channel: ChannelName, val: ChannelVal):
        """Set's the channel to value val.

        Will throw a ValueError if:
        The channel is not a,b,c or d (upper or lowercase)
        The val is notan integer between 0-100 for A and B, 2-100 for C, or 1-100 for D

        args:
        channel (str): A or B for power channels, C for Speed, D for Feeling. (generally)
        val (int): 1-100 for A or B, 2-100 for C, 1-100 for D
        
        returns:
        Estim2pyStatus
        """
        channel = channel.upper()
        if channel not in ['A', 'B', 'C', 'D']: raise ValueError(f"channel argument must be A, B, C, D. was {channel!r}")
        if channel in ['A','B'] and (val > 100 or val < 0): raise ValueError(f"channel value out of range [0-100] was {val}")

        # More experimentation needed prolly
        if channel == 'C' and (val > 100 or val < 2): raise ValueError(f"channel value out of range [2-100] was {val}")
        if channel == 'D' and (val > 100 or val < 1): raise ValueError(f"channel value out of range [1-100] was {val}")

        return self.__send(channel+str(val))

    def set_a(self, val: ChannelVal) -> Estim2pyStatus:
        """ Set channel A to val"""
        return self.set_channel("A", val)
    
    def set_b(self, val: ChannelVal) -> Estim2pyStatus:
        """ Set channel B to val"""
        return self.set_channel("B", val)
      
    def set_c(self, val: ChannelVal) -> Estim2pyStatus:
        """ Set channel C to val"""
        return self.set_channel("C", val)
    
    def set_d(self, val: ChannelVal) -> Estim2pyStatus:
        """ Set channel D to val"""
        return self.set_channel("D", val)
    
    def reset(self):
        """Resets the box and returns Estim2pyStatus"""
        return self.__send("E")

    def low(self):
        """Sets the box to low power mode and returns Estim2pyStatus"""
        return self.__send("L")

    def high(self):
        """Sets the box to high power mode and returns Estim2pyStatus"""
        return self.__send("H")

    def link(self):
        """Links the A and B controls and returns Estim2pyStatus.  Note, may not work on 2.106 firmware."""
        return self.__send(self.protocol.join_command(True))

    def unlink(self):
        """Unlinks the A and B controls and returns Estim2pyStatus.  Note, may not work on 2.106 firmware."""
        return self.__send(self.protocol.join_command(False))
    
    def kill(self):
        """Sets channels A and B to 0 and returns Estim2pyStatus"""
        return self.__send("K")

    def dynamic(self) -> Estim2pyStatus:
        """Sets the box to dynamic power mode and returns Estim2pyStatus.  Beta firmware only."""
        self.__require("dynamic", "Dynamic power")
        return self.__send("Y")

    def set_bias(self, bias: Estim2pyBias) -> Estim2pyStatus:
        """Sets the dynamic bias (used with dynamic power) and returns Estim2pyStatus.  Beta firmware only.

        args:
        bias (Estim2pyBias): A, B, AVERAGE or MAX.  The firmwares number these differently, this sends the right number.
        """
        self.__require("bias", "Dynamic bias")
        return self.__send("Q"+str(self.protocol.bias_code(bias)))

    def set_output_map(self, output_map: int) -> Estim2pyStatus:
        """Sets the output map (0 Map A, 1 Map B, 2 Map C) and returns Estim2pyStatus.  Beta firmware only."""
        self.__require("output_map", "Output map")
        if output_map not in range(3): raise ValueError(f"output map out of range [0-2] was {output_map}")
        return self.__send("O"+str(output_map))

    def step_channel(self, channel: ChannelName, direction: int) -> Estim2pyStatus:
        """Raises (direction 1) or lowers (direction -1) a channel by 1 and returns Estim2pyStatus.  Beta firmware only."""
        self.__require("step", "Stepping a channel")
        channel = channel.upper()
        if channel not in ['A', 'B', 'C', 'D']: raise ValueError(f"channel argument must be A, B, C, D. was {channel!r}")
        if direction not in (1, -1): raise ValueError(f"direction must be 1 or -1. was {direction}")
        return self.__send(channel + ("+" if direction == 1 else "-"))

    def set_warp(self, warp: int) -> Estim2pyStatus:
        """Sets the time warp factor (0-5 for x1 to x32) and returns Estim2pyStatus.  2.120B firmware and later."""
        self.__require("warp", "Warp factor")
        if warp not in range(6): raise ValueError(f"warp out of range [0-5] was {warp}")
        return self.__send("W"+str(warp))

    def set_ramp(self, ramp: int) -> Estim2pyStatus:
        """Sets the ramp step (0-3 for x1 to x4) and returns Estim2pyStatus.  2.120B firmware and later."""
        self.__require("ramp", "Ramp step")
        if ramp not in range(4): raise ValueError(f"ramp out of range [0-3] was {ramp}")
        return self.__send("R"+str(ramp))

    def version(self) -> Estim2pyStatus:
        """Asks the box for its version and returns Estim2pyStatus.  Without a version command (2.106) this is get_status()."""
        if not self.protocol.supports("version"):
            return self.get_status()
        return self.__send("V")

    def set_mode(self, mode_num: int) -> Estim2pyStatus:
        """Sets the mode to the numbered mode and returns Estim2pyStatus.

        Doesn't accept arguments over 100.  2.106 has modes 0-13, beta firmware 0-16, and the
        numbers mean different modes.  set_mode_by_name() works on every firmware.

        args:
        mode_num (int): mode number to set to.
        """
        if (mode_num < 0 or mode_num > self.MODE_MAX): raise ValueError("invalid mode number")
        return self.__send("M"+str(mode_num))

    def set_mode_by_name(self, name: str) -> Estim2pyStatus:
        """Sets the mode by name, e.g. "step", using this firmware's mode numbers.  Returns Estim2pyStatus.

        Raises ValueError for a mode this firmware does not have.  See Estim2pyMode for the names."""
        return self.set_mode(Estim2pyMode.get_id(name, self.protocol.name))

    def __require(self, feature: str, what: str) -> None:
        if not self.protocol.supports(feature):
            raise Estim2pyUnsupportedError(f"{what} is not supported by firmware {self.protocol.name}.")
    
    def __receive(self) -> bytes:
        logger.debug(f"Getting all input until a [{self.TERMINATION_CHAR}]. If things are broken here, this is the problem.")
        # May be different line ending on windows!  Or version?

        input = self.serial.read_until(self.TERMINATION_CHAR)
        logger.info(f"Received: {input.decode("ascii")}")
        return input

    def _exchange(self, out: str) -> bytes:
        """Send one command and return the raw reply.  Resends once if the box reports a buffer overrun."""
        for attempt in range(2):
            command = out+"\r" # thank you STPIHKAL https://buttplug.io/stpihkal/protocols/estim-systems/
            logger.info(f"Sending command: {out}")

            # kill the output buffer before sending
            self.serial.reset_input_buffer()

            self.serial.write(command.encode())  # pyright: ignore[reportUnusedCallResult]
            self.serial.flush() # block until everything is written out... Required! https://www.pyserial.com/docs/writing-data#flush

            # wait for delay before calling receive
            logger.debug(f"Sleeping for: {self.delay}")
            time.sleep(self.delay)

            reply = self.__receive()
            if reply.strip() != b"ERR":
                return reply
            logger.warning(f"2B reported a buffer overrun (ERR) on command {out!r}, attempt {attempt + 1} of 2")

        raise Estim2pyError("2B reported a buffer overrun (ERR) twice.", out)

    def __detect(self) -> Estim2pyProtocol:
        """Ask the box for its status and return the matching protocol.  Tries twice."""
        error = Estim2pyError("No reply from 2B.  Is it switched on and out of its menu?")
        for attempt in range(2):
            reply = self._exchange("")
            if not reply.strip():
                logger.warning(f"No reply from 2B while detecting the protocol, attempt {attempt + 1} of 2")
                continue
            try:
                return detect_protocol(reply)
            except Estim2pyError as e:
                logger.warning(f"Could not detect the protocol, attempt {attempt + 1} of 2: {e}")
                error = e
        raise error

    def __send(self, out: str) -> Estim2pyStatus:
        reply = self._exchange(out)
        if not reply.strip():
            raise Estim2pyError("No reply from 2B.  Is it switched on and out of its menu?", out)
        return self.protocol.parse(split_status(reply))
