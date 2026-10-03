import copy
from .__version__ import __version__
from .status import Estim2pyStatus
from .connection import Estim2pyConnection
from .exceptions import Estim2pyError
from .protocol import Legacy2106Protocol

# NOTE!  Next refactor, override send and recieve, call super, and then set status
class Estim2pySimulatedConnection(Estim2pyConnection):
    """
    This is a sumulated 2B box, so you don't always have to plug a box in to write code.
    It should behave exactly like the real box.

    If it doesn't... that's a bug!

    The interface is exactly like Estim2pyConnection.
    """
    def __init__(self):  # pyright: ignore[reportMissingSuperCall]
        self.serial = None
        self.protocol = Legacy2106Protocol()
        self.do_throw = False
        self.reset_status()

    def reset_status(self):
        """Manually reset the status to the default state."""
        self.status = Estim2pyStatus(230,0,0,100,100,0,"L",0,__version__)

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

    def get_status(self):
        self.simulate()
        return copy.deepcopy(self.status)

    def set_channel(self, channel, val):
        setattr(self.status, channel.lower(), val*2)
        self.simulate()
        return copy.deepcopy(self.status)

    def reset(self):
        self.reset_status()
        self.simulate()
        return copy.deepcopy(self.status)

    def low(self):
        self.kill()
        self.status.power = "L"
        self.simulate()
        return copy.deepcopy(self.status)

    def high(self):
        self.kill()
        self.status.power = "H"
        self.simulate()
        return copy.deepcopy(self.status)

    def link(self):
        self.status.linked = 1
        self.simulate()
        return copy.deepcopy(self.status)

    def unlink(self):
        self.status.linked = 0
        self.simulate()
        return copy.deepcopy(self.status)

    def kill(self):
        self.set_channel("A",0)
        self.set_channel("B",0)
        self.simulate()
        return copy.deepcopy(self.status)

    def set_mode(self, mode_num):
        power = self.status.power
        linked = self.status.linked

        self.reset_status()

        self.status.mode = mode_num
        self.status.power = power
        self.status.linked = linked

        self.simulate()
        return copy.deepcopy(self.status)
