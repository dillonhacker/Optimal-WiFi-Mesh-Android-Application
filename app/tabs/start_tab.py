# app/tabs/start_tab.py

from __future__ import annotations

from typing import Dict, Any, List

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
)

# MainWindow is only used for callbacks; use forward reference type hints
# to avoid circular imports at runtime.
if False:  # type checking only
    from app.main_window import MainWindow


class StartTab(QWidget):
    """
    Home screen:
      - Enter house name
      - Choose floors + rooms per floor
      - Create new house
      - Save / Load existing house
    """

    def __init__(self, state: Dict[str, Any], main_window: "MainWindow"):
        super().__init__()
        self.state = state
        self.main_window = main_window

        main_layout = QVBoxLayout(self)

        title = QLabel("Wi-Fi Mesh Optimizer")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        main_layout.addWidget(title)

        subtitle = QLabel("Create a new house layout or load an existing one.")
        subtitle.setStyleSheet("font-size: 13px; color: gray;")
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(15)

        # --- House configuration box ---
        config_group = QGroupBox("House Configuration")
        config_layout = QVBoxLayout(config_group)

        form = QFormLayout()
        config_layout.addLayout(form)

        self.house_name_edit = QLineEdit()
        form.addRow("House Name:", self.house_name_edit)

        self.floor_spin = QSpinBox()
        self.floor_spin.setMinimum(1)
        self.floor_spin.setMaximum(20)
        self.floor_spin.setValue(1)
        self.floor_spin.valueChanged.connect(self._rebuild_room_spinners)
        form.addRow("Number of Floors:", self.floor_spin)

        self.rooms_box = QGroupBox("Rooms per Floor")
        self.rooms_layout = QVBoxLayout(self.rooms_box)
        config_layout.addWidget(self.rooms_box)

        # Create initial room spinners
        self.room_spinners: List[QSpinBox] = []
        self._rebuild_room_spinners(self.floor_spin.value())

        # Create house button row
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.create_btn = QPushButton("Create / Reset House")
        self.create_btn.clicked.connect(self._on_create_house)
        btn_row.addWidget(self.create_btn)

        config_layout.addLayout(btn_row)

        main_layout.addWidget(config_group)

        # --- File actions box ---
        file_group = QGroupBox("Saved Houses")
        file_layout = QHBoxLayout(file_group)

        self.load_btn = QPushButton("Load House…")
        self.load_btn.clicked.connect(self.main_window.load_house)
        file_layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("Save House…")
        self.save_btn.clicked.connect(self.main_window.save_house)
        file_layout.addWidget(self.save_btn)

        file_layout.addStretch(1)

        main_layout.addWidget(file_group)
        main_layout.addStretch(1)

    # ---------- Internal helpers ----------

    def _rebuild_room_spinners(self, count: int) -> None:
        # Clear old
        for i in reversed(range(self.rooms_layout.count())):
            item = self.rooms_layout.itemAt(i)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            self.rooms_layout.removeItem(item)

        self.room_spinners.clear()

        for floor_index in range(count):
            row = QHBoxLayout()
            label = QLabel(f"Rooms on Floor {floor_index + 1}:")
            spinner = QSpinBox()
            spinner.setMinimum(1)
            spinner.setMaximum(50)
            spinner.setValue(2)

            row.addWidget(label)
            row.addWidget(spinner)
            row.addStretch(1)

            container = QWidget()
            container.setLayout(row)
            self.rooms_layout.addWidget(container)

            self.room_spinners.append(spinner)

    def _on_create_house(self) -> None:
        house_name = self.house_name_edit.text()
        num_floors = self.floor_spin.value()
        rooms_per_floor = [spin.value() for spin in self.room_spinners]

        self.main_window.create_or_reset_house(
            house_name=house_name,
            num_floors=num_floors,
            rooms_per_floor=rooms_per_floor,
        )

    # ---------- External API ----------

    def refresh_from_state(self) -> None:
        """
        Called by MainWindow when state changes (new house or loaded house).
        Keeps the Home tab in sync.
        """
        name = self.state.get("house_name", "")
        self.house_name_edit.setText(name)

        floors = self.state.get("floors", [])
        if floors:
            self.floor_spin.blockSignals(True)
            self.floor_spin.setValue(len(floors))
            self.floor_spin.blockSignals(False)
            self._rebuild_room_spinners(len(floors))

            # Try to set room counts if they exist
            for i, floor in enumerate(floors):
                if i < len(self.room_spinners):
                    rooms = floor.get("rooms", [])
                    self.room_spinners[i].setValue(len(rooms))

        # Enable save if we have any house
        has_house = bool(floors)
        self.save_btn.setEnabled(has_house)
