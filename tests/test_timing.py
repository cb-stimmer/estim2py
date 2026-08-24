from estim2py import Estim2pyConnection
from estim2py import Estim2pyStatus

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.timing]

# DO NOT HOOK UP A SUB TO THIS.

# This test is used to test various timings of the 2B box.
# it sets the power levels pretty high, so being attached to it while this is running
# would be VERY uncomfortable indeed.

# Some tests go as long as 5 seconds on max, on high.


"""This Test file is more a record of discovery rather than a test of behaviour.

Each test will have it's failures tracked in comments.

Tests will be done in reverse chronological order."""


### Test: What is the shortest delay with the most consistent success rate.
# 2026-05-30
# No flushing, Short Timeout

# No prediction.  We just experimenting mad science style now.
# Outcome: 00.4 is safe

# Discussion: This lines up with a ~34 ms transmission time. 

# [False-0.01-0.01_0]
# [False-0.01-0.01_0]
# [False-0.01-0.01_1]
# [False-0.01-0.01_1]
# [False-0.01-0.01_2]
# [False-0.01-0.01_2]
# [False-0.02-0.01_0]
# [False-0.02-0.01_0]
# [False-0.02-0.01_1]
# [False-0.02-0.01_1]
# [False-0.02-0.01_2]
# [False-0.02-0.01_2]
# [False-0.03-0.01_0]
# [False-0.03-0.01_0]
# [False-0.03-0.01_1]
# [False-0.03-0.01_1]
# [False-0.03-0.01_2]
# [False-0.03-0.01_2]

@pytest.mark.skip(reason="conclusion: 0.4s is a relatively safe value")
@pytest.mark.parametrize("timeout",[0.01, 0.01, 0.01])
@pytest.mark.parametrize("delay",  [0.01, 0.02, 0.03, 0.04, 0.05])
@pytest.mark.parametrize("flush",  [False, False])
def test_failure_resolution_coarse(timeout, delay, flush, reset_2b_resp, hardware_port):

    con = Estim2pyConnection(hardware_port, timeout=timeout, delay=delay, do_flush=flush)
    
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:0:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:0:L:0:2.106\n')
    assert con.set_channel('C',75) == Estim2pyStatus.from_binary(b'666:200:100:150:100:0:L:0:2.106\n')
    assert con.set_channel('D',25) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:L:0:2.106\n')

    assert con.high() == Estim2pyStatus.from_binary(b'666:0:0:150:50:0:H:0:2.106\n')

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:150:50:0:H:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:H:0:2.106\n')
    assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:0:2.106\n')

    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    
    assert con.set_mode(5) == Estim2pyStatus.from_binary(b'666:0:0:100:100:5:L:0:2.106\n')
    
    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:5:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:5:L:0:2.106\n')
    assert con.set_channel('C',75) == Estim2pyStatus.from_binary(b'666:200:100:150:100:5:L:0:2.106\n')
    assert con.set_channel('D',25) == Estim2pyStatus.from_binary(b'666:200:100:150:50:5:L:0:2.106\n')

    assert con.high() == Estim2pyStatus.from_binary(b'666:0:0:150:50:5:H:0:2.106\n')

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:150:50:5:H:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:150:50:5:H:0:2.106\n')
    assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:0:2.106\n')



### Proposition: At least a little delay is necessary and is it connected to Baudrate 
# 2026-05-30
# According to https://lucidar.me/en/serialib/most-used-baud-rates-table/
# Each byte will take 1.042 ms

# Prediction:
# anything < 0.001 will fail.
# 0.001 will be (slightly?) intermittent
# 0.002 will be safe.

# Observations:
# not many empty results, but a lot of the results were cut off.

# Outcome:
# A 0.05 Delay will be successful.
# A 0.01 Delay will not

# Discussion:
# There are up to 33 bytes being set, so it's actually 34.386 ms of data transmission
# Which actually fits with the outcome 


@pytest.mark.parametrize("timeout",[0.01, 0.1, 0.2])
@pytest.mark.parametrize("delay",  [0, 0.0005, 0.001, 0.002, 0.01, 0.05, 0.08, 0.1])
@pytest.mark.parametrize("flush",  [False, True])
@pytest.mark.skip(reason="conclusion: no direct correlation between baud and failures")
def test_relation_of_baud_to_delay(timeout, delay, flush, reset_2b_resp, hardware_port):

    con = Estim2pyConnection(hardware_port, timeout=timeout, delay=delay, do_flush=flush)
    
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:0:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:0:L:0:2.106\n')
    assert con.set_channel('C',75) == Estim2pyStatus.from_binary(b'666:200:100:150:100:0:L:0:2.106\n')
    assert con.set_channel('D',25) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:L:0:2.106\n')

    assert con.high() == Estim2pyStatus.from_binary(b'666:0:0:150:50:0:H:0:2.106\n')

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:150:50:0:H:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:H:0:2.106\n')
    assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:0:2.106\n')

    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    
    assert con.set_mode(5) == Estim2pyStatus.from_binary(b'666:0:0:100:100:5:L:0:2.106\n')
    
    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:5:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:5:L:0:2.106\n')
    assert con.set_channel('C',75) == Estim2pyStatus.from_binary(b'666:200:100:150:100:5:L:0:2.106\n')
    assert con.set_channel('D',25) == Estim2pyStatus.from_binary(b'666:200:100:150:50:5:L:0:2.106\n')

    assert con.high() == Estim2pyStatus.from_binary(b'666:0:0:150:50:5:H:0:2.106\n')

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:150:50:5:H:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:150:50:5:H:0:2.106\n')
    assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:0:2.106\n')


### Is a flush before a status needed?  Is a Delay needed?  How about Timeout?
    
# Failures  2026-05-28 
# Run 1 - Box connected and powered
# Flush Delay Timeout
# False   0     0.1
# False   0     0.5
# True    0     0.1
# True    0     0.5
# Run 2 -Box connected but not powered
# False   0     0.1
# False   0     0.5
# False   0      1
# False   0      2
# True    0     0.1
# True    0     0.5
# True    0      1
# True    0      2
# 2026-05-29 - Box connected and powered
# True    0     0.1
# True    0     0.5
@pytest.mark.skip(reason="Conclusion, at least a 0.1 delay is necessary")
@pytest.mark.parametrize("timeout",[0.1, 0.5, 1, 2])
@pytest.mark.parametrize("delay",  [0, 0.1, 0.2, 0.5])
@pytest.mark.parametrize("flush",  [False, True])
def test_what_combo_of_timeout_delay_flush_fails(timeout, delay, flush, reset_2b_resp, hardware_port):

    con = Estim2pyConnection(hardware_port, timeout=timeout, delay=delay, do_flush=flush)
    
    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:0:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:0:L:0:2.106\n')
    assert con.set_channel('C',75) == Estim2pyStatus.from_binary(b'666:200:100:150:100:0:L:0:2.106\n')
    assert con.set_channel('D',25) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:L:0:2.106\n')

    assert con.high() == Estim2pyStatus.from_binary(b'666:0:0:150:50:0:H:0:2.106\n')

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:150:50:0:H:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:150:50:0:H:0:2.106\n')
    assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:0:2.106\n')

    assert con.reset() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    assert con.get_status() == Estim2pyStatus.from_binary(reset_2b_resp)
    
    assert con.set_mode(5) == Estim2pyStatus.from_binary(b'666:0:0:100:100:5:L:0:2.106\n')
    
    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:100:100:5:L:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:100:100:5:L:0:2.106\n')
    assert con.set_channel('C',75) == Estim2pyStatus.from_binary(b'666:200:100:150:100:5:L:0:2.106\n')
    assert con.set_channel('D',25) == Estim2pyStatus.from_binary(b'666:200:100:150:50:5:L:0:2.106\n')

    assert con.high() == Estim2pyStatus.from_binary(b'666:0:0:150:50:5:H:0:2.106\n')

    assert con.set_channel('A',100) == Estim2pyStatus.from_binary(b'666:200:0:150:50:5:H:0:2.106\n')
    assert con.set_channel('B',50) == Estim2pyStatus.from_binary(b'666:200:100:150:50:5:H:0:2.106\n')
    assert con.low() == Estim2pyStatus.from_binary(b'666:0:0:100:100:0:L:0:2.106\n')

    
    
@pytest.fixture
def con(hardware_port):
    return Estim2pyConnection(hardware_port)
    
@pytest.fixture
def reset_2b_resp():
    return b'666:0:0:100:100:0:L:0:2.106\n'
        
@pytest.fixture
def fake_2b_resp():
    return b'746:12:22:32:42:5:L:0:2.106\n'

