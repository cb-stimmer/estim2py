import os
import pytest

HARDWARE_PORT = "/dev/ttyUSB0"
#HARDWARE_AVAILABLE = os.path.exists('/dev/ttyUSB1')

# FOR THE LOVE OF GOD, MOUNT A SCRATCH SUBMISSIVE
# These Tests are brutal, see test_timing.py for more info
# but do not connect anything to the box when running this. 
# https://www.irt.org/foldoc/scratch%20monkey.htm
RUN_HEAVY_TIMING_TESTS = False

# note, would love to get auto-detect working
HARDWARE_AVAILABLE = os.path.exists(HARDWARE_PORT)

def pytest_configure(config):
    config.addinivalue_line("markers", "hardware: mark test as requiring physical hardware")

@pytest.fixture
def hardware_port():
    return HARDWARE_PORT
    
@pytest.fixture(autouse=True)
def skip_non_applicable_tests(request):
    # Only apply to tests marked with @pytest.mark.hardware
    if request.node.get_closest_marker("hardware"):
        if not HARDWARE_AVAILABLE:
            pytest.skip(f"Skipping: 2B not plugged into /dev/{HARDWARE_PORT}.  See conftest.py")

    if request.node.get_closest_marker("timing"):
        if not RUN_HEAVY_TIMING_TESTS:
            pytest.skip("Skipping long running timing tests.")


@pytest.fixture
def mock_serial(mocker, fake_2b_resp):
    mock_ser = mocker.patch('serial.Serial', autospec=True)
    mock_instance = mock_ser.return_value
    mock_instance.read_until.return_value = fake_2b_resp

    return mock_ser
