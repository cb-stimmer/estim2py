from estim2py import Estim2pyConnection
from estim2py import Estim2pyStatus
import pytest

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
    assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:0:2.106\n')


@pytest.mark.hardware
def test_integration_kill(con, reset_2b_resp):
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:0:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:0:L:0:2.106\n')

    assert con.kill() == Estim2pyStatus.from_binary(reset_2b_resp)

    
@pytest.mark.hardware
@pytest.mark.xfail(reason="Can't find mic or line mode, but may not be able to set.")
def test_integration_modes_past_13(con, reset_2b_resp):
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.set_mode(14) == Estim2pyStatus.from_binary(b'666:0:0:100:100:14:L:0:2.106\n')
    assert con.set_mode(15) == Estim2pyStatus.from_binary(b'666:0:0:100:100:15:L:0:2.106\n')        
    
@pytest.mark.hardware
@pytest.mark.xfail(reason="For whatever reason, linking doesn't seem to work.")
def test_integration_link_bug(con, reset_2b_resp):
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.link() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:1:2.106\n')

@pytest.fixture
def con(hardware_port):
    return Estim2pyConnection(hardware_port)
    
@pytest.fixture
def reset_2b_resp():
    return b'666:0:0:100:100:0:L:0:2.106\n'
        
@pytest.fixture
def fake_2b_resp():
    return b'746:12:22:32:42:5:L:0:2.106\n'

