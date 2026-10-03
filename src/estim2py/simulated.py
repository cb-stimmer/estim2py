from typing import override

from .__version__ import __version__
from .connection import Estim2pyConnection
from .exceptions import Estim2pyError
from .protocol import Estim2pyProtocol, get_protocol
from .status import Estim2pyStatus


class Estim2pySimulatedConnection(Estim2pyConnection):
    """
    This is a sumulated 2B box, so you don't always have to plug a box in to write code.
    It should behave exactly like the real box.

    If it doesn't... that's a bug!

    The interface is exactly like Estim2pyConnection.  It replaces only the serial exchange: commands are
    interpreted here and answered with a status line in the format of the simulated firmware.

    keywords:
    protocol - the firmware to simulate: "2.106" (default), "2.119B", "2.120B" or an Estim2pyProtocol.
    """
    def __init__(self, protocol: str | Estim2pyProtocol = "2.106"):  # pyright: ignore[reportMissingSuperCall]
        self.serial = None
        self.delay = 0
        self.do_flush = False
        self.protocol = protocol if isinstance(protocol, Estim2pyProtocol) else get_protocol(protocol)
        self.do_throw = False
        self.reset_status()

    def reset_status(self):
        """Manually reset the status to the default state."""
        p = self.protocol
        version = __version__ if p.name == "2.106" else p.name
        self.status = Estim2pyStatus(230,0,0,100,100,0,"L",0,version,
                                     bias=0 if p.supports("bias") else None,
                                     output_map=0 if p.supports("output_map") else None,
                                     warp=0 if p.supports("warp") else None,
                                     ramp=0 if p.supports("ramp") else None,
                                     protocol=p.name)

    def error_on_next(self, do_throw=True):
        """Simulate an error on the next command.

        Error will only happen once.  After that normal behavior will continue.
        You can send it False to not error on the next command."""
        self.do_throw = do_throw
        return self.do_throw

    def simulate(self):
        if self.do_throw:
            self.do_throw = False
            raise Estim2pyError("Simulated Error.")

    @override
    def _exchange(self, out: str) -> bytes:
        self.run_command(out)
        self.simulate()
        return (self.protocol.format(self.status) + "\n").encode("ascii")

    def run_command(self, command: str):
        """Change the simulated status the way the box would for one command.

        Like the box, a command it does not know (or "" and V) changes nothing."""
        s = self.status
        legacy = self.protocol.name == "2.106"
        letter, rest = command[:1], command[1:]

        if command == "E":
            self.reset_status()
        elif command in ("L", "H") or (command == "Y" and self.protocol.supports("dynamic")):
            # Changing power zeroes A and B.  2.106 also resets C and D when going to low power.
            # Y (dynamic) also resets the bias to 0, seen on a 2.131B box.
            s.a = s.b = 0
            if command == "L" and legacy:
                s.c = s.d = 100
            if command == "Y":
                s.bias = 0
            s.power = "D" if command == "Y" else command
        elif command == "K":
            s.a = s.b = 0
        elif command == self.protocol.join_command(True):
            s.linked = 1
        elif command == self.protocol.join_command(False):
            s.linked = 0
        elif letter == "M" and rest.isdigit():
            # A new mode resets the channels, but keeps power, link and the beta settings.
            kept = (s.power, s.linked, s.bias, s.output_map, s.warp, s.ramp)
            self.reset_status()
            s = self.status
            s.mode = int(rest)
            s.power, s.linked, s.bias, s.output_map, s.warp, s.ramp = kept
        elif letter in ("A", "B", "C", "D") and rest.isdigit():
            setattr(s, letter.lower(), int(rest) * 2)
        elif letter in ("A", "B", "C", "D") and rest in ("+", "-") and self.protocol.supports("step"):
            value: int = getattr(s, letter.lower())  # pyright: ignore[reportAny]
            setattr(s, letter.lower(), min(200, max(0, value + (2 if rest == "+" else -2))))
        elif letter == "Q" and rest.isdigit() and self.protocol.supports("bias"):
            s.bias = int(rest)
        elif letter == "O" and rest.isdigit() and self.protocol.supports("output_map"):
            s.output_map = int(rest)
        elif letter == "W" and rest.isdigit() and self.protocol.supports("warp"):
            s.warp = int(rest)
        elif letter == "R" and rest.isdigit() and self.protocol.supports("ramp"):
            s.ramp = int(rest)
