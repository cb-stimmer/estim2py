from .status import Estim2pyStatus
from .modes import Estim2pyMode
from .connection import Estim2pyConnection
from .simulated import Estim2pySimulatedConnection
from .exceptions import Estim2pyError
from .__version__ import __version__

import logging

"""A set of classes for interacting with the Estim 2B Power box

Classes:
    Estim2pyConnection - Main class for speaking with the box
    Estim2pySimulatedConnection - A pretend box, for testing and developing.  Doesn't require serial
    Estim2pyStatus - A class representing a status returned from the 2B box
    Esitm2pyMode - A class representing a mode, plus it's metadata

Exception:
    Estim2pyError - Encapsulates connection and status parsing errors
"""


"""
Estim2py logs to the standard logger.

It will log any parse errors, which can be handy when troubleshooting.
INFO will be very chatty and tell you serial messages going back and forth
DEBUG will get into the internals, which may be too much.
"""
logger = logging.getLogger(__name__)
