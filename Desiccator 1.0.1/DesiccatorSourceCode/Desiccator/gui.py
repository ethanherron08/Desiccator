# gui.py
"""
Desiccator GUI.

The previous version connected three signals to slots
(update_reading / update_status / append_log) but only defined
update_reading -- and that one was itself truncated. All three are
implemented here.
"""

import os
import traceback

import serial
from serial.tools import list_ports

from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
)

from serial_reader import SerialReader


BAUD_RATES = ["1200", "2400", "4800", "9600", "19200", "38400", "57600"]

PARITY_MAP = {
    "None": serial.PARITY_NONE,
    "Even": serial.PARITY_EVEN,
    "Odd": serial.PARITY_ODD,
}

BYTESIZE_MAP = {
    "8": serial.EIGHTBITS,
    "7": serial.SEVENBITS,
}

STOPBITS_MAP = {
    "1": serial.STOPBITS_ONE,
    "2": serial.STOPBITS_TWO,
}

HANDSHAKE_MAP = {
    "None": "none",
    "Xon/Xoff": "xonxoff",
    "Hardware (RTS/CTS)": "rtscts",
}


class ScaleLoggerGUI(QWidget):

    def __init__(self):
        super().__init__()

        self.reader = None
        self.sample_count = 0

        self.setWindowTitle("Desiccator v1.0.1 for Ohaus Adventurer")
        self.resize(760, 620)

        self.build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout()

        # ---------------- port selection ----------------
        port_box = QGroupBox("Port")
        port_layout = QHBoxLayout()

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(320)

        self.refresh_button = QPushButton("Refresh")
        self.test_button = QPushButton("Test Port")

        port_layout.addWidget(self.port_combo, 1)
        port_layout.addWidget(self.refresh_button)
        port_layout.addWidget(self.test_button)
        port_box.setLayout(port_layout)
        layout.addWidget(port_box)

        # ---------------- framing -----------------------
        cfg_box = QGroupBox("Serial settings (must match the balance menu)")
        cfg = QGridLayout()

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(BAUD_RATES)
        self.baud_combo.setCurrentText("9600")

        self.bytesize_combo = QComboBox()
        self.bytesize_combo.addItems(BYTESIZE_MAP.keys())

        self.parity_combo = QComboBox()
        self.parity_combo.addItems(PARITY_MAP.keys())

        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(STOPBITS_MAP.keys())

        self.handshake_combo = QComboBox()
        self.handshake_combo.addItems(HANDSHAKE_MAP.keys())

        cfg.addWidget(QLabel("Baud"),      0, 0)
        cfg.addWidget(self.baud_combo,     0, 1)
        cfg.addWidget(QLabel("Data bits"), 0, 2)
        cfg.addWidget(self.bytesize_combo, 0, 3)
        cfg.addWidget(QLabel("Parity"),    1, 0)
        cfg.addWidget(self.parity_combo,   1, 1)
        cfg.addWidget(QLabel("Stop bits"), 1, 2)
        cfg.addWidget(self.stopbits_combo, 1, 3)
        cfg.addWidget(QLabel("Handshake"), 2, 0)
        cfg.addWidget(self.handshake_combo, 2, 1, 1, 3)

        cfg_box.setLayout(cfg)
        layout.addWidget(cfg_box)

        # ---------------- polling -----------------------
        poll_box = QGroupBox("Polling (use if the balance auto-print is off)")
        poll_layout = QHBoxLayout()

        self.poll_check = QCheckBox("Send print command every")

        self.poll_interval = QDoubleSpinBox()
        self.poll_interval.setRange(1.0, 3600.0)
        self.poll_interval.setValue(60.0)
        self.poll_interval.setSuffix(" s")
        self.poll_interval.setDecimals(0)

        poll_layout.addWidget(self.poll_check)
        poll_layout.addWidget(self.poll_interval)
        poll_layout.addStretch(1)
        poll_box.setLayout(poll_layout)
        layout.addWidget(poll_box)

        # ---------------- status ------------------------
        self.status_label = QLabel("Status: Disconnected")
        self.weight_label = QLabel("Last Weight: ---")
        self.time_label = QLabel("Last Reading: ---")
        self.count_label = QLabel("Samples Logged: 0")

        for w in (
            self.status_label,
            self.weight_label,
            self.time_label,
            self.count_label,
        ):
            layout.addWidget(w)

        self._set_status_colour("Disconnected")

        # ---------------- file --------------------------
        file_layout = QHBoxLayout()
        self.file_button = QPushButton("Select CSV File")
        self.file_label = QLabel("No file selected")
        file_layout.addWidget(self.file_button)
        file_layout.addWidget(self.file_label, 1)
        layout.addLayout(file_layout)

        # ---------------- controls ----------------------
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Logging")
        self.stop_button = QPushButton("Stop Logging")
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        layout.addLayout(control_layout)

        # ---------------- log ---------------------------
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        layout.addWidget(self.log_window, 1)

        self.setLayout(layout)

        self.refresh_ports()

        # ---------------- signals -----------------------
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.test_button.clicked.connect(self.test_port)
        self.file_button.clicked.connect(self.select_file)
        self.start_button.clicked.connect(self.start_logging)
        self.stop_button.clicked.connect(self.stop_logging)

    # ------------------------------------------------------------------
    # slots
    # ------------------------------------------------------------------

    def _set_status_colour(self, text):
        t = text.lower()
        if "connected" in t and "dis" not in t:
            colour = "#0a7d28"
        elif "error" in t:
            colour = "#b00020"
        else:
            colour = "#555555"
        self.status_label.setStyleSheet(
            f"color: {colour}; font-weight: bold;"
        )

    def update_status(self, status):
        """Slot for SerialReader.status_update."""
        self.status_label.setText(f"Status: {status}")
        self._set_status_colour(status)
        self.append_log(f"[status] {status}")

    def append_log(self, message):
        """Slot for SerialReader.log_message."""
        self.log_window.append(message)

        # Keep the buffer bounded -- this runs for days.
        doc = self.log_window.document()
        if doc.blockCount() > 2000:
            cursor = self.log_window.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(
                cursor.MoveOperation.Down,
                cursor.MoveMode.KeepAnchor,
                500,
            )
            cursor.removeSelectedText()

        self.log_window.verticalScrollBar().setValue(
            self.log_window.verticalScrollBar().maximum()
        )

    def update_reading(self, weight, units, timestamp):
        """Slot for SerialReader.new_reading."""
        self.sample_count += 1
        self.weight_label.setText(f"Last Weight: {weight} {units}")
        self.time_label.setText(f"Last Reading: {timestamp}")
        self.count_label.setText(f"Samples Logged: {self.sample_count}")

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def refresh_ports(self):
        self.port_combo.clear()

        ports = list_ports.comports()

        if not ports:
            self.port_combo.addItem("No COM ports found", None)
            return

        for port in ports:
            manufacturer = port.manufacturer or "Unknown"
            display_text = (
                f"{manufacturer} - {port.description} ({port.device})"
            )
            self.port_combo.addItem(display_text, port.device)

    def _selected_port(self):
        return self.port_combo.currentData()

    def test_port(self):
        """Open, report control lines, close. Returns immediately."""
        port = self._selected_port()

        if not port:
            QMessageBox.warning(self, "Warning", "No COM port selected.")
            return

        try:
            ser = serial.Serial(
                port=port,
                baudrate=int(self.baud_combo.currentText()),
                bytesize=BYTESIZE_MAP[self.bytesize_combo.currentText()],
                parity=PARITY_MAP[self.parity_combo.currentText()],
                stopbits=STOPBITS_MAP[self.stopbits_combo.currentText()],
                timeout=0.5,
            )
            ser.dtr = True
            ser.rts = True

            info = (
                f"{port} opened successfully.\n\n"
                f"CTS={ser.cts}  DSR={ser.dsr}  CD={ser.cd}  RI={ser.ri}\n"
                f"Bytes already waiting: {ser.in_waiting}"
            )

            ser.close()

            self.append_log(f"[test] {info}")
            QMessageBox.information(self, "Success", info)

        except Exception as e:
            self.append_log(f"[test failed] {e}")
            QMessageBox.critical(self, "Error", str(e))

    def select_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Select CSV File",
            "scale_log.csv",
            "CSV Files (*.csv)",
        )

        if not filename:
            return

        self.file_label.setText(filename)

        if not os.path.exists(filename):
            with open(filename, "w", newline="") as f:
                f.write("timestamp,weight,units,raw\n")

    def start_logging(self):

        if self.file_label.text() == "No file selected":
            QMessageBox.warning(self, "Warning", "Select output file first.")
            return

        port = self._selected_port()
        if not port:
            QMessageBox.warning(self, "Warning", "Select a COM port.")
            return

        self.reader = SerialReader(
            port=port,
            baudrate=int(self.baud_combo.currentText()),
            csv_file=self.file_label.text(),
            bytesize=BYTESIZE_MAP[self.bytesize_combo.currentText()],
            parity=PARITY_MAP[self.parity_combo.currentText()],
            stopbits=STOPBITS_MAP[self.stopbits_combo.currentText()],
            handshake=HANDSHAKE_MAP[self.handshake_combo.currentText()],
            poll_enabled=self.poll_check.isChecked(),
            poll_interval=self.poll_interval.value(),
        )

        self.reader.new_reading.connect(self.update_reading)
        self.reader.status_update.connect(self.update_status)
        self.reader.log_message.connect(self.append_log)
        self.reader.finished.connect(self._on_reader_finished)

        self.reader.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_logging(self):
        if self.reader:
            self.reader.stop()
            if not self.reader.wait(4000):
                self.append_log("[warn] thread did not exit; terminating")
                self.reader.terminate()
                self.reader.wait(1000)

        self.update_status("Stopped")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def _on_reader_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        if self.reader and self.reader.isRunning():
            self.reader.stop()
            self.reader.wait(4000)
        event.accept()
