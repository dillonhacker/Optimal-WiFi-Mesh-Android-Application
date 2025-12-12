"""
app/state.py

AppState centralizes all mutable runtime data:
- House structure: floors -> rooms -> scans
- Methods to clear/reset/save the data

This avoids passing raw dicts everywhere and keeps behavior consistent.
"""

import json


class AppState:
    """
    Global application state.

    Structure:
        house = {
            "floors": [
                {
                    "rooms": [
                        {"name": "Room 1", "scan": {...} or None},
                        ...
                    ]
                },
                ...
            ]
        }
    """

    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        """Reset the entire house + scan data."""
        self.house = {"floors": []}

    def save(self, path: str = "house.json") -> None:
        """
        Save current house data to disk as JSON.

        Users never need to open JSON manually; this is for persistence only.
        """
        with open(path, "w") as f:
            json.dump(self.house, f, indent=2)
