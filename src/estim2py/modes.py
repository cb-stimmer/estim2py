class Estim2pyMode:
    """A class representing a mode for the Estim 2b.

    Construct with Estim2pyMode.get_mode(int).  That will return the relevant mode by integer id.

    2.106 and the beta firmwares (2.119B and later) number the modes differently.  Pass the protocol
    name to get_mode(), id_names() and get_id() to use the right numbering; without it, 2.106 is used.
    """

    modes: dict[ int, tuple[str, str, str | None, str]] = {
        0: ( "pulse",     "pulse speed", "pulse feel", "Pulsing on and off" ),
        1: ( "bounce",    "pulse speed", "pulse feel", "Pulsing alternatively" ),
        2: ( "continuous","pulse feel", None,          "Both channels always on" ),
        3: ( "asplit",    "pulse speed", "pulse feel", "A Pulse B Continuous" ),
        4: ( "bsplit",    "pulse speed", "pulse feel", "B Pulse A Continuous" ),
        5: ( "wave",      "speed of increase",            "wave feel",   "Output increases to power, then to 0" ),
        6: ( "waterfall", "speed of increase / decrease", "waterfall feel", "Output to power, then back down" ),
        7: ( "squeeze",   "pulse speed", "feel", "Pulse rate increases and then drops to slow" ),
        8: ( "milk",      "pulse speed", "feel", "Pulse rate increases and then drops to slow, b channel alternates" ),
        9: ( "throb",     "feel range", None, "Continuous, with the feel increasing to range and dropping to 0" ),
        10: ( "thrust",   "feel range", None, "Continuous, with the feel increasing to range and decreasing" ),
        11: ( "random",   "random range", "pulse feel", "Random Levels" ),
        12: ( "step",     "step delay", "pulse feel", "Builds towards a power level slowly" ),
        13: ( "training", "jump delay", "pulse feel", "Jumps to the power level quickly" )
    }
    """Numeric dictionary of modes that this class knows about. Access directly if you like!
    The key is the mode id, and the value is a tuple in the format of:
    [0] - Name
    [1] - Channel C name
    [2] - Channel D name, or none if N/A
    [3] - short description

    These are the 2.106 numbers.  See beta_modes for 2.119B and later.
    """

    beta_modes: dict[ int, tuple[str, str, str | None, str]] = {
        0: ( "pulse",     "pulse speed", "pulse feel", "Pulsing on and off" ),
        1: ( "bounce",    "pulse speed", "pulse feel", "Pulsing alternatively" ),
        2: ( "continuous","pulse feel", None,          "Both channels always on" ),
        3: ( "flo",       "A feel",      "B feel",     "Continuous, C sets the feel of channel A and D the feel of channel B" ),
        4: ( "asplit",    "pulse speed", "pulse feel", "A Pulse B Continuous" ),
        5: ( "bsplit",    "pulse speed", "pulse feel", "B Pulse A Continuous" ),
        6: ( "wave",      "speed of increase",            "wave feel",   "Output increases to power, then to 0" ),
        7: ( "waterfall", "speed of increase / decrease", "waterfall feel", "Output to power, then back down" ),
        8: ( "squeeze",   "pulse speed", "feel", "Pulse rate increases and then drops to slow" ),
        9: ( "milk",      "pulse speed", "feel", "Pulse rate increases and then drops to slow, b channel alternates" ),
        10: ( "throb",    "feel range", None, "Continuous, with the feel increasing to range and dropping to 0" ),
        11: ( "thrust",   "feel range", None, "Continuous, with the feel increasing to range and decreasing" ),
        # No description for cycle and twist yet, they borrow thrust's.
        12: ( "cycle",    "feel range", None, "Continuous, with the feel increasing to range and decreasing" ),
        13: ( "twist",    "feel range", None, "Continuous, with the feel increasing to range and decreasing" ),
        14: ( "random",   "random range", "pulse feel", "Random Levels" ),
        15: ( "step",     "step delay", "pulse feel", "Builds towards a power level slowly" ),
        16: ( "training", "jump delay", "pulse feel", "Jumps to the power level quickly" )
    }
    """Modes of the beta firmwares (2.119B and later), in the same format as modes."""

    
    def __init__(self, mid: int, name: str, param_a: str, param_b: str | None, notes: str):
        """Constructor.  Not normally meant to be called from Estim2pyMode.get_mode"""
        self.mid: int  = mid
        """numeric id of the mode."""
        self.name: str = name
        """Short name of the mode."""
        self.param_a: str = param_a
        """What channel C modifies."""
        self.param_b: str | None = param_b
        """What channel D modifies, or None if not applicable"""
        self.notes: str = notes
        """A real short description of the mode."""
        
    @classmethod
    def table(cls, protocol: str | None = None) -> dict[int, tuple[str, str, str | None, str]]:
        """Returns the mode table for a protocol name.  None or "2.106" gives modes, anything else beta_modes."""
        return cls.modes if protocol in (None, "2.106") else cls.beta_modes

    @classmethod
    def get_mode(cls, mid: int, protocol: str | None = None):
        """Returns the mode based on the integer id.

        A number the firmware does not have returns a mode named "unknown"."""
        m = cls.table(protocol).get(mid, ("unknown", "C", "D", "Unknown mode"))
        return Estim2pyMode(mid, m[0], m[1], m[2], m[3])

    @classmethod
    def get_id(cls, name: str, protocol: str | None = None) -> int:
        """Returns the mode number for a mode name, e.g. "step" is 12 on 2.106 and 15 on beta firmware.

        Raises ValueError for a name the firmware does not have."""
        for mid, m in cls.table(protocol).items():
            if m[0] == name.lower():
                return mid
        raise ValueError(f"Unknown mode {name!r} for firmware {protocol or '2.106'}.")

    @classmethod
    def id_names(cls, protocol: str | None = None) -> dict[int, str]:
        """returns a dictionary of {modeid: name, ...}

        i.e. {0: "pulse", 1: "bounce", ...}
        """ 
        return {id: m[0] for id, m in cls.table(protocol).items() }


