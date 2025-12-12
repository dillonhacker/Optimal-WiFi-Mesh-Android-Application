# app/tabs/scan_tab.py

from __future__ import annotations

from typing import List, Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
)

from pybackend.rust_bridge import run_wifi_scan


class ScanTab(QWidget):
    """
    Scan tab:
        - Shows house name
        - Floor + Room selectors
        - Run Scan button
        - Table of APs for the selected room
    """

    def __init__(self, state: dict, main_window):
        super().__init__()
        self.state = state
        self.main_window = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Wi-Fi Scanner")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.house_label = QLabel("House: (none)")
        self.house_label.setStyleSheet("margin-bottom: 8px;")
        layout.addWidget(self.house_label)

        # Floor + Room selectors
        selector_row = QHBoxLayout()
        layout.addLayout(selector_row)

        selector_row.addWidget(QLabel("Floor:"))
        self.floor_combo = QComboBox()
        self.floor_combo.currentIndexChanged.connect(self._on_floor_changed)
        selector_row.addWidget(self.floor_combo)

        selector_row.addSpacing(20)

        selector_row.addWidget(QLabel("Room:"))
        self.room_combo = QComboBox()
        self.room_combo.currentIndexChanged.connect(self._on_room_changed)
        selector_row.addWidget(self.room_combo)

        selector_row.addStretch(1)

        # Run Scan button
        self.btn_scan = QPushButton("Run Scan")
        self.btn_scan.setFixedHeight(28)
        self.btn_scan.clicked.connect(self._run_scan)
        layout.addWidget(self.btn_scan)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["SSID", "BSSID", "Freq MHz", "Signal (dBm)", "Channel"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    # ------------------------------------------------------------------ Helpers

    def _current_floor_room_indices(self) -> tuple[int, int] | None:
        floors = self.state.get("floors") or []
        if not floors:
            return None

        f_idx = self.floor_combo.currentIndex()
        if f_idx < 0 or f_idx >= len(floors):
            return None

        rooms = floors[f_idx].get("rooms") or []
        if not rooms:
            return None

        r_idx = self.room_combo.currentIndex()
        if r_idx < 0 or r_idx >= len(rooms):
            return None

        return f_idx, r_idx

    def _clear_table(self):
        self.table.setRowCount(0)

    # ------------------------------------------------------------------ Slots

    def _on_floor_changed(self, idx: int):
        # Repopulate rooms for selected floor
        floors = self.state.get("floors") or []
        self.room_combo.blockSignals(True)
        self.room_combo.clear()
        if 0 <= idx < len(floors):
            for room in floors[idx].get("rooms", []):
                self.room_combo.addItem(room.get("name", "Room"))
        self.room_combo.blockSignals(False)

        self._clear_table()

    def _on_room_changed(self, idx: int):
        # Just clear table; user must run scan for this room
        self._clear_table()

    def _run_scan(self):
        indices = self._current_floor_room_indices()
        if indices is None:
            QMessageBox.warning(self, "No Room Selected", "Please select a floor and room.")
            return

        f_idx, r_idx = indices
        floors = self.state["floors"]
        floor = floors[f_idx]
        room = floor["rooms"][r_idx]

        room_name = room.get("name", f"Room {r_idx + 1}")

        try:
            rows = run_wifi_scan(room_name)
        except Exception as e:
            QMessageBox.critical(self, "Scan Error", str(e))
            return

        # Save scan data to that specific room
        room["scan_data"] = rows

        # Update table
        self._clear_table()
        for ap in rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            ssid = ap.get("ssid", "")
            bssid = ap.get("bssid", "")
            freq = ap.get("freq_mhz", "")
            sig = ap.get("signal_dbm", "")
            ch = ap.get("channel", "")

            self.table.setItem(row_idx, 0, QTableWidgetItem(str(ssid)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(bssid)))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(freq)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(sig)))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(ch)))

        # Let other tabs update summaries / per-room info
        self.main_window.results_tab.refresh_from_state()
        self.main_window.summary_tab.refresh_from_state()

    # ------------------------------------------------------------------ External API

    def refresh_from_state(self):
        # Update labels and combos from global state
        name = self.state.get("house_name") or "Untitled House"
        self.house_label.setText(f"House: {name}")

        floors = self.state.get("floors") or []

        self.floor_combo.blockSignals(True)
        self.room_combo.blockSignals(True)

        self.floor_combo.clear()
        self.room_combo.clear()
        for floor in floors:
            self.floor_combo.addItem(floor.get("name", "Floor"))
        if floors:
            for room in floors[0].get("rooms", []):
                self.room_combo.addItem(room.get("name", "Room"))

        self.floor_combo.blockSignals(False)
        self.room_combo.blockSignals(False)

        self._clear_table()
