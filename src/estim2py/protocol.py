# pyright: reportImportCycles=false
# status.py imports this module, and _build() imports status.py lazily, so the cycle is safe.
import logging
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, final, override

from .exceptions import Estim2pyError

if TYPE_CHECKING:
    from .status import Estim2pyStatus

logger = logging.getLogger(__name__)


class Estim2pyProtocol(ABC):
    """The serial protocol spoken by one 2B firmware family.

    A protocol knows how many fields the status line has, how to turn those fields into an
    Estim2pyStatus, and how to spell the commands that differ between firmwares.

    Use detect_protocol() to pick the right one from a raw status line.
    """

    name: ClassVar[str]
    """Short name, also stored on every status this protocol parses."""

    field_count: ClassVar[int]
    """Number of colon separated fields in the status line."""

    power_modes: ClassVar[frozenset[str]]
    """Power mode letters this firmware reports."""

    features: ClassVar[frozenset[str]] = frozenset()
    """Optional features beyond the common command set."""

    version_pattern: ClassVar[re.Pattern[str] | None] = None
    """If set, a version field that does not match logs a warning.  Detection still trusts the field count."""

    @abstractmethod
    def _build(self, fields: list[str]) -> "Estim2pyStatus":
        """Build a status from fields that are known to be the right count."""

    @abstractmethod
    def join_command(self, on: bool) -> str:
        """The command that turns join (linked controls) on or off."""

    def supports(self, feature: str) -> bool:
        """Returns True if this firmware supports the named optional feature."""
        return feature in self.features

    def parse(self, fields: list[str]) -> "Estim2pyStatus":
        """Return an Estim2pyStatus from the colon separated fields of a status line.

        Raises Estim2pyError if the fields do not fit this protocol."""
        line = ":".join(fields)
        if len(fields) != self.field_count:
            raise Estim2pyError(f"Protocol {self.name} expects {self.field_count} fields, got {len(fields)}.", line)

        try:
            status = self._build(fields)
        except ValueError as e:
            logger.error(f"Got unexpected input.  Non numeric field in [{line}]")
            raise Estim2pyError(f"Cannot parse status as protocol {self.name}: {e}", line) from e

        if status.power not in self.power_modes:
            logger.error(f"Got unexpected input.  Unknown power mode {status.power!r} in [{line}]")
            raise Estim2pyError(f"Unknown power mode {status.power!r} for protocol {self.name}.", line)

        if self.version_pattern and not self.version_pattern.search(status.version):
            logger.warning(f"Firmware version {status.version!r} is not a known {self.name} version.  Parsing as {self.name} anyway.")

        return status


@final
class Legacy2106Protocol(Estim2pyProtocol):
    """Firmware 2.106 and earlier.  Status: battery:a:b:c:d:mode:power:linked:version"""

    name = "2.106"
    field_count = 9
    power_modes = frozenset("LH")

    @override
    def _build(self, fields: list[str]) -> "Estim2pyStatus":
        # imported here, status.py imports this module
        from .status import Estim2pyStatus

        f = fields
        return Estim2pyStatus(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4]),
                              int(f[5]), f[6], int(f[7]), f[8], protocol=self.name)

    @override
    def join_command(self, on: bool) -> str:
        return "J" if on else "U"


@final
class Beta2119Protocol(Estim2pyProtocol):
    """Beta firmware 2.119B.  Status: battery:a:b:c:d:mode:power:bias:join:map:version

    Bias: 0 A, 1 B, 2 Average, 3 Max.
    The join field is stored in Estim2pyStatus.linked, so is_linked() means the same on every firmware."""

    name = "2.119B"
    field_count = 11
    power_modes = frozenset("LHD")
    features = frozenset({"dynamic", "bias", "output_map", "step", "high_speed"})
    version_pattern = re.compile(r"^2\.119")

    @override
    def _build(self, fields: list[str]) -> "Estim2pyStatus":
        # imported here, status.py imports this module
        from .status import Estim2pyStatus

        f = fields
        return Estim2pyStatus(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4]),
                              int(f[5]), f[6], int(f[8]), f[10],
                              bias=int(f[7]), output_map=int(f[9]), protocol=self.name)

    @override
    def join_command(self, on: bool) -> str:
        return "J1" if on else "J0"


@final
class Beta2120Protocol(Estim2pyProtocol):
    """Beta firmware 2.120B and later 2.1xxB.  Status: battery:a:b:c:d:mode:power:bias:join:map:warp:ramp:version

    Bias: 0 Max, 1 A, 2 B, 3 Average (numbered differently from 2.119B).
    Warp: 0-5 for x1 to x32.  Ramp: 0-3 for x1 to x4.
    The join field is stored in Estim2pyStatus.linked, so is_linked() means the same on every firmware."""

    name = "2.120B"
    field_count = 13
    power_modes = frozenset("LHD")
    features = frozenset({"dynamic", "bias", "output_map", "step", "warp", "ramp"})
    version_pattern = re.compile(r"^2\.1[23]\d")

    @override
    def _build(self, fields: list[str]) -> "Estim2pyStatus":
        # imported here, status.py imports this module
        from .status import Estim2pyStatus

        f = fields
        return Estim2pyStatus(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4]),
                              int(f[5]), f[6], int(f[8]), f[12],
                              bias=int(f[7]), output_map=int(f[9]), warp=int(f[10]), ramp=int(f[11]),
                              protocol=self.name)

    @override
    def join_command(self, on: bool) -> str:
        return "J1" if on else "J0"


PROTOCOLS: dict[int, type[Estim2pyProtocol]] = {
    p.field_count: p for p in (Legacy2106Protocol, Beta2119Protocol, Beta2120Protocol)
}
"""Known protocols, keyed by the field count of their status line."""


def split_status(raw: bytes) -> list[str]:
    """Decode a raw status line and split it into fields.

    Raises Estim2pyError if the line is not a colon separated status."""
    line = raw.decode("ascii", errors="replace").strip()
    if ":" not in line:
        logger.error(f"Got unexpected input.  No colon in [{line}]")
        raise Estim2pyError("Unexpected input from 2B! Cannot parse into status.", line)
    return line.split(":")


def detect_protocol(raw: bytes) -> Estim2pyProtocol:
    """Return the protocol that matches a raw status line, chosen by its field count.

    Raises Estim2pyError carrying the raw line if no known protocol matches."""
    fields = split_status(raw)
    try:
        return PROTOCOLS[len(fields)]()
    except KeyError:
        line = ":".join(fields)
        logger.error(f"Got unexpected input.  {len(fields)} fields in [{line}], expecting one of {sorted(PROTOCOLS)}")
        raise Estim2pyError("Unknown 2B protocol", line) from None
