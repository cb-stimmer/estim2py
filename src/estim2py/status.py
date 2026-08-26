from typing import override
from typing import Any
import logging

from warnings import deprecated

from .modes import Estim2pyMode
from .exceptions import Estim2pyError

logger = logging.getLogger(__name__)

NUMBER_OF_COLONS = 9

class Estim2pyStatus:
    """An object that reports back the status of the Estim Box.

    Object members are direct from the serial port.  Object methods relate closer to what the box displays and return useful python objects.

    i.e. status.a will return 200 at max power, but get_channel('a') will return 100.
    """
    def __init__(self, battery:int, a:int, b:int, c:int, d:int, mode:int, power:str, linked:int, version:str):
        """Not meant for instantiation directly.  But you can if you want I guess?"""
        self.battery:int  = battery
        self.a: int = a
        self.b: int = b
        self.c: int = c
        self.d: int = d
        self.mode: int = mode
        self.power: str = power
        self.linked: int = linked 
        self.version: str = version

    def get_channel(self, channel: str) -> int:
        """Returns the value of the channel as reported by UI on the box.

        Channel must be a,b,c or d (upper or lower).
        The value is what is displayed on the LCD, which is half of that reported on the serial port.

        This value is compatible with Estim2pyConnection.set_channel().
        """

        # note, we enforce channels a-d on runtime, so we know this is an int.
        if channel.lower() not in ['a','b','c','d']: raise ValueError(f"channel argument must be A, B, C, D. was {channel!r}")
        return getattr(self, channel.lower()) // 2  # pyright: ignore[reportAny]

    def get_a(self) ->int: return self.get_channel("a")
    def get_b(self) ->int: return self.get_channel("b")
    def get_c(self) ->int: return self.get_channel("c")
    def get_d(self) ->int: return self.get_channel("d")
    
    def is_high_power(self):
        """Returns True if the box is in high power mode, False otherwise."""
        return self.power == "H"
    
    def is_low_power(self):
        """Returns True if the box is in low power mode, False otherwise."""
        return self.power == "L"

    def is_linked(self):
        """Return True if the box is in linked mode, False otherwise."""
        return self.linked == 1
        
    def is_unlinked(self):
        """Returns True if the box is in unlinked mode, False otherwise."""
        return self.linked == 0

    def get_mode(self) -> Estim2pyMode:
        """Returns an Estim2pyMode representing the current mode.

        See Estim2pyMode for more information."""
        return Estim2pyMode.get_mode(self.mode)

    def as_items(self) -> tuple[tuple[str,int], tuple[str,int], tuple[str,int], tuple[str,int], tuple[str,int], tuple[str,int], tuple[str,str], tuple[str,int], tuple[str,str]]:
        """Returns an items-like representation of the status.

        It's 'items-like' in that you can use it for iteration, but modifying
        the values of the tuples inside the dictionary does nothing.

        NOTE, this is the raw values from the serial port.
        """
        return (("battery",self.battery),
                ("a",self.a),
                ("b",self.b),
                ("c",self.c),
                ("d",self.d),
                ("mode",self.mode),
                ("power",self.power),
                ("linked",self.linked),
                ("version",self.version))

    @override
    def __eq__(self, other: Any) -> bool:    # pyright: ignore[reportExplicitAny, reportAny]
        """Perform an equality check.

        This means you can do Estim2pyStatus == Estim2pyStatus and it will do the right thing!

        It ignores battery and version information as "incidental".
        """
        return isinstance(other, Estim2pyStatus) and\
            (self.a == other.a) and\
            (self.b == other.b) and\
            (self.c == other.c) and\
            (self.d == other.d) and\
            (self.mode == other.mode) and\
            (self.power == other.power) and\
            (self.linked == other.linked)

    @override
    def __ne__(self, other: Any) -> bool:  # pyright: ignore[reportExplicitAny, reportAny]
        return not self.__eq__(other)

    @override
    def __gt__(self, other: "Estim2pyStatus") -> bool:
        return isinstance(other, Estim2pyStatus) and \
            self.__power_level_greater(other) or self.__power_channels_greater(other)  

    @override
    def __ge__(self, other: "Estim2pyStatus") -> bool:
        return isinstance(other, Estim2pyStatus) and \
            ((self.__power_level_greater(other) or self.__power_level_equal(other)) and self.__rest_of_params_equal(other)) or \
            ((self.__power_channels_greater(other) or self.__power_channels_equal(other)) and self.__rest_of_params_equal(other))

    @override
    def __lt__(self, other: "Estim2pyStatus") -> bool:
        return isinstance(other, Estim2pyStatus) and \
            other.__power_level_greater(self) or other.__power_channels_greater(self)

    @override
    def __le__(self, other: "Estim2pyStatus") -> bool:
        return isinstance(other, Estim2pyStatus) and other.__ge__(self)
        
    def __power_level_greater(self, other: "Estim2pyStatus") -> bool:
        return self.is_high_power() and other.is_low_power()

    def __power_channels_greater(self, other: "Estim2pyStatus") -> bool:
        return (self.a + self.b) > (other.a + other.b)

    def __power_level_equal(self, other: "Estim2pyStatus") -> bool:
        return (self.power == other.power) 
    
    def __power_channels_equal(self, other: "Estim2pyStatus") -> bool:
        return self.a == other.a and self.b == other.b
     
    def __rest_of_params_equal(self, other: "Estim2pyStatus") -> bool:
        return (self.c == other.c) and\
            (self.d == other.d) and\
            (self.mode == other.mode) and\
            (self.linked == other.linked)

    def changes(self, other: "Estim2PyStatus") -> None | tuple:
        """ Returns a tuple of value-names that are different between two values"""
        if self == other:
            return None

        changeset = []

        if self.a != other.a:
            changeset.append("a")
        
        if self.b != other.b:
            changeset.append("b")

        if self.c != other.c:
            changeset.append("c")

        if self.d != other.d:
            changeset.append("d")

        if self.mode != other.mode:
            changeset.append("mode")
            
        if not self.__power_level_equal(other):
            changeset.append("power")

        if self.linked != other.linked:
            changeset.append("linked")

        return tuple(changeset)
    
    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.battery=},{self.a=},{self.b=},{self.c=},{self.d=},{self.mode=},{self.power=},{self.linked=},{self.version})"

    @override
    def __bytes__(self) -> bytes:
        """Returns a binary string that can can be used with from_binary."""
        return self.__str__().encode("ascii")

    @override
    def __str__(self) -> str:
        return f"230:{self.a}:{self.b}:{self.c}:{self.d}:{self.mode}:{self.power}:{self.linked}:0.2.3"
    
    @staticmethod
    def from_binary(bin: bytes):
        """Return an Estim2pyStatus object from bytes.

        This is mostly internal, but may be useful in some circumstances.  Check unit tests."""
        converted_string = bin.decode().strip()
        if not ":" in converted_string:
            logger.error(f"Got unexpected input.  No colon in [{converted_string}]")
            raise Estim2pyError("Unexpected input from 2B! Cannot parse into status.", converted_string)

        vals = converted_string.split(":")

        if len(vals) != NUMBER_OF_COLONS:
            logger.error(f"Got unexpected input.  Wrong Number of Colons [{converted_string}] Expecting {NUMBER_OF_COLONS}")
            raise Estim2pyError("Splitting failed.  Not enough parts:between:colon", converted_string)
        
        return Estim2pyStatus(int(vals[0]),\
                              int(vals[1]),\
                              int(vals[2]),\
                              int(vals[3]),\
                              int(vals[4]),\
                              int(vals[5]),\
                              str(vals[6]),\
                              int(vals[7]),\
                              str(vals[8]))

     
