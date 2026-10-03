from estim2py import Estim2pyConnection
from estim2py import Estim2pyStatus
from estim2py import Estim2pyError
from estim2py import Estim2pyBias
from estim2py import Estim2pyUnsupportedError
from estim2py.protocol import Beta2120Protocol
import pytest

BOX_2131_LINE = b'762:0:0:100:100:0:L:0:0:0:0:0:2.131B\n'

def test_get_status_returns_a_status(fake_2b_resp, mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    s = con.get_status()

    check = Estim2pyStatus.from_binary(fake_2b_resp)
    
    assert s == check

@pytest.mark.parametrize("chan,val",[
    ('A',-1),('A',101),
    ('B',-1),('B',101),
    ('C',1),('A',101),
    ('D',0),('A',101),
    ('E',23)])
def test_set_channel_argument_range(chan,val,fake_2b_resp,mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    
    with pytest.raises(ValueError):
        con.set_channel(chan,val)

def test_set_channel_lower_case(fake_2b_resp, mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    con.set_channel("a",100)
        
def written(con):
    """The commands written to the mocked serial port, in order."""
    return [c.args[0] for c in con.serial.write.call_args_list]

def test_auto_detects_legacy(mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    assert con.protocol.name == "2.106"
    assert written(con) == [b"\r"]

def test_auto_detects_2120(mock_serial):
    mock_serial.return_value.read_until.return_value = BOX_2131_LINE
    con = Estim2pyConnection("COM_FAKE")
    assert con.protocol.name == "2.120B"
    assert con.get_status().version == "2.131B"

def test_forced_protocol_skips_probe(mock_serial):
    con = Estim2pyConnection("COM_FAKE", protocol="2.120B")
    assert con.protocol.name == "2.120B"
    assert written(con) == []

def test_protocol_instance_accepted(mock_serial):
    p = Beta2120Protocol()
    con = Estim2pyConnection("COM_FAKE", protocol=p)
    assert con.protocol is p

def test_unknown_protocol_name(mock_serial):
    with pytest.raises(ValueError):
        _ = Estim2pyConnection("COM_FAKE", protocol="9.999")

def test_detect_retries_once(fake_2b_resp, mock_serial):
    mock_serial.return_value.read_until.side_effect = [b'0:0:0\n', fake_2b_resp]
    con = Estim2pyConnection("COM_FAKE")
    assert con.protocol.name == "2.106"
    assert written(con) == [b"\r", b"\r"]

def test_detect_gives_up_after_retry(mock_serial):
    mock_serial.return_value.read_until.side_effect = [b'0:0:0\n', b'1:1:1\n']
    with pytest.raises(Estim2pyError) as exc:
        _ = Estim2pyConnection("COM_FAKE")
    assert exc.value.data == "1:1:1"

def test_detect_no_reply(mock_serial):
    mock_serial.return_value.read_until.side_effect = [b'', b'']
    with pytest.raises(Estim2pyError) as exc:
        _ = Estim2pyConnection("COM_FAKE")
    assert "menu" in str(exc.value)

@pytest.mark.parametrize("line,on,off", [
    (b'746:12:22:32:42:5:L:0:2.106\n', b"J\r", b"U\r"),
    (BOX_2131_LINE, b"J1\r", b"J0\r")])
def test_link_sends_join_command(line, on, off, mock_serial):
    mock_serial.return_value.read_until.return_value = line
    con = Estim2pyConnection("COM_FAKE")
    _ = con.link()
    assert written(con)[-1] == on
    _ = con.unlink()
    assert written(con)[-1] == off

def test_err_reply_is_retried(fake_2b_resp, mock_serial):
    mock_serial.return_value.read_until.side_effect = [fake_2b_resp, b'ERR\n', fake_2b_resp]
    con = Estim2pyConnection("COM_FAKE")
    assert con.set_channel("A", 10) == Estim2pyStatus.from_binary(fake_2b_resp)
    assert written(con) == [b"\r", b"A10\r", b"A10\r"]

def test_err_reply_twice_raises(fake_2b_resp, mock_serial):
    mock_serial.return_value.read_until.side_effect = [fake_2b_resp, b'ERR\n', b'ERR\n']
    con = Estim2pyConnection("COM_FAKE")
    with pytest.raises(Estim2pyError):
        _ = con.set_channel("A", 10)

def test_empty_reply_raises(fake_2b_resp, mock_serial):
    mock_serial.return_value.read_until.side_effect = [fake_2b_resp, b'']
    con = Estim2pyConnection("COM_FAKE")
    with pytest.raises(Estim2pyError) as exc:
        _ = con.get_status()
    assert "menu" in str(exc.value)

def test_reply_parsed_with_connection_protocol(mock_serial):
    mock_serial.return_value.read_until.return_value = BOX_2131_LINE
    con = Estim2pyConnection("COM_FAKE", protocol="2.106")
    with pytest.raises(Estim2pyError):
        _ = con.get_status()

@pytest.mark.parametrize("call", [
    lambda con: con.dynamic(),
    lambda con: con.set_bias(Estim2pyBias.A),
    lambda con: con.set_output_map(1),
    lambda con: con.step_channel("A", 1),
    lambda con: con.set_warp(1),
    lambda con: con.set_ramp(1)])
def test_beta_methods_unsupported_on_legacy(call, mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    with pytest.raises(Estim2pyUnsupportedError):
        _ = call(con)
    assert written(con) == [b"\r"]

@pytest.mark.parametrize("call,command", [
    (lambda con: con.dynamic(), b"Y\r"),
    (lambda con: con.set_bias(Estim2pyBias.MAX), b"Q0\r"),
    (lambda con: con.set_bias(Estim2pyBias.AVERAGE), b"Q3\r"),
    (lambda con: con.set_output_map(2), b"O2\r"),
    (lambda con: con.step_channel("a", 1), b"A+\r"),
    (lambda con: con.step_channel("D", -1), b"D-\r"),
    (lambda con: con.set_warp(5), b"W5\r"),
    (lambda con: con.set_ramp(3), b"R3\r"),
    (lambda con: con.version(), b"V\r"),
    (lambda con: con.set_mode_by_name("step"), b"M15\r")])
def test_beta_methods_send(call, command, mock_serial):
    mock_serial.return_value.read_until.return_value = BOX_2131_LINE
    con = Estim2pyConnection("COM_FAKE")
    _ = call(con)
    assert written(con)[-1] == command

def test_set_bias_uses_2119_numbering(mock_serial):
    mock_serial.return_value.read_until.return_value = b'344:0:0:100:100:0:L:0:0:0:2.119B\n'
    con = Estim2pyConnection("COM_FAKE")
    _ = con.set_bias(Estim2pyBias.MAX)
    assert written(con)[-1] == b"Q3\r"

def test_warp_unsupported_on_2119(mock_serial):
    mock_serial.return_value.read_until.return_value = b'344:0:0:100:100:0:L:0:0:0:2.119B\n'
    con = Estim2pyConnection("COM_FAKE")
    with pytest.raises(Estim2pyUnsupportedError):
        _ = con.set_warp(1)

@pytest.mark.parametrize("call", [
    lambda con: con.set_output_map(3),
    lambda con: con.set_warp(6),
    lambda con: con.set_ramp(4),
    lambda con: con.step_channel("E", 1),
    lambda con: con.step_channel("A", 2),
    lambda con: con.set_mode_by_name("disco")])
def test_beta_method_arguments(call, mock_serial):
    mock_serial.return_value.read_until.return_value = BOX_2131_LINE
    con = Estim2pyConnection("COM_FAKE")
    with pytest.raises(ValueError):
        _ = call(con)

def test_legacy_version_falls_back_to_status(mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    _ = con.version()
    assert written(con) == [b"\r", b"\r"]

def test_legacy_set_mode_by_name(mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    _ = con.set_mode_by_name("step")
    assert written(con)[-1] == b"M12\r"

def test_del_closes_open_port(mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    con.serial.reset_mock()
    con.__del__()
    con.serial.flush.assert_called_once()
    con.serial.close.assert_called_once()

def test_del_skips_closed_port(mock_serial):
    con = Estim2pyConnection("COM_FAKE")
    con.serial.is_open = False
    con.serial.flush.side_effect = AssertionError("flushed a closed port")
    con.__del__()
    con.serial.close.assert_not_called()

@pytest.mark.hardware
def test_integration(con, reset_2b_resp):
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:0:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:0:L:0:2.106\n')
    assert con.set_channel('C',75) == Estim2pyStatus.from_binary(b'666:200:100:150:100:0:L:0:2.106\n')
    assert con.set_channel('D',25) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:L:0:2.106\n')

    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)

@pytest.mark.xfail(reason="pyserial will continue to wait even if the read_until sequence is observed")
@pytest.mark.timeout(1)
@pytest.mark.hardware
def test_timeout(reset_2b_resp, hardware_port):
    Estim2pyConnection(hardware_port, timeout=3)
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    
@pytest.mark.hardware
def test_integration_power_change_resets_a_b(con, reset_2b_resp):

    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:0:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:0:L:0:2.106\n')
    assert con.set_channel('C',75) == Estim2pyStatus.from_binary(b'666:200:100:150:100:0:L:0:2.106\n')
    assert con.set_channel('D',25) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:L:0:2.106\n')

    assert con.high() == Estim2pyStatus.from_binary(b'666:0:0:150:50:0:H:0:2.106\n')

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:150:50:0:H:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:H:0:2.106\n')

    # 2.106 resets C and D to 100 when switching to low power, 2.120B and later keep them.  2.119B is unverified.
    if con.protocol.name == "2.106":
        assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:0:2.106\n')
    else:
        assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:150:50:0:L:0:2.106\n')


@pytest.mark.hardware
def test_integration_kill(con, reset_2b_resp):
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:0:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:0:L:0:2.106\n')

    assert con.kill() == Estim2pyStatus.from_binary(reset_2b_resp)

    
@pytest.mark.hardware
def test_integration_modes_past_13(con, reset_2b_resp):
    if con.protocol.name == "2.106":
        pytest.xfail("2.106 has modes 0-13 only.  Can't find mic or line mode, but may not be able to set.")
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.set_mode(14) == Estim2pyStatus.from_binary(b'666:0:0:100:100:14:L:0:2.106\n')
    assert con.set_mode(15) == Estim2pyStatus.from_binary(b'666:0:0:100:100:15:L:0:2.106\n')        
    
@pytest.mark.hardware
def test_integration_link(con, reset_2b_resp):
    if con.protocol.name == "2.106":
        pytest.xfail("For whatever reason, linking doesn't seem to work on 2.106.")
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.link() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:1:2.106\n')
    assert con.unlink() == Estim2pyStatus.from_binary(reset_2b_resp)

@pytest.mark.hardware
def test_integration_beta_settings(con, reset_2b_resp):
    """Checks the beta-only commands, and that the simulator's guesses match the box.  A and B stay at 0."""
    if not con.protocol.supports("dynamic"):
        pytest.skip(f"Firmware {con.protocol.name} has no beta settings.")
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)

    if con.protocol.supports("warp"):
        assert con.set_warp(2).warp == 2
        assert con.set_ramp(1).ramp == 1
    assert con.set_output_map(1).output_map == 1
    assert con.set_bias(Estim2pyBias.AVERAGE).get_bias() == Estim2pyBias.AVERAGE
    assert con.step_channel("C", 1).get_c() == 51
    assert con.step_channel("C", -1).get_c() == 50
    assert con.link().is_linked()

    # Like the simulator: a new mode resets the channels but keeps power, link and the beta settings.
    _ = con.set_channel("C", 75)
    s = con.set_mode_by_name("flo")
    assert s.get_mode().name == "flo"
    assert (s.c, s.d) == (100, 100)
    assert s.is_linked()
    assert s.output_map == 1
    assert s.get_bias() == Estim2pyBias.AVERAGE
    if con.protocol.supports("warp"):
        assert (s.warp, s.ramp) == (2, 1)

    # Dynamic power resets the bias to 0, which is Max on 2.120B and later.
    s = con.dynamic()
    assert s.is_dynamic_power()
    assert (s.a, s.b) == (0, 0)
    assert s.bias == 0
    assert con.version().protocol == con.protocol.name

    _ = con.reset()

@pytest.fixture
def con(hardware_port):
    return Estim2pyConnection(hardware_port)
    
@pytest.fixture
def reset_2b_resp():
    return b'666:0:0:100:100:0:L:0:2.106\n'
        
@pytest.fixture
def fake_2b_resp():
    return b'746:12:22:32:42:5:L:0:2.106\n'

