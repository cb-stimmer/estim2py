import logging

import pytest

from estim2py import Estim2pyError, Estim2pyStatus
from estim2py.protocol import (
    Beta2119Protocol,
    Beta2120Protocol,
    Legacy2106Protocol,
    detect_protocol,
    split_status,
)

LEGACY_LINE = b'666:0:0:100:100:0:L:0:2.106\n'
BETA_LINE = b'344:10:12:120:116:15:L:0:0:0:2.119B\n'
BETA_2120_LINE = b'344:10:12:120:116:15:L:0:0:0:0:0:2.120B\n'
BOX_2131_LINE = b'762:0:0:100:100:0:L:0:0:0:0:0:2.131B\n'  # reset reply from a real 2.131B box


def test_detect_legacy():
    assert isinstance(detect_protocol(LEGACY_LINE), Legacy2106Protocol)

def test_detect_beta():
    assert isinstance(detect_protocol(BETA_LINE), Beta2119Protocol)

@pytest.mark.parametrize("raw", [BETA_2120_LINE, BOX_2131_LINE])
def test_detect_beta_2120(raw):
    assert isinstance(detect_protocol(raw), Beta2120Protocol)

@pytest.mark.parametrize("raw", [b'1:2:3:4:5:6:7:8\n', b'1:2:3:4:5:6:7:8:9:10\n', b'1:2:3:4:5:6:7:8:9:10:11:12\n', b'1:2:3:4:5:6:7:8:9:10:11:12:13:14\n'])
def test_detect_unknown_field_count(raw):
    with pytest.raises(Estim2pyError) as exc:
        _ = detect_protocol(raw)
    assert exc.value.data == raw.decode().strip()

@pytest.mark.parametrize("raw", [b'', b'\n', b'foo'])
def test_detect_not_a_status(raw):
    with pytest.raises(Estim2pyError):
        _ = detect_protocol(raw)

def test_error_message_carries_raw_line():
    with pytest.raises(Estim2pyError) as exc:
        _ = detect_protocol(b'1:2:3\n')
    assert str(exc.value) == "Unknown 2B protocol (1:2:3)"

def test_parse_legacy():
    s = Estim2pyStatus.from_binary(LEGACY_LINE)
    assert s.as_items() == (("battery",666),("a",0),("b",0),("c",100),("d",100),
                            ("mode",0),("power","L"),("linked",0),("version","2.106"))
    assert s.bias is None
    assert s.output_map is None
    assert s.protocol == "2.106"

def test_parse_beta():
    s = Estim2pyStatus.from_binary(BETA_LINE)
    assert s.as_items() == (("battery",344),("a",10),("b",12),("c",120),("d",116),
                            ("mode",15),("power","L"),("linked",0),("version","2.119B"))
    assert s.bias == 0
    assert s.output_map == 0
    assert s.protocol == "2.119B"

def test_parse_beta_join_maps_to_linked():
    s = Estim2pyStatus.from_binary(b'344:10:12:120:116:15:L:3:1:2:2.119B\n')
    assert s.is_linked()
    assert s.bias == 3
    assert s.output_map == 2

@pytest.mark.parametrize("power", ["L", "H", "D"])
def test_parse_beta_power_modes(power):
    s = Estim2pyStatus.from_binary(f'344:10:12:120:116:15:{power}:0:0:0:2.119B\n'.encode())
    assert s.power == power

@pytest.mark.parametrize("bias", [0, 1, 2, 3])
def test_parse_beta_bias(bias):
    assert Estim2pyStatus.from_binary(f'344:0:0:100:100:0:L:{bias}:0:0:2.119B'.encode()).bias == bias

@pytest.mark.parametrize("output_map", [0, 1, 2])
def test_parse_beta_output_map(output_map):
    assert Estim2pyStatus.from_binary(f'344:0:0:100:100:0:L:0:0:{output_map}:2.119B'.encode()).output_map == output_map

def test_legacy_rejects_dynamic_power():
    with pytest.raises(Estim2pyError):
        _ = Estim2pyStatus.from_binary(b'666:0:0:100:100:0:D:0:2.106\n')

def test_beta_rejects_non_numeric_field():
    with pytest.raises(Estim2pyError):
        _ = Estim2pyStatus.from_binary(b'344:10:12:120:116:15:L:x:0:0:2.119B\n')

def test_parse_rejects_wrong_field_count():
    with pytest.raises(Estim2pyError):
        _ = Legacy2106Protocol().parse(split_status(BETA_LINE))

def test_beta_version_mismatch_warns(caplog):
    with caplog.at_level(logging.WARNING, logger="estim2py.protocol"):
        s = Estim2pyStatus.from_binary(b'344:10:12:120:116:15:L:0:0:0:2.200\n')
    assert s.protocol == "2.119B"
    assert "2.200" in caplog.text

def test_beta_version_match_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING, logger="estim2py.protocol"):
        _ = Estim2pyStatus.from_binary(BETA_LINE)
    assert caplog.text == ""

def test_parse_beta_2120():
    s = Estim2pyStatus.from_binary(BETA_2120_LINE)
    assert s.as_items() == (("battery",344),("a",10),("b",12),("c",120),("d",116),
                            ("mode",15),("power","L"),("linked",0),("version","2.120B"))
    assert (s.bias, s.output_map, s.warp, s.ramp) == (0, 0, 0, 0)
    assert s.protocol == "2.120B"

def test_parse_beta_2120_every_field_in_place():
    s = Estim2pyStatus.from_binary(b'344:10:12:120:116:15:D:3:1:2:5:3:2.120B\n')
    assert s.power == "D"
    assert s.bias == 3
    assert s.is_linked()
    assert s.output_map == 2
    assert s.warp == 5
    assert s.ramp == 3

def test_parse_real_2131_box(caplog):
    with caplog.at_level(logging.WARNING, logger="estim2py.protocol"):
        s = Estim2pyStatus.from_binary(BOX_2131_LINE)
    assert s.protocol == "2.120B"
    assert s.version == "2.131B"
    assert (s.battery, s.a, s.b, s.c, s.d, s.mode, s.power) == (762, 0, 0, 100, 100, 0, "L")
    assert caplog.text == ""

def test_older_protocols_have_no_warp_or_ramp():
    for line in (LEGACY_LINE, BETA_LINE):
        s = Estim2pyStatus.from_binary(line)
        assert s.warp is None
        assert s.ramp is None

def test_join_commands():
    assert Legacy2106Protocol().join_command(True) == "J"
    assert Legacy2106Protocol().join_command(False) == "U"
    assert Beta2119Protocol().join_command(True) == "J1"
    assert Beta2119Protocol().join_command(False) == "J0"
    assert Beta2120Protocol().join_command(True) == "J1"
    assert Beta2120Protocol().join_command(False) == "J0"

def test_supports():
    assert not Legacy2106Protocol().supports("dynamic")
    assert Beta2119Protocol().supports("dynamic")
    assert not Beta2119Protocol().supports("teleport")
    assert Beta2120Protocol().supports("warp")
    assert not Beta2120Protocol().supports("high_speed")
