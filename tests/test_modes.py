import pytest

from estim2py import Estim2pyMode

def test_constructor():
    m = Estim2pyMode.get_mode(0)
    assert m.mid == 0
    assert m.name == "pulse"
    assert m.param_a == "pulse speed"
    assert m.param_b == "pulse feel"
    assert m.notes == "Pulsing on and off"

def test_mode_id_names():
    modes = Estim2pyMode.id_names()

    assert modes[0] == "pulse"
    assert modes[5] == "wave"
    assert modes[8] == "milk"
    assert modes[13] == "training"

def test_beta_mode_names():
    modes = Estim2pyMode.id_names("2.120B")

    assert modes[3] == "flo"
    assert modes[12] == "cycle"
    assert modes[13] == "twist"
    assert modes[16] == "training"
    assert Estim2pyMode.id_names("2.119B") == modes

def test_flo():
    m = Estim2pyMode.get_mode(3, "2.120B")
    assert m.name == "flo"
    assert m.param_a == "A feel"
    assert m.param_b == "B feel"

def test_same_name_different_number():
    assert Estim2pyMode.get_id("step") == 12
    assert Estim2pyMode.get_id("step", "2.106") == 12
    assert Estim2pyMode.get_id("step", "2.120B") == 15
    assert Estim2pyMode.get_id("STEP", "2.120B") == 15

def test_every_mode_number_round_trips():
    for protocol in ("2.106", "2.119B", "2.120B"):
        for mid, name in Estim2pyMode.id_names(protocol).items():
            assert Estim2pyMode.get_id(name, protocol) == mid

def test_unknown_mode_number():
    m = Estim2pyMode.get_mode(16)
    assert m.mid == 16
    assert m.name == "unknown"

def test_unknown_mode_name():
    with pytest.raises(ValueError):
        _ = Estim2pyMode.get_id("flo", "2.106")
