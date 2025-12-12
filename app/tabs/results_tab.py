# app/tabs/results_tab.py

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit


class ResultsTab(QWidget):
    """
    Shows per-floor / per-room scan results in text form.
    """

    def __init__(self, state: dict):
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Scan Results")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QTextEdit.NoWrap)
        self.text.setStyleSheet("font-family: monospace; font-size: 13px;")
        layout.addWidget(self.text)

    def refresh_from_state(self):
        floors = self.state.get("floors") or []
        lines = []

        for floor in floors:
            lines.append(f"=== {floor.get('name', 'Floor')} ===")
            for room in floor.get("rooms", []):
                room_name = room.get("name", "Room")
                lines.append(f"--- {room_name} ---")
                rows = room.get("scan_data") or []
                if not rows:
                    lines.append("  (No data)")
                else:
                    for ap in rows:
                        ssid = ap.get("ssid", "")
                        bssid = ap.get("bssid", "")
                        ch = ap.get("channel", "")
                        sig = ap.get("signal_dbm", "")
                        lines.append(
                            f"  SSID: {ssid or '<hidden>'} | "
                            f"BSSID: {bssid or '<unknown>'} | "
                            f"Ch: {ch} | "
                            f"Signal: {sig} dBm"
                        )
                lines.append("")  # blank after each room
            lines.append("")  # blank after each floor

        if not lines:
            lines.append("No house data yet.")

        self.text.setPlainText("\n".join(lines))
