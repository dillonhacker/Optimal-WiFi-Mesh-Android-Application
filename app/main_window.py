# app/main_window.py

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QLabel,
)

from app.tabs.home_tab import HomeTab
from app.tabs.scan_tab import ScanTab
from app.tabs.results_tab import ResultsTab
from app.tabs.summary_tab import SummaryTab


class MainWindow(QMainWindow):
    """
    Top-level window.

    Layout:
        [ Home | Scan | Results | Summary ] (button bar)
        -----------------------------------------------
        [ stacked tab widgets                      ]
    """

    def __init__(self, state: dict):
        super().__init__()
        self.state = state
        self.current_file: Path | None = None

        self.setWindowTitle("WiFi Mesh Optimizer")
        self.resize(1000, 700)

        # Central widget + main layout
        central = QWidget(self)
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(6, 6, 6, 6)

        # Top navigation buttons
        nav_layout = QHBoxLayout()
        self.main_layout.addLayout(nav_layout)

        self.btn_home = QPushButton("Home")
        self.btn_scan = QPushButton("Scan")
        self.btn_results = QPushButton("Results")
        self.btn_summary = QPushButton("Summary")

        for btn in (self.btn_home, self.btn_scan, self.btn_results, self.btn_summary):
            btn.setFixedHeight(30)
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)

        # Status label (shows current house name)
        self.house_label = QLabel("")
        self.house_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.house_label.setStyleSheet("font-weight: bold; padding-right: 8px;")
        nav_layout.addWidget(self.house_label)

        # Stacked tabs
        self.stack = QWidget()
        self.stack_layout = QVBoxLayout(self.stack)
        self.stack_layout.setContentsMargins(0, 6, 0, 0)
        self.main_layout.addWidget(self.stack)

        # Tab widgets
        self.home_tab = HomeTab(self.state, main_window=self)
        self.scan_tab = ScanTab(self.state, main_window=self)
        self.results_tab = ResultsTab(self.state)
        self.summary_tab = SummaryTab(self.state)

        # Simple manual "stack": we show/hide tab widgets
        self.stack_layout.addWidget(self.home_tab)
        self.stack_layout.addWidget(self.scan_tab)
        self.stack_layout.addWidget(self.results_tab)
        self.stack_layout.addWidget(self.summary_tab)

        self._show_only(self.home_tab)

        # Connect nav buttons
        self.btn_home.clicked.connect(lambda: self._switch_to(self.home_tab))
        self.btn_scan.clicked.connect(lambda: self._switch_to(self.scan_tab))
        self.btn_results.clicked.connect(lambda: self._switch_to(self.results_tab))
        self.btn_summary.clicked.connect(lambda: self._switch_to(self.summary_tab))

        # Menus for Save / Load
        self._build_menu_bar()

        # Initial refresh
        self.refresh_all_tabs()

    # ------------------------------------------------------------------ Utils

    def _show_only(self, widget: QWidget):
        for i in range(self.stack_layout.count()):
            w = self.stack_layout.itemAt(i).widget()
            if w is not None:
                w.setVisible(w is widget)

    def _switch_to(self, widget: QWidget):
        self._show_only(widget)
        if widget is self.scan_tab:
            self.scan_tab.refresh_from_state()
        elif widget is self.results_tab:
            self.results_tab.refresh_from_state()
        elif widget is self.summary_tab:
            self.summary_tab.refresh_from_state()
        elif widget is self.home_tab:
            self.home_tab.refresh_from_state()

    def switch_to_scan(self):
        """Called by HomeTab after house setup is finished."""
        self._switch_to(self.scan_tab)

    # ------------------------------------------------------------------ Menus

    def _build_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        act_new = file_menu.addAction("New House")
        act_save = file_menu.addAction("Save House...")
        act_load = file_menu.addAction("Load House...")
        file_menu.addSeparator()
        act_quit = file_menu.addAction("Quit")

        act_new.triggered.connect(self._new_house)
        act_save.triggered.connect(self._save_house_dialog)
        act_load.triggered.connect(self._load_house_dialog)
        act_quit.triggered.connect(self.close)

    # ------------------------------------------------------------------ State helpers

    def refresh_all_tabs(self):
        """Refresh titles / labels when state changes."""
        name = self.state.get("house_name") or "Untitled House"
        self.setWindowTitle(f"WiFi Mesh Optimizer - {name}")
        self.house_label.setText(f"House: {name}")

        self.home_tab.refresh_from_state()
        self.scan_tab.refresh_from_state()
        self.results_tab.refresh_from_state()
        self.summary_tab.refresh_from_state()

    # ---------------------------- New / Save / Load --------------------

    def _new_house(self):
        """Clear state and go back to Home tab wizard."""
        self.state.clear()
        self.state.update(
            {
                "house_name": "",
                "floors": [],
            }
        )
        self.current_file = None
        self.refresh_all_tabs()
        self._switch_to(self.home_tab)

    def _save_house_dialog(self):
        if not self.state.get("floors"):
            QMessageBox.information(
                self,
                "Nothing to save",
                "Please create a house and run at least one scan before saving.",
            )
            return

        default_name = (self.state.get("house_name") or "house").replace(" ", "_")
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save House",
            f"{default_name}.json",
            "JSON Files (*.json)",
        )
        if not path_str:
            return

        path = Path(path_str)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")

        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            self.current_file = path
            QMessageBox.information(self, "Saved", f"House saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving", str(e))

    def _load_house_dialog(self):
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Load House",
            "",
            "JSON Files (*.json)",
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading", str(e))
            return

        # Basic sanity check
        if not isinstance(data, dict) or "floors" not in data:
            QMessageBox.critical(
                self,
                "Invalid File",
                "Selected JSON does not look like a WiFi Mesh Optimizer house file.",
            )
            return

        self.state.clear()
        self.state.update(data)
        self.current_file = path

        self.refresh_all_tabs()
        self._switch_to(self.scan_tab)
