Design: Supporting the New 2B Firmware Protocols
================================================

*Design proposal, 2026-10-03. Status: steps 1 and 2 of the rollout are
implemented (see* :mod:`estim2py.protocol` *and*
:class:`estim2py.connection.Estim2pyConnection` *); steps 3 and 4 are
proposed.*

Summary
-------

Add a small protocol layer so ``Estim2pyConnection`` works with the original
firmware (2.106, 9-field status) and the beta firmwares (2.119B, 11 fields;
2.120B and later, 13 fields), picking the right one automatically from the
first status reply.

- **Detection is free and safe.** Every firmware answers any command, even an
  empty one, with a full status line. The number of colon-separated fields
  (9, 11 or 13) identifies the protocol without sending anything that changes
  the box.
- **Existing code keeps working.** The public methods and ``Estim2pyStatus``
  attributes stay as they are; new firmware features are added as new methods
  and optional status fields.
- **Users can override.** A ``protocol=`` argument forces a protocol when
  auto-detection is not wanted.

Background
----------

Before this work the protocol was hard-coded, so a box that answered with
more than 9 fields failed at parse time with
``Estim2pyError("Splitting failed. Not enough parts:between:colon")``.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Module
     - What it assumed about the protocol
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

The test box runs firmware **2.131B** and replies with 13 fields, for example
``762:0:0:100:100:0:L:0:0:0:0:0:2.131B``. That matches the 2.120B command
summary, so 2.131B is handled by the 2.120B protocol.

Protocol comparison
-------------------

The beta firmwares keep the framing and the core commands, add new commands,
change how join is set, and add status fields before the version. 2.120B adds
two more fields and renumbers the dynamic bias values.

Status line
~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 8 26 30 36

   * - Index
     - 2.106
     - 2.119B
     - 2.120B and later
   * - 0
     - Battery
     - Battery (0–999)
     - Battery (0–999)
   * - 1–4
     - A, B, C, D (0–200, double the display)
     - Same
     - Same
   * - 5
     - Mode
     - Mode 0–16 (see `Modes`_)
     - Mode 0–16 (see `Modes`_)
   * - 6
     - Power: ``L`` / ``H``
     - Power: ``L`` / ``H`` / ``D`` (dynamic)
     - Power: ``L`` / ``H`` / ``D`` (dynamic)
   * - 7
     - Linked: 0 / 1
     - Dynamic bias: 0 A, 1 B, 2 Average, 3 Max
     - Dynamic bias: 0 Max, 1 A, 2 B, 3 Average
   * - 8
     - Version, e.g. ``2.106``
     - Join: 0 off, 1 joined
     - Join: 0 off, 1 joined
   * - 9
     - —
     - Output map: 0 A, 1 B, 2 C
     - Output map: 0 A, 1 B, 2 C
   * - 10
     - —
     - Version, e.g. ``2.119B``
     - Warp factor: 0–5 for x1, x2, x4, x8, x16, x32
   * - 11
     - —
     - —
     - Ramp step: 0–3 for x1 to x4
   * - 12
     - —
     - —
     - Version, e.g. ``2.120B``, ``2.131B``
   * - Example
     - ``666:0:0:100:100:0:L:0:2.106``
     - ``344:10:12:120:116:15:L:0:0:0:2.119B``
     - ``344:10:12:120:116:15:L:0:0:0:0:0:2.120B``

Index 7 changes meaning between versions, and even between the two betas the
bias numbers mean different things (the 2.120B document lists this as a "Bias
Command Correction"). So a raw bias number is only meaningful together with
its protocol. All firmwares end the reply with ``\n``.

Modes
~~~~~

Only modes 0–2 keep their number. The beta firmwares insert Flo at 3 and Cycle
and Twist at 12–13, so the same ``Mnn`` command starts a different program on
a 2.106 box than on a beta box. Audio modes cannot be selected over serial.

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - ``M``
     - 2.106
     - 2.119B and later
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
   :widths: 34 22 22 22

   * - Command
     - 2.106
     - 2.119B
     - 2.120B and later
   * - ``Cnnn``, ``E``, ``L``, ``H``, ``K``, ``Mnn``
     - Yes
     - Yes (``E`` also resets baud to 9600)
     - Yes
   * - Join on / off
     - ``J`` / ``U``
     - ``J1`` / ``J0``
     - ``J1`` / ``J0``
   * - ``C+`` / ``C-`` step a channel by 1
     - No
     - Yes
     - Yes
   * - ``Y`` dynamic power
     - No
     - Yes
     - Yes
   * - ``Qn`` dynamic bias
     - No
     - Yes
     - Yes (new numbering)
   * - ``On`` output map
     - No
     - Yes
     - Yes
   * - ``V`` version (returns status)
     - No
     - Yes
     - Yes
   * - ``Wn`` warp factor
     - No
     - No
     - Yes
   * - ``Rn`` ramp step
     - No
     - No
     - Yes
   * - ``Z`` switch to 57600 baud
     - No
     - Yes
     - No (removed)

All use 9600 8N1, uppercase ASCII, ``\r`` terminated, one command at a time.
The beta documents state every command, even an unknown one, gets a full
status reply. On 2.120B a buffer overrun replies ``ERR`` instead of a status
line.

Behaviour differences
~~~~~~~~~~~~~~~~~~~~~

Changing power level resets other settings differently. Seen on hardware:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Command
     - 2.106
     - 2.131B
   * - ``H`` (to high)
     - A and B to 0, C and D kept
     - A and B to 0, C and D kept
   * - ``L`` (to low)
     - A and B to 0, C and D back to 100
     - A and B to 0, C and D kept

The 2.106 column comes from the expectations in the existing hardware tests.

Detection strategy
------------------

On connect, send an empty command (just ``\r``, which ``get_status()`` already
does), split the reply on ``:`` and choose the protocol by field count; the
version string is a cross-check, not the primary key.

- **Why the empty command.** It changes nothing on any firmware. ``E`` would
  reset the box, ``V`` does not exist on 2.106, and ``Z`` changes the baud
  rate, so none of those are used for probing.
- **Why field count first.** It is the one difference that is structural and
  guaranteed by every document. Version strings like ``2.106``, ``2.119B`` and
  ``2.131B`` are less predictable across future releases.
- **Cross-check.** If a protocol declares a version pattern and the version
  field does not match, log a warning but keep the count-based choice. The
  2.120B protocol accepts 2.120 to 2.139.
- **Flush first, retry once.** The box sometimes sends an extra status line,
  and a reply with an unknown field count is often a partial line left in the
  buffer. Flush input before probing, and probe once more before giving up.
- **Box not answering.** A box in its menu does not answer serial commands, so
  an empty reply should raise an error that suggests leaving the menu.
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
                              |                   | 13 fields --> use 2.120B protocol
                              |                   | other
                              |                   v
                              +--- first time -- Flush input, retry once
                                                  | still unknown
                                                  v
                                                 Raise Estim2pyError

With ``protocol=`` given, the probe is skipped and the named protocol is used
directly.

Architecture
------------

``protocol.py`` holds one class per firmware; the connection asks its protocol
how to spell each command and how to parse each reply, and nothing else in the
package knows field positions.

.. list-table::
   :header-rows: 1
   :widths: 20 65 15

   * - Component
     - Change
     - Step
   * - ``protocol.py`` (new)
     - ``Estim2pyProtocol`` base class, ``Legacy2106Protocol``,
       ``Beta2119Protocol``, ``Beta2120Protocol``, a ``PROTOCOLS`` registry
       keyed by field count, ``split_status(raw)`` and
       ``detect_protocol(raw)``
     - 1 (done)
   * - ``status.py``
     - Optional ``bias``, ``output_map``, ``warp``, ``ramp`` and ``protocol``
       fields (default ``None``). ``from_binary()`` delegates to
       ``detect_protocol()``. ``NUMBER_OF_COLONS`` is gone
     - 1 (done)
   * - ``exceptions.py``
     - ``Estim2pyError.__str__`` fixed so errors show the raw line
       (it used to print ``<exception str() failed>``)
     - 1 (done)
   * - ``connection.py``
     - New ``protocol="auto"`` argument and ``connection.protocol``.
       Replies are parsed with the connection's protocol.
       ``link()``/``unlink()`` send ``protocol.join_command(on)``. An ``ERR``
       reply is resent once; an empty reply raises an error that mentions
       the menu
     - 2 (done)
   * - ``connection.py``
     - New methods gated by ``protocol.supports(feature)``
     - 3
   * - ``simulated.py``
     - Has a 2.106 ``protocol`` attribute (step 2).
       ``Estim2pySimulatedConnection(protocol="2.106")`` simulates any
       firmware, including the power-change differences
     - 3
   * - ``modes.py``
     - One mode table per mode numbering (2.106, and 2.119B and later),
       keyed by mode number. ``Estim2pyStatus.get_mode()`` looks up the table
       for ``self.protocol``; an unknown number returns an "unknown" mode
       instead of raising ``KeyError``
     - 3
   * - ``exceptions.py``
     - ``Estim2pyUnsupportedError(Estim2pyError)`` for a feature the firmware
       lacks
     - 3

Each protocol class declares its field count, power letters, optional features
and version pattern, and implements ``_build()`` (fields to status) and
``join_command()``. The shared ``parse()`` checks the field count, wraps
non-numeric fields and unknown power letters in ``Estim2pyError``, and warns
on an unexpected version. See :mod:`estim2py.protocol` for the code.

The beta parsers store the join field (index 8) in the existing ``linked``
attribute, so ``is_linked()`` and equality mean the same thing on every box.

Public API and compatibility
----------------------------

Every existing call keeps its signature and behaviour on a 2.106 box; on a
beta box the same calls just work, and the new features are opt-in methods.

.. code-block:: python

    con = Estim2pyConnection("/dev/ttyUSB0")                    # auto-detect (default)
    con = Estim2pyConnection("/dev/ttyUSB0", protocol="2.106")  # force, no probe
    con.protocol.name        # "2.106", "2.119B" or "2.120B"

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - New method
     - Command
     - Without firmware support
   * - ``dynamic()``
     - ``Y``
     - Raises ``Estim2pyUnsupportedError``
   * - ``set_bias(bias)`` (an ``IntEnum``: A, B, Average, Max)
     - ``Qn``, number from the protocol's bias numbering
     - Raises
   * - ``set_output_map(n)`` (0–2)
     - ``On``
     - Raises
   * - ``step_channel(ch, +1 / -1)``
     - ``C+`` / ``C-``
     - Raises
   * - ``set_warp(n)`` (0–5)
     - ``Wn``
     - Raises (2.120B and later only)
   * - ``set_ramp(n)`` (0–3)
     - ``Rn``
     - Raises (2.120B and later only)
   * - ``version()``
     - ``V``
     - Falls back to ``get_status()``
   * - ``set_mode_by_name(name)``
     - ``Mnn``, number looked up in the box's mode table
     - Works everywhere

Because the bias numbering differs between 2.119B and 2.120B, ``set_bias()``
takes a named value rather than a raw number, and the status should offer a
matching ``get_bias()`` that translates ``status.bias`` through the protocol.

Status additions: ``status.bias``, ``status.output_map``, ``status.warp``,
``status.ramp``, ``status.protocol`` (``None`` where the firmware does not
report them) and ``is_dynamic_power()``. ``__eq__`` should compare the new
fields only when both sides have them, so 2.106 comparisons are unchanged.

Three existing behaviours need small fixes:

- ``Estim2pyStatus.__str__`` and ``__bytes__`` currently always emit a 9-field
  line; they should emit the line for ``self.protocol``, so
  ``from_binary(bytes(status))`` round-trips on every protocol.
- ``set_to_status()`` picks high or low power only; it should also handle
  ``D`` and, on beta firmware, apply bias, output map, warp and ramp.
- ``set_mode(n)`` keeps sending the raw number, but ``set_to_status()`` should
  set the mode by name when the status came from a firmware with a different
  mode numbering.

The 2.119B ``Z`` high-speed command is left out: it changes the serial baud
rate under the connection, needs ``E`` or a power cycle to undo, and was
removed in 2.120B.

Testing plan
------------

Most of the change is testable without hardware, because detection and
parsing work on raw byte strings.

- **Parsing (done):** each protocol parses its documented example, the real
  2.131B reply, ``D`` power, and every bias, map, warp and ramp value.
- **Detection (done):** 9 fields → 2.106, 11 → 2.119B, 13 → 2.120B; other
  counts and non-status replies raise ``Estim2pyError`` carrying the raw line;
  a version mismatch logs a warning.
- **Round trip:** ``from_binary(bytes(status)) == status`` for every protocol.
- **Connection without a port (done):** mock ``serial.Serial`` so ``read_until``
  returns a canned line, and assert the bytes written (``J``/``U`` vs
  ``J1``/``J0``, ``Qn``, ``On``, ``Wn``, ``Rn``), the retry-once behaviour and
  ``ERR`` handling.
- **Simulator:** run the existing simulated-connection tests against every
  protocol with ``pytest.mark.parametrize``.
- **Hardware (done):** the expected replies in the hardware tests depend on
  ``con.protocol``: what ``L`` does to C and D (see `Behaviour
  differences`_), and modes above 13 and linking, which are expected
  failures on 2.106 only. All pass on the 2.131B box.
  ``test_timeout`` still needs a look: it uses a ``con`` it never creates, so
  it fails with an ``AttributeError`` and is reported as an expected failure
  for the wrong reason.
- **Modes:** every number in both mode tables resolves to the expected name,
  and ``set_mode_by_name("step")`` sends ``M12`` on 2.106 and ``M15`` on beta
  firmware.

Open questions and rollout
--------------------------

Resolved:

- Every firmware ends replies with ``\n``.
- The beta mode list is known (see `Modes`_), including what C and D do in
  the new Flo mode.
- 2.106 has no ``V`` command, so ``version()`` falls back to ``get_status()``
  there.
- The test box is 2.131B and speaks the 13-field 2.120B protocol.
- ``J1``/``J0`` link and unlink the controls on 2.131B: the join field
  (index 8) changes and the box shows the controls as linked. The library's
  ``link()`` fails on beta boxes only because it sends the 2.106 ``J``;
  step 2 switches it to ``join_command()``.

Still open:

- Does 2.119B reset C and D on ``L`` like 2.106, or keep them like 2.131B?
  No 2.119B box is available to check.

Rollout, one pull request each:

1. **Done.** Add ``protocol.py`` with the parsers and detection, plus the
   parsing and detection tests. ``from_binary()`` uses it; no connection
   changes yet.
2. **Done.** Wire ``protocol=`` and detection into ``Estim2pyConnection``, switch
   ``link()``/``unlink()`` to ``join_command()``, handle ``ERR`` and empty
   replies, and make the hardware tests protocol-aware.
3. Add the beta-only methods, ``get_bias()``/``set_bias()``, the remaining
   status changes, per-firmware mode tables and simulator support.
4. Update the user docs and release as 0.4.0 (new public API, nothing
   removed).
