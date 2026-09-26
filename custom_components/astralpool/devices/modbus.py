"""Shared Modbus TCP transport coordination.

Many TCP-to-RTU gateways accept multiple TCP connections but can only process one
RTU request at a time.  Serializing requests per gateway prevents responses from
one unit being received while another unit's request is in flight.
"""

from __future__ import annotations

import asyncio


_ENDPOINT_LOCKS: dict[tuple[str, int], asyncio.Lock] = {}


def endpoint_lock(host: str, port: int) -> asyncio.Lock:
    """Return the event-loop lock shared by all clients for one gateway."""
    key = (host.casefold(), port)
    lock = _ENDPOINT_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _ENDPOINT_LOCKS[key] = lock
    return lock
