class Estim2pyMode:
    """A class representing a mode for the Estim 2b.

    Construct with Estim2pyMode.get_mode(int).  That will return the relevant mode by integer id.
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
    """
    
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
    def get_mode(cls, mid: int):
        """Returns the mode based on the integer id.""" 
        m = Estim2pyMode.modes[mid]
        return Estim2pyMode(mid, m[0], m[1], m[2], m[3])

    @classmethod
    def id_names(cls) -> dict[int, str]:
        """returns a dictionary of {modeid: name, ...}

        i.e. {0: "pulse", 1: "bounce", ...}
        """ 
        return {id: m[0] for id, m in cls.modes.items() }


