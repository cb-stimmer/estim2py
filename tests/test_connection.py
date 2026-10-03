from estim2py import Estim2pyConnection
from estim2py import Estim2pyStatus
from estim2py import Estim2pyError
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

@pytest.fixture
def con(hardware_port):
    return Estim2pyConnection(hardware_port)
    
@pytest.fixture
def reset_2b_resp():
    return b'666:0:0:100:100:0:L:0:2.106\n'
        
@pytest.fixture
def fake_2b_resp():
    return b'746:12:22:32:42:5:L:0:2.106\n'

