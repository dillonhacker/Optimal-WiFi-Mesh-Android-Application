# pybackend/rust_bridge.py
"""
Python ↔ Rust bridge for wifi_backend (PyO3 module).

Exposes:
    - run_wifi_scan(room_name: str) -> list[dict]
    - compute_best_channel() -> int
    - get_connected_bssid() -> str | None
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional

import wifi_backend  # compiled PyO3 module


def run_wifi_scan(room_name: str) -> List[Dict[str, Any]]:
    """
    Call Rust wifi_backend.scan() and return a list of AP dictionaries.

    Expected Rust dict keys:
        ssid: str (optional)
        bssid: str (optional)
        freq_mhz: int (optional)
        signal_dbm: float (optional)
        channel: int (optional)
    """
    rows = wifi_backend.scan()

    if not isinstance(rows, list):
        raise RuntimeError(f"wifi_backend.scan() returned invalid type: {type(rows)!r}")

    out: List[Dict[str, Any]] = []
    for idx, ap in enumerate(rows):
        if not isinstance(ap, dict):
            print(f"WARNING: scan result entry {idx} is not a dict: {ap!r}")
            continue
        out.append(ap)

    return out


def compute_best_channel() -> int:
    """
    Proxy to Rust's compute_best_channel(), which uses its own scan +
    heuristics to pick a good channel.
    """
    best = wifi_backend.compute_best_channel()
    if not isinstance(best, int):
        raise RuntimeError(f"wifi_backend.compute_best_channel() returned {best!r}")
    return best


def get_connected_bssid() -> Optional[str]:
    """
    Proxy to Rust's connected_bssid().

    Returns:
        - "aa:bb:cc:dd:ee:ff" string, or
        - None if not associated / not detectable.
    """
    try:
        val = wifi_backend.connected_bssid()
    except AttributeError:
        # Older native lib that doesn't expose this yet
        return None

    if val is None:
        return None
    if isinstance(val, str):
        return val or None

    # Defensive: Rust *should* always return string or None
    return str(val) or None
