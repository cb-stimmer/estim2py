from .status import Estim2pyStatus
from .modes import Estim2pyMode
from .connection import Estim2pyConnection
from .simulated import Estim2pySimulatedConnection
from .exceptions import Estim2pyError
from .__version__ import __version__

import logging

logger = logging.getLogger(__name__)

"""
A simple but thorough interface to the Estim 2B box.

Estim2pyConnection is the main Class you'll be interacting with.  You can use Estim2pySimulatedConnection for ... yanno... simulation.

Each interaction with Estim2pyConnection will return a Estim2pyStatus to query the state of the box.  Access it's members directly for the direct results from the box, or use the methods for a more human interface.  When you ues get_mode it will return an Estim2pyMode object, which will have all the information for that mode. You can also get any mode from it.
"""
