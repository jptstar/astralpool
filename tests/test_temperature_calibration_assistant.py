"""Tests for the hardware-validated Smart Next temperature calibration."""

from __future__ import annotations

import asyncio

import pytest

from custom_components.astralpool.devices.smartnext.calibration_debug import (
    COIL_TEMPERATURE_CALIBRATION,
    COIL_TEMPERATURE_CALIBRATION_RESET,
    HR_CALIBRATION_VALUE,
)
from custom_components.astralpool.devices.smartnext import temperature_calibration


class FakeApi:
    def __init__(self) -> None:
        self.writes: list[tuple[str, int, int | bool]] = []

    async def async_write_register(self, address: int, value: int) -> None:
        self.writes.append(("register", address, value))

    async def async_write_coil(self, address: int, value: bool) -> None:
        self.writes.append(("coil", address, value))


@pytest.mark.asyncio
async def test_temperature_calibration_writes_reference_then_b0f(monkeypatch) -> None:
    api = FakeApi()
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    await temperature_calibration.async_calibrate_temperature(api, 29.0)

    assert api.writes == [
        ("register", HR_CALIBRATION_VALUE, 290),
        ("coil", COIL_TEMPERATURE_CALIBRATION, True),
    ]
    assert sleeps == [15.0]


@pytest.mark.asyncio
async def test_temperature_factory_reset_writes_b0d_then_waits(monkeypatch) -> None:
    api = FakeApi()
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    await temperature_calibration.async_reset_temperature_calibration(api)

    assert api.writes == [
        ("coil", COIL_TEMPERATURE_CALIBRATION_RESET, True),
    ]
    assert sleeps == [15.0]
