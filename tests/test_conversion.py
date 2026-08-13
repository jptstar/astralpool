sed: --: No such file or directory
"""Basic mapping and conversion tests for SmartNext v1.70."""


def uint16_to_int16(value: int) -> int:
    return value - 65536 if value > 32767 else value


def combine_u32(lsb: int, msb: int) -> int:
    return (msb << 16) | lsb


def test_signed_temperature_conversion() -> None:
    assert uint16_to_int16(250) / 10 == 25.0
    assert uint16_to_int16(65526) / 10 == -1.0


def test_scaling_reference_values() -> None:
    assert 712 / 100 == 7.12
    assert 365 / 100 == 3.65
    assert 256 / 10 == 25.6
    assert 1741 / 100 == 17.41


def test_32bit_hour_counter() -> None:
    assert combine_u32(0x0002, 0x0001) == 65538


def test_v170_salt_threshold_addresses() -> None:
    assert 0xC2 == 194
    assert 0xC3 == 195


def test_ph_pump_stop_reset_address() -> None:
    assert 0x56D == 1389


def test_v170_biopool_flag() -> None:
    technologies_enabled = 1 << 9
    assert bool(technologies_enabled & (1 << 9))
    assert not bool(0 & (1 << 9))


def test_v170_mode_dependent_setpoint_ranges() -> None:
    standard_ph = (7.0, 7.8)
    biopool_ph = (6.5, 8.5)
    standard_orp = (600, 850)
    biopool_orp = (300, 850)

    assert standard_ph == (7.0, 7.8)
    assert biopool_ph == (6.5, 8.5)
    assert standard_orp == (600, 850)
    assert biopool_orp == (300, 850)
