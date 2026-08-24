import pytest

from estim2py import Estim2pyStatus
from estim2py import Estim2pyError


def test_constructor(a_status):    
    assert a_status.battery == 746
    assert a_status.a == 8
    assert a_status.b == 30
    assert a_status.c == 160
    assert a_status.d == 100
    assert a_status.mode == 5
    assert a_status.power == "L"
    assert a_status.linked == 0
    assert a_status.version == "2.106"

def test_get_mode(b_status):
    m = b_status.get_mode()
    assert m.mid == 5
    
def test_get_channel(b_status):
    assert b_status.get_channel("a") == 2
    assert b_status.get_channel("b") == 15
    assert b_status.get_channel("c") == 80
    assert b_status.get_channel("d") == 50

def test_get_channel_methods(b_status):
    assert b_status.get_a() == 2
    assert b_status.get_b() == 15
    assert b_status.get_c() == 80
    assert b_status.get_d() == 50

def test_get_channel_handles_uppercaseb(b_status):
    assert b_status.get_channel("A") == 2

def test_get_channel_errors_invalid(a_status):
    with pytest.raises(ValueError):
        assert a_status.get_channel("E")
    
    
def test_equal(b_status):
    assert b_status == b_status
    
def test_equal_different_battery_and_version(b_status):
    same_bin = b'745:4:30:160:100:5:L:0:2.105\n'
    t = Estim2pyStatus.from_binary(same_bin)

    assert b_status == t

def test_not_equal(a_status, b_status):
    assert a_status != b_status

def test_not_equal_type(a_status):
    assert not a_status == None
    assert not a_status == "foo"

def test_greater_than(big_channels, small_channels):
    assert big_channels > small_channels
    assert not big_channels > big_channels

def test_less_than(big_channels, small_channels):
    assert small_channels < big_channels
    assert not big_channels < big_channels

    
def test_greater_than_high_power(big_channels, big_channels_high, small_channels):
    assert big_channels_high > big_channels
    assert big_channels_high > small_channels

def test_greater_than_equals(big_channels, big_channels_high, big_channels_alt, small_channels):
    assert big_channels >= small_channels
    assert big_channels_high >= big_channels
    assert big_channels >= big_channels
    assert not big_channels_alt >= small_channels

def test_less_than_equals(big_channels, big_channels_high, big_channels_alt, small_channels):
    assert small_channels <= big_channels
    assert big_channels <= big_channels_high
    assert small_channels <= small_channels
    assert not small_channels <= big_channels_alt

def test_status_changes_report_none_on_no_change(a_status):
    assert a_status.changes(a_status) == None

def test_statuschnages_report_changes_on_everything(a_status, z_status):
    expected = ("a","b","c","d","mode","power","linked")
    assert a_status.changes(z_status) == expected
    assert z_status.changes(a_status) == expected
    
def test_bad_status():
    with pytest.raises(Estim2pyError) as exc:
        _ = Estim2pyStatus.from_binary(b"foo")

    with pytest.raises(Estim2pyError) as exc:
        _ = Estim2pyStatus.from_binary(b"0:1:2:3:4:5:6:7:8:9:")

def test_dunder_bytes(a_status):
    assert(a_status == Estim2pyStatus.from_binary(bytes(a_status)))

def test_dunder_string(a_status):
    assert(a_status == Estim2pyStatus.from_binary(str(a_status).encode("ascii")))
    
def test_items():
    bin = b'746:4:30:160:100:5:L:0:2.106\n'
    s = Estim2pyStatus.from_binary(bin)

    expected = (
        ("battery",746),
        ("a",4),
        ("b",30),
        ("c",160),
        ("d",100),
        ("mode",5),
        ("power","L"),
        ("linked",0),
        ("version","2.106"))
    
    assert s.as_items() == expected
    
@pytest.fixture
def a_status():
    return Estim2pyStatus.from_binary(b'746:8:30:160:100:5:L:0:2.106\n')

@pytest.fixture
def b_status():
    return Estim2pyStatus.from_binary(b'746:4:30:160:100:5:L:0:2.106\n')

@pytest.fixture
def z_status():
    return Estim2pyStatus.from_binary(b'746:7:28:150:110:4:H:1:2.106\n')

@pytest.fixture
def big_channels_high():
    return Estim2pyStatus.from_binary(b'746:100:180:160:100:5:H:0:2.106\n')

@pytest.fixture
def big_channels():
    return Estim2pyStatus.from_binary(b'746:100:180:160:100:5:L:0:2.106\n')

@pytest.fixture
def small_channels():
    return Estim2pyStatus.from_binary(b'746:2:3:160:100:5:L:0:2.106\n')

@pytest.fixture
def big_channels_alt():
    return Estim2pyStatus.from_binary(b'746:100:180:160:100:6:L:1:2.106\n')

