# app/tabs/summary_tab.py

from __future__ import annotations

from collections import Counter
from typing import Dict, Any, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

from pybackend.rust_bridge import compute_best_channel, get_connected_bssid


class SummaryTab(QWidget):
    """
    Displays per-floor summary:
      - Total APs
      - Channel usage histogram
      - Recommended channel with special message if already on best channel.
    """

    def __init__(self, state: dict):
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Summary")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QTextEdit.NoWrap)
        self.text.setStyleSheet("font-family: monospace; font-size: 13px;")
        layout.addWidget(self.text)

    # ------------------------------------------------------------------ Core logic

    def _find_my_channel(
        self, all_scan_data: List[Dict[str, Any]], connected_bssid: Optional[str]
    ) -> Optional[int]:
        """
        Look up the channel of the currently connected BSSID in the scan data.
        """
        if not connected_bssid:
            return None

        target = connected_bssid.lower()
        for ap in all_scan_data:
            bssid = ap.get("bssid")
            ch = ap.get("channel")
            if not bssid or ch is None:
                continue
            if str(bssid).lower() == target:
                return int(ch)

        return None

    # ------------------------------------------------------------------ Public API

    def refresh_from_state(self):
        floors = self.state.get("floors") or []
        lines: List[str] = []

        # Ask Rust once for global recommendation & current BSSID
        try:
            best_global = compute_best_channel()
        except Exception as e:
            best_global = None
            best_err = str(e)
        else:
            best_err = ""

        try:
            connected = get_connected_bssid()
        except Exception:
            connected = None

        for floor in floors:
            floor_name = floor.get("name", "Floor")
            lines.append(f"=== {floor_name} ===")

            # Flatten all scan data for this floor
            all_scan_data: List[Dict[str, Any]] = []
            for room in floor.get("rooms", []):
                scan = room.get("scan_data") or []
                all_scan_data.extend(scan)

            if not all_scan_data:
                lines.append("  No scan data.")
                lines.append("")
                continue

            # AP count
            lines.append(f"  Total APs detected: {len(all_scan_data)}")

            # Channel usage histogram
            channel_counter: Counter[int] = Counter()
            for ap in all_scan_data:
                ch = ap.get("channel")
                if ch:
                    try:
                        channel_counter[int(ch)] += 1
                    except (TypeError, ValueError):
                        pass

            lines.append("  Channel usage:")
            for ch in sorted(channel_counter.keys()):
                lines.append(f"    Ch {ch}: {channel_counter[ch]} APs")

            # My current channel (if we can detect it)
            my_ch = self._find_my_channel(all_scan_data, connected)

            # Recommended channel
            if best_global is None:
                lines.append(f"  Recommended channel: ERROR ({best_err})")
            else:
                if my_ch is not None and int(my_ch) == int(best_global):
                    lines.append(
                        "  Recommended channel: **On the best channel already!**"
                    )
                else:
                    lines.append(f"  Recommended channel: {best_global}")

            lines.append("")

        if not floors:
            lines = ["No house configured yet. Go to the Home tab to create one."]

        self.text.setMarkdown("\n".join(lines))
