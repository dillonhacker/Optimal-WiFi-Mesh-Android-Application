# app/tabs/home_tab.py

from __future__ import annotations

from typing import List, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QScrollArea,
)


class HomeTab(QWidget):
    """
    Step 1:
        - House name
        - Number of floors
        - [Continue]

    Step 2:
        For each floor:
            - Number of rooms
            - Room name fields
        - [Finish]
    """

    def __init__(self, state: dict, main_window):
        super().__init__()
        self.state = state
        self.main_window = main_window

        self.page_index = 1  # 1 or 2

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(12, 12, 12, 12)

        # We'll swap between page1 and page2 widgets
        self.page1 = QWidget()
        self.page2 = QWidget()
        self.outer_layout.addWidget(self.page1)
        self.outer_layout.addWidget(self.page2)

        self._build_page1()
        self._build_page2()

        self._show_page(1)

    # ------------------------------------------------------------------ Page 1

    def _build_page1(self):
        layout = QVBoxLayout(self.page1)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Create New House")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(10)

        # House name
        name_row = QHBoxLayout()
        lbl_name = QLabel("House Name:")
        self.house_name_edit = QLineEdit()
        self.house_name_edit.setPlaceholderText("e.g., My House")
        name_row.addWidget(lbl_name)
        name_row.addWidget(self.house_name_edit)
        layout.addLayout(name_row)

        layout.addSpacing(8)

        # Number of floors
        floors_row = QHBoxLayout()
        lbl_floors = QLabel("Number of Floors:")
        self.num_floors_spin = QSpinBox()
        self.num_floors_spin.setRange(1, 20)
        self.num_floors_spin.setValue(1)
        floors_row.addWidget(lbl_floors)
        floors_row.addWidget(self.num_floors_spin)
        layout.addLayout(floors_row)

        layout.addSpacing(20)

        self.btn_continue = QPushButton("Continue")
        self.btn_continue.setFixedHeight(32)
        self.btn_continue.clicked.connect(self._go_to_page2)
        layout.addWidget(self.btn_continue)

        layout.addStretch(1)

    # ------------------------------------------------------------------ Page 2

    def _build_page2(self):
        # Scroll area in case of many floors / rooms
        outer_layout = QVBoxLayout(self.page2)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.page2_title = QLabel("Configure Floors & Rooms")
        self.page2_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        outer_layout.addWidget(self.page2_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        self.page2_inner = QWidget()
        self.page2_inner_layout = QVBoxLayout(self.page2_inner)
        self.page2_inner_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.page2_inner)

        # Footer buttons
        btn_row = QHBoxLayout()
        outer_layout.addLayout(btn_row)
        btn_row.addStretch(1)

        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(lambda: self._show_page(1))
        btn_row.addWidget(self.btn_back)

        self.btn_finish = QPushButton("Finish")
        self.btn_finish.setFixedHeight(32)
        self.btn_finish.clicked.connect(self._finish_house_setup)
        btn_row.addWidget(self.btn_finish)

        self.floor_widgets: List[Dict] = []  # filled in when entering page2

    # ------------------------------------------------------------------ Page switching

    def _show_page(self, index: int):
        self.page_index = index
        self.page1.setVisible(index == 1)
        self.page2.setVisible(index == 2)

    # ------------------------------------------------------------------ Logic

    def _go_to_page2(self):
        # Preserve house name & floor count in state
        house_name = self.house_name_edit.text().strip()
        self.state["house_name"] = house_name
        num_floors = self.num_floors_spin.value()

        # Build per-floor configuration UI
        # Clear old widgets
        for i in reversed(range(self.page2_inner_layout.count())):
            w = self.page2_inner_layout.itemAt(i).widget()
            if w is not None:
                w.setParent(None)

        self.floor_widgets.clear()

        for floor_idx in range(num_floors):
            floor_num = floor_idx + 1
            gb = QGroupBox(f"Floor {floor_num}")
            form = QFormLayout(gb)

            # Rooms spinbox
            rooms_spin = QSpinBox()
            rooms_spin.setRange(1, 50)
            rooms_spin.setValue(2)

            # Container for room name edits
            names_container = QWidget()
            names_layout = QVBoxLayout(names_container)
            names_layout.setContentsMargins(0, 0, 0, 0)
            names_layout.setAlignment(Qt.AlignTop)

            floor_info = {
                "group": gb,
                "rooms_spin": rooms_spin,
                "names_container": names_container,
                "names_layout": names_layout,
                "room_edits": [],  # list[QLineEdit]
            }
            self.floor_widgets.append(floor_info)

            # When room count changes, rebuild name fields
            def handle_rooms_changed(value, fi=floor_info):
                self._rebuild_room_name_fields(fi, value)

            rooms_spin.valueChanged.connect(handle_rooms_changed)

            form.addRow(QLabel("Number of Rooms:"), rooms_spin)
            form.addRow(QLabel("Room Names:"), names_container)

            self.page2_inner_layout.addWidget(gb)

            # Initialize with default number of rooms
            self._rebuild_room_name_fields(floor_info, rooms_spin.value())

        self.page2_inner_layout.addStretch(1)

        self._show_page(2)

    def _rebuild_room_name_fields(self, floor_info: Dict, count: int):
        # Clear old edits
        layout = floor_info["names_layout"]
        for i in reversed(range(layout.count())):
            w = layout.itemAt(i).widget()
            if w is not None:
                w.setParent(None)

        floor_info["room_edits"] = []

        for idx in range(count):
            le = QLineEdit()
            le.setPlaceholderText(f"Room {idx + 1}")
            layout.addWidget(le)
            floor_info["room_edits"].append(le)

    def _finish_house_setup(self):
        floors = []

        for floor_idx, fi in enumerate(self.floor_widgets):
            floor_num = floor_idx + 1
            floor_name = f"Floor {floor_num}"

            room_edits = fi["room_edits"]
            rooms = []
            for idx, le in enumerate(room_edits):
                text = le.text().strip()
                if not text:
                    text = f"Room {idx + 1}"
                rooms.append({"name": text, "scan_data": []})

            floors.append({"name": floor_name, "rooms": rooms})

        self.state["floors"] = floors

        # Notify main window & go to scan tab
        self.main_window.refresh_all_tabs()
        self.main_window.switch_to_scan()

    # ------------------------------------------------------------------ External API

    def refresh_from_state(self):
        # Sync page1 fields from state (for loaded house)
        house_name = self.state.get("house_name", "")
        self.house_name_edit.setText(house_name)
        self.num_floors_spin.setValue(max(1, len(self.state.get("floors", [])) or 1))
