from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, \
    QSpinBox, QPushButton, QFormLayout, QHBoxLayout


class NewHouseTab(QWidget):
    def __init__(self, state, main_window):
        super().__init__()
        self.state = state
        self.main_window = main_window

        layout = QVBoxLayout(self)

        self.house_name_input = QLineEdit()
        self.house_name_input.setPlaceholderText("Optional house name")

        self.floor_count = QSpinBox()
        self.floor_count.setMinimum(1)
        self.floor_count.setMaximum(20)

        self.create_btn = QPushButton("Create House")
        self.create_btn.clicked.connect(self.create_house)

        form = QFormLayout()
        form.addRow("House Name:", self.house_name_input)
        form.addRow("Number of Floors:", self.floor_count)

        layout.addLayout(form)
        layout.addWidget(self.create_btn)

    def create_house(self):
        name = self.house_name_input.text().strip()
        floors = self.floor_count.value()

        self.state.clear()
        self.state["house_name"] = name
        self.state["floors"] = []

        for i in range(floors):
            self.state["floors"].append({
                "name": f"Floor {i+1}",
                "rooms": [
                    {"name": f"Room 1", "scan_data": []},
                    {"name": f"Room 2", "scan_data": []},
                ]
            })

        self.main_window.tabs.setCurrentIndex(1)  # Move to Scan tab

    def refresh(self):
        self.house_name_input.setText(self.state.get("house_name", ""))
