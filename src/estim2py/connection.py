from typing import Literal

import serial  # pyright: ignore[reportMissingModuleSource]
import time
import logging

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
    """

    BAUD: int = 9600
    BYTESIZE: int = serial.EIGHTBITS
    PARITY: str = serial.PARITY_NONE
    STOPBITS: int = serial.STOPBITS_ONE

    MODE_MAX: int = 100

    TERMINATION_CHAR: Literal[b"\n"] = b"\n" 
    
    def __init__(self, device: str, timeout:float=2, delay:float=0.04, do_flush:bool=False) -> None:
        self.delay: float = delay
        self.do_flush: bool = do_flush
        self.serial: serial.Serial = serial.Serial(
            device,
            self.BAUD,
            timeout  = timeout,
            bytesize = self.BYTESIZE,
            parity   = self.PARITY,
            stopbits = self.STOPBITS)
        
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

        This will cowardly set the link to 0 before trying to send all the statuses
        Until I figure out what is wrong with channel link.
        
        args:
        to_status (Estim2pyStatus): target status.

        returns:
        True if all parameters were set, false if there was a mismatch.
        """


        if to_status.is_high_power():
            _ = self.high()
        else:
            _ = self.low()

        logger.debug("Cowardly setting linked to 0 because of link bug.")
        to_status.linked = 0
        # if (to_status.linked == 0): self.unlink else: self.link

        _ = self.set_mode(to_status.mode)
        
        _ = self.set_channel('a', to_status.get_channel('a'))
        _ = self.set_channel('b', to_status.get_channel('b'))
        _ = self.set_channel('c', to_status.get_channel('c'))
        _ = self.set_channel('d', to_status.get_channel('d'))

        current_status = self.get_status()
        result = current_status == to_status

        if not result:
            logger.warn(f"Estim2pyConneciton.set_to_status() failed.\nCurrent: {current_status=}\nTarget : {to_status}")  
        
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
        """Enable's link mode and returns Estim2pyStatus.  Note, does not work on my box!"""
        return self.__send("J")

    def unlink(self):
        """Enable's link mode and returns Estim2pyStatus.  Note, does not work on my box!"""
        return self.__send("U")
    
    def kill(self):
        """Sets channels A and B to 0 and returns Estim2pyStatus"""
        return self.__send("K")

    def set_mode(self, mode_num: int) -> Estim2pyStatus:
        """Sets the mode to the numbered mode and returns Estim2pyStatus.

        Doesn't accept arguments over 100.  Note that my box only accepts up to 13.
        (I might need an update.)

        args:
        mode_num (int): mode number to set to.
        """
        if (mode_num < 0 or mode_num > self.MODE_MAX): raise ValueError("invalid mode number")
        return self.__send("M"+str(mode_num))
    
    def __receive(self) -> bytes:
        logger.debug(f"Getting all input until a [{self.TERMINATION_CHAR}]. If things are broken here, this is the problem.")
        # May be different line ending on windows!  Or version?

        input = self.serial.read_until(self.TERMINATION_CHAR)
        logger.info(f"Received: {input.decode("ascii")}")
        return input

    def __send(self, out: str) -> Estim2pyStatus:
        command = out+"\r" # thank you STPIHKAL https://buttplug.io/stpihkal/protocols/estim-systems/
        logger.info(f"Sending command: {out}")

        # kill the output buffer before sending
        self.serial.reset_input_buffer()

        self.serial.write(command.encode())  # pyright: ignore[reportUnusedCallResult]
        self.serial.flush() # block until everything is written out... Required! https://www.pyserial.com/docs/writing-data#flush

        # wait for delay before calling receive
        logger.debug(f"Sleeping for: {self.delay}")
        time.sleep(self.delay)
        
        return Estim2pyStatus.from_binary(self.__receive())
