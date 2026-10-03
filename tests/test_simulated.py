import pytest
from estim2py import Estim2pyStatus
from estim2py import Estim2pyConnection
from estim2py import Estim2pySimulatedConnection
from estim2py import Estim2pyError
from estim2py import Estim2pyBias
from estim2py import Estim2pyUnsupportedError

def test_constructor(default_status):
    s = Estim2pySimulatedConnection()
    assert isinstance(s, Estim2pyConnection)

    assert s.get_status() == default_status

def test_set_and_get(driver, default_status, changed_status):
    assert driver.get_status() == default_status
    assert driver.change_all() == changed_status
    
def test_kill(driver, default_status, changed_status, changed_then_kill):
    assert driver.get_status() == default_status
    assert driver.change_all() == changed_status
    
    assert driver.target.kill() == changed_then_kill
    
def test_mode(driver, default_status, changed_status, changed_then_mode):
    assert driver.get_status() == default_status
    assert driver.change_all() == changed_status
    assert driver.target.set_mode(5) == changed_then_mode
    
def test_reset(driver, default_status, changed_status):
    assert driver.get_status() == default_status
    assert driver.change_all() == changed_status
    driver.target.reset()
    assert driver.get_status() == default_status

def test_set_to_status(driver, default_status, changed_for_set_to_status):
    assert driver.target.get_status() == default_status
    assert driver.target.set_to_status(changed_for_set_to_status)

def test_returns_fresh_statuses(driver, default_status, changed_for_set_to_status):
    d: Estim2pyStatus = driver.target.get_status()
    assert d == default_status

    driver.target.set_to_status(changed_for_set_to_status)
    c = driver.target.get_status()
    assert d == default_status
    assert c == changed_for_set_to_status

    assert c != d

def test_failture(driver, default_status):
    assert not driver.target.error_on_next(False)
    assert driver.target.get_status() == default_status

    assert driver.target.error_on_next(True)
    with pytest.raises(Estim2pyError) as exc:
        driver.target.set_mode(5)
        
    
@pytest.fixture
def default_status():
    return Estim2pyStatus.from_binary(b"320:0:0:100:100:0:L:0:0.0.1\n")

@pytest.fixture
def changed_status():
    return Estim2pyStatus.from_binary(b"320:2:4:8:24:0:H:1:0.0.1\n")

@pytest.fixture
def changed_then_mode():
    return Estim2pyStatus.from_binary(b"320:0:0:100:100:5:H:1:0.0.1\n")

@pytest.fixture
def changed_then_power():
    return Estim2pyStatus.from_binary(b"320:0:0:40:60:0:H:1:0.0.1\n")

@pytest.fixture
def changed_then_kill():
    return Estim2pyStatus.from_binary(b"320:0:0:8:24:0:H:1:0.0.1\n")

@pytest.fixture
def changed_for_set_to_status():
    return Estim2pyStatus.from_binary(b"320:2:4:8:24:5:H:0:0.0.1\n")

@pytest.fixture
def simulated():
    return Estim2pySimulatedConnection()

@pytest.fixture
def driver():
    return BoxDriver()
    
class BoxDriver():
    def __init__(self):
        self.target = Estim2pySimulatedConnection()

    def get_status(self):
        return self.target.get_status()
        
    def change_all(self):
        self.set_high()
        self.set_link()
        self.set_channels()

        return self.get_status()
    
    def set_high(self):
        return self.target.high()

    def set_link(self):
        return self.target.link()
        
    def set_channels(self):    
        self.target.set_channel('A',1)
        self.target.set_channel('B',2)
        self.target.set_channel('C',4)
        return self.target.set_channel('D',12)
        


PROTOCOLS = ["2.106", "2.119B", "2.120B"]

@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_simulates_protocol(protocol):
    sim = Estim2pySimulatedConnection(protocol)
    s = sim.get_status()
    assert sim.protocol.name == protocol
    assert s.protocol == protocol
    assert len(str(s).split(":")) == sim.protocol.field_count

@pytest.mark.parametrize("protocol,c_after_low", [("2.106", 100), ("2.119B", 150), ("2.120B", 150)])
def test_low_power_resets_c_and_d_on_2106_only(protocol, c_after_low):
    sim = Estim2pySimulatedConnection(protocol)
    sim.high()
    sim.set_channel("A", 50)
    sim.set_channel("C", 75)
    s = sim.low()
    assert (s.a, s.c, s.power) == (0, c_after_low, "L")

@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_link(protocol):
    sim = Estim2pySimulatedConnection(protocol)
    assert sim.link().is_linked()
    assert sim.unlink().is_unlinked()

def test_beta_settings():
    sim = Estim2pySimulatedConnection("2.120B")
    assert sim.dynamic().is_dynamic_power()
    assert sim.set_bias(Estim2pyBias.AVERAGE).get_bias() == Estim2pyBias.AVERAGE
    assert sim.set_output_map(2).output_map == 2
    assert sim.set_warp(5).warp == 5
    assert sim.set_ramp(3).ramp == 3
    assert sim.set_mode_by_name("flo").get_mode().name == "flo"

def test_mode_keeps_beta_settings():
    sim = Estim2pySimulatedConnection("2.120B")
    sim.set_warp(2)
    sim.link()
    s = sim.set_mode(3)
    assert (s.mode, s.warp, s.linked) == (3, 2, 1)

def test_step_channel_clamps():
    sim = Estim2pySimulatedConnection("2.120B")
    assert sim.step_channel("A", 1).get_a() == 1
    assert sim.step_channel("A", -1).get_a() == 0
    assert sim.step_channel("A", -1).get_a() == 0
    assert sim.step_channel("D", 1).get_d() == 51

def test_legacy_simulator_rejects_beta_methods():
    sim = Estim2pySimulatedConnection()
    with pytest.raises(Estim2pyUnsupportedError):
        sim.dynamic()

@pytest.mark.parametrize("source,target", [(a, b) for a in PROTOCOLS for b in PROTOCOLS])
def test_set_to_status_across_firmware(source, target):
    origin = Estim2pySimulatedConnection(source)
    origin.high()
    origin.set_mode_by_name("step")
    origin.set_channel("A", 10)
    origin.set_channel("C", 30)
    want = origin.get_status()

    box = Estim2pySimulatedConnection(target)
    assert box.set_to_status(want)
    got = box.get_status()
    assert got.get_mode().name == "step"
    assert (got.get_a(), got.get_c(), got.power) == (10, 30, "H")

def test_set_to_status_translates_bias():
    origin = Estim2pySimulatedConnection("2.119B")
    origin.set_bias(Estim2pyBias.MAX)
    box = Estim2pySimulatedConnection("2.120B")
    assert box.set_to_status(origin.get_status())
    assert box.get_status().get_bias() == Estim2pyBias.MAX
    assert box.get_status().bias == 0

def test_set_to_status_links_on_beta():
    origin = Estim2pySimulatedConnection("2.120B")
    origin.link()
    box = Estim2pySimulatedConnection("2.120B")
    assert box.set_to_status(origin.get_status())
    assert box.get_status().is_linked()

def test_set_to_status_does_not_change_its_argument():
    origin = Estim2pySimulatedConnection("2.106")
    origin.link()
    want = origin.get_status()
    Estim2pySimulatedConnection("2.106").set_to_status(want)
    assert want.is_linked()

def test_set_to_status_mode_missing_on_target():
    origin = Estim2pySimulatedConnection("2.120B")
    origin.set_mode_by_name("flo")
    with pytest.raises(ValueError):
        Estim2pySimulatedConnection("2.106").set_to_status(origin.get_status())

def test_dynamic_resets_bias():
    sim = Estim2pySimulatedConnection("2.120B")
    sim.set_bias(Estim2pyBias.AVERAGE)
    assert sim.dynamic().get_bias() == Estim2pyBias.MAX

def test_set_to_status_dynamic_keeps_bias():
    origin = Estim2pySimulatedConnection("2.120B")
    origin.dynamic()
    origin.set_bias(Estim2pyBias.A)
    box = Estim2pySimulatedConnection("2.120B")
    assert box.set_to_status(origin.get_status())
    assert box.get_status().get_bias() == Estim2pyBias.A
