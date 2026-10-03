Design: Supporting the New 2B Firmware Protocol
===============================================

*Design proposal, 2026-10-03. Status: proposed, not yet implemented.*

Summary
-------

Add a small protocol layer so ``Estim2pyConnection`` works with both the
current firmware (2.106, 9-field status) and the beta firmware (2.119B,
11-field status), picking the right one automatically from the first status
reply.

- **Detection is free and safe.** Both firmwares answer any command, even an
  empty one, with a full status line. The number of colon-separated fields
  (9 or 11) identifies the protocol without sending anything that changes the
  box.
- **Existing code keeps working.** The public methods and ``Estim2pyStatus``
  attributes stay as they are; new firmware features are added as new methods
  and optional status fields.
- **Users can override.** A ``protocol=`` argument forces a protocol when
  auto-detection is not wanted.

Background
----------

Today the protocol is hard-coded in two places, so a box that answers with 11
fields fails at parse time with
``Estim2pyError("Splitting failed. Not enough parts:between:colon")``.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Module
     - What it assumes about the protocol
   * - ``connection.py``
     - 9600 8N1; command strings ``E L H K J U Mnn Cnnn`` terminated by
       ``\r``; reply read until ``\n``; ``MODE_MAX = 100``
   * - ``status.py``
     - ``NUMBER_OF_COLONS = 9`` (actually the field count); fixed field order
       ``battery:a:b:c:d:mode:power:linked:version``; ``__str__`` emits that
       9-field line
   * - ``simulated.py``
     - Mirrors the 2.106 behaviour; status built with the 9 positional fields
   * - ``modes.py``
     - Knows modes 0–13; ``get_mode()`` raises ``KeyError`` for anything else

The three failing integration tests (``test_integration``,
``test_integration_power_change_resets_a_b``, ``test_integration_kill``) fail
with exactly that parse error. They were run against a 2.119B box, so the
11-field reply is verified on real hardware.

Protocol comparison
-------------------

The beta firmware keeps the framing and the core commands, adds five commands,
changes how join is set, and adds two status fields before the version.

Status line
~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 40 50

   * - Index
     - 2.106 (current)
     - 2.119B (beta)
   * - 0
     - Battery
     - Battery (0–999)
   * - 1–4
     - A, B, C, D (0–200, double the display)
     - Same
   * - 5
     - Mode
     - Mode 0–16, numbered differently (see `Modes`_)
   * - 6
     - Power: ``L`` / ``H``
     - Power: ``L`` / ``H`` / ``D`` (dynamic)
   * - 7
     - Linked: 0 / 1
     - Dynamic bias: 0 A, 1 B, 2 Average, 3 Max
   * - 8
     - Version, e.g. ``2.106``
     - Join: 0 off, 1 joined
   * - 9
     - —
     - Output map: 0 A, 1 B, 2 C
   * - 10
     - —
     - Version, e.g. ``2.119B``
   * - Example
     - ``666:0:0:100:100:0:L:0:2.106``
     - ``344:10:12:120:116:15:L:0:0:0:2.119B``

Index 7 changes meaning between versions, so field position alone cannot be
reused across protocols. Both firmwares end the reply with ``\n``.

Modes
~~~~~

Only modes 0–2 keep their number. 2.119B inserts Flo at 3 and Cycle and Twist
at 12–13, so the same ``Mnn`` command starts a different program on each box.

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - ``M``
     - 2.106
     - 2.119B
   * - 0
     - Pulse
     - Pulse
   * - 1
     - Bounce
     - Bounce
   * - 2
     - Continuous
     - Continuous
   * - 3
     - A split
     - Flo (new)
   * - 4
     - B split
     - A split
   * - 5
     - Wave
     - B split
   * - 6
     - Waterfall
     - Wave
   * - 7
     - Squeeze
     - Waterfall
   * - 8
     - Milk
     - Squeeze
   * - 9
     - Throb
     - Milk
   * - 10
     - Thrust
     - Throb
   * - 11
     - Random
     - Thrust
   * - 12
     - Step
     - Cycle (new)
   * - 13
     - Training
     - Twist (new)
   * - 14
     - —
     - Random
   * - 15
     - —
     - Step
   * - 16
     - —
     - Training

Flo is a continuous mode: C controls the feel of channel A and D controls the
feel of channel B. Cycle and Twist reuse Thrust's C/D meanings and description
for now.

Commands
~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Command
     - 2.106
     - 2.119B
   * - ``Cnnn``, ``E``, ``L``, ``H``, ``K``, ``Mnn``
     - Yes
     - Yes (``E`` also resets baud to 9600)
   * - Join on / off
     - ``J`` / ``U``
     - ``J1`` / ``J0``
   * - ``C+`` / ``C-`` step a channel by 1
     - No
     - Yes
   * - ``Y`` dynamic power
     - No
     - Yes
   * - ``Qn`` dynamic bias
     - No
     - Yes
   * - ``On`` output map
     - No
     - Yes
   * - ``V`` version (returns status)
     - No (not in the 2.106 documentation)
     - Yes
   * - ``Z`` switch to 57600 baud
     - No
     - Yes

Both use 9600 8N1, uppercase ASCII, ``\r`` terminated, one command at a time.
The beta document states every command, even an unknown one, gets a full
status reply.

Detection strategy
------------------

On connect, send an empty command (just ``\r``, which ``get_status()`` already
does), split the reply on ``:`` and choose the protocol by field count; the
version string is a cross-check, not the primary key.

- **Why the empty command.** It changes nothing on either firmware. ``E`` would
  reset the box, ``V`` does not exist on 2.106, and ``Z`` changes the baud
  rate, so none of those are used for probing.
- **Why field count first.** It is the one difference that is structural and
  guaranteed by both documents. Version strings like ``2.106`` and ``2.119B``
  are less predictable across future releases.
- **Cross-check.** If a protocol declares a version pattern and the version
  field does not match, log a warning but keep the count-based choice.
- **Retry once.** A reply with neither 9 nor 11 fields is often a partial line
  left in the buffer. Flush input and probe once more before giving up.
- **Fail clearly.** After the retry, raise
  ``Estim2pyError("Unknown 2B protocol", raw_reply)`` so the user sees the
  exact line the box sent.
- **Remember the result.** Detection runs once per connection;
  ``connection.protocol`` exposes what was chosen. After an ``E`` the protocol
  does not change, so no re-detection is needed.

::

    Open serial port --> Send empty command --> Field count?
                              ^                   |  9 fields --> use 2.106 protocol
                              |                   | 11 fields --> use 2.119B protocol
                              |                   | other
                              |                   v
                              +--- first time -- Flush input, retry once
                                                  | still unknown
                                                  v
                                                 Raise Estim2pyError

With ``protocol=`` given, the probe is skipped and the named protocol is used
directly.

Proposed architecture
---------------------

A new ``protocol.py`` holds one class per firmware; the connection asks its
protocol how to spell each command and how to parse each reply, and nothing
else in the package knows field positions.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Component
     - Change
   * - ``protocol.py`` (new)
     - ``Estim2pyProtocol`` base class, ``Legacy2106Protocol``,
       ``Beta2119Protocol``, a ``PROTOCOLS`` registry and
       ``detect_protocol(raw)``
   * - ``status.py``
     - Gains optional ``bias``, ``output_map`` and ``protocol`` fields
       (default ``None``). ``from_binary()`` delegates to
       ``detect_protocol(raw).parse(raw)``. ``NUMBER_OF_COLONS`` goes away
   * - ``connection.py``
     - New ``protocol="auto"`` argument. ``link()``/``unlink()`` send
       ``protocol.join_command(on)``. New methods gated by
       ``protocol.supports(feature)``
   * - ``simulated.py``
     - ``Estim2pySimulatedConnection(protocol="2.106")`` simulates either
       firmware
   * - ``modes.py``
     - One mode table per protocol (``MODES_2106``, ``MODES_2119B``), keyed by
       mode number. ``Estim2pyStatus.get_mode()`` looks up in the table for
       ``self.protocol``; an unknown number returns an "unknown" mode instead
       of raising ``KeyError``
   * - ``exceptions.py``
     - ``Estim2pyUnsupportedError(Estim2pyError)`` for a feature the firmware
       lacks

.. code-block:: python

    class Estim2pyProtocol(ABC):
        name: ClassVar[str]
        field_count: ClassVar[int]
        power_modes: ClassVar[frozenset[str]]
        features: ClassVar[frozenset[str]] = frozenset()

        @abstractmethod
        def parse(self, fields: list[str]) -> Estim2pyStatus: ...

        @abstractmethod
        def join_command(self, on: bool) -> str: ...

        def supports(self, feature: str) -> bool:
            return feature in self.features


    class Legacy2106Protocol(Estim2pyProtocol):
        name = "2.106"
        field_count = 9
        power_modes = frozenset("LH")

        def parse(self, f):
            return Estim2pyStatus(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4]),
                                  int(f[5]), f[6], int(f[7]), f[8], protocol=self.name)

        def join_command(self, on):
            return "J" if on else "U"


    class Beta2119Protocol(Estim2pyProtocol):
        name = "2.119B"
        field_count = 11
        power_modes = frozenset("LHD")
        features = frozenset({"dynamic", "bias", "output_map", "step", "high_speed"})

        def parse(self, f):
            return Estim2pyStatus(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4]),
                                  int(f[5]), f[6], int(f[8]), f[10],
                                  bias=int(f[7]), output_map=int(f[9]), protocol=self.name)

        def join_command(self, on):
            return "J1" if on else "J0"


    PROTOCOLS = {p.field_count: p for p in (Legacy2106Protocol, Beta2119Protocol)}

    def detect_protocol(raw: bytes) -> Estim2pyProtocol:
        fields = raw.decode("ascii").strip().split(":")
        try:
            return PROTOCOLS[len(fields)]()
        except KeyError:
            raise Estim2pyError("Unknown 2B protocol", raw) from None

The beta parser maps its join field (index 8) onto the existing ``linked``
attribute, so ``is_linked()`` and equality keep meaning the same thing on both
boxes.

Public API and compatibility
----------------------------

Every existing call keeps its signature and behaviour on a 2.106 box; on a
2.119B box the same calls just work, and the new features are opt-in methods.

.. code-block:: python

    con = Estim2pyConnection("/dev/ttyUSB0")                    # auto-detect (default)
    con = Estim2pyConnection("/dev/ttyUSB0", protocol="2.106")  # force, no probe
    con.protocol.name        # "2.106" or "2.119B"

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - New method
     - Command
     - On 2.106
   * - ``dynamic()``
     - ``Y``
     - Raises ``Estim2pyUnsupportedError``
   * - ``set_bias(n)`` (0–3, or an ``IntEnum``)
     - ``Qn``
     - Raises
   * - ``set_output_map(n)`` (0–2)
     - ``On``
     - Raises
   * - ``step_channel(ch, +1 / -1)``
     - ``C+`` / ``C-``
     - Raises
   * - ``version()``
     - ``V``
     - Falls back to ``get_status()``
   * - ``set_mode_by_name(name)``
     - ``Mnn``, number looked up in the box's mode table
     - Works on both

Status additions: ``status.bias``, ``status.output_map``, ``status.protocol``
(all ``None`` on 2.106) and ``is_dynamic_power()``. ``__eq__`` compares
``bias`` and ``output_map`` only when both sides have them, so 2.106
comparisons are unchanged.

Three existing behaviours need small fixes:

- ``Estim2pyStatus.__str__`` and ``__bytes__`` currently always emit a 9-field
  line; they should emit the line for ``self.protocol``, so
  ``from_binary(bytes(status))`` round-trips on both.
- ``set_to_status()`` picks high or low power only; it should also handle
  ``D`` and, on 2.119B, apply bias and output map.
- ``set_mode(n)`` keeps sending the raw number, but ``set_to_status()`` should
  set the mode by name when the status came from a different firmware, since
  the numbers do not match.

The ``Z`` high-speed command is left out of the first version: it changes the
serial baud rate under the connection and needs ``E`` or a power cycle to
undo, which is easy to get wrong.

Testing plan
------------

Most of the change is testable without hardware, because detection and
parsing work on raw byte strings.

- **Parsing:** each protocol parses its documented example
  (``666:0:0:100:100:0:L:0:2.106``, ``344:10:12:120:116:15:L:0:0:0:2.119B``),
  including ``D`` power and every bias and map value.
- **Detection:** 9 fields → 2.106, 11 → 2.119B; 8, 10 and empty replies raise
  ``Estim2pyError`` carrying the raw line; a version mismatch logs a warning.
- **Round trip:** ``from_binary(bytes(status)) == status`` for both protocols.
- **Connection without a port:** mock ``serial.Serial`` so ``read_until``
  returns a canned line, and assert the bytes written (``J``/``U`` vs
  ``J1``/``J0``, ``Qn``, ``On``) and the retry-once behaviour.
- **Simulator:** run the existing simulated-connection tests against both
  ``protocol="2.106"`` and ``protocol="2.119B"`` with
  ``pytest.mark.parametrize``.
- **Hardware:** mark the three failing integration tests
  ``@pytest.mark.hardware`` so they skip without a box, then make their
  expected replies protocol-aware and run them on both boxes.
- **Modes:** every number in both mode tables resolves to the expected name,
  and ``set_mode_by_name("step")`` sends ``M12`` on 2.106 and ``M15`` on
  2.119B.

Open questions and rollout
--------------------------

Resolved:

- The 2.119B box ends replies with ``\n``, like 2.106.
- The 2.119B mode list is known (see `Modes`_), including what C and D do in
  the new Flo mode.
- 2.106 has no ``V`` command, so ``version()`` falls back to ``get_status()``
  there.

Still open:

- Does ``J1``/``J0`` fix the join problem that ``link()`` documents ("does not
  work on my box")? To be tested on the 2.119B box.

Rollout, one pull request each:

1. Add ``protocol.py`` with both parsers and detection, plus the parsing and
   detection tests. ``from_binary()`` uses it; no connection changes yet.
2. Wire ``protocol=`` and detection into ``Estim2pyConnection``, switch
   ``link()``/``unlink()`` to ``join_command()``, and mark the hardware tests.
3. Add the 2.119B-only methods, status fields, per-firmware mode tables and
   simulator support.
4. Update the docs and release as 0.4.0 (new public API, nothing removed).
