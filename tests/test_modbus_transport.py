"""Tests for shared TCP-to-RTU gateway coordination."""

import importlib.util
from pathlib import Path


def _load_transport_module():
    path = Path("custom_components/astralpool/devices/modbus.py").resolve()
    spec = importlib.util.spec_from_file_location("modbus_transport_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lock_is_shared_per_gateway_and_not_per_unit_id() -> None:
    transport = _load_transport_module()

    assert transport.endpoint_lock("POOL-GATEWAY", 502) is transport.endpoint_lock(
        "pool-gateway", 502
    )
    assert transport.endpoint_lock("pool-gateway", 502) is not transport.endpoint_lock(
        "pool-gateway", 503
    )
