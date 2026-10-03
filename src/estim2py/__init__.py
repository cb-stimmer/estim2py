from .status import Estim2pyStatus
from .modes import Estim2pyMode
from .connection import Estim2pyConnection
from .simulated import Estim2pySimulatedConnection
from .exceptions import Estim2pyError, Estim2pyUnsupportedError
from .protocol import Estim2pyBias, Estim2pyProtocol
from .__version__ import __version__

import logging

"""A set of classes for interacting with the Estim 2B Power box

Classes:
    Estim2pyConnection - Main class for speaking with the box
    Estim2pySimulatedConnection - A pretend box, for testing and developing.  Doesn't require serial
    Estim2pyStatus - A class representing a status returned from the 2B box
    Esitm2pyMode - A class representing a mode, plus it's metadata
    Estim2pyProtocol - The serial protocol of a firmware family (2.106, 2.119B, 2.120B)
    Estim2pyBias - Dynamic bias settings, for set_bias() and get_bias()

Exception:
    Estim2pyError - Encapsulates connection and status parsing errors
    Estim2pyUnsupportedError - The connected firmware does not support a feature
"""


"""
Estim2py logs to the standard logger.

It will log any parse errors, which can be handy when troubleshooting.
INFO will be very chatty and tell you serial messages going back and forth
DEBUG will get into the internals, which may be too much.
"""
logger = logging.getLogger(__name__)
